"""Return-aware follow-ups and selected, repeatable review generation."""
import hashlib
import json
from pathlib import Path
from . import goal_review as review
from .part_responsibilities import resolve, stamp
from .word_packages import prior_goals, create_word_package
from .packages import _secondary_employment_text


def revision(connection, revision_id, *, allow_withdrawn=False):
    row=connection.execute("SELECT * FROM hr_goal_revisions WHERE id=? AND status='confirmed'",(revision_id,)).fetchone()
    if not row:
        raise ValueError('Eine bestätigte Zielversion ist erforderlich.')
    if review.withdrawn(connection,revision_id):
        if allow_withdrawn:
            return dict(row)
        raise ValueError('Diese Zielfreigabe wurde zurückgenommen. Alte Ausgaben bleiben erhalten und dürfen nicht erneut verwendet werden.')
    latest=connection.execute("SELECT MAX(id) FROM hr_goal_revisions WHERE source_id=? AND status='confirmed'",(row['source_id'],)).fetchone()[0]
    if latest!=row['id']:
        raise ValueError('Die Zielversion wurde inzwischen ersetzt. Bitte neu laden.')
    return dict(row)


def return_evidence(connection, part):
    """Unassigned pending returns are uncertainty, never proof of absence."""
    evidence=[]
    for row in connection.execute("SELECT id,sha256,handoff_status,handoff_at,replaces_document_id FROM official_documents WHERE case_id=? AND document_kind IN ('review','no_md') AND is_current=1 ORDER BY id",(part['case_id'],)):
        evidence.append({'document_id':row['id'],'sha256':row['sha256'],'handoff_status':row['handoff_status'],
                         'handoff_at':row['handoff_at'],'replaces_document_id':row['replaces_document_id']})
    pending=connection.execute('''SELECT w.* FROM word_pdf_imports w LEFT JOIN workflow_pdf_state s ON s.import_id=w.id
        WHERE w.status='pending' AND COALESCE(s.dismissed,0)=0
        AND NOT EXISTS(SELECT 1 FROM hr_goal_origins o WHERE o.pdf_import_id=w.id) ORDER BY w.id''').fetchall()
    year=part['period_end'][:4]
    for row in pending:
        parsed=json.loads(row['reviewed_json'] or row['parsed_json'])
        data=parsed.get('data') or {}
        if row['case_id'] and row['case_id']!=part['case_id']:
            continue
        if data.get('document_kind') in ('outlook','feedback'):
            continue
        if data.get('pn') and str(data['pn'])!=part['employee_pn']:
            continue
        if data.get('ans') and str(data['ans'])!=part['employment_assignment']:
            continue
        if data.get('period_end') and str(data['period_end'])[:4]!=year:
            continue
        evidence.append({'pending_import_id':row['id'],'sha256':row['sha256'],
                         'assignment_uncertain':not (data.get('pn') and data.get('ans') and data.get('period_end'))})
    payload=json.loads(part['data_json'] or '{}').get('review') or {}
    if any(payload.get(k) for k in ('conducted','dialog_date','word_pdf_import_id','overall_rating','overall_rating_code')) and not evidence:
        evidence.append({'case_data':review.digest(payload)})
    # Unprocessed mail PDFs may not yet have made it into the PDF staging queue.
    rows=connection.execute('''SELECT a.id,a.sha256 FROM inbound_mail_attachments a
        WHERE a.status IN ('stored','review_required','failed') AND a.file_kind='md_pdf'
        AND a.official_document_id IS NULL
        AND NOT EXISTS(SELECT 1 FROM word_pdf_imports w WHERE w.sha256=a.sha256)
        AND NOT EXISTS(SELECT 1 FROM hr_goal_sources s WHERE s.sha256=a.sha256) ORDER BY a.id''').fetchall()
    evidence.extend({'unassigned_attachment_id':r['id'],'sha256':r['sha256']} for r in rows)
    return evidence


