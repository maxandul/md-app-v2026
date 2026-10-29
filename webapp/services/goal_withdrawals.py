"""Withdraw an approval without rewriting its assignment, files or external history."""
import json
from . import goal_review as review,goal_followups as followups
from .part_responsibilities import stamp
from .outlook_lock import serialized_goal_delivery


def impact(connection,source_id):
    source=review.get(connection,source_id)
    revisions=connection.execute('''SELECT r.* FROM hr_goal_revisions r WHERE r.source_id=? AND r.status='confirmed'
        AND NOT EXISTS(SELECT 1 FROM hr_goal_withdrawals w WHERE w.source_id=r.source_id AND w.through_revision>=r.revision)
        ORDER BY r.revision''',(source_id,)).fetchall()
    if not revisions:
        raise ValueError('Für diese Quelle gibt es keine aktive Freigabe zurückzunehmen.')
    ids=[r['id'] for r in revisions];marks=','.join('?' for _ in ids)
    cases={r['case_id']:r for r in followups.targets(connection,ids[-1])}
    outputs=[];deliveries={}
    for row in connection.execute(f'SELECT * FROM hr_goal_outputs WHERE revision_id IN ({marks}) ORDER BY id',ids):
        outputs.append({'kind':'goal','id':row['id'],'case_id':row['case_id'],'path':row['stored_path']})
        case=connection.execute('SELECT case_id,cycle_id,employee_pn,employment_assignment FROM dialog_cases WHERE case_id=?',(row['case_id'],)).fetchone()
        if case:cases[case['case_id']]=dict(case)
        for group in connection.execute('''SELECT d.* FROM hr_goal_dispatches d JOIN hr_goal_dispatch_outputs m ON m.dispatch_id=d.id
            WHERE m.output_id=? ORDER BY d.id''',(row['id'],)):
            deliveries[('goal',group['id'])]={'kind':'goal','id':group['id'],'status':group['status'],'recipient':group['recipient_email']}
    for kind,table in (('person','word_person_corrections'),('package','word_dispatch_packages')):
        rows=connection.execute(f'''SELECT p.* FROM {table} p WHERE EXISTS(SELECT 1 FROM json_each(p.manifest_json,'$.documents') d
            WHERE json_extract(d.value,'$.goal_source.hr_goal_revision_id') IN ({marks})) ORDER BY p.id''',ids)
        for row in rows:
            manifest=json.loads(row['manifest_json'])
            for document in manifest['documents']:
                if document.get('goal_source',{}).get('hr_goal_revision_id') in ids:
                    case_id=document['case_id']
                    case=connection.execute('SELECT case_id,cycle_id,employee_pn,employment_assignment FROM dialog_cases WHERE case_id=?',(case_id,)).fetchone()
                    if case:cases[case_id]=dict(case)
                    outputs.append({'kind':kind,'id':row['id'],'case_id':case_id,'path':row['stored_path']})
            delivery=row if kind=='person' else connection.execute('SELECT * FROM word_mail_deliveries WHERE package_id=?',(row['id'],)).fetchone()
            if delivery:
                deliveries[(kind,row['id'])]={'kind':kind,'id':row['id'],'status':delivery['status'],'recipient':delivery['recipient_email']}
    evidence={}
    for case in cases:
        evidence[case]=followups.return_evidence(connection,followups.resolve(connection,case))
    return {'source_id':source_id,'source_revision':source['revision'],'confirmed_revision_id':ids[-1],
            'revision_ids':ids,'employment_id':revisions[-1]['employment_id'],'goal_year':revisions[-1]['goal_year'],
            'cases':[cases[key] for key in sorted(cases)],'outputs':outputs,
            'deliveries':[deliveries[key] for key in sorted(deliveries)],'returns':evidence}


def get(connection,withdrawal_id):
    row=connection.execute('SELECT * FROM hr_goal_withdrawals WHERE id=?',(withdrawal_id,)).fetchone()
    if not row:raise ValueError('Rücknahme nicht gefunden.')
    result=dict(row);result['impact']=json.loads(result['impact_json'])
    return result


def deliveries(connection,withdrawal):
    result=[]
    for saved in withdrawal['impact']['deliveries']:
        if saved['kind']=='goal':
            row=connection.execute('SELECT status FROM hr_goal_dispatches WHERE id=?',(saved['id'],)).fetchone()
        elif saved['kind']=='person':
            row=connection.execute('''SELECT p.status,p.case_id,c.cycle_id FROM word_person_corrections p
                JOIN dialog_cases c ON c.case_id=p.case_id WHERE p.id=?''',(saved['id'],)).fetchone()
        else:
            row=connection.execute('''SELECT d.status,p.cycle_id FROM word_mail_deliveries d
                JOIN word_dispatch_packages p ON p.id=d.package_id WHERE d.package_id=?''',(saved['id'],)).fetchone()
        result.append({**saved,**(dict(row) if row else {'status':'unknown'})})
    return result


def open_outlook(connection,withdrawal_id):
    return [d for d in deliveries(connection,get(connection,withdrawal_id)) if d['status'] in ('processing','draft_created','failed','unknown')]


def checks(connection,withdrawal):
    cases=withdrawal['impact']['cases'] or [{'case_id':None}]
    result=[]
    for case in cases:
        case_id=case['case_id']
        part=followups.resolve(connection,case_id) if case_id else None
        evidence=followups.return_evidence(connection,part) if part else []
        decision=followups.latest_decision(connection,withdrawal['confirmed_revision_id'],case_id,withdrawal_id=withdrawal['id'])
        done=followups.decision_effective(decision,evidence) and decision['outcome'] in ('no_change','no_output','corrected')
        result.append({**case,'part':part,'evidence':evidence,'evidence_token':review.digest(evidence),'decision':decision,'done':bool(done)})
    return result


