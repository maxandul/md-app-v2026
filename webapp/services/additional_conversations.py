"""Explicit additions and whole-order replacement over the existing event model."""
import json
from datetime import date
from . import part_changes,part_responsibilities as parts,dialog_events
from .outlook_lock import serialized_goal_delivery
from .sap_staging import available

TYPES={k:dialog_events.EVENT_TYPE_LABELS[k] for k in ('interim','transfer_review','departure_review')}
SCOPES={k:dialog_events.SCOPE_LABELS[k] for k in ('full','review_only','outlook_only')}
KINDS={'full':{'review','outlook'},'review_only':{'review'},'outlook_only':{'outlook'}}


def context(db,case_id):
    source=parts.case_parts(db,case_id)
    if not source:raise ValueError('Ausgangsauftrag nicht gefunden.')
    first=source[0]
    employment=db.execute('SELECT * FROM employment_assignments WHERE person_number=? AND assignment_number=?',(first['employee_pn'],first['employment_assignment'])).fetchone()
    if not employment or not employment['active']:raise ValueError('Die gewählte Anstellung ist nicht mehr aktiv. Zuerst die Stammdaten klären.')
    existing=[dict(r) for r in db.execute('''SELECT e.*,m.manager_person_number AS manager_pn FROM dialog_events e
        JOIN manager_assignments m ON m.id=e.manager_assignment_id WHERE e.employment_id=? ORDER BY e.id''',(employment['id'],))]
    return {'parts':[part_changes.context(db,case_id,p['kind']) for p in source], 'employment':dict(employment),'events':existing}


def plan(db,case_id,proposal):
    if not available(db):raise ValueError('Für diesen Ablauf zuerst das aktuelle Datenmodell übernehmen.')
    value=context(db,case_id);first=value['parts'][0]['part'];p=dict(proposal)
    if p['event_type'] not in TYPES or p['required_scope'] not in SCOPES:raise ValueError('Bitte Gesprächsart und Umfang wählen.')
    if p['disposition'] not in ('keep','replace'):raise ValueError('Bitte ausdrücklich entscheiden, was mit dem bisherigen Auftrag geschieht.')
    if p['form_org_source'] not in ('employee','manager'):raise ValueError('Bitte die Formular-OE wählen.')
    if not p['reason'].strip():raise ValueError('Bitte den Anlass und die Entscheidung zum bisherigen Auftrag begründen.')
    manager=db.execute('SELECT * FROM employees WHERE pn=? AND active=1',(p['manager_pn'],)).fetchone()
    if not manager:raise ValueError('Bitte eine aktive Führungskraft aus der Namensauswahl wählen.')
    try:
        start,end=date.fromisoformat(p['period_start']),date.fromisoformat(p['period_end'])
        if start>end:raise ValueError()
        for k in ('review_due_date','outlook_due_date'):
            if p[k]:date.fromisoformat(p[k])
    except (ValueError,TypeError):raise ValueError('Bitte einen gültigen Zeitraum und gültige Fristen angeben.') from None
    employment=value['employment']
    if (employment['entry_date'] and p['period_start']<employment['entry_date']) or (employment['exit_date'] and p['period_end']>employment['exit_date']):
        raise ValueError('Der Zeitraum muss innerhalb der gewählten Anstellung liegen.')
    if 'review' in KINDS[p['required_scope']]:
        from .form_data import validate_review_period
        validate_review_period(p['period_start'],p['period_end'],first['review_year'],employment['entry_date'],employment['exit_date'])
    defaults=dialog_events.default_due_dates(first['review_year'])
    value['new']={'manager_name':manager['first_name']+' '+manager['last_name'],'recipient_email':manager['email'],
        'form_org_unit':employment['org_unit'] if p['form_org_source']=='employee' else manager['org_unit'],
        'period_start':p['period_start'],'period_end':p['period_end'],'review_due_date':p['review_due_date'] or defaults[0],
        'outlook_due_date':p['outlook_due_date'] or defaults[1]}
    blockers=[]
    if not first['active'] or any(c['part']['event_status']=='cancelled' for c in value['parts']):blockers.append('Der Ausgangsauftrag ist nicht mehr aktiv. Bitte von einem aktiven Auftrag starten.')
    duplicate=next((e for e in value['events'] if e['status']!='cancelled' and e['manager_pn']==p['manager_pn'] and e['event_type']==p['event_type'] and e['required_scope']==p['required_scope'] and e['period_start']==p['period_start'] and e['period_end']==p['period_end'] and e['review_year']==first['review_year']),None)
    if duplicate:blockers.append('Ein entsprechendes Gespräch besteht bereits. Bestehenden Auftrag öffnen statt nochmals anlegen.')
    if p['disposition']=='replace':
        required={c['part']['kind'] for c in value['parts'] if c['part']['required']}
        if not required or not required<=KINDS[p['required_scope']]:blockers.append('Der neue Umfang ersetzt nicht alle vorgesehenen Teile des bisherigen Auftrags. Bisherigen Auftrag beibehalten oder einzelne Zuständigkeit ändern.')
        for c in value['parts']:
            part,impact=c['part'],c['effects']
            if part['obligation_status'] in ('complete','received','review','scan_pending') or impact['evidence']:
                blockers.append('Zum bisherigen Auftrag liegt ein Rücklauf vor oder ein Eingang ist ungeklärt. Zuerst den konkreten Eingang bzw. Korrekturbedarf prüfen.')
            if any(f['status'] in part_changes.OPEN for f in impact['files']):blockers.append('Zum bisherigen Auftrag ist ein Outlook-Vorgang offen. Tatsächlichen Versandstand zuerst klären.')
            if any(r['status'] in ('prepared','draft_created','failed') and not r['resolution'] for r in impact['reminders']):blockers.append('Zum bisherigen Auftrag ist eine Erinnerung offen. Tatsächlichen Versandstand zuerst klären.')
    value.update(proposal=p,blockers=list(dict.fromkeys(blockers)),duplicate=duplicate)
    value['fingerprint']=part_changes.digest(value)
    return value


