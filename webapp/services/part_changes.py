"""Read-only change plans over the existing per-part responsibility model."""
import hashlib
import json
from datetime import date
from . import part_responsibilities as parts
from .goal_followups import return_evidence
from .form_data import validate_review_period
from .person_display import enrich

OPEN=('processing','draft_created','failed')


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def effects(db,part):
    documents=[]
    for kind,sql in (
        ('regular', '''SELECT p.*,d.status AS delivery_status,d.recipient_email,d.updated_at AS delivery_updated_at
            FROM word_dispatch_packages p LEFT JOIN word_mail_deliveries d ON d.package_id=p.id
            WHERE EXISTS(SELECT 1 FROM json_each(p.manifest_json,'$.documents') j
                WHERE json_extract(j.value,'$.case_id')=? AND json_extract(j.value,'$.kind') IN (?,?)) ORDER BY p.id DESC'''),
        ('person', '''SELECT p.*,p.status AS delivery_status FROM word_person_corrections p
            WHERE EXISTS(SELECT 1 FROM json_each(p.manifest_json,'$.documents') j
                WHERE json_extract(j.value,'$.case_id')=? AND json_extract(j.value,'$.kind') IN (?,?)) ORDER BY p.id DESC''')):
        for row in db.execute(sql,(part['case_id'],part['kind'],'probation' if part['kind']=='review' else part['kind'])):
            value=dict(row);manifest=json.loads(value.pop('manifest_json'))
            documents.append({'kind':kind,'id':row['id'],'status':row['delivery_status'] or ('cancelled' if value.get('discarded_at') else 'prepared'),
                'recipient_email':value.get('recipient_email') or '', 'created_at':row['created_at'],
                'manager_pn':manifest['manager_pn'],'redelivery':bool(manifest.get('redelivery'))})
    if part['kind']=='review':
        for row in db.execute('''SELECT DISTINCT d.* FROM hr_goal_dispatches d JOIN hr_goal_dispatch_outputs m ON m.dispatch_id=d.id
            JOIN hr_goal_outputs o ON o.id=m.output_id WHERE o.case_id=? ORDER BY d.id DESC''',(part['case_id'],)):
            documents.append({'kind':'goals','id':row['id'],'status':row['status'],'recipient_email':row['recipient_email'],
                'created_at':row['created_at'],'manager_pn':row['manager_pn'],'redelivery':False})
        # Generated but not grouped goal outputs are also part of the source context.
        outputs=[dict(r) for r in db.execute('SELECT id,input_fingerprint,approved_at FROM hr_goal_outputs WHERE case_id=? ORDER BY id',(part['case_id'],))]
    else:outputs=[]
    reminders=[dict(r) for r in db.execute('''SELECT r.id,r.status,r.recipient_email,r.created_at,r.subject,rr.outcome AS resolution
        FROM reminders r JOIN reminder_obligations ro ON ro.reminder_id=r.id
        LEFT JOIN hr_reminder_resolutions rr ON rr.reminder_id=r.id
        WHERE ro.obligation_id=? ORDER BY r.id DESC''',(part['obligation_id'],))]
    names={r['pn']:(r['first_name']+' '+r['last_name']).strip() for r in db.execute('SELECT pn,first_name,last_name FROM employees')}
    for row in documents:row['manager_name']=names.get(row['manager_pn']) or 'Name nicht hinterlegt'
    documents.sort(key=lambda r:r['created_at'],reverse=True)
    documents.sort(key=lambda r:r['status'] not in OPEN)
    return {'files':documents,'goal_outputs':outputs,'reminders':reminders,'evidence':return_evidence(db,part)}


def context(db,case_id,kind):
    part=parts.resolve(db,case_id,kind)
    enrich(db,[part])
    return {'part':part,'other_parts':[p for p in parts.case_parts(db,case_id) if p['kind']!=kind], 'effects':effects(db,part)}


