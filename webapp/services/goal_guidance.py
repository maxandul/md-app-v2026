"""Read-only next actions, derived from the same checks used when generating."""
from . import goal_review as review, goal_followups as followups


def target(connection, revision_id, case, template_paths=None):
    row = {**case, 'revision_id': revision_id, 'part': None, 'evidence': [],
           'decision': None, 'error': '', 'token': '', 'task': 'case', 'state': 'followup'}
    try:
        row['part'] = followups.resolve(connection, case['case_id'])
        row['evidence'] = followups.return_evidence(connection, row['part'])
        row['decision'] = followups.latest_decision(connection, revision_id, case['case_id'])
        decision = row['decision']
        if followups.decision_effective(decision, row['evidence']):
            row.update(state='done' if decision['outcome'] in ('no_change', 'no_output', 'corrected') else 'waiting',
                       error=decision['reason'], task='clarify')
            return row
        output = connection.execute('''SELECT * FROM hr_goal_outputs WHERE revision_id=? AND case_id=?
            ORDER BY id DESC LIMIT 1''', (revision_id, case['case_id'])).fetchone()
        dispatch = followups.output_dispatch(connection, output['id']) if output else None
        if dispatch and dispatch['status'] == 'sent_confirmed':
            row.update(state='done', task='dispatch', dispatch=dispatch)
            return row
        if dispatch and dispatch['status'] in ('processing', 'failed'):
            row.update(state='blocked', task='dispatch', dispatch=dispatch,
                       error='Den tatsächlichen Stand des offenen Outlook-Vorgangs klären.')
            return row
        if row['evidence']:
            raise followups.PreparationError('Rückblick eingegangen oder Eingang noch unklar: Korrekturbedarf klären.', 'clarify')
        fingerprint = None
        if template_paths is not None:
            _, fingerprint, _ = followups.inputs(connection, revision_id, case['case_id'], template_paths)
        # Only an output for the current inputs is usable. Generation itself still
        # rechecks all inputs inside its transaction.
        if output and (fingerprint is None or output['input_fingerprint'] == fingerprint):
            if template_paths is not None:
                try:
                    followups.validate_output(connection, output['id'], template_paths)
                except (ValueError, OSError) as exc:
                    row.update(error=str(exc), task='outputs')
                    return row
            if output:
                row.update(state='dispatch' if dispatch or output['approved_at'] else 'approve',
                           task='dispatch' if dispatch else 'outputs', dispatch=dispatch)
                return row
        row.update(state='ready', task='generate')
        if fingerprint is not None:
            row['token'] = review.dump([revision_id, case['case_id'], fingerprint])
    except (ValueError, OSError) as exc:
        row.update(error=str(exc), task=getattr(exc, 'task', 'case'))
    finally:
        row['evidence_token'] = review.digest(row['evidence'])
    return row


def review_tasks(item):
    tasks = []
    if not item['employment_id']:
        tasks.append('Person und Anstellung zuordnen')
    if not item['goal_year']:
        tasks.append('Zieljahr festlegen')
    if item['extraction'].get('issues'):
        tasks.append('Auslesehinweise am Original klären')
    tasks.append('Ziele am Original prüfen und bestätigen')
    return tasks
