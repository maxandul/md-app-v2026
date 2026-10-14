from __future__ import annotations

import json
import unittest
from pathlib import Path
from zipfile import ZipFile

from webapp.adapters.outlook import DraftResult
from webapp.services.word_dispatch import (
    prepare_word_batch, word_dispatch_candidates, dispatch_word_packages, confirm_word_draft_sent, discard_word_draft,
)
from tests import test_word_packages as fixtures


class FakeOutlook:
    def __init__(self, fail=False):
        self.calls=[]
        self.fail=fail
    def create_encrypted_draft(self, **message):
        self.calls.append(message)
        if self.fail:
            raise RuntimeError('Outlook nicht verfügbar')
        return DraftResult(entry_id='test-draft',encryption_flag_verified=True)
    def send_encrypted(self, **message):
        return self.create_encrypted_draft(**message)


class WordDispatchTest(unittest.TestCase):
    setUp=fixtures.WordPackagesTest.setUp
    tearDown=fixtures.WordPackagesTest.tearDown

    def prepare(self, numbers=None):
        return prepare_word_batch(self.db,cycle_id=self.cycle_id,manager_pns=numbers or ['111116'],template_paths=self.paths,output_dir=self.root/'dispatch')
    def send(self, ids, adapter, **kwargs):
        return dispatch_word_packages(self.db,cycle_id=self.cycle_id,package_ids=ids,template_paths=self.paths,sender_email='hr@example.invalid',adapter=adapter,**kwargs)
    def candidates(self):
        return word_dispatch_candidates(self.db,cycle_id=self.cycle_id,template_paths=self.paths)

    def test_preview_without_packages_and_matches_outlook(self):
        client = self.app.test_client()
        page = client.get(f'/versand?cycle_id={self.cycle_id}')
        self.assertEqual(page.status_code, 200)
        self.assertIn('E-Mail-Vorschau aktualisieren', page.text)
        payload = {'preview_manager_pn': '111116'}
        response = client.post(f'/cycles/{self.cycle_id}/word-mail-preview', data=payload)
        self.assertEqual(response.status_code, 200)
        preview = response.json
        self.assertEqual(preview['subject'], 'MD-Unterlagen Durchlauf 2025/2026')
        self.assertIn('Rückblick_2025_', preview['body_html'])
        self.assertIn('Ausblick_2026_', preview['body_html'])
        self.assertIn('31.01.2026', preview['body_html'])
        self.assertIn('<ul>', preview['body_html'])
        self.assertIn('<a href="https://ktzuerich.sharepoint.com/', preview['body_html'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_mail_deliveries').fetchone()[0], 0)
        self.prepare()
        fake = FakeOutlook()
        self.app.config['HR_MAILBOX_EMAIL'] = 'hr@example.invalid'
        preview = client.post(f'/cycles/{self.cycle_id}/word-mail-preview', data=payload).json
        self.send([self.candidates()[0]['id']], fake)
        self.assertEqual(preview['body_html'], fake.calls[0]['body_html'])
        self.assertEqual(preview['subject'], fake.calls[0]['subject'])

    def test_preview_custom_text_errors_and_html_escaping(self):
        client = self.app.test_client()
        endpoint = f'/cycles/{self.cycle_id}/word-mail-preview'
        payload = {'preview_manager_pn': '111116', 'subject_template': 'Test {years}',
                   'body_template': '<script>alert(1)</script> **Hallo** [Link](javascript:alert)'}
        response = client.post(endpoint, data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('<script>', response.json['body_html'])
        self.assertNotIn('href="javascript:', response.json['body_html'])
        self.assertIn('<strong>Hallo</strong>', response.json['body_html'])
        payload['body_template'] = '{unknown}'
        self.assertEqual(client.post(endpoint, data=payload).status_code, 400)
        self.assertEqual(client.post(endpoint, data={'preview_manager_pn': 'missing'}).status_code, 400)

    def test_document_filenames_without_assignment_and_separate_cases(self):
        # Duplicate one person's case with another assignment in the same leadership line.
        original = dict(self.db.execute('SELECT * FROM dialog_cases WHERE case_id=?', (self.case_id,)).fetchone())
        original.pop('id')
        original['case_id'] += '-second'
        original['employment_assignment'] = '2'
        columns = ','.join(original)
        self.db.execute(f"INSERT INTO dialog_cases ({columns}) VALUES ({','.join('?' for _ in original)})", tuple(original.values()))
        self.db.commit()
        _batch, result = self.prepare()
        manifest = result['packages'][0]['manifest']
        docs = manifest['documents']
        self.assertTrue(any(d['filename'].startswith('Fall_1/') for d in docs))
        self.assertTrue(any(d['filename'].startswith('Fall_2/') for d in docs))
        self.assertEqual(len({d['filename'] for d in docs}), len(docs))
        for doc in docs:
            self.assertNotIn('_Ans', doc['filename'])
            self.assertRegex(doc['filename'], r'_\d+\.docx$')

    def test_interrupted_delivery_recovery_checks_lock_and_does_not_send(self):
        from webapp.services.outlook_lock import package_lock
        from webapp.services.word_dispatch import resolve_interrupted_delivery
        self.prepare()
        item=self.candidates()[0]
        fake=FakeOutlook()
        self.send([item['id']],fake)
        self.db.execute("UPDATE word_mail_deliveries SET status='processing' WHERE package_id=?",(item['id'],))
        self.db.commit()
        client=self.app.test_client()
        self.assertIn(f"/word-packages/{item['id']}/resolve-interrupted",client.get(f'/versand?cycle_id={self.cycle_id}').text)
        with package_lock(item['stored_path']):
            with self.assertRaisesRegex(ValueError,'läuft noch'):
                resolve_interrupted_delivery(self.db,item['id'],outcome='cancelled',reason='Outlook geprüft, Entwurf entfernt')
        resolve_interrupted_delivery(self.db,item['id'],outcome='cancelled',reason='Outlook geprüft, Entwurf entfernt')
        self.assertEqual(len(fake.calls),1)
        self.assertEqual(self.db.execute('SELECT status FROM word_mail_deliveries').fetchone()[0],'cancelled')
        with self.assertRaisesRegex(ValueError,'nicht mehr'):
            resolve_interrupted_delivery(self.db,item['id'],outcome='sent_confirmed',reason='Doppelte Bestätigung unterbinden')

    def test_prepare_versions_without_marking_sent_or_changing_workbooks(self):
        batch,result=self.prepare()
        self.assertTrue(batch.is_file())
        with ZipFile(batch) as archive:
            self.assertEqual(len(archive.namelist()),1)
        item=self.candidates()[0]
        self.assertTrue(item['ready']);self.assertIsNone(item['delivery_status'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM package_events').fetchone()[0],0)
        old_bytes=Path(item['stored_path']).read_bytes()
        self.prepare()
        self.assertNotEqual(item['id'],self.candidates()[0]['id'])
        self.assertEqual(Path(item['stored_path']).read_bytes(),old_bytes)

    def test_batch_failure_rolls_back_and_removes_partial_output(self):
        with self.assertRaises(ValueError):
            self.prepare(['111116','missing'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_dispatch_packages').fetchone()[0],0)
        self.assertEqual(list((self.root/'dispatch').iterdir()),[])

    def test_draft_then_manual_confirmation_without_second_outlook_call(self):
        self.prepare();item=self.candidates()[0];adapter=FakeOutlook()
        result=self.send([item['id']],adapter)
        self.assertEqual(result['created'],1);self.assertEqual(result['sent'],0)
        self.assertEqual(adapter.calls[0]['recipient_email'],item['recipient_email'])
        self.assertEqual(adapter.calls[0]['attachments'],[Path(item['stored_path'])])
        self.assertIn('MD-Unterlagen Durchlauf',adapter.calls[0]['subject'])
        self.assertNotIn('Arbeitsmappe',adapter.calls[0]['body_html'])
        with self.assertRaises(ValueError):
            self.send([item['id']],adapter)
        confirm_word_draft_sent(self.db,item['id'])
        self.assertEqual(self.candidates()[0]['delivery_status'],'sent_confirmed')
        self.assertEqual(len(adapter.calls),1)

    def test_stale_data_and_tampered_files_prevent_any_outlook_call(self):
        self.prepare();item=self.candidates()[0];adapter=FakeOutlook()
        self.db.execute("UPDATE employees SET first_name='Geändert' WHERE pn='111113'");self.db.commit()
        with self.assertRaisesRegex(ValueError,'geändert'):
            self.send([item['id']],adapter)
        self.assertEqual(adapter.calls,[])
        self.prepare();item=self.candidates()[0]
        Path(item['stored_path']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'verändert'):
            self.send([item['id']],adapter)
        self.assertEqual(adapter.calls,[])

    def test_late_goals_make_prepared_package_stale(self):
        self.prepare();item=self.candidates()[0]
        fixtures.WordPackagesTest.add_goals(self)
        self.assertFalse(self.candidates()[0]['ready'])
        with self.assertRaisesRegex(ValueError,'geändert'):
            self.send([item['id']],FakeOutlook())

    def test_old_package_or_cross_cycle_selection_cannot_be_sent(self):
        self.prepare();old=self.candidates()[0]['id'];self.prepare()
        adapter=FakeOutlook()
        with self.assertRaises(ValueError):
            self.send([old],adapter)
        with self.assertRaises(ValueError):
            self.send([self.candidates()[0]['id'],999999],adapter)
        self.assertEqual(adapter.calls,[])

    def test_failure_retry_requires_outlook_check(self):
        self.prepare();item=self.candidates()[0]
        result=self.send([item['id']],FakeOutlook(fail=True))
        self.assertEqual(result['failed'],1)
        adapter=FakeOutlook()
        with self.assertRaisesRegex(ValueError,'Wiederholung'):
            self.send([item['id']],adapter)
        self.assertEqual(adapter.calls,[])
        result=self.send([item['id']],adapter,retry_confirmed=True,delivery_mode='send')
        self.assertEqual(result['sent'],1)
        self.assertEqual(self.candidates()[0]['delivery_status'],'sent_confirmed')

    def test_two_managers_receive_only_their_own_packet(self):
        self.prepare(['111116','111117'])
        items=self.candidates();adapter=FakeOutlook()
        result=self.send([item['id'] for item in items],adapter)
        self.assertEqual(result['created'],2)
        self.assertEqual(len(adapter.calls),2)
        for item in items:
            call=next(call for call in adapter.calls if call['recipient_email']==item['recipient_email'])
            self.assertEqual(call['attachments'],[Path(item['stored_path'])])
            manifest=json.loads(item['manifest_json'])
            expected={row['case_id'] for row in self.db.execute('SELECT case_id FROM dialog_cases WHERE manager_pn=?',(item['manager_pn'],))}
            self.assertTrue({doc['case_id'] for doc in manifest['documents']}.issubset(expected))
            with ZipFile(call['attachments'][0]) as archive:
                self.assertEqual(set(archive.namelist()),{doc['filename'] for doc in manifest['documents'] + manifest['attachments']})
                feedback=next(doc for doc in manifest['attachments'] if doc['kind']=='feedback')
                values=fixtures.controls(fixtures.xml_for(archive.read(feedback['filename'])))
                self.assertEqual(values['fb_pn_vg'],item['manager_pn'])

    def test_open_draft_must_be_resolved_before_new_generation(self):
        self.prepare();item=self.candidates()[0];self.send([item['id']],FakeOutlook())
        with self.assertRaisesRegex(ValueError,'Entwurf offen'):
            self.prepare()
        discard_word_draft(self.db,item['id'])
        self.assertEqual(self.candidates()[0]['delivery_status'],'cancelled')
        self.assertFalse(self.candidates()[0]['ready'])
        self.prepare()
        self.assertTrue(self.candidates()[0]['ready'])

    def test_failed_attempt_requires_resolution_before_regenerating(self):
        self.prepare();item=self.candidates()[0]
        self.send([item['id']],FakeOutlook(fail=True))
        with self.assertRaisesRegex(ValueError,'fehlgeschlagener Versuch'):
            self.prepare()
        discard_word_draft(self.db,item['id'])
        self.prepare()
        self.assertTrue(self.candidates()[0]['ready'])

    def test_word_preparation_removes_missing_template_task_but_not_dispatch_task(self):
        from webapp.services.cockpit import cockpit_overview
        before=cockpit_overview(self.db,selected_cycle_id=self.cycle_id)
        self.prepare()
        after=cockpit_overview(self.db,selected_cycle_id=self.cycle_id)
        self.assertEqual(after['metrics']['workbooks_missing'],before['metrics']['workbooks_missing']-1)
        self.assertTrue(any(t['title']=='Word-Versand abschliessen' and t['manager_pn']=='111116' for t in after['tasks']))

    def test_missing_sender_and_invalid_template_do_not_call_outlook(self):
        self.prepare();item=self.candidates()[0];adapter=FakeOutlook()
        with self.assertRaisesRegex(ValueError,'Absenderadresse'):
            dispatch_word_packages(self.db,cycle_id=self.cycle_id,package_ids=[item['id']],template_paths=self.paths,sender_email='',adapter=adapter)
        with self.assertRaisesRegex(ValueError,'Platzhalter'):
            self.send([item['id']],adapter,subject_template='{unknown}')
        self.assertEqual(adapter.calls,[])

    def test_dispatch_routes_prepare_then_offer_download_and_keep_html_alternative(self):
        client=self.app.test_client()
        response=client.post(f'/cycles/{self.cycle_id}/word-packages/batch',data={'selection_mode':'selected','manager_pn':'111116'})
        self.assertEqual(response.status_code,302)
        page=client.get(response.location)
        self.assertEqual(page.status_code,200)
        self.assertIn(b'Word-Vorlagen bereitstellen',page.data)
        self.assertIn(b'Sammel-ZIP',page.data)
        self.assertEqual(client.get(f'/versand?cycle_id={self.cycle_id}&workflow=workbook').status_code,200)
        package_id=self.candidates()[0]['id']
        response=client.post(f'/word-packages/{package_id}/confirm-sent',data={'sent_checked':'yes'})
        self.assertEqual(response.status_code,302)
        self.assertIsNone(self.candidates()[0]['delivery_status'])

if __name__=='__main__':unittest.main()
