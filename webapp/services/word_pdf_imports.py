"""Prüfbare PDF-Rückläufe und versionierte Zielquellen ohne Arbeitsmappen-ID."""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import uuid
from datetime import date, datetime
from pathlib import Path

from .word_pdf import inspect_word_pdf, NARRATIVE_FIELDS
from .documents import PdfInspection, inspect_pdf, _case_row, _store_current_document, refresh_case_status, update_scope_obligations
from .legacy_forms import COMPETENCY_TAGS


def now():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def stage_pdf(connection, path: Path, *, filename: str, directory: Path):
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    existing=connection.execute('SELECT id FROM word_pdf_imports WHERE sha256=?',(digest,)).fetchone()
    if existing:
        return existing['id'], True
    if connection.execute('SELECT id FROM official_documents WHERE sha256=?',(digest,)).fetchone():
        raise ValueError('Dieses PDF wurde bereits als offizielles Dokument importiert.')
    parsed=inspect_word_pdf(path)
    directory.mkdir(parents=True,exist_ok=True)
    stored=directory/(digest+'-'+uuid.uuid4().hex[:12]+'.pdf')
    try:
        shutil.copyfile(path,stored)
        cursor=connection.execute('''INSERT INTO word_pdf_imports(original_filename,stored_path,sha256,parsed_json,created_at)
            VALUES (?,?,?,?,?)''',(Path(filename).name,str(stored),digest,json.dumps(parsed,ensure_ascii=False),now()))
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback(); stored.unlink(missing_ok=True)
        duplicate=connection.execute('SELECT id FROM word_pdf_imports WHERE sha256=?',(digest,)).fetchone()
        if duplicate:
            return duplicate['id'], True
        raise
    except Exception:
        connection.rollback(); stored.unlink(missing_ok=True); raise
    return cursor.lastrowid, False


def matching_cases(connection, data):
    # Führungskraft nur anzeigen: Wechsel darf die richtige Person nicht ausschliessen.
    pn=data.get('pn',''); kind=data.get('document_kind','')
    year=data.get('period_end','')[:4]
    if not pn or not year.isdigit() or kind not in ('review','outlook'):
        return []
    year_column='outlook_year' if kind=='outlook' else 'review_year'
    return [dict(row) for row in connection.execute(f'''SELECT dc.*,c.review_year,c.outlook_year,e.first_name,e.last_name
        FROM dialog_cases dc JOIN cycles c ON c.id=dc.cycle_id JOIN employees e ON e.pn=dc.employee_pn
        WHERE dc.employee_pn=? AND dc.active=1 AND c.{year_column}=? ORDER BY dc.id''',(pn,int(year)))]


