"""Actionable progress without bypassing source approval or return protection."""
import unittest
import json
from pathlib import Path
from tests import test_goal_workflow as fixtures
from webapp.services import goal_queries, goal_review as review, goal_followups as followups
from webapp.services import hr_workflow


class GoalGuidanceTest(unittest.TestCase):
    setUp = fixtures.GoalWorkflowTest.setUp
    tearDown = fixtures.GoalWorkflowTest.tearDown
    stage = fixtures.GoalWorkflowTest.stage
    confirm = fixtures.GoalWorkflowTest.confirm
    generate = fixtures.GoalWorkflowTest.generate
    pending_return = fixtures.GoalWorkflowTest.pending_return

    def listing(self, **kwargs):
        return goal_queries.listing(self.db, template_paths=self.paths, **kwargs)

    def test_confirmation_leads_to_creation_then_file_check_and_dispatch(self):
        source = self.stage()
        self.assertEqual(self.listing()['summary'], {'review': 1})
        item = review.get(self.db, source)
        values = dict(csrf_token=self.csrf, revision=item['revision'], action='confirm_outputs',
                      employment_id=item['employment_id'], goal_year=item['goal_year'], checked='yes',
                      sources_fingerprint=followups.review.digest([]))
        for kind, goals in item['goals'].items():
            for field in review.FIELDS:
                values[kind+'_'+field] = [g.get(field, '') for g in goals]
        response = self.client.post(f'/arbeit/ziele/{source}', data=values)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/arbeit/ziele/ausgaben?', response.location)
        self.assertEqual(self.listing()['summary'], {'ready': 1})
        rev = review.get(self.db, source)['revision_id']
        output = self.generate(rev)['output_id']
        self.assertEqual(self.listing()['summary'], {'approve': 1})
        page = self.client.get('/arbeit/ziele/ausgaben', query_string={'source': source})
        self.assertNotIn('name="target"', page.text)
        self.assertIn('Datei erstellt – noch prüfen', page.text)
        followups.approve(self.db, output, self.paths)
        self.assertEqual(self.listing()['summary'], {'dispatch': 1})

    def test_missing_template_shown_before_generation_in_both_views(self):
        source = self.stage(); self.confirm(source)
        Path(self.paths['review']).unlink()
        data = self.listing()
        self.assertEqual(data['summary'], {'followup': 1})
        self.assertIn('Word-Vorlage', data['rows'][0]['next_reason'])
        page = self.client.get('/arbeit/ziele/ausgaben', query_string={'source': source})
        self.assertEqual(page.status_code, 200)
        self.assertIn('Word-Vorlage einrichten', page.text)
        self.assertNotIn('name="target"', page.text)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM hr_goal_outputs').fetchone()[0], 0)

    def test_sap_conflict_preflight_has_link_to_actual_import(self):
        source = self.stage(); self.confirm(source)
        with self.db:
            self.db.execute("UPDATE sap_import_issues SET severity='blocking',status='open',person_number='111113'")
        self.assertEqual(self.listing()['summary'], {'followup': 1})
        page = self.client.get('/arbeit/ziele/ausgaben', query_string={'source': source})
        self.assertIn('SAP-Konflikte anzeigen', page.text)
        self.assertNotIn('name="target"', page.text)

    def test_unknown_pdf_explains_shared_blocker_and_retains_evidence(self):
        source = self.stage(); self.confirm(source)
        self.pending_return(pn='', kind='unknown')
        part = followups.resolve(self.db, self.case_id)
        before = followups.return_evidence(self.db, part)
        page = self.client.get('/arbeit/ziele/ausgaben', query_string={'source': source})
        self.assertEqual(page.status_code, 200)
        self.assertIn('return.pdf · Eingang zuordnen / prüfen', page.text)
        self.assertIn('kann mehrere Rückblicke betreffen', page.text)
        self.assertNotIn('name="target"', page.text)
        self.assertNotIn('name="outcome"', page.text)
        self.assertIn('Dafür ist hier keine Entscheidung zum Rückblick nötig', page.text)
        self.assertEqual(before, followups.return_evidence(self.db, part))
        self.assertEqual(goal_queries.source_state(self.db, source, self.paths), 'followup')

    def test_non_md_exclusion_unblocks_creation_without_filling_md_fields_and_is_reversible(self):
        source = self.stage(); self.confirm(source)
        self.pending_return(pn='', kind='unknown')
        item = self.db.execute('SELECT * FROM word_pdf_imports').fetchone()
        original = self.root/'foreign.pdf'
        original.write_bytes(b'%PDF-1.4\nSynthetic non-MD attachment\n%%EOF')
        with self.db:
            self.db.execute('UPDATE word_pdf_imports SET stored_path=? WHERE id=?', (str(original), item['id']))
        url = f"/word-pdf-imports/{item['id']}"
        back = f'/arbeit/ziele/ausgaben?source={source}'
        page = self.client.get(url, query_string={'back': back})
        self.assertIn('Kein MD-Dokument – ausschliessen', page.text)
        page = self.client.post(url, data={'csrf_token': self.csrf, 'revision': 0,
            'action': 'not_md', 'back': back}, follow_redirects=True)
        self.assertEqual(page.status_code, 200)
        self.assertIn('Dieser Eingang blockiert keine Rückblicke mehr', page.text)
        self.assertIn('Zurück zu den ausgewählten Rückblicken', page.text)
        self.assertNotIn('name="document_kind"', page.text)
        self.assertNotIn('word_pdf_review.js', page.text)
        saved = self.db.execute('SELECT * FROM word_pdf_imports WHERE id=?', (item['id'],)).fetchone()
        self.assertEqual(saved['parsed_json'], item['parsed_json'])
        self.assertEqual(json.loads(saved['reviewed_json'])['data'], json.loads(item['parsed_json'])['data'])
        self.assertEqual(saved['status'], 'pending')
        self.assertTrue(original.is_file())
        self.assertEqual(hr_workflow.pdf_queue(self.db, status='pending')['pdf_total'], 0)
        self.assertEqual(hr_workflow.pdf_queue(self.db, status='not_md')['pdf_total'], 1)
        self.assertEqual(self.listing()['summary'], {'ready': 1})
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0], 0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM hr_goal_decisions').fetchone()[0], 0)
        self.assertEqual(self.client.post('/arbeit/ziele/pdf/'+str(item['id']), data={'csrf_token':self.csrf}).status_code, 302)
        page = self.client.post(url, data={'csrf_token':self.csrf, 'revision':1, 'action':'reopen'}, follow_redirects=True)
        self.assertIn('Prüfung wieder geöffnet', page.text)
        self.assertFalse(hr_workflow.pdf_state(self.db, item['id'])['not_md'])
        self.assertEqual(hr_workflow.pdf_queue(self.db, status='not_md')['pdf_total'], 0)
        self.assertEqual(self.listing()['summary'], {'followup': 1})

    def test_exclusion_requires_current_revision_and_csrf_and_cannot_change_imported_pdf(self):
        self.pending_return(pn='', kind='unknown')
        item = self.db.execute('SELECT id FROM word_pdf_imports').fetchone()[0]
        url = f'/word-pdf-imports/{item}'
        values = {'action':'not_md','revision':0}
        self.assertEqual(self.client.post(url, data=values).status_code, 400)
        values['csrf_token'] = self.csrf
        self.client.post(url, data=values)
        page = self.client.post(url, data=values)
        self.assertIn('inzwischen geändert', page.text)
        self.assertEqual(hr_workflow.pdf_state(self.db, item)['revision'], 1)
        with self.db:
            self.db.execute("UPDATE word_pdf_imports SET status='imported' WHERE id=?", (item,))
        values['revision'] = 1
        self.client.post(url, data=values)
        self.assertEqual(hr_workflow.pdf_state(self.db, item)['revision'], 1)

    def test_exclusion_unblocks_all_affected_sources_and_ignores_external_return_url(self):
        first = self.stage(); self.confirm(first)
        second = self.stage('other-person.docx', 'Andere Ziele')
        employment = self.db.execute("SELECT id FROM employment_assignments WHERE person_number='111111' ORDER BY id").fetchone()[0]
        self.confirm(second, employment_id=employment)
        self.pending_return(pn='', kind='unknown')
        self.assertEqual(self.listing()['summary'], {'followup': 2})
        item = self.db.execute('SELECT id FROM word_pdf_imports').fetchone()[0]
        page = self.client.post(f'/word-pdf-imports/{item}', data={'csrf_token':self.csrf, 'revision':0,
            'action':'not_md', 'back':'https://example.invalid/arbeit/ziele'}, follow_redirects=True)
        self.assertNotIn('https://example.invalid', page.text)
        self.assertEqual(self.listing()['summary'], {'ready': 2})
        self.assertNotEqual(first, second)

    def test_unprocessed_mail_attachment_has_specific_file_and_original_links(self):
        source = self.stage(); self.confirm(source)
        with self.db:
            message = self.db.execute('''INSERT INTO inbound_mail_messages
                (outlook_entry_id,subject,received_at,created_at,updated_at)
                VALUES ('synthetic','Unklarer Testeingang','2026-11-09','2026-11-09','2026-11-09')''').lastrowid
            attachment = self.db.execute('''INSERT INTO inbound_mail_attachments
                (mail_message_id,attachment_index,original_filename,sha256,file_kind,status,created_at)
                VALUES (?,1,'unklar.pdf','synthetic-pdf','md_pdf','stored','2026-11-09')''', (message,)).lastrowid
        page = self.client.get('/arbeit/ziele/ausgaben', query_string={'source': source})
        self.assertEqual(page.status_code, 200)
        self.assertIn('unklar.pdf · Eingang zuordnen / prüfen', page.text)
        self.assertIn(f'/mail-attachments/{attachment}/original', page.text)
        self.assertNotIn('name="target"', page.text)

    def test_main_worklist_uses_same_preflight_and_links_to_next_action(self):
        source = self.stage(); self.confirm(source)
        page = self.client.get('/arbeit', query_string={'kind': 'Ziele'})
        self.assertIn('Rückblicke erstellen', page.text)
        self.assertIn(f'/arbeit/ziele/ausgaben?source={source}', page.text)
        Path(self.paths['review']).unlink()
        page = self.client.get('/arbeit', query_string={'kind': 'Ziele'})
        self.assertIn('Rücklauf / Zuordnung klären', page.text)
        self.assertNotIn('>Rückblicke erstellen</a>', page.text)

    def test_known_other_person_does_not_block_and_summary_survives_state_filter(self):
        source = self.stage(); self.confirm(source)
        self.pending_return(pn='111111')
        draft = self.stage('draft.docx', 'Noch zu prüfen')
        data = self.listing(state='ready', batch_id=self.group)
        self.assertEqual(data['summary'], {'ready': 1, 'review': 1})
        self.assertEqual([row['id'] for row in data['rows']], [source])
        self.assertNotEqual(source, draft)
        self.assertEqual(self.listing(q='draft.docx')['summary'], {'review': 1})
        page = self.client.get('/arbeit/ziele', query_string={'batch_id': self.group, 'state': 'ready'})
        self.assertIn('Was ist als Nächstes zu tun?', page.text)
        self.assertIn('batch_id='+str(self.group), page.text)

    def test_unconfirmed_source_cannot_be_generated_from_new_confirmation_button(self):
        source = self.stage()
        item = review.get(self.db, source)
        page = self.client.post(f'/arbeit/ziele/{source}', data={
            'csrf_token': self.csrf, 'revision': item['revision'], 'action': 'confirm_outputs',
            'employment_id': item['employment_id'], 'goal_year': item['goal_year'],
        })
        self.assertEqual(page.status_code, 200)
        self.assertIn('ausdrücklich bestätigen', page.text)
        self.assertEqual(review.get(self.db, source)['status'], 'draft')


if __name__ == '__main__':
    unittest.main()
