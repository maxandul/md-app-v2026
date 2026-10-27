"""A/B acceptance tests with synthetic originals and an isolated Outlook adapter."""
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
from tests import test_word_packages as fixtures
from tests.test_goal_import import word
from tests.test_word_dispatch import FakeOutlook
from webapp.db import init_db
from webapp.migrations import migrate
from webapp.services import goal_review as review, goal_followups as followups, goal_delivery as delivery, goal_queries
from webapp.services.part_responsibilities import assign_review, resolve
from webapp.services.word_packages import prior_goals,goal_sources_fingerprint


class GoalWorkflowTest(unittest.TestCase):
    def setUp(self):
        fixtures.WordPackagesTest.setUp(self)
        migrate(self.db)
        self.app.config['HR_GOAL_WORKFLOW']=True
        self.group=review.batch(self.db,'test-upload','Synthetische Nachreichung')
        self.client=self.app.test_client()
        self.client.get('/arbeit/ziele')
        with self.client.session_transaction() as s:
            self.csrf=s['goal_csrf']

    tearDown=fixtures.WordPackagesTest.tearDown

    def stage(self,name='goals.docx',title='Projekt abschliessen'):
        path=word(self.root/name,title=title)
        return review.stage(self.db,path,filename=name,batch_id=self.group,origin_key='upload:'+name)

    def confirm(self,source_id,**updates):
        item=review.get(self.db,source_id)
        values=dict(expected_revision=item['revision'],status='confirmed',employment_id=item['employment_id'],
            goal_year=item['goal_year'],goals=item['goals'],note='Am Original geprüft und Quellen verglichen',checked=True,
            expected_sources=goal_sources_fingerprint(review.sources(self.db,item['employment_id'],item['goal_year'])))
        values.update(updates)
        if 'expected_sources' not in updates:
            values['expected_sources']=goal_sources_fingerprint(review.sources(self.db,values['employment_id'],values['goal_year']))
        return review.save(self.db,source_id,**values)

    def generate(self,rev,case=None):
        case=case or self.case_id
        _,fp,_=followups.inputs(self.db,rev,case,self.paths)
        return followups.generate(self.db,[(rev,case,fp)],template_paths=self.paths,output_dir=self.root/'outputs')[0]

    def ready(self):
        source=self.stage();rev=self.confirm(source);output=self.generate(rev)['output_id']
        followups.approve(self.db,output,self.paths)
        ids,errors=delivery.prepare(self.db,[output],self.paths)
        self.assertFalse(errors)
        return source,rev,output,ids[0]

    def act(self,group,action='draft',**updates):
        args=dict(action=action,template_paths=self.paths,lock_root=self.root/'locks',sender_email='hr@example.invalid',
                  subject='Aktualisierte Rückblicke',body='Hallo\n\nBitte Inhalte abgleichen.',checked=True,reason='Tatsächlichen Outlook-Stand geprüft')
        args.update(updates)
        return delivery.act(self.db,group,**args)

    def pending_return(self,pn='111113',kind='review'):
        with self.db:
            self.db.execute('''INSERT INTO word_pdf_imports(original_filename,stored_path,sha256,parsed_json,created_at)
                VALUES ('return.pdf','not-needed','return-hash',?,'2026-10-27')''',
                (json.dumps({'data':{'document_kind':kind,'pn':pn,'period_end':'2025-12-31'},'issues':[]}),))

    def test_roundtrip_revision_output_draft_confirmation_and_repeat(self):
        source,rev,output,group=self.ready()
        selected=prior_goals(self.db,employee_pn='111113',assignment='1',year=2025)
        self.assertEqual(selected[2]['hr_goal_revision_id'],rev)
        fake=FakeOutlook();self.act(group,adapter=fake)
        self.assertEqual(delivery.get(self.db,group)['status'],'draft_created')
        self.assertEqual(len(fake.calls),1)
        with self.assertRaises(ValueError):self.act(group,adapter=fake)
        self.act(group,action='sent_confirmed');self.act(group,action='sent_confirmed')
        self.assertEqual(goal_queries.source_state(self.db,source),'done')
        self.assertEqual(self.generate(rev)['output_id'],output)
        ids,errors=delivery.prepare(self.db,[output],self.paths)
        self.assertEqual(ids,[group]);self.assertFalse(errors)

    def test_duplicate_upload_recovers_edited_revision_and_preserves_original(self):
        source=self.stage();original=review.get(self.db,source)
        goals=original['goals'];goals['performance_goals'][0]['title']='Von HR ergänzt'
        rev=self.confirm(source,goals=goals)
        group=review.batch(self.db,'another-upload','Erneuter Eingang')
        duplicate=review.stage(self.db,self.root/'goals.docx',filename='copy.docx',batch_id=group,origin_key='second')
        self.assertEqual(source,duplicate)
        self.assertEqual(review.get(self.db,source)['revision_id'],rev)
        self.assertEqual(review.get(self.db,source)['extraction']['performance_goals'][0]['title'],'Projekt abschliessen')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM hr_goal_sources').fetchone()[0],1)

    def test_stale_edit_and_competing_sources_cannot_overwrite(self):
        source=self.stage();self.confirm(source)
        with self.assertRaisesRegex(ValueError,'inzwischen'):
            self.confirm(source,expected_revision=0)
        old=self.generate(self.db.execute("SELECT id FROM hr_goal_revisions WHERE status='confirmed'").fetchone()[0])['output_id']
        other=self.stage('other.docx','Andere Ziele');self.confirm(other)
        with self.assertRaisesRegex(ValueError,'andere Zielquelle'):
            followups.validate_output(self.db,old,self.paths)

    def test_incoming_return_between_selection_and_generation_blocks_only_item(self):
        source=self.stage();rev=self.confirm(source);_,fp,_=followups.inputs(self.db,rev,self.case_id,self.paths)
        self.pending_return()
        result=followups.generate(self.db,[(rev,self.case_id,fp)],template_paths=self.paths,output_dir=self.root/'outputs')
        self.assertIn('Korrekturbedarf',result[0]['error'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM hr_goal_outputs').fetchone()[0],0)

    def test_unknown_pending_return_is_not_treated_as_missing(self):
        source=self.stage();rev=self.confirm(source);self.pending_return(pn='',kind='unknown')
        with self.assertRaisesRegex(ValueError,'Korrekturbedarf'):
            self.generate(rev)

    def test_incoming_return_before_outlook_blocks_and_decision_keeps_original(self):
        source,rev,output,group=self.ready();self.pending_return();fake=FakeOutlook()
        with self.assertRaisesRegex(ValueError,'Korrekturbedarf'):
            self.act(group,adapter=fake)
        self.assertFalse(fake.calls)
        part=resolve(self.db,self.case_id);evidence=followups.return_evidence(self.db,part)
        followups.decide(self.db,rev,self.case_id,outcome='no_change',reason='Rückblick enthält die Ziele bereits',expected_evidence=review.digest(evidence))
        self.assertEqual(goal_queries.source_state(self.db,source),'done')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_pdf_imports').fetchone()[0],1)

    def test_outlook_failure_requires_resolution_and_sent_history_survives_changes(self):
        source,rev,output,group=self.ready();fake=FakeOutlook(fail=True)
        with self.assertRaisesRegex(ValueError,'Ausgang unklar'):self.act(group,adapter=fake)
        self.assertEqual(delivery.get(self.db,group)['status'],'failed')
        with self.assertRaises(ValueError):self.act(group,adapter=FakeOutlook())
        self.confirm(source)
        self.act(group,action='sent_confirmed')
        self.assertEqual(delivery.get(self.db,group)['status'],'sent_confirmed')

    def test_separate_manager_and_org_snapshot_used_in_form_and_group(self):
        source=self.stage();rev=self.confirm(source)
        with self.db:self.db.execute("UPDATE employees SET org_unit='Alte OE' WHERE pn='111118'")
        assign_review(self.db,self.case_id,manager_pn='111118',form_org_source='manager',period_start='2025-01-01',period_end='2025-08-31',expected_revision=0,reason='Übertritt, alte Führungskraft macht Rückblick')
        with self.db:self.db.execute("UPDATE employees SET org_unit='Spätere OE' WHERE pn='111118'")
        result=self.generate(rev);self.assertFalse(result['error'],result)
        row=self.db.execute('SELECT * FROM hr_goal_outputs WHERE id=?',(result['output_id'],)).fetchone()
        manifest=json.loads(row['manifest_json'])
        with ZipFile(row['stored_path']) as archive:
            fields=fixtures.controls(fixtures.xml_for(archive.read(manifest['documents'][0]['filename'])))
        self.assertEqual(fields['rb_pn_vg'],'111118');self.assertEqual(fields['rb_oe'],'Alte OE')
        followups.approve(self.db,row['id'],self.paths)
        ids,errors=delivery.prepare(self.db,[row['id']],self.paths)
        self.assertFalse(errors)
        self.assertEqual(delivery.get(self.db,ids[0])['recipient_email'],'person-111118@example.invalid')
        self.assertEqual(self.db.execute('SELECT manager_pn FROM dialog_cases WHERE case_id=?',(self.case_id,)).fetchone()[0],'111116')

    def test_assignment_change_after_output_blocks_draft(self):
        _,_,_,group=self.ready()
        assign_review(self.db,self.case_id,manager_pn='111118',form_org_source='employee',period_start='2025-01-01',period_end='2025-12-31',expected_revision=0,reason='Vertretung')
        with self.assertRaisesRegex(ValueError,'Grundlagen'):
            self.act(group,adapter=FakeOutlook())

    def test_restart_preserves_ids_revisions_and_manual_decisions(self):
        source,rev,output,group=self.ready()
        before={t:[tuple(r) for r in self.db.execute('SELECT * FROM '+t)] for t in ('dialog_cases','document_obligations','hr_goal_sources','hr_goal_revisions','hr_goal_outputs','hr_goal_dispatches')}
        init_db(self.db,hr_goals=True);init_db(self.db)
        for table,rows in before.items():
            self.assertEqual(rows,[tuple(r) for r in self.db.execute('SELECT * FROM '+table)],table)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0],2)

    def test_ui_direct_links_upload_search_and_csrf(self):
        raw=word(self.root/'ui.docx').read_bytes()
        self.assertEqual(self.client.post('/arbeit/ziele/upload',data={'forms':(io.BytesIO(raw),'ui.docx')}).status_code,400)
        response=self.client.post('/arbeit/ziele/upload',data={'csrf_token':self.csrf,'forms':(io.BytesIO(raw),'ui.docx')},follow_redirects=True)
        self.assertEqual(response.status_code,200)
        self.assertIn('Ziele prüfen',response.text)
        source=self.db.execute('SELECT id FROM hr_goal_sources').fetchone()[0]
        self.assertIn('Zieltext',self.client.get(f'/arbeit/ziele/{source}').text)
        self.confirm(source)
        response=self.client.get('/arbeit/ziele/ausgaben',query_string={'source':source})
        self.assertEqual(response.status_code,200);self.assertIn('Zur Erstellung bereit',response.text)
        lookup=self.client.get('/arbeit/ziele/lookup',query_string={'q':'Rufname3','kind':'employment'}).json
        self.assertEqual(len(lookup['results']),1)
        original=self.client.get(f'/arbeit/ziele/{source}/original');self.assertEqual(original.status_code,200);original.close()

    def test_pagination_filters_include_old_year_and_preserve_selection_scope(self):
        for n in range(28):self.stage(f'goals{n}.docx',f'Ziel {n}')
        data=goal_queries.listing(self.db,page_size=25)
        self.assertEqual(data['total'],28);self.assertEqual(len(data['rows']),25)
        second=goal_queries.listing(self.db,page=2)
        self.assertEqual(len(second['rows']),3)
        self.assertFalse(set(r['id'] for r in data['rows'])&set(r['id'] for r in second['rows']))
        self.assertEqual(goal_queries.listing(self.db,year=2025)['total'],28)
        self.assertEqual(goal_queries.listing(self.db,q='111113')['total'],28)

    def test_five_sources_one_unclear_partial_failure_retry_and_two_recipients(self):
        selections=[];sources=[]
        for i,pn in enumerate(('111111','111112','111113','111115','111116')):
            source=self.stage(f'five-{pn}.docx',f'Ziele für {pn}');sources.append(source)
            if i==4:
                continue
            employment=self.db.execute('SELECT id FROM employment_assignments WHERE person_number=? ORDER BY id',(pn,)).fetchone()[0]
            rev=self.confirm(source,employment_id=employment)
            case=self.db.execute('SELECT case_id FROM dialog_cases WHERE employee_pn=? ORDER BY id',(pn,)).fetchone()[0]
            assign_review(self.db,case,manager_pn='111116' if i<2 else '111118',form_org_source='employee',
                period_start='2025-01-01',period_end='2025-12-31',expected_revision=0,reason='Geprüfte Verantwortung')
            _,fp,_=followups.inputs(self.db,rev,case,self.paths);selections.append((rev,case,fp))
        real=followups.create_word_package
        def interrupted(*args,**kwargs):
            if kwargs['case_id']==selections[1][1]:
                raise OSError('Synthetischer einzelner Dateifehler')
            return real(*args,**kwargs)
        with patch.object(followups,'create_word_package',side_effect=interrupted):
            first=followups.generate(self.db,selections,template_paths=self.paths,output_dir=self.root/'outputs')
        self.assertEqual(sum(bool(r['error']) for r in first),1)
        retry=followups.generate(self.db,selections,template_paths=self.paths,output_dir=self.root/'outputs')
        self.assertTrue(all(not r['error'] for r in retry),retry)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM hr_goal_outputs').fetchone()[0],4)
        self.assertEqual(goal_queries.source_state(self.db,sources[-1]),'review')
        for row in retry:followups.approve(self.db,row['output_id'],self.paths)
        groups,errors=delivery.prepare(self.db,[r['output_id'] for r in retry],self.paths)
        self.assertFalse(errors);self.assertEqual(len(groups),2)
        fake=FakeOutlook()
        for group in groups:self.act(group,adapter=fake)
        self.assertEqual(len(fake.calls),2)
        self.assertEqual(sum(len(call['attachments']) for call in fake.calls),4)

    def test_mail_and_upload_share_original_revision_and_no_automatic_move(self):
        from tests.test_mail_goals import MailGoalsTest
        from webapp.services.mail_intake import mail_inbox_overview,resolve_inbound_message
        original=word(self.root/'mail.docx')
        self.assertEqual(MailGoalsTest.scan(self,original)['moved'],0)
        source=self.db.execute('SELECT id FROM hr_goal_sources').fetchone()[0]
        rev=self.confirm(source)
        duplicate=review.stage(self.db,original,filename='manual.docx',batch_id=self.group,origin_key='manual')
        self.assertEqual(source,duplicate)
        self.assertEqual(MailGoalsTest.scan(self,original)['moved'],0)
        attachment=mail_inbox_overview(self.db)['mail_messages'][0]['attachments'][0]
        self.assertEqual(attachment['goal_source_id'],source)
        self.assertEqual(review.get(self.db,source)['revision_id'],rev)
        message=self.db.execute('SELECT id FROM inbound_mail_messages').fetchone()[0]
        resolve_inbound_message(self.db,message_id=message,mailbox_name='Test',target_folder='MD',review_note='Zusatzanliegen manuell geprüft')
        MailGoalsTest.scan(self,original)
        self.assertFalse(self.moves)
        self.assertNotEqual(goal_queries.source_state(self.db,source),'done')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM legacy_form_imports').fetchone()[0],0)

    def test_manual_responsibility_survives_changed_or_missing_sap_reporting_line(self):
        from webapp.services.cycles import synchronize_cycle_with_import
        source=self.stage();rev=self.confirm(source)
        assign_review(self.db,self.case_id,manager_pn='111118',form_org_source='employee',
            period_start='2025-01-01',period_end='2025-08-31',expected_revision=0,reason='Bestätigter Übertritt')
        sap_id=self.db.execute('SELECT sap_import_id FROM cycles WHERE id=?',(self.cycle_id,)).fetchone()[0]
        for missing in (False,True):
            with self.db:
                if missing:self.db.execute("DELETE FROM reporting_lines WHERE employee_pn='111113'")
                else:self.db.execute("UPDATE reporting_lines SET manager_pn='111117' WHERE employee_pn='111113'")
            synchronize_cycle_with_import(self.db,cycle_id=self.cycle_id,sap_import_id=sap_id)
            part=resolve(self.db,self.case_id)
            self.assertEqual(part['manager_pn'],'111118');self.assertTrue(part['active'])
            self.assertEqual(part['period_end'],'2025-08-31')
            self.assertEqual(self.db.execute("SELECT COUNT(*) FROM dialog_cases WHERE employee_pn='111113'").fetchone()[0],1)
            self.assertFalse(self.generate(rev)['error'])

    def test_waiting_blocks_prepared_output_and_explicit_resume_reopens(self):
        source,rev,output,group=self.ready()
        followups.decide(self.db,rev,self.case_id,outcome='waiting',reason='Zieltext rückfragen',expected_evidence=review.digest([]))
        with self.assertRaisesRegex(ValueError,'Folgeentscheidung'):self.act(group,adapter=FakeOutlook())
        followups.decide(self.db,rev,self.case_id,outcome='resume',reason='Rückfrage beantwortet, Fassung stimmt',expected_evidence=review.digest([]))
        self.act(group,adapter=FakeOutlook())
        self.assertEqual(delivery.get(self.db,group)['status'],'draft_created')

    def test_recipient_and_file_tampering_block_outlook(self):
        _,_,output,group=self.ready()
        with self.db:self.db.execute("UPDATE employees SET email='changed@example.invalid' WHERE pn='111116'")
        with self.assertRaisesRegex(ValueError,'Grundlagen'):self.act(group,adapter=FakeOutlook())
        with self.db:self.db.execute("UPDATE employees SET email='person-111116@example.invalid' WHERE pn='111116'")
        row=self.db.execute('SELECT stored_path FROM hr_goal_outputs WHERE id=?',(output,)).fetchone()
        Path(row[0]).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'verändert'):self.act(group,adapter=FakeOutlook())

    def test_second_database_connection_cannot_save_stale_source(self):
        import sqlite3
        source=self.stage();before=review.get(self.db,source)
        other=sqlite3.connect(self.app.config['DATABASE']);other.row_factory=sqlite3.Row
        try:
            self.confirm(source)
            with self.assertRaisesRegex(ValueError,'inzwischen'):
                review.save(other,source,expected_revision=before['revision'],status='draft',employment_id=before['employment_id'],
                    goal_year=before['goal_year'],goals=before['goals'],note='Veralteter Browser')
        finally:other.close()

    def test_existing_dispatch_routes_respect_new_open_draft(self):
        from webapp.services.word_dispatch import prepare_word_batch,dispatch_word_packages
        source,rev,output,group=self.ready()
        _,batch=prepare_word_batch(self.db,cycle_id=self.cycle_id,manager_pns=['111116'],template_paths=self.paths,output_dir=self.root/'legacy-dispatch')
        self.act(group,adapter=FakeOutlook())
        with self.assertRaisesRegex(ValueError,'Zielnachreichungs-Versand'):
            dispatch_word_packages(self.db,cycle_id=self.cycle_id,package_ids=[batch['packages'][0]['id']],
                template_paths=self.paths,sender_email='hr@example.invalid',adapter=FakeOutlook())

    def test_shared_lock_prevents_other_process_outlook_entry(self):
        from webapp.services.outlook_lock import package_lock
        _,_,_,group=self.ready()
        with package_lock(Path(self.app.config['DATABASE']).with_suffix('.dispatch')):
            with self.assertRaisesRegex(ValueError,'läuft noch'):self.act(group,adapter=FakeOutlook())

    def test_output_action_rejects_selection_from_other_source(self):
        source,rev,output,group=self.ready();other=self.stage('other.docx','Andere Ziele')
        response=self.client.post('/arbeit/ziele/ausgaben',data={'csrf_token':self.csrf,'source':other,'output':output,'action':'approve'})
        self.assertEqual(response.status_code,200);self.assertIn('gehört nicht zur aktuellen Auswahl',response.text)

    def test_migration_checksum_and_failed_ddl_are_atomic(self):
        import sqlite3
        import webapp.migrations as migrations
        with self.db:self.db.execute("UPDATE schema_migrations SET sha256='tampered'")
        with self.assertRaisesRegex(ValueError,'nachträglich'):migrate(self.db)
        empty=sqlite3.connect(self.root/'migration-failure.db')
        sql=self.root/'999_broken.sql';sql.write_text('CREATE TABLE partial(id); INVALID STATEMENT;',encoding='utf-8')
        try:
            with patch.object(migrations.Path,'glob',return_value=[sql]):
                with self.assertRaises(sqlite3.OperationalError):migrate(empty)
            self.assertFalse(empty.execute("SELECT 1 FROM sqlite_master WHERE name='partial'").fetchone())
            self.assertEqual(empty.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0],0)
        finally:empty.close()

    def test_pdf_uses_same_review_and_leaves_old_queue_without_reupload(self):
        import fitz
        from webapp.services.hr_workflow import pending_pdfs
        path=self.root/'old-outlook.pdf'
        pdf=fitz.open();page=pdf.new_page();page.insert_text((50,50),'Ausblick 2025 Personalnummer 111113');pdf.save(path);pdf.close()
        with self.db:
            cur=self.db.execute('''INSERT INTO word_pdf_imports(original_filename,stored_path,sha256,parsed_json,created_at)
                VALUES ('old-outlook.pdf',?,'pdf-hash',?,'2026-10-27')''',
                (str(path),json.dumps({'data':{'document_kind':'outlook','pn':'111113'},'issues':[]})))
            import_id=cur.lastrowid
        self.assertEqual(len(pending_pdfs(self.db)),1)
        response=self.client.post(f'/arbeit/ziele/pdf/{import_id}',data={'csrf_token':self.csrf})
        self.assertEqual(response.status_code,302)
        source=self.db.execute('SELECT source_id FROM hr_goal_origins WHERE pdf_import_id=?',(import_id,)).fetchone()[0]
        self.assertEqual(len(pending_pdfs(self.db)),0)
        self.assertEqual(self.client.get(f'/word-pdf-imports/{import_id}').location,f'/arbeit/ziele/{source}')
        original=self.client.get(f'/arbeit/ziele/{source}/original')
        self.assertEqual(original.mimetype,'application/pdf');self.assertEqual(original.headers['X-Frame-Options'],'SAMEORIGIN');original.close()
        self.assertEqual(Path(review.get(self.db,source)['stored_path']),path)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],0)

    def test_corrected_return_requires_new_checked_document_and_external_effect_stays_open(self):
        source=self.stage();rev=self.confirm(source)
        def document(sha,old=None,handoff=''):
            with self.db:
                if old:self.db.execute('UPDATE official_documents SET is_current=0 WHERE id=?',(old,))
                return self.db.execute('''INSERT INTO official_documents(case_id,cycle_id,employee_pn,manager_pn,
                    document_kind,variant,original_filename,stored_path,sha256,received_at,handoff_status,handoff_at,replaces_document_id)
                    VALUES (?,?,'111113','111116','review','digital','review.pdf','preserved-original',?,'2026-10-27','staged',?,?)''',
                    (self.case_id,self.cycle_id,sha,handoff,old)).lastrowid
        old=document('old-return')
        def decision(outcome,**kwargs):
            evidence=followups.return_evidence(self.db,resolve(self.db,self.case_id))
            return followups.decide(self.db,rev,self.case_id,outcome=outcome,reason='Ziele im bestehenden Rückblick abgleichen',
                expected_evidence=review.digest(evidence),**kwargs)
        decision('request_correction',recipient_email='person-111116@example.invalid',requested_at='2026-10-27')
        with self.assertRaisesRegex(ValueError,'neuer'):decision('corrected',corrected_document_id=old)
        new=document('corrected-return',old)
        decision('corrected',corrected_document_id=new)
        self.assertEqual(goal_queries.source_state(self.db,source),'done')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],2)
        # A later, still unreviewed return must reopen a previously completed correction.
        self.pending_return()
        self.assertEqual(goal_queries.source_state(self.db,source),'followup')
        # A subsequent correction of an externally provided version cannot silently finish.
        with self.db:self.db.execute("UPDATE official_documents SET handoff_at='2026-10-27' WHERE id=?",(new,))
        decision('request_correction',recipient_email='person-111116@example.invalid',requested_at='2026-10-27')
        third=document('another-correction',new)
        with self.assertRaisesRegex(ValueError,'externe Korrektur'):decision('corrected',corrected_document_id=third)
        # A repeated request must retain external effects of replaced ancestors.
        decision('request_correction',recipient_email='person-111116@example.invalid',requested_at='2026-10-27')
        fourth=document('fourth-correction',third)
        with self.assertRaisesRegex(ValueError,'externe Korrektur'):decision('corrected',corrected_document_id=fourth)
        self.assertNotEqual(goal_queries.source_state(self.db,source),'done')

    def test_backup_restores_revisions_originals_outputs_and_dispatch_history(self):
        from webapp.services.operations import create_system_backup,restore_system_backup
        from webapp.db import connect_database
        storage=Path(self.app.config['STORAGE_ROOT']);folder=storage/'goal_workflow'/'originals';folder.mkdir(parents=True)
        original=word(folder/'goals.docx')
        source=review.stage(self.db,original,filename='goals.docx',batch_id=self.group,origin_key='backup')
        rev=self.confirm(source);_,fp,_=followups.inputs(self.db,rev,self.case_id,self.paths)
        output=followups.generate(self.db,[(rev,self.case_id,fp)],template_paths=self.paths,output_dir=storage/'goal_workflow'/'outputs')[0]['output_id']
        followups.approve(self.db,output,self.paths);groups,_=delivery.prepare(self.db,[output],self.paths)
        self.act(groups[0],adapter=FakeOutlook())
        backup=create_system_backup(self.db,database_path=Path(self.app.config['DATABASE']),storage_root=storage,
            dossier_root=Path(self.app.config['DOSSIER_HANDOFF_ROOT']),backup_root=Path(self.app.config['BACKUP_ROOT']))
        restored=self.root/'restored';restored.mkdir()
        restore_system_backup(backup['path'],database_path=restored/'db.sqlite3',storage_root=restored/'data',dossier_root=restored/'handoff')
        db=connect_database(restored/'db.sqlite3')
        try:
            for table in ('schema_migrations','hr_goal_sources','hr_goal_revisions','hr_goal_outputs','hr_goal_dispatches','hr_goal_events'):
                self.assertEqual([tuple(r) for r in self.db.execute('SELECT * FROM '+table)],
                                 [tuple(r) for r in db.execute('SELECT * FROM '+table)],table)
            for file in storage.rglob('*'):
                if file.is_file():self.assertEqual(file.read_bytes(),(restored/'data'/file.relative_to(storage)).read_bytes())
        finally:db.close()


if __name__=='__main__':unittest.main()
