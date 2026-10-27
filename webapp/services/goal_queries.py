"""Server-side search/pagination over canonical sources, including old years."""
from . import goal_review as review
from . import goal_followups as followups

# A SQLite function derives status from the same domain objects as the detail
# page. No independently closable task record, and no complete result list in
# the browser. Register per request/connection; the synthetic volume test times it.
def source_state(connection, source_id):
    source=review.get(connection,source_id)
    from .goal_withdrawals import unresolved
    if unresolved(connection,source_id):
        return 'withdrawal'
    if source['status']=='discarded':
        return 'done'
    if source['status'] in ('draft','waiting'):
        return 'waiting' if source['status']=='waiting' else 'review'
    cases=followups.targets(connection,source['revision_id'])
    if not cases:
        decision=followups.latest_decision(connection,source['revision_id'],None)
        return 'done' if decision and decision['outcome']=='no_output' else 'followup'
    states=[]
    for case in cases:
        try:
            part=followups.resolve(connection,case['case_id'])
            evidence=followups.return_evidence(connection,part)
        except ValueError:
            states.append('followup')
            continue
        decision=followups.latest_decision(connection,source['revision_id'],case['case_id'])
        if followups.decision_effective(decision,evidence):
            if decision['outcome'] in ('no_change','no_output','corrected'):
                states.append('done')
                continue
            if decision['outcome'] in ('waiting','request_correction'):
                states.append('waiting')
                continue
        dispatched=connection.execute('''SELECT d.status FROM hr_goal_outputs o
            JOIN hr_goal_dispatch_outputs m ON m.output_id=o.id JOIN hr_goal_dispatches d ON d.id=m.dispatch_id
            WHERE o.revision_id=? AND o.case_id=? AND d.status<>'cancelled' ORDER BY d.id DESC LIMIT 1''',
            (source['revision_id'],case['case_id'])).fetchone()
        if dispatched and dispatched['status']=='sent_confirmed':
            states.append('done')
        elif evidence:
            states.append('followup')
        elif dispatched:
            states.append('blocked' if dispatched['status'] in ('processing','failed') else 'dispatch')
        else:
            states.append('followup')
    for state in ('blocked','followup','dispatch','waiting'):
        if state in states:
            return state
    return 'done'


LABELS={'review':'Ziele prüfen','waiting':'Warten auf Rückmeldung','followup':'Folgeaktion prüfen',
        'dispatch':'Versand fortsetzen','blocked':'Outlook-Ausgang klären','done':'Abgeschlossen','withdrawal':'Folgen der Rücknahme klären'}


def listing(connection, *, q='',state='open',year=None,org_unit='',batch_id=None,page=1,page_size=25):
    cache={}
    def status(source_id):
        if source_id not in cache:
            cache[source_id]=source_state(connection,source_id)
        return cache[source_id]
    connection.create_function('hr_goal_state',1,status)
    conditions=[];params=[]
    if q:
        conditions.append("""(COALESCE(p.first_name,'')||' '||COALESCE(p.last_name,'')||' '||COALESCE(ea.person_number,'')||' '||s.original_filename LIKE ?
            OR EXISTS(SELECT 1 FROM hr_goal_withdrawals w JOIN hr_goal_revisions old ON old.id=w.confirmed_revision_id
                JOIN employment_assignments oe ON oe.id=old.employment_id JOIN persons op ON op.person_number=oe.person_number
                WHERE w.source_id=s.id AND op.first_name||' '||op.last_name||' '||oe.person_number LIKE ?))""")
        params.extend(['%'+q+'%']*2)
    if year:
        conditions.append('''(r.goal_year=? OR EXISTS(SELECT 1 FROM hr_goal_withdrawals w
            JOIN hr_goal_revisions old ON old.id=w.confirmed_revision_id WHERE w.source_id=s.id AND old.goal_year=?))''');params.extend([year,year])
    if org_unit:
        conditions.append('''(ea.org_unit=? OR EXISTS(SELECT 1 FROM hr_goal_withdrawals w
            JOIN hr_goal_revisions old ON old.id=w.confirmed_revision_id JOIN employment_assignments oe ON oe.id=old.employment_id
            WHERE w.source_id=s.id AND oe.org_unit=?))''');params.extend([org_unit,org_unit])
    if batch_id:
        conditions.append('EXISTS(SELECT 1 FROM hr_goal_batch_sources b WHERE b.source_id=s.id AND b.batch_id=?)');params.append(batch_id)
    base='''FROM hr_goal_sources s JOIN hr_goal_revisions r ON r.source_id=s.id AND r.revision=s.revision
        LEFT JOIN employment_assignments ea ON ea.id=r.employment_id LEFT JOIN persons p ON p.person_number=ea.person_number'''
    where=' WHERE '+' AND '.join(conditions) if conditions else ''
    # Apply indexed/text filters before deriving workflow state. MATERIALIZED
    # prevents SQLite from evaluating the domain function for unrelated sources.
    candidates='''WITH candidates AS MATERIALIZED (SELECT s.id,s.original_filename,s.created_at,r.id AS revision_id,
        r.goal_year,r.status,p.first_name,p.last_name,ea.person_number,ea.assignment_number,ea.org_unit '''+base+where+') '
    state_where=''
    if state=='open':
        state_where=" WHERE hr_goal_state(id)<>'done'"
    elif state in LABELS:
        state_where=' WHERE hr_goal_state(id)=?';params.append(state)
    total=connection.execute(candidates+'SELECT COUNT(*) FROM candidates'+state_where,params).fetchone()[0]
    page_size=page_size if page_size in (25,50,100) else 25
    pages=max(1,(total+page_size-1)//page_size);page=max(1,min(page,pages))
    rows=[dict(row) for row in connection.execute(candidates+'''SELECT *,hr_goal_state(id) AS task_state FROM candidates'''
        +state_where+' ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?',
        (*params,page_size,(page-1)*page_size))]
    return {'rows':rows,'total':total,'page':page,'pages':pages,'page_size':page_size,'labels':LABELS}
