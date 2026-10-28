import io
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from tests import test_goal_workflow as workflow_fixtures
from tests.e2_pdf_factory import form_pdf
from webapp.services.word_pdf import inspect_word_pdf
from webapp.services.word_pdf_imports import stage_pdf
from webapp.services import return_review, return_automation
from webapp.services.mail_intake import process_inbound_messages
from webapp.adapters.outlook import InboundAttachment, InboundMessage


class ReturnAutomationTest(unittest.TestCase):
    tearDown=workflow_fixtures.GoalWorkflowTest.tearDown

    def setUp(self):
        workflow_fixtures.GoalWorkflowTest.setUp(self)
        self.app.config['HR_RETURN_AUTOMATION']=True

    def stage(self, **kwargs):
        path=form_pdf(self.root/'synthetic.pdf',**kwargs)
        return stage_pdf(self.db,path,filename='neutral.pdf',directory=self.root/'incoming',auto_handoff_dir=self.root/'handoff')[0]

    def item(self,i):
        return self.db.execute('SELECT * FROM word_pdf_imports WHERE id=?',(i,)).fetchone()

    def test_validated_review_is_imported_and_delivered_once_without_claiming_hr_check(self):
        i=self.stage(); item=self.item(i)
        self.assertEqual(item['status'],'imported',item['parsed_json'])
        state=return_review.view(self.db,item['official_document_id'])
        self.assertTrue(state['complete']);self.assertEqual(state['validation_origin'],'automatic')
        self.assertIsNone(state['validated_by']);self.assertFalse(state['signature_checked'])
        self.assertEqual(state['overall_rating_code'] if 'overall_rating_code' in state else json.loads(state['data_block_json'])['rating'],'C')
        self.assertEqual(sum(e['action']=='data_automated' for e in state['history']),1)
        target=Path(state['handoff']['destination']);target.unlink()
        self.assertEqual(self.stage(),i);self.assertFalse(target.exists())
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],1)

    def test_negative_review_and_outlook_wait_for_two_separate_signature_checks(self):
        for kind in ('review','outlook'):
            i=self.stage(kind=kind,rating='Genügend')
            self.assertEqual(self.item(i)['status'],'imported',self.item(i)['parsed_json'])
            state=return_review.view(self.db,self.item(i)['official_document_id'])
            self.assertTrue(state['required']);self.assertFalse(state['complete'])
            self.assertEqual(state['signature_state'],'missing_scan')
        self.assertFalse(list((self.root/'handoff').glob('*.pdf')))

    def test_ambiguous_assignment_wrong_manager_and_period_remain_pending(self):
        for values in ({'manager':'999999'},{'year':2024},{'no_reason':'Gleichzeitig Nein begründet'}):
            with self.subTest(values=values):self.assertEqual(self.item(self.stage(**values))['status'],'pending')
        with self.db:
            self.db.execute("INSERT INTO employment_assignments(person_number,assignment_number,last_import_id,updated_at) SELECT person_number,'2',last_import_id,updated_at FROM employment_assignments WHERE person_number='111113' AND assignment_number='1'")
        self.assertEqual(self.item(self.stage())['status'],'pending')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],0)

    def test_another_version_never_replaces_existing_or_delivers_twice(self):
        first=self.stage();second=self.stage(marker='Korrigierter Inhalt')
        self.assertNotEqual(first,second);self.assertEqual(self.item(second)['status'],'pending')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],1)

    def test_delivery_error_keeps_committed_data_and_does_not_retry_on_upload(self):
        with patch('webapp.services.dossier_files.publish_copy',side_effect=OSError('Test: Ablage nicht verfügbar')):
            i=self.stage()
        item=self.item(i);self.assertEqual(item['status'],'imported')
        state=return_review.view(self.db,item['official_document_id'])
        self.assertEqual(state['handoff']['status'],'uncertain')
        self.assertEqual(json.loads(item['parsed_json'])['automation']['state'],'handoff_pending')
        self.assertEqual(self.stage(),i)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM hr_return_handoffs').fetchone()[0],1)

    def test_automation_off_and_started_draft_are_preserved(self):
        self.app.config['HR_RETURN_AUTOMATION']=False
        i=self.stage();self.assertEqual(self.item(i)['status'],'pending')
        with self.db:self.db.execute('UPDATE word_pdf_imports SET reviewed_json=? WHERE id=?',('{"note":"HR-Entwurf"}',i))
        self.app.config['HR_RETURN_AUTOMATION']=True
        result=return_automation.process_new(self.db,i,handoff_dir=self.root/'handoff')
        self.assertEqual(result['state'],'unchanged')
        self.assertEqual(self.item(i)['reviewed_json'],'{"note":"HR-Entwurf"}')

    def test_http_upload_uses_same_pipeline_and_shows_automatic_origin(self):
        path=form_pdf(self.root/'upload.pdf')
        response=self.client.post('/word-pdf-imports',data={'csrf_token':self.csrf,'word_pdf_files':(io.BytesIO(path.read_bytes()),'upload.pdf')})
        self.assertEqual(response.status_code,302)
        item=self.db.execute('SELECT * FROM word_pdf_imports').fetchone()
        self.assertEqual(item['status'],'imported',item['parsed_json'])
        page=self.client.get('/arbeit/ruecklaeufe/'+str(item['official_document_id']))
        self.assertIn('automatisch anhand'.encode(),page.data)

    def test_mail_attachment_auto_import_never_implies_email_body_was_checked(self):
        path=form_pdf(self.root/'mail.pdf')
        message=InboundMessage('e2','<e2@example.invalid>','test@example.invalid','MD',datetime.now(timezone.utc),(InboundAttachment(1,'neutral.pdf',path.read_bytes()),))
        moved=[]
        process_inbound_messages(self.db,messages=[message],inbox_dir=self.root/'inbox',pdf_dir=self.root/'pdfs',handoff_dir=self.root/'handoff',target_folder='MD',move_message=lambda *args:moved.append(args))
        item=self.db.execute('SELECT * FROM word_pdf_imports').fetchone()
        self.assertEqual(item['status'],'imported',item['parsed_json']);self.assertFalse(moved)


