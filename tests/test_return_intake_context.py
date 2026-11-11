"""Identity suggestions preserve case obligations and show the actual handoff."""
import json
import re
import unittest
from pathlib import PurePosixPath
from zipfile import ZipFile

from tests import test_goal_workflow as workflow
from tests import test_word_pdf_imports as pdf_fixtures
from tests import test_return_review as return_fixtures
from tests.e2_pdf_factory import form_pdf
from webapp.services import word_pdf_imports as pdfs, return_review
from webapp.services.return_identity import filename_pn, supplement_identity
from webapp.services.word_pdf import parse_word_pdf_text


class ReturnIntakeContextTest(unittest.TestCase):
    setUp = workflow.GoalWorkflowTest.setUp
    tearDown = workflow.GoalWorkflowTest.tearDown

    def stage(self, filename='Rückblick_2025_Test_Person_111113.pdf', **kwargs):
        path=pdf_fixtures.sample_pdf(self.root/'incoming.pdf', **kwargs)
        return pdfs.stage_pdf(self.db,path,filename=filename,directory=self.root/'incoming')[0]

    def test_unique_person_and_case_are_preselected_without_scope_question(self):
        incoming=self.stage()
        page=self.client.get(f'/word-pdf-imports/{incoming}')
        self.assertEqual(page.status_code,200)
        self.assertRegex(page.text,rf'<option value="{re.escape(self.case_id)}"[^>]*selected')
        self.assertNotIn('name="scope"',page.text)
        self.assertIn('MD-Umfang wird aus dem gewählten Fall übernommen',page.text)

    def test_missing_pn_uses_standard_filename_with_visible_origin(self):
        incoming=self.stage(person_pn='')
        parsed=json.loads(self.db.execute('SELECT parsed_json FROM word_pdf_imports WHERE id=?',(incoming,)).fetchone()[0])
        self.assertEqual(parsed['data']['pn'],'111113')
        self.assertEqual(parsed['identity_hints']['pn']['origin'],'filename')
        page=self.client.get(f'/word-pdf-imports/{incoming}')
        self.assertIn('aus dem Dateinamen ergänzt',page.text)
        self.assertRegex(page.text,rf'<option value="{re.escape(self.case_id)}"[^>]*selected')

    def test_conflicting_filename_does_not_preselect_case_or_automate(self):
        self.app.config['HR_RETURN_AUTOMATION']=True
        path=form_pdf(self.root/'validated.pdf')
        incoming=pdfs.stage_pdf(self.db,path,filename='Rückblick_2025_Andere_Person_111112.pdf',directory=self.root/'incoming',auto_handoff_dir=self.root/'handoff')[0]
        row=self.db.execute('SELECT * FROM word_pdf_imports WHERE id=?',(incoming,)).fetchone()
        self.assertEqual(row['status'],'pending')
        parsed=json.loads(row['parsed_json'])
        self.assertTrue(parsed['identity_conflicts'])
        self.assertEqual(parsed['automation']['state'],'needs_review')
        page=self.client.get(f'/word-pdf-imports/{incoming}')
        self.assertNotRegex(page.text,rf'<option value="{re.escape(self.case_id)}"[^>]*selected')
        self.assertIn('widersprüchliche Personalnummern',page.text)

    def test_multiple_employments_are_not_guessed(self):
        with self.db:
            self.db.execute("INSERT INTO employment_assignments(person_number,assignment_number,last_import_id,updated_at) SELECT person_number,'2',last_import_id,updated_at FROM employment_assignments WHERE person_number='111113' AND assignment_number='1'")
        page=self.client.get(f'/word-pdf-imports/{self.stage()}')
        self.assertNotRegex(page.text,rf'<option value="{re.escape(self.case_id)}"[^>]*selected')
        self.assertIn('Person oder Anstellung ist noch nicht eindeutig',page.text)

    def test_existing_scope_is_used_when_not_submitted(self):
        incoming=self.stage()
        reviewed=pdf_fixtures.WordPdfImportsTest.reviewed(self,incoming)
        reviewed.pop('scope')
        document=pdfs.confirm_import(self.db,incoming,reviewed=reviewed,assignment='1',case_id=self.case_id,historical=False,reason='')
        self.assertIsNotNone(document)
        self.assertEqual(reviewed['scope'],'full')
        self.assertEqual(self.db.execute('SELECT official_scope FROM dialog_cases WHERE case_id=?',(self.case_id,)).fetchone()[0],'full')

    def test_return_cannot_reduce_existing_scope(self):
        incoming=self.stage()
        reviewed=pdf_fixtures.WordPdfImportsTest.reviewed(self,incoming)
        reviewed['scope']='review_only'
        with self.assertRaisesRegex(ValueError,'MD-Umfang'):
            pdfs.confirm_import(self.db,incoming,reviewed=reviewed,assignment='1',case_id=self.case_id,historical=False,reason='')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],0)

    def test_http_confirmation_needs_no_scope_input(self):
        incoming=self.stage()
        employment=self.db.execute("SELECT id FROM employment_assignments WHERE person_number='111113' AND assignment_number='1'").fetchone()[0]
        response=self.client.post(f'/word-pdf-imports/{incoming}',data={
            'csrf_token':self.csrf,'revision':'0','checked':'yes','action':'confirm',
            'document_kind':'review','employment_id':str(employment),'case_id':self.case_id,
            'period_start':'2025-01-01','period_end':'2025-12-31','rating':'C','probation':'nein'},follow_redirects=True)
        self.assertEqual(response.status_code,200)
        self.assertIn('Stand dieser Fassung',response.text)
        self.assertIn(str(self.app.config['DOSSIER_HANDOFF_ROOT']),response.text)
        self.assertEqual(self.db.execute('SELECT status FROM word_pdf_imports WHERE id=?',(incoming,)).fetchone()[0],'imported')

    def test_mail_handoff_links_back_to_open_mail_without_moving_it(self):
        from datetime import datetime, timezone
        from webapp.adapters.outlook import InboundMessage, InboundAttachment
        from webapp.services.mail_intake import process_inbound_messages
        path=pdf_fixtures.sample_pdf(self.root/'mail.pdf')
        message=InboundMessage('synthetic-entry','<synthetic-mail>','test@example.invalid','MD Rückblick zur Prüfung',datetime.now(timezone.utc),
                               (InboundAttachment(1,'Rückblick_2025_Test_Person_111113.pdf',path.read_bytes()),))
        moves=[]
        process_inbound_messages(self.db,messages=[message],inbox_dir=self.root/'mail',pdf_dir=self.root/'processed',
                                 handoff_dir=self.root/'handoff',target_folder='MD',move_message=lambda *args:moves.append(args))
        incoming=self.db.execute('SELECT id FROM word_pdf_imports').fetchone()[0]
        reviewed=pdf_fixtures.WordPdfImportsTest.reviewed(self,incoming)
        document=pdfs.confirm_import(self.db,incoming,reviewed=reviewed,assignment='1',case_id=self.case_id,historical=False,reason='')
        state=return_review.view(self.db,document)
        return_review.handoff(self.db,document,directory=self.root/'handoff',revision=state['revision'],token=state['token'])
        page=self.client.get(f'/arbeit/ruecklaeufe/{document}')
        self.assertEqual(page.status_code,200)
        self.assertIn('MD Rückblick zur Prüfung',page.text)
        self.assertIn('Mailprüfung noch offen',page.text)
        self.assertIn('Zur E-Mail-Prüfung',page.text)
        self.assertFalse(moves)

    def test_handoff_shows_saved_destination_after_configuration_changes(self):
        document,_=return_fixtures.ReturnReviewTest.imported(self,rating='C')
        state=return_review.view(self.db,document)
        old=self.root/'first-target'
        return_review.handoff(self.db,document,directory=old,revision=state['revision'],token=state['token'])
        self.app.config['DOSSIER_HANDOFF_ROOT']=str(self.root/'new-target')
        page=self.client.get(f'/arbeit/ruecklaeufe/{document}')
        self.assertEqual(page.status_code,200)
        self.assertIn(str(old),page.text)
        self.assertIn('Übergabeordner wurde inzwischen geändert',page.text)
        self.assertFalse((self.root/'new-target').exists())

    def test_new_goal_review_uses_standard_filename_ending_in_pn(self):
        source=workflow.GoalWorkflowTest.stage(self)
        revision=workflow.GoalWorkflowTest.confirm(self,source)
        output=workflow.GoalWorkflowTest.generate(self,revision)
        row=self.db.execute('SELECT * FROM hr_goal_outputs WHERE id=?',(output['output_id'],)).fetchone()
        document=json.loads(row['manifest_json'])['documents'][0]
        name=PurePosixPath(document['filename']).name
        self.assertTrue(name.startswith('Rückblick_2025_'))
        self.assertTrue(name.endswith('_111113.docx'))
        self.assertNotIn('_Ans_',name)
        with ZipFile(row['stored_path']) as archive:
            self.assertIn(document['filename'],archive.namelist())


