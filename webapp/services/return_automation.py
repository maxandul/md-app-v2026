"""Admit only validated new originals; use the existing versioned handoff.

No OCR guesses, replacement, email movement or signature decisions. Data commit
and file delivery are separate: a delivery failure must not import data twice.
"""
from copy import deepcopy
import json
from pathlib import Path

from . import return_review as returns
from .word_pdf import inspect_word_pdf


def enabled():
    from flask import current_app, has_app_context
    return bool(has_app_context() and current_app.config.get('HR_GOAL_WORKFLOW')
                and current_app.config.get('HR_RETURN_AUTOMATION'))


def record(db, import_id, state, reasons=()):
    row = db.execute('SELECT parsed_json FROM word_pdf_imports WHERE id=?',(import_id,)).fetchone()
    parsed = json.loads(row[0])
    parsed['automation'] = {'state':state,'reasons':list(reasons)}
    with db:
        db.execute('UPDATE word_pdf_imports SET parsed_json=? WHERE id=?',
                   (json.dumps(parsed,ensure_ascii=False),import_id))
    return parsed['automation']


def process_new(db, import_id, *, handoff_dir):
    from .word_pdf_imports import confirm_import, matching_cases, _validate
    if not enabled() or not returns.available(db):
        return {'state':'disabled','reasons':[]}
    db.execute('BEGIN IMMEDIATE')
    try:
        item = db.execute('SELECT * FROM word_pdf_imports WHERE id=?',(import_id,)).fetchone()
        if not item or item['status']!='pending' or item['reviewed_json']:
            db.rollback()
            return {'state':'unchanged','reasons':[]}
        if db.execute('SELECT 1 FROM workflow_pdf_state WHERE import_id=?',(import_id,)).fetchone():
            raise ValueError('Die manuelle Bearbeitung dieses Eingangs hat bereits begonnen.')
        if db.execute('SELECT 1 FROM hr_goal_origins WHERE pdf_import_id=?',(import_id,)).fetchone():
            raise ValueError('Dieser Eingang wird bereits als Zielquelle bearbeitet.')
        source = returns.checked_file(item['stored_path'],item['sha256'])
        parsed = inspect_word_pdf(source)
        if 'MD-DATENBLOCK' in parsed.get('text',''):
            raise ValueError('Frühere Arbeitsmappenfassung: vollständige Angaben manuell prüfen.')
        validation = parsed.get('validation',{})
        if not validation.get('eligible'):
            db.rollback()
            return record(db,import_id,'needs_review',validation.get('reasons') or ['Formularformat nicht validiert.'])
        data = parsed['data']
        assignments = db.execute('SELECT assignment_number FROM employment_assignments WHERE person_number=?',(data['pn'],)).fetchall()
        if len(assignments)!=1:
            raise ValueError('Anstellung fehlt oder ist nicht eindeutig. Bitte anhand des Originals zuordnen.')
        matches = matching_cases(db,data)
        matches = [m for m in matches if m['active'] and m['required'] and m['event_status'] not in ('cancelled','no_md')
                   and m['employment_assignment']==assignments[0][0]
                   and (not data.get('manager_pn') or m['manager_pn']==data['manager_pn'])
                   and all(not data.get(k) or m[k]==data[k] for k in ('period_start','period_end'))
                   and (m['event_type']=='probation_review')==(data.get('probation')=='ja')]
        if len(matches)!=1:
            raise ValueError('Person, Anstellung, verantwortliche Führungskraft und genauer Zeitraum ergeben keinen eindeutigen offenen Gesprächsteil.')
        part = matches[0]
        if db.execute('SELECT 1 FROM official_documents WHERE case_id=? AND document_kind=? AND is_current=1',
                      (part['case_id'],data['document_kind'])).fetchone():
            raise ValueError('Für diesen Gesprächsteil besteht bereits eine Fassung. Ersatz oder zusätzlichen Scan manuell klären.')
        others = db.execute("SELECT id,parsed_json FROM word_pdf_imports WHERE id<>? AND status='pending'",(import_id,))
        for other in others:
            prior = json.loads(other['parsed_json']).get('data',{})
            if all(prior.get(k)==data.get(k) for k in ('pn','document_kind','period_start','period_end')):
                raise ValueError('Ein weiterer ungeklärter Rücklauf für denselben Gesprächsteil liegt bereits vor.')
        reviewed = {k:deepcopy(parsed.get(k,{} if k in ('data','narratives','assessments') else []))
                    for k in ('data','narratives','assessments','performance_goals','development_goals')}
        for key in ('performance_goals','development_goals'):
            for goal in reviewed[key]:goal.pop('evidence',None)
        reviewed.update(scope=part['official_scope'] or part['suggested_scope'],source_role='digital',
                        format_validation={**validation,'sha256':item['sha256']})
        _validate(reviewed)
        # confirm_import commits this reservation and all data in one transaction.
        doc = confirm_import(db,import_id,reviewed=reviewed,assignment=assignments[0][0],case_id=part['case_id'],
                             historical=False,reason='',validation_origin='automatic')
    except (ValueError,LookupError) as exc:
        db.rollback()
        return record(db,import_id,'needs_review',[str(exc)])
    except Exception:
        db.rollback()
        raise
    if doc is None:
        return record(db,import_id,'duplicate')
    state = returns.view(db,doc)
    if any(state['part'][k]!=part[k] for k in ('manager_pn','period_start','period_end','responsibility_revision','required','active')):
        return record(db,import_id,'handoff_pending',['Gesprächsteilzuordnung hat sich nach der Datenübernahme geändert. Bereitstellung manuell prüfen.'])
    if not state['signature_ready']:
        return record(db,import_id,'signature_required',[state['signature_label']])
    try:
        returns.handoff(db,doc,directory=Path(handoff_dir),revision=state['revision'],token=state['token'])
    except (OSError,ValueError) as exc:
        return record(db,import_id,'handoff_pending',[str(exc)])
    return record(db,import_id,'staged')
