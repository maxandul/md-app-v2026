"""Unchanged resend sources for person corrections and goal bundles."""
import json
import hashlib
import shutil
import uuid
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
from zipfile import ZipFile
from . import redeliveries as regular,word_dispatch,part_changes,goal_delivery,goal_followups
from .part_responsibilities import resolve,stamp
from .outlook_lock import serialized_goal_delivery


def person_snapshot(db,manifest,template_paths):
    from .word_packages import prior_goals,preparation_templates
    from .form_data import _secondary_employment_text
    from .word_packages import check_sap_assignments
    documents=manifest['documents'];case_id=documents[0]['case_id']
    if any(d['case_id']!=case_id for d in documents):raise ValueError('Die Einzelausgabe enthält mehrere Personen. Zuordnung zuerst klären.')
    manager=db.execute('SELECT pn,first_name,last_name,position,org_unit,email FROM employees WHERE pn=?',(manifest['manager_pn'],)).fetchone()
    if not manager:raise ValueError('Die Führungskraft fehlt in den Stammdaten.')
    value={'format':1,'manager':dict(manager),'parts':[],'templates':{}}
    for doc in documents:
        part=resolve(db,doc['case_id'],'review' if doc['kind']=='probation' else doc['kind'])
        check_sap_assignments(db,part['cycle_id'],[part['employee_pn'],part['manager_pn']])
        item={k:part[k] for k in ('case_id','obligation_id','kind','employee_pn','employment_assignment','first_name','last_name','position',
            'manager_pn','recipient_email','form_org_unit','form_org_source','period_start','period_end','responsibility_revision','event_type','active','required')}
        item['secondary']=_secondary_employment_text(db,employee_pn=part['employee_pn'],employment_assignment=part['employment_assignment'],fallback=part['secondary_employment'])
        if doc['kind']=='review':item['goals']=prior_goals(db,employee_pn=part['employee_pn'],assignment=part['employment_assignment'],year=int(part['period_end'][:4]))
        value['parts'].append(item)
        value['templates'][doc['kind']]=word_dispatch._hash(template_paths[doc['kind']])
    for attachment in manifest.get('attachments',[]):value['templates'][attachment['kind']]=word_dispatch._hash(preparation_templates(template_paths)[attachment['kind']])
    return value


def provenance(db,dispatch_id):
    row=db.execute("SELECT details_json FROM hr_goal_events WHERE dispatch_id=? AND action='redelivery_prepared' ORDER BY id DESC LIMIT 1",(dispatch_id,)).fetchone()
    return json.loads(row[0]) if row else None


def existing(db,kind,source_id,request_key=''):
    if kind=='person':
        rows=[dict(r) for r in db.execute("SELECT * FROM word_person_corrections WHERE json_extract(manifest_json,'$.redelivery.source_kind')='person' AND json_extract(manifest_json,'$.redelivery.source_id')=? ORDER BY id DESC",(source_id,))]
        for row in rows:
            meta=json.loads(row['manifest_json'])['redelivery']
            if (request_key and meta['request_key']==request_key) or row['status'] in ('prepared','processing','draft_created','failed'):
                return {'kind':'person','id':row['id'],'case_id':row['case_id'],'cycle_id':meta['cycle_id']}
    elif kind=='goals':
        rows=db.execute("SELECT d.id,d.status,e.details_json FROM hr_goal_events e JOIN hr_goal_dispatches d ON d.id=e.dispatch_id WHERE e.action='redelivery_prepared' AND json_extract(e.details_json,'$.source_id')=? ORDER BY d.id DESC",(source_id,))
        for row in rows:
            meta=json.loads(row['details_json'])
            if (request_key and meta['request_key']==request_key) or row['status'] in ('prepared','processing','draft_created','failed'):return {'kind':'goals','id':row['id']}
    return None


def moment(value):
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed


