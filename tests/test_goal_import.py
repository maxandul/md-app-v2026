"""Folder uploads and visible Word/PDF goal extraction, synthetic fixtures only."""
import io
import re
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile

from tests import test_word_packages as fixtures
from webapp.services.legacy_forms import parse_legacy_form, scan_legacy_forms, import_legacy_forms
from webapp.services.word_packages import prior_goals
from webapp.services.goal_documents import pdf_goals
from webapp.services.goal_batches import preview

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def word(path, year=2025, modern=False, review=False, title='Projekt abschliessen'):
    def p(text):
        return f'<w:p><w:r><w:t>{text}</w:t></w:r></w:p>'
    def cell(text):
        return '<w:tc>' + p(text) + '</w:tc>'
    def sdt(tag, content):
        return f'<w:sdt><w:sdtPr><w:tag w:val="{tag}"/></w:sdtPr><w:sdtContent>{content}</w:sdtContent></w:sdt>'
    header = '<w:tr>' + ''.join(cell(v) for v in ('Ziel', 'Messkriterien', 'Weg zum Ziel', 'Termin')) + '</w:tr>'
    title = cell(title) if modern else sdt('ab_ziel', '<w:tc>' + sdt('ab_ziel', p(title)) + '</w:tc>')
    row = '<w:tr>' + title + cell('Qualität bestätigt') + cell('Erheben und umsetzen') + cell('31.12.2025') + '</w:tr>'
    dev = '<w:tr>' + cell('Selbstmanagement (Eigenverantwortung)') + '</w:tr>'
    dev += header.replace('>Ziel<', '>Entwicklungsziel<')
    dev += '<w:tr>' + ''.join(cell(v) for v in ('Prioritäten setzen', 'Termine einhalten', 'Planen', '')) + '</w:tr>'
    content = p('Mitarbeitenden-Dialog (MD) - ' + ('Rückblick' if review else 'Ausblick'))
    content += sdt('ab_pn', p('111113')) + p(f'Ausblick auf: {year} bis {year}')
    content += '<w:tbl>' + header + row + '</w:tbl><w:tbl>' + dev + '</w:tbl>'
    with ZipFile(path, 'w') as z:
        z.writestr('word/document.xml', f'<w:document xmlns:w="{W}"><w:body>{content}</w:body></w:document>')
    return path


