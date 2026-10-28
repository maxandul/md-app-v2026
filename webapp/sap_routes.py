"""SAP preview, selected application and linked MD follow-up decisions."""
import json
from pathlib import Path
import uuid
from zipfile import BadZipFile
from urllib.parse import urlsplit
from flask import Blueprint,abort,current_app,flash,redirect,render_template,request,send_file,session,url_for
from .db import get_db
from .goal_routes import protect,actor
from .services import sap_staging as service

bp=Blueprint('sap_work',__name__,url_prefix='/stammdaten/abgleich')
bp.before_request(protect)
LABELS={'new':'Neue Person / Anstellung','changed':'Geänderte Angaben','missing':'Im Export nicht enthalten','conflict':'Widerspruch klären','unchanged':'Unverändert','excluded':'Nicht übernommen'}


def render(name,**values):
    back=request.values.get('back','');parsed=urlsplit(back)
    if parsed.netloc or parsed.scheme or not parsed.path.startswith('/stammdaten/abgleich'):back=url_for('sap_work.index')
    return render_template(name,active_nav='master_data',csrf_token=session['goal_csrf'],category_labels=LABELS,back=back,**values)


@bp.get('')
def index():
    db=get_db();batch_id=request.args.get('batch_id',type=int)
    batch=db.execute('SELECT * FROM hr_sap_batches WHERE id=?',(batch_id,)).fetchone() if batch_id else None
    if batch_id and not batch:abort(404)
    filters=dict(q=request.args.get('q',''),state=request.args.get('state','open'),page=request.args.get('page',1,type=int))
    return render('sap/index.html',batch=batch,summary=json.loads(batch['summary_json']) if batch else None,
        batches=db.execute('''SELECT b.*,COUNT(c.id) AS people,SUM(c.data_status='applied') AS applied,
            SUM(c.category='conflict') AS conflicts FROM hr_sap_batches b LEFT JOIN hr_sap_changes c ON c.batch_id=b.id
            GROUP BY b.id ORDER BY b.id DESC LIMIT 50''').fetchall(),filters=filters,
        page_url=lambda p:url_for('sap_work.index',batch_id=batch_id,**{**filters,'page':p}),
        **service.changes(db,batch_id,**filters))


@bp.post('/upload')
def upload():
    file=request.files.get('sap_file')
    if not file or not file.filename or not file.filename.lower().endswith('.xlsx'):
        flash('Bitte einen SAP-Export im XLSX-Format auswählen.','error');return redirect(url_for('sap_work.index'))
    root=Path(current_app.config['STORAGE_ROOT'])/'sap_staging';root.mkdir(parents=True,exist_ok=True)
    path=root/(uuid.uuid4().hex+'.xlsx');file.save(path)
    try:batch=service.stage(get_db(),path,original_filename=file.filename,user_id=actor())
    except (ValueError,KeyError,OSError,BadZipFile) as exc:
        path.unlink(missing_ok=True);flash(str(exc),'error');return redirect(url_for('sap_work.index'))
    saved=get_db().execute('SELECT stored_path FROM hr_sap_batches WHERE id=?',(batch,)).fetchone()[0]
    if Path(saved)!=path:path.unlink(missing_ok=True)
    flash('Vorschau gespeichert. Stammdaten und bestehende Dialoge sind noch unverändert.','success')
    return redirect(url_for('sap_work.index',batch_id=batch))


def selection():
    result={}
    try:
        for value in request.form.getlist('selected'):
            key,revision=value.split(':');result[int(key)]=int(revision)
    except ValueError:abort(400)
    if not result:raise ValueError('Bitte mindestens eine Person auswählen.')
    return result


def list_url():
    return url_for('sap_work.index',batch_id=request.form.get('batch_id',type=int),
        q=request.form.get('q',''),state=request.form.get('state','open'),page=request.form.get('page',1,type=int))


