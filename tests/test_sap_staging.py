"""SAP observation/application separation and continuous dialogue regression cases."""
import io
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch
from zipfile import ZipFile
import pandas as pd
from tests import test_goal_workflow as fixtures
from tests import test_word_packages as old_fixtures
from tests import test_word_pdf_imports as pdf_fixtures
from webapp.db import init_db
from webapp.services import sap_staging as sap,part_responsibilities as parts,dialog_events,cycles,word_packages,word_dispatch
from webapp.services import word_pdf_imports as pdfs
from webapp.services.cockpit import cockpit_overview


class SapStagingTest(unittest.TestCase):
    setUp=fixtures.GoalWorkflowTest.setUp
    tearDown=fixtures.GoalWorkflowTest.tearDown

    def frame(self):return pd.read_excel(self.root/'sap.xlsx',dtype=object)

    def preview(self,frame,name='changed.xlsx'):
        path=self.root/name;frame.to_excel(path,index=False)
        return sap.stage(self.db,path,original_filename=name)

    def row(self,batch,pn='111113'):
        return self.db.execute('SELECT * FROM hr_sap_changes WHERE batch_id=? AND person_number=?',(batch,pn)).fetchone()

    def changed(self,*,field='OE Bez.',value='Neue OE',name='changed.xlsx'):
        frame=self.frame();frame.loc[frame['ID_NO_ZERO'].astype(str)=='111113',field]=value
        return self.preview(frame,name)

    def apply(self,batch,pns=('111113',)):
        return sap.apply(self.db,{self.row(batch,pn)['id']:self.row(batch,pn)['revision'] for pn in pns},reason='Originalexport und Auswirkungen an der Person geprüft')

    def manual(self,**updates):
        values=dict(employee_pn='111113',assignment_number='1',manager_pn='111116',event_type='interim',required_scope='review_only',
            review_year=2025,period_start='2025-03-01',period_end='2025-08-31',reason='Separates unterjähriges Gespräch bestätigt',cycle_id=self.cycle_id)
        values.update(updates)
        return dialog_events.create_manual_event(self.db,**values)

    def test_preview_does_not_mutate_live_data_and_duplicate_is_idempotent(self):
        tables=('employees','persons','employment_assignments','dialog_cases','dialog_events','document_obligations','sap_imports','reporting_lines')
        before={t:[tuple(r) for r in self.db.execute('SELECT * FROM '+t)] for t in tables}
        batch=self.changed()
        for t in tables:self.assertEqual(before[t],[tuple(r) for r in self.db.execute('SELECT * FROM '+t)])
        self.assertEqual(self.row(batch)['category'],'changed')
        self.assertEqual(sap.stage(self.db,self.root/'changed.xlsx',original_filename='renamed.xlsx'),batch)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM hr_sap_batches').fetchone()[0],1)

    def test_partial_application_preserves_missing_people_cases_and_history(self):
        frame=self.frame();frame=frame[frame['ID_NO_ZERO'].astype(str)=='111113'].copy();frame['OE Bez.']='Neue OE'
        cases=[tuple(r) for r in self.db.execute('SELECT * FROM dialog_cases')]
        active=[tuple(r) for r in self.db.execute("SELECT pn,active FROM employees WHERE pn<>'111113'")]
        old=parts.resolve(self.db,self.case_id)
        batch=self.preview(frame);imported=self.apply(batch)
        self.assertIsNotNone(imported);self.assertEqual(self.db.execute("SELECT org_unit FROM employees WHERE pn='111113'").fetchone()[0],'Neue OE')
        self.assertEqual(cases,[tuple(r) for r in self.db.execute('SELECT * FROM dialog_cases')])
        self.assertEqual(active,[tuple(r) for r in self.db.execute("SELECT pn,active FROM employees WHERE pn<>'111113'")])
        self.assertEqual(parts.resolve(self.db,self.case_id)['form_org_unit'],old['form_org_unit'])
        self.assertEqual(self.db.execute('SELECT origin FROM hr_part_responsibilities WHERE obligation_id=?',(old['obligation_id'],)).fetchone()[0],'preserved')
        self.assertEqual(cycles.synchronize_cycle_with_import(self.db,cycle_id=self.cycle_id,sap_import_id=imported)['deactivated'],0)
        self.assertEqual(self.row(batch)['followup_status'],'open')
        init_db(self.db)
        self.assertEqual(cases,[tuple(r) for r in self.db.execute('SELECT * FROM dialog_cases')])
        self.assertIn('kein vollständiger',self.db.execute('SELECT warnings_json FROM sap_imports WHERE id=?',(imported,)).fetchone()[0].lower())

    def test_manual_responsibility_survives_sap_manager_change_without_false_dates(self):
        parts.assign(self.db,self.case_id,kind='review',manager_pn='111114',form_org_source='manager',period_start='2025-01-01',period_end='2025-08-31',expected_revision=0,reason='Bisherige Führungskraft bleibt für Rückblick zuständig')
        original=dict(self.db.execute('SELECT * FROM hr_part_responsibilities').fetchone())
        batch=self.changed(field='Dir. Vorgesetzter (PN)',value='111114');imported=self.apply(batch)
        self.assertEqual(original,dict(self.db.execute('SELECT * FROM hr_part_responsibilities WHERE obligation_id=?',(original['obligation_id'],)).fetchone()))
        dates=self.db.execute('SELECT valid_from,valid_to FROM manager_assignments WHERE sap_import_id=?',(imported,)).fetchall()
        self.assertTrue(dates);self.assertTrue(all(tuple(r)==('','') for r in dates))
        self.assertEqual(parts.resolve(self.db,self.case_id,'outlook')['manager_pn'],'111116')

    def test_conflicting_manager_and_dates_cannot_be_applied_but_other_people_can(self):
        frame=self.frame();copy=frame[frame['ID_NO_ZERO'].astype(str)=='111113'].copy();copy['Dir. Vorgesetzter (PN)']='111114'
        frame=pd.concat([frame,copy],ignore_index=True);batch=self.preview(frame)
        self.assertEqual(self.row(batch)['category'],'conflict')
        with self.assertRaisesRegex(ValueError,'widersprüchlichen'):self.apply(batch)
        before=self.db.execute("SELECT * FROM employees WHERE pn='111113'").fetchone()
        self.apply(batch,('111115',))
        self.assertEqual(tuple(before),tuple(self.db.execute("SELECT * FROM employees WHERE pn='111113'").fetchone()))
        next_batch=self.changed(field='Eintritt',value='kein Datum',name='invalid.xlsx')
        self.assertEqual(self.row(next_batch)['category'],'conflict')

    def test_missing_assignment_is_retained_during_other_changes(self):
        frame=self.frame();copy=frame[frame['ID_NO_ZERO'].astype(str)=='111113'].copy();copy['Ans.']='2';copy['OE Bez.']='Zweite OE'
        batch=self.preview(pd.concat([frame,copy],ignore_index=True));self.apply(batch)
        second=self.changed(name='second.xlsx');self.apply(second)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM employment_assignments WHERE person_number='111113'").fetchone()[0],2)
        self.assertEqual(sap.snapshot(self.db,'111113')['employments'][1]['org_unit'],'Zweite OE')

    def test_unformatted_numeric_dates_require_clarification(self):
        before=sap.snapshot(self.db,'111113')
        for index,value in enumerate((45292,45292.5,True)):
            with self.subTest(value=value):
                batch=self.changed(field='Eintritt',value=value,name=f'numeric-date-{index}.xlsx')
                self.assertEqual(self.row(batch)['category'],'conflict')
                self.assertIn('Ungültiges Datum: Eintritt',self.row(batch)['issues_json'])
                with self.assertRaisesRegex(ValueError,'widersprüchlichen'):self.apply(batch)
                self.assertEqual(sap.snapshot(self.db,'111113'),before)
        batch=self.changed(field='Eintritt',value=pd.Timestamp('2025-03-01'),name='calendar-date.xlsx')
        self.assertEqual(self.row(batch)['category'],'changed')
        self.apply(batch)
        self.assertEqual(sap.snapshot(self.db,'111113')['employments'][0]['entry_date'],'2025-03-01')

    def test_stale_comparison_requires_explicit_refresh_and_audits_prior_basis(self):
        batch=self.changed();row=self.row(batch)
        with self.db:self.db.execute("UPDATE employees SET email='changed@example.invalid' WHERE pn='111113'")
        with self.assertRaisesRegex(ValueError,'veraltet'):self.apply(batch)
        sap.resolve(self.db,row['id'],revision=0,action='recompare',reason='Neuen Vergleichsstand am Original geprüft',token=sap.context_token(self.db,'111113'))
        self.assertEqual(self.row(batch)['revision'],1);self.apply(batch)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM hr_sap_decisions WHERE change_id=?',(row['id'],)).fetchone()[0],2)

    def test_transaction_failure_keeps_all_selected_people_unmodified(self):
        batch=self.changed();before=sap.snapshot(self.db,'111113')
        with patch('webapp.services.sap_staging.write_person',side_effect=OSError('Test: nicht gespeichert')):
            with self.assertRaises(OSError):self.apply(batch)
        self.assertEqual(sap.snapshot(self.db,'111113'),before)
        self.assertEqual(self.row(batch)['data_status'],'pending')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM hr_part_responsibilities').fetchone()[0],0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM sap_imports').fetchone()[0],1)

    def test_repeated_application_and_unchanged_manual_difference_create_no_duplicate_work(self):
        batch=self.changed();self.apply(batch);count=self.db.execute('SELECT COUNT(*) FROM sap_imports').fetchone()[0]
        self.assertIsNone(self.apply(batch));self.assertEqual(self.db.execute('SELECT COUNT(*) FROM sap_imports').fetchone()[0],count)
        frame=self.frame();frame.loc[frame['ID_NO_ZERO'].astype(str)=='111113','OE Bez.']='Neue OE';frame['Unverwendete Exportnotiz']='anderer Dateicontainer'
        next_batch=self.preview(frame,'repeated.xlsx')
        self.assertEqual(next_batch,batch)
        frame.loc[frame['ID_NO_ZERO'].astype(str)=='111115','OE Bez.']='Weitere Änderung'
        next_batch=self.preview(frame,'other-person.xlsx')
        self.assertEqual(self.row(next_batch)['category'],'unchanged')
        self.apply(next_batch)
        # The still-open earlier consequence remains visible; unchanged input
        # must neither duplicate nor silently close that work.
        self.assertEqual(self.row(batch)['followup_status'],'open')
        self.assertIsNone(self.row(batch)['superseded_by'])

    def test_followup_closure_detects_intervening_part_change(self):
        batch=self.changed();self.apply(batch);row=self.row(batch);token=sap.context_token(self.db,'111113')
        part=parts.resolve(self.db,self.case_id,'outlook')
        parts.assign(self.db,self.case_id,kind='outlook',manager_pn='111114',form_org_source='employee',period_start=part['period_start'],period_end=part['period_end'],expected_revision=part['responsibility_revision'],reason='Neue Zuständigkeit bewusst festgelegt')
        with self.assertRaisesRegex(ValueError,'Dialogstand'):sap.resolve(self.db,row['id'],revision=row['revision'],action='followup_done',reason='Alle Auswirkungen nochmals geprüft',token=token)
        sap.resolve(self.db,row['id'],revision=row['revision'],action='followup_done',reason='Ausblick neu zugewiesen; Rückblick bleibt bestehen',token=sap.context_token(self.db,'111113'))
        self.assertEqual(self.row(batch)['followup_status'],'done')

    def test_missing_person_retention_is_audited_and_not_an_exit(self):
        frame=self.frame();frame=frame[frame['ID_NO_ZERO'].astype(str)!='111113'];batch=self.preview(frame);row=self.row(batch)
        self.assertEqual(row['category'],'missing')
        sap.resolve(self.db,row['id'],revision=0,action='retain',reason='Person fehlt wegen eingeschränktem Exportumfang',token=sap.context_token(self.db,'111113'))
        self.assertEqual(self.db.execute("SELECT active FROM employees WHERE pn='111113'").fetchone()[0],1)
        self.assertEqual(self.row(batch)['data_status'],'retained')

    def test_manual_dialog_after_closed_campaign_is_operational_and_repeat_safe(self):
        with self.db:self.db.execute("UPDATE cycles SET status='abgeschlossen' WHERE id=?",(self.cycle_id,))
        previous=[tuple(r) for r in self.db.execute('SELECT * FROM dialog_cases')]
        event=self.manual();self.assertEqual(self.manual(),event)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM dialog_cases').fetchone()[0],len(previous)+1)
        self.assertEqual(self.db.execute('SELECT status FROM cycles WHERE id=?',(self.cycle_id,)).fetchone()[0],'abgeschlossen')
        for row in previous:self.assertEqual(row,tuple(self.db.execute('SELECT * FROM dialog_cases WHERE id=?',(row[0],)).fetchone()))
        path,manifest=word_packages.create_word_package(self.db,cycle_id=self.cycle_id,manager_pn='111116',case_id=event,template_paths=self.paths,output_dir=self.root/'manual-output')
        self.assertEqual(manifest['documents'][0]['period_start'],'2025-03-01')
        with ZipFile(path) as archive:self.assertTrue(archive.testzip() is None)
        self.assertEqual(self.db.execute('SELECT sap_leading FROM dialog_events WHERE event_id=?',(event,)).fetchone()[0],0)
        path=pdf_fixtures.sample_pdf(self.root/'return.pdf',kind='review',year=2025)
        incoming=pdfs.stage_pdf(self.db,path,filename=path.name,directory=self.root/'intake')[0]
        reviewed=pdf_fixtures.WordPdfImportsTest.reviewed(self,incoming)
        doc=pdfs.confirm_import(self.db,incoming,reviewed=reviewed,assignment='1',case_id=event,historical=False,reason='Unterjährigen Rücklauf am Original und Zeitraum geprüft')
        self.assertEqual(self.db.execute('SELECT case_id FROM official_documents WHERE id=?',(doc,)).fetchone()[0],event)

    def test_manual_event_without_cycle_creates_only_requested_case(self):
        count=self.db.execute('SELECT COUNT(*) FROM dialog_cases').fetchone()[0]
        event=self.manual(cycle_id=None,review_year=2027,period_start='2027-01-01',period_end='2027-06-30')
        row=self.db.execute('SELECT cycle_id,legacy_case_id FROM dialog_events WHERE event_id=?',(event,)).fetchone()
        self.assertIsNotNone(row['cycle_id']);self.assertEqual(row['legacy_case_id'],event)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM dialog_cases').fetchone()[0],count+1)
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(),[])

    def test_multiple_conversations_have_distinct_word_filenames(self):
        self.manual();self.manual(period_start='2025-09-01',period_end='2025-12-31')
        path,manifest=word_packages.create_word_package(self.db,cycle_id=self.cycle_id,manager_pn='111116',template_paths=self.paths,output_dir=self.root/'combined')
        names=[d['filename'] for d in manifest['documents']]
        self.assertEqual(len(names),len(set(names)))
        with ZipFile(path) as archive:self.assertEqual(len(archive.namelist()),len(set(archive.namelist())))

    def test_routes_protect_mutations_show_preview_and_keep_filters(self):
        self.assertEqual(self.client.get('/stammdaten').status_code,302)
        data=(self.root/'sap.xlsx').read_bytes()
        self.assertEqual(self.client.post('/stammdaten/abgleich/upload',data={'sap_file':(io.BytesIO(data),'sap.xlsx')}).status_code,400)
        response=self.client.post('/imports',data={'csrf_token':self.csrf,'sap_file':(io.BytesIO(data),'sap.xlsx')},follow_redirects=True)
        self.assertEqual(response.status_code,200);self.assertIn('noch unverändert',response.text)
        batch=self.changed();row=self.row(batch)
        response=self.client.get(f"/stammdaten/abgleich/person/{row['id']}?back=/stammdaten/abgleich?state=changed%26q=111113")
        self.assertEqual(response.status_code,200);self.assertIn('state=changed&amp;q=111113',response.text)
        selected=f"{row['id']}:{row['revision']}"
        response=self.client.post('/stammdaten/abgleich/auswahl',data={'csrf_token':self.csrf,'selected':selected})
        self.assertIn('1 Person(en)',response.text)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM sap_imports').fetchone()[0],1)
        response=self.client.post('/stammdaten/abgleich/uebernehmen',data={'csrf_token':self.csrf,'selected':selected,'reason':'Originalexport vor Übernahme geprüft','checked':'yes'},follow_redirects=True)
        self.assertEqual(response.status_code,200);self.assertIn('Dialogentscheidungen bleiben separat offen',response.text)
        self.assertTrue(any(t['target']=='sap_preview' for t in cockpit_overview(self.db)['tasks']))

    def test_legacy_import_service_cannot_bypass_preview(self):
        from webapp.services.sap_import import import_sap_workbook
        with self.assertRaisesRegex(ValueError,'Vorschau'):import_sap_workbook(self.db,self.root/'sap.xlsx',original_filename='sap.xlsx',stored_filename='sap.xlsx')

    def test_original_change_blocks_application(self):
        batch=self.changed();(self.root/'changed.xlsx').write_bytes(b'changed after preview')
        with self.assertRaisesRegex(ValueError,'Originalexport'):self.apply(batch)
        self.assertEqual(self.row(batch)['data_status'],'pending')

    def test_exact_reupload_restores_missing_original_without_duplicate(self):
        batch=self.changed();source=self.root/'changed.xlsx';contents=source.read_bytes();source.unlink()
        restored=self.root/'restored.xlsx';restored.write_bytes(contents)
        self.assertEqual(sap.stage(self.db,restored,original_filename='restored.xlsx'),batch)
        self.assertEqual(self.db.execute('SELECT stored_path FROM hr_sap_batches WHERE id=?',(batch,)).fetchone()[0],str(restored.resolve()))
        self.apply(batch)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM audit_log WHERE action='sap_original_restored'").fetchone()[0],1)

    def test_conflicting_org_units_are_not_silently_reduced_to_first_row(self):
        frame=self.frame();copy=frame[frame['ID_NO_ZERO'].astype(str)=='111113'].copy();copy['OE Bez.']='Widersprechende OE'
        batch=self.preview(pd.concat([frame,copy],ignore_index=True))
        self.assertEqual(self.row(batch)['category'],'conflict')
        with self.assertRaises(ValueError):self.apply(batch)

    def test_manager_change_preview_includes_affected_employee_dialogs(self):
        ids={r['case_id'] for r in sap.impacts(self.db,'111116')}
        self.assertIn(self.case_id,ids)

    def test_years_and_manual_submission_are_visible_without_reopening(self):
        with self.db:self.db.execute("UPDATE cycles SET status='abgeschlossen' WHERE id=?",(self.cycle_id,))
        response=self.client.get('/dialoge')
        self.assertEqual(response.status_code,200);self.assertIn('Alle Jahre und offenen Altfälle',response.text)
        self.assertIn('csrf_token',response.text)
        self.assertEqual(self.client.get('/stammdaten?history=yes').status_code,200)
        self.assertEqual(self.client.post('/dialog-events',data={}).status_code,400)

    def test_new_migration_preserves_case_references_and_foreign_keys(self):
        import webapp.migrations as migrations
        old=old_fixtures.WordPackagesTest();old.setUp()
        try:
            directory=Path(migrations.__file__).with_suffix('')
            with patch.object(migrations.Path,'glob',return_value=sorted(directory.glob('00[123]*.sql'))):migrations.migrate(old.db)
            incoming=pdfs.stage_pdf(old.db,pdf_fixtures.sample_pdf(old.root/'old.pdf',kind='review',year=2025),filename='old.pdf',directory=old.root/'intake')[0]
            reviewed=pdf_fixtures.WordPdfImportsTest.reviewed(old,incoming)
            doc=pdfs.confirm_import(old.db,incoming,reviewed=reviewed,assignment='1',case_id=old.case_id,historical=False,reason='Bestehender Rücklauf vor Migration geprüft')
            tables=('dialog_cases','dialog_events','document_obligations','official_documents','word_pdf_imports')
            before={t:[tuple(r) for r in old.db.execute('SELECT * FROM '+t)] for t in tables}
            with old.db:old.db.execute("UPDATE sqlite_sequence SET seq=10000 WHERE name='dialog_cases'")
            migrations.migrate(old.db);init_db(old.db)
            for table,rows in before.items():self.assertEqual(rows,[tuple(r) for r in old.db.execute('SELECT * FROM '+table)])
            self.assertEqual(old.db.execute('PRAGMA foreign_keys').fetchone()[0],1)
            self.assertEqual(old.db.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(old.db.execute("SELECT seq FROM sqlite_sequence WHERE name='dialog_cases'").fetchone()[0],10000)
            self.assertIsNotNone(old.db.execute('SELECT * FROM official_documents WHERE id=?',(doc,)).fetchone())
        finally:old.tearDown()


if __name__=='__main__':unittest.main()
