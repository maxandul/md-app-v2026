"""Shared part responsibility for forms, deliveries, returns and reminders."""
from datetime import date, datetime, timezone
import json
from .packages import bounded_review_period
from webapp.migrations import available
from .outlook_lock import serialized_goal_delivery


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def resolve(connection, case_id, kind='review'):
    case = connection.execute('''SELECT dc.*, c.review_year,c.outlook_year,
        e.first_name,e.last_name,e.position,e.entry_date,e.exit_date,e.probation_end,e.secondary_employment,
        COALESCE(ea.org_unit,e.org_unit) AS employee_org_unit
        FROM dialog_cases dc JOIN cycles c ON c.id=dc.cycle_id
        JOIN employees e ON e.pn=dc.employee_pn LEFT JOIN employment_assignments ea
        ON ea.person_number=dc.employee_pn AND ea.assignment_number=dc.employment_assignment
        WHERE dc.case_id=?''', (case_id,)).fetchone()
    if not case or kind not in ('review','outlook'):
        raise ValueError('Gesprächsteil nicht gefunden.')
    case = dict(case)
    rows = connection.execute('''SELECT o.*,de.event_type,de.status AS event_status,
        fo.org_unit AS saved_org_unit,fo.source AS saved_org_source
        FROM document_obligations o JOIN dialog_events de ON de.id=o.dialog_event_id
        LEFT JOIN dialog_form_org_units fo ON fo.dialog_event_id=de.id
        WHERE de.legacy_case_id=? AND o.document_kind=?''', (case_id,kind)).fetchall()
    if len(rows) != 1:
        raise ValueError('Gesprächsteil ist nicht eindeutig verknüpft. Dialogzuordnung klären.')
    obligation = dict(rows[0])
    override = connection.execute('SELECT * FROM hr_part_responsibilities WHERE obligation_id=?', (obligation['id'],)).fetchone() if available(connection) else None
    year = case['review_year'] if kind=='review' else case['outlook_year']
    if override:
        start,end=override['period_start'],override['period_end']
    elif case['period_start'] and case['period_end'] and (kind=='review' or obligation['event_type']!='annual'):
        start,end=case['period_start'],case['period_end']
    elif kind=='review' and obligation['event_type']=='probation_review':
        start,end=case['entry_date'],case['probation_end']
    else:
        start,end=bounded_review_period(year,case['entry_date'],case['exit_date'])
    result = {**case, 'case_manager_pn':case['manager_pn'], 'kind':kind, 'obligation_id':obligation['id'], 'event_type':obligation['event_type'],
              'required':bool(obligation['required'] and obligation['status']!='waived'),
              'event_status':obligation['event_status'], 'due_date':obligation['due_date'], 'obligation_status':obligation['status'],
              'form_org_unit':obligation['saved_org_unit'] if obligation['saved_org_unit'] is not None else case['employee_org_unit'],
              'form_org_source':obligation['saved_org_source'] or 'employee',
              'period_start':start,'period_end':end,'responsibility_revision':0,'reason':'Bestehende Fallzuordnung'}
    if override:
        result.update({key:override[key] for key in ('manager_pn','form_org_unit','form_org_source','period_start','period_end','reason')})
        result['responsibility_revision']=override['revision']
    manager=connection.execute('SELECT * FROM employees WHERE pn=?',(result['manager_pn'],)).fetchone()
    if not manager:
        raise ValueError('Die verantwortliche Führungskraft fehlt in den Stammdaten.')
    result.update(recipient_email=manager['email'], manager_name=f"{manager['first_name']} {manager['last_name']}".strip(),
                  manager_first_name=manager['first_name'],manager_salutation=manager['salutation'])
    return result


