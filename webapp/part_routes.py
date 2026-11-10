"""Part responsibility editing and navigation over existing cases."""
import json
import secrets
from urllib.parse import urlsplit
from flask import Blueprint,abort,current_app,flash,redirect,render_template,request,session,url_for
from .db import get_db
from .goal_routes import protect,actor
from .services import part_responsibilities as parts,part_queries,reminders,part_actions

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


@bp.route('/<case_id>/<kind>',methods=['GET','POST'])
def detail(case_id,kind):
    db=get_db()
    try:part=parts.resolve(db,case_id,kind)
    except ValueError:abort(404)
    if request.method=='POST':
        try:
            parts.assign(db,case_id,kind=kind,manager_pn=request.form.get('manager_pn',''),form_org_source=request.form.get('form_org_source',''),
                period_start=request.form.get('period_start',''),period_end=request.form.get('period_end',''),expected_revision=request.form.get('revision',type=int),reason=request.form.get('reason',''),user_id=actor())
            flash('Zuständigkeit, Zeitraum und Formular-OE für diesen Gesprächsteil gespeichert. Frühere Dateien und Versandnachweise bleiben erhalten.','success')
        except ValueError as exc:flash(str(exc),'error')
        return redirect(url_for('parts.detail',case_id=case_id,kind=kind,back=back_link()))
    history=[]
    for row in db.execute("SELECT * FROM hr_goal_events WHERE case_id=? AND action='responsibility_changed' ORDER BY id DESC",(case_id,)):
        value=dict(row);value['details']=json.loads(value['details_json'])
        if value['details'].get('kind','review')==kind:history.append(value)
    pending=[dict(r) for r in db.execute('''SELECT r.* FROM reminders r JOIN reminder_obligations ro ON ro.reminder_id=r.id
        WHERE ro.obligation_id=? AND r.status IN ('prepared','draft_created','failed')
        AND NOT EXISTS(SELECT 1 FROM hr_reminder_resolutions rr WHERE rr.reminder_id=r.id) ORDER BY r.id''',(part['obligation_id'],))]
    return render('parts/detail.html',part=part,history=history,pending_reminders=pending)


@bp.post('/erinnerung/<int:reminder_id>')
def resolve_reminder(reminder_id):
    try:reminders.resolve_reminder(get_db(),reminder_id,outcome=request.form.get('outcome'),reason=request.form.get('reason',''),checked=request.form.get('checked')=='yes',user_id=actor())
    except ValueError as exc:flash(str(exc),'error')
    else:flash('Tatsächlicher Erinnerungsstand dokumentiert.','success')
    return redirect(back_link())
