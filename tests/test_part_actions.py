"""Reviewed selection scope, concurrency and real mail boundaries on synthetic data."""
import unittest
from datetime import date
from unittest.mock import patch
from urllib.parse import urlsplit, parse_qs

from tests import test_goal_workflow as goals
from tests import test_part_consumers as consumers
from tests.test_word_dispatch import FakeOutlook
from webapp.services import part_actions as actions, part_queries


class PartActionsTest(unittest.TestCase):
    setUp = goals.GoalWorkflowTest.setUp
    tearDown = goals.GoalWorkflowTest.tearDown
    assign = consumers.PartConsumersTest.assign
    pending_return = goals.GoalWorkflowTest.pending_return
    today = date(2027, 1, 1)
    owner = 'test-owner'

    def filters(self, **updates):
        pn=self.db.execute('SELECT employee_pn FROM dialog_cases WHERE case_id=?',(self.case_id,)).fetchone()[0]
        return dict(q=pn,manager='',kind='',state='all',year=None,org_unit='',due='',page=1,page_size=25,**updates)

    def choose(self, ids=None):
        filters=self.filters()
        if ids is None:
            return actions.select(self.db,owner=self.owner,filters=filters,mode='all')
        return actions.select(self.db,owner=self.owner,filters=filters,checked=ids)

    def preview(self, chosen=None, action='deadline', **updates):
        chosen=chosen or self.choose()
        values=dict(owner=self.owner,selection_id=chosen['id'],revision=chosen['revision'],action=action,
                    new_due_date='2028-02-01',reason='Abgesprochene Verlängerung',sender_email='hr@example.invalid',today=self.today)
        values.update(updates)
        return actions.preview(self.db,**values)

    def execute(self,key,**updates):
        return actions.execute(self.db,key,owner=self.owner,sender_email='hr@example.invalid',today=self.today,**updates)

    def test_selection_is_owned_versioned_and_bound_to_filters(self):
        chosen=self.choose()
        with self.assertRaisesRegex(ValueError,'andere'):
            actions.selection(self.db,chosen['id'],'other')
        with self.assertRaisesRegex(ValueError,'Filter'):
            actions.selection(self.db,chosen['id'],self.owner,{**self.filters(),'q':'changed'})
        actions.select(self.db,owner=self.owner,filters=self.filters(),key=chosen['id'],revision=chosen['revision'],mode='clear')
        with self.assertRaisesRegex(ValueError,'anderen Fenster'):
            actions.select(self.db,owner=self.owner,filters=self.filters(),key=chosen['id'],revision=chosen['revision'],mode='all')
        self.assertEqual(actions.selection(self.db,chosen['id'],self.owner)['ids'],[])

    def test_expiry_and_forged_page_ids_are_rejected(self):
        chosen=self.choose()
        with self.db:self.db.execute('UPDATE hr_part_selections SET created_at=0 WHERE id=?',(chosen['id'],))
        with self.assertRaisesRegex(ValueError,'abgelaufen'):
            actions.selection(self.db,chosen['id'],self.owner)
        with self.assertRaisesRegex(ValueError,'Seitenauswahl'):
            self.choose([999999])

    def test_page_changes_and_all_filtered_selection_freeze_exact_ids(self):
        def clone(table,row,**updates):
            value=dict(row);value.pop('id',None);value.update(updates)
            return self.db.execute('INSERT INTO '+table+' ('+','.join(value)+') VALUES ('+','.join('?' for _ in value)+')',list(value.values())).lastrowid
        event=self.db.execute('SELECT * FROM dialog_events WHERE legacy_case_id=?',(self.case_id,)).fetchone()
        obligation=self.db.execute('SELECT * FROM document_obligations WHERE dialog_event_id=? LIMIT 1',(event['id'],)).fetchone()
        with self.db:
            for i in range(60):
                eid=clone('dialog_events',event,event_id='page-test-'+str(i),legacy_case_id=None,sap_leading=0)
                clone('document_obligations',obligation,obligation_id='page-part-'+str(i),dialog_event_id=eid)
        filters=self.filters()
        first=part_queries.listing(self.db,**filters)['rows']
        chosen=actions.select(self.db,owner=self.owner,filters=filters,checked=[first[0]['id']])
        page2={**filters,'page':2}
        second=part_queries.listing(self.db,**page2)['rows']
        chosen=actions.select(self.db,owner=self.owner,filters=page2,key=chosen['id'],revision=chosen['revision'],checked=[second[0]['id']])
        self.assertEqual(set(chosen['ids']),{first[0]['id'],second[0]['id']})
        chosen=actions.select(self.db,owner=self.owner,filters=filters,key=chosen['id'],revision=chosen['revision'],mode='all')
        self.assertEqual(len(chosen['ids']),62)
        with self.db:
            eid=clone('dialog_events',event,event_id='later-event',legacy_case_id=None,sap_leading=0)
            later=clone('document_obligations',obligation,obligation_id='later-part',dialog_event_id=eid)
        self.assertNotIn(later,actions.selection(self.db,chosen['id'],self.owner)['ids'])

    def test_deadlines_only_change_reviewed_eligible_subset_and_are_idempotent(self):
        chosen=self.choose()
        ids=chosen['ids']
        with self.db:self.db.execute("UPDATE document_obligations SET status='complete' WHERE id=?",(ids[1],))
        key=self.preview(chosen)
        before={r['id']:r['due_date'] for r in self.db.execute('SELECT * FROM document_obligations')}
        self.assertEqual(actions.view(self.db,key,self.owner)['plan']['eligible'],[ids[0]])
        result=self.execute(key)
        self.assertEqual(result['changed'],1)
        after={r['id']:r['due_date'] for r in self.db.execute('SELECT * FROM document_obligations')}
        self.assertEqual([i for i in before if before[i]!=after[i]],[ids[0]])
        audit=self.db.execute('SELECT * FROM deadline_changes WHERE obligation_id=?',(ids[0],)).fetchone()
        self.assertEqual(audit['old_due_date'],before[ids[0]])
        self.assertEqual(audit['reason'],'Abgesprochene Verlängerung')
        with self.assertRaisesRegex(ValueError,'bereits gestartet'):self.execute(key)

    def test_changed_responsibility_return_or_date_prevents_execution(self):
        for column,value in [('due_date','2029-01-01'),('status','received')]:
            with self.subTest(column=column):
                chosen=self.choose();key=self.preview(chosen)
                old=self.db.execute('SELECT '+column+' FROM document_obligations WHERE id=?',(chosen['ids'][0],)).fetchone()[0]
                with self.db:self.db.execute('UPDATE document_obligations SET '+column+'=? WHERE id=?',(value,chosen['ids'][0]))
                with self.assertRaisesRegex(ValueError,'geändert'):self.execute(key)
                self.assertEqual(actions.view(self.db,key,self.owner)['status'],'preview')
                with self.db:self.db.execute('UPDATE document_obligations SET '+column+'=? WHERE id=?',(old,chosen['ids'][0]))
        key=self.preview()
        self.assign('outlook')
        with self.assertRaisesRegex(ValueError,'geändert'):self.execute(key)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM deadline_changes').fetchone()[0],0)

    def test_deadline_failure_rolls_back_changes_and_batch_consumption(self):
        key=self.preview()
        with self.db:self.db.execute("CREATE TRIGGER reject_bulk_audit BEFORE INSERT ON deadline_changes BEGIN SELECT RAISE(ABORT,'test failure'); END")
        before=[tuple(r) for r in self.db.execute('SELECT * FROM document_obligations')]
        with self.assertRaises(Exception):self.execute(key)
        self.assertEqual(before,[tuple(r) for r in self.db.execute('SELECT * FROM document_obligations')])
        self.assertEqual(actions.view(self.db,key,self.owner)['status'],'preview')

    def test_reminder_mentions_only_selected_part_and_tracks_actual_manager(self):
        self.assign('outlook')
        ids=self.choose()['ids']
        chosen=self.choose([ids[0]])
        key=self.preview(chosen,action='reminder')
        fake=FakeOutlook()
        self.execute(key,adapter=fake)
        self.assertEqual(len(fake.calls),1)
        row=self.db.execute('SELECT * FROM reminders ORDER BY id DESC LIMIT 1').fetchone()
        self.assertEqual([r[0] for r in self.db.execute('SELECT obligation_id FROM reminder_obligations WHERE reminder_id=?',(row['id'],))],chosen['ids'])
        self.assertEqual(row['status'],'draft_created')
        expected=self.db.execute('SELECT manager_pn FROM hr_resolved_obligations WHERE id=?',(ids[0],)).fetchone()[0]
        self.assertEqual(row['manager_pn'],expected)
        self.assertEqual(len(actions.view(self.db,key,self.owner)['reminders']),1)
        with self.assertRaises(ValueError):self.execute(key,adapter=fake)
        self.assertEqual(len(fake.calls),1)

    def test_reminder_subset_does_not_expand_to_other_people_of_same_manager(self):
        chosen=self.choose()
        key=self.preview(chosen,action='reminder')
        fake=FakeOutlook();self.execute(key,adapter=fake)
        mapped={r[0] for r in self.db.execute('SELECT obligation_id FROM reminder_obligations')}
        self.assertEqual(mapped,set(chosen['ids']))
        self.assertEqual(len(fake.calls),1)

    def test_pending_input_and_existing_open_draft_have_explicit_exclusions(self):
        self.pending_return()
        key=self.preview(action='reminder')
        value=actions.view(self.db,key,self.owner)['plan']
        self.assertFalse(value['eligible'])
        self.assertTrue(all('PDF-Eingang' in r['exclusion'] for r in value['rows']))
        fake=FakeOutlook()
        with self.assertRaisesRegex(ValueError,'keine Aktion'):self.execute(key,adapter=fake)
        self.assertFalse(fake.calls)

    def test_late_input_blocks_a_previously_reviewed_reminder(self):
        key=self.preview(action='reminder')
        self.pending_return()
        fake=FakeOutlook()
        with self.assertRaisesRegex(ValueError,'geändert'):self.execute(key,adapter=fake)
        self.assertFalse(fake.calls)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM reminders').fetchone()[0],0)

    def test_received_without_dispatch_is_not_requested_again(self):
        chosen=self.choose()
        with self.db:self.db.execute("UPDATE document_obligations SET status='received' WHERE id=?",(chosen['ids'][0],))
        key=self.preview(chosen,action='reminder')
        plan=actions.view(self.db,key,self.owner)['plan']
        self.assertNotIn(chosen['ids'][0],plan['eligible'])
        self.assertTrue(next(r for r in plan['rows'] if r['id']==chosen['ids'][0])['exclusion'])
        fake=FakeOutlook();self.execute(key,adapter=fake)
        self.assertEqual({r[0] for r in self.db.execute('SELECT obligation_id FROM reminder_obligations')},set(plan['eligible']))

    def test_failed_outlook_is_reserved_and_requires_resolution(self):
        key=self.preview(action='reminder');fake=FakeOutlook(fail=True)
        result=self.execute(key,adapter=fake)
        self.assertEqual(result['failed'],1)
        view=actions.view(self.db,key,self.owner)
        self.assertEqual(view['status'],'complete')
        self.assertEqual(view['reminders'][0]['status'],'failed')
        retry=self.preview(action='reminder')
        plan=actions.view(self.db,retry,self.owner)['plan']
        self.assertFalse(plan['eligible'])
        self.assertIn('Outlook-Stand',plan['rows'][0]['exclusion'])

    def test_routes_preserve_scope_require_csrf_and_checked_preview(self):
        path='/arbeit/dialogteile'
        self.assertEqual(self.client.post(path+'/auswahl').status_code,400)
        response=self.client.post(path+'/auswahl',data={**self.filters(),'csrf_token':self.csrf,'mode':'all'})
        query=parse_qs(urlsplit(response.location).query)
        key=query['selection'][0]
        page=self.client.get(response.location)
        self.assertEqual(page.status_code,200)
        self.assertIn('2 Gesprächsteile gespeichert ausgewählt',page.text)
        with self.client.session_transaction() as session:owner=session['part_selection_owner']
        chosen=actions.selection(self.db,key,owner)
        response=self.client.post(path+'/vorschau',data={'csrf_token':self.csrf,'selection':key,'revision':chosen['revision'],
            'action':'deadline','new_due_date':'2028-01-01','reason':'Freigabe eingeholt','back':response.location})
        preview=self.client.get(response.location)
        self.assertEqual(preview.status_code,200)
        self.assertIn('2 berücksichtigt',preview.text)
        unchecked=self.client.post(response.location,data={'csrf_token':self.csrf},follow_redirects=True)
        self.assertIn('ausdrücklich',unchecked.text)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM deadline_changes').fetchone()[0],0)
        checked=self.client.post(response.location,data={'csrf_token':self.csrf,'checked':'yes'},follow_redirects=True)
        self.assertIn('2 Frist(en) geändert',checked.text)

    def test_combined_page_selection_and_preview_uses_unsaved_checkboxes(self):
        row=part_queries.listing(self.db,**self.filters())['rows'][0]
        response=self.client.post('/arbeit/dialogteile/auswahl',data={**self.filters(),'csrf_token':self.csrf,
            'mode':'preview','part':row['id'],'action':'deadline','new_due_date':'2028-01-01','reason':'Vereinbart'},follow_redirects=True)
        self.assertEqual(response.status_code,200)
        self.assertIn('1 ausgewählte Gesprächsteile',response.text)
        self.assertIn('1 berücksichtigt',response.text)

    def test_different_browser_cannot_open_preview_and_sandbox_cannot_create_mail(self):
        response=self.client.post('/arbeit/dialogteile/auswahl',data={**self.filters(),'csrf_token':self.csrf,
            'mode':'preview','action':'reminder','part':self.choose()['ids'][0]})
        self.assertEqual(self.app.test_client().get(response.location).status_code,404)
        self.app.config['HR_REVIEW_SANDBOX']=True
        with patch('webapp.services.reminders.OutlookDraftAdapter') as adapter:
            self.assertEqual(self.client.post(response.location,data={'csrf_token':self.csrf,'checked':'yes'}).status_code,403)
            adapter.assert_not_called()

    def test_two_responsibilities_create_two_exact_recipient_groups(self):
        self.assign('outlook')
        key=self.preview(action='reminder')
        fake=FakeOutlook();result=self.execute(key,adapter=fake)
        self.assertEqual(result['created'],2)
        self.assertEqual(len(fake.calls),2)
        rows=actions.view(self.db,key,self.owner)['reminders']
        self.assertEqual({r['manager_pn'] for r in rows},{'111114','111116'})
        self.assertEqual([r[0] for r in self.db.execute('SELECT COUNT(*) FROM reminder_obligations GROUP BY reminder_id')],[1,1])

    def test_partial_result_preserves_completed_group_when_next_recipient_changes(self):
        self.assign('outlook')
        key=self.preview(action='reminder')
        db=self.db
        class ChangingAdapter(FakeOutlook):
            def create_encrypted_draft(self,**message):
                with db:db.execute("UPDATE employees SET email='changed@example.invalid' WHERE pn='111116'")
                return super().create_encrypted_draft(**message)
        fake=ChangingAdapter();result=self.execute(key,adapter=fake)
        self.assertEqual(len(fake.calls),1)
        self.assertEqual(result['created'],1)
        self.assertTrue(result['errors'])
        view=actions.view(self.db,key,self.owner)
        self.assertEqual(view['reminders'][0]['status'],'draft_created')
        self.assertEqual(view['status'],'complete')
