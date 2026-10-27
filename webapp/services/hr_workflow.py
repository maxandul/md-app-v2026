"""Arbeitslisten und kontrollierte Übergänge für die eigenständige HR-Betreuung."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path


def stamp():
    return datetime.now().astimezone().isoformat(timespec='microseconds')


def pending_pdfs(db):
    from webapp.migrations import available
    routed=" AND NOT EXISTS(SELECT 1 FROM hr_goal_origins o WHERE o.pdf_import_id=w.id)" if available(db) else ''
    return db.execute("""SELECT w.* FROM word_pdf_imports w LEFT JOIN workflow_pdf_state s ON s.import_id=w.id
        WHERE w.status='pending' AND COALESCE(s.dismissed,0)=0"""+routed+' ORDER BY w.id').fetchall()


def pdf_queue(db, *, query='', status='pending', page=1):
    where=[];args=[]
    from webapp.migrations import available
    if available(db) and status=='pending':
        where.append('NOT EXISTS(SELECT 1 FROM hr_goal_origins o WHERE o.pdf_import_id=w.id)')
    if status=='dismissed':where.append('COALESCE(s.dismissed,0)=1')
    elif status=='pending':where.append("w.status='pending' AND COALESCE(s.dismissed,0)=0")
    elif status in ('imported','historical','duplicate'):where.append('w.status=?');args.append(status)
    elif status!='all':raise ValueError('Unbekannter Prüfstatus.')
    if query.strip():
        where.append("(w.original_filename LIKE ? OR json_extract(COALESCE(NULLIF(w.reviewed_json,''),w.parsed_json),'$.data.pn') LIKE ?)")
        args += ['%'+query.strip()+'%']*2
    clause=' WHERE '+' AND '.join(where) if where else ''
    source=' FROM word_pdf_imports w LEFT JOIN workflow_pdf_state s ON s.import_id=w.id'
    total=db.execute('SELECT COUNT(*)'+source+clause,args).fetchone()[0]
    pages=max(1,(total+24)//25);page=max(1,min(page,pages))
    rows=db.execute("SELECT w.id,w.original_filename,w.status,w.created_at,COALESCE(s.dismissed,0) AS dismissed"+source+clause+' ORDER BY w.id DESC LIMIT 25 OFFSET ?',[*args,(page-1)*25]).fetchall()
    return dict(word_pdf_queue=rows,pdf_total=total,pdf_page=page,pdf_pages=pages,pdf_query=query,pdf_status=status)


def pdf_state(db, item_id):
    row=db.execute('SELECT * FROM workflow_pdf_state WHERE import_id=?',(item_id,)).fetchone()
    return dict(row) if row else {'revision':0,'dismissed':0,'reason':''}


def lock_pdf(db,item_id,revision):
    db.execute('BEGIN IMMEDIATE')
    item=db.execute('SELECT status FROM word_pdf_imports WHERE id=?',(item_id,)).fetchone()
    state=pdf_state(db,item_id)
    if not item or item['status']!='pending' or str(state['revision'])!=str(revision):
        db.rollback()
        raise ValueError('Die Prüfung wurde inzwischen geändert. Lade die Seite neu und vergleiche den gespeicherten Stand. Deine Eingaben werden unten weiterhin angezeigt.')
    return state


def advance_pdf(db,item_id,*,dismissed=0,reason=''):
    db.execute('''INSERT INTO workflow_pdf_state(import_id,revision,dismissed,reason,updated_at) VALUES (?,1,?,?,?)
        ON CONFLICT(import_id) DO UPDATE SET revision=revision+1,dismissed=excluded.dismissed,reason=excluded.reason,updated_at=excluded.updated_at''',(item_id,dismissed,reason,stamp()))


def closure_summary(db,cycle_id):
    def count(sql):return db.execute(sql,(cycle_id,)).fetchone()[0]
    return {
      'Offene Pflichtdokumente':count("SELECT COUNT(*) FROM document_obligations o JOIN dialog_events e ON e.id=o.dialog_event_id WHERE e.cycle_id=? AND e.status<>'cancelled' AND o.required=1 AND o.status NOT IN ('complete','waived')"),
      'Offene Dossierübergaben':count("SELECT COUNT(*) FROM official_documents WHERE cycle_id=? AND is_current=1 AND variant='digital' AND signature_checked=0"),
      'Offene Word-Versandvorgänge':count("SELECT COUNT(*) FROM word_dispatch_packages p LEFT JOIN word_mail_deliveries d ON d.package_id=p.id WHERE p.cycle_id=? AND p.id=(SELECT MAX(x.id) FROM word_dispatch_packages x WHERE x.cycle_id=p.cycle_id AND x.manager_pn=p.manager_pn AND x.discarded_at='') AND COALESCE(d.status,'') NOT IN ('sent_confirmed','cancelled')"),
      'Noch nicht exportierte vollständige Rückblicke':count("SELECT COUNT(*) FROM dialog_cases c JOIN dialog_events e ON e.legacy_case_id=c.case_id WHERE c.cycle_id=? AND c.status='vollstaendig' AND c.official_scope IN ('full','review_only') AND e.sap_leading=1 AND c.overall_rating_code<>'' AND NOT EXISTS(SELECT 1 FROM sap_export_rows r WHERE r.dialog_event_id=e.id)"),
      'Ungebündelte Feedbacks':count('SELECT COUNT(*) FROM word_feedback_submissions WHERE cycle_id=? AND bundle_id IS NULL'),
      'Ungeprüfte PDFs (durchlaufübergreifend)':len(pending_pdfs(db)),
      'Ereignisse ohne Durchlauf (gesamt)':db.execute("SELECT COUNT(*) FROM dialog_events WHERE cycle_id IS NULL AND status<>'cancelled'").fetchone()[0],
    }


def setup_checks(config,db):
    templates=config.get('WORD_TEMPLATE_PATHS',{})
    items=[]
    for kind,name in [('review','Rückblick'),('outlook','Ausblick'),('probation','Probezeit')]:
        ready=bool(templates.get(kind) and Path(templates[kind]).is_file())
        items.append((name+'-Vorlage vorhanden',ready,'Vorlagendatei und Pfad in instance/word_config.json hinterlegen.'))
    from .word_packages import preparation_templates
    for kind,path in preparation_templates(templates).items():
        items.append((('Reflexionsvorlage' if kind=='reflection' else 'Feedbackvorlage')+' vorhanden',path.is_file(),'Dateien unter templates/preparation prüfen; eigene Pfade optional in instance/word_config.json hinterlegen.'))
    for key,name,hint in [('HR_MAILBOX_EMAIL','HR-Absender hinterlegt','HR_MAILBOX_EMAIL in instance/organisation.json ergänzen.'),('OUTLOOK_MAILBOX_NAME','Outlook-Postfach hinterlegt','OUTLOOK_MAILBOX_NAME mit Systemadministration prüfen.')]:
        items.append((name,bool(config.get(key)),hint))
    items.append(('Dossierordner vorhanden',Path(config['DOSSIER_HANDOFF_ROOT']).is_dir(),'Dossierpfad mit Systemadministration prüfen; Schreibzugriff und RPA separat testen.'))
    items.append(('SAP-Daten vorhanden',bool(db.execute('SELECT 1 FROM sap_imports LIMIT 1').fetchone()),'Vollständigen freigegebenen SAP-Export unter Stammdaten einlesen.'))
    items.append(('Prozessbackup vorhanden',bool(list(Path(config['BACKUP_ROOT']).glob('MD_Backup_*.zip'))),'Systemadministration erstellt ein Backup; Vorlagen und Konfiguration zusätzlich sichern.'))
    return items


def attach_event(db,event_id,cycle_id,reason):
    if len(reason.strip())<10:raise ValueError('Bitte die Zuordnung mit mindestens 10 Zeichen begründen.')
    e=db.execute('''SELECT e.*,a.person_number,a.assignment_number,m.manager_person_number FROM dialog_events e JOIN employment_assignments a ON a.id=e.employment_id JOIN manager_assignments m ON m.id=e.manager_assignment_id WHERE e.id=?''',(event_id,)).fetchone()
    c=db.execute('SELECT * FROM cycles WHERE id=?',(cycle_id,)).fetchone()
    if not e or e['cycle_id'] is not None or e['status']=='cancelled':raise ValueError('Nur ein offenes Ereignis ohne Durchlauf kann zugeordnet werden.')
    if not c or c['review_year']!=e['review_year'] or c['status']=='abgeschlossen':raise ValueError('Wähle einen offenen Durchlauf mit demselben Rückblickjahr. Bei Bedarf zuerst den Durchlauf eröffnen oder wieder öffnen.')
    if db.execute('SELECT 1 FROM dialog_cases WHERE cycle_id=? AND employee_pn=? AND employment_assignment=? AND manager_pn=?',(cycle_id,e['person_number'],e['assignment_number'],e['manager_person_number'])).fetchone():
        raise ValueError('Für diese Person, Anstellung und Führungslinie besteht bereits ein Fall im Durchlauf. Prüfe diesen bestehenden Fall. Eine doppelte Fehlanlage kannst du begründet aufheben; fachlich unterschiedliche Gespräche benötigen eine Klärung mit der Systemadministration.')
    with db:
        db.execute('''INSERT INTO dialog_cases(case_id,cycle_id,employee_pn,employment_assignment,manager_pn,suggested_scope,suggestion_reason,status,period_start,period_end,data_json,active,updated_at)
            VALUES (?,?,?,?,?,?,?,'offen',?,?,'',1,?)''',(e['event_id'],cycle_id,e['person_number'],e['assignment_number'],e['manager_person_number'],e['required_scope'],reason,e['period_start'],e['period_end'],stamp()))
        db.execute('UPDATE dialog_events SET cycle_id=?,legacy_case_id=?,updated_at=? WHERE id=?',(cycle_id,e['event_id'],stamp(),event_id))
    return e['event_id']


def cancel_manual_event(db,event_id,reason):
    if len(reason.strip())<10:raise ValueError('Bitte die Aufhebung mit mindestens 10 Zeichen begründen.')
    e=db.execute('SELECT * FROM dialog_events WHERE id=?',(event_id,)).fetchone()
    if not e or e['source']!='manual' or e['status']=='cancelled':raise ValueError('Nur ein noch nicht aufgehobenes manuelles Ereignis kann hier aufgehoben werden.')
    if e['legacy_case_id'] and db.execute('SELECT 1 FROM official_documents WHERE case_id=?',(e['legacy_case_id'],)).fetchone():raise ValueError('Zum Ereignis liegen Dokumente vor. Eine Aufhebung erfordert eine separate fachliche Klärung.')
    with db:
        db.execute("UPDATE dialog_events SET status='cancelled',sap_leading=0,source_reason=source_reason || ?,updated_at=? WHERE id=?",('\nAufgehoben: '+reason,stamp(),event_id))
        db.execute("UPDATE document_obligations SET status='waived',updated_at=? WHERE dialog_event_id=?",(stamp(),event_id))
        if e['legacy_case_id']:db.execute('UPDATE dialog_cases SET active=0 WHERE case_id=?',(e['legacy_case_id'],))
