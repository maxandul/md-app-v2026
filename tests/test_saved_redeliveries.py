"""Additional resend sources keep the exact saved archive and all original evidence."""
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch
from tests import test_goal_workflow as fixtures,test_part_consumers as part_fixtures
from tests.test_word_dispatch import FakeOutlook
from webapp.services import saved_redeliveries as saved,person_corrections as person,goal_delivery as delivery,goal_followups


class SavedRedeliveriesTest(unittest.TestCase):
    setUp=fixtures.GoalWorkflowTest.setUp
    tearDown=fixtures.GoalWorkflowTest.tearDown
    stage=fixtures.GoalWorkflowTest.stage
    confirm=fixtures.GoalWorkflowTest.confirm
    generate=fixtures.GoalWorkflowTest.generate
    ready=fixtures.GoalWorkflowTest.ready
    act=fixtures.GoalWorkflowTest.act
    pending_return=fixtures.GoalWorkflowTest.pending_return
    assign=part_fixtures.PartConsumersTest.assign

    def sent_person(self,kinds=None):
        case=person.person(self.db,self.case_id,self.cycle_id)
        ids,errors=person.prepare_groups(self.db,case=case,kinds=kinds or ['review','outlook'],template_paths=self.paths,output_dir=self.root/'person')
        self.assertFalse(errors);id=ids[0]
        args=dict(correction_id=id,template_paths=self.paths,sender_email='hr@example.invalid',checked=True)
        person.act(self.db,action='draft',subject='Original',body='Originalnachricht',adapter=FakeOutlook(),**args)
        person.act(self.db,action='sent_confirmed',**args)
        return id

    def sent_goals(self):
        source,revision,output,group=self.ready()
        self.act(group,adapter=FakeOutlook());self.act(group,action='sent_confirmed')
        return group

    def plan(self,kind,id):return saved.source(self.db,kind,id,self.paths,dispatch_dir=self.root/'dispatches')

    def prepare(self,kind,id,key='request'):
        plan=self.plan(kind,id)
        return saved.prepare(self.db,kind,id,template_paths=self.paths,dispatch_dir=self.root/'dispatches',output_dir=self.root/'again',
            expected=plan['fingerprint'],request_key=key,reason='Auf ausdrückliche Anfrage dieselbe gespeicherte Fassung nochmals zustellen')

    def test_person_source_and_resend_are_byte_equal_without_any_rendering(self):
        id=self.sent_person();old=self.db.execute('SELECT * FROM word_person_corrections WHERE id=?',(id,)).fetchone()
        before={t:[tuple(r) for r in self.db.execute('SELECT * FROM '+t)] for t in ('dialog_cases','dialog_events','document_obligations')}
        with patch('webapp.services.word_packages.render_word_form',side_effect=AssertionError('No rendering')):
            result=self.prepare('person',id)
            current=self.db.execute('SELECT * FROM word_person_corrections WHERE id=?',(result['id'],)).fetchone()
            self.assertEqual(Path(current['stored_path']).read_bytes(),Path(old['stored_path']).read_bytes())
            person.act(self.db,correction_id=result['id'],action='draft',template_paths=self.paths,sender_email='hr@example.invalid',subject='Erneut',body='Dieselben Dateien',checked=True,adapter=FakeOutlook())
        self.assertEqual(self.prepare('person',id),result)
        self.assertEqual(self.db.execute('SELECT status FROM word_person_corrections WHERE id=?',(id,)).fetchone()[0],'sent_confirmed')
        for t in before:self.assertEqual(before[t],[tuple(r) for r in self.db.execute('SELECT * FROM '+t)])

    def test_goal_bundle_is_byte_equal_and_is_not_rebuilt_before_outlook(self):
        id=self.sent_goals();original=delivery.get(self.db,id);path=saved.archive_path(original,self.root/'dispatches');raw=path.read_bytes()
        with patch('webapp.services.word_packages.render_word_form',side_effect=AssertionError('No rendering')),patch.object(delivery,'_bundle_reviews',side_effect=AssertionError('Do not rebuild the bundle')):
            result=self.prepare('goals',id)
            new=delivery.get(self.db,result['id']);self.assertEqual(Path(new['redelivery']['stored_path']).read_bytes(),raw)
            fake=FakeOutlook();self.act(result['id'],adapter=fake)
            self.assertEqual(len(fake.calls),1)
            self.assertEqual(Path(new['redelivery']['stored_path']).read_bytes(),raw)
        self.act(result['id'],action='sent_confirmed')
        self.assertEqual(delivery.get(self.db,id)['status'],'sent_confirmed')
        self.assertEqual(self.prepare('goals',id),result)
        self.assertEqual(goal_followups.output_dispatch(self.db,delivery.members(self.db,id)[0]['id'])['id'],result['id'])

    def test_person_outlook_resend_ignores_unrelated_review_changes(self):
        id=self.sent_person(['outlook'])
        self.assign('review',period_end='2025-08-31')
        self.assertFalse(self.plan('person',id)['issues'])
        result=self.prepare('person',id);self.assertTrue(result['id'])
        self.assertEqual(json.loads(self.db.execute('SELECT manifest_json FROM word_person_corrections WHERE id=?',(result['id'],)).fetchone()[0])['documents'][0]['kind'],'outlook')

    def test_changed_person_basis_and_older_unproven_sources_have_concrete_errors(self):
        id=self.sent_person()
        self.db.execute("UPDATE employees SET first_name='Neuer Name' WHERE pn='111113'");self.db.commit()
        plan=self.plan('person',id)
        self.assertTrue(plan['issues'])
        with self.assertRaises(ValueError):saved.validate(self.db,plan)
        row=self.db.execute('SELECT manifest_json FROM word_person_corrections WHERE id=?',(id,)).fetchone();manifest=json.loads(row[0]);manifest.pop('redelivery_snapshot')
        self.db.execute('UPDATE word_person_corrections SET manifest_json=? WHERE id=?',(json.dumps(manifest),id));self.db.commit()
        with self.assertRaisesRegex(ValueError,'ältere Einzelausgabe'):self.plan('person',id)

    def test_newer_overlapping_output_is_not_silently_ignored(self):
        id=self.sent_person(['review'])
        case=person.person(self.db,self.case_id,self.cycle_id)
        person.prepare_groups(self.db,case=case,kinds=['review'],template_paths=self.paths,output_dir=self.root/'later')
        self.assertIn('spätere Ausgabe',' '.join(self.plan('person',id)['issues']))

    def test_late_return_blocks_both_preparation_and_prepared_person_outlook(self):
        id=self.sent_person(['review']);new=self.prepare('person',id)
        self.pending_return()
        plan=self.plan('person',id);self.assertTrue(plan['blockers'])
        fake=FakeOutlook()
        with self.assertRaisesRegex(ValueError,'return.pdf'):
            person.act(self.db,correction_id=new['id'],action='draft',template_paths=self.paths,sender_email='hr@example.invalid',subject='Erneut',body='Originale',checked=True,adapter=fake)
        self.assertFalse(fake.calls)

    def test_late_goal_return_blocks_existing_prepared_group_and_preserves_original(self):
        id=self.sent_goals();new=self.prepare('goals',id)
        self.pending_return();fake=FakeOutlook()
        with self.assertRaises(ValueError):self.act(new['id'],adapter=fake)
        self.assertFalse(fake.calls);self.assertEqual(delivery.get(self.db,id)['status'],'sent_confirmed')

    def test_saved_archive_tampering_blocks_original_and_prepared_resends(self):
        id=self.sent_goals();new=self.prepare('goals',id)
        group=delivery.get(self.db,new['id']);Path(group['redelivery']['stored_path']).write_bytes(b'changed')
        fake=FakeOutlook()
        with self.assertRaises(ValueError):self.act(new['id'],adapter=fake)
        self.assertFalse(fake.calls)
        original=delivery.get(self.db,id);saved.archive_path(original,self.root/'dispatches').write_bytes(b'changed original')
        with self.assertRaisesRegex(ValueError,'verändert'):self.plan('goals',id)

    def test_http_person_preview_is_read_only_signed_and_session_bound(self):
        id=self.sent_person(['outlook']);url=f'/versand/pakete/gespeichert/person/{id}'
        before=self.db.total_changes;page=self.client.get(url)
        self.assertEqual(page.status_code,200);self.assertIn('Rufname3 Nachname3',page.text);self.assertEqual(self.db.total_changes,before)
        token=re.search('name="request_token" value="([^"]+)"',page.text).group(1)
        form=dict(csrf_token=self.csrf,request_token=token,checked='yes',reason='Unveränderte Fassung nochmals angefordert')
        self.assertEqual(self.client.post(url,data={k:v for k,v in form.items() if k!='csrf_token'}).status_code,400)
        other=self.app.test_client();other.get(url)
        with other.session_transaction() as session:csrf=session['goal_csrf']
        other.post(url,data={**form,'csrf_token':csrf})
        self.assertIsNone(saved.existing(self.db,'person',id))
        response=self.client.post(url,data=form);self.assertEqual(response.status_code,302)
        result=self.client.get(response.location);self.assertEqual(result.status_code,200);self.assertIn('Unveränderte Wiederzustellung',result.text)

    def test_cancelled_goal_retry_can_be_prepared_again_without_rebuilding(self):
        id=self.sent_goals();first=self.prepare('goals',id)
        self.act(first['id'],action='cancelled')
        second=self.prepare('goals',id,key='new-explicit-request')
        self.assertNotEqual(first['id'],second['id'])
        self.assertEqual(delivery.get(self.db,id)['status'],'sent_confirmed')

    def test_http_goal_resend_download_and_prepared_group_are_consistent(self):
        source,rev,output,id=self.ready()
        storage=Path(self.app.config['STORAGE_ROOT'])/'goal_workflow'
        args=dict(template_paths=self.paths,lock_root=storage/'locks',sender_email='hr@example.invalid',subject='Original',body='Geprüfte Rückblicke',checked=True)
        delivery.act(self.db,id,action='draft',adapter=FakeOutlook(),**args)
        delivery.act(self.db,id,action='sent_confirmed',**args)
        url=f'/versand/pakete/gespeichert/goals/{id}'
        page=self.client.get(url);self.assertEqual(page.status_code,200)
        token=re.search('name="request_token" value="([^"]+)"',page.text).group(1)
        response=self.client.post(url,data={'csrf_token':self.csrf,'request_token':token,'checked':'yes','reason':'Auf Anfrage dieselben Rückblicke nochmals zustellen'})
        self.assertEqual(response.status_code,302)
        result=self.client.get(response.location)
        self.assertEqual(result.status_code,200);self.assertIn('Unveränderte Wiederzustellung',result.text)
        new=saved.existing(self.db,'goals',id)['id']
        archive=self.client.get(f'/versand/pakete/zielnachreichung/{new}/zip')
        self.assertEqual(archive.status_code,200)
        original=saved.archive_path(delivery.get(self.db,id),storage/'dispatches').read_bytes()
        self.assertEqual(archive.data,original);archive.close()
        self.pending_return()
        page=self.client.get(response.location)
        self.assertIn('Wiederzustellung zuerst klären',page.text)
        self.assertNotIn('S/MIME-Outlook-Entwurf erstellen',page.text)
        source_page=self.client.get(url)
        self.assertIn('return.pdf',source_page.text);self.assertIn('/word-pdf-imports/',source_page.text)

    def test_changed_prepared_recipient_is_rejected_before_outlook(self):
        id=self.sent_person(['outlook']);new=self.prepare('person',id)
        self.db.execute("UPDATE word_person_corrections SET recipient_email='wrong@example.invalid' WHERE id=?",(new['id'],));self.db.commit()
        fake=FakeOutlook()
        with self.assertRaisesRegex(ValueError,'Empfänger'):
            person.act(self.db,correction_id=new['id'],action='draft',template_paths=self.paths,sender_email='hr@example.invalid',subject='Erneut',body='Gleiche Dateien',checked=True,adapter=fake)
        self.assertFalse(fake.calls)

    def test_utc_and_local_dispatch_times_are_shown_in_the_same_swiss_time(self):
        from webapp.services.intake_views import date_label
        self.assertEqual(date_label('2026-11-10T17:20:00+00:00',True),'10.11.2026 18:20')
        self.assertEqual(date_label('2026-11-10T18:20:00+01:00',True),'10.11.2026 18:20')
