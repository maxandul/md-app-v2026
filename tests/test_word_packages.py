from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from webapp import create_app
from webapp.db import get_db
from webapp.services.cycles import create_cycle
from webapp.services.sap_import import import_sap_workbook
from webapp.services.word_packages import create_word_package, load_word_config, prior_goals
from webapp.services.word_templates import render_word_form, W
from webapp.services.legacy_forms import COMPETENCY_TAGS
from tests.sample_data import create_sap_sample

NS = {"w": W}


def synthetic_template(path, prefix):
    def control(tag, index):
        date = '<w:date w:fullDate="1999-01-01T00:00:00Z"/>' if "datum" in tag else ''
        return f'<w:sdt><w:sdtPr><w:id w:val="{index}"/><w:tag w:val="{tag}"/>{date}<w:showingPlcHdr/></w:sdtPr><w:sdtContent><w:p><w:r><w:t> </w:t></w:r></w:p></w:sdtContent></w:sdt>'
    tags = [f"{prefix}_{suffix}" for suffix in ("name", "pn", "funktion", "oe", "name_vg", "pn_vg", "datum_von", "datum_bis", "datum_gespraech")]
    content = ''.join(control(t, i) for i, t in enumerate(tags, 1))
    if prefix == "rb":
        content += control('rb_nebenbeschaeftigung', 20)
        groups = [[f'rb_ziel_{s}_1' for s in ('vorjahr', 'kriterien', 'schritte', 'termin')]]
        groups += [[f'rb_{tag}_vorjahr_{s}_1' for s in ('ziel', 'kriterien', 'schritte', 'termin')] for tag in COMPETENCY_TAGS]
        for group_index, group in enumerate(groups):
            content += '<w:tbl><w:tr>' + ''.join('<w:tc>' + control(t, 100 + group_index * 4 + i) + '</w:tc>' for i, t in enumerate(group)) + '</w:tr></w:tbl>'
    with ZipFile(path, 'w') as z:
        z.writestr('word/document.xml', f'<w:document xmlns:w="{W}"><w:body>{content}</w:body></w:document>')
        z.writestr('word/styles.xml', b'preserved-template-styles')


def xml_for(raw):
    return ET.fromstring(ZipFile(io.BytesIO(raw)).read('word/document.xml'))


def controls(root):
    return {s.find('w:sdtPr/w:tag', NS).get(f'{{{W}}}val'): ''.join(s.itertext()) for s in root.findall('.//w:sdt', NS)}


class WordPackagesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.paths = {kind: str(self.root / f'{kind}.docx') for kind in ('review', 'outlook', 'probation')}
        for kind, prefix in [('review', 'rb'), ('outlook', 'ab'), ('probation', 'pz')]:
            synthetic_template(Path(self.paths[kind]), prefix)
        self.app = create_app({'TESTING': True, 'AUTH_DISABLED': True, 'SECRET_KEY': 'test',
            'DATABASE': str(self.root / 'db.sqlite3'), 'STORAGE_ROOT': str(self.root / 'data'),
            'BACKUP_ROOT': str(self.root / 'backup'), 'DOSSIER_HANDOFF_ROOT': str(self.root / 'handoff'),
            'WORD_TEMPLATE_PATHS': self.paths})
        self.context = self.app.app_context(); self.context.push()
        self.db = get_db()
        sample = create_sap_sample(self.root / 'sap.xlsx')
        result = import_sap_workbook(self.db, sample, original_filename='sap.xlsx', stored_filename='sap.xlsx')
        self.cycle_id = create_cycle(self.db, review_year=2025, sap_import_id=result.import_id)
        self.case_id = self.db.execute("SELECT case_id FROM dialog_cases WHERE employee_pn='111113'").fetchone()[0]

    def tearDown(self):
        self.context.pop(); self.tmp.cleanup()

    def generate(self):
        return create_word_package(self.db, cycle_id=self.cycle_id, manager_pn='111116',
            template_paths=self.paths, output_dir=self.root / 'output', case_id=self.case_id)

    def add_goals(self, title='Erstes Ziel', source_hash='hash1'):
        cursor = self.db.execute("""INSERT INTO legacy_form_imports(goal_year,document_type,employee_pn,assignment_number,original_filename,sha256,imported_at)
            VALUES (2025,'outlook','111113','1','old.docx',?,'2026-10-09')""", (source_hash,))
        self.db.execute("""INSERT INTO historical_goals(legacy_form_import_id,employee_pn,assignment_number,goal_year,goal_kind,sequence,title,criteria,steps,target_date,created_at)
            VALUES (?,'111113','1',2025,'performance',1,?,'Kriterium','• Schritt A\n• Schritt B','31.12.2025','2026-10-09')""", (cursor.lastrowid, title))
        self.db.commit()

    def test_dynamic_rows_empty_competencies_and_date_metadata(self):
        fields = {'name': 'Test & Beispiel', 'datum_von': '01.01.2026', 'datum_bis': '31.12.2026'}
        goals = [{'title': f'Ziel {i}', 'steps': '• Eins\n• Zwei'} for i in range(6)]
        development = [{'title': 'Entwicklung', 'competency': 'Selbstmanagement'}] * 2
        raw = render_word_form(Path(self.paths['review']), kind='review', fields=fields, performance_goals=goals, development_goals=development)
        root = xml_for(raw); values = controls(root)
        self.assertEqual(values['rb_name'], 'Test & Beispiel')
        self.assertIn('6. Ziel 5', values['rb_ziel_vorjahr_6'])
        self.assertIn('2. Entwicklung', values['rb_selbstmanagement_vorjahr_ziel_2'])
        self.assertEqual(values['rb_werteorientierung_vorjahr_ziel_1'], '')
        ids = [n.get(f'{{{W}}}val') for n in root.findall('.//w:sdtPr/w:id', NS)]
        self.assertEqual(len(ids), len(set(ids)))
        dates = root.findall('.//w:date', NS)
        self.assertEqual([n.get(f'{{{W}}}fullDate') for n in dates], ['2026-01-01T00:00:00Z', '2026-12-31T00:00:00Z', None])
        self.assertEqual(ZipFile(io.BytesIO(raw)).read('word/styles.xml'), b'preserved-template-styles')
        self.assertEqual(len(root.findall('.//w:br', NS)), 6)

    def test_late_goals_only_affect_new_output_and_do_not_mark_sent(self):
        first, manifest = self.generate(); first_bytes = first.read_bytes()
        self.assertEqual(len(manifest['documents']), 2)
        self.add_goals()
        second, manifest = self.generate()
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_bytes(), first_bytes)
        self.assertEqual(manifest['documents'][0]['performance_goals'], 1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM package_events').fetchone()[0], 0)
        with ZipFile(second) as z:
            review = next(n for n in z.namelist() if n.startswith('Rueckblick'))
            self.assertIn('Erstes Ziel', controls(xml_for(z.read(review)))['rb_ziel_vorjahr_1'])

    def test_conflicting_goal_sources_stop_generation_without_partial_output(self):
        self.add_goals(); self.add_goals('Andere Version', 'hash2')
        with self.assertRaisesRegex(ValueError, 'mehrere Zielquellen'):
            self.generate()
        self.assertEqual(list((self.root / 'output').iterdir()), [])

    def test_unknown_competency_and_wrong_template_are_not_silently_ignored(self):
        with self.assertRaisesRegex(ValueError, 'bekannte Kompetenz'):
            render_word_form(Path(self.paths['review']), kind='review', fields={}, development_goals=[{'title': 'X', 'competency': 'Unbekannt'}])
        with self.assertRaisesRegex(ValueError, 'fehlt'):
            render_word_form(Path(self.paths['outlook']), kind='review', fields={})

    def test_read_config_resolves_relative_paths(self):
        config = self.root / 'word_config.json'
        config.write_text(json.dumps({'templates': {'review': 'review.docx'}}))
        self.assertEqual(load_word_config(config)['review'], self.paths['review'])

    def test_probation_uses_own_template_and_explicit_period(self):
        self.db.execute("UPDATE dialog_events SET event_type='probation_review' WHERE legacy_case_id=?", (self.case_id,))
        self.db.execute("UPDATE dialog_cases SET official_scope='review_only', period_start='2025-02-01', period_end='2025-04-30' WHERE case_id=?", (self.case_id,))
        path, manifest = self.generate()
        self.assertEqual([d['kind'] for d in manifest['documents']], ['probation'])
        with ZipFile(path) as archive:
            values = controls(xml_for(archive.read(archive.namelist()[0])))
            self.assertEqual(values['pz_datum_von'], '01.02.2025')
            self.assertEqual(values['pz_datum_bis'], '30.04.2025')

    def test_missing_second_template_removes_incomplete_package(self):
        Path(self.paths['outlook']).unlink()
        with self.assertRaisesRegex(ValueError, 'konfiguriert'):
            self.generate()
        self.assertEqual(list((self.root / 'output').iterdir()), [])

    def test_goal_assignment_is_not_taken_from_another_employment(self):
        self.add_goals()
        self.assertEqual(prior_goals(self.db, employee_pn='111113', assignment='2', year=2025), ([], [], {}))

    def test_route_downloads_zip_and_records_generation(self):
        response = self.app.test_client().post(f'/cycles/{self.cycle_id}/managers/111116/word-package', data={'case_id': self.case_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/zip')
        self.assertEqual(len(ZipFile(io.BytesIO(response.data)).namelist()), 2)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM audit_log WHERE action='word_package_created'").fetchone()[0], 1)
        response.close()


if __name__ == '__main__':
    unittest.main()
