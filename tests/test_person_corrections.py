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