def inputs(connection, revision_id, case_id, template_paths, *, allow_return=False):
    rev=revision(connection,revision_id)
    part=resolve(connection,case_id)
    employment=connection.execute('SELECT * FROM employment_assignments WHERE id=?',(rev['employment_id'],)).fetchone()
    if (part['employee_pn'],part['employment_assignment'])!=(employment['person_number'],employment['assignment_number']):
        raise ValueError('Zielquelle und Anstellung passen nicht zusammen.')
    if not part['active'] or not part['required'] or part['event_status'] in ('cancelled','no_md'):
        raise ValueError('Für diesen Fall ist kein aktiver Rückblick vorgesehen.')
    if part['event_type']=='probation_review':
        raise ValueError('Diese Nachreichung betrifft reguläre Rückblicke, keinen Probezeit-Rückblick.')
    if part['period_end'][:4]!=str(rev['goal_year']):
        raise ValueError('Zieljahr und Rückblickzeitraum passen nicht zusammen.')
    goals=prior_goals(connection,employee_pn=part['employee_pn'],assignment=part['employment_assignment'],year=rev['goal_year'])
    if goals[2].get('hr_goal_revision_id')!=revision_id:
        raise ValueError('Eine andere Zielquelle ist ausgewählt. Quellenwahl erneut prüfen.')
    evidence=return_evidence(connection,part)
    if evidence and not allow_return:
        raise ValueError('Rückblick eingegangen oder Eingang noch unklar: Korrekturbedarf klären.')
    template=Path(template_paths.get('review',''))
    if not template.is_file():
        raise ValueError('Die Word-Vorlage für Rückblicke fehlt.')
    data={k:part[k] for k in ('case_id','cycle_id','employee_pn','employment_assignment','first_name','last_name','position',
        'manager_pn','manager_name','recipient_email','form_org_unit','form_org_source','period_start','period_end',
        'responsibility_revision','obligation_id')}
    data.update(revision_id=revision_id,goals=goals,template_sha256=hashlib.sha256(template.read_bytes()).hexdigest(),
        secondary_employment=_secondary_employment_text(connection,employee_pn=part['employee_pn'],employment_assignment=part['employment_assignment'],fallback=part['secondary_employment']))
    return data,review.digest(data),evidence


def targets(connection, revision_id, *, allow_withdrawn=False):
    rev=revision(connection,revision_id,allow_withdrawn=allow_withdrawn)
    return [dict(r) for r in connection.execute('''SELECT dc.case_id,dc.cycle_id,c.review_year,dc.active,
        dc.employee_pn,dc.employment_assignment FROM dialog_cases dc
        JOIN cycles c ON c.id=dc.cycle_id JOIN employment_assignments ea
        ON ea.person_number=dc.employee_pn AND ea.assignment_number=dc.employment_assignment
        WHERE ea.id=? AND (c.review_year=? OR substr(dc.period_end,1,4)=?) ORDER BY dc.id''',
        (rev['employment_id'],rev['goal_year'],str(rev['goal_year'])))]


def latest_decision(connection, revision_id, case_id, *, withdrawal_id=None):
    row=connection.execute('SELECT * FROM hr_goal_decisions WHERE revision_id=? AND case_id IS ? AND withdrawal_id IS ? ORDER BY id DESC LIMIT 1',(revision_id,case_id,withdrawal_id)).fetchone()
    return dict(row) if row else None


def decision_effective(decision,evidence):
    if not decision or decision['outcome']=='resume':
        return False
    if decision['outcome']=='corrected':
        return (decision['evidence_json']==review.dump(evidence)
                and any(e.get('document_id')==decision['corrected_document_id'] for e in evidence))
    return decision['evidence_json']==review.dump(evidence)


