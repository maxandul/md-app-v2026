"""Word-Sammelerzeugung und separat protokollierter S/MIME-Versand."""
from __future__ import annotations

import hashlib
import html
import json
import shutil
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from webapp.adapters.outlook import OutlookDraftAdapter
from .packages import _secondary_employment_text
from .word_packages import create_word_package, prior_goals


def _stamp():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_fingerprint(connection, *, cycle_id, manager_pn, template_paths):
    cycle = connection.execute('SELECT review_year,outlook_year,sap_import_id FROM cycles WHERE id=?', (cycle_id,)).fetchone()
    manager = connection.execute('SELECT pn,first_name,last_name,email FROM employees WHERE pn=?', (manager_pn,)).fetchone()
    if not cycle or not manager:
        raise ValueError('Durchlauf oder Stammdaten der Führungskraft fehlen.')
    cases = connection.execute('''SELECT dc.case_id,dc.employee_pn,dc.employment_assignment,
        dc.official_scope,dc.suggested_scope,dc.period_start,dc.period_end,
        e.first_name,e.last_name,e.position,e.org_unit,e.entry_date,e.exit_date,e.probation_end,e.secondary_employment,
        COALESCE(de.event_type,'annual') AS event_type
        FROM dialog_cases dc JOIN employees e ON e.pn=dc.employee_pn
        LEFT JOIN dialog_events de ON de.legacy_case_id=dc.case_id
        WHERE dc.cycle_id=? AND dc.manager_pn=? AND dc.active=1 ORDER BY dc.case_id''', (cycle_id,manager_pn)).fetchall()
    snapshot = {'cycle':dict(cycle),'manager':dict(manager),'cases':[],'templates':{}}
    needed = set()
    for row in cases:
        item = dict(row)
        scope = row['official_scope'] or row['suggested_scope']
        if scope in ('full','review_only'):
            needed.add('probation' if row['event_type']=='probation_review' else 'review')
            if row['event_type']!='probation_review':
                year = int(row['period_end'][:4]) if row['period_end'] else cycle['review_year']
                item['goals'] = prior_goals(connection,employee_pn=row['employee_pn'],assignment=row['employment_assignment'],year=year)
        if scope in ('full','outlook_only'):
            needed.add('outlook')
        item['secondary'] = _secondary_employment_text(connection,employee_pn=row['employee_pn'],employment_assignment=row['employment_assignment'],fallback=row['secondary_employment'])
        snapshot['cases'].append(item)
    for kind in sorted(needed):
        path = template_paths.get(kind)
        if not path or not Path(path).is_file():
            raise ValueError(f'Word-Vorlage «{kind}» fehlt in der lokalen Konfiguration.')
        snapshot['templates'][kind] = _hash(path)
    numbers = [manager_pn, *(row['employee_pn'] for row in cases)]
    conflicts = connection.execute(f"SELECT COUNT(*) FROM sap_import_issues WHERE sap_import_id=? AND status='open' AND severity='blocking' AND person_number IN ({','.join('?' for _ in numbers)})", (cycle['sap_import_id'],*numbers)).fetchone()[0]
    if conflicts:
        raise ValueError('Offene SAP-Zuordnungskonflikte müssen zuerst geklärt werden.')
    return hashlib.sha256(json.dumps(snapshot,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def prepare_word_batch(connection, *, cycle_id, manager_pns, template_paths, output_dir):
    selected = list(dict.fromkeys(str(pn).strip() for pn in manager_pns if str(pn).strip()))
    if not selected:
        raise ValueError('Bitte mindestens eine Führungskraft auswählen.')
    directory = output_dir / ('WORD-BATCH-' + uuid.uuid4().hex)
    directory.mkdir(parents=True)
    packages, skipped = [], []
    try:
        with connection:
            for pn in selected:
                pending = connection.execute("""SELECT d.status FROM word_dispatch_packages p
                    JOIN word_mail_deliveries d ON d.package_id=p.id
                    WHERE p.cycle_id=? AND p.manager_pn=? AND d.status IN ('processing','draft_created','failed')
                    ORDER BY p.id DESC LIMIT 1""",(cycle_id,pn)).fetchone()
                if pending:
                    raise ValueError(f'Für PN {pn} ist noch eine Outlook-Übernahme, ein fehlgeschlagener Versuch oder ein Entwurf offen. Bitte zuerst den Versand bestätigen oder den Entwurf in Outlook löschen und hier als verworfen markieren.')
                scopes = connection.execute("SELECT COALESCE(NULLIF(official_scope,''),suggested_scope) AS scope FROM dialog_cases WHERE cycle_id=? AND manager_pn=? AND active=1", (cycle_id,pn)).fetchall()
                if not scopes:
                    raise ValueError(f'Für PN {pn} sind keine aktiven Fälle vorhanden.')
                if all(row['scope']=='none' for row in scopes):
                    skipped.append(pn)
                    continue
                fingerprint = source_fingerprint(connection,cycle_id=cycle_id,manager_pn=pn,template_paths=template_paths)
                path, manifest = create_word_package(connection,cycle_id=cycle_id,manager_pn=pn,template_paths=template_paths,output_dir=directory)
                if fingerprint != source_fingerprint(connection,cycle_id=cycle_id,manager_pn=pn,template_paths=template_paths):
                    raise ValueError('Die Quelldaten wurden während der Erzeugung geändert. Bitte erneut erzeugen.')
                cursor = connection.execute('''INSERT INTO word_dispatch_packages(export_id,cycle_id,manager_pn,stored_path,sha256,source_fingerprint,manifest_json,created_at)
                    VALUES (?,?,?,?,?,?,?,?)''', (manifest['export_id'],cycle_id,pn,str(path),manifest['sha256'],fingerprint,json.dumps(manifest,ensure_ascii=False),manifest['created_at']))
                packages.append({'id':cursor.lastrowid,'path':path,'manifest':manifest})
            if not packages:
                raise ValueError('Für diese Auswahl sind keine Word-Formulare vorgesehen.')
            batch = directory / 'MD_Word_Sammelausgabe.zip'
            with ZipFile(batch,'w',ZIP_DEFLATED) as archive:
                for package in packages:
                    # Pro Führungskraft ein eigener Anhang; das Sammel-ZIP bleibt bei HR.
                    archive.write(package['path'],package['path'].name)
    except Exception:
        shutil.rmtree(directory,ignore_errors=True)
        raise
    return batch, {'packages':packages,'skipped':skipped}


def word_dispatch_candidates(connection, *, cycle_id, template_paths):
    rows = connection.execute('''SELECT p.*, e.email AS recipient_email,
        TRIM(e.first_name || ' ' || e.last_name) AS manager_name,
        c.review_year,c.outlook_year,c.review_due_date,c.outlook_due_date,
        d.status AS delivery_status,d.error_message,d.updated_at AS delivery_updated_at
        FROM word_dispatch_packages p JOIN cycles c ON c.id=p.cycle_id
        LEFT JOIN employees e ON e.pn=p.manager_pn
        LEFT JOIN word_mail_deliveries d ON d.package_id=p.id
        WHERE p.cycle_id=? AND p.id=(SELECT MAX(p2.id) FROM word_dispatch_packages p2 WHERE p2.cycle_id=p.cycle_id AND p2.manager_pn=p.manager_pn)
        ORDER BY manager_name,p.manager_pn''', (cycle_id,)).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item['filename'] = Path(row['stored_path']).name
        item['document_count'] = len(json.loads(row['manifest_json'])['documents'])
        try:
            if not Path(row['stored_path']).is_file() or _hash(row['stored_path'])!=row['sha256']:
                raise ValueError('Die Versanddatei fehlt oder wurde verändert. Bitte neu erzeugen.')
            if source_fingerprint(connection,cycle_id=cycle_id,manager_pn=row['manager_pn'],template_paths=template_paths)!=row['source_fingerprint']:
                raise ValueError('Stammdaten, Ziele oder Vorlagen haben sich geändert. Bitte neu erzeugen.')
            if not row['recipient_email']:
                raise ValueError('Geschäftliche E-Mail-Adresse fehlt.')
            item['readiness_error'] = ''
        except (ValueError,OSError) as exc:
            item['readiness_error'] = str(exc)
        item['ready'] = not item['readiness_error'] and row['delivery_status'] not in ('processing','draft_created','sent_confirmed','cancelled')
        result.append(item)
    return result


def word_message(row, *, sender_email, subject_template='', body_template=''):
    values = {'manager_name':row['manager_name'] or row['manager_pn'],
              'years':f"{row['review_year']}/{row['outlook_year']}",
              'review_due':row['review_due_date'] or 'noch nicht festgelegt',
              'outlook_due':row['outlook_due_date'] or 'noch nicht festgelegt',
              'sender_email':sender_email,
              'introduction':'Im Anhang erhältst du die personalisierten Word-Vorlagen für deine Mitarbeitenden als ZIP. Entpacke die Dateien und bearbeite sie in Word.'}
    default_body = '''Guten Tag {manager_name}

{introduction}

Rückblick: {review_due}
Ausblick: {outlook_due}

Speichere die Dateien auf deinem persönlichen Geschäftsgerät. Sende nach dem Gespräch nur die fertig ausgefüllten und gemäss Formular unterzeichneten PDFs S/MIME-verschlüsselt an {sender_email}. Die Word-Dateien bleiben bei dir. Beachte die Unterschriftshinweise im jeweiligen Formular.

Bei einer erneut zugestellten Vorlage übertrage bereits erfasste Angaben bei Bedarf in die neue Datei. Die neue Vorlage ersetzt deinen lokal bearbeiteten Stand nicht automatisch.

Freundliche Grüsse
Human Resources'''
    try:
        subject = (subject_template.strip() or 'Mitarbeitenden-Dialog {years}: Deine Word-Vorlagen').format_map(values)
        body = (body_template.strip() or default_body).format_map(values)
    except (ValueError,KeyError,IndexError,AttributeError) as exc:
        raise ValueError(f'Ungültiger Platzhalter im Word-E-Mailtext: {exc}') from exc
    return subject, ''.join('<p>'+html.escape(p).replace('\n','<br>')+'</p>' for p in body.replace('\r\n','\n').split('\n\n') if p.strip())


def _dispatch_word_packages(connection, *, cycle_id, package_ids, template_paths, sender_email,
                           delivery_mode='draft', subject_template='', body_template='', retry_confirmed=False, adapter=None):
    if delivery_mode not in ('draft','send'):
        raise ValueError('Ungültige Versandart.')
    if not sender_email or '@' not in sender_email or any(c.isspace() for c in sender_email):
        raise ValueError('Bitte die HR-Absenderadresse in der lokalen Konfiguration hinterlegen.')
    selected = set(package_ids)
    if not selected:
        raise ValueError('Bitte mindestens eine Word-Ausgabe auswählen.')
    candidates = {row['id']:row for row in word_dispatch_candidates(connection,cycle_id=cycle_id,template_paths=template_paths)}
    # Gesamte Auswahl vor dem ersten Outlook-Aufruf prüfen.
    for package_id in selected:
        row = candidates.get(package_id)
        if not row or not row['ready']:
            raise ValueError((row or {}).get('readiness_error') or 'Die Auswahl enthält eine abgelöste oder bereits bearbeitete Word-Ausgabe.')
        if row['delivery_status']=='failed' and not retry_confirmed:
            raise ValueError('Bitte vor einem erneuten Versuch in Outlook prüfen, ob bereits eine Nachricht angelegt oder versendet wurde, und die Wiederholung bestätigen.')
        row['subject'],row['body_html'] = word_message(row,sender_email=sender_email,subject_template=subject_template,body_template=body_template)
    outlook = adapter or OutlookDraftAdapter()
    result = {'created':0,'sent':0,'failed':0,'errors':[]}
    for package_id in sorted(selected):
        row = candidates[package_id]
        timestamp = _stamp()
        # Ein zweiter Browser darf dieselbe Ausgabe nicht parallel zustellen.
        try:
            connection.execute('BEGIN IMMEDIATE')
            latest = connection.execute('SELECT MAX(id) FROM word_dispatch_packages WHERE cycle_id=? AND manager_pn=?',(cycle_id,row['manager_pn'])).fetchone()[0]
            existing = connection.execute('SELECT status FROM word_mail_deliveries WHERE package_id=?',(package_id,)).fetchone()
            if latest!=package_id or (existing and existing['status']!='failed'):
                raise ValueError('Die Word-Ausgabe wurde inzwischen abgelöst oder bereits für Outlook übernommen.')
            if _hash(row['stored_path'])!=row['sha256'] or source_fingerprint(connection,cycle_id=cycle_id,manager_pn=row['manager_pn'],template_paths=template_paths)!=row['source_fingerprint']:
                raise ValueError('Die Word-Ausgabe ist nicht mehr aktuell. Bitte neu erzeugen.')
            connection.execute('''INSERT INTO word_mail_deliveries(package_id,sender_email,recipient_email,subject,body_html,status,created_at,updated_at)
                VALUES (?,?,?,?,?,'processing',?,?) ON CONFLICT(package_id) DO UPDATE SET
                sender_email=excluded.sender_email,recipient_email=excluded.recipient_email,subject=excluded.subject,body_html=excluded.body_html,status='processing',error_message='',updated_at=excluded.updated_at''',
                (package_id,sender_email,row['recipient_email'],row['subject'],row['body_html'],timestamp,timestamp))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        try:
            method = outlook.send_encrypted if delivery_mode=='send' else outlook.create_encrypted_draft
            response = method(sender_email=sender_email,recipient_email=row['recipient_email'],subject=row['subject'],body_html=row['body_html'],attachments=[Path(row['stored_path'])])
            if not response.encryption_flag_verified:
                raise ValueError('Outlook hat die Verschlüsselungsmarkierung nicht bestätigt. Bitte Nachricht in Outlook prüfen.')
        except Exception as exc:
            connection.execute("UPDATE word_mail_deliveries SET status='failed',encryption_flag_verified=0,error_message=?,updated_at=? WHERE package_id=?", (str(exc),_stamp(),package_id))
            result['failed'] += 1
            result['errors'].append(f"{row['manager_name']}: {exc}")
        else:
            connection.execute('''UPDATE word_mail_deliveries SET status=?,encryption_flag_verified=1,outlook_entry_id=?,error_message='',updated_at=? WHERE package_id=?''', ('sent_confirmed' if delivery_mode=='send' else 'draft_created',response.entry_id,_stamp(),package_id))
            result['sent' if delivery_mode=='send' else 'created'] += 1
        connection.commit()
    return result


def confirm_word_draft_sent(connection, package_id):
    with connection:
        cursor = connection.execute("UPDATE word_mail_deliveries SET status='sent_confirmed',encryption_flag_verified=1,updated_at=? WHERE package_id=? AND status IN ('draft_created','failed')", (_stamp(),package_id))
        if cursor.rowcount!=1:
            raise ValueError('Für diese Ausgabe gibt es keinen offenen oder zu klärenden Outlook-Vorgang.')


def discard_word_draft(connection, package_id):
    with connection:
        cursor = connection.execute("UPDATE word_mail_deliveries SET status='cancelled',updated_at=? WHERE package_id=? AND status IN ('draft_created','failed')", (_stamp(),package_id))
        if cursor.rowcount!=1:
            raise ValueError('Nur ein offener Entwurf oder fehlgeschlagener Outlook-Vorgang kann als verworfen markiert werden.')


def dispatch_word_packages(connection, *, cycle_id, package_ids, **kwargs):
    from contextlib import ExitStack
    from .outlook_lock import package_lock
    with ExitStack() as stack:
        for package_id in sorted(set(package_ids)):
            row=connection.execute('SELECT stored_path FROM word_dispatch_packages WHERE id=? AND cycle_id=?',(package_id,cycle_id)).fetchone()
            if not row:raise ValueError('Die Word-Ausgabe gehört nicht zu diesem Durchlauf.')
            stack.enter_context(package_lock(row['stored_path']))
        return _dispatch_word_packages(connection,cycle_id=cycle_id,package_ids=package_ids,**kwargs)


def resolve_interrupted_delivery(connection, package_id, *, outcome, reason):
    from .outlook_lock import package_lock
    if outcome not in ('sent_confirmed','cancelled') or len(reason.strip())<10:
        raise ValueError('Bitte Ergebnis der Outlook-Prüfung wählen und mit mindestens 10 Zeichen begründen.')
    row=connection.execute('SELECT stored_path FROM word_dispatch_packages WHERE id=?',(package_id,)).fetchone()
    if not row:raise ValueError('Word-Ausgabe nicht gefunden.')
    with package_lock(row['stored_path']):
        with connection:
            cursor=connection.execute("UPDATE word_mail_deliveries SET status=?,encryption_flag_verified=?,error_message=?,updated_at=? WHERE package_id=? AND status='processing'",(outcome,int(outcome=='sent_confirmed'),'Manuell geklärt: '+reason,_stamp(),package_id))
            if cursor.rowcount!=1:raise ValueError('Der Vorgang ist nicht mehr als unterbrochen offen. Bitte Ansicht aktualisieren.')
