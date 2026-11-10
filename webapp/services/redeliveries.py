"""Copy recorded Word bytes into existing dispatch records, without rendering forms."""
import hashlib
import json
import shutil
import uuid
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZIP_DEFLATED
from . import word_dispatch as dispatch
from .part_responsibilities import resolve
from .outlook_lock import serialized_goal_delivery, check_goal_workflow
from .goal_followups import return_evidence


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def source(connection,package_id,template_paths,*,case_id='',allowed_latest=None):
    row=connection.execute('''SELECT p.*,d.status AS delivery_status,d.recipient_email,
        m.first_name||' '||m.last_name AS manager_name,m.first_name AS manager_first_name,c.review_year,c.outlook_year
        FROM word_dispatch_packages p LEFT JOIN word_mail_deliveries d ON d.package_id=p.id
        LEFT JOIN employees m ON m.pn=p.manager_pn JOIN cycles c ON c.id=p.cycle_id WHERE p.id=?''',(package_id,)).fetchone()
    if not row:raise ValueError('Gespeicherte Ausgabe nicht gefunden.')
    row=dict(row)
    if row['discarded_at'] or row['delivery_status']!='sent_confirmed':
        raise ValueError('Nur eine als versandt bestätigte, nicht verworfene Ausgabe kann erneut zugestellt werden. Den bestehenden Versand zuerst fortsetzen oder klären.')
    latest=connection.execute("SELECT MAX(id) FROM word_dispatch_packages WHERE cycle_id=? AND manager_pn=? AND discarded_at=''",(row['cycle_id'],row['manager_pn'])).fetchone()[0]
    if latest not in (package_id,allowed_latest):raise ValueError('Eine neuere Ausgabe liegt vor. Diese zuerst prüfen; die alte Fassung wird nicht erneut zugestellt.')
    manifest=json.loads(row['manifest_json'])
    if dispatch._hash(row['stored_path'])!=row['sha256']:raise ValueError('Die gespeicherte Versanddatei wurde verändert. Original und aktuelle Ausgabe zuerst klären.')
    documents=[d for d in manifest['documents'] if not case_id or d['case_id']==case_id]
    current=dispatch.source_snapshot(connection,cycle_id=row['cycle_id'],manager_pn=row['manager_pn'],template_paths=template_paths)
    if case_id:
        old=manifest.get('source_snapshot')
        if not old:raise ValueError('Für diese ältere Ausgabe fehlt ein prüfbarer Grundlagenstand. Aktuelle Formulare gezielt erstellen.')
        needed={d['kind'] for d in documents}|{a['kind'] for a in manifest.get('attachments',[])}
        def scoped(snapshot):
            return {**snapshot,'cases':[c for c in snapshot['cases'] if c['case_id']==case_id],
                    'templates':{k:v for k,v in snapshot['templates'].items() if k in needed},
                    'feedback_case_ids':[c for c in snapshot.get('feedback_case_ids',[]) if c==case_id]}
        unchanged=digest(scoped(old))==digest(scoped(current))
    else:unchanged=digest(current)==row['source_fingerprint']
    if not unchanged:
        raise ValueError('Grundlagen seit dieser Ausgabe geändert. Zuständigkeit, Stammdaten, Ziele und Vorlagen zuerst prüfen; keine unveränderte Wiederzustellung möglich.')
    if not documents:raise ValueError('Diese Person gehört nicht zur gewählten gespeicherten Ausgabe.')
    blockers=[]
    for doc_index,doc in enumerate(documents):
        part=resolve(connection,doc['case_id'],'review' if doc['kind']=='probation' else doc['kind'])
        name=(part['first_name']+' '+part['last_name']).strip()
        doc={**doc,'person_name':name}
        documents[doc_index]=doc
        closed=not part['required'] or not part['active'] or part['event_status'] in ('cancelled','no_md') or part['obligation_status'] in ('complete','waived')
        evidence=return_evidence(connection,part)
        if closed or evidence:blockers.append({'name':name,'kind':part['kind'],'message':'Gesprächsteil ist abgeschlossen oder nicht mehr vorgesehen.' if closed else 'Rücklauf vorhanden oder Eingang zuerst klären.','evidence':evidence})
    result={**row,'documents':documents,'attachments':manifest.get('attachments',[]),'case_id':case_id,'blockers':blockers}
    result['fingerprint']=digest({'package_id':package_id,'case_id':case_id,'source':row['source_fingerprint'],'sha256':row['sha256'],
        'recipient':row['recipient_email'],'documents':documents,'blockers':blockers})
    return result