@bp.post('/auswahl')
def selected():
    try:
        if request.form.get('selection_scope')=='all_filtered':
            chosen={r['id']:r['revision'] for r in service.eligible_changes(get_db(),
                request.form.get('batch_id',type=int),q=request.form.get('q',''),state=request.form.get('state','open'))}
            if not chosen:raise ValueError('Keine übernehmbaren Einträge für diesen Export und Filter vorhanden.')
        else:chosen=selection()
    except ValueError as exc:flash(str(exc),'error');return redirect(list_url())
    rows=[]
    for key,revision in chosen.items():
        row=get_db().execute('SELECT * FROM hr_sap_changes WHERE id=?',(key,)).fetchone()
        if not row or row['revision']!=revision or row['superseded_by'] or row['data_status']!='pending' or row['category'] not in ('new','changed','unchanged'):
            flash('Die Auswahl enthält inzwischen geänderte oder nicht zulässige Einträge. Bitte neu auswählen.','error');return redirect(list_url())
        value=dict(row);value['assignments']=[e['assignment_number'] for e in json.loads(row['after_json'])['employments']];rows.append(value)
    if len({r['batch_id'] for r in rows})!=1:
        flash('Bitte einen Export öffnen und daraus Personen auswählen.','error');return redirect(url_for('sap_work.index'))
    return render('sap/selection.html',rows=rows)


@bp.post('/uebernehmen')
def apply_selection():
    try:
        if request.form.get('checked')!='yes':raise ValueError('Bitte den Umfang der Datenübernahme bestätigen.')
        imported=service.apply(get_db(),selection(),reason=request.form.get('reason',''),user_id=actor())
    except ValueError as exc:flash(str(exc),'error')
    else:flash(f'Datenübernahme {imported} gespeichert. Dialogentscheidungen bleiben separat offen.' if imported else 'Diese Auswahl wurde bereits übernommen.','success')
    return redirect(list_url())


def comparison(before,after):
    labels={'first_name':'Vorname','last_name':'Nachname','email':'E-Mail','salutation':'Anrede','active':'Aktiv',
        'position':'Funktion','org_unit':'OE','employment_degree':'Beschäftigungsgrad','entry_date':'Eintritt','exit_date':'Austritt',
        'probation_end':'Probezeitende','managers':'SAP-Führungskraft (PN)','permissions':'Bewilligungen'}
    def flat(value):
        result=dict(value.get('person',{}));result['active']=value.get('active','')
        for e in value.get('employments',[]):
            for key,label in labels.items():
                if key not in e:continue
                v=e[key]
                if key=='managers':v=', '.join(v) or 'Keine direkte Führungskraft'
                if key=='permissions':v='; '.join(p['permission_for'] for p in v)
                result['Ans. '+e['assignment_number']+' · '+label]=v
        return result
    left,right=flat(before),flat(after)
    return [dict(label=labels.get(k,k),before=left.get(k,'—'),after=right.get(k,'—'),changed=left.get(k)!=right.get(k)) for k in dict.fromkeys([*left,*right])]


@bp.route('/person/<int:change_id>',methods=['GET','POST'])
def detail(change_id):
    db=get_db();row=db.execute('SELECT * FROM hr_sap_changes WHERE id=?',(change_id,)).fetchone()
    if not row:abort(404)
    if request.method=='POST':
        try:service.resolve(db,change_id,revision=request.form.get('revision',type=int),action=request.form.get('action',''),reason=request.form.get('reason',''),token=request.form.get('context',''),user_id=actor())
        except ValueError as exc:flash(str(exc),'error')
        else:flash('Entscheidung mit Begründung gespeichert.','success')
        return redirect(url_for('sap_work.detail',change_id=change_id,back=request.values.get('back','')))
    return render('sap/detail.html',row=row,comparison=comparison(json.loads(row['before_json']),json.loads(row['after_json'])),
        issues=json.loads(row['issues_json']),impacts=service.impacts(db,row['person_number']),context=service.context_token(db,row['person_number']),
        history=db.execute('SELECT * FROM hr_sap_decisions WHERE change_id=? ORDER BY id DESC',(change_id,)).fetchall())


@bp.get('/<int:batch_id>/original')
def original(batch_id):
    row=get_db().execute('SELECT * FROM hr_sap_batches WHERE id=?',(batch_id,)).fetchone()
    if not row or not Path(row['stored_path']).is_file():abort(404)
    if service.legacy.file_sha256(Path(row['stored_path']))!=row['sha256']:abort(409,'Der Originalexport wurde verändert. Bitte dieselbe Originaldatei erneut hochladen.')
    return send_file(row['stored_path'],as_attachment=True,download_name=row['original_filename'])
