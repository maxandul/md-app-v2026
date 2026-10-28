"""Separated responsibility across the operational Word workflow (stage C)."""
import json
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
from tests import test_goal_workflow as fixtures
from tests.test_word_dispatch import FakeOutlook
from tests import test_word_pdf_imports as pdf_fixtures
sample_pdf=pdf_fixtures.sample_pdf
from webapp.db import init_db
from webapp.services import part_responsibilities as parts,part_queries,word_dispatch,person_corrections,reminders
from webapp.services.word_packages import create_word_package
from webapp.services.word_pdf_imports import stage_pdf,confirm_import,matching_cases
from webapp.services.deadlines import extend_deadlines


class PartConsumersTest(unittest.TestCase):
    setUp=fixtures.GoalWorkflowTest.setUp
    tearDown=fixtures.GoalWorkflowTest.tearDown
    pending_return=fixtures.GoalWorkflowTest.pending_return
    stage=fixtures.GoalWorkflowTest.stage
    confirm=fixtures.GoalWorkflowTest.confirm

    def assign(self,kind,manager='111114',**updates):
        current=parts.resolve(self.db,self.case_id,kind)
        values=dict(kind=kind,manager_pn=manager,form_org_source='manager',period_start=current['period_start'],
                    period_end=current['period_end'],expected_revision=current['responsibility_revision'],reason='Vertretung für diesen Gesprächsteil bestätigt')
        values.update(updates)
        parts.assign(self.db,self.case_id,**values)
        return parts.resolve(self.db,self.case_id,kind)

    def word(self,manager,**kwargs):
        return create_word_package(self.db,cycle_id=self.cycle_id,manager_pn=manager,template_paths=self.paths,
                                   output_dir=self.root/'parts-word',**kwargs)

    def groups(self):
        case=person_corrections.person(self.db,self.case_id,self.cycle_id)
        return person_corrections.prepare_groups(self.db,case=case,kinds=['review','outlook'],template_paths=self.paths,output_dir=self.root/'corrections')

    def act(self,correction,adapter):
        person_corrections.act(self.db,correction_id=correction,action='draft',template_paths=self.paths,
            sender_email='hr@example.invalid',subject='Neue Formulare',body='Bitte prüfen',adapter=adapter)

    def test_independent_assignment_period_org_history_and_restart(self):
        old=parts.resolve(self.db,self.case_id,'review');case=dict(self.db.execute('SELECT * FROM dialog_cases WHERE case_id=?',(self.case_id,)).fetchone())
        new=self.assign('outlook',period_start='2026-09-01',period_end='2027-08-31')
        self.assertEqual(parts.resolve(self.db,self.case_id,'review'),old)
        self.assertEqual(case,dict(self.db.execute('SELECT * FROM dialog_cases WHERE case_id=?',(self.case_id,)).fetchone()))
        with self.db:self.db.execute("UPDATE employees SET org_unit='Neue SAP-OE' WHERE pn='111114'")
        init_db(self.db)
        self.assertEqual(parts.resolve(self.db,self.case_id,'outlook')['form_org_unit'],new['form_org_unit'])
        from webapp.services.cycles import synchronize_cycle_with_import
        import_id=self.db.execute('SELECT sap_import_id FROM cycles WHERE id=?',(self.cycle_id,)).fetchone()[0]
        synchronize_cycle_with_import(self.db,cycle_id=self.cycle_id,sap_import_id=import_id)
        self.assertEqual(parts.resolve(self.db,self.case_id,'outlook')['manager_pn'],'111114')
        self.assertEqual(parts.resolve(self.db,self.case_id,'outlook')['form_org_unit'],new['form_org_unit'])
        with self.assertRaisesRegex(ValueError,'inzwischen'):self.assign('outlook',expected_revision=0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM hr_goal_events WHERE action='responsibility_changed'").fetchone()[0],1)
        with self.db:self.db.execute("UPDATE employees SET entry_date='2028-01-01' WHERE pn='111113'")
        self.assertEqual(parts.resolve(self.db,self.case_id,'outlook')['period_end'],'2027-08-31')

    def test_word_groups_only_assigned_parts_and_actual_fields(self):
        self.assign('outlook',period_start='2026-09-01',period_end='2027-08-31')
        old_path,old=self.word('111116',case_id=self.case_id)
        new_path,new=self.word('111114',case_id=self.case_id)
        self.assertEqual([d['kind'] for d in old['documents']],['review'])
        self.assertEqual([d['kind'] for d in new['documents']],['outlook'])
        self.assertEqual(new['documents'][0]['period_start'],'2026-09-01')
        self.assertEqual(new['documents'][0]['responsibility']['manager_pn'],'111114')
        self.assertFalse(any(a['kind']=='feedback' for a in new['attachments']))
        with ZipFile(new_path) as outer:
            import io
            with ZipFile(io.BytesIO(outer.read(new['documents'][0]['filename']))) as word:
                text=word.read('word/document.xml').decode()
        self.assertIn('111114',text);self.assertIn('01.09.2026',text)
        with self.assertRaises(ValueError):self.word('111116',case_id=self.case_id,document_kinds=['outlook'])

    def test_regular_package_accepts_manager_without_original_case(self):
        self.assign('outlook')
        _,result=word_dispatch.prepare_word_batch(self.db,cycle_id=self.cycle_id,manager_pns=['111114'],template_paths=self.paths,output_dir=self.root/'dispatch')
        package=result['packages'][0]
        self.assertEqual([d['kind'] for d in package['manifest']['documents']],['outlook'])
        fake=FakeOutlook()
        result=word_dispatch.dispatch_word_packages(self.db,cycle_id=self.cycle_id,package_ids=[package['id']],template_paths=self.paths,sender_email='hr@example.invalid',adapter=fake)
        self.assertEqual(result['created'],1)
        self.assertEqual(fake.calls[0]['recipient_email'],parts.resolve(self.db,self.case_id,'outlook')['recipient_email'])

    def test_person_selection_creates_two_independent_recipient_outputs(self):
        self.assign('outlook');ids,errors=self.groups()
        self.assertEqual(len(ids),2);self.assertFalse(errors)
        fake=FakeOutlook()
        for correction in ids:self.act(correction,fake)
        self.assertEqual(len(fake.calls),2)
        self.assertEqual(len({c['recipient_email'] for c in fake.calls}),2)

    def test_partial_person_failure_preserves_other_recipient(self):
        self.assign('outlook')
        original=person_corrections.create_word_package
        def render(*args,**kwargs):
            if kwargs['manager_pn']=='111114':raise ValueError('Testfehler Ausblick')
            return original(*args,**kwargs)
        with patch('webapp.services.person_corrections.create_word_package',side_effect=render):ids,errors=self.groups()
        self.assertEqual(len(ids),1);self.assertEqual(len(errors),1)
        self.assertTrue(Path(self.db.execute('SELECT stored_path FROM word_person_corrections WHERE id=?',(ids[0],)).fetchone()[0]).is_file())

    def test_old_prepared_output_becomes_stale_but_keeps_file(self):
        ids,_=self.groups();row=self.db.execute('SELECT * FROM word_person_corrections WHERE id=?',(ids[0],)).fetchone()
        original=Path(row['stored_path']).read_bytes();self.assign('outlook')
        with self.assertRaisesRegex(ValueError,'Zuständigkeit'):self.act(ids[0],FakeOutlook())
        self.assertEqual(Path(row['stored_path']).read_bytes(),original)

    def test_open_old_recipient_blocks_duplicate_part_after_reassignment(self):
        ids,_=self.groups();fake=FakeOutlook();self.act(ids[0],fake)
        self.assign('outlook');new,_=self.groups()
        for correction in new:
            with self.assertRaisesRegex(ValueError,'Outlook'):self.act(correction,fake)
        self.assertEqual(len(fake.calls),1)
        person_corrections.act(self.db,correction_id=ids[0],action='sent_confirmed',template_paths=self.paths,sender_email='',checked=True)
        self.assertEqual(self.db.execute('SELECT status FROM word_person_corrections WHERE id=?',(ids[0],)).fetchone()[0],'sent_confirmed')

    def test_return_matching_uses_assigned_manager_year_and_keeps_other_part(self):
        self.assign('outlook',period_start='2027-01-01',period_end='2027-12-31')
        path=sample_pdf(self.root/'return.pdf',kind='outlook',year=2027)
        incoming=stage_pdf(self.db,path,filename='return.pdf',directory=self.root/'intake')[0]
        reviewed=pdf_fixtures.WordPdfImportsTest.reviewed(self,incoming);reviewed['data']['manager_pn']='111114'
        matches=matching_cases(self.db,reviewed['data'])
        self.assertIn(self.case_id,[c['case_id'] for c in matches])
        self.assertEqual(next(c for c in matches if c['case_id']==self.case_id)['manager_pn'],'111114')
        document=confirm_import(self.db,incoming,reviewed=reviewed,assignment='1',case_id=self.case_id,historical=False,reason='Original und tatsächliche Zuständigkeit geprüft')
        self.assertEqual(self.db.execute('SELECT manager_pn FROM official_documents WHERE id=?',(document,)).fetchone()[0],'111114')
        self.assertTrue(parts.resolve(self.db,self.case_id,'review')['required'])
        self.assign('outlook',manager='111116')
        self.assertEqual(self.db.execute('SELECT manager_pn FROM official_documents WHERE id=?',(document,)).fetchone()[0],'111114')

    def test_return_cannot_waive_other_managers_part(self):
        self.assign('outlook');path=sample_pdf(self.root/'return.pdf',kind='outlook',year=2026)
        incoming=stage_pdf(self.db,path,filename='return.pdf',directory=self.root/'intake')[0]
        reviewed=pdf_fixtures.WordPdfImportsTest.reviewed(self,incoming);reviewed['scope']='outlook_only'
        with self.assertRaisesRegex(ValueError,'gesamte MD-Umfang'):
            confirm_import(self.db,incoming,reviewed=reviewed,assignment='1',case_id=self.case_id,historical=False,reason='Geprüft')
        self.assertTrue(parts.resolve(self.db,self.case_id,'review')['required'])

    def test_deadlines_and_reminders_follow_each_part(self):
        new=self.assign('outlook');old=parts.resolve(self.db,self.case_id)
        extend_deadlines(self.db,cycle_id=self.cycle_id,scope='manager',manager_pn='111114',document_kind='outlook',new_due_date='2026-03-10',reason='Für zugewiesenen Ausblick vereinbart')
        self.assertEqual(parts.resolve(self.db,self.case_id)['due_date'],old['due_date'])
        candidates={r['manager_pn']:r for r in reminders.reminder_candidates(self.db,cycle_id=self.cycle_id,today=date(2027,1,1))}
        self.assertIn(new['obligation_id'],candidates['111114']['obligation_ids'])
        self.assertNotIn(new['obligation_id'],candidates['111116']['obligation_ids'])
        self.assertIn(old['obligation_id'],candidates['111116']['obligation_ids'])
        self.pending_return()
        self.assertTrue(all(not r['ready'] for r in reminders.reminder_candidates(self.db,cycle_id=self.cycle_id,today=date(2027,1,1))))

    def test_old_reminder_draft_keeps_history_and_blocks_new_manager_until_resolved(self):
        self.assign('outlook')
        reminders.create_reminder_drafts(self.db,cycle_id=self.cycle_id,manager_pns=['111114'],sender_email='hr@example.invalid',adapter=FakeOutlook(),today=date(2027,1,1))
        old=dict(self.db.execute("SELECT * FROM reminders WHERE manager_pn='111114'").fetchone())
        self.assign('outlook',manager='111116')
        candidates={r['manager_pn']:r for r in reminders.reminder_candidates(self.db,cycle_id=self.cycle_id,today=date(2027,1,1))}
        self.assertFalse(candidates['111116']['ready']);self.assertIn(old['id'],candidates['111116']['open_reminder_ids'])
        reminders.resolve_reminder(self.db,old['id'],outcome='cancelled',reason='Alten Entwurf in Outlook geprüft und gelöscht',checked=True)
        self.assertEqual(old,dict(self.db.execute('SELECT * FROM reminders WHERE id=?',(old['id'],)).fetchone()))
        self.assertTrue(next(r for r in reminders.reminder_candidates(self.db,cycle_id=self.cycle_id,today=date(2027,1,1)) if r['manager_pn']=='111116')['ready'])

    def test_routes_show_both_parts_preserve_filters_and_reject_stale_or_no_csrf(self):
        self.assign('outlook')
        for url in ['/arbeit/dialogteile',f'/cycles/{self.cycle_id}/cases/{self.case_id}',f'/cycles/{self.cycle_id}/managers/111114']:
            self.assertEqual(self.client.get(url).status_code,200,url)
        url=f'/arbeit/dialogteile/{self.case_id}/outlook'
        self.assertEqual(self.client.post(url).status_code,400)
        response=self.client.post(url,data={'csrf_token':self.csrf,'revision':'0','manager_pn':'111116','period_start':'2026-01-01','period_end':'2026-12-31','form_org_source':'employee','reason':'Stale browser','back':'/arbeit/dialogteile?q=111113&page=2'},follow_redirects=True)
        self.assertIn('inzwischen',response.text);self.assertEqual(parts.resolve(self.db,self.case_id,'outlook')['manager_pn'],'111114')
        self.assertIn('q=111113',response.text)


    def test_word_dispatch_allows_managers_with_split_responsibilities(self):
        from html.parser import HTMLParser
        self.assign('outlook')
        class SelectionParser(HTMLParser):
            def __init__(self):
                super().__init__();self.managers={}
            def handle_starttag(self,tag,attrs):
                attrs=dict(attrs)
                if tag=='input' and attrs.get('name')=='manager_pn':
                    self.managers[attrs['value']]='disabled' not in attrs
        response=self.client.get('/versand',query_string={'cycle_id':self.cycle_id,'workflow':'workbook'})
        self.assertEqual(response.status_code,200)
        selection=SelectionParser();selection.feed(response.text)
        self.assertTrue(selection.managers.get('111114'))
        self.assertTrue(selection.managers.get('111116'))
        self.assertNotIn('HTML-Arbeitsmappe',response.text)

    def test_person_and_manager_search_find_assigned_part(self):
        new=self.assign('outlook',period_start='2027-01-01',period_end='2027-12-31')
        found=part_queries.listing(self.db,q='111113',manager='111114',year=2027)
        self.assertEqual(found['total'],1);self.assertEqual(found['rows'][0]['id'],new['obligation_id'])
        self.assertEqual(part_queries.listing(self.db,q='111113',manager='111116',kind='outlook')['total'],0)
        with self.db:
            self.db.execute("UPDATE dialog_cases SET period_start='2024-02-01',period_end='2024-10-31' WHERE case_id=?",(self.case_id,))
        old=part_queries.listing(self.db,q='111113',kind='review',year=2024)
        self.assertEqual(old['total'],1)
        self.assertEqual(old['rows'][0]['part']['period_end'],'2024-10-31')
        self.assertEqual(part_queries.listing(self.db,q='111113',kind='review',year=2025)['total'],0)
        self.assertEqual(part_queries.listing(self.db,q='111113',kind='outlook',year=2027)['total'],1)

    def test_regular_word_path_cannot_bypass_goal_return_guard(self):
        source=self.stage();self.confirm(source);self.pending_return()
        with self.assertRaisesRegex(ValueError,'Korrekturbedarf'):self.word('111116',case_id=self.case_id,document_kinds=['review'])

    def test_new_migration_preserves_assignments_and_existing_reminder_history(self):
        import webapp.migrations as migrations
        from tests import test_word_packages as old_fixtures
        old=old_fixtures.WordPackagesTest();old.setUp()
        try:
            directory=Path(migrations.__file__).with_suffix('')
            with patch.object(migrations.Path,'glob',return_value=[directory/'001_hr_goals.sql',directory/'002_goal_withdrawals.sql']):migrations.migrate(old.db)
            parts.assign_review(old.db,old.case_id,manager_pn='111114',form_org_source='manager',period_start='2025-01-01',period_end='2025-12-31',expected_revision=0,reason='Bestehende A/B-Zuordnung')
            with old.db:
                reminder=old.db.execute("INSERT INTO reminders(cycle_id,manager_pn,sender_email,recipient_email,subject,body_html,status,created_at,updated_at) VALUES (?,'111116','hr@example.invalid','manager@example.invalid','Alte Erinnerung','Erhalten','draft_created','2026-10-27','2026-10-27')",(old.cycle_id,)).lastrowid
                obligation=parts.resolve(old.db,old.case_id)['obligation_id']
                old.db.execute('INSERT INTO reminder_obligations VALUES (?,?,?)',(reminder,obligation,'2026-01-31'))
            before={t:[tuple(r) for r in old.db.execute('SELECT * FROM '+t)] for t in ('hr_part_responsibilities','reminders','reminder_obligations','dialog_cases','document_obligations')}
            columns={t:','.join(r[1] for r in old.db.execute('PRAGMA table_info('+t+')')) for t in before}
            migrations.migrate(old.db);init_db(old.db)
            for table,rows in before.items():self.assertEqual(rows,[tuple(r) for r in old.db.execute('SELECT '+columns[table]+' FROM '+table)])
            self.assertEqual(old.db.execute('SELECT manager_pn FROM hr_resolved_obligations WHERE id=?',(obligation,)).fetchone()[0],'111114')
        finally:old.tearDown()


if __name__=='__main__':unittest.main()
