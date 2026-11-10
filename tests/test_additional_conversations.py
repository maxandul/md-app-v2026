"""Guided additions must retain the old evidence and apply both decisions atomically."""
import json
import re
import unittest
from unittest.mock import patch
from tests import test_goal_workflow as fixtures
from tests import test_part_changes as change_tests
from webapp.services import additional_conversations as additions,part_responsibilities as parts,dialog_events,person_corrections


class AdditionalConversationTest(unittest.TestCase):
    setUp=fixtures.GoalWorkflowTest.setUp
    tearDown=fixtures.GoalWorkflowTest.tearDown
    pending_return=fixtures.GoalWorkflowTest.pending_return
    prepared=change_tests.PartChangeTest.prepared

    def values(self,**updates):
        values=dict(manager_pn='111114',event_type='interim',required_scope='full',period_start='2025-01-01',period_end='2025-08-31',
            review_due_date='2026-01-20',outlook_due_date='2026-02-20',form_org_source='manager',disposition='keep',reason='Übertritt fachlich geprüft')
        values.update(updates);return values

    def preview(self,**updates):
        return self.client.post(f'/arbeit/dialogteile/{self.case_id}/zusaetzlich',data={'csrf_token':self.csrf,**self.values(**updates)})

    def proof(self,response):
        match=re.search('name="change_token" value="([^"]+)"',response.text)
        self.assertIsNotNone(match,response.text[:1200]);return match.group(1)

    def apply(self,token,**updates):
        return self.client.post(f'/arbeit/dialogteile/{self.case_id}/zusaetzlich',data={'csrf_token':self.csrf,'action':'apply','change_token':token,'checked':'yes',**updates})

    def saved(self):
        return json.loads(self.db.execute("SELECT details_json FROM hr_goal_events WHERE action='additional_conversation_created' ORDER BY id DESC").fetchone()[0])

    def test_read_and_preview_have_no_domain_writes_and_show_old_and_new_names(self):
        before=self.db.total_changes
        page=self.client.get(f'/arbeit/dialogteile/{self.case_id}/zusaetzlich')
        self.assertEqual(page.status_code,200);self.assertIn('Bitte ausdrücklich wählen',page.text)
        response=self.preview()
        self.assertEqual(response.status_code,200);self.assertIn('Rufname4 Nachname4',response.text);self.assertIn('Rufname6 Nachname6',response.text)
        self.assertIn('Bleibt vorgesehen',response.text);self.assertEqual(self.db.total_changes,before)

    def test_keep_adds_new_parts_and_forms_without_changing_the_original(self):
        before=parts.case_parts(self.db,self.case_id)
        from webapp.services.person_display import enrich
        identity={'employee_pn':'111113','employment_assignment':'1'};enrich(self.db,[identity]);original_identity=identity['current_contexts']
        response=self.apply(self.proof(self.preview()),manager_pn='111116',disposition='replace')
        self.assertEqual(response.status_code,302)
        details=self.saved();new=details['new_case_id']
        self.assertEqual(parts.case_parts(self.db,self.case_id),before)
        enrich(self.db,[identity]);self.assertEqual(identity['current_contexts'],original_identity)
        self.assertEqual({p['manager_pn'] for p in parts.case_parts(self.db,new)},{'111114'})
        case=person_corrections.person(self.db,new,self.cycle_id)
        ids,errors=person_corrections.prepare_groups(self.db,case=case,kinds=['review','outlook'],template_paths=self.paths,output_dir=self.root/'additional-forms')
        self.assertFalse(errors);self.assertEqual(len(ids),1)
        page=self.client.get(response.location);self.assertEqual(page.status_code,200);self.assertIn('Unterlagen für den neuen Auftrag',page.text)

    def test_replace_retires_whole_old_order_preserves_sent_files_and_is_repeatable(self):
        from pathlib import Path
        packet=self.prepared('send');row=self.db.execute('SELECT * FROM word_dispatch_packages WHERE id=?',(packet,)).fetchone();raw=Path(row['stored_path']).read_bytes()
        token=self.proof(self.preview(disposition='replace'))
        first=self.apply(token);self.assertEqual(first.status_code,302)
        new=self.saved()['new_case_id']
        self.assertEqual(self.db.execute('SELECT active FROM dialog_cases WHERE case_id=?',(self.case_id,)).fetchone()[0],0)
        self.assertEqual({p['event_status'] for p in parts.case_parts(self.db,self.case_id)},{'cancelled'})
        self.assertEqual({p['obligation_status'] for p in parts.case_parts(self.db,self.case_id)},{'waived'})
        self.assertTrue(all(p['required'] for p in parts.case_parts(self.db,new)))
        self.assertEqual(Path(row['stored_path']).read_bytes(),raw)
        self.assertEqual(self.db.execute('SELECT status FROM word_mail_deliveries WHERE package_id=?',(packet,)).fetchone()[0],'sent_confirmed')
        second=self.apply(token);self.assertEqual(first.location,second.location)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM hr_goal_events WHERE action='additional_conversation_created'").fetchone()[0],1)
        dialog_events.sync_cycle_events(self.db,self.cycle_id)
        self.assertEqual(parts.resolve(self.db,self.case_id)['event_status'],'cancelled')

    def test_partial_replacement_and_missing_decision_or_reason_are_rejected(self):
        for updates in ({'disposition':''},{'reason':''}):
            page=self.preview(**updates);self.assertNotIn('name="change_token"',page.text)
        page=self.preview(disposition='replace',required_scope='review_only')
        self.assertIn('ersetzt nicht alle',page.text);self.assertNotIn('value="apply"',page.text)
        self.apply(self.proof(page));self.assertIsNone(self.db.execute("SELECT 1 FROM hr_goal_events WHERE action='additional_conversation_created'").fetchone())

    def test_open_outlook_or_late_return_prevents_replacement_but_not_an_explicit_addition(self):
        packet=self.prepared()
        page=self.preview(disposition='replace');self.assertIn(f'/versand/pakete/{packet}',page.text);self.assertNotIn('value="apply"',page.text)
        self.assertIn('value="apply"',self.preview().text)
        from webapp.services.word_dispatch import discard_word_draft
        discard_word_draft(self.db,packet)
        token=self.proof(self.preview(disposition='replace'));self.pending_return(kind='review')
        response=self.apply(token);self.assertIn('inzwischen',response.text)
        page=self.preview(disposition='replace');self.assertIn('return.pdf',page.text);self.assertNotIn('value="apply"',page.text)

    def test_concurrent_new_event_invalidates_preview_and_duplicate_links_existing(self):
        token=self.proof(self.preview());self.apply(token)
        oldtoken=self.proof(self.preview(event_type='transfer_review'))
        # Any concurrent event for the employment changes the reviewed overall picture.
        values=self.values(event_type='departure_review');values.pop('disposition')
        dialog_events.create_manual_event(self.db,employee_pn='111113',assignment_number='1',review_year=2025,cycle_id=self.cycle_id,**values)
        response=self.apply(oldtoken);self.assertIn('inzwischen',response.text)
        page=self.preview();self.assertIn('Bestehendes Gespräch öffnen',page.text);self.assertNotIn('value="apply"',page.text)

    def test_creation_failure_rolls_back_new_event_and_old_retirement_together(self):
        proposal=self.values(disposition='replace');plan=additions.plan(self.db,self.case_id,proposal)
        before=self.db.execute('SELECT COUNT(*) FROM dialog_events').fetchone()[0]
        original=dialog_events._create_manual_event
        def fail(*args,**kwargs):
            original(*args,**kwargs);raise ValueError('synthetischer Abbruch')
        with patch.object(dialog_events,'_create_manual_event',side_effect=fail):
            with self.assertRaisesRegex(ValueError,'Abbruch'):additions.apply(self.db,self.case_id,proposal,expected=plan['fingerprint'],request_key='rollback')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM dialog_events').fetchone()[0],before)
        self.assertEqual(parts.resolve(self.db,self.case_id)['active'],1)

    def test_preview_is_session_bound_signed_and_csrf_protected(self):
        token=self.proof(self.preview())
        url=f'/arbeit/dialogteile/{self.case_id}/zusaetzlich'
        self.assertEqual(self.client.post(url,data={'action':'apply','change_token':token,'checked':'yes'}).status_code,400)
        self.apply(token+'bad')
        other=self.app.test_client();other.get(url)
        with other.session_transaction() as s:csrf=s['goal_csrf']
        other.post(url,data={'csrf_token':csrf,'action':'apply','change_token':token,'checked':'yes'})
        self.assertIsNone(self.db.execute("SELECT 1 FROM hr_goal_events WHERE action='additional_conversation_created'").fetchone())

    def test_retired_order_cannot_be_dispatched_from_an_old_prepared_package(self):
        from webapp.services import word_dispatch
        from tests.test_word_dispatch import FakeOutlook
        _,batch=word_dispatch.prepare_word_batch(self.db,cycle_id=self.cycle_id,manager_pns=['111116'],template_paths=self.paths,output_dir=self.root/'prepared')
        packet=batch['packages'][0]['id']
        response=self.apply(self.proof(self.preview(disposition='replace')))
        self.assertEqual(response.status_code,302)
        fake=FakeOutlook()
        with self.assertRaisesRegex(ValueError,'Grundlagen haben sich geändert'):
            word_dispatch.dispatch_word_packages(self.db,cycle_id=self.cycle_id,package_ids=[packet],template_paths=self.paths,
                sender_email='hr@example.invalid',adapter=fake)
        self.assertFalse(fake.calls)

    def test_new_record_does_not_inherit_sap_leading_and_old_history_links_decision(self):
        token=self.proof(self.preview(disposition='replace'));self.apply(token)
        details=self.saved();new=details['new_case_id']
        self.assertEqual(self.db.execute('SELECT sap_leading FROM dialog_events WHERE legacy_case_id=?',(new,)).fetchone()[0],0)
        old=self.client.get(f'/arbeit/dialogteile/{self.case_id}/review')
        self.assertIn('Durch neuen Auftrag ersetzt',old.text);self.assertIn(new,old.text)
        self.assertIn('Dieser Auftrag ist nicht mehr vorgesehen',old.text)
        self.assertNotIn('Änderung zuerst prüfen',old.text)

    def test_pending_reminder_blocks_whole_replacement_and_invalid_dates_preserve_form(self):
        from webapp.services import reminders
        from tests.test_word_dispatch import FakeOutlook
        from datetime import date
        reminders.create_reminder_drafts(self.db,cycle_id=self.cycle_id,manager_pns=['111116'],sender_email='hr@example.invalid',adapter=FakeOutlook(),today=date(2027,1,1))
        page=self.preview(disposition='replace');self.assertIn('Erinnerung offen',page.text);self.assertNotIn('value="apply"',page.text)
        page=self.preview(period_start='2025-12-31',period_end='2025-01-01')
        self.assertIn('gültigen Zeitraum',page.text);self.assertIn('Übertritt fachlich geprüft',page.text)
