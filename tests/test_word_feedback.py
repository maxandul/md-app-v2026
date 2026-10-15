"""Plan B feedback over real HTTP and PDF paths, with isolated databases."""
import io
import json
import unittest
from pathlib import Path
from datetime import datetime, timezone
from reportlab.pdfgen import canvas
from pypdf import PdfReader
from tests import test_word_packages as fixtures
from webapp.services.word_feedback import inspect_feedback, bundle_feedback
from webapp.services.word_pdf_imports import stage_pdf
from webapp.services.mail_intake import process_inbound_messages, resolve_inbound_message
from webapp.adapters.outlook import InboundMessage, InboundAttachment


def feedback_pdf(path, name='Person Eins', pn='111116', text='Mehr Austausch', blank=False):
    c=canvas.Canvas(str(path),pagesize=(595,842))
    if not blank:
        for y,line in [(810,'Mitarbeitenden-Dialog (MD) - Feedback'),(785,'Name Mitarbeitende/r: '+name),
                       (765,'Personalnummer Vorgesetzte/r: '+pn),(740,'Gespräch vom: 15.01.2026'),
                       (700,'Selbstmanagement (Eigenverantwortung, Resilienz)'),(550,'Was soll mein/e Vorgesetzte/r unbedingt beibehalten?')]:
            c.setFont('Helvetica',9); c.drawString(40,y,line)
        for y,value in [(630,text),(480,'Offener Austausch')]:
            c.setFillColorRGB(.882,.965,1);c.rect(40,y,513,50,fill=1,stroke=0)
            c.setFillColorRGB(0,0,0);c.drawString(44,y+30,value)
    c.showPage(); c.save();return path