class ReturnIdentityTest(unittest.TestCase):
    def test_filename_patterns_keep_person_and_feedback_manager_separate(self):
        self.assertEqual(filename_pn('Rückblick_2025_Test_Person_000123.pdf'),'000123')
        self.assertEqual(filename_pn('Rückblick_2025_Test_Person_000123_Ans_2_abcdef12.pdf'),'000123')
        self.assertEqual(filename_pn('Rückblick_2025_Test_Person_000123_Ans_2_12345678.pdf'),'000123')
        self.assertEqual(filename_pn('NameMA_Feedback_an_Test_Person_000456.pdf',feedback=True),'000456')
        self.assertEqual(filename_pn('NameMA_Feedback_an_Test_Person_000456.pdf'),'')
        self.assertEqual(filename_pn('Andere_Datei_2025.pdf'),'')

    def test_full_personal_number_labels_are_read_from_document(self):
        parsed=parse_word_pdf_text('Mitarbeitenden-Dialog (MD) - Rückblick Personalnummer: 000123 Personalnummer Vorgesetzte/r: 000456')
        self.assertEqual(parsed['data']['pn'],'000123')
        self.assertEqual(parsed['data']['manager_pn'],'000456')

    def test_multiple_printed_numbers_are_never_replaced_by_filename(self):
        parsed={'data':{'document_kind':'review','pn':''},'text':'PN: 000123 PN: 000124','issues':[]}
        supplement_identity(parsed,'Rückblick_2025_Test_Person_000123.pdf')
        self.assertEqual(parsed['data']['pn'],'')