def validate(connection,plan,*,exclude=None):
    if plan['blockers']:
        reasons=[]
        for blocker in plan['blockers']:
            files=[]
            for e in blocker['evidence']:
                if e.get('pending_import_id'):
                    row=connection.execute('SELECT original_filename FROM word_pdf_imports WHERE id=?',(e['pending_import_id'],)).fetchone()
                    if row:files.append(row[0])
                elif e.get('unassigned_attachment_id'):
                    row=connection.execute('SELECT original_filename FROM inbound_mail_attachments WHERE id=?',(e['unassigned_attachment_id'],)).fetchone()
                    if row:files.append(row[0])
            reasons.append(blocker['name']+': '+blocker['message']+(' Dateien: '+', '.join(files) if files else ''))
        raise ValueError('; '.join(reasons))
    check_goal_workflow(connection,[d['case_id'] for d in plan['documents']],documents=plan['documents'],exclude=exclude)


def existing(connection,package_id,case_id='',request_key=''):
    table='word_person_corrections' if case_id else 'word_dispatch_packages'
    rows=connection.execute('SELECT p.*'+(",d.status AS delivery_status FROM word_dispatch_packages p LEFT JOIN word_mail_deliveries d ON d.package_id=p.id" if not case_id else ' FROM word_person_corrections p')+
        " WHERE json_extract(p.manifest_json,'$.redelivery.source_package_id')=? AND COALESCE(json_extract(p.manifest_json,'$.redelivery.case_id'),'')=? ORDER BY p.id DESC",(package_id,case_id))
    rows=list(rows)
    if request_key:
        for row in rows:
            meta=json.loads(row['manifest_json'])['redelivery']
            if meta['request_key']==request_key:return {'kind':'person' if case_id else 'regular','id':row['id'],'case_id':case_id,'cycle_id':meta['cycle_id']}
    for row in rows:
        meta=json.loads(row['manifest_json'])['redelivery']
        status=row['status'] if case_id else row['delivery_status']
        if status in (None,'prepared','processing','draft_created','failed') and (case_id or not row['discarded_at']):
            return {'kind':'person' if case_id else 'regular','id':row['id'],'case_id':case_id,'cycle_id':meta['cycle_id']}
    return None


def _copy_subset(plan,target):
    with ZipFile(plan['stored_path']) as source_zip,ZipFile(target,'w',ZIP_DEFLATED) as archive:
        for entry in [*plan['documents'],*plan['attachments']]:
            name=entry['filename'];path=PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or '\\' in name:raise ValueError('Ungültiger gespeicherter Dateiname.')
            if source_zip.namelist().count(name)!=1:raise ValueError('Eine gespeicherte Datei fehlt oder ist doppelt enthalten.')
            raw=source_zip.read(name)
            if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Eine gespeicherte Word-Datei wurde verändert.')
            archive.writestr(name,raw)