class ValidatedFormTest(unittest.TestCase):
    def test_page_image_with_ocr_reading_order_cannot_suggest_wrong_manager(self):
        import tempfile
        from PIL import Image
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'scan.pdf';c=canvas.Canvas(str(path),pagesize=(595,842))
            c.drawImage(ImageReader(Image.new('RGB',(50,50),'white')),0,0,595,842)
            for i,text in enumerate(['Mitarbeitenden-Dialog (MD) - Ausblick','PN: OE: PN VG: 1345',
                                     '696731','Ausblick auf: 01.01.2026 bis 31.12.2026','Gespräch vom: 01.01.2026']):
                c.drawString(40,800-i*20,text)
            c.save();result=inspect_word_pdf(path)
            self.assertEqual(result['source_role'],'scan')
            self.assertNotIn('manager_pn',result['data']);self.assertNotIn('pn',result['data'])
            self.assertFalse(result['validation']['eligible'])

    def test_all_three_structural_profiles_and_rating_values(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            for values in ({'kind':'review'},{'kind':'outlook'},{'probation':True}):
                with self.subTest(values=values):
                    result=inspect_word_pdf(form_pdf(Path(directory)/'test.pdf',**values))
                    self.assertTrue(result['validation']['eligible'],result['validation'])
            for text,code in [('Vorzüglich','A'),('Sehr gut','B'),('Gut','C'),('Genügend','D'),('Ungenügend','E')]:
                result=inspect_word_pdf(form_pdf(Path(directory)/'test.pdf',rating=text))
                self.assertEqual(result['data']['rating'],code)

    def test_missing_page_or_unknown_rating_cannot_auto_import(self):
        import tempfile
        from pypdf import PdfReader,PdfWriter
        with tempfile.TemporaryDirectory() as directory:
            path=form_pdf(Path(directory)/'test.pdf',rating='Unbekannt')
            self.assertFalse(inspect_word_pdf(path)['validation']['eligible'])
            path=form_pdf(path)
            reader=PdfReader(path);writer=PdfWriter()
            for i,page in enumerate(reader.pages):
                if i!=2:writer.add_page(page)
            incomplete=Path(directory)/'incomplete.pdf';writer.write(incomplete)
            self.assertFalse(inspect_word_pdf(incomplete)['validation']['eligible'])