def archive_path(group,dispatch_dir):
    if group.get('redelivery'):return Path(group['redelivery']['stored_path'])
    attachment=group.get('attachment')
    if not attachment or PurePosixPath(attachment['filename']).name!=attachment['filename']:raise ValueError('Für diese Versandgruppe fehlt ein eindeutig gespeicherter ZIP-Anhang. Frühere Outlook-Nachricht prüfen.')
    return Path(dispatch_dir)/attachment['filename']


def source(db,kind,source_id,template_paths,*,dispatch_dir,exclude=None):
    issues=[]
    if kind=='person':
        found=db.execute('SELECT * FROM word_person_corrections WHERE id=?',(source_id,)).fetchone()
        if not found:raise ValueError('Gespeicherte Einzelausgabe nicht gefunden.')
        row=dict(found);manifest=json.loads(row['manifest_json'])
        if row['status']!='sent_confirmed':raise ValueError('Die Einzelausgabe zuerst tatsächlich versenden und den Versand bestätigen oder den offenen Vorgang klären.')
        old=manifest.get('redelivery_snapshot')
        if old is None:raise ValueError('Für diese ältere Einzelausgabe fehlt ein prüfbarer Grundlagenstand. Aktuelle Formulare für die Person erstellen; die alte Datei bleibt erhalten.')
        if regular.digest(old)!=regular.digest(person_snapshot(db,manifest,template_paths)):issues.append('Grundlagen dieser Einzelausgabe geändert. Zuständigkeit, Stammdaten, Ziele und Vorlagen zuerst prüfen.')
        path=Path(row['stored_path']);sha=manifest['sha256'];documents=manifest['documents'];attachments=manifest.get('attachments',[])
        manager_pn=manifest['manager_pn'];attachment_meta=None;outputs=[]
    elif kind=='goals':
        row=goal_delivery.get(db,source_id)
        if row['status']!='sent_confirmed':raise ValueError('Die Zielnachreichungs-Gruppe zuerst tatsächlich versenden und den Versand bestätigen oder den offenen Vorgang klären.')
        outputs=goal_delivery.members(db,source_id)
        attachment_meta=row['attachment'] or (row.get('redelivery') or {}).get('attachment')
        if not attachment_meta:raise ValueError('Für diese Versandgruppe fehlt der gespeicherte Anhangnachweis. Frühere Outlook-Nachricht prüfen.')
        path=archive_path(row,dispatch_dir);sha=attachment_meta['sha256'];attachments=[];documents=[]
        bundled={d['output_id']:d for d in attachment_meta['documents']}
        if len(outputs)!=len(bundled):raise ValueError('Versandgruppe und gespeicherter ZIP-Umfang stimmen nicht überein.')
        for output in outputs:
            manifest=json.loads(output['manifest_json'])
            if len(manifest['documents'])!=1 or manifest['documents'][0]['kind']!='review' or manifest['documents'][0]['case_id']!=output['case_id']:raise ValueError('Die Ausgabe enthält nicht genau den zugeordneten Rückblick.')
            doc=manifest['documents'][0]
            record=bundled.get(output['id'])
            if not record or record['sha256']!=doc['sha256']:raise ValueError('Ein Rückblick stimmt nicht mit dem gespeicherten Versandanhang überein.')
            documents.append({**doc,'filename':record['filename'],'output_id':output['id']})
            try:
                _,data=goal_followups.validate_output(db,output['id'],template_paths)
                if not output['approved_at']:issues.append('Eine enthaltene Ausgabe ist nicht mehr als geprüft dokumentiert.')
                if (data['manager_pn'],data['recipient_email'])!=(row['manager_pn'],row['recipient_email']):issues.append('Empfänger seit der ursprünglichen Zustellung geändert.')
            except (ValueError,OSError) as exc:issues.append(str(exc))
        manager_pn=row['manager_pn']
    else:raise ValueError('Unbekannte gespeicherte Ausgabe.')
    if not path.is_file() or word_dispatch._hash(path)!=sha:raise ValueError('Der gespeicherte Versandanhang fehlt oder wurde verändert. Ausgangsdatei und Versandnachweis zuerst klären.')
    if not documents:raise ValueError('Diese Ausgabe enthält keine zugeordneten Formulare.')
    blockers=[];copies=[]
    for doc in documents:
        part=resolve(db,doc['case_id'],'review' if doc['kind']=='probation' else doc['kind'])
        name=part['first_name']+' '+part['last_name'];evidence=part_changes.effects(db,part)
        copies.append({**doc,'person_name':name,'cycle_id':part['cycle_id']})
        if not part['active'] or not part['required'] or part['event_status'] in ('cancelled','no_md') or part['obligation_status'] in ('complete','waived') or evidence['evidence']:
            blockers.append({'name':name,'kind':part['kind'],'message':'Gesprächsteil nicht mehr vorgesehen, bereits abgeschlossen oder Eingang zuerst klären.','evidence':evidence['evidence']})
        if (part['manager_pn'],part['recipient_email'])!=(manager_pn,row['recipient_email']):issues.append(name+': Empfänger oder Zuständigkeit geändert.')
        for item in evidence['files']:
            if item['status']=='cancelled' or (item['kind'],item['id']) in ((kind,source_id),exclude):continue
            if moment(item['created_at'])>moment(row['created_at']) or (item['kind']==kind and moment(item['created_at'])==moment(row['created_at']) and item['id']>source_id):issues.append(name+': Eine spätere Ausgabe liegt vor. Die aktuelle Fassung zuerst prüfen.')
    with ZipFile(path) as archive:
        if kind=='goals' and sorted(archive.namelist())!=sorted(d['filename'] for d in copies):raise ValueError('Der ZIP-Anhang enthält einen abweichenden Dateiumfang.')
        for doc in [*copies,*attachments]:
            if archive.namelist().count(doc['filename'])!=1 or hashlib.sha256(archive.read(doc['filename'])).hexdigest()!=doc['sha256']:raise ValueError('Ein gespeichertes Formular fehlt oder wurde verändert.')
    manager=db.execute('SELECT first_name,last_name FROM employees WHERE pn=?',(manager_pn,)).fetchone()
    result={'source_kind':kind,'source_id':source_id,'stored_path':str(path),'sha256':sha,'recipient_email':row['recipient_email'],
        'manager_pn':manager_pn,'manager_name':manager['first_name']+' '+manager['last_name'],'manager_first_name':manager['first_name'],
        'created_at':row['created_at'],'documents':copies,'attachments':attachments,'blockers':blockers,'issues':list(dict.fromkeys(issues)),
        'manifest':manifest if kind=='person' else None,'output_ids':[o['id'] for o in outputs],'attachment':attachment_meta}
    result['fingerprint']=regular.digest(result)
    return result


