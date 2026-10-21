import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from tests import test_word_packages as fixtures
from tests.test_goal_import import word
from tests.test_word_dispatch import FakeOutlook
from webapp.adapters.outlook import InboundAttachment, InboundMessage
from webapp.services.mail_intake import process_inbound_messages, mail_inbox_overview
from webapp.services.word_packages import prior_goals
from webapp.services.word_dispatch import prepare_word_batch, dispatch_word_packages, word_dispatch_candidates


class MailGoalsTest(unittest.TestCase):
    setUp = fixtures.WordPackagesTest.setUp
    tearDown = fixtures.WordPackagesTest.tearDown

    def scan(self, *paths):
        message = InboundMessage('goals-mail', '<goals-mail>', 'test@example.invalid', 'Ausblicke', datetime.now(timezone.utc), tuple(InboundAttachment(i, path.name, path.read_bytes()) for i, path in enumerate(paths, 1)))
        self.moves = []
        return process_inbound_messages(self.db, messages=[message], inbox_dir=self.root/'inbox', pdf_dir=self.root/'pdf', handoff_dir=self.root/'robot', target_folder='12 Mitarbeitenden-Dialog', move_message=lambda entry, folder: self.moves.append((entry, folder)) or 'moved-id')

    def test_import_moves_and_flags_sent_person_without_sending(self):
        prepare_word_batch(self.db, cycle_id=self.cycle_id, manager_pns=['111116'], template_paths=self.paths, output_dir=self.root/'dispatch')
        package = word_dispatch_candidates(self.db, cycle_id=self.cycle_id, template_paths=self.paths)[0]
        dispatch_word_packages(self.db, cycle_id=self.cycle_id, package_ids=[package['id']], template_paths=self.paths, sender_email='test@example.invalid', adapter=FakeOutlook(), delivery_mode='send')
        path = word(self.root/'Ausblick.docx')
        result = self.scan(path)
        self.assertEqual(result['moved'], 1)
        self.assertEqual(len(self.moves), 1)
        self.assertEqual(len(prior_goals(self.db, employee_pn='111113', assignment='1', year=2025)[0]), 1)
        self.assertFalse(list((self.root/'robot').iterdir()))
        changed = word_dispatch_candidates(self.db, cycle_id=self.cycle_id, template_paths=self.paths)[0]
        self.assertTrue(any('Vorjahresziele' in change['details'] for change in changed['source_changes']))
        self.assertEqual(changed['delivery_status'], 'sent_confirmed')
        attachment = mail_inbox_overview(self.db)['mail_messages'][0]['attachments'][0]
        self.assertIn('Ziele 2025', attachment['progress'])
        self.assertIn('Versand', attachment['next_step'])
        self.assertTrue(any(case['case_id']==self.case_id for case in attachment['goal_cases']))
        self.assertEqual(self.app.test_client().get('/ruecklaeufe').status_code,200)
        self.scan(path)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM legacy_form_imports').fetchone()[0], 1)

    def test_old_pending_word_is_reprocessed_on_next_scan(self):
        path = word(self.root/'Ausblick.docx')
        with patch('webapp.services.mail_goals.process_word_goals'):
            self.scan(path)
        self.db.execute("UPDATE inbound_mail_attachments SET file_kind='other'")
        self.db.commit()
        self.assertEqual(self.scan(path)['moved'], 1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM inbound_mail_attachments').fetchone()[0], 1)

    def test_competing_sources_stay_pending_without_partial_import(self):
        a = word(self.root/'Ausblick1.docx', title='Ziel A')
        b = word(self.root/'Ausblick2.docx', title='Ziel B')
        self.assertEqual(self.scan(a,b)['moved'], 0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM legacy_form_imports').fetchone()[0], 0)
        self.assertIn('Mehrere unterschiedliche Ausblicke', mail_inbox_overview(self.db)['mail_messages'][0]['attachments'][0]['progress'])

    def test_mixed_mail_imports_goals_but_stays_pending(self):
        a = word(self.root/'Ausblick.docx')
        b = self.root/'Anderes.txt'; b.write_text('other')
        self.assertEqual(self.scan(a,b)['moved'], 0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM legacy_form_imports').fetchone()[0], 1)
        self.assertFalse(self.moves)

    def test_ambiguous_assignment_is_not_guessed(self):
        path = word(self.root/'Ausblick.docx')
        with patch('webapp.services.mail_goals._match_assignment', return_value=('ambiguous_assignment','')):
            self.assertEqual(self.scan(path)['moved'], 0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM legacy_form_imports').fetchone()[0], 0)
        self.assertIn('Mehrfachanstellung', mail_inbox_overview(self.db)['mail_messages'][0]['attachments'][0]['progress'])

    def test_missing_year_stays_pending(self):
        path = word(self.root/'Ausblick.docx')
        from webapp.services.legacy_forms import parse_legacy_form
        parsed = parse_legacy_form(path)
        parsed['detected_years'] = []
        with patch('webapp.services.mail_goals.parse_legacy_form', return_value=parsed):
            self.assertEqual(self.scan(path)['moved'], 0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM legacy_form_imports').fetchone()[0], 0)
        self.assertIn('Zieljahr', mail_inbox_overview(self.db)['mail_messages'][0]['attachments'][0]['progress'])

    def test_existing_different_goals_are_not_overwritten(self):
        from webapp.services.legacy_forms import import_legacy_forms
        folder = self.root/'earlier'; folder.mkdir()
        word(folder/'Ausblick.docx', title='Bisheriges Ziel')
        import_legacy_forms(self.db, forms_root=folder, goal_year=2025)
        path = word(self.root/'Ausblick.docx', title='Anderes Ziel')
        self.assertEqual(self.scan(path)['moved'], 0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM legacy_form_imports').fetchone()[0], 1)
        self.assertIn('Abweichende Zielquelle', mail_inbox_overview(self.db)['mail_messages'][0]['attachments'][0]['progress'])

    def test_partial_import_preserves_warning_and_does_not_duplicate_on_rescan(self):
        from zipfile import ZipFile
        path = word(self.root/'Ausblick.docx')
        with ZipFile(path) as archive:
            xml = archive.read('word/document.xml').decode()
        broken = '<w:tr><w:tc><w:p><w:r><w:t>Zusatz mit unklaren Spalten</w:t></w:r></w:p></w:tc></w:tr>'
        xml = xml.replace('</w:tbl>', broken + '</w:tbl>', 1)
        with ZipFile(path, 'w') as archive:
            archive.writestr('word/document.xml', xml)
        for _ in range(2):
            self.assertEqual(self.scan(path)['moved'], 0)
            self.assertEqual(self.db.execute('SELECT COUNT(*) FROM historical_goals').fetchone()[0], 2)
            attachment = mail_inbox_overview(self.db)['mail_messages'][0]['attachments'][0]
            self.assertIn('Teilweise übernommen:', attachment['progress'])
            self.assertIn('Tabelle 1, Zeile 3', attachment['progress'])
            self.assertIn('Zusatz mit unklaren Spalten', attachment['progress'])
            self.assertNotIn('noch nicht übernommen', attachment['progress'])
            self.assertIn('Lesbare Ziele stehen bereits', attachment['next_step'])
        # A user can finish the remaining review without reimporting or moving mail.
        from webapp.services.mail_intake import resolve_inbound_message
        message = self.db.execute('SELECT id FROM inbound_mail_messages').fetchone()
        resolve_inbound_message(self.db, message_id=message['id'], mailbox_name='Test', target_folder='MD', review_note='Zusatz geprüft und im Rückblick ergänzt.')
        self.scan(path)
        self.assertFalse(self.moves)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM historical_goals').fetchone()[0], 2)

    def test_empty_optional_fields_do_not_block_import(self):
        from zipfile import ZipFile
        path = word(self.root/'Ausblick.docx')
        with ZipFile(path) as archive:
            xml = archive.read('word/document.xml').decode()
        xml = xml.replace('Qualität bestätigt', '').replace('Erheben und umsetzen', '').replace('31.12.2025', '')
        with ZipFile(path, 'w') as archive:
            archive.writestr('word/document.xml', xml)
        self.assertEqual(self.scan(path)['moved'], 1)
        goals = prior_goals(self.db, employee_pn='111113', assignment='1', year=2025)
        self.assertEqual(goals[0][0]['title'], 'Projekt abschliessen')
        self.assertEqual(goals[0][0]['criteria'], '')
