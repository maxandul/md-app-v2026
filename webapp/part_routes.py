"""Part responsibility editing and navigation over existing cases."""
import json
import secrets
import hashlib
from itsdangerous import URLSafeTimedSerializer,BadSignature
from urllib.parse import urlsplit
from flask import Blueprint,abort,current_app,flash,redirect,render_template,request,session,url_for
from .db import get_db
from .goal_routes import protect,actor
from .services import part_responsibilities as parts,part_queries,reminders,part_actions,part_changes,part_change_links
from .services.intake_views import date_label

bp=Blueprint('parts',__name__,url_prefix='/arbeit/dialogteile')
bp.before_request(protect)


def back_link():
    value=request.values.get('back','');parsed=urlsplit(value)
    return value if not parsed.netloc and not parsed.scheme and '\\' not in value and parsed.path.startswith(('/start','/arbeit','/cycles/','/mitarbeitende','/fuehrungskraefte','/stammdaten/abgleich')) else url_for('parts.index')


def render(template,**values):
    return render_template(template,active_nav='parts',back=back_link(),csrf_token=session['goal_csrf'],**values)


def list_filters(values):
    result={k:values.get(k,'') for k in ('q','manager','kind','org_unit','due')}
    result['perspective']='managers' if values.get('perspective')=='managers' else 'people'
    result.update(state=values.get('state','open'),year=values.get('year',type=int),
        page=values.get('page',1,type=int),page_size=values.get('page_size',25,type=int))
    return result


def selection_owner():
    session.setdefault('part_selection_owner',secrets.token_urlsafe(32))
    return session['part_selection_owner']


@bp.get('')
def index():
    filters=list_filters(request.args)
    chosen=None
    if request.args.get('selection'):
        try:chosen=part_actions.selection(get_db(),request.args['selection'],selection_owner(),filters)
        except ValueError as exc:flash(str(exc),'error')
    return render('parts/index.html',filters=filters,selection=chosen,
        page_url=lambda p:url_for('parts.index',**{**filters,'page':p},selection=chosen['id'] if chosen else ''),
        **part_queries.listing(get_db(),**filters))


@bp.post('/auswahl')
def select_parts():
    filters=list_filters(request.form)
    chosen=None
    mode=request.form.get('mode','page')
    try:
        chosen=part_actions.select(get_db(),owner=selection_owner(),filters=filters,
            key=request.form.get('selection',''),revision=request.form.get('revision',0,type=int),
            mode='page' if mode=='preview' else mode,checked=request.form.getlist('part'))
        if mode=='preview':
            key=part_actions.preview(get_db(),owner=selection_owner(),selection_id=chosen['id'],revision=chosen['revision'],
                action=request.form.get('action'),new_due_date=request.form.get('new_due_date',''),
                reason=request.form.get('reason',''),sender_email=current_app.config['HR_MAILBOX_EMAIL'])
            back=url_for('parts.index',**filters,selection=chosen['id'])
            return redirect(url_for('parts.action_preview',key=key,back=back))
    except ValueError as exc:
        flash(str(exc),'error')
        return redirect(url_for('parts.index',**filters,selection=chosen['id'] if chosen else request.form.get('selection','')))
    filters['page']=request.form.get('next_page',filters['page'],type=int)
    return redirect(url_for('parts.index',**filters,selection=chosen['id']))


@bp.post('/vorschau')
def preview_action():
    try:
        key=part_actions.preview(get_db(),owner=selection_owner(),selection_id=request.form.get('selection',''),
            revision=request.form.get('revision',type=int),action=request.form.get('action'),
            new_due_date=request.form.get('new_due_date',''),reason=request.form.get('reason',''),
            sender_email=current_app.config['HR_MAILBOX_EMAIL'])
    except ValueError as exc:
        flash(str(exc),'error')
        return redirect(back_link())
    return redirect(url_for('parts.action_preview',key=key,back=back_link()))


