"""Recorded Word bytes, separate delivery evidence, no duplicate conversation effects."""
import hashlib
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
from tests import test_goal_workflow as fixtures, test_part_consumers
from tests.test_word_dispatch import FakeOutlook
from webapp.services import redeliveries as resend,word_dispatch as dispatch,person_corrections
from webapp.services import goal_review


class RedeliveriesTest(unittest.TestCase):
    setUp=fixtures.GoalWorkflowTest.setUp
    tearDown=fixtures.GoalWorkflowTest.tearDown
    pending_return=fixtures.GoalWorkflowTest.pending_return
    assign=test_part_consumers.PartConsumersTest.assign

    def sent(self):
        _,batch=dispatch.prepare_word_batch(self.db,cycle_id=self.cycle_id,manager_pns=['111116'],template_paths=self.paths,output_dir=self.root/'initial')
        id=batch['packages'][0]['id']
        dispatch.dispatch_word_packages(self.db,cycle_id=self.cycle_id,package_ids=[id],template_paths=self.paths,sender_email='hr@example.invalid',adapter=FakeOutlook(),delivery_mode='send')
        return id

    def prepare(self,id,case='',key='request1',**updates):
        plan=resend.source(self.db,id,self.paths,case_id=case)
        values=dict(case_id=case,request_key=key,expected_fingerprint=plan['fingerprint'],reason='Gespeicherte Unterlagen auf Anfrage nochmals zustellen',template_paths=self.paths,output_dir=self.root/'resend')
        values.update(updates)
        return resend.prepare(self.db,id,**values)

    def row(self,result):
        table='word_person_corrections' if result['kind']=='person' else 'word_dispatch_packages'
        return self.db.execute('SELECT * FROM '+table+' WHERE id=?',(result['id'],)).fetchone()

    def test_full_package_is_byte_identical_and_previous_evidence_survives(self):
        id=self.sent();old=self.db.execute('SELECT * FROM word_dispatch_packages WHERE id=?',(id,)).fetchone()
        before={t:[tuple(r) for r in self.db.execute('SELECT * FROM '+t)] for t in ('dialog_cases','dialog_events','document_obligations')}
        with patch('webapp.services.word_packages.create_word_package',side_effect=AssertionError('No rendering for redelivery')):
            new=self.prepare(id)
        self.assertNotEqual(new['id'],id)
        self.assertEqual(Path(old['stored_path']).read_bytes(),Path(self.row(new)['stored_path']).read_bytes())
        self.assertEqual(self.db.execute('SELECT status FROM word_mail_deliveries WHERE package_id=?',(id,)).fetchone()[0],'sent_confirmed')
        for t in before:self.assertEqual(before[t],[tuple(r) for r in self.db.execute('SELECT * FROM '+t)])
        self.assertIsNone(self.db.execute('SELECT status FROM word_mail_deliveries WHERE package_id=?',(new['id'],)).fetchone())

    def test_person_subset_copies_only_exact_person_files_and_shared_attachments(self):
        id=self.sent();plan=resend.source(self.db,id,self.paths,case_id=self.case_id)
        result=self.prepare(id,self.case_id)
        row=self.row(result);meta=json.loads(row['manifest_json'])
        with ZipFile(plan['stored_path']) as original,ZipFile(row['stored_path']) as copied:
            expected={d['filename'] for d in [*plan['documents'],*plan['attachments']]}
            self.assertEqual(set(copied.namelist()),expected)
            for filename in expected:self.assertEqual(original.read(filename),copied.read(filename))
        self.assertTrue(all(d['case_id']==self.case_id for d in meta['documents']))
        self.assertEqual(meta['redelivery']['source_package_id'],id)

    def test_repeat_preparation_finds_same_record_even_after_actual_sent(self):
        id=self.sent();first=self.prepare(id,self.case_id)
        self.assertEqual(self.prepare(id,self.case_id),first)
        fake=FakeOutlook()
        with patch('webapp.services.word_packages.create_word_package',side_effect=AssertionError('No rendering')):
            person_corrections.act(self.db,correction_id=first['id'],action='draft',template_paths=self.paths,sender_email='hr@example.invalid',subject='Erneut',body='Unveränderte Dateien',checked=True,adapter=fake)
        person_corrections.act(self.db,correction_id=first['id'],action='sent_confirmed',template_paths=self.paths,sender_email='hr@example.invalid',checked=True)
        self.assertEqual(self.prepare(id,self.case_id),first)
        later=self.prepare(id,self.case_id,key='fresh-request')
        self.assertNotEqual(later['id'],first['id'])
        self.assertEqual(self.prepare(id,self.case_id),first)
        self.assertEqual(len(fake.calls),1)

    def test_full_copy_drafts_through_existing_dispatch_and_cannot_dispatch_twice(self):
        id=self.sent();result=self.prepare(id);fake=FakeOutlook()
        with patch('webapp.services.word_packages.create_word_package',side_effect=AssertionError('No rendering')):
            dispatch.dispatch_word_packages(self.db,cycle_id=self.cycle_id,package_ids=[result['id']],template_paths=self.paths,sender_email='hr@example.invalid',adapter=fake)
        with self.assertRaises(ValueError):dispatch.dispatch_word_packages(self.db,cycle_id=self.cycle_id,package_ids=[result['id']],template_paths=self.paths,sender_email='hr@example.invalid',adapter=fake)
        dispatch.confirm_word_draft_sent(self.db,result['id'])
        self.assertEqual(len(fake.calls),1)
        statuses=[r[0] for r in self.db.execute('SELECT status FROM word_mail_deliveries ORDER BY id')]
        self.assertEqual(statuses,['sent_confirmed','sent_confirmed'])

    def test_changed_target_goals_names_templates_or_responsibility_block(self):
        id=self.sent()
        self.db.execute("UPDATE employees SET first_name='Anderer Name' WHERE pn='111113'");self.db.commit()
        with self.assertRaisesRegex(ValueError,'Grundlagen'):self.prepare(id,self.case_id)
        self.db.execute("UPDATE employees SET first_name='Rufname3' WHERE pn='111113'");self.db.commit()
        self.assign('outlook')
        with self.assertRaisesRegex(ValueError,'Grundlagen'):self.prepare(id,self.case_id)

    def test_an_unrelated_person_change_does_not_block_selected_person(self):
        id=self.sent()
        self.db.execute("UPDATE employees SET first_name='Anderer Name' WHERE pn='111111'");self.db.commit()
        with self.assertRaisesRegex(ValueError,'Grundlagen'):self.prepare(id)
        result=self.prepare(id,self.case_id)
        self.assertEqual(result['kind'],'person')

    def test_incoming_outlook_is_respected_without_blocking_unrelated_review(self):
        id=self.sent();self.pending_return(kind='outlook')
        parsed=json.loads(self.db.execute('SELECT parsed_json FROM word_pdf_imports').fetchone()[0]);parsed['data']['period_end']='2026-12-31'
        self.db.execute('UPDATE word_pdf_imports SET parsed_json=?',(json.dumps(parsed),));self.db.commit()
        plan=resend.source(self.db,id,self.paths,case_id=self.case_id)
        self.assertTrue(any(b['kind']=='outlook' for b in plan['blockers']))
        self.assertFalse(any(b['kind']=='review' for b in plan['blockers']))
        with self.assertRaisesRegex(ValueError,'Eingang'):self.prepare(id,self.case_id)

    def test_unknown_incoming_file_has_concrete_link_and_non_md_exclusion_releases_it(self):
        id=self.sent();self.pending_return(pn='',kind='unknown')
        html=self.client.get(f'/versand/pakete/{id}/erneut').text
        self.assertIn('return.pdf',html);self.assertIn('/word-pdf-imports/',html)
        item=self.db.execute('SELECT id FROM word_pdf_imports').fetchone()[0]
        from webapp.services import hr_workflow
        hr_workflow.advance_pdf(self.db,item,dismissed=1,reason='Fremder Anhang ohne MD-Bezug');self.db.commit()
        self.assertFalse(resend.source(self.db,id,self.paths,case_id=self.case_id)['blockers'])

    def test_new_return_after_preparation_blocks_draft_but_history_can_be_confirmed(self):
        id=self.sent();result=self.prepare(id,self.case_id);self.pending_return();fake=FakeOutlook()
        with self.assertRaisesRegex(ValueError,'Eingang'):
            person_corrections.act(self.db,correction_id=result['id'],action='draft',template_paths=self.paths,sender_email='hr@example.invalid',subject='Erneut',body='Dateien',checked=True,adapter=fake)
        self.assertFalse(fake.calls)
        self.assertEqual(self.row(result)['status'],'prepared')
        html=self.client.get(f'/cycles/{self.cycle_id}/cases/{self.case_id}/word-correction').text
        self.assertIn('return.pdf',html)
        self.assertNotIn('S/MIME-Outlook-Entwurf erstellen</button>',html)

    def test_open_redelivery_blocks_other_dispatches_for_same_parts(self):
        id=self.sent();result=self.prepare(id,self.case_id);fake=FakeOutlook()
        person_corrections.act(self.db,correction_id=result['id'],action='draft',template_paths=self.paths,sender_email='hr@example.invalid',subject='Erneut',body='Dateien',checked=True,adapter=fake)
        from webapp.services.outlook_lock import check_goal_workflow
        with self.assertRaisesRegex(ValueError,'Outlook'):check_goal_workflow(self.db,[self.case_id])
        with self.assertRaises(ValueError):self.prepare(id)
        self.assertEqual(len(fake.calls),1)

    def test_file_tampering_and_later_source_changes_cannot_send(self):
        id=self.sent();result=self.prepare(id,self.case_id);row=self.row(result)
        Path(row['stored_path']).write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError,'verändert'):resend.validate_prepared(self.db,row,self.paths,kind='person')
        other=self.db.execute('SELECT stored_path FROM word_dispatch_packages WHERE id=?',(id,)).fetchone()[0]
        Path(other).write_bytes(b'tampered source')
        with self.assertRaisesRegex(ValueError,'verändert'):resend.source(self.db,id,self.paths,case_id=self.case_id)

    def test_unsigned_and_cross_session_requests_do_not_create_records(self):
        id=self.sent();url=f'/versand/pakete/{id}/erneut?case_id={self.case_id}'
        html=self.client.get(url).text
        token=re.search('name="request_token" value="([^"]+)"',html).group(1)
        self.assertEqual(self.client.post(url,data={'request_token':token}).status_code,400)
        self.client.post(url,data={'csrf_token':self.csrf,'request_token':'bad','checked':'yes','reason':'Geprüft'})
        other=self.app.test_client();other.get('/arbeit/ziele')
        with other.session_transaction() as session:csrf=session['goal_csrf']
        other.post(url,data={'csrf_token':csrf,'request_token':token,'checked':'yes','reason':'Geprüft'})
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_person_corrections').fetchone()[0],0)
        response=self.client.post(url,data={'csrf_token':self.csrf,'request_token':token,'checked':'yes','reason':'Geprüfter Wiederzustellungsauftrag','case_id':self.case_id})
        self.assertEqual(response.status_code,302)
        self.assertIn('word-correction',response.location)
        self.client.post(url,data={'csrf_token':self.csrf,'request_token':token,'checked':'yes','reason':'Geprüft','case_id':self.case_id})
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_person_corrections').fetchone()[0],1)

    def test_pending_or_superseded_sources_are_not_eligible(self):
        id=self.sent()
        _,batch=dispatch.prepare_word_batch(self.db,cycle_id=self.cycle_id,manager_pns=['111116'],template_paths=self.paths,output_dir=self.root/'new')
        with self.assertRaisesRegex(ValueError,'neuere'):self.prepare(id)
        with self.assertRaisesRegex(ValueError,'versandt'):self.prepare(batch['packages'][0]['id'])
        with self.assertRaises(ValueError):resend.source(self.db,id,self.paths,case_id='foreign-case')

    def test_shipping_ledger_and_person_view_make_redelivery_visible(self):
        id=self.sent();result=self.prepare(id,self.case_id)
        html=self.client.get('/versand?view=overview').text
        self.assertIn('Unveränderte Wiederzustellung',html)
        html=self.client.get(f'/cycles/{self.cycle_id}/cases/{self.case_id}/word-correction').text
        self.assertIn('unverändert nochmals zustellen',html)
        self.assertIn('Unveränderte Wiederzustellung',html)
