"""Reviewed export and campaign closure over existing records."""
import hashlib
import secrets
import json
from pathlib import Path
from flask import Blueprint,current_app,request,session,url_for,render_template,redirect,flash,abort
from itsdangerous import URLSafeTimedSerializer,BadSignature
from .db import get_db
from .goal_routes import protect,actor
from .services import export_closure_views as views,sap_export,reviewed_closure
from .services.intake_views import date_label

bp=Blueprint('export_work',__name__,url_prefix='/abschluss-export')
bp.before_request(protect)


def signer():return URLSafeTimedSerializer(current_app.secret_key,salt='md-export-close')


def token(kind,cycle_id,fingerprint):
    session.setdefault('export_close_owner',secrets.token_urlsafe(32))
    return signer().dumps({'owner':session['export_close_owner'],'kind':kind,'cycle_id':cycle_id,'fingerprint':fingerprint,'nonce':secrets.token_urlsafe(24)})


def proof(kind,cycle_id):
    value=signer().loads(request.form.get('review_token',''),max_age=3600)
    if value['owner']!=session.get('export_close_owner') or value['kind']!=kind or value['cycle_id']!=cycle_id:raise ValueError('Diese Vorschau gehört zu einer anderen Sitzung oder einem anderen Durchlauf.')
    return value


def render(template,**values):return render_template(template,active_nav='sap_export',csrf_token=session['goal_csrf'],date_label=date_label,**values)


@bp.route('/<int:cycle_id>/sap',methods=['GET','POST'])
def export(cycle_id):
    db=get_db()
    if request.method=='POST':
        try:
            value=proof('sap',cycle_id)
            if request.form.get('checked')!='yes':raise ValueError('Bitte den gezeigten Batch-Umfang prüfen.')
            batch=sap_export.create_sap_upload_batch(db,cycle_id=cycle_id,template_path=Path(current_app.root_path).parent/'templates'/'massenupload.xlsx',
                output_dir=Path(current_app.config['STORAGE_ROOT'])/'sap_exports',user_id=actor(),expected_fingerprint=value['fingerprint'],
                request_key=hashlib.sha256(request.form['review_token'].encode()).hexdigest())
            return redirect(url_for('export_work.batch',batch_id=batch['id']))
        except (BadSignature,ValueError,KeyError,TypeError) as exc:flash(str(exc) or 'Vorschau abgelaufen. Bitte erneut prüfen.','error')
    try:plan=views.export_plan(db,cycle_id)
    except LookupError:abort(404)
    filtered=[r for r in plan['rows'] if (not request.args.get('state') or r['state']==request.args['state']) and request.args.get('q','').casefold() in (r['first_name']+' '+r['last_name']+' '+str(r.get('manager_name',''))+' '+str(r['part']['employee_org_unit'] if r['part'] else '')).casefold()]
    pages=max(1,(len(filtered)+24)//25);page=min(max(request.args.get('page',1,type=int),1),pages)
    return render('export_work/preview.html',plan=plan,rows=filtered[(page-1)*25:page*25],page=page,pages=pages,total=len(filtered),labels=views.LABELS,
        review_token=token('sap',cycle_id,plan['fingerprint']))


@bp.get('/batch/<int:batch_id>')
def batch(batch_id):
    db=get_db()
    try:batch=dict(sap_export.get_sap_export_batch(db,batch_id))
    except (LookupError,ValueError) as exc:flash(str(exc),'error');return redirect(url_for('main.sap_exports'))
    rows=[dict(r) for r in db.execute('''SELECT s.*,e.first_name,e.last_name FROM sap_export_rows s JOIN dialog_cases c ON c.case_id=s.case_id JOIN employees e ON e.pn=c.employee_pn
        WHERE s.batch_id=? ORDER BY e.last_name,e.first_name,s.id''',(batch_id,))]
    page=max(1,request.args.get('page',1,type=int));pages=max(1,(len(rows)+24)//25);page=min(page,pages)
    return render('export_work/batch.html',batch=batch,rows=rows[(page-1)*25:page*25],page=page,pages=pages)


@bp.route('/<int:cycle_id>/abschluss',methods=['GET','POST'])
def close(cycle_id):
    db=get_db();reason=request.form.get('closure_reason','');owner=request.form.get('closure_owner','')
    if request.method=='POST' and request.form.get('action')!='refresh':
        try:
            value=proof('close',cycle_id)
            changed=reviewed_closure.apply(db,cycle_id,expected=value['fingerprint'],request_key=hashlib.sha256(request.form['review_token'].encode()).hexdigest(),
                reason=reason,owner=owner,checked=request.form.get('external_checked')=='yes',user_id=actor())
            flash('Kampagnenphase abgeschlossen. Restfälle bleiben bearbeitbar; eine Verarbeitung in SAP wurde dadurch nicht ausgelöst.' if changed else 'Diese Bestätigung wurde bereits dokumentiert. Der aktuelle Stand steht unten.','success')
            return redirect(url_for('export_work.close',cycle_id=cycle_id))
        except (BadSignature,ValueError,KeyError,TypeError) as exc:flash(str(exc) or 'Vorschau abgelaufen. Bitte neu prüfen.','error')
    try:plan=views.closure_plan(db,cycle_id)
    except LookupError:abort(404)
    record=db.execute('SELECT * FROM workflow_cycle_closures WHERE cycle_id=?',(cycle_id,)).fetchone()
    saved_summary=json.loads(record['summary_json']) if record else None
    return render('export_work/closure.html',plan=plan,record=record,saved_summary=saved_summary,reason=reason,owner=owner,
        review_token=token('close',cycle_id,plan['fingerprint']))
