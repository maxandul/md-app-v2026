"""Word-Sammelerzeugung und separat protokollierter S/MIME-Versand."""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import sqlite3
import uuid
from datetime import datetime, date
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from webapp.adapters.outlook import OutlookDraftAdapter
from .packages import _secondary_employment_text
from .word_packages import create_word_package, prior_goals, preparation_templates


def _stamp():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_snapshot(connection, *, cycle_id, manager_pn, template_paths):
    cycle = connection.execute('SELECT review_year,outlook_year,sap_import_id FROM cycles WHERE id=?', (cycle_id,)).fetchone()
    manager = connection.execute('SELECT pn,first_name,last_name,email FROM employees WHERE pn=?', (manager_pn,)).fetchone()
    if not cycle or not manager:
        raise ValueError('Durchlauf oder Stammdaten der Führungskraft fehlen.')
    cases = connection.execute('''SELECT dc.case_id,dc.employee_pn,dc.employment_assignment,
        dc.official_scope,dc.suggested_scope,dc.period_start,dc.period_end,
        e.first_name,e.last_name,e.position,COALESCE(fo.org_unit,e.org_unit) AS org_unit,e.entry_date,e.exit_date,e.probation_end,e.secondary_employment,
        COALESCE(de.event_type,'annual') AS event_type
        FROM dialog_cases dc JOIN employees e ON e.pn=dc.employee_pn
        LEFT JOIN dialog_events de ON de.legacy_case_id=dc.case_id
        LEFT JOIN dialog_form_org_units fo ON fo.dialog_event_id=de.id
        WHERE dc.cycle_id=? AND dc.manager_pn=? AND dc.active=1 ORDER BY dc.case_id''', (cycle_id,manager_pn)).fetchall()
    from webapp.migrations import available
    from .part_responsibilities import case_rows,case_parts,assigned_kinds
    modern=available(connection)
    if modern:cases=case_rows(connection,cycle_id,manager_pn)
    snapshot = {'package_format': 3 if modern else 2, 'cycle':dict(cycle),'manager':dict(manager),'cases':[],'templates':{}}
    needed = set()
    for row in cases:
        item = dict(row)
        if modern:item={k:item[k] for k in ('case_id','employee_pn','employment_assignment','official_scope','suggested_scope','period_start','period_end','first_name','last_name','position','org_unit','entry_date','exit_date','probation_end','secondary_employment','event_type')}
        scope = row['official_scope'] or row['suggested_scope']
        if modern and scope!='none':
            kinds=assigned_kinds(connection,row['case_id'],manager_pn)
            scope='full' if len(kinds)==2 else ('outlook_only' if kinds==['outlook'] else 'review_only' if kinds else 'none')
            item['official_scope']=scope if row['official_scope'] else ''
            item['suggested_scope']=scope
            item['parts']=[{key:p[key] for key in ('kind','manager_pn','recipient_email','form_org_unit','form_org_source','period_start','period_end','responsibility_revision')}
                           for p in case_parts(connection,row['case_id']) if p['manager_pn']==manager_pn and p['required']]
            review_part=next((p for p in item['parts'] if p['kind']=='review'),None)
            if review_part:item['period_end']=review_part['period_end']
        if scope in ('full','review_only'):
            needed.add('probation' if row['event_type']=='probation_review' else 'review')
            if row['event_type']!='probation_review':
                year = int(item['period_end'][:4]) if item['period_end'] else cycle['review_year']
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
    if modern:
        from .word_packages import feedback_cases
        snapshot['feedback_case_ids']=feedback_cases(connection,cycle,manager_pn,cases)
    for kind,path in preparation_templates(template_paths).items():
        if modern and kind=='feedback' and not snapshot['feedback_case_ids']:continue
        if not path.is_file():
            raise ValueError(f'Beilage «{kind}» fehlt. Vorlagenkonfiguration prüfen.')
        snapshot['templates'][kind] = _hash(path)
    numbers = [manager_pn, *(row['employee_pn'] for row in cases)]
    conflicts = connection.execute(f"SELECT COUNT(*) FROM sap_import_issues WHERE sap_import_id=? AND status='open' AND severity='blocking' AND person_number IN ({','.join('?' for _ in numbers)})", (cycle['sap_import_id'],*numbers)).fetchone()[0]
    if conflicts:
        raise ValueError('Offene SAP-Zuordnungskonflikte müssen zuerst geklärt werden.')
    return snapshot


