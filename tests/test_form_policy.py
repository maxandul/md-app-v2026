"""Regression for optional content, employment bounds and local Word setup."""
import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from webapp import create_app
from webapp.services.form_data import validate_review_period
from webapp.services.word_packages import load_word_config, word_template_status
from webapp.services.word_pdf_imports import matching_cases
from tests import test_word_pdf_imports as fixtures


class FormPolicyTest(unittest.TestCase):
    setUp = fixtures.WordPdfImportsTest.setUp
    tearDown = fixtures.WordPdfImportsTest.tearDown
    stage = fixtures.WordPdfImportsTest.stage
    reviewed = fixtures.WordPdfImportsTest.reviewed
    confirm = fixtures.WordPdfImportsTest.confirm

    def blank_review(self, item):
        reviewed = self.reviewed(item)
        reviewed['data'] = {'document_kind':'review','pn':'111113','period_start':'2025-01-01',
                            'period_end':'2025-12-31','rating':'C'}
        for key in ('performance_goals','development_goals'):
            reviewed[key] = []
        reviewed['assessments'] = {}
        return reviewed

    def test_only_required_content_and_today_default_preserve_original(self):
        item = self.stage()
        original = self.db.execute('SELECT parsed_json FROM word_pdf_imports WHERE id=?',(item,)).fetchone()[0]
        reviewed = self.blank_review(item)
        doc = self.confirm(item,reviewed)
        row = self.db.execute('SELECT * FROM word_pdf_imports WHERE id=?',(item,)).fetchone()
        saved = json.loads(row['reviewed_json'])
        self.assertEqual(saved['data']['dialog_date'],date.today().isoformat())
        self.assertEqual(saved['filled_fields']['dialog_date']['origin'],'current_date')
        self.assertEqual(saved['data']['conducted'],'')
        self.assertNotIn('manager_pn',saved['data'])
        self.assertEqual(row['parsed_json'],original)
        self.assertEqual(self.db.execute('SELECT manager_pn FROM official_documents WHERE id=?',(doc,)).fetchone()[0],'111116')

    def test_required_fields_cannot_be_omitted(self):
        item = self.stage()
        for field in ('period_start','period_end','rating'):
            reviewed = self.blank_review(item);reviewed['data'][field]=''
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.confirm(item,reviewed)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],0)

    def test_selected_assignment_bounds_are_inclusive_and_primary_employee_is_not_used(self):
        with self.db:
            self.db.execute("UPDATE employment_assignments SET entry_date='2025-03-01',exit_date='2025-10-31' WHERE person_number='111113'")
            self.db.execute("UPDATE employees SET entry_date='2020-01-01',exit_date='' WHERE pn='111113'")
        item = self.stage()
        for start,end in [('2025-02-28','2025-10-31'),('2025-03-01','2025-11-01'),
                          ('2024-03-01','2025-10-31'),('2025-10-31','2025-03-01'),('2025-03-01','2026-01-01')]:
            reviewed = self.blank_review(item);reviewed['data'].update(period_start=start,period_end=end)
            with self.subTest(start=start,end=end), self.assertRaises(ValueError):
                self.confirm(item,reviewed)
        reviewed = self.blank_review(item);reviewed['data'].update(period_start='2025-03-01',period_end='2025-10-31')
        self.assertIsNotNone(self.confirm(item,reviewed))

    def test_blank_outlook_content_uses_explicit_case_without_inventing_answers(self):
        item = self.stage(kind='outlook',year=2026)
        reviewed = self.blank_review(item)
        reviewed['data'] = {'document_kind':'outlook','pn':'111113'}
        self.assertIn(self.case,[row['case_id'] for row in matching_cases(self.db,reviewed['data'])])
        self.confirm(item,reviewed)
        saved = json.loads(self.db.execute('SELECT reviewed_json FROM word_pdf_imports WHERE id=?',(item,)).fetchone()[0])
        self.assertEqual(saved['data']['period_start'],'2026-01-01')
        self.assertEqual(saved['data']['period_end'],'2026-12-31')
        self.assertEqual(saved['data']['dialog_date'],'')
        self.assertEqual(saved['data']['conducted'],'')
        self.assertEqual(saved['filled_fields']['period_start']['origin'],'selected_case')

    def test_partial_goals_are_kept_and_empty_rows_ignored(self):
        item = self.stage(kind='outlook',year=2026)
        reviewed = self.reviewed(item)
        reviewed['performance_goals'] = [{'criteria':'Messung ohne Zieltext'},{}]
        reviewed['development_goals'] = [{'steps':'Schritt ohne Kompetenzzuordnung'},{}]
        self.confirm(item,reviewed)
        saved = json.loads(self.db.execute('SELECT goals_json FROM word_pdf_goal_versions').fetchone()[0])
        self.assertEqual(saved['performance_goals'],[{'criteria':'Messung ohne Zieltext'}])
        self.assertEqual(saved['development_goals'],[{'steps':'Schritt ohne Kompetenzzuordnung'}])

    def test_blank_probation_decision_and_period_are_optional(self):
        with self.db:
            self.db.execute("UPDATE dialog_events SET event_type='probation_review' WHERE legacy_case_id=?",(self.case,))
            self.db.execute("UPDATE dialog_cases SET period_start='2025-02-01',period_end='2025-04-30' WHERE case_id=?",(self.case,))
        item = self.stage();reviewed = self.blank_review(item)
        reviewed['data'].update(probation='ja',rating='',period_start='',period_end='',employment_continues='')
        self.confirm(item,reviewed)
        self.assertEqual(reviewed['data']['period_end'],'2025-04-30')
        self.assertEqual(reviewed['data']['employment_continues'],'')

    def test_explicit_nonconducted_needs_no_reason_and_no_invented_date(self):
        item = self.stage();reviewed = self.blank_review(item)
        reviewed['data'].update(conducted='nein',rating='',no_md_reason='')
        doc = self.confirm(item,reviewed)
        self.assertEqual(reviewed['data']['dialog_date'],'')
        self.assertNotIn('filled_fields',reviewed)
        self.assertEqual(self.db.execute('SELECT variant FROM official_documents WHERE id=?',(doc,)).fetchone()[0],'administrative')

    def test_existing_conversation_date_is_preserved(self):
        item = self.stage();reviewed = self.blank_review(item)
        reviewed['data']['dialog_date']='2026-01-15'
        self.confirm(item,reviewed)
        self.assertEqual(reviewed['data']['dialog_date'],'2026-01-15')
        self.assertNotIn('filled_fields',reviewed)

    def test_review_screen_keeps_optional_fields_optional(self):
        from html.parser import HTMLParser
        class Fields(HTMLParser):
            def __init__(self):super().__init__();self.fields={}
            def handle_starttag(self,tag,attrs):
                values=dict(attrs)
                if tag in ('input','select','textarea') and values.get('name'):
                    self.fields[values['name']]=values
        parser=Fields();parser.feed(self.app.test_client().get(f'/word-pdf-imports/{self.stage()}').text)
        for key in ('manager_pn','dialog_date','no_md_reason','reason','conducted','employment_continues'):
            self.assertNotIn('required',parser.fields[key])
            self.assertNotIn('minlength',parser.fields[key])
        for key in ('pn','period_start','period_end','checked'):
            self.assertIn('required',parser.fields[key])


