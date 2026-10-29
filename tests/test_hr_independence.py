"""Regression der HR-Ausnahmefälle ohne echtes Outlook oder produktive Daten."""
import io
import json
import re
import unittest
from unittest.mock import patch
from datetime import date

from tests import test_word_pdf_imports as pdf_fixtures
from webapp.services import hr_workflow as workflow
from webapp.services.cycles import change_cycle_status
from webapp.services.reminders import reminder_candidates
from webapp.services.word_packages import prior_goals
from webapp.services.outlook_lock import package_lock


class HRIndependenceTest(unittest.TestCase):
    setUp = pdf_fixtures.WordPdfImportsTest.setUp
    tearDown = pdf_fixtures.WordPdfImportsTest.tearDown
    stage = pdf_fixtures.WordPdfImportsTest.stage
    reviewed = pdf_fixtures.WordPdfImportsTest.reviewed
    confirm = pdf_fixtures.WordPdfImportsTest.confirm

    def test_new_guidance_pages_and_document_whitelist(self):
        client = self.app.test_client()
        for page in ['/aufgaben', '/einrichtung', '/hilfe', '/zielquellen', '/alte-ziele',
                     f'/cycles/{self.cycle}/abschluss', f'/dialoge?unassigned=yes&cycle_id={self.cycle}']:
            self.assertEqual(client.get(page).status_code, 200, page)
        for name in ['BUEROTEST.md', 'PLAN_B_WORD_PDF.md', 'BETRIEBSKONZEPT.md', 'FLASK_SQLITE_MVP.md', 'ANFORDERUNGEN.md']:
            with client.get('/hilfe/dokument/' + name) as response:
                self.assertEqual(response.status_code, 200, name)
        self.assertEqual(client.get('/hilfe/dokument/organisation.json').status_code, 404)

    def test_draft_conflict_dismiss_reopen_and_no_official_write(self):
        item = self.stage()
        client = self.app.test_client()
        url = f'/word-pdf-imports/{item}'
        form = {'action': 'draft', 'revision': '0', 'pn': '111113', 'document_kind': 'review',
                'assignment': '1', 'case_id': self.case, 'destination': 'case',
                'reason': 'Prüfung mit HR abstimmen', 'conducted': 'ja'}
        response = client.post(url, data=form, follow_redirects=True)
        self.assertIn('Prüfentwurf gespeichert', response.text)
        self.assertEqual(workflow.pdf_state(self.db, item)['revision'], 1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0], 0)
        self.assertIn('inzwischen geändert', client.post(url, data=form).text)
        self.assertEqual(workflow.pdf_state(self.db, item)['revision'], 1)
        form.update(action='dismiss', revision='1')
        self.assertIn('Prüfung zurückgestellt', client.post(url, data=form, follow_redirects=True).text)
        self.assertEqual(len(workflow.pending_pdfs(self.db)), 0)
        self.assertEqual(workflow.pdf_queue(self.db, status='dismissed')['pdf_total'], 1)
        with self.assertRaisesRegex(ValueError, 'zurückgestellt'):
            self.confirm(item)
        form.update(action='reopen', revision='2')
        self.assertIn('wieder geöffnet', client.post(url, data=form, follow_redirects=True).text)
        self.assertEqual(len(workflow.pending_pdfs(self.db)), 1)

    def test_queue_accessible_beyond_one_hundred(self):
        self.stage()
        row = dict(self.db.execute('SELECT * FROM word_pdf_imports').fetchone())
        cols = [key for key in row if key != 'id']
        for i in range(101):
            values = row | {'sha256': f'{i:064x}', 'original_filename': f'R-{i}.pdf'}
            self.db.execute(f"INSERT INTO word_pdf_imports ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})", [values[key] for key in cols])
        self.db.commit()
        result = workflow.pdf_queue(self.db, page=5)
        self.assertEqual(result['pdf_total'], 102)
        self.assertEqual(len(result['word_pdf_queue']), 2)
        self.assertEqual(workflow.pdf_queue(self.db, query='R-100.pdf')['pdf_total'], 1)

    def test_received_documents_never_generate_missing_document_reminders(self):
        self.db.execute("UPDATE document_obligations SET due_date='2020-01-01',status='received'")
        self.db.commit()
        self.assertEqual(reminder_candidates(self.db, cycle_id=self.cycle, today=date(2026, 1, 1)), [])
        self.db.execute("UPDATE document_obligations SET status='open'")
        self.db.commit()
        self.stage()
        candidates = reminder_candidates(self.db, cycle_id=self.cycle, today=date(2026, 1, 1))
        self.assertTrue(candidates)
        self.assertTrue(all(not row['ready'] for row in candidates))

    def test_tasks_follow_pending_pdf_then_handoff(self):
        item = self.stage()
        client = self.app.test_client()
        self.assertIn(f'/word-pdf-imports/{item}', client.get('/aufgaben').text)
        self.confirm(item)
        self.assertIn('Dossierübergabe', client.get('/aufgaben').text)

    def test_inactive_late_return_allows_empty_reason_but_closed_cycle_requires_reopening(self):
        from webapp.services.word_pdf_imports import confirm_import, matching_cases
        item = self.stage()
        self.db.execute('UPDATE dialog_cases SET active=0 WHERE case_id=?', (self.case,))
        self.db.commit()
        self.assertTrue(matching_cases(self.db, self.reviewed(item)['data']))
        self.db.execute("UPDATE cycles SET status='abgeschlossen' WHERE id=?", (self.cycle,))
        self.db.commit()
        with self.assertRaisesRegex(ValueError, 'abgeschlossen'):
            confirm_import(self.db, item, reviewed=self.reviewed(item), assignment='1', case_id=self.case, historical=False, reason='')
        self.db.execute("UPDATE cycles SET status='ruecklauf' WHERE id=?", (self.cycle,))
        self.db.commit()
        confirm_import(self.db, item, reviewed=self.reviewed(item), assignment='1', case_id=self.case, historical=False, reason='')
        self.assertEqual(self.db.execute('SELECT active FROM dialog_cases WHERE case_id=?', (self.case,)).fetchone()[0], 0)

    def test_closure_requires_external_check_and_owned_remainder(self):
        self.db.execute("UPDATE cycles SET status='ruecklauf' WHERE id=?", (self.cycle,))
        self.db.commit()
        with self.assertRaisesRegex(ValueError, 'Abschlussprüfung'):
            change_cycle_status(self.db, cycle_id=self.cycle, new_status='abgeschlossen')
        with self.assertRaisesRegex(ValueError, 'offene Aufgaben'):
            change_cycle_status(self.db, cycle_id=self.cycle, new_status='abgeschlossen', external_checked=True)
        change_cycle_status(self.db, cycle_id=self.cycle, new_status='abgeschlossen', external_checked=True, closure_reason='Restfälle nach Ferien prüfen', closure_owner='HR Vertretung')
        record = self.db.execute('SELECT * FROM workflow_cycle_closures').fetchone()
        self.assertEqual(record['owner'], 'HR Vertretung')
        self.assertTrue(any(json.loads(record['summary_json']).values()))
        change_cycle_status(self.db, cycle_id=self.cycle, new_status='ruecklauf')

    def test_source_choice_invalidated_when_source_changes(self):
        payload = {'outlook': {'performance_goals': [{'title': 'Ziel A', 'criteria': '', 'steps': '', 'target_date': ''}], 'development_goals': []}}
        self.db.execute('UPDATE dialog_cases SET data_json=? WHERE case_id=?', (json.dumps(payload), self.case))
        self.db.commit()
        client = self.app.test_client()
        page = client.get('/zielquellen?pn=111113&assignment=1&year=2026')
        fingerprint = re.search('name="fingerprint" value="([a-f0-9]+)"', page.text)[1]
        result = client.post('/zielquellen', data={'pn': '111113', 'assignment': '1', 'year': '2026', 'source': '0', 'reason': 'Mit unterschriebenem Original verglichen', 'fingerprint': fingerprint})
        self.assertIn('Zielquelle festgelegt', result.text)
        self.assertEqual(prior_goals(self.db, employee_pn='111113', assignment='1', year=2026)[0][0]['title'], 'Ziel A')
        payload['outlook']['performance_goals'][0]['title'] = 'Ziel B'
        self.db.execute('UPDATE dialog_cases SET data_json=? WHERE case_id=?', (json.dumps(payload), self.case))
        self.db.commit()
        with self.assertRaisesRegex(ValueError, 'geändert'):
            prior_goals(self.db, employee_pn='111113', assignment='1', year=2026)

    def test_unreadable_docx_gets_actionable_preview(self):
        client = self.app.test_client()
        response = client.post('/alte-ziele', data={'goal_year': '2025', 'forms': (io.BytesIO(b'broken'), 'Ausblick.docx')}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Datei nicht lesbar', response.text)

    def test_orphan_event_attach_and_cancel_without_duplicate_obligations(self):
        from webapp.services.dialog_events import create_manual_event
        event = create_manual_event(self.db, employee_pn='111113', assignment_number='1',
            manager_pn='111116', event_type='interim', required_scope='outlook_only',
            review_year=2025, period_start='2025-01-01', period_end='2025-12-31',
            reason='Unterjähriger Dialog für Test')
        row = self.db.execute('SELECT id FROM dialog_events WHERE event_id=?', (event,)).fetchone()
        event_id = row[0]
        client = self.app.test_client()
        self.assertIn(f'/dialog-events/{event_id}/attach', client.get(f'/dialoge?unassigned=yes&cycle_id={self.cycle}').text)
        with self.assertRaisesRegex(ValueError, 'bereits ein Fall'):
            workflow.attach_event(self.db, event_id, self.cycle, 'Zuordnung geprüft und bestätigt')
        self.db.execute("UPDATE dialog_cases SET manager_pn='anderer-test-vg' WHERE case_id=?", (self.case,))
        self.db.commit()
        count = self.db.execute('SELECT COUNT(*) FROM document_obligations').fetchone()[0]
        case = workflow.attach_event(self.db, event_id, self.cycle, 'Zuordnung geprüft und bestätigt')
        self.assertEqual(case, event)
        self.assertEqual(count, self.db.execute('SELECT COUNT(*) FROM document_obligations').fetchone()[0])
        workflow.cancel_manual_event(self.db, event_id, 'Fehlanlage nach Prüfung aufheben')
        self.assertEqual(self.db.execute('SELECT active FROM dialog_cases WHERE case_id=?', (case,)).fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT status FROM document_obligations WHERE dialog_event_id=?', (event_id,)).fetchone()[0], 'waived')

    def test_competing_historical_sources_can_be_resolved_without_deletion(self):
        from tests.test_word_packages import WordPackagesTest
        WordPackagesTest.add_goals(self, title='Quelle A', source_hash='a')
        WordPackagesTest.add_goals(self, title='Quelle B', source_hash='b')
        with self.assertRaisesRegex(ValueError, 'mehrere Zielquellen'):
            prior_goals(self.db, employee_pn='111113', assignment='1', year=2025)
        client = self.app.test_client()
        page = client.get('/zielquellen?pn=111113&assignment=1&year=2025')
        fingerprint = re.search('name="fingerprint" value="([a-f0-9]+)"', page.text)[1]
        client.post('/zielquellen', data={'pn': '111113', 'assignment': '1', 'year': '2025', 'source': '1', 'reason': 'Zweite Quelle mit Original bestätigt', 'fingerprint': fingerprint})
        self.assertEqual(prior_goals(self.db, employee_pn='111113', assignment='1', year=2025)[0][0]['title'], 'Quelle B')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM historical_goals').fetchone()[0], 2)

    def test_active_outlook_lock_cannot_be_recovered(self):
        path = self.root / 'package.zip'
        with package_lock(path):
            with self.assertRaisesRegex(ValueError, 'läuft noch'):
                with package_lock(path):
                    self.fail('Parallelzugriff darf nicht möglich sein')
        with package_lock(path):
            pass

    def test_storage_failure_has_recovery_guidance(self):
        with patch('webapp.routes.workflow.setup_checks', side_effect=PermissionError('test')):
            response = self.app.test_client().get('/einrichtung')
        self.assertEqual(response.status_code, 503)
        self.assertIn('Systemadministration', response.text)


if __name__ == '__main__':
    unittest.main()