def validate(db,plan,exclude=None):
    regular.validate(db,plan,exclude=exclude)
    if plan['issues']:raise ValueError('; '.join(plan['issues']))


@serialized_goal_delivery
def prepare(db,kind,source_id,*,template_paths,dispatch_dir,output_dir,expected,request_key,reason,user_id=None):
    found=existing(db,kind,source_id,request_key)
    if found:return found
    if not reason.strip():raise ValueError('Bitte den Anlass der unveränderten Wiederzustellung festhalten.')
    target=None;db.execute('BEGIN IMMEDIATE')
    try:
        plan=source(db,kind,source_id,template_paths,dispatch_dir=dispatch_dir)
        if plan['fingerprint']!=expected:raise ValueError('Der Prüfstand hat sich inzwischen geändert. Bitte neu prüfen.')
        validate(db,plan)
        target=Path(output_dir)/uuid.uuid4().hex/'MD_Unveraenderte_Unterlagen.zip';target.parent.mkdir(parents=True)
        shutil.copyfile(plan['stored_path'],target)
        if word_dispatch._hash(target)!=plan['sha256']:raise ValueError('Die Ausgangsdatei wurde während der Übernahme verändert.')
        meta={'source_kind':kind,'source_id':source_id,'source_sha256':plan['sha256'],'source_fingerprint':plan['fingerprint'],
            'request_key':request_key,'reason':reason.strip(),'stored_path':str(target),'attachment':plan['attachment']}
        subject='Erneut: unveränderte MD-Unterlagen'
        body='Hallo '+plan['manager_first_name']+'\n\nWie gewünscht erhältst du die bereits zugestellten Formulare nochmals unverändert. Lokale Ergänzungen deiner bisherigen Arbeitsfassung sind im Anhang nicht enthalten. Wenn du diese bereits bearbeitet hast, arbeite mit deinem bisherigen Bearbeitungsstand weiter.\n\nFreundliche Grüsse\nHR'
        if kind=='person':
            manifest={**plan['manifest'],'redelivery':{**meta,'cycle_id':plan['manifest']['cycle_id']}}
            row=db.execute('''INSERT INTO word_person_corrections(case_id,stored_path,manifest_json,recipient_email,subject,body_text,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)''',
                (plan['documents'][0]['case_id'],str(target),json.dumps(manifest,ensure_ascii=False),plan['recipient_email'],subject,body,stamp(),stamp()))
            result={'kind':'person','id':row.lastrowid,'case_id':plan['documents'][0]['case_id'],'cycle_id':manifest['cycle_id']}
        else:
            row=db.execute('''INSERT INTO hr_goal_dispatches(manager_pn,recipient_email,subject,body_text,user_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?)''',
                (plan['manager_pn'],plan['recipient_email'],subject,body,user_id,stamp(),stamp()))
            result={'kind':'goals','id':row.lastrowid}
            for output_id in plan['output_ids']:db.execute('INSERT INTO hr_goal_dispatch_outputs VALUES (?,?)',(row.lastrowid,output_id))
            db.execute("INSERT INTO hr_goal_events(dispatch_id,action,details_json,user_id,created_at) VALUES (?,'redelivery_prepared',?,?,?)",(row.lastrowid,json.dumps(meta,ensure_ascii=False),user_id,stamp()))
        db.commit();return result
    except Exception:
        db.rollback()
        if target:shutil.rmtree(target.parent,ignore_errors=True)
        raise