@serialized_goal_delivery
def assign(connection, case_id, *, kind, manager_pn, form_org_source, period_start, period_end,
                  expected_revision, reason, user_id=None):
    if not reason.strip() or form_org_source not in ('employee','manager'):
        raise ValueError('Bitte OE-Quelle und Grund für die Zuordnung angeben.')
    try:
        if date.fromisoformat(period_start)>date.fromisoformat(period_end):
            raise ValueError()
    except (ValueError,TypeError):
        raise ValueError('Bitte einen gültigen Zeitraum angeben.') from None
    connection.execute('BEGIN IMMEDIATE')
    try:
        part=resolve(connection,case_id,kind)
        if part['responsibility_revision']!=expected_revision:
            raise ValueError('Die Zuständigkeit wurde inzwischen geändert. Bitte neu laden.')
        manager=connection.execute('SELECT org_unit FROM employees WHERE pn=?',(manager_pn,)).fetchone()
        if not manager:
            raise ValueError('Bitte eine Führungskraft aus der Liste wählen.')
        org=part['employee_org_unit'] if form_org_source=='employee' else manager['org_unit']
        connection.execute('''INSERT INTO hr_part_responsibilities
            (obligation_id,manager_pn,form_org_source,form_org_unit,period_start,period_end,revision,reason,user_id,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(obligation_id) DO UPDATE SET manager_pn=excluded.manager_pn,
            form_org_source=excluded.form_org_source,form_org_unit=excluded.form_org_unit,
            period_start=excluded.period_start,period_end=excluded.period_end,revision=excluded.revision,
            reason=excluded.reason,user_id=excluded.user_id,updated_at=excluded.updated_at''',
            (part['obligation_id'],manager_pn,form_org_source,org,period_start,period_end,expected_revision+1,reason.strip(),user_id,stamp()))
        from .sap_staging import available as staged
        if staged(connection):connection.execute("UPDATE hr_part_responsibilities SET origin='manual' WHERE obligation_id=?",(part['obligation_id'],))
        connection.execute('''INSERT INTO hr_goal_events(case_id,action,details_json,user_id,created_at)
            VALUES (?,'responsibility_changed',?,?,?)''',(case_id,json.dumps({'kind':kind,'before':part,'manager_pn':manager_pn,'org_unit':org,'period_start':period_start,'period_end':period_end,'reason':reason},ensure_ascii=False),user_id,stamp()))
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def assign_review(connection,case_id,**kwargs):
    return assign(connection,case_id,kind='review',**kwargs)


def case_parts(connection,case_id):
    return [resolve(connection,case_id,r['document_kind']) for r in connection.execute('''
        SELECT o.document_kind FROM document_obligations o JOIN dialog_events de ON de.id=o.dialog_event_id
        WHERE de.legacy_case_id=? AND o.document_kind IN ('review','outlook') ORDER BY o.id''',(case_id,))]


def assigned_kinds(connection,case_id,manager_pn,*,required_only=True):
    return [('probation' if p['event_type']=='probation_review' and p['kind']=='review' else p['kind'])
            for p in case_parts(connection,case_id) if p['manager_pn']==manager_pn
            and (not required_only or (p['required'] and p['active'] and p['event_status'] not in ('cancelled','no_md')))]


def case_rows(connection,cycle_id,manager_pn,*,case_id='',active_only=True):
    """Same case IDs, but only the parts assigned to this recipient are rendered."""
    return [dict(r) for r in connection.execute('''SELECT dc.*,e.first_name,e.last_name,e.position,
        e.entry_date,e.exit_date,e.probation_end,e.secondary_employment,e.employment_degree,
        COALESCE(fo.org_unit,ea.org_unit,e.org_unit) AS org_unit,COALESCE(de.event_type,'annual') AS event_type
        FROM dialog_cases dc JOIN employees e ON e.pn=dc.employee_pn
        LEFT JOIN employment_assignments ea ON ea.person_number=dc.employee_pn AND ea.assignment_number=dc.employment_assignment
        LEFT JOIN dialog_events de ON de.legacy_case_id=dc.case_id
        LEFT JOIN dialog_form_org_units fo ON fo.dialog_event_id=de.id
        WHERE dc.cycle_id=? AND (?=0 OR dc.active=1) AND (?='' OR dc.case_id=?)
        AND (EXISTS(SELECT 1 FROM hr_resolved_obligations o WHERE o.case_id=dc.case_id AND o.manager_pn=?
                    AND o.document_kind IN ('review','outlook') AND o.required=1)
             OR (dc.manager_pn=? AND COALESCE(NULLIF(dc.official_scope,''),dc.suggested_scope)='none'))
        ORDER BY e.last_name,e.first_name,dc.id''',(cycle_id,int(active_only),case_id,case_id,manager_pn,manager_pn))]


def has_assignments(connection,*,cycle_id=None,manager_pn=None,case_id=None):
    if not available(connection):return False
    where=[];params=[]
    if cycle_id is not None:where.append('de.cycle_id=?');params.append(cycle_id)
    if case_id:where.append('dc.case_id=?');params.append(case_id)
    if manager_pn:where.append('(dc.manager_pn=? OR r.manager_pn=?)');params.extend([manager_pn,manager_pn])
    return bool(connection.execute('''SELECT 1 FROM hr_part_responsibilities r
        JOIN document_obligations o ON o.id=r.obligation_id JOIN dialog_events de ON de.id=o.dialog_event_id
        JOIN dialog_cases dc ON dc.case_id=de.legacy_case_id WHERE '''+(' AND '.join(where) or '1')+' LIMIT 1',params).fetchone())


def require_legacy_compatible(connection,*,cycle_id=None,manager_pn=None,case_id=None):
    if has_assignments(connection,cycle_id=cycle_id,manager_pn=manager_pn,case_id=case_id):
        raise ValueError('Dieser Bestand hat Zuständigkeiten oder Zeiträume je Gesprächsteil. Bitte die Word-Ausgabe verwenden; die bisherige HTML-Arbeitsmappe bildet diese Trennung nicht ab.')
