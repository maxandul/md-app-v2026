"""Explicit, signed preparation of another dispatch of recorded Word bytes."""
import hashlib
import secrets
from pathlib import Path
from itsdangerous import URLSafeTimedSerializer, BadSignature
from flask import Blueprint,current_app,request,session,render_template,redirect,url_for,flash,abort
from .goal_routes import protect
from .db import get_db
from .auth import audit
from .services import redeliveries as service
from .services.intake_views import date_label

bp=Blueprint('redelivery',__name__,url_prefix='/versand/pakete')
bp.before_request(protect)


def signer():return URLSafeTimedSerializer(current_app.secret_key,salt='md-redelivery')


def destination(result):
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
    if not existing:
        try:
            plan=service.source(db,package_id,current_app.config['WORD_TEMPLATE_PATHS'],case_id=case_id)
            service.validate(db,plan)
            token=signer().dumps({'owner':session['redelivery_owner'],'package_id':package_id,'case_id':case_id,'fingerprint':plan['fingerprint'],'nonce':secrets.token_urlsafe(24)})
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
