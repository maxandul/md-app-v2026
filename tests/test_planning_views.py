"""Task context never substitutes for SAP, conversation or delivery decisions."""
import unittest
from tests import test_sap_staging as fixtures
from webapp.services import planning_views, sap_staging as sap


class PlanningViewsTest(unittest.TestCase):
    setUp=fixtures.SapStagingTest.setUp
    tearDown=fixtures.SapStagingTest.tearDown
    frame=fixtures.SapStagingTest.frame
    preview=fixtures.SapStagingTest.preview
    row=fixtures.SapStagingTest.row
    changed=fixtures.SapStagingTest.changed
    apply=fixtures.SapStagingTest.apply

    def test_cycle_plan_is_read_only_and_keeps_conversation_and_shipping_separate(self):
        before=self.db.total_changes
        response=self.client.get('/durchlauf',query_string={'cycle_id':self.cycle_id})
        self.assertEqual(response.status_code,200)
        self.assertIn('Gesprächsaufträge und Fristen prüfen',response.text)
        self.assertIn('noch keine',self.client.get('/durchlauf?new=yes').text)
        self.assertIn('keine inhaltliche Prüfung',response.text)
        self.assertEqual(self.db.total_changes,before)
        self.assertIn('/durchlauf',self.client.get('/start').text)

    def test_creation_uses_current_import_only_and_repeated_year_resumes(self):
        imported=self.db.execute('SELECT MAX(id) FROM sap_imports').fetchone()[0]
        payload={'csrf_token':self.csrf,'review_year':'2027','sap_import_id':str(imported)}
        self.assertEqual(self.client.post('/durchlauf',data={k:v for k,v in payload.items() if k!='csrf_token'}).status_code,400)
        first=self.client.post('/durchlauf',data=payload)
        self.assertIn('cycle_id=',first.location)
        count=self.db.execute('SELECT COUNT(*) FROM dialog_cases').fetchone()[0]
        second=self.client.post('/durchlauf',data=payload)
        self.assertEqual(first.location,second.location)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM dialog_cases').fetchone()[0],count)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_dispatch_packages').fetchone()[0],0)

    def test_stale_import_invalid_year_and_unknown_context_are_rejected(self):
        old=self.db.execute('SELECT MAX(id) FROM sap_imports').fetchone()[0]
        batch=self.changed();self.apply(batch)
        self.client.post('/durchlauf',data={'csrf_token':self.csrf,'review_year':'2027','sap_import_id':old})
        self.assertIsNone(self.db.execute('SELECT 1 FROM cycles WHERE review_year=2027').fetchone())
        current=self.db.execute('SELECT MAX(id) FROM sap_imports').fetchone()[0]
        self.client.post('/durchlauf',data={'csrf_token':self.csrf,'review_year':'1900','sap_import_id':current})
        self.assertIsNone(self.db.execute('SELECT 1 FROM cycles WHERE review_year=1900').fetchone())
        self.assertEqual(self.client.get('/durchlauf?cycle_id=999999').status_code,404)
        self.assertEqual(self.client.get('/stammdaten/abgleich?plan_cycle=999999').status_code,404)

    def test_followup_filter_and_counts_follow_canonical_status(self):
        batch=self.changed();row=self.row(batch)
        self.assertEqual(planning_views.sap_progress(self.db,batch)['followup_open'],0)
        pending=sap.changes(self.db,batch,state='data')['total']
        self.assertGreaterEqual(pending,1)
        self.apply(batch)
        self.assertEqual(sap.changes(self.db,batch,state='data')['total'],pending-1)
        self.assertEqual(sap.changes(self.db,batch,state='followup')['total'],1)
        self.assertEqual(planning_views.sap_progress(self.db,batch)['followup_open'],1)
        row=self.row(batch)
        sap.resolve(self.db,row['id'],revision=row['revision'],action='followup_done',reason='Keine Änderung am Gesprächsauftrag nötig',token=sap.context_token(self.db,row['person_number']))
        self.assertEqual(sap.changes(self.db,batch,state='followup')['total'],0)

    def test_superseded_preview_is_history_and_not_an_open_followup(self):
        first=self.changed();self.apply(first)
        second=self.changed(field='OE Bez.',value='Nochmals neue OE',name='second.xlsx');self.apply(second)
        self.assertEqual(planning_views.sap_progress(self.db,first)['followup_open'],0)
        self.assertEqual(planning_views.sap_progress(self.db,second)['followup_open'],1)
        self.assertEqual(sap.changes(self.db,first,state='followup')['total'],0)

    def test_names_use_export_manager_and_do_not_change_live_assignments(self):
        frame=self.frame()
        frame.loc[frame['ID_NO_ZERO'].astype(str)=='111116','Rufname']='VorgesetzteNeu'
        batch=self.preview(frame);rows=sap.changes(self.db,batch,state='all')['rows']
        before=self.db.total_changes
        planning_views.named_snapshots(self.db,rows)
        person=next(r for r in rows if r['person_number']=='111113')
        self.assertIn('VorgesetzteNeu Nachname6',person['after']['employments'][0]['manager_names'])
        self.assertIn('Rufname6 Nachname6',person['before']['employments'][0]['manager_names'])
        self.assertEqual(before,self.db.total_changes)
        self.assertNotIn('VorgesetzteNeu',sap.snapshot(self.db,'111116')['person']['first_name'])

    def test_person_preview_can_start_apply_and_context_survives_selection(self):
        batch=self.changed();row=self.row(batch)
        url=f"/stammdaten/abgleich/person/{row['id']}"
        html=self.client.get(url,query_string={'plan_cycle':self.cycle_id,'back':f'/stammdaten/abgleich?batch_id={batch}&state=data'}).text
        self.assertIn('Daten dieser Person zur Übernahme prüfen',html)
        self.assertIn('Rufname6 Nachname6',html)
        response=self.client.post('/stammdaten/abgleich/auswahl',data={'csrf_token':self.csrf,'selected':f"{row['id']}:{row['revision']}",'batch_id':batch,'plan_cycle':self.cycle_id})
        self.assertEqual(response.status_code,200)
        self.assertIn(f'name="plan_cycle" value="{self.cycle_id}"',response.text)
        self.assertIn('Direkt vorgesetzt:',response.text)
        response=self.client.post('/stammdaten/abgleich/uebernehmen',data={'csrf_token':self.csrf,'selected':f"{row['id']}:{row['revision']}",'batch_id':batch,'plan_cycle':self.cycle_id,'checked':'yes','reason':'Geprüft'})
        self.assertIn('plan_cycle='+str(self.cycle_id),response.location)

    def test_followup_completion_needs_result_and_revalidates_current_context(self):
        batch=self.changed();self.apply(batch);row=self.row(batch)
        url=f"/stammdaten/abgleich/person/{row['id']}"
        payload={'csrf_token':self.csrf,'revision':row['revision'],'context':sap.context_token(self.db,row['person_number']),'action':'followup_done','reason':''}
        self.client.post(url,data=payload)
        self.assertEqual(self.row(batch)['followup_status'],'open')
        self.db.execute("UPDATE employees SET first_name='Geändert' WHERE pn='111113'");self.db.commit()
        self.client.post(url,data={**payload,'reason':'Prüfung dokumentiert'})
        self.assertEqual(self.row(batch)['followup_status'],'open')
        self.client.post(url,data={**payload,'context':sap.context_token(self.db,row['person_number']),'reason':'Keine weiteren Unterlagen nötig; Rückblick bleibt bei bisheriger FK'})
        self.assertEqual(self.row(batch)['followup_status'],'done')

    def test_impacts_show_people_and_years_instead_of_technical_case(self):
        batch=self.changed();self.apply(batch);row=self.row(batch)
        response=self.client.get(f"/stammdaten/abgleich/person/{row['id']}")
        self.assertEqual(response.status_code,200)
        self.assertIn('Rufname3 Nachname3 · 2025/2026',response.text)
        self.assertIn('Folgearbeit abschliessen',response.text)
        self.assertIn('Diese Bestätigung dokumentiert dein Prüfergebnis',response.text)
        self.assertIn('back=',response.text)

    def test_counts_exclude_complete_parts_and_foreign_return_path(self):
        counts=planning_views.cycle_progress(self.db,self.cycle_id)
        self.db.execute("UPDATE document_obligations SET status='complete' WHERE id=(SELECT id FROM hr_resolved_obligations WHERE cycle_id=? AND required=1 LIMIT 1)",(self.cycle_id,));self.db.commit()
        self.assertEqual(planning_views.cycle_progress(self.db,self.cycle_id)['open_parts'],counts['open_parts']-1)
        batch=self.changed();row=self.row(batch)
        html=self.client.get(f"/stammdaten/abgleich/person/{row['id']}?back=//example.invalid").text
        self.assertNotIn('href="//example.invalid',html)

    def test_filtered_back_survives_individual_apply_preview_and_post(self):
        batch=self.changed();row=self.row(batch)
        back=f'/stammdaten/abgleich?batch_id={batch}&state=data&q=Rufname3&plan_cycle={self.cycle_id}'
        payload={'csrf_token':self.csrf,'selected':f"{row['id']}:{row['revision']}",'batch_id':batch,'plan_cycle':self.cycle_id,'back':back}
        preview=self.client.post('/stammdaten/abgleich/auswahl',data=payload)
        self.assertIn('state=data&amp;q=Rufname3',preview.text)
        response=self.client.post('/stammdaten/abgleich/uebernehmen',data={**payload,'checked':'yes','reason':'Übernahme geprüft'})
        self.assertEqual(response.location,back)

    def test_under_year_event_returns_to_followup_without_closing_it(self):
        batch=self.changed();self.apply(batch);row=self.row(batch)
        back=f"/stammdaten/abgleich/person/{row['id']}?plan_cycle={self.cycle_id}"
        form=self.client.get('/dialoge',query_string={'back':back,'person':'Nachname3 Rufname3','next_year':2025})
        self.assertIn('Zurück zur aufrufenden Aufgabe',form.text)
        self.assertIn('name="back"',form.text)
        response=self.client.post('/dialog-events',data={'csrf_token':self.csrf,'back':back,'employee_pn':'111113','assignment_number':'1',
            'manager_pn':'111116','event_type':'interim','required_scope':'review_only','review_year':2025,
            'period_start':'2025-03-01','period_end':'2025-08-31','reason':'Zusätzlichen unterjährigen Gesprächsbedarf geprüft','cycle_id':self.cycle_id})
        self.assertEqual(response.location,back)
        self.assertEqual(self.row(batch)['followup_status'],'open')
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM dialog_events WHERE source='manual'").fetchone()[0],1)
        html=self.client.get('/dialoge?back=//example.invalid').text
        self.assertNotIn('href="//example.invalid',html)
