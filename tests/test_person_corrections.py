import json
import unittest
from pathlib import Path
from zipfile import ZipFile
from unittest.mock import patch
from tests import test_word_packages as fixtures
from tests.test_word_dispatch import FakeOutlook
from webapp.services.person_corrections import person, prepare, act


class PersonCorrectionsTest(unittest.TestCase):
    setUp = fixtures.WordPackagesTest.setUp
    tearDown = fixtures.WordPackagesTest.tearDown

    def prepare(self, kinds=None):
        return prepare(self.db, case=person(self.db,self.case_id,self.cycle_id), kinds=kinds or ['review'], template_paths=self.paths,output_dir=self.root/'corrections')

    def act(self, id, action='draft', **kwargs):
        return act(self.db,correction_id=id,action=action,template_paths=self.paths,sender_email='hr@example.invalid',subject='Korrektur',body='Hallo\n\nKorrigierte Formulare.',**kwargs)

    def test_selected_review_only_and_draft_confirmation(self):
        id = self.prepare()
        row = self.db.execute('SELECT * FROM word_person_corrections WHERE id=?',(id,)).fetchone()
        with ZipFile(row['stored_path']) as archive:
            self.assertEqual(len(archive.namelist()),1)
            self.assertTrue(archive.namelist()[0].startswith('Rückblick_'))
        fake = FakeOutlook()
        self.act(id,adapter=fake)
        self.assertEqual(len(fake.calls),1)
        self.assertEqual(fake.calls[0]['recipient_email'],'person-111116@example.invalid')
        self.assertEqual(fake.calls[0]['attachments'],[Path(row['stored_path'])])
        with self.assertRaises(ValueError):self.act(id,adapter=fake)
        self.act(id,action='sent_confirmed',checked=True)
        self.assertEqual(self.db.execute('SELECT status FROM word_person_corrections WHERE id=?',(id,)).fetchone()[0],'sent_confirmed')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_dispatch_packages').fetchone()[0],0)

    def test_changed_data_and_tampered_file_block_draft(self):
        id = self.prepare()
        self.db.execute("UPDATE employees SET first_name='Anders' WHERE pn='111113'");self.db.commit()
        fake=FakeOutlook()
        with self.assertRaisesRegex(ValueError,'Grundlagen'): self.act(id,adapter=fake)
        id2=self.prepare()
        row=self.db.execute('SELECT stored_path FROM word_person_corrections WHERE id=?',(id2,)).fetchone()
        Path(row[0]).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Datei verändert'):self.act(id2,adapter=fake)
        self.assertEqual(fake.calls,[])

    def test_pending_draft_and_failure_require_resolution(self):
        one=self.prepare();two=self.prepare(['outlook'])
        self.act(one,adapter=FakeOutlook())
        with self.assertRaisesRegex(ValueError,'noch ein Outlook'):self.act(two,adapter=FakeOutlook())
        self.act(one,action='cancelled',checked=True)
        with self.assertRaises(ValueError):self.act(two,adapter=FakeOutlook(fail=True))
        with self.assertRaises(ValueError):self.act(two,adapter=FakeOutlook())
        self.act(two,action='cancelled',checked=True)

    def test_routes_and_invalid_selection(self):
        client=self.app.test_client()
        url=f'/cycles/{self.cycle_id}/cases/{self.case_id}/word-correction'
        self.assertIn('Formulare auswählen',client.get(url).text)
        response=client.post(url,data={'kind':['outlook']},follow_redirects=True)
        self.assertEqual(response.status_code,200)
        self.assertIn('S/MIME-Outlook-Entwurf erstellen',response.text)
        id=self.db.execute('SELECT id FROM word_person_corrections').fetchone()[0]
        download=client.get(f'/word-corrections/{id}/download')
        self.assertEqual(download.status_code,200)
        download.close()
        with self.assertRaises(ValueError):self.prepare(['bad'])
        self.db.execute("UPDATE dialog_cases SET official_scope='outlook_only' WHERE case_id=?",(self.case_id,));self.db.commit()
        with self.assertRaises(ValueError):self.prepare(['review'])

    def test_manual_event_selects_employment_and_preserves_chosen_form_org(self):
        from webapp.services.word_packages import create_word_package
        from webapp.services.word_dispatch import source_snapshot
        self.db.execute("UPDATE employment_assignments SET org_unit='Neue OE' WHERE person_number='111113'")
        self.db.execute("UPDATE employees SET org_unit='Alte OE' WHERE pn='111118'")
        self.db.commit()
        employment=self.db.execute("SELECT id FROM employment_assignments WHERE person_number='111113' AND assignment_number='1'").fetchone()[0]
        client=self.app.test_client()
        self.assertIn('Person und Anstellung',client.get('/dialoge').text)
        response=client.post('/dialog-events',data={'employment_id':employment,'manager_pn':'111118','event_type':'transfer_review','required_scope':'review_only','review_year':2025,'period_start':'2025-01-01','period_end':'2025-08-31','reason':'Übertritt zur neuen Organisation','cycle_id':self.cycle_id,'form_org_source':'manager'})
        self.assertEqual(response.status_code,302)
        event=self.db.execute("SELECT legacy_case_id,id FROM dialog_events WHERE source='manual' ORDER BY id DESC").fetchone()
        self.assertIsNotNone(event)
        self.assertEqual(self.db.execute('SELECT org_unit FROM dialog_form_org_units WHERE dialog_event_id=?',(event['id'],)).fetchone()[0],'Alte OE')
        self.db.execute("UPDATE employees SET org_unit='Später geändert' WHERE pn='111118'");self.db.commit()
        path,manifest=create_word_package(self.db,cycle_id=self.cycle_id,manager_pn='111118',case_id=event['legacy_case_id'],document_kinds=['review'],template_paths=self.paths,output_dir=self.root/'manual')
        with ZipFile(path) as archive:
            raw=archive.read(manifest['documents'][0]['filename'])
        self.assertEqual(fixtures.controls(fixtures.xml_for(raw))['rb_oe'],'Alte OE')
        snapshot=source_snapshot(self.db,cycle_id=self.cycle_id,manager_pn='111118',template_paths=self.paths)
        self.assertEqual(next(c['org_unit'] for c in snapshot['cases'] if c['case_id']==event['legacy_case_id']),'Alte OE')

        from webapp.services.dialog_events import create_manual_event
        event_key=create_manual_event(self.db,employee_pn='111113',assignment_number='1',manager_pn='111118',event_type='interim',required_scope='review_only',review_year=2025,period_start='2025-01-01',period_end='2025-08-31',reason='Stellvertretung bei Vakanz',form_org_source='employee')
        saved=self.db.execute('SELECT fo.org_unit FROM dialog_form_org_units fo JOIN dialog_events de ON de.id=fo.dialog_event_id WHERE de.event_id=?',(event_key,)).fetchone()
        self.assertEqual(saved['org_unit'],'Neue OE')
        page=client.get(f"/cycles/{self.cycle_id}/cases/{event['legacy_case_id']}")
        self.assertIn('Gespeicherte Formular-OE',page.text)
        self.assertIn('Alte OE',page.text)
