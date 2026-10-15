from __future__ import annotations

import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from reportlab.pdfgen import canvas

from webapp import create_app
from webapp.db import get_db
from webapp.services.cycles import create_cycle
from webapp.services.sap_import import import_sap_workbook
from webapp.services.word_pdf import inspect_word_pdf
from webapp.services.word_pdf_imports import stage_pdf, confirm_import, matching_cases
from webapp.services.word_packages import prior_goals
from webapp.services.documents import confirm_digital_signature
from tests.sample_data import create_sap_sample
from webapp.adapters.outlook import InboundAttachment, InboundMessage
from webapp.services.mail_intake import process_inbound_messages, resolve_inbound_message, mail_inbox_overview


def sample_pdf(path, *, printed=False, old=False, marker='', kind='review', year=2025, narrative=False):
    c=canvas.Canvas(str(path),pagesize=(595,842))
    if printed:
        c.translate(0,842); c.scale(.75,-.75)
    def text(x,y,value):
        if printed:
            c.saveState(); c.translate(x/.75,(842-y)/.75); c.scale(1,-1); c.setFont('Helvetica',12);c.drawString(0,0,value);c.restoreState()
        else:
            c.setFont('Helvetica',9);c.drawString(x,y,value)
    def box(x,y,w,h,blue=False):
        c.setFillColorRGB(*((.882,.965,1) if blue else (.949,.949,.949)))
        if printed:
            x,y,w,h=x/.75,(842-y)/.75,w/.75,-h/.75
            p=c.beginPath();p.moveTo(x,y);p.lineTo(x+w,y);p.lineTo(x+w,y+h);p.lineTo(x,y+h);p.close();c.drawPath(p,fill=1,stroke=0)
        else:
            c.rect(x,y,w,h,fill=1,stroke=0)
        c.setFillColorRGB(0,0,0)
    label='Ausblick' if kind=='outlook' else 'Rückblick'
    for y,s in [(805,f'Mitarbeitenden-Dialog (MD) - {label}'),(785,'Name: Test PN: 111113'),(770,'Name VG: Andere Person PN VG: 111116'),(755,f'Wird der {label} durchgeführt? Ja'),(740,f'{label} auf: 01.01.{year} bis 31.12.{year} Gespräch vom: 15.01.{year+1}')]:
        text(40,y,s)
    if not old:
        text(40,705,'1. Zielvereinbarung' if kind=='outlook' else 'Leistungsziele aus dem Vorjahr')
        for x,w,value in [(40,150,'1. Erstes Ziel'),(191,130,'Messbar'),(322,160,'1. Schritt eins'),(483,70,'31.12.')]:
            box(x,640,w,50,kind=='outlook');text(x+4,677,value)
            if x==322:text(x+4,664,'2. Schritt zwei')
        text(40,600,'Selbstmanagement (Eigenverantwortung)')
        for x,w,value in [(40,150,'1. Entwicklung'),(191,130,'Kriterium'),(322,160,'Plan'),(483,70,'30.06.')]:
            box(x,540,w,45,kind=='outlook');text(x+4,572,value)
        if kind=='review':
            box(40,510,513,23,True);text(44,520,'Einschätzung:')
    text(40,460,marker)
    if narrative:
        text(40,440,'2. Bemerkungen zum Gespräch')
        text(40,420,'Gibt es allgemeine Bemerkungen?')
        box(40,350,513,55,True)
        text(44,390,'Erster Absatz'); text(44,375,'1. Ein Schritt'); text(44,360,'2. Noch ein Schritt')
    c.save()
    return path


class WordPdfImportsTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.app=create_app({'TESTING':True,'AUTH_DISABLED':True,'SECRET_KEY':'test','DATABASE':str(self.root/'db'),
            'STORAGE_ROOT':str(self.root/'storage'),'BACKUP_ROOT':str(self.root/'backup'),'DOSSIER_HANDOFF_ROOT':str(self.root/'handoff')})
        self.context=self.app.app_context();self.context.push();self.db=get_db()
        sample=create_sap_sample(self.root/'sap.xlsx')
        imported=import_sap_workbook(self.db,sample,original_filename='sap.xlsx',stored_filename='sap.xlsx')
        self.cycle=create_cycle(self.db,review_year=2025,sap_import_id=imported.import_id)
        self.case=self.db.execute("SELECT case_id FROM dialog_cases WHERE employee_pn='111113'").fetchone()[0]
    def tearDown(self):
        self.context.pop();self.tmp.cleanup()
    def stage(self,**kwargs):
        path=sample_pdf(self.root/'input.pdf',**kwargs)
        return stage_pdf(self.db,path,filename='Ruecklauf.pdf',directory=self.root/'queue')[0]
    def reviewed(self,item_id):
        parsed=json.loads(self.db.execute('SELECT parsed_json FROM word_pdf_imports WHERE id=?',(item_id,)).fetchone()[0])
        data=dict(parsed['data']);data['rating']='C' if data['document_kind']=='review' else ''
        for key in ('performance_goals','development_goals'):
            for goal in parsed[key]:goal.pop('evidence',None)
        return {k:parsed[k] for k in ('performance_goals','development_goals','assessments')}|{'data':data,'scope':'full'}
    def confirm(self,item_id,reviewed=None,**kwargs):
        return confirm_import(self.db,item_id,reviewed=reviewed or self.reviewed(item_id),assignment='1',case_id=self.case,historical=False,reason='',**kwargs)

    def test_original_survives_robot_consumption_and_release_is_idempotent(self):
        item=self.stage(); doc=self.confirm(item)
        original=Path(self.db.execute('SELECT stored_path FROM official_documents WHERE id=?',(doc,)).fetchone()[0])
        result=confirm_digital_signature(self.db,document_id=doc,handoff_dir=self.root/'handoff')
        published=self.root/'handoff'/result['handoff_filename']
        self.assertTrue(original.is_file());self.assertEqual(original.read_bytes(),published.read_bytes())
        published.unlink()  # Robot consumed its copy.
        confirm_digital_signature(self.db,document_id=doc,handoff_dir=self.root/'handoff')
        self.assertFalse(published.exists())
        self.assertEqual(self.app.test_client().get(f'/word-pdf-imports/{item}/original').status_code,200)

    def test_interrupted_mail_resumes_existing_pdf_without_duplicate_or_move(self):
        from unittest.mock import patch
        path=sample_pdf(self.root/'mail.pdf')
        message=InboundMessage('resume','<resume>','test@example.invalid','MD Rückblick',datetime.now(timezone.utc),(InboundAttachment(1,'Rueckblick.pdf',path.read_bytes()),InboundAttachment(2,'Zusatz.txt',b'Andere Aufgabe')))
        options=dict(messages=[message],inbox_dir=self.root/'inbox',pdf_dir=self.root/'processed',handoff_dir=self.root/'handoff',target_folder='MD')
        with patch('webapp.services.mail_intake._insert_attachment',side_effect=RuntimeError('Unterbrochen')):
            with self.assertRaises(RuntimeError):process_inbound_messages(self.db,**options)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_pdf_imports').fetchone()[0],1)
        process_inbound_messages(self.db,**options)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_pdf_imports').fetchone()[0],1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM inbound_mail_attachments').fetchone()[0],2)
        progress=mail_inbox_overview(self.db)['mail_messages'][0]
        self.assertEqual(progress['status'],'review_required')
        self.assertIn('PDF-Prüfung offen',progress['attachments'][0]['progress'])
        self.assertIn('Fremdanlage',progress['attachments'][1]['progress'])
        self.assertFalse(list((self.root/'handoff').glob('*.pdf')))

    def test_hr_followup_status_and_revision_are_persisted(self):
        from webapp.services.analytics import analytics_data
        item=self.stage(kind='outlook',year=2026);reviewed=self.reviewed(item)
        reviewed['data']['career_requested']='ja';self.confirm(item,reviewed)
        client=self.app.test_client()
        url=f'/hr-followups/{self.case}/career'
        client.post(url,data={'status':'kontaktiert','note':'Gespräch vereinbart','revision':''})
        rows=analytics_data(self.db,cycle_id=self.cycle)['followups']
        self.assertEqual(rows[0]['contact_status'],'kontaktiert')
        self.assertEqual(rows[0]['contact_note'],'Gespräch vereinbart')
        client.post(url,data={'status':'abgeschlossen','revision':''})
        self.assertEqual(analytics_data(self.db,cycle_id=self.cycle)['followups'][0]['contact_status'],'kontaktiert')
        client.post(url,data={'status':'abgeschlossen','revision':rows[0]['contact_updated']})
        self.assertEqual(analytics_data(self.db,cycle_id=self.cycle)['followups'][0]['contact_status'],'abgeschlossen')

    def test_inbound_scan_requires_explicit_signature_check_and_keeps_original(self):
        item=self.stage();reviewed=self.reviewed(item);reviewed['data']['rating']='D'
        doc=self.confirm(item,reviewed)
        confirm_digital_signature(self.db,document_id=doc,handoff_dir=self.root/'handoff')
        scan=self.stage(marker='Geprüfter unterschriebener Scan')
        client=self.app.test_client();url=f'/word-pdf-imports/{scan}/scan'
        client.post(url,data={'case_id':self.case,'revision':'0'})
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM official_documents WHERE variant='scan'").fetchone()[0],0)
        response=client.post(url,data={'case_id':self.case,'revision':'0','scan_checked':'yes'})
        self.assertEqual(response.status_code,302)
        row=self.db.execute("SELECT * FROM official_documents WHERE variant='scan'").fetchone()
        self.assertTrue(Path(row['stored_path']).is_file())
        self.assertEqual(row['handoff_status'],'staged')
        self.assertEqual(self.db.execute('SELECT status FROM word_pdf_imports WHERE id=?',(scan,)).fetchone()[0],'imported')
        from webapp.services.documents import import_handwritten_scan
        handoff=Path(self.app.config['DOSSIER_HANDOFF_ROOT'])
        published=handoff/row['handoff_filename'];published.unlink()
        import_handwritten_scan(self.db,case_id=self.case,document_kind='review',path=Path(row['stored_path']),original_filename='scan.pdf',handoff_dir=handoff)
        self.assertFalse(published.exists())
        self.assertEqual(client.get(f"/documents/{row['id']}/original").status_code,200)

    def test_geometry_for_rectangle_and_print_paths_preserves_lists(self):
        results=[]
        for printed in (False,True):
            p=sample_pdf(self.root/f'{printed}.pdf',printed=printed)
            result=inspect_word_pdf(p);results.append(result)
            self.assertEqual(len(result['performance_goals']),1)
            self.assertEqual(len(result['development_goals']),1)
            self.assertEqual(result['assessments'],{})
            self.assertEqual(result['performance_goals'][0]['steps'],'1. Schritt eins\n2. Schritt zwei')
            self.assertEqual(result['development_goals'][0]['competency'],'Selbstmanagement')
        for key in ('performance_goals','development_goals'):
            for result in results:
                for goal in result[key]:goal.pop('evidence')
            self.assertEqual(results[0][key],results[1][key])

    def test_narrative_cells_retain_numbered_lines_for_both_export_paths(self):
        for printed in (False,True):
            with self.subTest(printed=printed):
                path=sample_pdf(self.root/'narrative.pdf', printed=printed, narrative=True)
                result=inspect_word_pdf(path)
                self.assertEqual(result['narratives']['general_comment'],'Erster Absatz\n1. Ein Schritt\n2. Noch ein Schritt')
                self.assertEqual(result['assessments'],{})

    def test_queue_is_persistent_and_duplicate_does_not_import(self):
        item_id=self.stage()
        duplicate,was_duplicate=stage_pdf(self.db,self.root/'input.pdf',filename='renamed.pdf',directory=self.root/'queue')
        self.assertEqual(duplicate,item_id);self.assertTrue(was_duplicate)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],0)
        response=self.app.test_client().get(f'/word-pdf-imports/{item_id}')
        self.assertEqual(response.status_code,200)
        self.assertIn(b'Erstes Ziel',response.data)
        self.assertEqual(self.app.test_client().get('/ruecklaeufe').status_code,200)

    def test_current_review_excludes_previous_goals_from_current_competencies(self):
        item_id=self.stage();document_id=self.confirm(item_id)
        doc=self.db.execute('SELECT * FROM official_documents WHERE id=?',(document_id,)).fetchone()
        self.assertEqual(doc['handoff_status'],'needs_signature_check')
        self.assertFalse(doc['signature_checked'])
        self.assertEqual(json.loads(doc['data_block_json'])['review_competencies'],'')
        payload=json.loads(self.db.execute('SELECT data_json FROM dialog_cases WHERE case_id=?',(self.case,)).fetchone()[0])
        self.assertEqual(payload['review']['competencies'],[])
        self.assertEqual(len(payload['review']['previous_development_goals']),1)
        confirm_digital_signature(self.db,document_id=document_id,handoff_dir=self.root/'handoff')
        with self.app.test_client().get(f'/word-pdf-imports/{item_id}/original') as response:
            self.assertEqual(response.status_code,200)

    def test_late_outlook_goals_and_replacement_versions(self):
        item_id=self.stage(kind='outlook')
        confirm_import(self.db,item_id,reviewed=self.reviewed(item_id),assignment='1',case_id='',historical=True,reason='Nachgereichter Ausblick')
        goals=prior_goals(self.db,employee_pn='111113',assignment='1',year=2025)
        self.assertEqual(goals[0][0]['title'],'Erstes Ziel')
        self.assertEqual(goals[2],{'word_pdf_import_id':item_id})
        new=self.stage(kind='outlook',marker='Korrektur');reviewed=self.reviewed(new);reviewed['performance_goals'][0]['title']='Korrigiertes Ziel'
        confirm_import(self.db,new,reviewed=reviewed,assignment='1',case_id='',historical=True,reason='Korrigierte Vereinbarung')
        self.assertEqual(prior_goals(self.db,employee_pn='111113',assignment='1',year=2025)[0][0]['title'],'Korrigiertes Ziel')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_pdf_goal_versions').fetchone()[0],2)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],0)

    def test_case_outlook_is_single_goal_source_and_has_correct_year(self):
        item_id=self.stage(kind='outlook',year=2026)
        self.confirm(item_id)
        goals=prior_goals(self.db,employee_pn='111113',assignment='1',year=2026)
        self.assertEqual(len(goals[0]),1)
        self.assertEqual(goals[2],{'case_id':self.case,'word_pdf_import_id':item_id})

    def test_failed_case_assignment_does_not_write_goals_or_mark_done(self):
        item_id=self.stage(kind='outlook',year=2025)
        with self.assertRaisesRegex(ValueError,'Zielzeitraum'):
            self.confirm(item_id)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_pdf_goal_versions').fetchone()[0],0)
        self.assertEqual(self.db.execute('SELECT status FROM word_pdf_imports').fetchone()[0],'pending')

    def test_old_layout_requires_review_note_and_can_be_manually_completed(self):
        item_id=self.stage(old=True)
        with self.assertRaisesRegex(ValueError,'Klärung'):
            self.confirm(item_id)
        reviewed=self.reviewed(item_id);reviewed['performance_goals']=[{'title':'Manuell geprüft'}]
        confirm_import(self.db,item_id,reviewed=reviewed,assignment='1',case_id=self.case,historical=False,reason='Alte Vorlage am Original geprüft')
        self.assertEqual(self.db.execute('SELECT status FROM word_pdf_imports').fetchone()[0],'imported')

    def test_semantic_duplicate_across_export_paths_is_closed_without_reimport(self):
        first=self.stage();self.confirm(first)
        second=self.stage(printed=True)
        self.confirm(second)
        duplicate=self.db.execute('SELECT status,duplicate_of FROM word_pdf_imports WHERE id=?',(second,)).fetchone()
        self.assertEqual(duplicate['status'],'duplicate')
        self.assertEqual(duplicate['duplicate_of'],first)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],1)

    def test_replacement_requires_reason_and_staged_version_cannot_be_replaced(self):
        first=self.stage();doc=self.confirm(first)
        second=self.stage(marker='Revidiert');reviewed=self.reviewed(second);reviewed['data']['rating']='B'
        with self.assertRaisesRegex(ValueError,'Ersetzungsgrund'):
            self.confirm(second,reviewed)
        confirm_digital_signature(self.db,document_id=doc,handoff_dir=self.root/'handoff')
        with self.assertRaisesRegex(ValueError,'Ablageprozess'):
            confirm_import(self.db,second,reviewed=reviewed,assignment='1',case_id=self.case,historical=False,reason='Korrektur')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents WHERE is_current=1').fetchone()[0],1)

    def test_probation_negative_decision_does_not_require_signature_scan(self):
        item_id=self.stage()
        reviewed=self.reviewed(item_id)
        reviewed['data'].update(probation='ja',employment_continues='nein',rating='')
        self.db.execute("UPDATE dialog_events SET event_type='probation_review' WHERE legacy_case_id=?",(self.case,))
        self.db.commit()
        doc=self.confirm(item_id,reviewed)
        self.assertFalse(self.db.execute('SELECT scan_required FROM official_documents WHERE id=?',(doc,)).fetchone()[0])
        self.assertEqual(self.db.execute('SELECT agreement FROM dialog_cases WHERE case_id=?',(self.case,)).fetchone()[0],'')

    def test_ambiguous_assignment_is_never_selected_by_matching(self):
        data={'pn':'111113','document_kind':'review','period_end':'2025-12-31','dialog_date':'2026-01-15'}
        self.assertEqual([c['case_id'] for c in matching_cases(self.db,data)],[self.case])
        self.db.execute("""INSERT INTO dialog_cases(case_id,cycle_id,employee_pn,employment_assignment,manager_pn,suggested_scope,suggestion_reason,updated_at)
            VALUES ('OTHER',?,'111113','2','111116','full','test','2026-01-01')""",(self.cycle,))
        self.db.commit()
        self.assertEqual(len(matching_cases(self.db,data)),2)
        item_id=self.stage()
        with self.assertRaisesRegex(ValueError,'Anstellung'):
            confirm_import(self.db,item_id,reviewed=self.reviewed(item_id),assignment='',case_id=self.case,historical=False,reason='')

    def test_mail_word_pdf_is_queued_and_cannot_be_marked_done_early(self):
        pdf=sample_pdf(self.root/'mail.pdf')
        message=InboundMessage('word-mail','<word@example.invalid>','sender@example.invalid','MD',datetime.now(timezone.utc),(InboundAttachment(1,'neutral-name.pdf',pdf.read_bytes()),))
        moved=[]
        result=process_inbound_messages(self.db,messages=[message],inbox_dir=self.root/'inbox',pdf_dir=self.root/'pdfs',target_folder='MD',move_message=lambda *args:moved.append(args))
        self.assertEqual(result['review'],1);self.assertEqual(moved,[])
        overview=mail_inbox_overview(self.db)
        mail=overview['mail_messages'][0]
        self.assertTrue(mail['attachments'][0]['word_pdf_import_id'])
        with self.assertRaisesRegex(ValueError,'Word-PDF-Prüfung'):
            resolve_inbound_message(self.db,message_id=mail['id'],mailbox_name='Test',target_folder='MD')
        self.confirm(mail['attachments'][0]['word_pdf_import_id'])
        result=resolve_inbound_message(self.db,message_id=mail['id'],mailbox_name='Test',target_folder='MD')
        self.assertEqual(result['status'],'review_completed')

    def test_post_requires_confirmation_and_can_commit_reviewed_form(self):
        item_id=self.stage()
        form={'document_kind':'review','pn':'111113','manager_pn':'111116','period_start':'2025-01-01','period_end':'2025-12-31','dialog_date':'2026-01-15',
              'conducted':'ja','rating':'C','scope':'full','assignment':'1','case_id':self.case,'destination':'case',
              'performance_title':'Geprüftes Ziel','performance_steps':'• Eins\n• Zwei'}
        client=self.app.test_client()
        response=client.post(f'/word-pdf-imports/{item_id}',data=form)
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],0)
        form['checked']='yes'
        response=client.post(f'/word-pdf-imports/{item_id}',data=form)
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],1)

    def nonconducted(self, item_id):
        reviewed = self.reviewed(item_id)
        reviewed['data'].update(conducted='nein', dialog_date='', rating='', no_md_reason='Längere Abwesenheit')
        reviewed['assessments'] = {}
        if reviewed['data']['document_kind']=='outlook':
            reviewed['performance_goals'] = []; reviewed['development_goals'] = []
        return reviewed

    def test_nonconducted_review_leaves_outlook_open_without_signature(self):
        item = self.stage(); doc_id = self.confirm(item, self.nonconducted(item))
        doc = self.db.execute('SELECT * FROM official_documents WHERE id=?',(doc_id,)).fetchone()
        self.assertEqual(doc['variant'],'administrative')
        self.assertFalse(doc['signature_checked']); self.assertFalse(doc['scan_required'])
        case = self.db.execute('SELECT * FROM dialog_cases WHERE case_id=?',(self.case,)).fetchone()
        self.assertEqual(case['status'],'in_bearbeitung')
        self.assertEqual(case['dialog_date'],''); self.assertEqual(case['overall_rating_code'],'')
        obligations = {r['document_kind']: r for r in self.db.execute('SELECT o.* FROM document_obligations o JOIN dialog_events e ON e.id=o.dialog_event_id WHERE e.legacy_case_id=?',(self.case,))}
        self.assertEqual(obligations['review']['status'],'complete')
        self.assertEqual(obligations['outlook']['status'],'open'); self.assertEqual(obligations['outlook']['required'],1)
        with self.assertRaises(ValueError):
            confirm_digital_signature(self.db,document_id=doc_id,handoff_dir=self.root/'handoff')
        self.assertEqual(self.app.test_client().get(f'/cycles/{self.cycle}/cases/{self.case}').status_code,200)

    def test_both_parts_nonconducted_finish_without_goals_or_sap(self):
        from webapp.services.sap_export import collect_sap_upload_rows
        first=self.stage(); self.confirm(first,self.nonconducted(first))
        second=self.stage(kind='outlook',year=2026); self.confirm(second,self.nonconducted(second))
        self.assertEqual(self.db.execute('SELECT status FROM dialog_cases WHERE case_id=?',(self.case,)).fetchone()[0],'kein_md')
        self.assertEqual(self.db.execute('SELECT status FROM dialog_events WHERE legacy_case_id=?',(self.case,)).fetchone()[0],'no_md')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_pdf_goal_versions').fetchone()[0],0)
        with self.assertRaisesRegex(ValueError,'keine neuen'):
            collect_sap_upload_rows(self.db,self.cycle)

    def test_nonconducted_review_and_completed_outlook_are_not_sap_assessment(self):
        from webapp.services.sap_export import collect_sap_upload_rows
        first=self.stage(); self.confirm(first,self.nonconducted(first))
        second=self.stage(kind='outlook',year=2026); doc=self.confirm(second)
        confirm_digital_signature(self.db,document_id=doc,handoff_dir=self.root/'handoff')
        self.assertEqual(self.db.execute('SELECT status FROM dialog_cases WHERE case_id=?',(self.case,)).fetchone()[0],'vollstaendig')
        with self.assertRaisesRegex(ValueError,'keine neuen'):
            collect_sap_upload_rows(self.db,self.cycle)

    def test_nonconducted_requires_reason_and_rejects_invented_facts_or_scope_reduction(self):
        item=self.stage()
        for field,value in [('no_md_reason',''),('dialog_date','2026-01-01'),('rating','C'),('conducted','')]:
            reviewed=self.nonconducted(item); reviewed['data'][field]=value
            with self.subTest(field=field), self.assertRaises(ValueError): self.confirm(item,reviewed)
        reviewed=self.nonconducted(item); reviewed['scope']='review_only'
        with self.assertRaisesRegex(ValueError,'MD-Umfang'): self.confirm(item,reviewed)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],0)

    def test_nonconducted_cannot_replace_completed_or_become_historical_goal_source(self):
        first=self.stage(); doc=self.confirm(first)
        second=self.stage(marker='Nicht durchgeführt')
        with self.assertRaisesRegex(ValueError,'bestehendes Gesprächsdokument'):
            confirm_import(self.db,second,reviewed=self.nonconducted(second),assignment='1',case_id=self.case,historical=False,reason='Korrektur')
        self.assertEqual(self.db.execute('SELECT is_current FROM official_documents WHERE id=?',(doc,)).fetchone()[0],1)
        third=self.stage(kind='outlook')
        with self.assertRaisesRegex(ValueError,'Zielquelle'):
            confirm_import(self.db,third,reviewed=self.nonconducted(third),assignment='1',case_id='',historical=True,reason='Nachreichung')

    def test_conducted_document_cannot_shadow_nonconducted_record(self):
        first=self.stage(); self.confirm(first,self.nonconducted(first))
        second=self.stage(marker='Doch durchgeführt')
        with self.assertRaisesRegex(ValueError,'Nichtdurchführung'):
            confirm_import(self.db,second,reviewed=self.reviewed(second),assignment='1',case_id=self.case,historical=False,reason='Korrektur')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],1)

    def test_analytics_preserves_unknown_no_and_zero_without_exporting_text(self):
        from webapp.services.analytics import analytics_data, analytics_csv
        item=self.stage(); reviewed=self.reviewed(item)
        reviewed['data'].update(higher_manager_requested='',sap_current='nein')
        reviewed['narratives']={'general_comment':'  Sichtbarer Text\nZweite Zeile  ', 'manager_comment':''}
        reviewed['assessments']={'Selbstmanagement':'Eine aktuelle Einschätzung'}
        self.confirm(item,reviewed)
        report=analytics_data(self.db,cycle_id=self.cycle,minimum_group_size=1)
        row=report['form_fields'][0]
        self.assertEqual(row['higher_manager_requested'],'Offen'); self.assertEqual(row['sap_current'],'Nein')
        self.assertEqual(row['sap_clarification'],'Klärung erforderlich')
        self.assertEqual(row['character_counts']['general_comment'],len('Sichtbarer Text\nZweite Zeile'))
        self.assertEqual(row['character_counts']['manager_comment'],0)
        self.assertNotIn('employee_comment',row['character_counts'])
        name,content=analytics_csv('form_fields',report)
        self.assertNotIn(b'Sichtbarer Text',content); self.assertNotIn('Eine aktuelle Einschätzung'.encode(),content)
        self.assertEqual(name,'MD_Formularangaben.csv')
        client=self.app.test_client()
        self.assertEqual(client.get('/auswertungen').status_code,200)
        self.assertEqual(client.post('/auswertungen/export',data={'report':'form_fields','cycle_id':self.cycle}).status_code,200)

    def test_career_requests_include_only_confirmed_yes_and_export_names(self):
        from webapp.services.analytics import analytics_data, analytics_csv
        item=self.stage(kind='outlook',year=2026)
        reviewed=self.reviewed(item)
        reviewed['data']['career_requested']='ja'
        self.confirm(item,reviewed)
        report=analytics_data(self.db,cycle_id=self.cycle,minimum_group_size=1)
        self.assertEqual(len(report['career_requests']),1)
        row=report['career_requests'][0]
        self.assertEqual(row['case_id'],self.case)
        self.assertTrue(row['employee_name'])
        name,content=analytics_csv('career_requests',report)
        self.assertEqual(name,'MD_Laufbahnwuensche.csv')
        self.assertIn(row['employee_name'],content.decode('utf-8-sig'))
        self.assertEqual(self.app.test_client().get('/auswertungen').status_code,200)
        self.assertEqual(self.app.test_client().post('/auswertungen/export',data={'report':'career_requests','cycle_id':self.cycle}).status_code,200)
        for answer in ('nein',''):
            document=self.db.execute("SELECT id,data_block_json FROM official_documents WHERE document_kind='outlook'").fetchone()
            data=json.loads(document['data_block_json']);data['career_requested']=answer
            self.db.execute('UPDATE official_documents SET data_block_json=? WHERE id=?',(json.dumps(data),document['id']))
            self.db.commit()
            self.assertEqual(analytics_data(self.db,cycle_id=self.cycle)['career_requests'],[])

    def test_nonconducted_post_and_old_missing_outlook_selection(self):
        item=self.stage(kind='outlook',year=2026)
        reviewed=self.nonconducted(item)
        form={**reviewed['data'],'scope':'full','assignment':'1','case_id':self.case,'destination':'case','checked':'yes'}
        response=self.app.test_client().post(f'/word-pdf-imports/{item}',data=form)
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.db.execute('SELECT status FROM word_pdf_imports WHERE id=?',(item,)).fetchone()[0],'imported')

if __name__=='__main__':unittest.main()
