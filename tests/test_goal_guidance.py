"""Actionable progress without bypassing source approval or return protection."""
import unittest
from pathlib import Path
from tests import test_goal_workflow as fixtures
from webapp.services import goal_queries, goal_review as review, goal_followups as followups


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
        self.assertIn('kann mehrere Personen betreffen', page.text)
        self.assertNotIn('name="target"', page.text)
        self.assertEqual(before, followups.return_evidence(self.db, part))
        self.assertEqual(goal_queries.source_state(self.db, source, self.paths), 'followup')

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
