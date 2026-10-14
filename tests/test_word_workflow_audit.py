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
            form.update(performance_title='Erstes Ziel', performance_criteria='Messbar', performance_steps='1. Schritt eins\n2. Schritt zwei', performance_target_date='31.12.', development_title='Entwicklung', development_competency='Selbstmanagement', development_steps='Plan')
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

        # The accepted outlook must become next year's Word review goals.
        from webapp.services.cycles import create_cycle
        from webapp.services.word_packages import prior_goals
        from zipfile import ZipFile
        sap_import = self.db.execute('SELECT sap_import_id FROM cycles WHERE id=?', (self.cycle_id,)).fetchone()[0]
        next_cycle = create_cycle(self.db, review_year=2026, sap_import_id=sap_import)
        goals, development, source = prior_goals(self.db, employee_pn='111113', assignment='1', year=2026)
        self.assertEqual([goal['title'] for goal in goals], ['Erstes Ziel'])
        self.assertEqual([goal['title'] for goal in development], ['Entwicklung'])
        self.assertEqual(source['case_id'], self.case_id)
        next_case = self.db.execute("SELECT case_id FROM dialog_cases WHERE cycle_id=? AND employee_pn='111113'", (next_cycle,)).fetchone()[0]
        response = client.post(f'/cycles/{next_cycle}/managers/111116/word-package', data={'case_id': next_case})
        self.assertEqual(response.status_code, 200)
        with ZipFile(io.BytesIO(response.data)) as archive:
            reviews = [name for name in archive.namelist() if name.endswith('.docx') and 'Rückblick' in name]
            contents = [fixtures.controls(fixtures.xml_for(archive.read(name))) for name in reviews]
        response.close()
        self.assertTrue(any('Erstes Ziel' in value.get('rb_ziel_vorjahr_1', '') for value in contents))
        self.assertEqual(self.db.execute('SELECT status FROM dialog_cases WHERE case_id=?',(next_case,)).fetchone()[0], 'offen')

        # Restore a real workflow snapshot, including stored PDFs and Word ZIPs.
        from webapp.services.operations import create_system_backup, restore_system_backup
        from webapp.db import close_db, get_db
        import hashlib
        roots = [Path(self.app.config[key]) for key in ('STORAGE_ROOT', 'DOSSIER_HANDOFF_ROOT')]
        files = {p: hashlib.sha256(p.read_bytes()).hexdigest() for root in roots for p in root.rglob('*') if p.is_file()}
        self.assertTrue(any(p.suffix == '.zip' for p in files))
        self.assertTrue(any(p.suffix == '.pdf' for p in files))
        options = dict(database_path=Path(self.app.config['DATABASE']), storage_root=roots[0], dossier_root=roots[1])
        backup = create_system_backup(self.db, **options, backup_root=Path(self.app.config['BACKUP_ROOT']))
        for path in files:
            path.unlink()
        self.db.execute('DELETE FROM sap_export_rows')
        self.db.commit()
        close_db()
        restore_system_backup(backup['path'], **options)
        self.db = get_db()
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM sap_export_rows').fetchone()[0], 1)
        for path, digest in files.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest, str(path))
        document_paths = [row[0] for row in self.db.execute('SELECT stored_path FROM official_documents')]
        self.assertTrue(all(Path(path).is_file() for path in document_paths))

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

    def test_default_ui_hides_legacy_and_admin_shows_configured_address(self):
        from unittest.mock import patch
        client=self.app.test_client()
        for page in ['/', '/stammdaten','/dialoge','/versand','/ruecklaeufe',f'/cycles/{self.cycle_id}',f'/cycles/{self.cycle_id}/managers/111116',f'/cycles/{self.cycle_id}/cases/{self.case_id}']:
            html=client.get(page).text
            self.assertNotIn('Arbeitsmappe',html,page)
            self.assertNotIn('START-Datei',html,page)
        self.app.config.update(PUBLIC_BASE_URL='https://md.example.invalid',SERVER_BIND_HOST='127.0.0.1',SERVER_BIND_PORT=5050)
        with patch('socket.gethostname',return_value='TEST-SERVER'):
            html=client.get('/administration').text
        self.assertIn('TEST-SERVER',html)
        self.assertIn('https://md.example.invalid',html)
        self.assertIn('Erreichbarkeit nicht geprüft',html)
        self.app.config['LEGACY_WORKBOOKS']='enabled'
        self.assertIn('Arbeitsmappe',client.get('/versand?workflow=workbook').text)

    def test_setup_explains_default_config_and_relative_paths(self):
        self.app.config['WORD_TEMPLATE_PATHS']={}
        for page in ['/versand',f'/cycles/{self.cycle_id}/managers/111116']:
            html=self.app.test_client().get(page).text
            self.assertIn('instance/word_config.json',html)
            self.assertIn('../templates/Dateiname.docx',html)

if __name__=='__main__': unittest.main()