def plan(db,case_id,*,kind,manager_pn,form_org_source,period_start,period_end,expected_revision,reason):
    value=context(db,case_id,kind);part=value['part']
    if expected_revision!=part['responsibility_revision']:raise ValueError('Die Zuständigkeit wurde inzwischen geändert. Bitte die aktuelle Grundlage neu prüfen.')
    manager=db.execute('SELECT pn,first_name,last_name,org_unit,email FROM employees WHERE pn=? AND active=1',(manager_pn,)).fetchone()
    if not manager:raise ValueError('Bitte eine aktive Führungskraft aus der Namensauswahl wählen.')
    if form_org_source not in ('employee','manager'):raise ValueError('Bitte die Herkunft der Formular-OE wählen.')
    if not reason.strip():raise ValueError('Bitte den Grund der Änderung festhalten.')
    try:
        start,end=date.fromisoformat(period_start),date.fromisoformat(period_end)
        if start>end:raise ValueError()
    except (ValueError,TypeError):raise ValueError('Bitte einen gültigen Zeitraum von/bis angeben.') from None
    if (part['entry_date'] and period_start<part['entry_date']) or (part['exit_date'] and period_end>part['exit_date']):
        raise ValueError('Der Zeitraum muss innerhalb der Anstellung liegen.')
    if kind=='review' and part['event_type']!='probation_review':
        validate_review_period(period_start,period_end,part['review_year'],part['entry_date'],part['exit_date'])
    if kind=='outlook' and part['event_type']=='annual' and (start.year!=part['outlook_year'] or end.year!=part['outlook_year']):
        raise ValueError('Der reguläre Ausblick muss innerhalb des Ausblickjahres liegen.')
    proposed={'manager_pn':manager_pn,'manager_name':manager['first_name']+' '+manager['last_name'],'recipient_email':manager['email'],
        'form_org_source':form_org_source,'form_org_unit':part['employee_org_unit'] if form_org_source=='employee' else manager['org_unit'],
        'period_start':period_start,'period_end':period_end,'reason':reason.strip()}
    changed=[k for k in ('manager_pn','form_org_source','form_org_unit','period_start','period_end') if proposed[k]!=part[k]]
    if not changed:raise ValueError('Die Auswahl entspricht bereits der bestehenden Zuordnung. Es wird keine Änderung gespeichert.')
    blockers=[];impact=value['effects']
    if not part['active'] or not part['required'] or part['event_status'] in ('cancelled','no_md'):
        blockers.append('Dieser Gesprächsteil ist nicht mehr als aktiver Auftrag vorgesehen.')
    if part['obligation_status'] in ('complete','received','review','scan_pending') or impact['evidence']:
        blockers.append('Ein Rücklauf liegt vor oder ein Eingang ist noch ungeklärt. Zuerst den konkreten Eingang bzw. Korrekturbedarf prüfen.')
    if any(r['status'] in OPEN for r in impact['files']):
        blockers.append('Für diesen Teil ist ein Outlook-Vorgang offen. Tatsächlichen Versand zuerst bestätigen oder einen nicht versandten Entwurf in Outlook löschen und hier klären.')
    if any(r['status'] in ('prepared','draft_created','failed') and not r['resolution'] for r in impact['reminders']):
        blockers.append('Ein Erinnerungsvorgang für diesen Teil ist noch offen. Zuerst dessen tatsächlichen Outlook-Stand klären.')
    value.update(proposal=proposed,changed_fields=changed,blockers=blockers)
    value['fingerprint']=digest(value)
    return value


def history(db,case_id,kind):
    names={r['pn']:(r['first_name']+' '+r['last_name']).strip() for r in db.execute('SELECT pn,first_name,last_name FROM employees')}
    result=[]
    for row in db.execute("SELECT * FROM hr_goal_events WHERE case_id=? AND action='responsibility_changed' ORDER BY id DESC",(case_id,)):
        value=dict(row);details=json.loads(value['details_json'])
        if details.get('kind','review')!=kind:continue
        details['new_label']=details.get('manager_name') or ((names.get(details['manager_pn']) or 'Name nicht hinterlegt')+' (heutige Stammdaten)')
        details['old_label']=details['before'].get('manager_name') or 'Name damals nicht festgehalten'
        value['details']=details;result.append(value)
    return result
