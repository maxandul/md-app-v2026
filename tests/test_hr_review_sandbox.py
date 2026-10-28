"""The guided walkthrough must never reach production configuration or Outlook."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from review_hr_ab import create_review_app
from webapp.db import get_db
from webapp.services import goal_review as review,goal_followups as followups,goal_delivery as delivery
from webapp.services.word_packages import goal_sources_fingerprint


class HRReviewSandboxTest(unittest.TestCase):
    def test_isolated_walkthrough_blocks_external_actions_and_preserves_existing_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'guided'
            with patch.dict(os.environ,{'MD_ORG_CONFIG':str(Path(temp)/'missing-prod-config.json'),
                         'MD_DOSSIER_HANDOFF_ROOT':str(Path(temp)/'must-not-exist')}):
                app=create_review_app(root)
            self.assertFalse((Path(temp)/'must-not-exist').exists())
            self.assertNotIn('mail_scan_worker',app.extensions)
            client=app.test_client()
            response=client.get('/arbeit/ziele')
            self.assertEqual(response.status_code,200)
            self.assertIn('HR-TEST',response.text);self.assertIn('Lena',response.text)
            for path in ('/arbeit','/mitarbeitende','/fuehrungskraefte','/arbeit/feedback','/arbeit/uebergaben','/?view=cycles'):
                page=client.get(path)
                self.assertEqual(page.status_code,200,path);self.assertIn('HR-TEST',page.text)
            with client.session_transaction() as session:csrf=session['goal_csrf']
            with app.app_context():
                db=get_db()
                self.assertEqual(db.execute('SELECT COUNT(*) FROM hr_goal_sources').fetchone()[0],5)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM hr_goal_revisions WHERE employment_id IS NULL').fetchone()[0],1)
                source=review.get(db,1)
                with ZipFile(source['stored_path']) as doc:self.assertIn('[Content_Types].xml',doc.namelist())
                rev=review.save(db,1,expected_revision=0,status='confirmed',employment_id=source['employment_id'],
                    goal_year=2025,goals=source['goals'],checked=True,note='Testprüfung',
                    expected_sources=goal_sources_fingerprint(review.sources(db,source['employment_id'],2025)))
                case=followups.targets(db,rev)[0]['case_id'];_,fingerprint,_=followups.inputs(db,rev,case,app.config['WORD_TEMPLATE_PATHS'])
                output=followups.generate(db,[(rev,case,fingerprint)],template_paths=app.config['WORD_TEMPLATE_PATHS'],output_dir=root/'data'/'outputs')[0]
                self.assertFalse(output['error'],output)
                followups.approve(db,output['output_id'],app.config['WORD_TEMPLATE_PATHS'])
                groups,errors=delivery.prepare(db,[output['output_id']],app.config['WORD_TEMPLATE_PATHS'])
                self.assertFalse(errors)
            with patch('webapp.services.goal_delivery.OutlookDraftAdapter') as outlook:
                response=client.post(f'/arbeit/ziele/versand/{groups[0]}',data={'csrf_token':csrf,'action':'draft','checked':'yes'})
                self.assertEqual(response.status_code,403);outlook.assert_not_called()
            self.assertEqual(client.post('/ruecklaeufe').status_code,403)
            self.assertEqual(client.get('/arbeit/dialogteile').status_code,200)
            response=client.post(f'/arbeit/dialogteile/{case}/outlook',data={'csrf_token':csrf,'revision':'0',
                'manager_pn':'900102','period_start':'2026-01-01','period_end':'2026-12-31','form_org_source':'manager','reason':'Test der Ausblick-Vertretung'},follow_redirects=True)
            self.assertEqual(response.status_code,200);self.assertIn('Luca Winter',response.text)
            with app.app_context():cycle=get_db().execute('SELECT cycle_id FROM dialog_cases WHERE case_id=?',(case,)).fetchone()[0]
            response=client.post(f'/cycles/{cycle}/cases/{case}/word-correction',data={'kind':['review','outlook']},follow_redirects=True)
            self.assertEqual(response.status_code,200)
            with app.app_context():
                ids=[r[0] for r in get_db().execute('SELECT id FROM word_person_corrections WHERE case_id=?',(case,))]
                self.assertEqual(len(ids),2)
            with patch('webapp.services.person_corrections.OutlookDraftAdapter') as outlook:
                self.assertEqual(client.post(f'/word-corrections/{ids[0]}/action',data={'action':'draft'}).status_code,403)
                outlook.assert_not_called()
            self.assertEqual(client.get('/arbeit/ziele',environ_overrides={'REMOTE_ADDR':'192.0.2.1'}).status_code,403)
            marker=root/'preserve.txt';marker.write_text('preserve',encoding='utf-8')
            with self.assertRaises(FileExistsError):create_review_app(root)
            self.assertEqual(marker.read_text(encoding='utf-8'),'preserve')


    def test_signature_walkthrough_only_copies_into_fresh_test_directory(self):
        from webapp.services import return_review
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'guided'
            outside=Path(temp)/'must-not-exist'
            with patch.dict(os.environ,{'MD_DOSSIER_HANDOFF_ROOT':str(outside)}):
                app=create_review_app(root)
            client=app.test_client();client.get('/arbeit')
            with client.session_transaction() as session:csrf=session['goal_csrf']
            with app.app_context():
                db=get_db()
                documents=[dict(r) for r in db.execute("SELECT * FROM official_documents WHERE employee_pn='900005' AND is_current=1")]
                automatic=[dict(r) for r in db.execute("SELECT * FROM official_documents WHERE employee_pn='900002' AND is_current=1")]
                self.assertEqual(len(automatic),2)
                for auto in automatic:
                    self.assertTrue(return_review.view(db,auto['id'])['complete'])
                    self.assertEqual(return_review.view(db,auto['id'])['validation_origin'],'automatic')
            self.assertEqual(len(documents),2)
            for document in documents:
                doc=document['id']
                with app.app_context():
                    db=get_db();state=return_review.view(db,doc)
                    incoming=db.execute("SELECT id FROM word_pdf_imports WHERE original_filename=? AND status='pending'",(document['document_kind']+'-testscan.pdf',)).fetchone()[0]
                    form={'csrf_token':csrf,'action':'attach','revision':state['revision'],'token':state['token'],'import_id':incoming}
                response=client.post(f'/arbeit/ruecklaeufe/{doc}',data=form,follow_redirects=True)
                self.assertEqual(response.status_code,200)
                with app.app_context():
                    state=return_review.view(get_db(),doc)
                    form={'csrf_token':csrf,'action':'confirmed','revision':state['revision'],'token':state['token'],'employee_signed':'yes','manager_signed':'yes','content_matches':'yes'}
                self.assertEqual(client.post(f'/arbeit/ruecklaeufe/{doc}',data=form).status_code,302)
                with app.app_context():
                    state=return_review.view(get_db(),doc)
                    form={'csrf_token':csrf,'action':'handoff','revision':state['revision'],'token':state['token']}
                self.assertEqual(client.post(f'/arbeit/ruecklaeufe/{doc}',data=form).status_code,302)
                with app.app_context():
                    state=return_review.view(get_db(),doc)
                    self.assertTrue(state['complete'])
                    self.assertTrue(Path(state['handoff']['destination']).is_relative_to(root/'handoff'))
                    self.assertTrue(Path(state['handoff']['destination']).is_file())
            self.assertFalse(outside.exists())
            self.assertEqual(client.post('/mail-inbox/scan').status_code,403)
            self.assertEqual(len(list((root/'handoff').glob('*.pdf'))),4)


if __name__=='__main__':unittest.main()