class WordFeedbackTest(unittest.TestCase):
    setUp=fixtures.WordPackagesTest.setUp
    tearDown=fixtures.WordPackagesTest.tearDown

    def stage(self, name='Person Eins', pn='111116', blank=False, filename='Feedback.pdf'):
        path=feedback_pdf(self.root/'input.pdf',name=name,pn=pn,blank=blank)
        return stage_pdf(self.db,path,filename=filename,directory=self.root/'data'/'queue')[0]

    def form(self, **kwargs):
        return {'revision':'0','manager_pn':'111116','cycle_id':str(self.cycle_id),'checked':'yes',
                'present_selbstmanagement':'yes','field_selbstmanagement':'Mehr Austausch',**kwargs}

    def confirm(self, item, **kwargs):
        return self.app.test_client().post(f'/feedback-imports/{item}',data=self.form(**kwargs))

    def test_counter_separates_pending_reviewed_and_bundled(self):
        from webapp.services.word_feedback import collections
        item=self.stage()
        group=lambda: next(row for row in collections(self.db) if row['cycle_id']==self.cycle_id and row['manager_pn']=='111116')
        self.assertGreater(group()['expected'],0)
        self.assertEqual(group()['pending'],1);self.assertEqual(group()['total'],0)
        self.confirm(item)
        self.assertEqual(group()['pending'],0);self.assertEqual(group()['count'],1)
        bundle_feedback(self.db,cycle_id=self.cycle_id,manager_pn='111116',expected_ids=[item],handoff_dir=self.root/'rpa',archive_dir=self.root/'archive')
        self.assertEqual(group()['total'],1);self.assertEqual(group()['bundled'],1);self.assertEqual(group()['count'],0)
        self.assertEqual(self.app.test_client().get(f'/feedback-collections/{self.cycle_id}/111116').status_code,200)

    def test_detection_geometry_and_no_inferred_year(self):
        item=self.stage()
        data=json.loads(self.db.execute('SELECT parsed_json FROM word_pdf_imports WHERE id=?',(item,)).fetchone()[0])
        self.assertEqual(data['data']['manager_pn'],'111116')
        self.assertNotIn('cycle_id',data['data'])
        self.assertEqual(data['feedback_fields']['selbstmanagement'],'Mehr Austausch')
        self.assertEqual(data['feedback_fields']['keep'],'Offener Austausch')
        client=self.app.test_client()
        page=client.get(f'/word-pdf-imports/{item}',follow_redirects=True)
        self.assertIn('Feedback übernehmen',page.text)
        self.assertIn('Bitte wählen',page.text)

    def test_upload_confirm_collect_bundle_download_repeat_and_addendum(self):
        client=self.app.test_client()
        ids=[]
        for name in ('Person Eins','Person Zwei'):
            path=feedback_pdf(self.root/'input.pdf',name=name)
            response=client.post('/word-pdf-imports',data={'word_pdf_files':(io.BytesIO(path.read_bytes()),name+'_Feedback.pdf')})
            item=int(response.location.rsplit('/',1)[1]);ids.append(item)
            self.assertEqual(self.confirm(item).status_code,302)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM feedback_bundles').fetchone()[0],0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_feedback_submissions').fetchone()[0],2)
        record=json.loads(self.db.execute('SELECT reviewed_json FROM word_pdf_imports WHERE id=?',(ids[0],)).fetchone()[0])
        self.assertEqual(record['competencies'],['Selbstmanagement'])
        self.assertEqual(record['character_counts']['selbstmanagement'],len('Mehr Austausch'))
        url=f'/feedback-collections/{self.cycle_id}/111116'
        self.assertIn('Person Eins_Feedback.pdf',client.get(url).text)
        form={'checked':'yes','import_id':[str(i) for i in ids]}
        self.assertEqual(client.post(url,data=form).status_code,302)
        bundle=self.db.execute('SELECT * FROM feedback_bundles').fetchone()
        self.assertEqual(bundle['submission_count'],2)
        self.assertIn('_111116.pdf',bundle['filename'])
        self.assertEqual(len(PdfReader(bundle['stored_path']).pages),3)
        original=Path(bundle['stored_path']).read_bytes()
        client.post(url,data=form)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM feedback_bundles').fetchone()[0],1)
        # RPA may remove the handoff file; the archive remains downloadable.
        Path(bundle['stored_path']).unlink()
        with client.get(f"/feedback-bundles/{bundle['id']}/download") as response:
            self.assertEqual(response.data,original)
        late=self.stage(name='Person Drei');self.confirm(late)
        client.post(url,data={'checked':'yes','import_id':str(late)})
        after=self.db.execute('SELECT * FROM feedback_bundles ORDER BY id DESC').fetchone()
        self.assertIn('_Nachtrag_2.pdf',after['filename'])
        self.assertEqual(after['submission_count'],1)

    def test_mail_with_neutral_filename_is_feedback_and_cannot_close_early(self):
        path=feedback_pdf(self.root/'mail.pdf')
        msg=InboundMessage('feedback-mail','<fb@test.invalid>','test@example.invalid','Datei',datetime.now(timezone.utc),(InboundAttachment(1,'neutral.pdf',path.read_bytes()),))
        result=process_inbound_messages(self.db,messages=[msg],inbox_dir=self.root/'inbox',pdf_dir=self.root/'pdfs',target_folder='MD',move_message=lambda *args:self.fail('Premature move'))
        self.assertEqual(result['review'],1)
        item=self.db.execute('SELECT id FROM word_pdf_imports').fetchone()[0]
        mail=self.db.execute('SELECT id FROM inbound_mail_messages').fetchone()[0]
        with self.assertRaises(ValueError):resolve_inbound_message(self.db,message_id=mail,mailbox_name='Test',target_folder='MD')
        self.confirm(item)
        self.assertEqual(resolve_inbound_message(self.db,message_id=mail,mailbox_name='Test',target_folder='MD')['status'],'review_completed')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM feedback_bundles').fetchone()[0],0)

    def test_duplicate_bytes_reuse_existing_review(self):
        item=self.stage();self.confirm(item)
        row=self.db.execute('SELECT * FROM word_pdf_imports WHERE id=?',(item,)).fetchone()
        duplicate,exists=stage_pdf(self.db,Path(row['stored_path']),filename='Renamed_Feedback.pdf',directory=self.root/'data'/'queue')
        self.assertEqual((duplicate,exists),(item,True))
        self.confirm(item)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_feedback_submissions').fetchone()[0],1)

    def test_conflicting_pn_missing_year_and_unchecked_are_blocked(self):
        item=self.stage(filename='Name_Feedback_an_Test_111117.pdf')
        for changes in ({'cycle_id':''},{'checked':''},{'manager_pn':'111118'},{'reason':''}):
            response=self.confirm(item,**changes)
            self.assertEqual(response.status_code,200)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_feedback_submissions').fetchone()[0],0)
        self.assertEqual(self.confirm(item,reason='PN anhand Original geprüft').status_code,302)

    def test_draft_stale_submission_dismiss_reopen(self):
        item=self.stage();client=self.app.test_client()
        self.confirm(item,action='draft')
        response=self.confirm(item)
        self.assertIn('inzwischen geändert',response.text)
        self.confirm(item,revision='1',action='dismiss',reason='Falsches Dokument, bitte klären')
        self.confirm(item,revision='2')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_feedback_submissions').fetchone()[0],0)
        self.confirm(item,revision='2',action='reopen',reason='Original mit Führungskraft geklärt')
        self.assertEqual(self.confirm(item,revision='3').status_code,302)

    def test_blank_scan_manual_classification_and_reversal(self):
        item=self.stage(blank=True,filename='scan.pdf');client=self.app.test_client()
        response=client.post(f'/word-pdf-imports/{item}/as-feedback',data={'revision':'0'})
        self.assertEqual(response.status_code,302)
        self.assertIn('Bild-PDF/Scan',client.get(response.location).text)
        self.confirm(item,revision='1',action='to_document')
        self.assertNotIn('Feedback übernehmen',client.get(f'/word-pdf-imports/{item}').text)

    def test_changed_collection_and_tampered_original_do_not_publish(self):
        first=self.stage();self.confirm(first)
        second=self.stage(name='Zwei');self.confirm(second)
        options=dict(cycle_id=self.cycle_id,manager_pn='111116',handoff_dir=self.root/'handoff',archive_dir=self.root/'data'/'bundles')
        with self.assertRaises(ValueError):bundle_feedback(self.db,expected_ids=[first],**options)
        source=self.db.execute('SELECT stored_path FROM word_pdf_imports WHERE id=?',(second,)).fetchone()[0]
        Path(source).write_bytes(b'tampered')
        with self.assertRaises(ValueError):bundle_feedback(self.db,expected_ids=[first,second],**options)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM feedback_bundles').fetchone()[0],0)
        self.assertFalse(list((self.root/'handoff').glob('*.pdf')))

    def test_manager_isolation_and_closed_cycle(self):
        one=self.stage();self.confirm(one)
        two=self.stage(name='Andere Person',pn='111117');self.confirm(two,manager_pn='111117')
        bundle_feedback(self.db,cycle_id=self.cycle_id,manager_pn='111116',expected_ids=[one],handoff_dir=self.root/'handoff',archive_dir=self.root/'data'/'bundles')
        self.assertIsNone(self.db.execute('SELECT bundle_id FROM word_feedback_submissions WHERE import_id=?',(two,)).fetchone()[0])
        self.db.execute("UPDATE cycles SET status='abgeschlossen'");self.db.commit()
        with self.assertRaises(ValueError):bundle_feedback(self.db,cycle_id=self.cycle_id,manager_pn='111117',expected_ids=[two],handoff_dir=self.root/'handoff',archive_dir=self.root/'data'/'bundles')

    def test_correction_retracts_collection_until_reconfirmed(self):
        item=self.stage();self.confirm(item);client=self.app.test_client()
        client.post(f'/feedback-imports/{item}/reopen',data={'revision':'1','reason':'Führungskraft wurde falsch zugeordnet'})
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_feedback_submissions').fetchone()[0],0)
        self.assertEqual(self.db.execute('SELECT status FROM word_pdf_imports WHERE id=?',(item,)).fetchone()[0],'pending')
        self.confirm(item,revision='2',manager_pn='111117',reason='Personalnummer anhand Original korrigiert')
        self.assertEqual(self.db.execute('SELECT manager_pn FROM word_feedback_submissions').fetchone()[0],'111117')
        bundle_feedback(self.db,cycle_id=self.cycle_id,manager_pn='111117',expected_ids=[item],handoff_dir=self.root/'handoff',archive_dir=self.root/'data'/'bundles')
        client.post(f'/feedback-imports/{item}/reopen',data={'revision':'3','reason':'Ein zweiter Korrekturversuch'})
        self.assertEqual(self.db.execute('SELECT status FROM word_pdf_imports WHERE id=?',(item,)).fetchone()[0],'imported')

    def test_preexisting_handoff_file_is_never_overwritten(self):
        item=self.stage();self.confirm(item)
        manager=self.db.execute("SELECT first_name,last_name FROM employees WHERE pn='111116'").fetchone()
        path=self.root/'handoff'/f"Feedback_2025_{manager['last_name']}_{manager['first_name']}_111116.pdf"
        path.parent.mkdir(exist_ok=True);path.write_bytes(b'existing handoff')
        with self.assertRaises(FileExistsError):
            bundle_feedback(self.db,cycle_id=self.cycle_id,manager_pn='111116',expected_ids=[item],handoff_dir=path.parent,archive_dir=self.root/'data'/'bundles')
        self.assertEqual(path.read_bytes(),b'existing handoff')
        self.assertFalse(list((self.root/'data'/'bundles').glob('*.pdf')))
        self.assertIsNone(self.db.execute('SELECT bundle_id FROM word_feedback_submissions').fetchone()[0])

    def test_other_year_is_not_included_and_identical_answers_are_not_deduplicated(self):
        from webapp.services.cycles import create_cycle
        sap=self.db.execute('SELECT sap_import_id FROM cycles WHERE id=?',(self.cycle_id,)).fetchone()[0]
        next_cycle=create_cycle(self.db,review_year=2026,sap_import_id=sap)
        first=self.stage(name='Eins');self.confirm(first)
        second=self.stage(name='Zwei');self.confirm(second,cycle_id=str(next_cycle))
        bundle_feedback(self.db,cycle_id=self.cycle_id,manager_pn='111116',expected_ids=[first],handoff_dir=self.root/'handoff',archive_dir=self.root/'data'/'bundles')
        self.assertIsNone(self.db.execute('SELECT bundle_id FROM word_feedback_submissions WHERE import_id=?',(second,)).fetchone()[0])

    def test_tampered_feedback_cannot_be_confirmed(self):
        item=self.stage()
        path=Path(self.db.execute('SELECT stored_path FROM word_pdf_imports WHERE id=?',(item,)).fetchone()[0])
        path.write_bytes(b'changed')
        self.assertIn('Original fehlt oder wurde verändert',self.confirm(item).text)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_feedback_submissions').fetchone()[0],0)