def validate_prepared(db,row,template_paths,*,kind,dispatch_dir):
    meta=json.loads(row['manifest_json'])['redelivery'] if kind=='person' else row['redelivery']
    plan=source(db,meta['source_kind'],meta['source_id'],template_paths,dispatch_dir=dispatch_dir,exclude=(kind,row['id']))
    validate(db,plan,exclude=(kind,row['id']))
    if plan['fingerprint']!=meta['source_fingerprint'] or word_dispatch._hash(meta['stored_path'])!=meta['source_sha256']:raise ValueError('Die vorbereitete Wiederzustellung oder ihre Grundlage wurde verändert. Bitte erneut prüfen.')
    if row['recipient_email']!=plan['recipient_email'] or (kind=='goals' and row['manager_pn']!=plan['manager_pn']):
        raise ValueError('Der Empfänger der vorbereiteten Wiederzustellung wurde geändert.')
    if kind=='person':
        if word_dispatch._hash(row['stored_path'])!=meta['source_sha256']:raise ValueError('Die vorbereitete Versanddatei wurde verändert.')
        manifest=json.loads(row['manifest_json'])
        expected=[{k:v for k,v in d.items() if k not in ('person_name','cycle_id')} for d in plan['documents']]
        if manifest['documents']!=expected:raise ValueError('Der ausgewiesene Formularumfang wurde verändert.')
    elif [o['id'] for o in goal_delivery.members(db,row['id'])]!=plan['output_ids']:raise ValueError('Der ausgewiesene Gruppenumfang wurde verändert.')
    return plan
