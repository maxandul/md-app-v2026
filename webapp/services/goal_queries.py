"""Server-side search/pagination over canonical sources, including old years."""
from . import goal_review as review
from . import goal_followups as followups

# A SQLite function derives status from the same domain objects as the detail
# page. No independently closable task record, and no complete result list in
# the browser. Register per request/connection; the synthetic volume test times it.
def source_progress(connection, source_id, template_paths=None):
    from . import goal_guidance
    from .goal_withdrawals import unresolved
    source = review.get(connection, source_id)
    if unresolved(connection, source_id):
        return dict(state='withdrawal', reason='Frühere Freigabe zurückgenommen: Auswirkungen klären.')
    if source['status'] == 'discarded':
        return dict(state='done', reason='Quelle verworfen.')
    if source['status'] in ('draft', 'waiting'):
        return dict(state='waiting' if source['status'] == 'waiting' else 'review',
                    reason=source['note'] if source['status'] == 'waiting' else ' · '.join(goal_guidance.review_tasks(source)))
    cases = followups.targets(connection, source['revision_id'])
    if not cases:
        decision = followups.latest_decision(connection, source['revision_id'], None)
        return dict(state='done' if decision and decision['outcome'] == 'no_output' else 'followup',
                    reason='Kein passender Rückblick vorhanden. Gesprächszuordnung prüfen oder Verzicht festhalten.')
    rows = [goal_guidance.target(connection, source['revision_id'], case, template_paths) for case in cases]
    # A ready part remains actionable even when another part needs clarification.
    state = next((state for state in ('blocked', 'ready', 'followup', 'approve', 'dispatch', 'waiting')
                  if any(row['state'] == state for row in rows)), 'done')
    reasons = list(dict.fromkeys(row['error'] for row in rows if row['error'] and row['state'] != 'done'))
    ready = sum(row['state'] == 'ready' for row in rows)
    reason = (f'{ready} Rückblick(e) zur Erstellung bereit. ' if ready else '') + ' · '.join(reasons)
    return dict(state=state, reason=reason, targets=rows)


def source_state(connection, source_id, template_paths=None):
    return source_progress(connection, source_id, template_paths)['state']


LABELS={'review':'Ziele prüfen','waiting':'Warten auf Rückmeldung','followup':'Rücklauf / Zuordnung klären', 'ready':'Rückblicke erstellen', 'approve':'Erzeugte Dateien prüfen',
        'dispatch':'Versand fortsetzen','blocked':'Outlook-Ausgang klären','done':'Abgeschlossen','withdrawal':'Folgen der Rücknahme klären'}


def listing(connection, *, q='',state='open',year=None,org_unit='',batch_id=None,page=1,page_size=25,template_paths=None):
    cache={}
    def status(source_id):
        if source_id not in cache:
            cache[source_id]=source_progress(connection,source_id,template_paths)
        return cache[source_id]['state']
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
    summary = {row['state']: row['n'] for row in connection.execute(candidates+
        'SELECT hr_goal_state(id) AS state,COUNT(*) AS n FROM candidates GROUP BY hr_goal_state(id)',params)}
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
    for row in rows:
        status(row['id'])
        row['next_reason'] = cache[row['id']]['reason']
    return {'summary':summary,'rows':rows,'total':total,'page':page,'pages':pages,'page_size':page_size,'labels':LABELS}
