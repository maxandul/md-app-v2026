"""Explicit, signed preparation of another dispatch of recorded Word bytes."""
import hashlib
import secrets
from pathlib import Path
from itsdangerous import URLSafeTimedSerializer, BadSignature
from flask import Blueprint,current_app,request,session,render_template,redirect,url_for,flash,abort,send_file
from .goal_routes import protect,actor
from .db import get_db
from .auth import audit
from .services import redeliveries as service
from .services.intake_views import date_label

bp=Blueprint('redelivery',__name__,url_prefix='/versand/pakete')
bp.before_request(protect)


def signer():return URLSafeTimedSerializer(current_app.secret_key,salt='md-redelivery')


def destination(result):
    if result['kind']=='goals':return url_for('goal_work.dispatch',dispatch_id=result['id'])
    if result['kind']=='regular':return url_for('main.dispatch_package',package_id=result['id'])
    return url_for('main.person_word_correction',cycle_id=result['cycle_id'],case_id=result['case_id'],_anchor='correction-'+str(result['id']))


@bp.route('/<int:package_id>/erneut',methods=['GET','POST'])
def prepare(package_id):
    db=get_db();case_id=request.values.get('case_id','');plan=None;error='';token='';existing=None
    if not db.execute('SELECT 1 FROM word_dispatch_packages WHERE id=?',(package_id,)).fetchone():abort(404)
    session.setdefault('redelivery_owner',secrets.token_urlsafe(32))
    if request.method=='POST':
        try:
            signed=request.form.get('request_token','')
            proof=signer().loads(signed,max_age=3600)
            if proof['owner']!=session['redelivery_owner'] or proof['package_id']!=package_id or proof['case_id']!=case_id:raise ValueError('Diese Vorschau gehört zu einer anderen Auswahl oder Sitzung.')
            if request.form.get('checked')!='yes':raise ValueError('Bitte die unveränderte Fassung, den Umfang und den Empfänger ausdrücklich prüfen.')
            result=service.prepare(db,package_id,case_id=case_id,expected_fingerprint=proof['fingerprint'],request_key=hashlib.sha256(signed.encode()).hexdigest(),
                reason=request.form.get('reason',''),template_paths=current_app.config['WORD_TEMPLATE_PATHS'],output_dir=Path(current_app.config['STORAGE_ROOT'])/'redeliveries')
            audit('word_redelivery_prepared','word_package',str(package_id),output=result)
            flash('Unveränderte Unterlagen für eine erneute Zustellung bereitgestellt. Der frühere Versandnachweis bleibt erhalten. Noch kein neuer Versand.','success')
            return redirect(destination(result))
        except (BadSignature,KeyError,TypeError,ValueError,OSError) as exc:error=str(exc) or 'Vorschau abgelaufen. Bitte erneut prüfen.'
    existing=service.existing(db,package_id,case_id)
    try:
        excluded=(('package' if existing['kind']=='regular' else 'person'),existing['id']) if existing else None
        plan=service.source(db,package_id,current_app.config['WORD_TEMPLATE_PATHS'],case_id=case_id,allowed_latest=existing['id'] if existing and existing['kind']=='regular' else None)
        service.validate(db,plan,exclude=excluded)
        if not existing:token=signer().dumps({'owner':session['redelivery_owner'],'package_id':package_id,'case_id':case_id,'fingerprint':plan['fingerprint'],'nonce':secrets.token_urlsafe(24)})
    except (ValueError,OSError) as exc:error=error or str(exc)
    # Enrich concrete evidence links; an unknown file remains unassigned.
    if plan:
        for blocker in plan['blockers']:
            for evidence in blocker['evidence']:
                if evidence.get('pending_import_id'):
                    row=db.execute('SELECT original_filename FROM word_pdf_imports WHERE id=?',(evidence['pending_import_id'],)).fetchone()
                    evidence['label']=row[0] if row else 'PDF-Eingang'
                    evidence['href']=url_for('main.word_pdf_review',import_id=evidence['pending_import_id'],back=request.full_path)
                elif evidence.get('unassigned_attachment_id'):
                    row=db.execute('SELECT a.original_filename,m.subject FROM inbound_mail_attachments a JOIN inbound_mail_messages m ON m.id=a.mail_message_id WHERE a.id=?',(evidence['unassigned_attachment_id'],)).fetchone()
                    evidence['label']=row['original_filename'] if row else 'Mailanhang prüfen'
                    evidence['href']=url_for('main.returns_overview',cycle_id='',tab='mail',mail_status='all',mail_q=row['subject'] if row else '')+'#postfach'
                elif evidence.get('document_id'):
                    evidence['label']='Vorhandenen Rücklauf prüfen'
                    evidence['href']=url_for('return_work.detail',document_id=evidence['document_id'],back=request.full_path)
    page=max(1,request.args.get('page',1,type=int));pages=max(1,((len(plan['documents']) if plan else 0)+49)//50);page=min(page,pages)
    return render_template('shipping/redelivery.html',page=page,pages=pages,documents=plan['documents'][(page-1)*50:page*50] if plan else [],active_nav='dispatch',plan=plan,package_id=package_id,case_id=case_id,
        csrf_token=session['goal_csrf'],error=error,token=token,existing=destination(existing) if existing else None,date_label=date_label,reason=request.form.get('reason',''))


@bp.route('/gespeichert/<kind>/<int:source_id>',methods=['GET','POST'])
def saved(kind,source_id):
    from .services import saved_redeliveries as saved_service,part_change_links
    if kind not in ('person','goals'):abort(404)
    db=get_db();plan=None;error='';signed_token=''
    session.setdefault('redelivery_owner',secrets.token_urlsafe(32))
    options=dict(template_paths=current_app.config['WORD_TEMPLATE_PATHS'],dispatch_dir=Path(current_app.config['STORAGE_ROOT'])/'goal_workflow'/'dispatches')
    if request.method=='POST':
        try:
            signed=request.form.get('request_token','');proof=signer().loads(signed,max_age=3600)
            if proof['owner']!=session['redelivery_owner'] or proof['kind']!=kind or proof['source_id']!=source_id:raise ValueError('Diese Vorschau gehört zu einer anderen Auswahl oder Sitzung.')
            if request.form.get('checked')!='yes':raise ValueError('Bitte Umfang, Empfänger und unveränderte Fassung prüfen.')
            result=saved_service.prepare(db,kind,source_id,**options,output_dir=Path(current_app.config['STORAGE_ROOT'])/'redeliveries',
                expected=proof['fingerprint'],request_key=hashlib.sha256(signed.encode()).hexdigest(),reason=request.form.get('reason',''),user_id=actor())
            audit('saved_word_redelivery_prepared','saved_word_source',kind+':'+str(source_id),output=result)
            flash('Gespeicherte Dateien für eine erneute Zustellung bereitgestellt. Noch kein neuer Versand.','success')
            return redirect(destination(result))
        except (BadSignature,ValueError,KeyError,TypeError,OSError) as exc:error=str(exc) or 'Vorschau abgelaufen. Bitte erneut prüfen.'
    existing=saved_service.existing(db,kind,source_id)
    try:
        excluded=(kind,existing['id']) if existing else None
        plan=saved_service.source(db,kind,source_id,**options,exclude=excluded)
        saved_service.validate(db,plan,exclude=excluded)
        if not existing:signed_token=signer().dumps({'owner':session['redelivery_owner'],'kind':kind,'source_id':source_id,'fingerprint':plan['fingerprint'],'nonce':secrets.token_urlsafe(24)})
    except (ValueError,OSError) as exc:error=error or str(exc)
    if plan:
        for blocker in plan['blockers']:
            part_change_links.enrich(db,{'effects':{'files':[],'evidence':blocker['evidence']},'part':{}},request.full_path)
    if kind=='person':
        record=db.execute('SELECT p.case_id,c.cycle_id FROM word_person_corrections p JOIN dialog_cases c ON c.case_id=p.case_id WHERE p.id=?',(source_id,)).fetchone()
        source_href=url_for('main.person_word_correction',cycle_id=record['cycle_id'],case_id=record['case_id'],_anchor='correction-'+str(source_id)) if record else url_for('main.dispatch')
    else:source_href=url_for('goal_work.dispatch',dispatch_id=source_id)
    page=max(1,request.args.get('page',1,type=int));pages=max(1,((len(plan['documents']) if plan else 0)+49)//50);page=min(page,pages)
    return render_template('shipping/saved_redelivery.html',active_nav='dispatch',plan=plan,error=error,token=signed_token,kind=kind,source_id=source_id,
        existing=destination(existing) if existing else None,source_href=source_href,csrf_token=session['goal_csrf'],date_label=date_label,reason=request.form.get('reason',''),
        page=page,pages=pages,documents=plan['documents'][(page-1)*50:page*50] if plan else [])


@bp.get('/zielnachreichung/<int:dispatch_id>/zip')
def goal_archive(dispatch_id):
    from .services import saved_redeliveries,goal_delivery,word_dispatch
    try:
        group=goal_delivery.get(get_db(),dispatch_id)
        path=saved_redeliveries.archive_path(group,Path(current_app.config['STORAGE_ROOT'])/'goal_workflow'/'dispatches')
        meta=group.get('attachment') or (group.get('redelivery') or {}).get('attachment')
        if not meta or word_dispatch._hash(path)!=meta['sha256']:raise ValueError('Der gespeicherte ZIP-Anhang fehlt oder wurde verändert.')
    except (ValueError,OSError) as exc:
        flash(str(exc),'error');return redirect(url_for('goal_work.dispatch',dispatch_id=dispatch_id))
    return send_file(path,as_attachment=True,download_name=path.name)
