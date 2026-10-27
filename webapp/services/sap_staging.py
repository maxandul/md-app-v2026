"""Reviewed SAP observations; applying master data never decides MD obligations."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from . import sap_import as legacy
from .outlook_lock import serialized_goal_delivery


PERSON_FIELDS=('first_name','last_name','email','salutation')
EMPLOYMENT_FIELDS=('assignment_number','position','org_unit','employment_degree','entry_date','exit_date','probation_end','active')


def available(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='hr_sap_batches'").fetchone())


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def encode(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def snapshot(db,pn):
    person=db.execute('SELECT * FROM employees WHERE pn=?',(pn,)).fetchone()
    if not person:return {}
    result={'person':{k:person[k] for k in PERSON_FIELDS},'active':person['active'],'employments':[]}
    for row in db.execute('SELECT * FROM employment_assignments WHERE person_number=? ORDER BY assignment_number',(pn,)):
        item={k:row[k] for k in EMPLOYMENT_FIELDS}
        item['managers']=[r[0] for r in db.execute('''SELECT manager_pn FROM reporting_lines
            WHERE sap_import_id=? AND employee_pn=? AND employment_assignment=? ORDER BY manager_pn''',(row['last_import_id'],pn,row['assignment_number']))]
        item['permissions']=[dict(r) for r in db.execute('''SELECT valid_from,valid_to,permission,permission_for,source_fingerprint
            FROM secondary_activity_permissions WHERE employment_id=? AND last_import_id=? ORDER BY source_fingerprint''',(row['id'],row['last_import_id']))]
        result['employments'].append(item)
    return result


def parse(path):
    """Reuse the established parser in an isolated in-memory database only."""
    memory=sqlite3.connect(':memory:');memory.row_factory=sqlite3.Row
    try:
        memory.executescript(Path(__file__).parents[1].joinpath('schema.sql').read_text(encoding='utf-8'))
        result=legacy.import_sap_workbook(memory,path,original_filename=path.name,stored_filename=path.name)
        people={r[0]:snapshot(memory,r[0]) for r in memory.execute('SELECT pn FROM employees')}
        issues={}
        for row in memory.execute("SELECT * FROM sap_import_issues WHERE severity IN ('warning','blocking')"):
            label={'conflicting_duplicate':'Widersprüchliche Angaben derselben Anstellung','missing_manager':'Direkte Führungskraft fehlt','missing_person_number':'Personalnummer fehlt'}.get(row['issue_type'],row['issue_type'])
            issues.setdefault(row['person_number'],[]).append({'blocking':row['severity']=='blocking','text':label,'rows':json.loads(row['row_numbers_json'])})
        # The old parser tolerates malformed dates and multiple managers. The
        # preview must make these ambiguities explicit before any live update.
        frame=legacy._canonicalize_sap_columns(legacy.pd.read_excel(path,dtype=object))
        frame.columns=[str(c).strip() for c in frame.columns]
        assignment=legacy._column(frame,'Ans.','Ans','Anstellung')
        for pn,rows in frame.groupby('ID_NO_ZERO',sort=False):
            pn=legacy.clean(pn)
            if pn not in people:continue
            errors=[]
            for col in ('Rufname','Nachname','lange ID/Nummer'):
                if len({legacy.clean(v) for v in rows[col]})>1:errors.append('Widersprüchliche Personenangabe: '+col)
            if not assignment or any(not legacy.clean(v) for v in rows[assignment]):errors.append('Anstellungsnummer fehlt; bitte im Export klären.')
            for col in ('Eintritt','Austritt','Ende Probezeit'):
                if col in rows and any(legacy.clean(v) and (not legacy.iso_date(v) or not '1900'<=legacy.iso_date(v)[:4]<='2100') for v in rows[col]):errors.append('Ungültiges Datum: '+col)
            if assignment:
                for _,same_assignment in rows.groupby(assignment,dropna=False):
                    for col in ('OE Bez.','Plans. Bez.'):
                        if col in same_assignment and len({legacy.clean(v) for v in same_assignment[col]})>1:errors.append('Widersprüchliche Anstellungsangabe: '+col)
            for employment in people[pn]['employments']:
                if len(employment['managers'])>1:errors.append('Mehrere direkte Führungskräfte für dieselbe Anstellung.')
                if employment['entry_date'] and employment['exit_date'] and employment['entry_date']>employment['exit_date']:errors.append('Austritt liegt vor Eintritt.')
            issues.setdefault(pn,[]).extend({'blocking':True,'text':e,'rows':[]} for e in errors)
        return people,issues,{'rows':result.row_count,'people':result.employee_count,'lines':result.reporting_line_count,
            'warnings':result.warnings,'bg_zero':result.ignored_bg_zero_count,'duplicates':result.exact_duplicate_count}
    finally:memory.close()


def stage(db,path,*,original_filename,user_id=None):
    path=Path(path);digest=legacy.file_sha256(path)
    previous=db.execute('SELECT * FROM hr_sap_batches WHERE sha256=?',(digest,)).fetchone()
    if previous:
        original=Path(previous['stored_path'])
        if not original.is_file() or legacy.file_sha256(original)!=digest:
            # Exact bytes restore the source reference; preserve the previous
            # path in the audit and never remove a differing old file.
            with db:
                db.execute('UPDATE hr_sap_batches SET stored_path=? WHERE id=?',(str(path.resolve()),previous['id']))
                db.execute('''INSERT INTO audit_log(user_id,action,object_type,object_id,details_json,created_at)
                    VALUES (?,'sap_original_restored','sap_preview',?,?,?)''',(user_id,str(previous['id']),encode({'previous_path':previous['stored_path'],'restored_path':str(path.resolve()),'sha256':digest}),stamp()))
        return previous['id']
    incoming,issues,summary=parse(path)
    if legacy.file_sha256(path)!=digest:raise ValueError('Die Quelldatei hat sich während der Prüfung geändert. Bitte erneut hochladen.')
    content_sha=hashlib.sha256(encode({'people':incoming,'issues':{pn:[{k:i[k] for k in ('blocking','text')} for i in values] for pn,values in issues.items()}}).encode()).hexdigest()
    summary['content_sha256']=content_sha
    db.execute('BEGIN IMMEDIATE')
    try:
        previous=db.execute("SELECT * FROM hr_sap_batches WHERE sha256=? OR json_extract(summary_json,'$.content_sha256')=?",(digest,content_sha)).fetchone()
        if previous and Path(previous['stored_path']).is_file() and legacy.file_sha256(Path(previous['stored_path']))==previous['sha256']:
            db.rollback();return previous['id']
        current={r[0]:snapshot(db,r[0]) for r in db.execute('SELECT pn FROM employees')}
        base=db.execute('SELECT MAX(id) FROM sap_imports').fetchone()[0]
        summary.update(previous_people=len(current),missing_people=len(set(current)-set(incoming)),unassigned_issues=issues.get('',[]))
        now=stamp()
        batch=db.execute('INSERT INTO hr_sap_batches(sha256,original_filename,stored_path,created_at,user_id,base_import_id,summary_json) VALUES (?,?,?,?,?,?,?)',
            (digest,original_filename,str(path.resolve()),now,user_id,base,encode(summary))).lastrowid
        for pn in sorted(set(current)|set(incoming)):
            before=current.get(pn,{});after=incoming.get(pn,{})
            alerts=issues.get(pn,[])
            if not after:category='missing'
            elif any(a['blocking'] for a in alerts):category='conflict'
            elif not before:category='new'
            elif before==after:category='unchanged'
            else:category='changed'
            if before and after:
                absent={e['assignment_number'] for e in before['employments']}-{e['assignment_number'] for e in after['employments']}
                if absent:alerts.append({'blocking':False,'text':'Fehlende Anstellungen bleiben erhalten: '+', '.join(sorted(absent)),'rows':[]})
            who=(after or before)['person']
            change=db.execute('''INSERT INTO hr_sap_changes(batch_id,person_number,first_name,last_name,before_json,after_json,issues_json,category)
                VALUES (?,?,?,?,?,?,?,?)''',(batch,pn,who['first_name'],who['last_name'],encode(before),encode(after),encode(alerts),category)).lastrowid
            # Only pending proposals are superseded. Already applied decisions
            # and open MD consequences remain until an actual newer application.
            db.execute("UPDATE hr_sap_changes SET superseded_by=? WHERE person_number=? AND id<>? AND superseded_by IS NULL AND data_status='pending'",(change,pn,change))
        db.commit();return batch
    except Exception:db.rollback();raise


def changes(db,batch_id=None,*,q='',state='open',page=1,page_size=25):
    where=['1'];params=[]
    if batch_id is not None:where.append('batch_id=?');params.append(batch_id)
    if q:where.append("first_name||' '||last_name||' '||person_number LIKE ?");params.append('%'+q+'%')
    if state=='open':where.extend(['superseded_by IS NULL',"((data_status='pending' AND category<>'unchanged') OR followup_status='open')"])
    elif state in ('new','changed','missing','conflict','unchanged'):where.append('category=?');params.append(state)
    base=' FROM hr_sap_changes WHERE '+' AND '.join(where)
    total=db.execute('SELECT COUNT(*)'+base,params).fetchone()[0]
    pages=max(1,(total+page_size-1)//page_size);page=max(1,min(page,pages))
    rows=[dict(r) for r in db.execute('SELECT *'+base+' ORDER BY last_name,first_name,id LIMIT ? OFFSET ?',[*params,page_size,(page-1)*page_size])]
    for row in rows:
        row['after']=json.loads(row['after_json']);row['before']=json.loads(row['before_json'])
    return dict(rows=rows,total=total,page=page,pages=pages)


def decision(db,row,action,reason,user_id,details):
    db.execute('INSERT INTO hr_sap_decisions(change_id,action,reason,details_json,user_id,created_at) VALUES (?,?,?,?,?,?)',
        (row['id'],action,reason,encode(details),user_id,stamp()))


def impacts(db,pn):
    from .part_responsibilities import case_parts
    result=[]
    for case in db.execute('''SELECT dc.* FROM dialog_cases dc WHERE dc.employee_pn=? OR dc.manager_pn=?
        OR EXISTS(SELECT 1 FROM hr_resolved_obligations o WHERE o.case_id=dc.case_id AND o.manager_pn=?) ORDER BY dc.id''',(pn,pn,pn)):
        item=dict(case);item['parts']=case_parts(db,case['case_id'])
        item['documents']=[dict(r) for r in db.execute('SELECT id,document_kind,manager_pn,received_at,handoff_status,is_current FROM official_documents WHERE case_id=? ORDER BY id',(case['case_id'],))]
        item['outputs']=[dict(r) for r in db.execute('''SELECT id,created_at,status,recipient_email FROM word_person_corrections WHERE case_id=? ORDER BY id''',(case['case_id'],))]
        item['packages']=[dict(r) for r in db.execute('''SELECT DISTINCT p.id,p.created_at,d.status FROM word_dispatch_packages p
            JOIN json_each(p.manifest_json,'$.documents') j LEFT JOIN word_mail_deliveries d ON d.package_id=p.id
            WHERE json_extract(j.value,'$.case_id')=? ORDER BY p.id''',(case['case_id'],))]
        result.append(item)
    return result


def context_token(db,pn):
    return hashlib.sha256(encode({'master':snapshot(db,pn),'impacts':impacts(db,pn)}).encode()).hexdigest()


def preserve_parts(db,pn,user_id):
    from .part_responsibilities import case_parts
    # Save the previous period/OE before replacing employee fields; no new HR
    # assignment is inferred. Existing explicit overrides are untouched.
    for case in db.execute('SELECT case_id FROM dialog_cases WHERE employee_pn=?',(pn,)):
        for part in case_parts(db,case['case_id']):
            if part['responsibility_revision']:continue
            db.execute('''INSERT INTO hr_part_responsibilities
                (obligation_id,manager_pn,form_org_source,form_org_unit,period_start,period_end,revision,reason,user_id,updated_at,origin)
                VALUES (?,?,?,?,?,?,1,?,?,?,'preserved')''',(part['obligation_id'],part['manager_pn'],part['form_org_source'],part['form_org_unit'],
                part['period_start'],part['period_end'],'Bestehende Teilgrundlage vor SAP-Übernahme gesichert; keine neue Fachentscheidung',user_id,stamp()))


def write_person(db,pn,value,import_id,now):
    who=value['person'];active=value.get('active',1)
    db.execute('''INSERT INTO persons VALUES (?,?,?,?,?,?,?) ON CONFLICT(person_number) DO UPDATE SET
        first_name=excluded.first_name,last_name=excluded.last_name,email=excluded.email,active=excluded.active,last_import_id=excluded.last_import_id,updated_at=excluded.updated_at''',
        (pn,who['first_name'],who['last_name'],who['email'],active,import_id,now))
    old=db.execute('SELECT employment_assignment FROM employees WHERE pn=?',(pn,)).fetchone()
    primary=next((e for e in value['employments'] if old and e['assignment_number']==old[0]),value['employments'][0])
    fields={'pn':pn,**who,**{k:primary[k] for k in ('position','org_unit','employment_degree','entry_date','exit_date','probation_end')},
            'employment_assignment':primary['assignment_number'],'secondary_employment':'\n'.join(p['permission_for'] for p in primary['permissions']),
            'active':active,'last_import_id':import_id,'updated_at':now}
    keys=list(fields)
    db.execute('INSERT INTO employees('+','.join(keys)+') VALUES ('+','.join('?' for _ in keys)+') ON CONFLICT(pn) DO UPDATE SET '+','.join(k+'=excluded.'+k for k in keys if k!='pn'),list(fields.values()))
    for item in value['employments']:
        data={'person_number':pn,**{k:item[k] for k in EMPLOYMENT_FIELDS},'last_import_id':import_id,'updated_at':now};keys=list(data)
        eid=db.execute('INSERT INTO employment_assignments('+','.join(keys)+') VALUES ('+','.join('?' for _ in keys)+') ON CONFLICT(person_number,assignment_number) DO UPDATE SET '+','.join(k+'=excluded.'+k for k in keys if k not in ('person_number','assignment_number'))+' RETURNING id',list(data.values())).fetchone()[0]
        for permission in item['permissions']:
            db.execute('''INSERT INTO secondary_activity_permissions(employment_id,valid_from,valid_to,permission,permission_for,source_fingerprint,last_import_id)
                VALUES (?,?,?,?,?,?,?) ON CONFLICT(employment_id,source_fingerprint) DO UPDATE SET last_import_id=excluded.last_import_id''',
                (eid,*[permission[k] for k in ('valid_from','valid_to','permission','permission_for','source_fingerprint')],import_id))
        for manager in item['managers']:
            db.execute('INSERT INTO reporting_lines(sap_import_id,employee_pn,employment_assignment,manager_pn,org_unit,position) VALUES (?,?,?,?,?,?)',
                (import_id,pn,item['assignment_number'],manager,item['org_unit'],item['position']))
            db.execute('''INSERT INTO manager_assignments(employment_id,manager_person_number,source,sap_import_id,valid_from,valid_to,active,reason,created_at,updated_at)
                VALUES (?,?,'sap',?,'','',1,'Im SAP-Export beobachtet; Wirksamkeitszeitraum unbekannt',?,?)''',(eid,manager,import_id,now,now))


@serialized_goal_delivery
def apply(db,selection,*,reason,user_id=None):
    """One transaction for selected person groups; reject stale/conflicting rows."""
    if not selection or len(reason.strip())<10:raise ValueError('Bitte Personen auswählen und die geprüfte Übernahme begründen.')
    db.execute('BEGIN IMMEDIATE')
    try:
        rows=[]
        for change_id,revision in selection.items():
            row=db.execute('SELECT * FROM hr_sap_changes WHERE id=?',(change_id,)).fetchone()
            if not row or row['revision']!=revision or row['superseded_by']:raise ValueError('Die Auswahl ist inzwischen geändert. Bitte neu prüfen.')
            if row['data_status']=='applied':continue
            if row['data_status']!='pending' or row['category'] not in ('new','changed','unchanged'):raise ValueError('Die Auswahl enthält einen fehlenden oder widersprüchlichen Datensatz. Zulässige Personen separat auswählen.')
            if encode(snapshot(db,row['person_number']))!=row['before_json']:raise ValueError('Der Vergleichsstand ist veraltet. Bitte die betroffene Person erneut vergleichen.')
            rows.append(row)
        if not rows:db.rollback();return None
        if len({r['batch_id'] for r in rows})!=1:raise ValueError('Bitte nur Personen desselben Exports gemeinsam übernehmen.')
        batch=db.execute('SELECT * FROM hr_sap_batches WHERE id=?',(rows[0]['batch_id'],)).fetchone()
        source=Path(batch['stored_path'])
        if not source.is_file() or legacy.file_sha256(source)!=batch['sha256']:
            raise ValueError('Der Originalexport fehlt oder wurde verändert. Vor Übernahme die Quelle klären.')
        now=stamp();summary=json.loads(batch['summary_json'])
        import_id=db.execute('''INSERT INTO sap_imports(original_filename,stored_filename,sha256,imported_at,row_count,employee_count,reporting_line_count,warning_count,warnings_json)
            VALUES (?,?,?,?,?,?,0,1,?)''',(f"Geprüfte Auswahl ({len(rows)} Personen): "+batch['original_filename'],batch['stored_path'],batch['sha256'],now,summary['rows'],len(rows),encode(['Ausgewählte Daten übernommen; zurückgehaltene und fehlende Einträge bleiben separat offen. Kein vollständiger SAP-Gesamtabgleich.']))).lastrowid
        # Snapshot the complete prior observation set. Retained people still
        # appear in the effective reporting-line set for future planning.
        selected={r['person_number'] for r in rows}
        for person in db.execute('SELECT pn FROM employees').fetchall():
            old=snapshot(db,person[0])
            db.execute('INSERT INTO hr_sap_observations(sap_import_id,person_number,snapshot_json,created_at) VALUES (?,?,?,?)',(import_id,person[0],encode(old),now))
            if person[0] not in selected:
                for e in old['employments']:
                    for manager in e['managers']:db.execute('INSERT INTO reporting_lines(sap_import_id,employee_pn,employment_assignment,manager_pn,org_unit,position) VALUES (?,?,?,?,?,?)',(import_id,person[0],e['assignment_number'],manager,e['org_unit'],e['position']))
        for row in rows:
            pn=row['person_number'];before=json.loads(row['before_json']);value=json.loads(row['after_json'])
            if before:
                known={e['assignment_number'] for e in value['employments']}
                value['employments'].extend(e for e in before['employments'] if e['assignment_number'] not in known)
                preserve_parts(db,pn,user_id)
            write_person(db,pn,value,import_id,now)
            db.execute('INSERT INTO hr_sap_observations(sap_import_id,person_number,snapshot_json,created_at) VALUES (?,?,?,?) ON CONFLICT(sap_import_id,person_number) DO UPDATE SET snapshot_json=excluded.snapshot_json',(import_id,pn,encode(snapshot(db,pn)),now))
            followup='none' if row['category']=='unchanged' else 'open'
            db.execute("UPDATE hr_sap_changes SET data_status='applied',applied_import_id=?,followup_status=?,revision=revision+1 WHERE id=?",(import_id,followup,row['id']))
            if followup=='open':
                db.execute("UPDATE hr_sap_changes SET superseded_by=? WHERE person_number=? AND id<>? AND superseded_by IS NULL AND followup_status='open'",(row['id'],pn,row['id']))
            decision(db,row,'apply',reason,user_id,{'before':before,'applied':value,'import_id':import_id})
        db.execute('UPDATE sap_imports SET employee_count=(SELECT COUNT(*) FROM employees),reporting_line_count=(SELECT COUNT(*) FROM reporting_lines WHERE sap_import_id=?) WHERE id=?',(import_id,import_id))
        db.commit();return import_id
    except Exception:db.rollback();raise


def resolve(db,change_id,*,revision,action,reason,token,user_id=None):
    if len(reason.strip())<10:raise ValueError('Bitte die Entscheidung mit mindestens 10 Zeichen begründen.')
    db.execute('BEGIN IMMEDIATE')
    try:
        row=db.execute('SELECT * FROM hr_sap_changes WHERE id=?',(change_id,)).fetchone()
        if not row or row['revision']!=revision or row['superseded_by']:raise ValueError('Der Abgleich wurde inzwischen geändert. Bitte neu laden.')
        if token!=context_token(db,row['person_number']):raise ValueError('Stammdaten oder Dialogstand inzwischen geändert. Bitte neu prüfen.')
        if action=='recompare' and row['data_status']=='pending':
            current=snapshot(db,row['person_number'])
            category=row['category']
            if category not in ('missing','conflict','excluded'):
                category='unchanged' if encode(current)==row['after_json'] else 'changed' if current else 'new'
            db.execute('UPDATE hr_sap_changes SET before_json=?,category=?,revision=revision+1 WHERE id=?',(encode(current),category,change_id))
        elif action=='retain' and row['data_status']=='pending':
            db.execute("UPDATE hr_sap_changes SET data_status='retained',revision=revision+1 WHERE id=?",(change_id,))
        elif action=='followup_done' and row['data_status']=='applied' and row['followup_status']=='open':
            db.execute("UPDATE hr_sap_changes SET followup_status='done',revision=revision+1 WHERE id=?",(change_id,))
        else:raise ValueError('Diese Entscheidung passt nicht zum aktuellen Bearbeitungsstand.')
        decision(db,row,action,reason,user_id,{'before':json.loads(row['before_json']),'current':snapshot(db,row['person_number']),'context':token})
        db.commit()
    except Exception:db.rollback();raise