class GoalImportTest(unittest.TestCase):
    setUp = fixtures.WordPackagesTest.setUp
    tearDown = fixtures.WordPackagesTest.tearDown

    def test_old_nested_controls_and_new_untagged_cells_are_read_once(self):
        for modern in (False, True):
            data = parse_legacy_form(word(self.root / f'{modern}.docx', modern=modern))
            self.assertEqual(len(data['performance_goals']), 1)
            self.assertEqual(data['performance_goals'][0]['title'], 'Projekt abschliessen')
            self.assertEqual(len(data['development_goals']), 1)
            self.assertEqual(data['performance_goals'][0]['criteria'], 'Qualität bestätigt')
            self.assertEqual(data['detected_years'], [2025])

    def test_year_and_document_type_cannot_be_silently_overridden(self):
        folder = self.root / 'sources'; folder.mkdir()
        word(folder / 'wrong-year.docx', year=2026)
        word(folder / 'review.docx', review=True)
        result = import_legacy_forms(self.db, forms_root=folder, goal_year=2025)
        self.assertEqual(result['imported'], 0)
        self.assertEqual(result['counts'], {'not_outlook': 1, 'year_mismatch': 1})

    def test_mixed_upload_preview_select_import_and_export_source(self):
        client = self.app.test_client()
        data = client.post('/alte-ziele/batches', data={'goal_year': 2025}).json
        raw = word(self.root / 'old.docx').read_bytes()
        for filename, content in [('folder/old.docx', raw), ('nested/old.docx', raw), ('broken.pdf', b'bad')]:
            response = client.post(data['upload_url'], data={'file': (io.BytesIO(content), filename)})
            self.assertEqual(response.status_code, 200)
        page = client.get(data['preview_url'])
        self.assertIn('Identische Datei', page.text)
        self.assertIn('Datei nicht lesbar', page.text)
        self.assertIn('Qualität bestätigt', page.text)
        fingerprint = re.search('name="fingerprint" value="([a-f0-9]+)"', page.text)[1]
        source = re.search('name="source" value="([a-f0-9]+)"', page.text)[1]
        response = client.post(data['preview_url'], data={'checked': 'yes', 'fingerprint': fingerprint, 'source': source}, follow_redirects=True)
        self.assertIn('1 ausgewählte Quelle(n) importiert', response.text)
        goals = prior_goals(self.db, employee_pn='111113', assignment='1', year=2025)
        self.assertEqual(goals[0][0]['title'], 'Projekt abschliessen')
        self.assertEqual(goals[1][0]['competency'], 'Selbstmanagement')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM historical_goals').fetchone()[0], 2)
        # A stale confirmation cannot import a second copy.
        client.post(data['preview_url'], data={'checked': 'yes', 'fingerprint': fingerprint, 'source': source})
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM historical_goals').fetchone()[0], 2)

    def test_conflicting_sources_require_one_choice(self):
        client = self.app.test_client()
        data = client.post('/alte-ziele/batches', data={'goal_year': 2025}).json
        for index, modern in enumerate((False, True)):
            raw = word(self.root / f'{index}.docx', modern=modern, title=f'Variante {index}').read_bytes()
            client.post(data['upload_url'], data={'file': (io.BytesIO(raw), f'{index}.docx')})
        page = client.get(data['preview_url']).text
        fingerprint = re.search('name="fingerprint" value="([a-f0-9]+)"', page)[1]
        sources = re.findall('name="source" value="([a-f0-9]+)"', page)
        response = client.post(data['preview_url'], data={'checked': 'yes', 'fingerprint': fingerprint, 'source': sources})
        self.assertIn('nur eine Quelle', response.text)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM historical_goals').fetchone()[0], 0)

    def test_upload_rejects_wrong_extension_and_path_escape(self):
        client = self.app.test_client()
        data = client.post('/alte-ziele/batches', data={'goal_year': 2025}).json
        self.assertEqual(client.post(data['upload_url'], data={'file': (io.BytesIO(b'bad'), 'foo.exe')}).status_code, 400)
        response = client.post(data['upload_url'], data={'file': (io.BytesIO(b'test'), '../../escape.docx')})
        self.assertEqual(response.status_code, 200)
        self.assertFalse((self.root / 'escape.docx').exists())
        self.assertEqual(client.get(data['preview_url'] + '/original/invalid').status_code, 404)

    def test_pdf_continuation_keeps_all_steps_in_one_goal(self):
        def goal(title, steps, page, top):
            return dict(title=title, criteria='', steps=steps, target_date='', competency='Selbstmanagement', evidence={'page': page, 'top': top})
        parsed = {'data': {'document_kind': 'outlook', 'pn': '111113'}, 'text': 'Ausblick auf: 2025 bis 2025',
                  'performance_goals': [], 'development_goals': [goal('Ziel', 'Erster Schritt', 1, 730), goal('', 'Zweiter Schritt', 2, 85)]}
        with patch('webapp.services.word_pdf.inspect_word_pdf', return_value=parsed):
            data = pdf_goals(Path('test.pdf'))
        self.assertEqual(len(data['development_goals']), 1)
        self.assertEqual(data['development_goals'][0]['steps'], 'Erster Schritt\nZweiter Schritt')
        parsed['development_goals'][1]['competency'] = 'Kommunikationsfähigkeit'
        with patch('webapp.services.word_pdf.inspect_word_pdf', return_value=parsed):
            data = pdf_goals(Path('test.pdf'))
        self.assertTrue(data['issues'])

    def test_new_pdf_is_imported_as_goals_without_creating_official_return(self):
        from tests.test_word_pdf_imports import sample_pdf
        folder = self.root / 'pdf-source'; folder.mkdir()
        path = folder / 'Ausblick.pdf'
        sample_pdf(path, kind='outlook')
        result = scan_legacy_forms(self.db, forms_root=folder, goal_year=2025)
        self.assertEqual(result['items'][0]['document_type'], 'outlook')
        self.assertEqual(len(result['items'][0]['performance_goals']), 1)

        self.assertEqual(result['items'][0]['status'], 'matched')
        applied = import_legacy_forms(self.db, forms_root=folder, goal_year=2025)
        self.assertEqual(applied['imported'], 1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0], 0)
        self.assertEqual(len(prior_goals(self.db, employee_pn='111113', assignment='1', year=2025)[0]), 1)

    def test_identical_goals_in_other_word_representation_are_not_reimported(self):
        folder = self.root / 'identical'; folder.mkdir()
        word(folder / 'old.docx')
        word(folder / 'new.docx', modern=True)
        result = import_legacy_forms(self.db, forms_root=folder, goal_year=2025)
        self.assertEqual(result['imported'], 1)
        self.assertEqual(result['counts']['same_goals'], 1)
        self.assertEqual(result['imported_performance_goals'], 1)
        result = import_legacy_forms(self.db, forms_root=folder, goal_year=2025)
        self.assertEqual(result['imported'], 0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM historical_goals').fetchone()[0], 2)
