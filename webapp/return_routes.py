"""One return/version from validated data through signature evidence to handoff."""
from pathlib import Path
import secrets
import uuid
from urllib.parse import urlsplit
from flask import Blueprint,abort,current_app,flash,g,redirect,render_template,request,session,url_for,send_file
from .auth import login_required
from .db import get_db
from .services import return_review as service


bp=Blueprint('return_work',__name__,url_prefix='/arbeit/ruecklaeufe')


@bp.before_request
@login_required
def protect():
    if not current_app.config.get('HR_GOAL_WORKFLOW') or not service.available(get_db()):abort(404)
    if g.user and g.user['password_temporary']:return redirect(url_for('auth.change_password'))
    session.setdefault('goal_csrf',secrets.token_urlsafe(32))
    if request.method=='POST' and not secrets.compare_digest(request.form.get('csrf_token',''),session['goal_csrf']):abort(400,'Bitte die Seite neu öffnen.')


def actor():return g.user['id'] if g.user else None


def back_link():
    value=request.values.get('back','')
    parsed=urlsplit(value)
    return value if value.startswith('/') and not value.startswith('//') and not parsed.netloc and not parsed.scheme and '\\' not in value else url_for('main.returns_overview')


@bp.get('/<int:document_id>')
def detail(document_id):
    try:row=service.view(get_db(),document_id)
    except ValueError:abort(404)
    alternatives=get_db().execute('''SELECT w.id,w.original_filename,w.status FROM word_pdf_imports w
        WHERE w.official_document_id=? OR w.duplicate_of IN(SELECT id FROM word_pdf_imports WHERE official_document_id=?) ORDER BY w.id''',(document_id,document_id)).fetchall()
    pending=get_db().execute('''SELECT w.id,w.original_filename FROM word_pdf_imports w
        LEFT JOIN workflow_pdf_state s ON s.import_id=w.id WHERE w.status='pending' AND COALESCE(s.dismissed,0)=0
        AND NOT EXISTS(SELECT 1 FROM hr_goal_origins o WHERE o.pdf_import_id=w.id)
        AND json_extract(COALESCE(NULLIF(w.reviewed_json,''),w.parsed_json),'$.data.pn')=? ORDER BY w.id DESC LIMIT 25''',(row['employee_pn'],)).fetchall()
    return render_template('returns/detail.html',item=row,alternatives=alternatives,pending=pending,csrf_token=session['goal_csrf'],back=back_link(),active_nav='returns')


@bp.get('/<int:document_id>/scan')
def evidence(document_id):
    try:row=service.view(get_db(),document_id)
    except ValueError:abort(404)
    if not row['evidence']:abort(404)
    try:path=service.checked_file(row['evidence']['stored_path'],row['evidence']['sha256'])
    except ValueError:abort(409,'Das Scanoriginal fehlt oder wurde verändert.')
    return send_file(path,mimetype='application/pdf',download_name=row['evidence']['original_filename'])


@bp.post('/<int:document_id>')
def act(document_id):
    db=get_db();action=request.form.get('action','');common=dict(revision=request.form.get('revision','-1'),token=request.form.get('token',''),user_id=actor())
    try:
        if action=='attach':
            incoming_id=request.form.get('import_id','')
            if incoming_id:
                incoming=db.execute('SELECT * FROM word_pdf_imports WHERE id=?',(incoming_id,)).fetchone()
                if not incoming:raise ValueError('Der gesicherte PDF-Eingang wurde nicht gefunden.')
                service.checked_file(incoming['stored_path'],incoming['sha256'])
                service.attach_evidence(db,document_id,path=Path(incoming['stored_path']),filename=incoming['original_filename'],directory=Path(current_app.config['STORAGE_ROOT'])/'return_evidence',import_id=incoming['id'],**common)
            else:
                upload=request.files.get('scan_file')
                if not upload or not upload.filename or not upload.filename.lower().endswith('.pdf'):raise ValueError('Bitte einen PDF-Scan auswählen.')
                directory=Path(current_app.config['STORAGE_ROOT'])/'return_evidence';directory.mkdir(parents=True,exist_ok=True)
                temporary=directory/('upload-'+uuid.uuid4().hex+'.pdf')
                try:
                    upload.save(temporary)
                    service.attach_evidence(db,document_id,path=temporary,filename=upload.filename,directory=directory,**common)
                finally:temporary.unlink(missing_ok=True)
            flash('Scan zugeordnet. '+service.view(db,document_id)['signature_label']+'.','success')
        elif action in ('confirmed','missing','requested'):
            service.inspect_signatures(db,document_id,action=action,reason=request.form.get('reason',''),employee_signed=request.form.get('employee_signed')=='yes',manager_signed=request.form.get('manager_signed')=='yes',content_matches=request.form.get('content_matches')=='yes',requested_at=request.form.get('requested_at',''),recipient=request.form.get('recipient',''),**common)
            flash('Prüfentscheidung gespeichert. Es wurde keine Nachricht versendet.','success')
        elif action=='handoff':
            service.handoff(db,document_id,directory=Path(current_app.config['DOSSIER_HANDOFF_ROOT']),**common)
            flash('Für Dossier bereitgestellt. Die externe Verarbeitung wird damit nicht bestätigt.','success')
        elif action=='clarify':
            service.clarify_failed_handoff(db,document_id,reason=request.form.get('reason',''),not_delivered=request.form.get('not_delivered')=='yes',**common)
            flash('Übergabe geklärt. Die gespeicherte Unterschriftenprüfung bleibt erhalten.','success')
        else:raise ValueError('Bitte eine gültige Aktion auswählen.')
    except (ValueError,LookupError,OSError) as exc:
        db.rollback();flash(str(exc),'error')
    return redirect(url_for('return_work.detail',document_id=document_id,back=back_link()))