class PeriodPolicyTest(unittest.TestCase):
    def test_leap_day_and_no_employment_in_year(self):
        validate_review_period('2024-02-29','2024-02-29',2024,'2024-02-29','2024-02-29')
        for args in [('2025-02-29','2025-12-31',2025),('2024-12-31','2025-01-01',2025),
                     ('2025-01-01','2025-12-31',2025,'2026-01-01','')]:
            with self.subTest(args=args),self.assertRaises(ValueError):validate_review_period(*args)


class WordSetupTest(unittest.TestCase):
    def test_relative_unicode_paths_bom_and_empty_optional_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);instance=root/'instance';instance.mkdir();(root/'templates').mkdir()
            paths={kind:'../templates/'+name for kind,name in
                   [('review','MD_Rückblick_2026.docx'),('outlook','MD_Ausblick_2026.docx'),('probation','MD_Rückblick_Probezeit_2026.docx')]}
            for path in paths.values():(instance/path).write_bytes(b'template')
            config=instance/'word_config.json'
            config.write_text(json.dumps({'templates':paths|{'feedback':'  '}},ensure_ascii=False),encoding='utf-8-sig')
            with patch.dict(os.environ,{'MD_WORD_CONFIG':''}):
                app=create_app({'TESTING':True,'AUTH_DISABLED':True,'SECRET_KEY':'test'},instance_path=str(instance))
            with app.app_context():
                status=word_template_status(app.config['WORD_TEMPLATE_PATHS'])
                self.assertTrue(status['ready']);self.assertTrue(status['config_loaded'])
                self.assertEqual(status['config_path'],str(config))
                self.assertTrue(all(Path(row['path']).is_absolute() for row in status['files']))
                self.assertNotIn('feedback',app.config['WORD_TEMPLATE_PATHS'])

    def test_malformed_json_shows_error_without_preventing_app_start(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config=root/'word_config.json'
            config.write_text('{"templates": {"review": "../templates/review.docx"}')
            with self.assertRaisesRegex(ValueError,'Zeile 1'):
                load_word_config(config)
            with patch.dict(os.environ,{'MD_WORD_CONFIG':str(config)}):
                app=create_app({'TESTING':True,'AUTH_DISABLED':True,'SECRET_KEY':'test'},instance_path=str(root))
            self.assertFalse(app.config['WORD_CONFIG_LOADED'])
            self.assertIn(str(config),app.config['WORD_CONFIG_ERROR'])
            response=app.test_client().get('/einrichtung')
            self.assertEqual(response.status_code,200)
            self.assertIn('ungültiges JSON',response.text)

    def test_missing_docx_and_accidental_txt_extension_are_explained(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);config=root/'word_config.json';Path(str(config)+'.txt').write_text('{}')
            with patch.dict(os.environ,{'MD_WORD_CONFIG':str(config)}):
                app=create_app({'TESTING':True,'AUTH_DISABLED':True,'SECRET_KEY':'test'},instance_path=str(root))
            with app.app_context():
                status=word_template_status({'review':str(root/'missing.docx')})
                self.assertFalse(status['ready']);self.assertTrue(status['txt_file'])
                self.assertFalse(status['files'][0]['exists'])
                self.assertEqual(status['files'][0]['path'],str(root/'missing.docx'))