def _validate(reviewed):
    data=reviewed['data']
    if data.get('document_kind') not in ('review','outlook') or not str(data.get('pn','')).isdigit():
        raise ValueError('Dokumenttyp und Personalnummer müssen geprüft sein.')
    try:
        start=date.fromisoformat(data['period_start']); end=date.fromisoformat(data['period_end'])
        if data.get('conducted') != 'nein':
            date.fromisoformat(data['dialog_date'])
    except (ValueError,KeyError,TypeError) as exc:
        raise ValueError('Bitte gültige Zeiträume und ein Gesprächsdatum erfassen.') from exc
    if start>end:
        raise ValueError('Der Zeitraum endet vor seinem Beginn.')
    if data.get('conducted') not in ('ja', 'nein'):
        raise ValueError('Bitte die Durchführung anhand des PDF ausdrücklich mit Ja oder Nein bestätigen.')
    if data['conducted'] == 'nein':
        if not data.get('no_md_reason', '').strip():
            raise ValueError('Bitte die Begründung für die Nichtdurchführung aus dem PDF erfassen.')
        if any(data.get(k) for k in ('dialog_date', 'rating', 'employment_continues')) or reviewed.get('scan_required'):
            raise ValueError('Bei Nichtdurchführung Gesprächsdatum, Beurteilung, Anstellungsentscheid und Scan-Anforderung leer lassen.')
        if reviewed.get('assessments') or (data['document_kind']=='outlook' and (reviewed.get('performance_goals') or reviewed.get('development_goals'))):
            raise ValueError('Bei Nichtdurchführung sind aktuelle Einschätzungen oder vereinbarte Ziele widersprüchlich. Bitte am Original klären.')
    for key in ('higher_manager_requested', 'sap_current', 'career_requested'):
        if data.get(key, '') not in ('', 'ja', 'nein'):
            raise ValueError('Ungültige Ja-/Nein-Angabe.')
    narratives = reviewed.get('narratives', {})
    if not isinstance(narratives, dict) or any(k not in NARRATIVE_FIELDS or not isinstance(v, str) for k, v in narratives.items()):
        raise ValueError('Ungültige Freitextangaben.')
    if data.get('document_kind')=='review' and data['conducted']=='ja':
        if data.get('probation')=='ja' and data.get('employment_continues') not in ('ja','nein'):
            raise ValueError('Bitte den Anstellungsentscheid prüfen.')
        if data.get('probation')!='ja' and data.get('rating') not in tuple('ABCDE'):
            raise ValueError('Bitte die Gesamtbeurteilung anhand des PDF prüfen und auswählen.')
    for key in ('performance_goals','development_goals'):
        goals=reviewed.get(key,[])
        if not isinstance(goals,list) or len(goals)>200:
            raise ValueError('Ungültige Zielanzahl.')
        for goal in goals:
            if not isinstance(goal,dict) or any(not isinstance(goal.get(k,''),str) for k in ('title','criteria','steps','target_date','competency')):
                raise ValueError('Ungültige Zielangaben.')
            if not goal.get('title','').strip():
                raise ValueError('Bei einem ausgefüllten Ziel fehlt der Zieltext.')
            if key=='development_goals' and goal.get('competency') not in COMPETENCY_TAGS.values():
                raise ValueError('Bitte jedem Entwicklungsziel eine bekannte Kompetenz zuordnen.')
    if not isinstance(reviewed.get('assessments',{}),dict) or any(k not in COMPETENCY_TAGS.values() or not isinstance(v,str) for k,v in reviewed.get('assessments',{}).items()):
        raise ValueError('Ungültige Kompetenz-Einschätzung.')