def unresolved(connection,source_id):
    for row in connection.execute('SELECT id FROM hr_goal_withdrawals WHERE source_id=? ORDER BY id',(source_id,)):
        withdrawal=get(connection,row['id'])
        if open_outlook(connection,row['id']) or pending_choice(connection,withdrawal) or any(not check['done'] for check in checks(connection,withdrawal)):
            return True
    return False


def previous_choice(connection,withdrawal):
    data=withdrawal['impact']
    employment=connection.execute('SELECT * FROM employment_assignments WHERE id=?',(data['employment_id'],)).fetchone()
    choice=connection.execute('SELECT * FROM workflow_goal_choices WHERE employee_pn=? AND assignment_number=? AND goal_year=?',
        (employment['person_number'],employment['assignment_number'],data['goal_year'])).fetchone()
    if not choice:return None
    metadata=json.loads(choice['source_json'])
    belongs=metadata.get('hr_goal_source_id')==withdrawal['source_id']
    for key,table in (('legacy_form_import_id','legacy_form_imports'),('word_pdf_import_id','word_pdf_imports')):
        if metadata.get(key):
            belongs=belongs or bool(connection.execute(f'''SELECT 1 FROM {table} p JOIN hr_goal_sources s ON s.sha256=p.sha256
                WHERE s.id=? AND p.id=?''',(withdrawal['source_id'],metadata[key])).fetchone())
    return dict(choice) if belongs else None


def pending_choice(connection,withdrawal):
    choice=previous_choice(connection,withdrawal)
    data=withdrawal['impact']
    return choice if choice and review.sources(connection,data['employment_id'],data['goal_year']) else None


@serialized_goal_delivery
def withdraw(connection,source_id,*,expected_revision,expected_impact,reason,checked=False,user_id=None):
    if not checked:
        raise ValueError('Bitte Rücknahme und Auswirkungen ausdrücklich prüfen und bestätigen.')
    connection.execute('BEGIN IMMEDIATE')
    try:
        source=review.get(connection,source_id)
        if source['revision']!=expected_revision:
            raise ValueError('Die Quelle wurde inzwischen bearbeitet. Rücknahme erneut prüfen.')
        affected=impact(connection,source_id)
        if review.digest(affected)!=expected_impact:
            raise ValueError('Ausgaben, Versand oder Rückläufe haben sich geändert. Auswirkungen erneut prüfen.')
        cur=connection.execute('''INSERT INTO hr_goal_withdrawals(source_id,confirmed_revision_id,through_revision,reason,impact_json,user_id,created_at)
            VALUES (?,?,?,?,?,?,?)''',(source_id,affected['confirmed_revision_id'],expected_revision,reason.strip(),review.dump(affected),user_id,stamp()))
        withdrawal_id=cur.lastrowid
        # Only local groups with no Outlook call may be cancelled automatically.
        # Their complete membership and approved files remain in the history.
        for delivery in affected['deliveries']:
            if delivery['kind']=='goal' and delivery['status']=='prepared':
                connection.execute('''UPDATE hr_goal_dispatches SET status='cancelled',resolution_note=?,updated_at=? WHERE id=? AND status='prepared' ''',
                    (f'Zielfreigabe zurückgenommen ({withdrawal_id}): {reason.strip()}. Gültige übrige Ausgaben erneut auswählen.',stamp(),delivery['id']))
                review.event(connection,'prepared_group_cancelled',source_id=source_id,dispatch_id=delivery['id'],user_id=user_id,withdrawal_id=withdrawal_id)
        new_revision=expected_revision+1
        connection.execute('UPDATE hr_goal_sources SET revision=? WHERE id=?',(new_revision,source_id))
        connection.execute('''INSERT INTO hr_goal_revisions(source_id,revision,status,employment_id,goal_year,goals_json,note,user_id,created_at)
            VALUES (?,?,'draft',?,?,?,?,?,?)''',(source_id,new_revision,source['employment_id'],source['goal_year'],source['goals_json'],reason.strip(),user_id,stamp()))
        review.event(connection,'approval_withdrawn',source_id=source_id,user_id=user_id,withdrawal_id=withdrawal_id,
                     through_revision=expected_revision,reason=reason.strip())
        connection.commit()
        return withdrawal_id
    except Exception:
        connection.rollback();raise


def release_empty_choice(connection,withdrawal_id,*,user_id=None):
    """Explicitly checked old assignments may proceed without the withdrawn goals.

    Existing competing sources still require an explicit source choice; we never
    silently select a different source. Called inside the follow-up transaction.
    """
    withdrawal=get(connection,withdrawal_id)
    if open_outlook(connection,withdrawal_id) or any(not check['done'] for check in checks(connection,withdrawal)):
        return
    data=withdrawal['impact']
    if review.sources(connection,data['employment_id'],data['goal_year']):
        return
    choice=previous_choice(connection,withdrawal)
    if choice:
        connection.execute('DELETE FROM workflow_goal_choices WHERE employee_pn=? AND assignment_number=? AND goal_year=?',
            (choice['employee_pn'],choice['assignment_number'],data['goal_year']))
        review.event(connection,'withdrawn_choice_cleared',source_id=withdrawal['source_id'],user_id=user_id,
                     withdrawal_id=withdrawal_id,previous_choice=dict(choice),reason='Auswirkungen geprüft; keine weitere freigegebene Quelle vorhanden')