@serialized_goal_delivery
def prepare(connection,package_id,*,case_id='',expected_fingerprint,request_key,reason,template_paths,output_dir):
    """A retry finds its record, even when already confirmed sent. No second effect."""
    found=existing(connection,package_id,case_id,request_key)
    if found:return found
    if not reason.strip():raise ValueError('Bitte den Anlass der erneuten Zustellung festhalten.')
    connection.execute('BEGIN IMMEDIATE')
    target=None
    try:
        plan=source(connection,package_id,template_paths,case_id=case_id)
        if plan['fingerprint']!=expected_fingerprint:raise ValueError('Der Prüfstand hat sich geändert. Bitte die Wiederzustellung erneut prüfen.')
        validate(connection,plan)
        directory=Path(output_dir)/('redelivery-'+uuid.uuid4().hex);directory.mkdir(parents=True)
        target=directory/'MD_Unveraenderte_Unterlagen.zip'
        if case_id:_copy_subset(plan,target)
        else:
            shutil.copyfile(plan['stored_path'],target)
            if dispatch._hash(target)!=plan['sha256']:raise ValueError('Die Versanddatei wurde während der Übernahme verändert.')
        manifest=json.loads(plan['manifest_json'])
        # The source manifest remains in its original ZIP. This is transport provenance.
        documents=[{k:v for k,v in d.items() if k!='person_name'} for d in plan['documents']]
        manifest={**manifest,'goal_warnings':[] if case_id else manifest.get('goal_warnings',[]),'documents':documents,'sha256':dispatch._hash(target),'redelivery':{
            'source_package_id':package_id,'source_sha256':plan['sha256'],'source_fingerprint':plan['source_fingerprint'],
            'case_id':case_id,'cycle_id':plan['cycle_id'],'request_key':request_key,'reason':reason.strip()}}
        now=dispatch._stamp()
        if case_id:
            cur=connection.execute('''INSERT INTO word_person_corrections(case_id,stored_path,manifest_json,recipient_email,subject,body_text,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?)''',(case_id,str(target),json.dumps(manifest,ensure_ascii=False),plan['recipient_email'],
                'Erneut: MD-Unterlagen für '+plan['documents'][0]['person_name'],
                'Hallo '+plan['manager_first_name']+'\n\nWie gewünscht erhältst du die bereits zugestellten Formulare nochmals unverändert. Wenn du deine erste Fassung bereits bearbeitet hast, arbeite mit deinem bisherigen Bearbeitungsstand weiter. Der Anhang enthält diese lokalen Ergänzungen nicht.\n\nFreundliche Grüsse\nHR',now,now))
        else:
            cur=connection.execute('''INSERT INTO word_dispatch_packages(export_id,cycle_id,manager_pn,stored_path,sha256,source_fingerprint,manifest_json,created_at)
                VALUES (?,?,?,?,?,?,?,?)''',('REDELIVERY-'+uuid.uuid4().hex,plan['cycle_id'],plan['manager_pn'],str(target),manifest['sha256'],plan['source_fingerprint'],json.dumps(manifest,ensure_ascii=False),now))
        connection.commit()
        return {'kind':'person' if case_id else 'regular','id':cur.lastrowid,'case_id':case_id,'cycle_id':plan['cycle_id']}
    except Exception:
        connection.rollback()
        if target:shutil.rmtree(target.parent,ignore_errors=True)
        raise


def validate_prepared(connection,row,template_paths,*,kind):
    manifest=json.loads(row['manifest_json']);meta=manifest['redelivery']
    plan=source(connection,meta['source_package_id'],template_paths,case_id=meta['case_id'],allowed_latest=row['id'] if kind=='regular' else None)
    validate(connection,plan,exclude=('package' if kind=='regular' else 'person',row['id']))
    if dispatch._hash(row['stored_path'])!=manifest['sha256']:raise ValueError('Die vorbereitete Wiederzustellung wurde verändert.')
    docs=[{k:v for k,v in d.items() if k!='person_name'} for d in plan['documents']]
    if docs!=manifest['documents'] or plan['source_fingerprint']!=meta['source_fingerprint'] or plan['sha256']!=meta['source_sha256']:
        raise ValueError('Die unveränderte Grundlage ist nicht mehr dieselbe. Bitte erneut prüfen.')
    if kind=='person' and plan['recipient_email']!=row['recipient_email']:raise ValueError('Der Empfänger hat sich geändert.')
    return plan
