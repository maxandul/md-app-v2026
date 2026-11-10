"""Reviewed SAP files and campaign closure keep external processing distinct."""
import json
import re
import unittest
from pathlib import Path
from unittest.mock import patch
from tests import test_goal_workflow as fixtures
from webapp.services import export_closure_views as views,sap_export,part_responsibilities as parts


class ExportClosureTest(unittest.TestCase):
    setUp=fixtures.GoalWorkflowTest.setUp
    tearDown=fixtures.GoalWorkflowTest.tearDown

    def ready(self):
        self.db.execute("UPDATE dialog_cases SET status='vollstaendig',official_scope='full',dialog_date='2025-12-15',overall_rating_code='C',data_json=? WHERE case_id=?",(json.dumps({'scope':'full','review':{'conducted':'ja'}}),self.case_id))
        self.db.execute('UPDATE dialog_events SET sap_leading=1 WHERE legacy_case_id=?',(self.case_id,));self.db.commit()

    def token(self,response):
        self.assertEqual(response.status_code,200)
        match=re.search('name="review_token" value="([^"]+)"',response.text)
        self.assertIsNotNone(match,response.text[:1500]);return match.group(1)

    def export(self,token):
        return self.client.post(f'/abschluss-export/{self.cycle_id}/sap',data={'csrf_token':self.csrf,'review_token':token,'checked':'yes'})

    def close(self,token,**updates):
        return self.client.post(f'/abschluss-export/{self.cycle_id}/abschluss',data={'csrf_token':self.csrf,'review_token':token,'external_checked':'yes','closure_reason':'Restfälle fachlich weiterverfolgen','closure_owner':'HR Test',**updates})

    def closure_ready(self):
        self.db.execute("UPDATE cycles SET status='ruecklauf' WHERE id=?",(self.cycle_id,));self.db.commit()

    def test_plan_is_read_only_and_names_actual_export_rows_match_canonical(self):
        self.ready();before=self.db.total_changes
        plan=views.export_plan(self.db,self.cycle_id)
        canonical=sap_export.collect_sap_upload_rows(self.db,self.cycle_id)
        self.assertEqual([r['case_id'] for r in plan['ready']],[r.case_id for r in canonical])
        page=self.client.get(f'/abschluss-export/{self.cycle_id}/sap')
        self.assertIn('Rufname3 Nachname3',page.text);self.assertIn('Filter begrenzen die Anzeige, nicht den Batch',page.text)
        self.assertEqual(self.db.total_changes,before)

    def test_creation_redirects_to_preserved_batch_and_repeat_does_not_create_another(self):
        self.ready();token=self.token(self.client.get(f'/abschluss-export/{self.cycle_id}/sap'))
        first=self.export(token);self.assertEqual(first.status_code,302)
        self.assertEqual(self.export(token).location,first.location)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM sap_export_batches').fetchone()[0],1)
        page=self.client.get(first.location);self.assertIn('kein',page.text)
        self.assertIn('Rufname3 Nachname3',page.text)
        batch=self.db.execute('SELECT * FROM sap_export_batches').fetchone()
        raw=Path(batch['stored_path']).read_bytes()
        response=self.client.post(f"/sap-export-batches/{batch['id']}/download")
        self.assertEqual(response.data,raw);response.close()
        self.assertFalse(views.export_plan(self.db,self.cycle_id)['ready'])

    def test_stale_export_and_tampered_file_are_rejected(self):
        self.ready();token=self.token(self.client.get(f'/abschluss-export/{self.cycle_id}/sap'))
        self.db.execute("UPDATE dialog_cases SET overall_rating_code='B' WHERE case_id=?",(self.case_id,));self.db.commit()
        self.assertIn('inzwischen',self.export(token).text)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM sap_export_batches').fetchone()[0],0)
        self.export(self.token(self.client.get(f'/abschluss-export/{self.cycle_id}/sap')))
        batch=self.db.execute('SELECT * FROM sap_export_batches').fetchone();Path(batch['stored_path']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Nachweis'):sap_export.get_sap_export_batch(self.db,batch['id'])

    def test_missing_leading_choice_and_invalid_data_have_named_clarification(self):
        self.ready();self.db.execute('UPDATE dialog_events SET sap_leading=0 WHERE legacy_case_id=?',(self.case_id,));self.db.commit()
        plan=views.export_plan(self.db,self.cycle_id)
        self.assertIn('Rufname3 Nachname3',plan['error']);self.assertEqual(plan['counts']['attention'],1)
        page=self.client.get(f'/abschluss-export/{self.cycle_id}/sap')
        self.assertIn('Massgebenden Rückblick auswählen',page.text);self.assertNotIn('Geprüften Batch erstellen',page.text)
        self.db.execute('UPDATE dialog_events SET sap_leading=1 WHERE legacy_case_id=?',(self.case_id,))
        self.db.execute("UPDATE dialog_cases SET dialog_date='' WHERE case_id=?",(self.case_id,));self.db.commit()
        plan=views.export_plan(self.db,self.cycle_id);self.assertIn('Datum MAB',plan['error'])

    def test_cancelled_or_inactive_case_cannot_enter_sap_export(self):
        self.ready();self.db.execute("UPDATE dialog_events SET status='cancelled' WHERE legacy_case_id=?",(self.case_id,));self.db.commit()
        self.assertFalse(views.export_plan(self.db,self.cycle_id)['ready'])
        with self.assertRaisesRegex(ValueError,'keine neuen'):sap_export.collect_sap_upload_rows(self.db,self.cycle_id)

    def test_closure_lists_real_remainders_preserves_reason_and_keeps_work_open(self):
        self.closure_ready()
        page=self.client.get(f'/abschluss-export/{self.cycle_id}/abschluss')
        token=self.token(page);self.assertIn('Offene Einzelausgaben',page.text)
        response=self.close(token,closure_reason='')
        self.assertIn('Begründung',response.text);self.assertIn('value="HR Test"',response.text)
        token=self.token(response);response=self.close(token);self.assertEqual(response.status_code,302)
        record=self.db.execute('SELECT * FROM workflow_cycle_closures').fetchone();self.assertEqual(record['owner'],'HR Test')
        self.assertEqual(self.db.execute('SELECT status FROM cycles WHERE id=?',(self.cycle_id,)).fetchone()[0],'abgeschlossen')
        self.assertTrue(any(json.loads(record['summary_json']).values()))
        self.assertTrue(parts.resolve(self.db,self.case_id)['required'])
        self.assertEqual(self.close(token).status_code,302)
        self.assertIn('Dokumentierter Abschluss',self.client.get(response.location).text)

    def test_changed_remainder_with_same_count_requires_a_new_closure_review(self):
        self.closure_ready();token=self.token(self.client.get(f'/abschluss-export/{self.cycle_id}/abschluss'))
        self.db.execute("UPDATE document_obligations SET due_date='2027-01-15' WHERE id=?",(parts.resolve(self.db,self.case_id)['obligation_id'],));self.db.commit()
        response=self.close(token);self.assertIn('inzwischen',response.text)
        self.assertIsNone(self.db.execute('SELECT * FROM workflow_cycle_closures').fetchone())

    def test_export_and_closure_proofs_are_scoped_and_csrf_protected(self):
        self.ready();url=f'/abschluss-export/{self.cycle_id}/sap';token=self.token(self.client.get(url))
        self.assertEqual(self.client.post(url,data={'review_token':token,'checked':'yes'}).status_code,400)
        self.assertEqual(self.export(token+'tamper').status_code,200)
        self.closure_ready();self.close(token)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM sap_export_batches').fetchone()[0],0)
        other=self.app.test_client();other.get(url)
        with other.session_transaction() as s:csrf=s['goal_csrf']
        other.post(url,data={'csrf_token':csrf,'review_token':token,'checked':'yes'})
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM sap_export_batches').fetchone()[0],0)

    def test_cycle_filter_contains_review_and_outlook_and_bulk_selection_keeps_scope(self):
        from webapp.services import part_queries,part_actions
        from webapp.services.cycles import create_cycle
        other=create_cycle(self.db,review_year=2027,sap_import_id=self.db.execute('SELECT MAX(id) FROM sap_imports').fetchone()[0])
        ids=part_queries.selection_ids(self.db,cycle_id=self.cycle_id)
        self.assertTrue(ids)
        rows=part_queries.listing(self.db,cycle_id=self.cycle_id)['rows']
        self.assertEqual({r['cycle_id'] for r in rows},{self.cycle_id})
        self.assertEqual({r['document_kind'] for r in rows},{'review','outlook'})
        filters={'cycle_id':self.cycle_id,'state':'open'}
        selected=part_actions.select(self.db,owner='test-owner',filters=filters,mode='all',checked=[])
        self.assertEqual(set(selected['ids']),set(ids))
        with self.assertRaisesRegex(ValueError,'Filter'):part_actions.selection(self.db,selected['id'],'test-owner',{'cycle_id':other,'state':'open'})
        page=self.client.get(f'/arbeit/dialogteile?cycle_id={self.cycle_id}')
        self.assertIn('Durchlauf 2025/2026',page.text);self.assertIn('name="cycle_id"',page.text)

    def test_old_export_and_closure_actions_lead_to_review_without_mutation(self):
        self.ready();self.closure_ready()
        for path,data in ((f'/cycles/{self.cycle_id}/sap-export',{}),(f'/cycles/{self.cycle_id}/status',{'status':'abgeschlossen','external_checked':'yes'})):
            response=self.client.post(path,data=data);self.assertEqual(response.status_code,302)
            self.assertIn('/abschluss-export/',response.location)
        self.assertIsNone(self.db.execute('SELECT * FROM workflow_cycle_closures').fetchone())
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM sap_export_batches').fetchone()[0],0)

    def test_replayed_closure_after_reopening_does_not_close_or_claim_closed_again(self):
        from webapp.services.cycles import change_cycle_status
        self.closure_ready();token=self.token(self.client.get(f'/abschluss-export/{self.cycle_id}/abschluss'))
        self.close(token)
        change_cycle_status(self.db,cycle_id=self.cycle_id,new_status='ruecklauf')
        response=self.close(token)
        page=self.client.get(response.location)
        self.assertIn('bereits dokumentiert',page.text)
        self.assertIn('inzwischen wieder geöffnet',page.text)
        self.assertEqual(self.db.execute('SELECT status FROM cycles WHERE id=?',(self.cycle_id,)).fetchone()[0],'ruecklauf')

    def test_new_mail_after_closure_review_is_visible_and_invalidates_the_review(self):
        self.closure_ready();token=self.token(self.client.get(f'/abschluss-export/{self.cycle_id}/abschluss'))
        self.db.execute("INSERT INTO inbound_mail_messages(outlook_entry_id,sender_email,subject,received_at,status,created_at,updated_at) VALUES ('synthetic-late','test@example.invalid','Synthetischer später Eingang','2026-11-10','review_required','2026-11-10','2026-11-10')")
        self.db.commit()
        response=self.close(token)
        self.assertIn('inzwischen',response.text)
        self.assertEqual(views.closure_plan(self.db,self.cycle_id)['summary']['Ungeklärte Postfachnachrichten (gesamt)'],1)
        self.assertIsNone(self.db.execute('SELECT * FROM workflow_cycle_closures').fetchone())
