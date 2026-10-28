"""Version-bound data validation, signature evidence and recoverable handoff."""
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import uuid

from .outlook_lock import serialized_goal_delivery


LABELS = {'missing_scan':'Unterschriebener Scan fehlt','pending':'Unterschriftenprüfung offen',
          'missing':'Unterschrift fehlt','requested':'Nachgefordert',
          'confirmed':'Unterschriften vorhanden','legacy_confirmed':'Unterschriftenprüfung aus Altbestand',
          'not_required':'Keine besondere Unterschriftenprüfung erforderlich'}
ACTION_LABELS={'data_validated':'Angaben übernommen','scan_received':'Scan zugeordnet','scan_duplicate':'Identischen Scan verknüpft',
    'confirmed':'Beide Unterschriften bestätigt','missing':'Fehlende Unterschrift erfasst','requested':'Nachforderung dokumentiert',
    'later_signature_requirement':'Nachträgliche Prüfpflicht erkannt','handoff_started':'Bereitstellung begonnen',
    'handoff_uncertain':'Übergabeausgang unklar','handoff_staged':'Lokal für Dossier bereitgestellt',
    'handoff_not_delivered':'Nicht erfolgte Übergabe geklärt'}


def available(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='hr_return_reviews'").fetchone())


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def encoded(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def checked_file(path,sha):
    path=Path(path)
    if not path.is_file() or digest(path)!=sha:
        raise ValueError('Das gespeicherte Original fehlt oder wurde verändert. Quelle zuerst klären.')
    return path


def signatures_required(db,case_id):
    # Existing assessment codes: D = genügend, E = ungenügend. No inference
    # from missing agreement markers or from a successful OCR operation.
    row=db.execute('SELECT overall_rating_code FROM dialog_cases WHERE case_id=?',(case_id,)).fetchone()
    return bool(row and row[0] in ('D','E'))


def decision(db,document_id,action,reason,user_id=None,details=None):
    row=db.execute('SELECT evidence_id FROM hr_return_reviews WHERE document_id=?',(document_id,)).fetchone()
    db.execute('''INSERT INTO hr_return_decisions(document_id,evidence_id,action,reason,details_json,user_id,created_at)
        VALUES (?,?,?,?,?,?,?)''',(document_id,row[0] if row else None,action,reason,encoded(details or {}),user_id,stamp()))


def register(db,document_id,*,source_role='digital',user_id=None,reviewed=None):
    """Participates in the caller's data-import transaction; never publishes."""
    if source_role not in ('digital','scan'):raise ValueError('Bitte Datenquelle als digitales PDF oder Scan kennzeichnen.')
    doc=db.execute('SELECT * FROM official_documents WHERE id=?',(document_id,)).fetchone()
    if not doc or doc['variant']=='administrative':return
    db.execute('''INSERT INTO hr_return_reviews(document_id,source_role,validation_origin,validated_at,validated_by,validation_json)
        VALUES (?,?,'manual',?,?,?)''',(document_id,source_role,stamp(),user_id,encoded(reviewed or {})))
    if source_role=='scan':
        evidence=db.execute('''INSERT INTO hr_return_evidence(document_id,original_filename,stored_path,sha256,created_at,created_by)
            VALUES (?,?,?,?,?,?)''',(document_id,doc['original_filename'],doc['stored_path'],doc['sha256'],stamp(),user_id)).lastrowid
        db.execute("UPDATE hr_return_reviews SET evidence_id=?,signature_status='pending' WHERE document_id=?",(evidence,document_id))
    decision(db,document_id,'data_validated','Angaben vollständig am Original geprüft',user_id,{'source_role':source_role,'sha256':doc['sha256']})
    sync_case(db,doc['case_id'])


def sync_case(db,case_id):
    """Preserve an existing external effect when a later review changes duties."""
    if not signatures_required(db,case_id):return
    for row in db.execute('''SELECT d.id,d.handoff_status,r.signature_status,r.external_followup
        FROM official_documents d JOIN hr_return_reviews r ON r.document_id=d.id
        WHERE d.case_id=? AND d.is_current=1 AND d.document_kind IN ('review','outlook')''',(case_id,)):
        if row['handoff_status']=='staged' and row['signature_status'] not in ('confirmed','legacy_confirmed') and not row['external_followup']:
            db.execute("UPDATE hr_return_reviews SET external_followup='open',revision=revision+1 WHERE document_id=?",(row['id'],))
            decision(db,row['id'],'later_signature_requirement','Nachträgliche Prüfpflicht bei bereits bereitgestelltem Dokument; externe Wirkung separat klären')


def view(db,document_id,*,include_history=True):
    row=db.execute('''SELECT d.*,r.source_role,r.validation_origin,r.validated_at,r.validated_by,r.validation_json,
        r.evidence_id,r.signature_status,r.external_followup,r.revision,e.first_name,e.last_name,c.employment_assignment
        FROM official_documents d JOIN hr_return_reviews r ON r.document_id=d.id
        JOIN employees e ON e.pn=d.employee_pn JOIN dialog_cases c ON c.case_id=d.case_id WHERE d.id=?''',(document_id,)).fetchone()
    if not row:raise ValueError('Der übernommene Rücklauf wurde nicht gefunden.')
    result=dict(row)
    result['required']=signatures_required(db,row['case_id'])
    result['signature_state']=row['signature_status'] if result['required'] else 'not_required'
    result['signature_label']=LABELS[result['signature_state']]
    evidence=db.execute('SELECT * FROM hr_return_evidence WHERE id=?',(row['evidence_id'],)).fetchone()
    result['evidence']=dict(evidence) if evidence else None
    handoff=db.execute('SELECT * FROM hr_return_handoffs WHERE document_id=?',(document_id,)).fetchone()
    result['handoff']=dict(handoff) if handoff else None
    derived=db.execute('SELECT * FROM hr_return_status WHERE document_id=?',(document_id,)).fetchone()
    for key in ('required','signature_ready','locally_staged','external_open','complete'):
        result[key]=bool(derived[key])
    from .part_responsibilities import resolve
    result['part']=resolve(db,row['case_id'],row['document_kind'])
    basis={key:result[key] for key in ('sha256','revision','evidence_id','signature_state','external_open','is_current')}
    basis['part']=result['part'];basis['evidence_sha256']=evidence['sha256'] if evidence else None
    result['token']=hashlib.sha256(encoded(basis).encode()).hexdigest()
    result['history']=([dict(r) for r in db.execute('''SELECT x.*,u.email AS actor FROM hr_return_decisions x
        LEFT JOIN app_users u ON u.id=x.user_id WHERE document_id=? ORDER BY x.id''',(document_id,))] if include_history else [])
    for entry in result['history']:entry['action_label']=ACTION_LABELS.get(entry['action'],entry['action'])
    return result


def next_action(item):
    if item['complete']:return 'Für Dossier bereitgestellt'
    if item['external_open']:return 'Externe Ablage und zusätzlichen Nachweis klären'
    if item['handoff'] and item['handoff']['status'] in ('processing','uncertain'):return 'Unklaren Übergabeausgang klären'
    if not item['signature_ready']:return item['signature_label']
    return 'Für Dossier bereitstellen'


def tasks(db):
    result=[]
    for row in db.execute('''SELECT d.id FROM official_documents d JOIN hr_return_reviews r ON r.document_id=d.id
        WHERE d.is_current=1 ORDER BY d.received_at,d.id'''):
        item=view(db,row['id'],include_history=False)
        if item['complete']:continue
        title=next_action(item)
        result.append(dict(priority='hoch',priority_rank=2,kind='Rücklauf',title=title,
            subject=item['first_name']+' '+item['last_name'],context=('Rückblick' if item['document_kind']=='review' else 'Ausblick')+' · '+item['part']['manager_pn'],
            date=item['received_at'],target='return_review',document_id=item['id'],case_id=item['case_id'],cycle_id=item['cycle_id'],
            manager_pn=item['part']['manager_pn'],waiting=item['signature_state']=='requested'))
    return result


def fresh(db,document_id,revision,token):
    row=view(db,document_id)
    if not row['is_current'] or row['revision']!=int(revision) or row['token']!=token:
        raise ValueError('Der Rücklauf oder seine Zuordnung hat sich geändert. Bitte neu öffnen und prüfen.')
    checked_file(row['stored_path'],row['sha256'])
    if row['evidence']:checked_file(row['evidence']['stored_path'],row['evidence']['sha256'])
    return row


@serialized_goal_delivery
def attach_evidence(db,document_id,*,path,filename,directory,revision,token,user_id=None,import_id=None):
    """Store a scan without claiming a signature check or importing data twice."""
    from .documents import inspect_pdf
    source=Path(path);sha=digest(source);inspect_pdf(source)
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    stored=directory/(sha+'-'+uuid.uuid4().hex+'.pdf')
    db.execute('BEGIN IMMEDIATE')
    try:
        row=fresh(db,document_id,revision,token)
        existing=db.execute('SELECT * FROM hr_return_evidence WHERE document_id=? AND sha256=?',(document_id,sha)).fetchone()
        if import_id:
            incoming=db.execute("SELECT * FROM word_pdf_imports WHERE id=? AND status='pending'",(import_id,)).fetchone()
            if not incoming or incoming['sha256']!=sha:raise ValueError('Dieser Eingang ist nicht mehr unverändert offen.')
            if db.execute('SELECT 1 FROM hr_goal_origins WHERE pdf_import_id=?',(import_id,)).fetchone():raise ValueError('Dieser Eingang gehört zur Zielprüfung.')
            if db.execute('SELECT 1 FROM workflow_pdf_state WHERE import_id=? AND dismissed=1',(import_id,)).fetchone():raise ValueError('Den zurückgestellten Eingang zuerst wieder öffnen.')
            if json.loads(incoming['parsed_json']).get('data',{}).get('document_kind')=='feedback':raise ValueError('Ein Feedback ist kein Unterschriftennachweis für einen MD-Teil.')
        if existing and row['evidence_id']==existing['id']:
            if import_id:
                db.execute("UPDATE word_pdf_imports SET status='imported',case_id=?,official_document_id=?,review_note='Identischer bereits zugeordneter Scan; vorhandener Prüfstand unverändert',reviewed_by=?,reviewed_at=? WHERE id=?",
                    (row['case_id'],document_id,user_id,stamp(),import_id))
                decision(db,document_id,'scan_duplicate','Identischen Eingang mit bestehendem Scan verknüpft',user_id,{'import_id':import_id,'sha256':sha})
                db.commit()
            else:db.rollback()
            return existing['id']
        if existing:evidence_id=existing['id']
        else:
            shutil.copyfile(source,stored)
            checked_file(stored,sha)
            evidence_id=db.execute('''INSERT INTO hr_return_evidence(document_id,original_filename,stored_path,sha256,import_id,created_at,created_by)
                VALUES (?,?,?,?,?,?,?)''',(document_id,Path(filename).name,str(stored),sha,import_id,stamp(),user_id)).lastrowid
        db.execute("UPDATE hr_return_reviews SET evidence_id=?,signature_status='pending',revision=revision+1 WHERE document_id=?",(evidence_id,document_id))
        if row['locally_staged']:
            db.execute("UPDATE hr_return_reviews SET external_followup='open' WHERE document_id=?",(document_id,))
        if import_id:
            db.execute("UPDATE word_pdf_imports SET status='imported',case_id=?,official_document_id=?,review_note='Als Unterschriftennachweis zugeordnet; Sichtprüfung noch offen',reviewed_by=?,reviewed_at=? WHERE id=?",
                       (row['case_id'],document_id,user_id,stamp(),import_id))
        decision(db,document_id,'scan_received','Scan zugeordnet; keine Fachdaten erneut übernommen',user_id,{'sha256':sha,'data_sha256':row['sha256']})
        refresh(db,row['case_id']);db.commit();return evidence_id
    except Exception:
        db.rollback();stored.unlink(missing_ok=True);raise


@serialized_goal_delivery
def inspect_signatures(db,document_id,*,revision,token,action,reason='',employee_signed=False,manager_signed=False,content_matches=False,requested_at='',recipient='',user_id=None):
    db.execute('BEGIN IMMEDIATE')
    try:
        row=fresh(db,document_id,revision,token)
        sync_case(db,row['case_id'])
        if not row['required']:raise ValueError('Dieser Rücklauf hat keine besondere Unterschriftenprüfpflicht.')
        details={'data_sha256':row['sha256'],'evidence_sha256':row['evidence']['sha256'] if row['evidence'] else None}
        if action=='confirmed':
            if not row['evidence'] or not all((employee_signed,manager_signed,content_matches)):
                raise ValueError('Bitte den konkreten Scan öffnen und beide Unterschriften sowie die vollständige inhaltliche Übereinstimmung bestätigen.')
            details.update(employee_signed=True,manager_signed=True,content_matches=True)
        elif action=='missing':
            if not row['evidence'] or len(reason.strip())<10:raise ValueError('Bitte die fehlende Unterschrift am vorhandenen Scan konkret beschreiben.')
        elif action=='requested':
            try:when=date.fromisoformat(requested_at)
            except (ValueError,TypeError):raise ValueError('Bitte das Datum der tatsächlich erfolgten Nachforderung angeben.')
            if when>date.today() or not recipient.strip() or len(reason.strip())<10:
                raise ValueError('Bitte tatsächliches Anforderungsdatum, Adressat und konkreten fehlenden Nachweis erfassen. Ein Entwurf genügt nicht.')
            details.update(requested_at=requested_at,recipient=recipient.strip(),responsible_manager=row['part']['manager_pn'])
        else:raise ValueError('Unbekannte Prüfentscheidung.')
        db.execute('UPDATE hr_return_reviews SET signature_status=?,revision=revision+1 WHERE document_id=?',(action,document_id))
        decision(db,document_id,action,reason.strip(),user_id,details)
        refresh(db,row['case_id']);db.commit()
    except Exception:db.rollback();raise


def refresh(db,case_id):
    from .documents import refresh_case_status
    refresh_case_status(db,case_id)


def refresh_case(db,case_id):
    """Return None only when there are no new-model documents in this case."""
    from .documents import refresh_dialog_event_status
    rows=db.execute('''SELECT o.id,o.document_kind,o.required FROM document_obligations o
        JOIN dialog_events e ON e.id=o.dialog_event_id WHERE e.legacy_case_id=?''',(case_id,)).fetchall()
    has_new=db.execute('''SELECT 1 FROM hr_return_reviews r JOIN official_documents d ON d.id=r.document_id
        WHERE d.case_id=? AND d.is_current=1''',(case_id,)).fetchone()
    if not has_new:return None
    complete=True;all_waived=True;count=0
    for part in rows:
        if not part['required'] or part['document_kind'] not in ('review','outlook'):continue
        count+=1
        docs=db.execute('SELECT * FROM official_documents WHERE case_id=? AND document_kind=? AND is_current=1',(case_id,part['document_kind'])).fetchall()
        admin=next((d for d in docs if d['variant']=='administrative'),None)
        data=next((d for d in docs if d['variant']=='digital'),None)
        all_waived=all_waived and bool(admin)
        if admin:status='complete'
        elif data:
            state=view(db,data['id']);status='complete' if state['complete'] else ('scan_pending' if state['required'] else 'received')
        else:status='open'
        complete=complete and status=='complete'
        db.execute('UPDATE document_obligations SET status=?,updated_at=? WHERE id=?',(status,stamp(),part['id']))
    status='kein_md' if count and all_waived else ('vollstaendig' if count and complete else 'in_bearbeitung')
    db.execute('UPDATE dialog_cases SET status=?,updated_at=? WHERE case_id=?',(status,stamp(),case_id))
    refresh_dialog_event_status(db,case_id)
    return status


@serialized_goal_delivery
def handoff(db,document_id,*,directory,revision,token,user_id=None):
    from .documents import _case_row,_handoff_filename
    from .dossier_files import publish_copy
    db.execute('BEGIN IMMEDIATE')
    try:
        row=fresh(db,document_id,revision,token)
        sync_case(db,row['case_id'])
        if row['external_open']:raise ValueError('Bereits erfolgte Bereitstellung: externe Korrektur separat klären. Keine automatische weitere Ablage.')
        if not row['signature_ready']:raise ValueError(row['signature_label']+'. Noch keine Dossierbereitstellung.')
        if row['locally_staged']:db.rollback();return row
        if row['handoff'] and row['handoff']['status'] in ('processing','uncertain'):
            raise ValueError('Die bisherige Übergabe hat einen unklaren Ausgang. Erst mit der Dossierverarbeitung klären; nicht nochmals kopieren.')
        source=row['evidence'] if row['required'] else row
        checked_file(source['stored_path'],source['sha256'])
        case={**dict(_case_row(db,row['case_id'])),'_document_manager':row['part']['manager_pn']}
        filename=_handoff_filename(case,row['document_kind'],scan=bool(row['required'] or row['source_role']=='scan'))
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
        target=directory/filename
        if db.execute('SELECT 1 FROM hr_return_handoffs WHERE destination=? AND document_id<>?',(str(target),document_id)).fetchone() or db.execute("SELECT 1 FROM official_documents WHERE handoff_filename=? AND id<>? AND handoff_status='staged'",(filename,document_id)).fetchone():
            raise ValueError('Dieser Ablagename gehört bereits zu einem anderen Rücklauf. Die externe Dateizuordnung zuerst klären; vorhandene Wirkungen bleiben erhalten.')
        db.execute('''INSERT INTO hr_return_handoffs(document_id,evidence_id,source_sha256,destination,status,started_at)
            VALUES (?,?,?,?,'processing',?) ON CONFLICT(document_id) DO UPDATE SET evidence_id=excluded.evidence_id,
            source_sha256=excluded.source_sha256,destination=excluded.destination,status='processing',error_message='',started_at=excluded.started_at''',
            (document_id,source.get('id') if row['required'] else None,source['sha256'],str(target),stamp()))
        decision(db,document_id,'handoff_started','Lokale Bereitstellung begonnen',user_id,{'sha256':source['sha256'],'destination':str(target)})
        db.commit()
    except Exception:db.rollback();raise
    try:
        publish_copy(Path(source['stored_path']),target)
        checked_file(source['stored_path'],source['sha256'])
    except Exception as exc:
        with db:
            db.execute("UPDATE hr_return_handoffs SET status='uncertain',error_message=? WHERE document_id=?",(str(exc),document_id))
            decision(db,document_id,'handoff_uncertain','Übergabeausgang prüfen; Unterschriftenprüfung bleibt erhalten',user_id,{'error':str(exc)})
        raise
    with db:
        db.execute("UPDATE hr_return_handoffs SET status='staged',completed_at=? WHERE document_id=?",(stamp(),document_id))
        # Compatibility fields describe local delivery only; do not fabricate a signature check.
        db.execute("UPDATE official_documents SET handoff_status='staged',handoff_filename=?,handoff_at=? WHERE id=?",(filename,stamp(),document_id))
        db.execute('UPDATE hr_return_reviews SET revision=revision+1 WHERE document_id=?',(document_id,))
        decision(db,document_id,'handoff_staged','Für Dossier bereitgestellt; externe Verarbeitung nicht bestätigt',user_id,{'sha256':source['sha256']})
        refresh(db,row['case_id'])
    return view(db,document_id)


@serialized_goal_delivery
def clarify_failed_handoff(db,document_id,*,revision,token,reason,not_delivered,user_id=None):
    db.execute('BEGIN IMMEDIATE')
    try:
        row=fresh(db,document_id,revision,token)
        if not row['handoff'] or row['handoff']['status'] not in ('processing','uncertain'):raise ValueError('Keine unklare Übergabe vorhanden.')
        if not not_delivered or len(reason.strip())<10:raise ValueError('Erst nach Prüfung der Ablage und Dossierverarbeitung bestätigen, dass keine Übergabe erfolgte; Klärung begründen.')
        db.execute("UPDATE hr_return_handoffs SET status='failed' WHERE document_id=?",(document_id,))
        db.execute('UPDATE hr_return_reviews SET revision=revision+1 WHERE document_id=?',(document_id,))
        decision(db,document_id,'handoff_not_delivered',reason,user_id)
        db.commit()
    except Exception:db.rollback();raise
