"""Shipping guidance follows existing records and validates again before Outlook."""
import unittest
from unittest.mock import patch
from tests import test_goal_workflow as fixtures, test_part_consumers
from tests.test_word_dispatch import FakeOutlook
from webapp.services import dispatch_views, word_dispatch, person_corrections


class DispatchViewsTest(unittest.TestCase):
    def setUp(self):
        fixtures.GoalWorkflowTest.setUp(self)
        self.app.config['HR_MAILBOX_EMAIL']='hr@example.invalid'
    tearDown=fixtures.GoalWorkflowTest.tearDown
    stage=fixtures.GoalWorkflowTest.stage
    confirm=fixtures.GoalWorkflowTest.confirm
    generate=fixtures.GoalWorkflowTest.generate
    ready=fixtures.GoalWorkflowTest.ready
    assign=test_part_consumers.PartConsumersTest.assign

    def prepare(self,manager='111116'):
        _,batch=word_dispatch.prepare_word_batch(self.db,cycle_id=self.cycle_id,manager_pns=[manager],
            template_paths=self.paths,output_dir=self.root/'dispatch')
        return batch['packages'][0]['id']

    def post(self,id,action,**values):
        return self.client.post(f'/versand/pakete/{id}',data=dict(csrf_token=self.csrf,checked='yes',action=action,**values))

    def test_overview_and_detail_are_read_only_and_names_are_primary(self):
        id=self.prepare();before=self.db.total_changes
        html=self.client.get('/versand?view=overview').text
        self.assertIn('Dateien erstellt',html);self.assertIn(f'/versand/pakete/{id}',html)
        detail=self.client.get(f'/versand/pakete/{id}')
        self.assertEqual(detail.status_code,200)
        self.assertIn('Outlook-Entwurf für diese Ausgabe erstellen',detail.text)
        self.assertIn('Rufname3 Nachname3',detail.text)
        self.assertEqual(self.db.total_changes,before)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_mail_deliveries').fetchone()[0],0)

    def test_draft_and_sent_are_separate_and_only_exact_package_is_dispatched(self):
        id=self.prepare();fake=FakeOutlook()
        with patch('webapp.services.word_dispatch.OutlookDraftAdapter',return_value=fake):
            response=self.post(id,'draft',subject_template='Hallo {manager_first_name}',body_template='Nachricht',package_id='999')
        self.assertEqual(response.status_code,302)
        self.assertEqual(len(fake.calls),1)
        self.assertEqual(dispatch_views.listing(self.db)['rows'][0]['status'],'draft_created')
        self.assertIn('Tatsächlichen Outlook-Stand dokumentieren',self.client.get(response.location).text)
        self.post(id,'sent_confirmed')
        self.assertEqual(dispatch_views.listing(self.db)['total'],0)
        self.assertEqual(dispatch_views.listing(self.db,state='sent')['rows'][0]['id'],id)

    def test_csrf_explicit_check_and_action_whitelist(self):
        id=self.prepare()
        self.assertEqual(self.client.post(f'/versand/pakete/{id}',data={'action':'draft','checked':'yes'}).status_code,400)
        self.client.post(f'/versand/pakete/{id}',data={'csrf_token':self.csrf,'action':'draft'})
        self.post(id,'send')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_mail_deliveries').fetchone()[0],0)

    def test_new_output_preserves_sent_evidence_and_discard_restores_old(self):
        old=self.prepare()
        word_dispatch.dispatch_word_packages(self.db,cycle_id=self.cycle_id,package_ids=[old],template_paths=self.paths,
            sender_email='hr@example.invalid',adapter=FakeOutlook(),delivery_mode='send')
        new=self.prepare();row=dispatch_views.listing(self.db)['rows'][0]
        self.assertEqual((row['id'],row['last_sent_id']),(new,old))
        self.assertIn('früherer Versand ist bereits bestätigt',self.client.get(f'/versand/pakete/{new}').text)
        self.post(new,'discard')
        self.assertEqual(dispatch_views.listing(self.db)['total'],0)
        self.assertIn('Vorgang verworfen',self.client.get(f'/versand/pakete/{new}').text)
        history=dispatch_views.listing(self.db,state='all')['rows']
        self.assertEqual(len(history),2)
        self.assertEqual(next(x['status'] for x in history if x['id']==old),'sent_confirmed')

    def test_stale_file_and_source_changes_cannot_create_draft(self):
        id=self.prepare()
        self.db.execute("UPDATE employees SET first_name='Neuer Vorname' WHERE pn='111113'");self.db.commit()
        fake=FakeOutlook()
        with patch('webapp.services.word_dispatch.OutlookDraftAdapter',return_value=fake):self.post(id,'draft')
        self.assertFalse(fake.calls)
        self.assertNotIn('Outlook-Entwurf für diese Ausgabe erstellen',self.client.get(f'/versand/pakete/{id}').text)

    def test_failure_and_interrupted_states_appear_in_clarification_filter(self):
        id=self.prepare()
        word_dispatch.dispatch_word_packages(self.db,cycle_id=self.cycle_id,package_ids=[id],template_paths=self.paths,
            sender_email='hr@example.invalid',adapter=FakeOutlook(fail=True),delivery_mode='draft')
        self.assertEqual(dispatch_views.listing(self.db,state='clarify')['rows'][0]['status'],'failed')
        self.db.execute("UPDATE word_mail_deliveries SET status='processing' WHERE package_id=?",(id,));self.db.commit()
        self.assertIn('Unterbrochenen Vorgang klären',self.client.get(f'/versand/pakete/{id}').text)

    def test_union_uses_stored_part_recipient_and_goal_dispatch(self):
        self.assign('outlook')
        case=person_corrections.person(self.db,self.case_id,self.cycle_id)
        ids,errors=person_corrections.prepare_groups(self.db,case=case,kinds=['outlook'],template_paths=self.paths,output_dir=self.root/'corrections')
        self.assertFalse(errors)
        _,_,_,group=self.ready()
        rows=dispatch_views.listing(self.db)['rows'];self.assertEqual({r['kind'] for r in rows},{'person','goals'})
        person=next(r for r in rows if r['kind']=='person')
        self.assertEqual(person['manager_pn'],'111114')
        goal=next(r for r in rows if r['kind']=='goals');self.assertEqual(goal['id'],group)
        self.assertEqual(dispatch_views.listing(self.db,year=2025)['total'],2)
        self.assertEqual(dispatch_views.listing(self.db,year=1999)['total'],0)
        self.assertEqual(dispatch_views.listing(self.db,kind='person')['total'],1)
        self.assertEqual(self.client.get('/arbeit/ziele/versand').status_code,200)
        self.assertEqual(self.client.get(f'/arbeit/ziele/versand/{group}').status_code,200)

    def test_filters_pagination_and_back_context(self):
        id=self.prepare()
        self.assertEqual(dispatch_views.listing(self.db,q="' OR 1=1 --")['total'],0)
        for i in range(27):
            self.db.execute('''INSERT INTO word_dispatch_packages(export_id,cycle_id,manager_pn,stored_path,sha256,source_fingerprint,manifest_json,created_at,discarded_at)
                SELECT export_id||?,cycle_id,manager_pn,stored_path,sha256,source_fingerprint,manifest_json,created_at,'test-history' FROM word_dispatch_packages WHERE id=?''',(str(i),id))
        self.db.commit()
        page=dispatch_views.listing(self.db,state='all',page_number=2)
        self.assertEqual((page['total'],len(page['rows']),page['pages']),(28,3,2))
        back='/versand?view=overview&state=all&q=Test'
        html=self.client.get(f'/versand/pakete/{id}',query_string={'back':back}).text
        self.assertIn('/versand?view=overview&amp;state=all&amp;q=Test',html)
        html=self.client.get(f'/versand/pakete/{id}?back=https://example.invalid').text
        self.assertNotIn('href="https://example.invalid',html)

    def test_reassigned_only_manager_can_preview_own_message(self):
        self.assign('outlook')
        id=self.prepare('111114')
        self.assertEqual(self.client.get(f'/versand/pakete/{id}').status_code,200)
        response=self.client.post(f'/cycles/{self.cycle_id}/word-mail-preview',data={
            'csrf_token':self.csrf,'preview_manager_pn':'111114','subject_template':'Hallo','body_template':'Text'})
        self.assertEqual(response.status_code,200)

    def test_sandbox_blocks_outlook_and_foreign_package_is_404(self):
        id=self.prepare();self.app.config['HR_REVIEW_SANDBOX']=True
        self.assertEqual(self.post(id,'draft').status_code,403)
        self.assertEqual(self.client.get('/versand/pakete/99999').status_code,404)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_mail_deliveries').fetchone()[0],0)

    def test_changed_zip_and_superseded_output_cannot_be_dispatched(self):
        old=self.prepare();current=self.prepare();fake=FakeOutlook()
        path=self.db.execute('SELECT stored_path FROM word_dispatch_packages WHERE id=?',(current,)).fetchone()[0]
        from pathlib import Path
        Path(path).write_bytes(b'Changed after file review')
        with patch('webapp.services.word_dispatch.OutlookDraftAdapter',return_value=fake):
            self.post(old,'draft');self.post(current,'draft')
        self.assertFalse(fake.calls)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_mail_deliveries').fetchone()[0],0)

    def test_goal_and_person_details_keep_filtered_shipping_back_link(self):
        _,_,_,group=self.ready()
        back='/versand?view=overview&state=all&q=Rufname'
        html=self.client.get(f'/arbeit/ziele/versand/{group}',query_string={'back':back}).text
        self.assertIn('/versand?view=overview&amp;state=all&amp;q=Rufname',html)
        url=f'/cycles/{self.cycle_id}/cases/{self.case_id}/word-correction'
        html=self.client.get(url,query_string={'back':back}).text
        self.assertIn('name="back" value="/versand?view=overview&amp;state=all&amp;q=Rufname"',html)
        html=self.client.get(url,query_string={'back':'//example.invalid'}).text
        self.assertNotIn('href="//example.invalid',html)