@serialized_goal_delivery
def apply(db,case_id,proposal,*,expected,request_key,user_id=None):
    db.execute('BEGIN IMMEDIATE')
    try:
        previous=db.execute("SELECT details_json FROM hr_goal_events WHERE case_id=? AND action='additional_conversation_created' AND json_extract(details_json,'$.request_key')=?",(case_id,request_key)).fetchone()
        if previous:
            db.rollback();return json.loads(previous[0])['new_case_id']
        current=plan(db,case_id,proposal)
        if current['fingerprint']!=expected:raise ValueError('Die Grundlage hat sich inzwischen geändert. Bitte die Vorschau neu prüfen.')
        if current['blockers']:raise ValueError(' '.join(current['blockers']))
        first=current['parts'][0]['part'];p=current['proposal']
        values={k:p[k] for k in ('manager_pn','event_type','required_scope','period_start','period_end','reason','form_org_source','review_due_date','outlook_due_date')}
        new_id=dialog_events._create_manual_event(db,employee_pn=first['employee_pn'],assignment_number=first['employment_assignment'],
            review_year=first['review_year'],cycle_id=first['cycle_id'],commit=False,**values)
        # This assignment belongs to the conversation, not to the current reporting line.
        db.execute('UPDATE manager_assignments SET active=0 WHERE id=(SELECT manager_assignment_id FROM dialog_events WHERE event_id=?)',(new_id,))
        if p['disposition']=='replace':
            now=parts.stamp()
            db.execute("UPDATE dialog_events SET status='cancelled',sap_leading=0,source_reason=source_reason || ?,updated_at=? WHERE legacy_case_id=?",('\nErübrigt durch '+new_id+': '+p['reason'],now,case_id))
            db.execute("UPDATE document_obligations SET status='waived',updated_at=? WHERE dialog_event_id IN (SELECT id FROM dialog_events WHERE legacy_case_id=?)",(now,case_id))
            db.execute('UPDATE dialog_cases SET active=0,updated_at=? WHERE case_id=?',(now,case_id))
        details={'request_key':request_key,'new_case_id':new_id,'proposal':p,'new':current['new'],'before':[c['part'] for c in current['parts']]}
        db.execute("INSERT INTO hr_goal_events(case_id,action,details_json,user_id,created_at) VALUES (?,'additional_conversation_created',?,?,?)",(case_id,json.dumps(details,ensure_ascii=False),user_id,parts.stamp()))
        db.commit();return new_id
    except Exception:
        db.rollback();raise