def confirm_import(connection, import_id: int, *, reviewed: dict, assignment: str, case_id: str,
                   historical: bool, reason: str, user_id=None):
    _validate(reviewed)
    reviewed['data']['ans']=assignment
    reviewed['data']['probation']='ja' if reviewed['data'].get('probation')=='ja' else 'nein'
    reviewed.setdefault('scan_required',False)
    reviewed.setdefault('narratives',{})
    for key in ('narratives', 'assessments'):
        reviewed[key] = {name: value.replace('\r\n','\n').replace('\r','\n').strip() for name,value in reviewed.get(key,{}).items()}
    data=reviewed['data']; kind=data['document_kind']; pn=data['pn']; year=int(data['period_end'][:4])
    item=connection.execute('SELECT * FROM word_pdf_imports WHERE id=?',(import_id,)).fetchone()
    if not item or item['status']!='pending':
        raise ValueError('Dieser Rücklauf ist nicht mehr zur Prüfung offen.')
    if not connection.execute('SELECT id FROM employment_assignments WHERE person_number=? AND assignment_number=?',(pn,assignment)).fetchone():
        raise ValueError('Personalnummer und Anstellung sind nicht in den Stammdaten vorhanden.')
    case=None
    if historical:
        if data['conducted']=='nein':
            raise ValueError('Ein nicht durchgeführter Ausblick kann nicht als vereinbarte Zielquelle übernommen werden.')
        if kind!='outlook':
            raise ValueError('Als nachgereichte Zielquelle sind nur Ausblicke zulässig.')
        if not reason.strip():
            raise ValueError('Bitte die Übernahme als nachgereichten Ausblick begründen.')
    else:
        case=_case_row(connection,case_id)
        expected=case['outlook_year'] if kind=='outlook' else case['review_year']
        if case['employee_pn']!=pn or case['employment_assignment']!=assignment or expected!=year:
            raise ValueError('Personalnummer, Anstellung oder Zielzeitraum passen nicht zum gewählten Fall.')
        if not case['active']:
            raise ValueError('Der gewählte Fall ist nicht mehr aktiv.')
        # Abweichende unterjährige Ereignisse nicht aufgrund des Jahres allein übernehmen.
        if case['period_start'] and case['period_end'] and kind=='review' and (case['period_start'],case['period_end'])!=(data['period_start'],data['period_end']) and not reason.strip():
            raise ValueError('Der Zeitraum weicht vom Fall ab. Bitte die Zuordnung begründen.')
        if data.get('manager_pn')!=case['manager_pn'] and not reason.strip():
            raise ValueError('Die Führungskraft weicht vom Fall ab. Bitte die Zuordnung begründen.')
    if case and kind=='review':
        event=connection.execute('SELECT event_type FROM dialog_events WHERE legacy_case_id=?',(case_id,)).fetchone()
        if event and (event['event_type']=='probation_review') != (data.get('probation')=='ja'):
            raise ValueError('Probezeitformular und Ereignisart des Falls passen nicht zusammen.')
    if case:
        current_scope = case['official_scope'] or case['suggested_scope']
        has_waiver = connection.execute("SELECT 1 FROM official_documents WHERE case_id=? AND is_current=1 AND variant='administrative' AND document_kind IN ('review','outlook')", (case_id,)).fetchone()
        if (data['conducted']=='nein' or has_waiver) and reviewed.get('scope') != current_scope:
            raise ValueError('Bei Nichtdurchführung bleibt der bisherige MD-Umfang bestehen. Eine Umfangsänderung muss separat geklärt werden.')
    original=json.loads(item['parsed_json'])
    if (original.get('issues') or original.get('data',{}).get('pn')!=pn) and not reason.strip():
        raise ValueError('Bitte die Klärung der Erkennungs- oder Zuordnungsprobleme dokumentieren.')
    source=Path(item['stored_path'])
    if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=item['sha256']:
        raise ValueError('Das gespeicherte Original-PDF fehlt oder wurde verändert.')
    comparable = lambda value: {k:v for k,v in value.items() if k in ('data','scope','performance_goals','development_goals','assessments','scan_required','narratives')}
    for previous in connection.execute("SELECT id,reviewed_json,case_id FROM word_pdf_imports WHERE status IN ('imported','historical') ORDER BY id"):
        if (previous['case_id'] or '') == (case_id if not historical else '') and comparable(json.loads(previous['reviewed_json'])) == comparable(reviewed):
            with connection:
                connection.execute("""UPDATE word_pdf_imports SET status='duplicate',duplicate_of=?,
                    reviewed_json=?,case_id=?,review_note=?,reviewed_by=?,reviewed_at=? WHERE id=?""",
                    (previous['id'],json.dumps(reviewed,ensure_ascii=False),previous['case_id'],
                     f"Inhaltliche Dublette von Prüfung {previous['id']}. " + reason,user_id,now(),import_id))
            return None
    if case and kind=='outlook':
        existing_payload=json.loads(case['data_json'] or '{}').get(kind) or {}
        if (existing_payload.get('performance_goals') or existing_payload.get('development_goals')) and not reason.strip():
            raise ValueError('Im Fall sind bereits Ziele vorhanden. Bitte vor der Ersetzung einen Ersetzungsgrund erfassen.')
    if kind=='outlook' and data['conducted']=='nein' and connection.execute(
        'SELECT 1 FROM word_pdf_goal_versions WHERE employee_pn=? AND assignment_number=? AND goal_year=? AND is_current=1', (pn, assignment, year)).fetchone():
        raise ValueError('Für dieses Jahr besteht bereits eine vereinbarte Zielquelle. Die Nichtdurchführung muss zuerst fachlich geklärt werden.')
    inspection=inspect_pdf(source)
    timestamp=now(); document_id=None
    with connection:
        # Alle Änderungen in einer Transaktion; kein partieller Ziel-/Dokumentimport.
        if kind=='outlook' and data['conducted']=='ja':
            old=connection.execute('''SELECT * FROM word_pdf_goal_versions WHERE employee_pn=? AND assignment_number=? AND goal_year=? AND is_current=1''',(pn,assignment,year)).fetchone()
            if old and not reason.strip():
                raise ValueError('Für diese Anstellung und dieses Zieljahr besteht bereits eine Zielversion. Bitte Ersetzungsgrund erfassen.')
            if old:
                if old['case_id'] and old['case_id']!=case_id:
                    raise ValueError('Die bisherige Zielquelle gehört zu einem anderen Fall. Bitte dort ersetzen, damit die Quellen nicht auseinanderlaufen.')
                connection.execute('UPDATE word_pdf_goal_versions SET is_current=0 WHERE id=?',(old['id'],))
            connection.execute('''INSERT INTO word_pdf_goal_versions(import_id,employee_pn,assignment_number,goal_year,period_start,period_end,goals_json,case_id,replaces_id,replacement_reason)
                VALUES (?,?,?,?,?,?,?,?,?,?)''',(import_id,pn,assignment,year,data['period_start'],data['period_end'],json.dumps({'performance_goals':reviewed.get('performance_goals',[]),'development_goals':reviewed.get('development_goals',[])},ensure_ascii=False),case_id if case else None,old['id'] if old else None,reason.strip()))
        if case:
            scope=reviewed.get('scope','')
            if scope not in ('full','review_only','outlook_only') or (kind=='review' and scope=='outlook_only') or (kind=='outlook' and scope=='review_only'):
                raise ValueError('Bitte einen zum Dokument passenden MD-Umfang wählen.')
            block={**data,'source':'word_pdf','word_pdf_import_id':str(import_id),
                   'review_competencies':'|'.join(k for k,v in reviewed.get('assessments',{}).items() if v.strip()),
                   'development_competencies':'|'.join(dict.fromkeys(g['competency'] for g in reviewed.get('development_goals',[]) if kind=='outlook'))}
            not_conducted = data['conducted']=='nein'
            document_id=_store_current_document(connection,case=case,document_kind=kind,variant='administrative' if not_conducted else 'digital',original_filename=item['original_filename'],stored_path=source,digest=item['sha256'],received_at=item['created_at'],inspection=PdfInspection(inspection.text,block,inspection.page_count,inspection.fill_sign_detected,inspection.fill_sign_count),signature_checked=False,scan_required=False if not_conducted else (data.get('rating') in ('D','E') or data.get('employment_continues')=='nein' or reviewed.get('scan_required',False)),handoff_status='not_applicable' if not_conducted else 'needs_signature_check',replacement_reason=reason)
            payload=json.loads(case['data_json'] or '{}')
            section=dict(payload.get(kind) or {})
            if kind=='outlook':
                section.update(performance_goals=reviewed.get('performance_goals',[]),development_goals=reviewed.get('development_goals',[]))
            else:
                section.update(previous_performance_goals=reviewed.get('performance_goals',[]),previous_development_goals=reviewed.get('development_goals',[]),competencies=[{'competency':k,'text':v} for k,v in reviewed.get('assessments',{}).items() if v.strip()])
            section.update({key: data.get(key, '') for key in ('conducted', 'no_md_reason', 'period_start', 'period_end', 'dialog_date', 'higher_manager_requested', 'sap_current', 'career_requested')})
            section['narratives'] = reviewed.get('narratives', {})
            section['character_counts'] = {key: len(value.strip()) for key, value in section['narratives'].items()}
            section['assessment_character_counts'] = {key: len(value.strip()) for key, value in reviewed.get('assessments', {}).items()}
            section['sap_clarification_required'] = data.get('sap_current') == 'nein'
            section['word_pdf_import_id']=import_id
            payload[kind]=section
            connection.execute('UPDATE dialog_cases SET data_json=?,official_scope=?,updated_at=? WHERE case_id=?',(json.dumps(payload,ensure_ascii=False),scope,timestamp,case_id))
            if kind=='review':
                connection.execute("UPDATE dialog_cases SET dialog_date=?,period_start=?,period_end=?,overall_rating_code=?,agreement='' WHERE case_id=?",(data['dialog_date'],data['period_start'],data['period_end'],data.get('rating',''),case_id))
            update_scope_obligations(connection,case_id=case_id,scope=scope,timestamp=timestamp)
            refresh_case_status(connection,case_id)
        connection.execute('''UPDATE word_pdf_imports SET reviewed_json=?,status=?,case_id=?,official_document_id=?,review_note=?,reviewed_by=?,reviewed_at=? WHERE id=?''',(json.dumps(reviewed,ensure_ascii=False),'historical' if historical else 'imported',case_id if case else None,document_id,reason,user_id,timestamp,import_id))
    return document_id
