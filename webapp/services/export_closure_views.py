"""Read-only task guidance; export decisions continue to use the canonical collector."""
import json
from dataclasses import asdict
from . import sap_export,part_changes,part_responsibilities as parts,person_display,hr_workflow

LABELS={'ready':'Im neuen Batch','attention':'Zuerst klären','waiting':'Rückblick noch offen','exported':'Bereits bereitgestellt','excluded':'Nicht im neuen Batch'}


def packed(value):
    return json.loads(json.dumps(value,default=str,sort_keys=True,ensure_ascii=False))


def export_plan(db,cycle_id):
    cycle=db.execute('SELECT * FROM cycles WHERE id=?',(cycle_id,)).fetchone()
    if not cycle:raise LookupError('Durchlauf nicht gefunden.')
    rows=[dict(r) for r in db.execute('''SELECT c.*,e.first_name,e.last_name,e.entry_date,e.exit_date,e.position,
        d.id AS event_db_id,d.status AS event_status,d.sap_leading,d.event_type,
        s.batch_id,s.source_version AS exported_version,s.overall_rating AS exported_rating,
        (SELECT sha256 FROM official_documents od WHERE od.case_id=c.case_id AND od.document_kind='review' AND od.is_current=1
         ORDER BY CASE od.variant WHEN 'digital' THEN 0 ELSE 1 END,od.id DESC LIMIT 1) AS document_sha
        FROM dialog_cases c JOIN employees e ON e.pn=c.employee_pn LEFT JOIN dialog_events d ON d.legacy_case_id=c.case_id
        LEFT JOIN sap_export_rows s ON s.dialog_event_id=d.id WHERE c.cycle_id=? ORDER BY e.last_name,e.first_name,c.case_id''',(cycle_id,))]
    error='';ready=[]
    try:ready=sap_export.collect_sap_upload_rows(db,cycle_id)
    except ValueError as exc:
        if str(exc)!='Es gibt keine neuen, noch nicht exportierten SAP-relevanten Rückblicke.':error=str(exc)
    by_case={r.case_id:packed(asdict(r)) for r in ready}
    for row in rows:
        row.update(state='excluded',reason='',export_row=None,part=None)
        try:
            row['part']=parts.resolve(db,row['case_id'],'review')
            row['manager_pn']=row['part']['manager_pn'];row['manager_name']=row['part']['manager_name']
        except ValueError:row['manager_name']='Keine Rückblickzuständigkeit'
        try:payload=json.loads(row['data_json'] or '{}')
        except (ValueError,TypeError):payload={};row['reason']='Gespeicherter MD-Datensatz ist ungültig.'
        scope=row['official_scope'] or payload.get('scope','')
        if not row['active'] or row['event_status']=='cancelled':row['reason']='Auftrag nicht mehr vorgesehen; Nachweise bleiben erhalten.'
        elif row['batch_id']:
            row.update(state='exported',reason='Im gespeicherten Batch erfasst. Das ist kein Nachweis einer Verarbeitung in SAP.')
            if row['document_sha'] and row['document_sha']!=row['exported_version']:row['reason']+=' Die heutige Dokumentfassung weicht ab; Korrektur im SAP-Zielprozess separat klären.'
        elif row['status']=='vollstaendig' and row['reason']:
            row['state']='attention'
        elif row['status']!='vollstaendig':row.update(state='waiting',reason='Der Gesprächsfall ist noch nicht vollständig abgeschlossen. Rücklauf und Dossierübergabe prüfen.')
        elif scope not in ('full','review_only') or (payload.get('review') or {}).get('conducted')=='nein':row['reason']='Kein durchgeführter SAP-relevanter Rückblick.'
        elif row['case_id'] in by_case:row.update(state='ready',reason='Wird in den neuen Batch aufgenommen.',export_row=by_case[row['case_id']])
        else:
            try:
                candidate=sap_export.collect_sap_upload_rows(db,cycle_id,_case_id=row['case_id'])
                row.update(state='ready',reason='Daten dieses Rückblicks sind bereit; vor der Batch-Erstellung die übrigen Klärungen erledigen.',export_row=packed(asdict(candidate[0])))
            except ValueError as exc:
                message=str(exc).replace('PN '+row['employee_pn']+': ','')
                if not row['sap_leading'] and not error:row['reason']='Ein anderer Rückblick dieser Anstellung ist für diesen Batch massgebend.'
                else:row.update(state='attention',reason=message)
    person_display.enrich(db,rows)
    for row in rows:
        if error.startswith('PN '+row['employee_pn']):error=error.replace('PN '+row['employee_pn'],row['first_name']+' '+row['last_name'],1);break
    value={'cycle':dict(cycle),'rows':rows,'ready':packed([asdict(r) for r in ready]),'error':error,
        'counts':{k:sum(r['state']==k for r in rows) for k in LABELS}}
    value['fingerprint']=part_changes.digest(value)
    return value


def closure_plan(db,cycle_id):
    export=export_plan(db,cycle_id);summary=hr_workflow.closure_summary(db,cycle_id)
    def records(sql,args=(cycle_id,)):return [dict(r) for r in db.execute(sql,args)]
    value={'cycle':export['cycle'],'summary':summary,'export':export,
        'obligations':records('SELECT o.* FROM document_obligations o JOIN dialog_events e ON e.id=o.dialog_event_id WHERE e.cycle_id=? ORDER BY o.id'),
        'documents':records('SELECT id,sha256,is_current,handoff_status,signature_checked FROM official_documents WHERE cycle_id=? ORDER BY id'),
        'pdfs':[dict(r) for r in hr_workflow.pending_pdfs(db)],
        'mail':records('SELECT id,status,review_completed_at,updated_at FROM inbound_mail_messages ORDER BY id',()),
        'events':records('SELECT id,updated_at,status,sap_leading FROM dialog_events WHERE cycle_id=? OR cycle_id IS NULL ORDER BY id'),
        'packages':records('SELECT p.id,p.discarded_at,d.status,d.updated_at FROM word_dispatch_packages p LEFT JOIN word_mail_deliveries d ON d.package_id=p.id WHERE p.cycle_id=? ORDER BY p.id'),
        'people_outputs':records('SELECT id,status,updated_at FROM word_person_corrections WHERE case_id IN (SELECT case_id FROM dialog_cases WHERE cycle_id=?) ORDER BY id'),
        'feedback':records('SELECT import_id,bundle_id FROM word_feedback_submissions WHERE cycle_id=? ORDER BY import_id')}
    from webapp.migrations import available
    if available(db):
        value['goals']=records('SELECT DISTINCT d.id,d.status,d.updated_at FROM hr_goal_dispatches d JOIN hr_goal_dispatch_outputs m ON m.dispatch_id=d.id JOIN hr_goal_outputs o ON o.id=m.output_id JOIN dialog_cases c ON c.case_id=o.case_id WHERE c.cycle_id=? ORDER BY d.id')
        value['reminders']=records('SELECT r.id,r.status,r.created_at,rr.outcome FROM reminders r LEFT JOIN hr_reminder_resolutions rr ON rr.reminder_id=r.id WHERE r.cycle_id=? ORDER BY r.id')
    from .return_review import available as return_available
    if return_available(db):value['return_status']=records('SELECT * FROM hr_return_status WHERE cycle_id=? ORDER BY document_id')
    value['fingerprint']=part_changes.digest(packed(value))
    return value