def source_fingerprint(connection, *, cycle_id, manager_pn, template_paths):
    snapshot=source_snapshot(connection,cycle_id=cycle_id,manager_pn=manager_pn,template_paths=template_paths)
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
                from webapp.migrations import available
                if available(connection):
                    from .part_responsibilities import case_rows
                    scopes=[{'scope':r['official_scope'] or r['suggested_scope']} for r in case_rows(connection,cycle_id,pn)]
                if not scopes:
                    raise ValueError(f'Für PN {pn} sind keine aktiven Fälle vorhanden.')
                if all(row['scope']=='none' for row in scopes):
                    skipped.append(pn)
                    continue
                fingerprint = source_fingerprint(connection,cycle_id=cycle_id,manager_pn=pn,template_paths=template_paths)
                path, manifest = create_word_package(connection,cycle_id=cycle_id,manager_pn=pn,template_paths=template_paths,output_dir=directory)
                if fingerprint != source_fingerprint(connection,cycle_id=cycle_id,manager_pn=pn,template_paths=template_paths):
                    raise ValueError('Die Quelldaten wurden während der Erzeugung geändert. Bitte erneut erzeugen.')
                manifest['source_snapshot']=source_snapshot(connection,cycle_id=cycle_id,manager_pn=pn,template_paths=template_paths)
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
        e.first_name AS manager_first_name, e.salutation AS manager_salutation,
        c.review_year,c.outlook_year,c.review_due_date,c.outlook_due_date,
        d.status AS delivery_status,d.error_message,d.updated_at AS delivery_updated_at
        FROM word_dispatch_packages p JOIN cycles c ON c.id=p.cycle_id
        LEFT JOIN employees e ON e.pn=p.manager_pn
        LEFT JOIN word_mail_deliveries d ON d.package_id=p.id
        WHERE p.cycle_id=? AND p.id=(SELECT MAX(p2.id) FROM word_dispatch_packages p2 WHERE p2.cycle_id=p.cycle_id AND p2.manager_pn=p.manager_pn AND p2.discarded_at='')
        ORDER BY manager_name,p.manager_pn''', (cycle_id,)).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        last_sent = connection.execute("""SELECT p.id,d.updated_at FROM word_dispatch_packages p
            JOIN word_mail_deliveries d ON d.package_id=p.id
            WHERE p.cycle_id=? AND p.manager_pn=? AND d.status='sent_confirmed'
            ORDER BY d.updated_at DESC,p.id DESC LIMIT 1""", (cycle_id,row['manager_pn'])).fetchone()
        item['last_sent_at'] = last_sent['updated_at'] if last_sent else ''
        item['last_sent_package_id'] = last_sent['id'] if last_sent else None
        item['can_discard'] = row['delivery_status'] in (None, 'cancelled')
        item['filename'] = Path(row['stored_path']).name
        manifest = json.loads(row['manifest_json'])
        item['goal_warnings'] = manifest.get('goal_warnings', [])
        item['performance_goal_count'] = sum(d.get('performance_goals', 0) for d in manifest['documents'])
        item['development_goal_count'] = sum(d.get('development_goals', 0) for d in manifest['documents'])
        item['document_count'] = len(manifest['documents'])
        item['attachment_count'] = len(json.loads(row['manifest_json']).get('attachments',[]))
        item['source_changes']=[]
        item['changes_resolved']=False
        try:
            if not Path(row['stored_path']).is_file() or _hash(row['stored_path'])!=row['sha256']:
                raise ValueError('Die Versanddatei fehlt oder wurde verändert. Bitte neu erzeugen.')
            if source_fingerprint(connection,cycle_id=cycle_id,manager_pn=row['manager_pn'],template_paths=template_paths)!=row['source_fingerprint']:
                from .dispatch_changes import changes_for_package
                current=source_snapshot(connection,cycle_id=cycle_id,manager_pn=row['manager_pn'],template_paths=template_paths)
                item['source_changes']=changes_for_package(row,manifest,current)
                for change in item['source_changes']:
                    decision=connection.execute('SELECT * FROM word_change_decisions WHERE package_id=? AND case_id=? AND source_signature=? ORDER BY id DESC LIMIT 1',(row['id'],change['case_id'],change['signature'])).fetchone()
                    change['decision']=dict(decision) if decision else None
                item['changes_resolved']=bool(item['source_changes']) and all(c['decision'] for c in item['source_changes'])
                if row['delivery_status']=='sent_confirmed':
                    if not item['changes_resolved']:
                        raise ValueError('Änderungen seit dieser versendeten Ausgabe: unten je Person prüfen und Vorgehen dokumentieren. Ein neuer Gesamtversand ist nicht automatisch nötig.')
                else:
                    raise ValueError('Die Grundlagen haben sich geändert; diese noch nicht versendete Ausgabe ist veraltet. Vor einem Versand neu erzeugen; Einzelkorrekturen bereits versendeter Pakete kannst du unten dokumentieren.')
            if not row['recipient_email']:
                raise ValueError('Geschäftliche E-Mail-Adresse fehlt.')
            item['readiness_error'] = ''
        except (ValueError,OSError) as exc:
            item['readiness_error'] = str(exc)
        item['ready'] = not item['readiness_error'] and row['delivery_status'] not in ('processing','draft_created','sent_confirmed','cancelled')
        result.append(item)
    return result


DEFAULT_WORD_SUBJECT = 'MD-Unterlagen Durchlauf {years}'
DEFAULT_WORD_BODY = """{greeting}

Der jährliche Mitarbeitenden-Dialog steht an. Im angehängten ZIP findest du:

- Ein Formular MD Feedback und MD Reflexion zum Verteilen an deine Mitarbeitenden.
- Ein Formular MD Rückblick pro Mitarbeiter/in.
- Ein Formular MD Rückblick Probezeit für Mitarbeitende, die in der Zeit von Oktober bis Januar ihre Probezeit abschliessen.
- Ein Formular MD Ausblick pro Mitarbeiter/in, es sei denn, sie verlassen die Organisation bis Ende Januar.
- Für Mitarbeitende, die zwischen Juni und September ihre Probezeit abgeschlossen haben, erhältst du nur einen MD Ausblick.

Bitte überlege dir im Rahmen des Ausblicks, ob Mitarbeitende in deinem Team für die Nominierung für das [KNF I](https://ktzuerich.sharepoint.com/sites/zh-personelles/SitePages/KNF-I.aspx) oder [KNF II](https://ktzuerich.sharepoint.com/sites/zh-personelles/SitePages/KNF-II.aspx) (Kadernachwuchsförderung) für {outlook_year} in Frage kommen. Halte ein allfälliges Interesse im Ausblick unter Punkt 3 schriftlich fest.

Für den Rückversand als PDF an [{sender_email}](mailto:{sender_email}) gelten folgende Vorgaben:

**Bis zum {review_due}:**

- Pro Mitarbeiter/in ein PDF mit dem Feedback an dich. Beschriftung: NameMitarbeiter/in_Feedback_an_DeinNachname_DeinVorname_DeinePersonalnummer.
- Pro Mitarbeiter/in ein ausgefüllter Rückblick als PDF mit Unterschrift. Beschriftung: Rückblick_{review_year}_NachnameMA_VornameMA_PersonalnummerMA.

**Bis zum {outlook_due}:**

- Pro Mitarbeiter/in ein ausgefüllter Ausblick als PDF mit Unterschrift. Beschriftung: Ausblick_{outlook_year}_NachnameMA_VornameMA_PersonalnummerMA.

**Hinweise:**

- Speichere das ZIP, entpacke es (Rechtsklick > Alle extrahieren...) und nutze die Wordvorlagen. Beim Speichern als PDF kannst du den vorgegebenen Dateinamen übernehmen. Sende nur die PDFs zurück ans HR.
- Die Dokumente im Anhang sind automatisch generiert. Mitarbeitende in der Probezeit, kurz vor dem Austritt oder mit vakanten Vorgesetzten sind weitgehend berücksichtigt worden. Dennoch können nicht alle Eventualitäten vollständig vorweggenommen werden. Hier findest du Infos zu den [Spezialfällen](https://ktzuerich.sharepoint.com/sites/vd/SitePages/Mitarbeitenden-Dialog-%28MD%29.aspx#spezialf%C3%A4lle).
- Sofern wir im letzten Durchlauf den Ausblick als Word-Datei korrekt erhalten haben, konnten wir die Ziele in den aktuellen Rückblick übernehmen. Falls bei dir keine Ziele übernommen wurden, kannst du uns die Ausblicke nachreichen und wir senden dir die ergänzten Rückblicke.
- Gemäss der [Allgemeinen Nutzungsrichtlinie M365](https://ktzuerich.sharepoint.com/:b:/r/sites/gd/Freigegebene%20Dokumente/Informationssicherheit/Allgemeine-Nutzungsrichtlinie-Microsoft365-Stand-1.%20Februar%202023.pdf?d=we6c7c63a52394d86a99cc39a42edac14&csf=1&web=1&e=S8GSP1) müssen E-Mails mit vertraulichem Inhalt verschlüsselt versendet werden.
- Die administrative Verarbeitung erfolgt maschinell. Deshalb ist es wichtig, dass die PDFs die Personalnummern am Ende der Beschriftung tragen.
- Standardmässig genügt die einfache elektronische Unterschrift auf dem PDF, wie sie in Adobe Acrobat möglich ist. Bei einer Gesamtbewertung genügend / ungenügend oder wenn Uneinigkeit besteht, müssen beide Parteien die Dokumente handschriftlich unterzeichnen und den Scan beilegen.
- Sämtliche Unterlagen und Informationen zum Mitarbeitenden-Dialog sind auf [ZHub](https://ktzuerich.sharepoint.com/sites/vd/SitePages/Mitarbeitenden-Dialog-%28MD%29.aspx) zu finden.

Bei Fragen steht dir dein/e HR Verantwortliche/r gerne zur Verfügung.

Wir wünschen dir spannende und konstruktive Dialoge!

Herzliche Grüsse
Dein Human Resources & Entwicklung

#### Dies ist eine automatisch generierte E-Mail ####"""


def _mail_html(body):
    # Escape all user input; only supported formatting and safe link schemes become HTML.
    def inline(text):
        text = html.escape(text)
        text = re.sub(r'\[([^\]\n]+)\]\(((?:https?://|mailto:)[^\s<>]+?)\)', r'<a href="\2">\1</a>', text)
        return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    parts = []
    for paragraph in body.replace('\r\n', '\n').split('\n\n'):
        if not paragraph.strip():
            continue
        lines = paragraph.splitlines()
        if all(line.startswith('- ') for line in lines):
            parts.append('<ul>' + ''.join('<li>' + inline(line[2:]) + '</li>' for line in lines) + '</ul>')
        else:
            parts.append('<p>' + inline(paragraph).replace('\n', '<br>') + '</p>')
    return ''.join(parts)


def word_message(row, *, sender_email, subject_template='', body_template=''):
    def due(value):
        if not value:
            return 'noch nicht festgelegt'
        return date.fromisoformat(value).strftime('%d.%m.%Y')
    first_name = (row.get('manager_first_name') or '').strip()
    salutation = (row.get('manager_salutation') or '').strip().casefold()
    greeting = {'frau': 'Liebe', 'herr': 'Lieber'}.get(salutation, 'Hallo') if first_name else 'Hallo'
    if first_name:
        greeting += ' ' + first_name
    values = {'manager_name':row['manager_name'] or row['manager_pn'],
              'manager_first_name':first_name, 'greeting':greeting,
              'years':f"{row['review_year']}/{row['outlook_year']}",
              'review_year':row['review_year'], 'outlook_year':row['outlook_year'],
              'review_due':due(row['review_due_date']),
              'outlook_due':due(row['outlook_due_date']),
              'sender_email':sender_email,
              'introduction':'Im Anhang erhältst du die personalisierten Word-Vorlagen für deine Mitarbeitenden als ZIP.'}
    try:
        subject = (subject_template.strip() or DEFAULT_WORD_SUBJECT).format_map(values)
        body = (body_template.strip() or DEFAULT_WORD_BODY).format_map(values)
        manifest=json.loads(row.get('manifest_json') or '{}')
        if not body_template.strip() and any(d.get('responsibility') for d in manifest.get('documents',[])):
            labels={'review':'Rückblick','outlook':'Ausblick','probation':'Probezeit-Rückblick'}
            entries='\n'.join('- '+labels[d['kind']]+': '+d['filename'] for d in manifest['documents'])
            body=(f"{greeting}\n\nIm Anhang erhältst du die Word-Formulare für die dir zugewiesenen Gesprächsteile:\n{entries}\n\n"
                  f"Frist Rückblick: {values['review_due']}; Frist Ausblick: {values['outlook_due']}. Individuell vereinbarte Fristen bleiben massgeblich.\n\n"
                  f"Bitte speichere und entpacke das ZIP und sende die bearbeiteten PDFs S/MIME-verschlüsselt an {sender_email}. Beachte die Unterschriften- und Rücksendehinweise im jeweiligen Formular.\n\n"
                  "Eine vorübergehende MD-Vertretung ändert die Feedback-Zuordnung nicht. Eine beigefügte Feedbackvorlage gilt für deine regulären Mitarbeitenden, nicht automatisch für vertretene Gesprächsteile.\n\nFreundliche Grüsse\nHR")
    except (ValueError,KeyError,IndexError,AttributeError) as exc:
        raise ValueError(f'Ungültiger Platzhalter im Word-E-Mailtext: {exc}') from exc
    return subject, _mail_html(body)


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
        from .outlook_lock import check_goal_workflow
        documents=json.loads(row['manifest_json'])['documents']
        check_goal_workflow(connection,[d['case_id'] for d in documents],documents=documents,exclude=('package',package_id))
    outlook = adapter or OutlookDraftAdapter()
    result = {'created':0,'sent':0,'failed':0,'errors':[]}
    for package_id in sorted(selected):
        row = candidates[package_id]
        timestamp = _stamp()
        # Ein zweiter Browser darf dieselbe Ausgabe nicht parallel zustellen.
        try:
            connection.execute('BEGIN IMMEDIATE')
            latest = connection.execute("SELECT MAX(id) FROM word_dispatch_packages WHERE cycle_id=? AND manager_pn=? AND discarded_at=''",(cycle_id,row['manager_pn'])).fetchone()[0]
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


def discard_word_package(connection, package_id):
    """Archive an unused output without altering any delivery evidence."""
    from .outlook_lock import package_lock
    row = connection.execute('SELECT * FROM word_dispatch_packages WHERE id=?', (package_id,)).fetchone()
    if not row:
        raise ValueError('Word-Ausgabe nicht gefunden.')
    with package_lock(row['stored_path']):
        try:
            connection.execute('BEGIN IMMEDIATE')
            latest = connection.execute("""SELECT MAX(id) FROM word_dispatch_packages
                WHERE cycle_id=? AND manager_pn=? AND discarded_at=''""", (row['cycle_id'], row['manager_pn'])).fetchone()[0]
            delivery = connection.execute('SELECT status FROM word_mail_deliveries WHERE package_id=?', (package_id,)).fetchone()
            if latest != package_id:
                raise ValueError('Diese Ausgabe ist nicht mehr aktuell. Bitte die Ansicht aktualisieren.')
            if delivery and delivery['status'] != 'cancelled':
                raise ValueError('Diese Ausgabe wurde bereits an Outlook übergeben. Zuerst den Outlook-Vorgang klären; bestätigte Versände bleiben erhalten.')
            connection.execute('UPDATE word_dispatch_packages SET discarded_at=? WHERE id=?', (_stamp(), package_id))
            connection.commit()
        except Exception:
            connection.rollback()
            raise


from .outlook_lock import serialized_goal_delivery


@serialized_goal_delivery
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
