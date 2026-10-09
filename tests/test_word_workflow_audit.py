"""Regression des Word-PDF-Ablaufs über die tatsächlich angebotenen HTTP-Aktionen."""
import io
import unittest
from pathlib import Path
from html.parser import HTMLParser
from tests import test_word_packages as fixtures
from tests.test_word_pdf_imports import sample_pdf


class Forms(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.actions=[]; self.feed(html)
    def handle_starttag(self, tag, attrs):
        if tag=='form': self.actions.append(dict(attrs).get('action',''))


class WordWorkflowAuditTest(unittest.TestCase):
    setUp=fixtures.WordPackagesTest.setUp
    tearDown=fixtures.WordPackagesTest.tearDown

    def test_whole_http_workflow_download_review_handoff_and_sap(self):
        client=self.app.test_client()
        manager=f'/cycles/{self.cycle_id}/managers/111116'
        case=f'/cycles/{self.cycle_id}/cases/{self.case_id}'
        for page in ['/', '/stammdaten','/dialoge','/versand','/ruecklaeufe','/sap-export','/auswertungen',manager,case]:
            self.assertEqual(client.get(page).status_code,200,page)
        response=client.post(manager+'/word-package')
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.data.startswith(b'PK')); response.close()
        package=self.db.execute('SELECT id FROM word_dispatch_packages').fetchone()[0]
        self.assertIn(f'/word-packages/{package}/download',client.get(manager).text)
        for kind,year in [('review',2025),('outlook',2026)]:
            path=sample_pdf(self.root/f'{kind}.pdf',kind=kind,year=year)
            response=client.post('/word-pdf-imports',data={'word_pdf_files':(io.BytesIO(path.read_bytes()),f'{kind}.pdf')})
            review_url=response.location
            self.assertIn('/word-pdf-imports/',review_url)
            form={'document_kind':kind,'pn':'111113','manager_pn':'111116','period_start':f'{year}-01-01','period_end':f'{year}-12-31','dialog_date':f'{year}-12-15','conducted':'ja','rating':'C' if kind=='review' else '', 'scope':'full','assignment':'1','case_id':self.case_id,'destination':'case','checked':'yes'}
            response=client.post(review_url,data=form,follow_redirects=True)
            self.assertIn('Nächster Schritt: Fallprüfung',response.text)
            row=self.db.execute('SELECT id,handoff_status FROM official_documents WHERE document_kind=?',(kind,)).fetchone()
            self.assertEqual(row['handoff_status'],'needs_signature_check')
            action=f"/documents/{row['id']}/signature-checked"
            self.assertIn(action,Forms(client.get(case).text).actions)
            self.assertNotIn('Vor Umstellung eingegangen',client.get(manager).text)
            response=client.post(action,headers={'Referer':'http://localhost'+case},follow_redirects=True)
            self.assertIn('für die Personaldossier-Ablage bereitgestellt',response.text)
            document=self.db.execute('SELECT * FROM official_documents WHERE id=?',(row['id'],)).fetchone()
            self.assertEqual(document['handoff_status'],'staged')
            self.assertTrue(Path(document['stored_path']).is_file())
            self.assertNotIn(action,Forms(client.get(case).text).actions)
            with client.get(review_url+'/original') as response:
                self.assertEqual(response.status_code,200)
        self.assertEqual(self.db.execute('SELECT status FROM dialog_cases WHERE case_id=?',(self.case_id,)).fetchone()[0],'vollstaendig')
        with client.post(f'/cycles/{self.cycle_id}/sap-export') as response:
            self.assertEqual(response.status_code,200)
            self.assertTrue(response.data.startswith(b'PK'))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM sap_export_rows').fetchone()[0],1)
        self.assertEqual(client.post(f'/cycles/{self.cycle_id}/sap-export').status_code,302)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM sap_export_rows').fetchone()[0],1)

    def test_scan_action_available_after_signature_and_removed_after_handoff(self):
        from webapp.services.word_pdf_imports import stage_pdf, confirm_import
        import json
        path=sample_pdf(self.root/'review.pdf')
        item=stage_pdf(self.db,path,filename='review.pdf',directory=self.root/'queue')[0]
        parsed=json.loads(self.db.execute('SELECT parsed_json FROM word_pdf_imports WHERE id=?',(item,)).fetchone()[0])
        parsed['data']['rating']='D'; parsed['scope']='review_only'
        confirm_import(self.db,item,reviewed=parsed,assignment='1',case_id=self.case_id,historical=False,reason='Nur Rückblick im geprüften Testfall')
        document=self.db.execute('SELECT id FROM official_documents').fetchone()[0]
        client=self.app.test_client();case=f'/cycles/{self.cycle_id}/cases/{self.case_id}'
        client.post(f'/documents/{document}/signature-checked',headers={'Referer':'http://localhost'+case})
        action=f'/cases/{self.case_id}/scans/review'
        self.assertIn(action,Forms(client.get(case).text).actions)
        scan=sample_pdf(self.root/'scan.pdf',marker='Unterschriebener Testscan')
        client.post(action,data={'scan_file':(io.BytesIO(scan.read_bytes()),'scan.pdf')},headers={'Referer':'http://localhost'+case})
        self.assertNotIn(action,Forms(client.get(case).text).actions)
        self.assertEqual(self.db.execute("SELECT handoff_status FROM official_documents WHERE variant='scan'").fetchone()[0],'staged')

    def test_setup_explains_default_config_and_relative_paths(self):
        self.app.config['WORD_TEMPLATE_PATHS']={}
        for page in ['/versand',f'/cycles/{self.cycle_id}/managers/111116']:
            html=self.app.test_client().get(page).text
            self.assertIn('instance/word_config.json',html)
            self.assertIn('../templates/Dateiname.docx',html)

if __name__=='__main__': unittest.main()