def decide(connection, revision_id, case_id, *, outcome, reason, expected_evidence,
           recipient_email='', requested_at='', corrected_document_id=None, user_id=None,
           withdrawal_id=None,effects_checked=False):
    if outcome not in ('no_change','waiting','request_correction','corrected','no_output','resume') or not reason.strip():
        raise ValueError('Bitte Entscheidung und Begründung angeben.')
    connection.execute('BEGIN IMMEDIATE')
    try:
        rev=revision(connection,revision_id,allow_withdrawn=withdrawal_id is not None)
        if withdrawal_id is not None:
            from . import goal_withdrawals
            withdrawal=goal_withdrawals.get(connection,withdrawal_id)
            if withdrawal['confirmed_revision_id']!=revision_id:
                raise ValueError('Die Entscheidung gehört nicht zu dieser Rücknahme.')
            if outcome in ('no_change','no_output','corrected'):
                if not effects_checked:
                    raise ValueError('Bitte auch bereits heruntergeladene oder manuell weitergegebene Dateien und deren Folgen prüfen.')
                if goal_withdrawals.open_outlook(connection,withdrawal_id):
                    raise ValueError('Den tatsächlichen Stand der offenen Outlook-Vorgänge zuerst klären.')
        affected_cases=withdrawal['impact']['cases'] if withdrawal_id is not None else targets(connection,revision_id)
        if case_id:
            if case_id not in {r['case_id'] for r in affected_cases}:
                raise ValueError('Dieser Rückblick gehört nicht zur Zielquelle.')
            part=resolve(connection,case_id)
            evidence=return_evidence(connection,part)
        else:
            if affected_cases:
                raise ValueError('Bitte die vorhandenen Rückblicke einzeln entscheiden.')
            evidence=[]
        if review.digest(evidence)!=expected_evidence:
            raise ValueError('Der Rücklaufstand wurde inzwischen geändert. Bitte neu prüfen.')
        if outcome=='request_correction':
            from datetime import datetime
            if not case_id or recipient_email!=part['recipient_email'] or '@' not in recipient_email:
                raise ValueError('Bitte den tatsächlichen Empfänger der Rückblick-Anforderung bestätigen.')
            try:
                datetime.fromisoformat(requested_at)
            except (ValueError,TypeError):
                raise ValueError('Bitte das Datum der tatsächlich erfolgten Anforderung angeben.') from None
        if outcome=='corrected':
            prior=latest_decision(connection,revision_id,case_id,withdrawal_id=withdrawal_id)
            doc=connection.execute("SELECT * FROM official_documents WHERE id=? AND case_id=? AND document_kind='review' AND is_current=1",(corrected_document_id,case_id)).fetchone()
            old_ids={e.get('document_id') for e in json.loads(prior['evidence_json'])} if prior else set()
            old_hashes={e.get('sha256') for e in json.loads(prior['evidence_json'])} if prior else set()
            if not prior or prior['outcome']!='request_correction' or not doc or doc['id'] in old_ids or doc['sha256'] in old_hashes:
                raise ValueError('Ein neuer, fachlich übernommener korrigierter Rücklauf ist erforderlich.')
            if old_ids-{None} and doc['replaces_document_id'] not in old_ids:
                raise ValueError('Der neue Rücklauf muss die bisherige Fassung nachvollziehbar ersetzen.')
            if doc['handoff_status']!='staged':
                raise ValueError('Die Prüfung und Bereitstellung des korrigierten Rücklaufs ist noch offen.')
            external=connection.execute('''WITH RECURSIVE versions(id,replaces_document_id,handoff_at) AS (
                SELECT id,replaces_document_id,handoff_at FROM official_documents WHERE id=?
                UNION SELECT d.id,d.replaces_document_id,d.handoff_at FROM official_documents d
                JOIN versions v ON d.id=v.replaces_document_id)
                SELECT 1 FROM versions WHERE COALESCE(handoff_at,'')<>'' LIMIT 1''',(doc['id'],)).fetchone()
            if external or any(e.get('handoff_at') for e in json.loads(prior['evidence_json'])):
                raise ValueError('Die externe Korrektur einer bereits bereitgestellten Fassung muss zuerst mit der zuständigen Stelle geklärt werden. Der Abschlussweg ist noch offen.')
        connection.execute('''INSERT INTO hr_goal_decisions(revision_id,case_id,outcome,reason,evidence_json,
            recipient_email,requested_at,corrected_document_id,user_id,created_at,withdrawal_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (revision_id,case_id,outcome,reason.strip(),review.dump(evidence),recipient_email,requested_at,corrected_document_id,user_id,stamp(),withdrawal_id))
        review.event(connection,'followup_decided',source_id=rev['source_id'],case_id=case_id,user_id=user_id,outcome=outcome,reason=reason)
        if withdrawal_id is not None:
            goal_withdrawals.release_empty_choice(connection,withdrawal_id,user_id=user_id)
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def output_dispatch(connection,output_id):
    row=connection.execute('''SELECT d.* FROM hr_goal_dispatches d JOIN hr_goal_dispatch_outputs m ON m.dispatch_id=d.id
        WHERE m.output_id=? AND d.status<>'cancelled' ORDER BY d.id DESC LIMIT 1''',(output_id,)).fetchone()
    return dict(row) if row else None


def generate(connection, selections, *, template_paths, output_dir, user_id=None):
    """One durable result per item. Recheck after selection and before rendering."""
    results=[]
    for selected in selections:
        rev_id,case_id,expected=selected
        try:
            connection.execute('BEGIN IMMEDIATE')
            data,fingerprint,_=inputs(connection,rev_id,case_id,template_paths)
            if fingerprint!=expected:
                raise ValueError('Grundlagen seit der Auswahl geändert. Bitte neu prüfen.')
            decision=latest_decision(connection,rev_id,case_id)
            if decision_effective(decision,[]) and decision['outcome'] in ('no_change','no_output','request_correction','waiting'):
                raise ValueError('Die dokumentierte Folgeentscheidung steht einer Vorlagenerstellung entgegen.')
            old=connection.execute('SELECT id FROM hr_goal_outputs WHERE revision_id=? AND case_id=? AND input_fingerprint=?',(rev_id,case_id,fingerprint)).fetchone()
            if old:
                output_id=old[0]
            else:
                path,manifest=create_word_package(connection,cycle_id=data['cycle_id'],manager_pn=data['manager_pn'],
                    case_id=case_id,document_kinds=['review'],template_paths=template_paths,output_dir=Path(output_dir),resolved_review=True)
                cur=connection.execute('''INSERT INTO hr_goal_outputs(revision_id,case_id,input_fingerprint,inputs_json,
                    stored_path,manifest_json,created_at) VALUES (?,?,?,?,?,?,?)''',
                    (rev_id,case_id,fingerprint,review.dump(data),str(path),review.dump(manifest),stamp()))
                output_id=cur.lastrowid
                rev=revision(connection,rev_id)
                review.event(connection,'output_created',source_id=rev['source_id'],case_id=case_id,user_id=user_id,output_id=output_id)
            connection.commit()
            results.append({'case_id':case_id,'output_id':output_id,'error':''})
        except Exception as exc:
            connection.rollback()
            results.append({'case_id':case_id,'output_id':None,'error':str(exc)})
    return results


def validate_output(connection,output_id,template_paths):
    row=connection.execute('SELECT * FROM hr_goal_outputs WHERE id=?',(output_id,)).fetchone()
    if not row:
        raise ValueError('Ausgabe nicht gefunden.')
    data,fingerprint,evidence=inputs(connection,row['revision_id'],row['case_id'],template_paths)
    decision=latest_decision(connection,row['revision_id'],row['case_id'])
    if decision_effective(decision,evidence):
        raise ValueError('Folgeentscheidung geändert. Vor einem Versand die Klärung prüfen.')
    if fingerprint!=row['input_fingerprint']:
        raise ValueError('Grundlagen dieser Ausgabe geändert. Bitte neu erstellen und prüfen.')
    manifest=json.loads(row['manifest_json'])
    if not Path(row['stored_path']).is_file() or hashlib.sha256(Path(row['stored_path']).read_bytes()).hexdigest()!=manifest['sha256']:
        raise ValueError('Ausgabedatei fehlt oder wurde verändert.')
    return dict(row),data


def approve(connection,output_id,template_paths,*,user_id=None):
    connection.execute('BEGIN IMMEDIATE')
    try:
        row,_=validate_output(connection,output_id,template_paths)
        if not row['approved_at']:
            connection.execute('UPDATE hr_goal_outputs SET approved_at=?,approved_by=? WHERE id=?',(stamp(),user_id,output_id))
            rev=revision(connection,row['revision_id'])
            review.event(connection,'output_approved',source_id=rev['source_id'],case_id=row['case_id'],user_id=user_id,output_id=output_id)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
