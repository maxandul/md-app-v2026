"""Separate correction drafts; never replace a manager's original dispatch record."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from .word_packages import create_word_package
from .word_dispatch import _mail_html, _stamp
from .outlook_lock import package_lock
from webapp.adapters.outlook import OutlookDraftAdapter


def person(connection, case_id, cycle_id):
    row = connection.execute('''SELECT dc.*, e.first_name,e.last_name,m.email AS recipient_email,
        m.first_name AS manager_first_name,m.salutation AS manager_salutation,
        COALESCE(de.event_type,'annual') AS event_type
        FROM dialog_cases dc JOIN employees e ON e.pn=dc.employee_pn
        JOIN employees m ON m.pn=dc.manager_pn LEFT JOIN dialog_events de ON de.legacy_case_id=dc.case_id
        WHERE dc.case_id=? AND dc.cycle_id=? AND dc.active=1''', (case_id,cycle_id)).fetchone()
    if not row: raise ValueError('Aktiver Fall nicht gefunden.')
    row = dict(row)
    scope = row['official_scope'] or row['suggested_scope']
    row['kinds'] = (['probation' if row['event_type']=='probation_review' else 'review'] if scope in ('full','review_only') else []) + (['outlook'] if scope in ('full','outlook_only') else [])
    from webapp.migrations import available
    if available(connection):
        from .part_responsibilities import case_parts
        row['parts']=[p for p in case_parts(connection,case_id) if p['required']]
    return row


def prepare(connection, *, case, kinds, template_paths, output_dir):
    if case.get('parts'):
        selected=[p for p in case['parts'] if ('probation' if p['kind']=='review' and p['event_type']=='probation_review' else p['kind']) in kinds]
        managers={p['manager_pn'] for p in selected}
        if len(managers)!=1 or len(selected)!=len(set(kinds)):
            raise ValueError('Diese Auswahl benötigt getrennte Empfängergruppen. Bitte die Teile gemeinsam über die Fallansicht vorbereiten.')
        part=selected[0]
        case={**case,**{k:part[k] for k in ('manager_pn','recipient_email','manager_first_name','manager_salutation')}}
    path, manifest = create_word_package(connection, cycle_id=case['cycle_id'], manager_pn=case['manager_pn'], case_id=case['case_id'], document_kinds=kinds, template_paths=template_paths, output_dir=output_dir)
    labels = {'review':'Rückblick','probation':'Probezeit-Rückblick','outlook':'Ausblick'}
    names = ', '.join(labels[d['kind']] for d in manifest['documents'])
    greeting = {'frau':'Liebe','herr':'Lieber'}.get((case['manager_salutation'] or '').casefold(),'Hallo')
    subject = f"MD-Korrektur: {case['first_name']} {case['last_name']} – {names}"
    body = f"{greeting} {case['manager_first_name']}\n\nIm Anhang erhältst du neu erzeugte Formulare für {case['first_name']} {case['last_name']} (Ans. {case['employment_assignment']}): {names}.\n\nBitte verwende diese für die genannten Gesprächsteile. Falls du die bisherigen Formulare bereits bearbeitet hast, gleiche die Inhalte vor dem Ersetzen ab.\n\nFreundliche Grüsse\nHR"
    now = _stamp()
    cur = connection.execute('''INSERT INTO word_person_corrections(case_id,stored_path,manifest_json,recipient_email,subject,body_text,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)''', (case['case_id'],str(path),json.dumps(manifest,ensure_ascii=False),case['recipient_email'] or '',subject,body,now,now))
    connection.commit()
    return cur.lastrowid


def prepare_groups(connection,*,case,kinds,template_paths,output_dir):
    """Prepare one durable output per actual recipient; return separate failures."""
    if not kinds or not set(kinds)<=set(case['kinds']):raise ValueError('Bitte gültige Gesprächsteile auswählen.')
    groups={}
    for kind in dict.fromkeys(kinds):
        part=next((p for p in case.get('parts',[]) if p['kind']==('review' if kind=='probation' else kind)),None)
        groups.setdefault(part['manager_pn'] if part else case['manager_pn'],[]).append(kind)
    ids=[];errors=[]
    for manager,selected in groups.items():
        try:ids.append(prepare(connection,case=case,kinds=selected,template_paths=template_paths,output_dir=output_dir))
        except (ValueError,LookupError,OSError) as exc:
            connection.rollback();errors.append(f'PN {manager}: {exc}')
    return ids,errors


from .outlook_lock import serialized_goal_delivery, check_goal_workflow


@serialized_goal_delivery
def act(connection, *, correction_id, action, template_paths, sender_email, subject='', body='', checked=False, adapter=None):
    row = connection.execute('SELECT * FROM word_person_corrections WHERE id=?',(correction_id,)).fetchone()
    if not row: raise ValueError('Einzelausgabe nicht gefunden.')
    with package_lock(Path(row['stored_path']).parents[1] / ('case-' + hashlib.sha256(row['case_id'].encode()).hexdigest())):
        row = connection.execute('SELECT * FROM word_person_corrections WHERE id=?',(correction_id,)).fetchone()
        if action in ('sent_confirmed','cancelled'):
            if not checked or row['status'] not in ('draft_created','failed','processing'):
                raise ValueError('Bitte den tatsächlichen Outlook-Stand prüfen und bestätigen.')
            connection.execute('UPDATE word_person_corrections SET status=?,updated_at=? WHERE id=?',(action,_stamp(),correction_id));connection.commit()
            return
        if action != 'draft' or row['status'] != 'prepared':
            raise ValueError('Diese Ausgabe wurde bereits an Outlook übergeben. Bestehenden Vorgang zuerst klären.')
        from webapp.migrations import available
        if not available(connection) and connection.execute("SELECT 1 FROM word_person_corrections WHERE case_id=? AND id<>? AND status IN ('processing','draft_created','failed')",(row['case_id'],correction_id)).fetchone():
            raise ValueError('Für diese Person ist noch ein Outlook-Vorgang offen. Diesen zuerst klären.')
        manifest = json.loads(row['manifest_json'])
        check_goal_workflow(connection,[row['case_id']],documents=manifest['documents'],exclude=('person',correction_id))
        case = person(connection,row['case_id'],manifest['cycle_id'])
        if case.get('parts'):
            selected=[p for p in case['parts'] if p['kind'] in {('review' if d['kind']=='probation' else d['kind']) for d in manifest['documents']}]
            if not selected or any(p['manager_pn']!=manifest['manager_pn'] for p in selected):
                raise ValueError('Zuständigkeit geändert. Bitte die betroffenen Formulare neu erzeugen.')
            case={**case,**{k:selected[0][k] for k in ('manager_pn','recipient_email','manager_first_name','manager_salutation')}}
        if case['recipient_email'] != row['recipient_email']:
            raise ValueError('Empfänger hat sich geändert. Bitte neu erzeugen.')
        if not sender_email or '@' not in sender_email or not row['recipient_email'] or '@' not in row['recipient_email']:
            raise ValueError('HR-Absender oder E-Mail-Adresse der Führungskraft fehlt.')
        if not subject.strip() or not body.strip(): raise ValueError('Betreff und Nachricht ausfüllen.')
        if hashlib.sha256(Path(row['stored_path']).read_bytes()).hexdigest() != manifest['sha256']:
            raise ValueError('Datei verändert. Bitte neu erzeugen.')
        with TemporaryDirectory(prefix='md-correction-check-') as tmp:
            _, current = create_word_package(connection,cycle_id=case['cycle_id'],manager_pn=case['manager_pn'],case_id=case['case_id'],document_kinds=[d['kind'] for d in manifest['documents']],template_paths=template_paths,output_dir=Path(tmp))
            if current['documents'] != manifest['documents']:
                raise ValueError('Grundlagen dieser Formulare haben sich geändert. Bitte neu erzeugen.')
        connection.execute("UPDATE word_person_corrections SET status='processing',subject=?,body_text=?,updated_at=? WHERE id=?",(subject.strip(),body.strip(),_stamp(),correction_id));connection.commit()
        try:
            result = (adapter or OutlookDraftAdapter()).create_encrypted_draft(sender_email=sender_email,recipient_email=row['recipient_email'],subject=subject.strip(),body_html=_mail_html(body),attachments=[Path(row['stored_path'])])
            if not result.encryption_flag_verified: raise ValueError('Verschlüsselungsmarkierung nicht bestätigt. Outlook prüfen.')
            connection.execute("UPDATE word_person_corrections SET status='draft_created',outlook_entry_id=?,updated_at=? WHERE id=?",(result.entry_id,_stamp(),correction_id));connection.commit()
        except Exception as exc:
            connection.execute("UPDATE word_person_corrections SET status='failed',error_message=?,updated_at=? WHERE id=?",(str(exc),_stamp(),correction_id));connection.commit()
            raise ValueError(str(exc)) from exc
