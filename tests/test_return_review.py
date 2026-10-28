from pathlib import Path
import unittest
from datetime import datetime,timezone
from unittest.mock import patch

from tests import test_goal_workflow as fixtures
from tests import test_word_packages as legacy_fixtures
from tests import test_word_pdf_imports as pdf_fixtures

sample_pdf=pdf_fixtures.sample_pdf
from webapp.db import init_db
from webapp.services import word_pdf_imports as pdfs,return_review as returns,part_responsibilities as parts
from webapp.services.documents import confirm_digital_signature,import_handwritten_scan


class ReturnReviewTest(unittest.TestCase):
    setUp=fixtures.GoalWorkflowTest.setUp
    tearDown=fixtures.GoalWorkflowTest.tearDown

    def imported(self,kind='review',rating='D',source_role='digital',marker=''):
        path=sample_pdf(self.root/(kind+marker+'.pdf'),kind=kind,year=2026 if kind=='outlook' else 2025,marker=marker)
        incoming=pdfs.stage_pdf(self.db,path,filename=path.name,directory=self.root/'incoming')[0]
        reviewed=pdf_fixtures.WordPdfImportsTest.reviewed(self,incoming)
        reviewed['data']['rating']=rating if kind=='review' else ''
        reviewed['source_role']=source_role
        doc=pdfs.confirm_import(self.db,incoming,reviewed=reviewed,assignment='1',case_id=self.case_id,historical=False,reason='Alle Angaben und erforderlichen Inhalte am Original geprüft')
        return doc,incoming

    def current(self,doc):
        row=returns.view(self.db,doc)
        return dict(revision=row['revision'],token=row['token'])

    def attach(self,doc,marker='scan'):
        path=sample_pdf(self.root/(marker+'.pdf'),marker=marker)
        return returns.attach_evidence(self.db,doc,path=path,filename=path.name,directory=self.root/'evidence',**self.current(doc))

    def confirm(self,doc):
        returns.inspect_signatures(self.db,doc,action='confirmed',employee_signed=True,manager_signed=True,content_matches=True,**self.current(doc))

    def publish(self,doc):
        return returns.handoff(self.db,doc,directory=self.root/'handoff',**self.current(doc))

    def test_negative_review_requires_both_parts_and_keeps_new_signatures_unclaimed(self):
        review,_=self.imported();outlook,_=self.imported('outlook')
        for doc in (review,outlook):
            state=returns.view(self.db,doc)
            self.assertTrue(state['required']);self.assertEqual(state['signature_state'],'missing_scan')
            self.assertEqual(state['signature_checked'],0)
            with self.assertRaisesRegex(ValueError,'Scan fehlt'):self.publish(doc)
        self.assertFalse(list((self.root/'handoff').glob('*.pdf')))

    def test_scan_upload_does_not_confirm_or_publish_and_both_signatures_are_required(self):
        doc,_=self.imported();self.attach(doc)
        self.assertEqual(returns.view(self.db,doc)['signature_state'],'pending')
        with self.assertRaisesRegex(ValueError,'beide Unterschriften'):
            returns.inspect_signatures(self.db,doc,action='confirmed',employee_signed=True,content_matches=True,**self.current(doc))
        self.assertFalse(list((self.root/'handoff').glob('*.pdf')))
        self.confirm(doc);self.publish(doc)
        state=returns.view(self.db,doc)
        self.assertTrue(state['complete']);self.assertEqual(state['signature_checked'],0)
        self.assertEqual(Path(state['handoff']['destination']).read_bytes(),Path(state['evidence']['stored_path']).read_bytes())

    def test_scan_alone_is_data_source_and_evidence_without_second_pdf(self):
        doc,_=self.imported(source_role='scan')
        state=returns.view(self.db,doc)
        self.assertEqual(state['source_role'],'scan');self.assertEqual(state['evidence']['sha256'],state['sha256'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],1)
        self.confirm(doc);self.publish(doc)
        self.assertTrue(returns.view(self.db,doc)['complete'])

    def test_duplicate_scan_retains_decision_but_new_scan_reopens_check(self):
        doc,_=self.imported();first=self.attach(doc);self.confirm(doc)
        before=returns.view(self.db,doc)
        path=Path(before['evidence']['stored_path'])
        again=returns.attach_evidence(self.db,doc,path=path,filename='renamed.pdf',directory=self.root/'evidence',**self.current(doc))
        self.assertEqual(again,first);self.assertEqual(returns.view(self.db,doc)['signature_state'],'confirmed')
        self.attach(doc,'replacement');self.assertEqual(returns.view(self.db,doc)['signature_state'],'pending')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM hr_return_evidence').fetchone()[0],2)

    def test_missing_signature_and_actual_request_are_distinct(self):
        doc,_=self.imported();self.attach(doc)
        returns.inspect_signatures(self.db,doc,action='missing',reason='Unterschrift der mitarbeitenden Person fehlt',**self.current(doc))
        self.assertEqual(returns.view(self.db,doc)['signature_state'],'missing')
        with self.assertRaisesRegex(ValueError,'Datum'):
            returns.inspect_signatures(self.db,doc,action='requested',reason='Unterschrift angefordert',recipient='Führungskraft',**self.current(doc))
        returns.inspect_signatures(self.db,doc,action='requested',requested_at='2026-01-15',recipient='Führungskraft 111116',reason='Fehlende Unterschrift tatsächlich per Telefon angefordert',**self.current(doc))
        state=returns.view(self.db,doc);self.assertEqual(state['signature_state'],'requested')
        self.assertIn('2026-01-15',state['history'][-1]['details_json'])
        self.attach(doc,'new-return');self.assertEqual(returns.view(self.db,doc)['signature_state'],'pending')

    def test_new_data_version_never_inherits_old_signature_check(self):
        old,_=self.imported();self.attach(old);self.confirm(old)
        new,_=self.imported(rating='E',marker='corrected')
        self.assertNotEqual(new,old);self.assertEqual(returns.view(self.db,new)['signature_state'],'missing_scan')
        self.assertEqual(returns.view(self.db,old)['signature_status'],'confirmed')
        with self.assertRaisesRegex(ValueError,'geändert'):self.confirm(old)

    def test_late_negative_review_keeps_external_outlook_effect_visible(self):
        outlook,_=self.imported('outlook');self.publish(outlook)
        original=Path(returns.view(self.db,outlook)['handoff']['destination']);data=original.read_bytes()
        self.imported()
        state=returns.view(self.db,outlook);self.assertTrue(state['external_open']);self.assertFalse(state['complete'])
        self.attach(outlook,'late-scan');self.confirm(outlook)
        with self.assertRaisesRegex(ValueError,'externe Korrektur'):self.publish(outlook)
        self.assertEqual(original.read_bytes(),data)

    def test_copy_error_keeps_data_and_signature_decision_then_retries_only_handoff(self):
        doc,_=self.imported(source_role='scan');self.confirm(doc)
        with patch('webapp.services.dossier_files.publish_copy',side_effect=OSError('Testablage nicht erreichbar')):
            with self.assertRaises(OSError):self.publish(doc)
        self.assertEqual(returns.view(self.db,doc)['signature_state'],'confirmed')
        with self.assertRaisesRegex(ValueError,'unklaren Ausgang'):self.publish(doc)
        returns.clarify_failed_handoff(self.db,doc,reason='Ablage und Verarbeitung geprüft: keine Kopie übergeben; Prozess beendet',not_delivered=True,**self.current(doc))
        self.publish(doc);state=returns.view(self.db,doc)
        self.assertTrue(state['complete'])
        self.assertEqual(sum(x['action']=='confirmed' for x in state['history']),1)

    def test_retry_after_robot_consumption_does_not_republish(self):
        doc,_=self.imported(rating='C');self.publish(doc)
        destination=Path(returns.view(self.db,doc)['handoff']['destination']);destination.unlink()
        self.publish(doc);self.assertFalse(destination.exists())

    def test_source_or_scan_mutation_blocks_check_and_delivery(self):
        doc,_=self.imported();self.attach(doc);state=returns.view(self.db,doc)
        Path(state['evidence']['stored_path']).write_bytes(b'altered')
        with self.assertRaisesRegex(ValueError,'Original'):self.confirm(doc)
        with self.assertRaisesRegex(ValueError,'Original'):self.publish(doc)

    def test_responsibility_change_invalidates_open_review(self):
        doc,_=self.imported(source_role='scan');state=self.current(doc)
        part=parts.resolve(self.db,self.case_id,'review')
        parts.assign(self.db,self.case_id,kind='review',manager_pn='111114',form_org_source='employee',period_start=part['period_start'],period_end=part['period_end'],expected_revision=part['responsibility_revision'],reason='Zuständigkeit für diesen Teil ausdrücklich korrigiert')
        with self.assertRaisesRegex(ValueError,'geändert'):
            returns.inspect_signatures(self.db,doc,action='confirmed',employee_signed=True,manager_signed=True,content_matches=True,**state)

    def test_restart_preserves_outlook_requirement_and_signature_history(self):
        self.imported();doc,_=self.imported('outlook',source_role='scan');self.confirm(doc)
        before=[tuple(r) for r in self.db.execute('SELECT * FROM hr_return_decisions')]
        init_db(self.db)
        self.assertEqual(before,[tuple(r) for r in self.db.execute('SELECT * FROM hr_return_decisions')])
        self.assertEqual(returns.view(self.db,doc)['signature_state'],'confirmed')
        self.assertTrue(returns.view(self.db,doc)['required'])
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_legacy_signature_api_does_not_claim_new_signature_check(self):
        doc,_=self.imported()
        result=confirm_digital_signature(self.db,document_id=doc,handoff_dir=self.root/'handoff')
        self.assertTrue(result['scan_required']);self.assertEqual(returns.view(self.db,doc)['signature_checked'],0)
        with self.assertRaisesRegex(ValueError,'versionsbezogen'):
            import_handwritten_scan(self.db,case_id=self.case_id,document_kind='review',path=self.root/'unused.pdf',original_filename='scan.pdf',handoff_dir=self.root/'handoff')

    def test_route_csrf_scan_original_and_no_automatic_signature(self):
        doc,_=self.imported(source_role='scan');url=f'/arbeit/ruecklaeufe/{doc}'
        response=self.client.get(url+'?back=/ruecklaeufe?pdf_page=2')
        self.assertEqual(response.status_code,200);self.assertIn('Unterschriftenprüfung offen',response.text)
        self.assertIn('/ruecklaeufe?pdf_page=2',response.text)
        self.assertEqual(self.client.get(url+'/scan').status_code,200)
        form=dict(self.current(doc),action='confirmed',employee_signed='yes',manager_signed='yes',content_matches='yes')
        self.assertEqual(self.client.post(url,data=form).status_code,400)
        response=self.client.post(url,data={**form,'csrf_token':self.csrf},follow_redirects=True)
        self.assertEqual(response.status_code,200);self.assertIn('Unterschriften vorhanden',response.text)
        self.assertFalse(list((self.root/'handoff').glob('*.pdf')))

    def test_saved_incoming_scan_links_without_duplicate_business_data(self):
        doc,_=self.imported();path=sample_pdf(self.root/'mail-scan.pdf',marker='mail')
        incoming=pdfs.stage_pdf(self.db,path,filename=path.name,directory=self.root/'incoming')[0]
        item=self.db.execute('SELECT * FROM word_pdf_imports WHERE id=?',(incoming,)).fetchone()
        returns.attach_evidence(self.db,doc,path=Path(item['stored_path']),filename=item['original_filename'],directory=self.root/'evidence',import_id=incoming,**self.current(doc))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],1)
        self.assertEqual(self.db.execute('SELECT status FROM word_pdf_imports WHERE id=?',(incoming,)).fetchone()[0],'imported')
        self.assertEqual(returns.view(self.db,doc)['signature_state'],'pending')
        response=self.client.get(f'/word-pdf-imports/{incoming}/original')
        self.assertEqual(response.data,path.read_bytes())

    def test_same_scan_received_by_mail_keeps_completed_signature_check(self):
        doc,_=self.imported();self.attach(doc);self.confirm(doc)
        state=returns.view(self.db,doc);path=Path(state['evidence']['stored_path'])
        incoming=pdfs.stage_pdf(self.db,path,filename='mail.pdf',directory=self.root/'incoming')[0]
        returns.attach_evidence(self.db,doc,path=path,filename='mail.pdf',directory=self.root/'evidence',import_id=incoming,**self.current(doc))
        self.assertEqual(returns.view(self.db,doc)['signature_state'],'confirmed')
        self.assertEqual(self.db.execute('SELECT status FROM word_pdf_imports WHERE id=?',(incoming,)).fetchone()[0],'imported')

    def test_attachment_success_without_message_text_never_moves_mail(self):
        from webapp.adapters.outlook import InboundAttachment,InboundMessage
        from webapp.services.mail_intake import process_inbound_messages
        doc,incoming=self.imported(rating='C');self.publish(doc)
        original=self.db.execute('SELECT stored_path FROM word_pdf_imports WHERE id=?',(incoming,)).fetchone()[0]
        message=InboundMessage('mail-e','<mail-e>','test@example.invalid','MD Rückblick',datetime.now(timezone.utc),(InboundAttachment(1,'Rueckblick.pdf',Path(original).read_bytes()),))
        moved=[]
        process_inbound_messages(self.db,messages=[message],inbox_dir=self.root/'mail',pdf_dir=self.root/'received',handoff_dir=self.root/'handoff',target_folder='MD',move_message=lambda *a:moved.append(a))
        self.assertEqual(moved,[])
        row=self.db.execute('SELECT * FROM inbound_mail_messages').fetchone()
        self.assertEqual(row['status'],'review_required');self.assertIn('Nachrichtentext',row['error_message'])

    def test_legacy_release_route_cannot_bypass_current_review_action(self):
        doc,_=self.imported(rating='C')
        response=self.client.post(f'/documents/{doc}/signature-checked')
        self.assertIn(f'/arbeit/ruecklaeufe/{doc}',response.location)
        self.assertFalse(returns.view(self.db,doc)['locally_staged'])

    def test_return_tasks_are_separate_by_part_and_wait_only_after_actual_request(self):
        review,_=self.imported();outlook,_=self.imported('outlook')
        from webapp.services.cockpit import cockpit_overview
        tasks=[t for t in cockpit_overview(self.db)['tasks'] if t['target']=='return_review']
        self.assertEqual({t['document_id'] for t in tasks},{review,outlook});self.assertFalse(any(t['waiting'] for t in tasks))
        returns.inspect_signatures(self.db,outlook,action='requested',requested_at='2026-01-15',recipient='Ausblickverantwortliche Person',reason='Unterschriebenen Ausblick tatsächlich angefordert',**self.current(outlook))
        tasks=returns.tasks(self.db);self.assertTrue(next(t for t in tasks if t['document_id']==outlook)['waiting'])

    def test_existing_overviews_use_new_signature_and_delivery_status(self):
        from webapp.services.part_queries import managers
        from webapp.services.hr_workflow import closure_summary
        from webapp.services.documents import case_document_overview
        doc,_=self.imported()
        state=returns.view(self.db,doc);cycle_id=state['cycle_id'];manager=state['part']['manager_pn']
        def counts():return next(r for r in managers(self.db,cycle_id) if r['manager_pn']==manager)
        self.assertEqual(counts()['scan_pending_count'],1)
        self.attach(doc)
        self.assertEqual(counts()['scan_pending_count'],0)
        self.assertEqual(counts()['signature_check_count'],1)
        self.confirm(doc);self.publish(doc)
        self.assertEqual(counts()['signature_check_count'],0)
        self.assertEqual(closure_summary(self.db,cycle_id)['Offene Dossierübergaben'],0)
        case=next(c for c in case_document_overview(self.db,cycle_id=cycle_id,manager_pn=manager) if c['case_id']==self.case_id)
        review=next(d for d in case['document_states'] if d['kind']=='review')
        self.assertEqual(review['key'],'staged');self.assertEqual(review['return_document_id'],doc)

    def test_migration_preserves_existing_scan_and_does_not_invent_reviewer(self):
        import webapp.migrations as migrations
        old=legacy_fixtures.WordPackagesTest();old.setUp()
        try:
            directory=Path(migrations.__file__).with_suffix('')
            previous=sorted(directory.glob('00[1234]*.sql'))
            with patch.object(migrations.Path,'glob',return_value=previous):migrations.migrate(old.db)
            path=sample_pdf(old.root/'review.pdf')
            incoming=pdfs.stage_pdf(old.db,path,filename=path.name,directory=old.root/'incoming')[0]
            reviewed=pdf_fixtures.WordPdfImportsTest.reviewed(old,incoming);reviewed['data']['rating']='D'
            doc=pdfs.confirm_import(old.db,incoming,reviewed=reviewed,assignment='1',case_id=old.case_id,historical=False,reason='Bisherige Prüfung vor neuer Migration')
            confirm_digital_signature(old.db,document_id=doc,handoff_dir=old.root/'handoff')
            scan=sample_pdf(old.root/'scan.pdf',marker='existing scan')
            import_handwritten_scan(old.db,case_id=old.case_id,document_kind='review',path=scan,original_filename='scan.pdf',handoff_dir=old.root/'handoff')
            tables=('official_documents','document_obligations','dialog_cases','word_pdf_imports')
            before={t:[tuple(r) for r in old.db.execute('SELECT * FROM '+t)] for t in tables}
            migrations.migrate(old.db);init_db(old.db)
            for table,rows in before.items():self.assertEqual(rows,[tuple(r) for r in old.db.execute('SELECT * FROM '+table)])
            state=returns.view(old.db,doc)
            self.assertEqual(state['signature_status'],'legacy_confirmed')
            self.assertEqual(state['validation_origin'],'legacy');self.assertIsNone(state['validated_by']);self.assertEqual(state['validated_at'],'')
            self.assertTrue(state['locally_staged']);self.assertTrue(Path(state['evidence']['stored_path']).is_file())
            self.assertEqual(old.db.execute('PRAGMA foreign_key_check').fetchall(),[])
        finally:old.tearDown()


if __name__=='__main__':unittest.main()
