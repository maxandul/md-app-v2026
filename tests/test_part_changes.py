"""Reviewed assignment changes retain all conversation and dispatch evidence."""
import json
import re
import unittest
from tests import test_goal_workflow as fixtures
from tests import test_part_consumers as old_parts
from tests.test_word_dispatch import FakeOutlook
from webapp.services import part_changes,part_responsibilities as parts,word_dispatch,person_corrections,reminders
from datetime import date


class PartChangeTest(unittest.TestCase):
    setUp=fixtures.GoalWorkflowTest.setUp
    tearDown=fixtures.GoalWorkflowTest.tearDown
    pending_return=fixtures.GoalWorkflowTest.pending_return
    assign=old_parts.PartConsumersTest.assign

    def values(self,kind='outlook',**updates):
        part=parts.resolve(self.db,self.case_id,kind)
        values=dict(kind=kind,manager_pn='111114',form_org_source='manager',period_start=part['period_start'],period_end=part['period_end'],
                    expected_revision=part['responsibility_revision'],reason='Verantwortung für diesen Gesprächsteil ausdrücklich neu regeln')
        values.update(updates);return values

    def preview(self,kind='outlook',**updates):
        values=self.values(kind,**updates);values['revision']=values.pop('expected_revision');values.pop('kind')
        return self.client.post(f'/arbeit/dialogteile/{self.case_id}/{kind}',data={**values,'csrf_token':self.csrf,'back':'/arbeit/dialogteile?q=Rufname3&page=2'})

    def token(self,response):
        match=re.search('name="change_token" value="([^"]+)"',response.text)
        self.assertIsNotNone(match,response.text[:1000]);return match.group(1)

    def apply_preview(self,token,kind='outlook',**updates):
        return self.client.post(f'/arbeit/dialogteile/{self.case_id}/{kind}',data={'csrf_token':self.csrf,'change_token':token,'action':'apply','checked':'yes','back':'/arbeit/dialogteile?q=Rufname3&page=2',**updates})

    def prepared(self,mode='draft'):
        _,batch=word_dispatch.prepare_word_batch(self.db,cycle_id=self.cycle_id,manager_pns=['111116'],template_paths=self.paths,output_dir=self.root/'dispatch')
        id=batch['packages'][0]['id']
        word_dispatch.dispatch_word_packages(self.db,cycle_id=self.cycle_id,package_ids=[id],template_paths=self.paths,sender_email='hr@example.invalid',adapter=FakeOutlook(),delivery_mode=mode)
        return id

    def test_read_and_preview_do_not_change_records_and_show_both_roles(self):
        before=self.db.total_changes
        page=self.client.get(f'/arbeit/dialogteile/{self.case_id}/outlook')
        self.assertEqual(page.status_code,200);self.assertIn('Direkt vorgesetzt:',page.text)
        preview=self.preview();self.assertEqual(preview.status_code,200)
        self.assertIn('noch nicht gespeichert',preview.text)
        self.assertIn('Rufname6 Nachname6',preview.text);self.assertIn('Rufname4 Nachname4',preview.text)
        self.assertIn('keine zweite Pflicht',preview.text)
        self.assertEqual(self.db.total_changes,before)

    def test_apply_replaces_one_responsibility_not_the_conversation_or_other_part(self):
        before=parts.resolve(self.db,self.case_id,'review')
        obligation=parts.resolve(self.db,self.case_id,'outlook')['obligation_id']
        counts={t:self.db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('dialog_cases','dialog_events','document_obligations')}
        response=self.apply_preview(self.token(self.preview()))
        self.assertEqual(response.status_code,302);self.assertIn('q%3DRufname3',response.location)
        after=parts.resolve(self.db,self.case_id,'outlook')
        self.assertEqual((after['manager_pn'],after['obligation_id']),('111114',obligation))
        self.assertEqual(parts.resolve(self.db,self.case_id,'review'),before)
        for t in counts:self.assertEqual(self.db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0],counts[t])
        html=self.client.get(response.location).text;self.assertIn('Nur für diesen Teil Unterlagen vorbereiten',html)
        case=person_corrections.person(self.db,self.case_id,self.cycle_id)
        ids,errors=person_corrections.prepare_groups(self.db,case=case,kinds=['outlook'],template_paths=self.paths,output_dir=self.root/'corrections')
        self.assertFalse(errors)
        row=self.db.execute('SELECT * FROM word_person_corrections WHERE id=?',(ids[0],)).fetchone()
        self.assertIn('111114',row['recipient_email'])
        self.assertEqual([d['kind'] for d in json.loads(row['manifest_json'])['documents']],['outlook'])

    def test_repeat_confirmation_is_idempotent_even_after_later_changes(self):
        token=self.token(self.preview());first=self.apply_preview(token)
        self.apply_preview(token)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM hr_goal_events WHERE action='responsibility_changed'").fetchone()[0],1)
        self.assign('outlook',manager='111116')
        self.apply_preview(token)
        self.assertEqual(parts.resolve(self.db,self.case_id,'outlook')['manager_pn'],'111116')
        self.assertIn('changed=',first.location)

    def test_csrf_signed_proof_and_cross_session_scope_are_required(self):
        token=self.token(self.preview())
        url=f'/arbeit/dialogteile/{self.case_id}/outlook'
        self.assertEqual(self.client.post(url,data={'action':'apply','change_token':token,'checked':'yes'}).status_code,400)
        self.apply_preview(token+'invalid')
        self.apply_preview(token,kind='review')
        other=self.app.test_client();other.get('/arbeit/ziele')
        with other.session_transaction() as s:csrf=s['goal_csrf']
        other.post(url,data={'csrf_token':csrf,'change_token':token,'checked':'yes','action':'apply'})
        self.assertEqual(parts.resolve(self.db,self.case_id,'outlook')['manager_pn'],'111116')

    def test_open_outlook_blocks_change_and_links_to_existing_packet(self):
        id=self.prepared();before=parts.resolve(self.db,self.case_id,'outlook')
        response=self.preview();self.assertIn('Zuerst klären',response.text)
        self.assertIn(f'/versand/pakete/{id}',response.text)
        self.assertNotIn('value="apply"',response.text)
        self.apply_preview(self.token(response))
        self.assertEqual(parts.resolve(self.db,self.case_id,'outlook'),before)

    def test_refresh_after_outlook_resolution_preserves_proposal_and_reason(self):
        id=self.prepared();token=self.token(self.preview())
        word_dispatch.discard_word_draft(self.db,id)
        self.apply_preview(token)
        self.assertEqual(parts.resolve(self.db,self.case_id,'outlook')['manager_pn'],'111116')
        response=self.client.post(f'/arbeit/dialogteile/{self.case_id}/outlook',data={'csrf_token':self.csrf,'change_token':token,'action':'refresh'})
        self.assertIn('Vorschau erneut prüfen',response.text)
        self.assertIn('Verantwortung für diesen Gesprächsteil ausdrücklich neu regeln',response.text)
        self.assertIn('value="apply"',response.text)
        self.apply_preview(self.token(response))
        self.assertEqual(parts.resolve(self.db,self.case_id,'outlook')['manager_pn'],'111114')

    def test_sent_package_and_old_document_bytes_survive_assignment(self):
        id=self.prepared('send');row=self.db.execute('SELECT * FROM word_dispatch_packages WHERE id=?',(id,)).fetchone()
        from pathlib import Path
        raw=Path(row['stored_path']).read_bytes()
        response=self.preview();self.assertIn('Tatsächlicher Versand bestätigt',response.text)
        self.apply_preview(self.token(response))
        self.assertEqual(raw,Path(row['stored_path']).read_bytes())
        self.assertEqual(self.db.execute('SELECT status FROM word_mail_deliveries WHERE package_id=?',(id,)).fetchone()[0],'sent_confirmed')
        candidate=word_dispatch.word_dispatch_candidates(self.db,cycle_id=self.cycle_id,template_paths=self.paths)[0]
        self.assertTrue(candidate['source_changes'])

    def test_late_return_blocks_old_preview_and_exposes_actual_file(self):
        token=self.token(self.preview(kind='review'));self.pending_return()
        response=self.apply_preview(token,kind='review')
        self.assertIn('inzwischen',response.text)
        self.assertEqual(parts.resolve(self.db,self.case_id)['manager_pn'],'111116')
        response=self.preview(kind='review')
        self.assertIn('return.pdf',response.text);self.assertIn('/word-pdf-imports/',response.text)
        self.assertNotIn('value="apply"',response.text)

    def test_completed_parts_and_active_reminders_require_clarification(self):
        reminders.create_reminder_drafts(self.db,cycle_id=self.cycle_id,manager_pns=['111116'],sender_email='hr@example.invalid',adapter=FakeOutlook(),today=date(2027,1,1))
        response=self.preview();self.assertIn('Erinnerungsvorgang',response.text);self.assertNotIn('value="apply"',response.text)
        self.db.execute("UPDATE document_obligations SET status='complete' WHERE id=?",(parts.resolve(self.db,self.case_id,'outlook')['obligation_id'],));self.db.commit()
        response=self.preview();self.assertIn('Rücklauf liegt vor',response.text)

    def test_other_part_and_manager_data_changes_invalidate_the_preview(self):
        token=self.token(self.preview())
        self.assign('review',manager='111116',period_end='2025-08-31')
        self.apply_preview(token)
        self.assertEqual(parts.resolve(self.db,self.case_id,'outlook')['manager_pn'],'111116')
        token=self.token(self.preview())
        self.db.execute("UPDATE employees SET org_unit='Neue OE' WHERE pn='111114'");self.db.commit()
        self.apply_preview(token)
        self.assertEqual(parts.resolve(self.db,self.case_id,'outlook')['manager_pn'],'111116')

    def test_edit_and_invalid_input_preserve_valid_fields(self):
        response=self.preview(period_start='2026-03-01',reason='Ausblick ab Wechsel')
        edited=self.client.post(f'/arbeit/dialogteile/{self.case_id}/outlook',data={'csrf_token':self.csrf,'change_token':self.token(response),'action':'edit'})
        self.assertIn('value="2026-03-01"',edited.text);self.assertIn('Ausblick ab Wechsel',edited.text)
        invalid=self.preview(period_start='2025-03-01',reason='Jahr noch korrigieren')
        self.assertIn('innerhalb des Ausblickjahres',invalid.text);self.assertIn('Jahr noch korrigieren',invalid.text)
        self.assertEqual(parts.resolve(self.db,self.case_id,'outlook')['manager_pn'],'111116')

    def test_history_uses_saved_names_and_form_selection_is_limited_to_changed_part(self):
        self.apply_preview(self.token(self.preview()))
        self.db.execute("UPDATE employees SET first_name='Heute Anders' WHERE pn='111114'");self.db.commit()
        history=part_changes.history(self.db,self.case_id,'outlook')
        self.assertEqual(history[0]['details']['new_label'],'Rufname4 Nachname4')
        html=self.client.get(f'/cycles/{self.cycle_id}/cases/{self.case_id}/word-correction?kind=outlook').text
        self.assertRegex(html,'name="kind" value="outlook" checked')
        self.assertNotRegex(html,'name="kind" value="review" checked')