@bp.route('/aktionen/<key>',methods=['GET','POST'])
def action_preview(key):
    try:batch=part_actions.view(get_db(),key,selection_owner())
    except ValueError:abort(404)
    if request.method=='POST':
        if request.form.get('checked')!='yes':
            flash('Bitte die Vorschau ausdrücklich prüfen und bestätigen.','error')
        elif current_app.config.get('HR_REVIEW_SANDBOX') and batch['plan']['action']=='reminder':
            abort(403,'HR-Test: Outlook-Zugriff bleibt gesperrt.')
        else:
            try:
                result=part_actions.execute(get_db(),key,owner=selection_owner(),
                    sender_email=current_app.config['HR_MAILBOX_EMAIL'],user_id=actor())
                summary=(str(result['changed'])+' Frist(en) geändert. ' if 'changed' in result else
                    str(result['created'])+' Entwurf/-entwürfe erstellt · '+str(result['failed'])+' fehlgeschlagen. ')
                flash(summary+result['message'],'error' if result.get('errors') else 'success')
            except ValueError as exc:flash(str(exc),'error')
        return redirect(url_for('parts.action_preview',key=key,back=back_link()))
    try:chosen=part_actions.selection(get_db(),batch['selection_id'],selection_owner())
    except ValueError:chosen=None
    def page_rows(excluded):
        rows=[r for r in batch['plan']['rows'] if bool(r['exclusion'])==excluded]
        key='excluded_page' if excluded else 'eligible_page'
        pages=max(1,(len(rows)+49)//50)
        page=min(max(request.args.get(key,1,type=int),1),pages)
        def href(number):
            args=request.args.to_dict();args[key]=number
            return url_for('parts.action_preview',key=batch['id'],**{k:v for k,v in args.items() if k!='key'})
        return dict(rows=rows[(page-1)*50:page*50],total=len(rows),page=page,pages=pages,page_url=href)
    from .services.hr_workflow import pending_pdfs
    pending_inputs=pending_pdfs(get_db()) if batch['plan']['action']=='reminder' else []
    return render('parts/action_preview.html',batch=batch,selection=chosen,pending_inputs=pending_inputs,
        included=page_rows(False),excluded=page_rows(True))


def change_signer():return URLSafeTimedSerializer(current_app.secret_key,salt='md-part-change')


def change_proof(token,case_id,kind):
    proof=change_signer().loads(token,max_age=3600)
    if proof['owner']!=session.get('part_change_owner') or proof['case_id']!=case_id or proof['kind']!=kind:
        raise ValueError('Diese Vorschau gehört zu einer anderen Auswahl oder Sitzung.')
    return proof


@bp.route('/<case_id>/<kind>',methods=['GET','POST'])
def detail(case_id,kind):
    db=get_db()
    try:current=part_changes.context(db,case_id,kind)
    except ValueError:abort(404)
    part=current['part']
    session.setdefault('part_change_owner',secrets.token_urlsafe(32))
    values={k:part[k] for k in ('manager_pn','form_org_source','period_start','period_end')};values['reason']=''
    def show_preview(proposal,revision):
        preview=part_changes.plan(db,case_id,kind=kind,expected_revision=revision,**proposal)
        token=change_signer().dumps({'owner':session['part_change_owner'],'case_id':case_id,'kind':kind,
            'revision':part['responsibility_revision'],'proposal':proposal,'fingerprint':preview['fingerprint'],'nonce':secrets.token_urlsafe(24)})
        part_change_links.enrich(db,preview,url_for('parts.detail',case_id=case_id,kind=kind,back=back_link()))
        return render('parts/change_preview.html',plan=preview,token=token,date_label=date_label)
    if request.method=='POST':
        action=request.form.get('action','preview')
        try:
            if action in ('apply','edit','refresh'):
                proof=change_proof(request.form.get('change_token',''),case_id,kind)
                values=proof['proposal']
                if action=='refresh':
                    flash('Aktuellen Stand neu eingelesen. Bitte diese Vorschau erneut prüfen.','info')
                    return show_preview(values,part['responsibility_revision'])
                if action=='apply':
                    if request.form.get('checked')!='yes':raise ValueError('Bitte den konkret beschriebenen Ersatz dieser Teilzuständigkeit prüfen und bestätigen.')
                    event_id=parts.assign(db,case_id,kind=kind,expected_revision=proof['revision'],user_id=actor(),
                        expected_change_context=proof['fingerprint'],change_request=hashlib.sha256(request.form['change_token'].encode()).hexdigest(),**values)
                    flash('Zuordnung dieses Gesprächsteils gespeichert. Die bisherige Zuständigkeit dafür ist abgelöst; die anderen Teile, frühere Dateien und Versandnachweise bleiben erhalten.','success')
                    return redirect(url_for('parts.detail',case_id=case_id,kind=kind,back=back_link(),changed=event_id))
            elif action=='preview':
                values={k:request.form.get(k,'') for k in values}
                return show_preview(values,request.form.get('revision',type=int))
            else:raise ValueError('Unbekannte Änderungsaktion.')
        except (BadSignature,KeyError,TypeError,ValueError) as exc:flash(str(exc) or 'Vorschau abgelaufen. Bitte neu prüfen.','error')
        current=part_changes.context(db,case_id,kind);part=current['part']
    history=part_changes.history(db,case_id,kind)
    selected=db.execute('SELECT first_name,last_name,org_unit FROM employees WHERE pn=?',(values['manager_pn'],)).fetchone()
    manager_label=(selected['first_name']+' '+selected['last_name']+' · '+selected['org_unit']) if selected else 'Auswahl erneut prüfen'
    changed_event=next((r for r in history if r['id']==request.args.get('changed',type=int)),None)
    pending=[r for r in current['effects']['reminders'] if r['status'] in ('prepared','draft_created','failed') and not r['resolution']]
    part_change_links.enrich(db,current,request.full_path)
    return render('parts/detail.html',part=part,context=current,values=values,manager_label=manager_label,
        history=history,pending_reminders=pending,date_label=date_label,changed_event=changed_event,
        additions=[json.loads(r[0]) for r in db.execute("SELECT details_json FROM hr_goal_events WHERE action='additional_conversation_created' AND case_id=? ORDER BY id DESC",(case_id,))])


@bp.post('/erinnerung/<int:reminder_id>')
def resolve_reminder(reminder_id):
    try:reminders.resolve_reminder(get_db(),reminder_id,outcome=request.form.get('outcome'),reason=request.form.get('reason',''),checked=request.form.get('checked')=='yes',user_id=actor())
    except ValueError as exc:flash(str(exc),'error')
    else:flash('Tatsächlicher Erinnerungsstand dokumentiert.','success')
    return redirect(back_link())


@bp.route('/<case_id>/zusaetzlich',methods=['GET','POST'])
def additional(case_id):
    from .services import additional_conversations as additions
    db=get_db()
    try:context=additions.context(db,case_id)
    except ValueError as exc:flash(str(exc),'error');return redirect(back_link())
    first=context['parts'][0]['part']
    session.setdefault('additional_owner',secrets.token_urlsafe(32))
    signer=URLSafeTimedSerializer(current_app.secret_key,salt='md-additional-conversation')
    values=dict(manager_pn=first['manager_pn'],event_type='interim',required_scope='review_only',
        period_start=first['period_start'],period_end=first['period_end'],review_due_date='',outlook_due_date='',
        form_org_source='employee',disposition='',reason='')
    def preview():
        plan=additions.plan(db,case_id,values)
        token=signer.dumps({'owner':session['additional_owner'],'case_id':case_id,'proposal':values,
            'fingerprint':plan['fingerprint'],'nonce':secrets.token_urlsafe(24)})
        for c in plan['parts']:part_change_links.enrich(db,c,back_link())
        return render('parts/additional_preview.html',plan=plan,token=token,types=additions.TYPES,scopes=additions.SCOPES,date_label=date_label)
    if request.method=='POST':
        action=request.form.get('action','preview')
        try:
            if action in ('apply','edit','refresh'):
                proof=signer.loads(request.form.get('change_token',''),max_age=3600)
                if proof['owner']!=session['additional_owner'] or proof['case_id']!=case_id:raise ValueError('Diese Vorschau gehört zu einer anderen Sitzung oder Person.')
                values=proof['proposal']
                if action=='refresh':return preview()
                if action=='apply':
                    if request.form.get('checked')!='yes':raise ValueError('Bitte den neuen Auftrag und die Entscheidung zum bisherigen Auftrag prüfen.')
                    new_id=additions.apply(db,case_id,values,expected=proof['fingerprint'],
                        request_key=hashlib.sha256(request.form['change_token'].encode()).hexdigest(),user_id=actor())
                    return redirect(url_for('parts.additional_result',case_id=case_id,new_case_id=new_id,back=back_link()))
            elif action=='preview':
                values={k:request.form.get(k,'') for k in values}
                return preview()
            else:raise ValueError('Unbekannte Aktion.')
        except (BadSignature,ValueError,KeyError,TypeError) as exc:flash(str(exc) or 'Vorschau abgelaufen. Bitte neu prüfen.','error')
    for c in context['parts']:part_change_links.enrich(db,c,back_link())
    manager=db.execute('SELECT first_name,last_name,org_unit FROM employees WHERE pn=?',(values['manager_pn'],)).fetchone()
    return render('parts/additional.html',context=context,values=values,types=additions.TYPES,scopes=additions.SCOPES,
        manager_label=(manager['first_name']+' '+manager['last_name']+' · '+manager['org_unit']) if manager else 'Auswahl erneut prüfen',date_label=date_label)


@bp.get('/<case_id>/zusaetzlich/<new_case_id>')
def additional_result(case_id,new_case_id):
    row=get_db().execute("SELECT details_json FROM hr_goal_events WHERE case_id=? AND action='additional_conversation_created' AND json_extract(details_json,'$.new_case_id')=?",(case_id,new_case_id)).fetchone()
    if not row:abort(404)
    details=json.loads(row[0])
    return render('parts/additional_result.html',details=details,new_parts=parts.case_parts(get_db(),new_case_id),date_label=date_label)
