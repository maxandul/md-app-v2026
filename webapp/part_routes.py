"""Part responsibility editing and navigation over existing cases."""
import json
from urllib.parse import urlsplit
from flask import Blueprint,abort,flash,redirect,render_template,request,session,url_for
from .db import get_db
from .goal_routes import protect,actor
from .services import part_responsibilities as parts,part_queries,reminders

bp=Blueprint('parts',__name__,url_prefix='/arbeit/dialogteile')
bp.before_request(protect)


def back_link():
    value=request.values.get('back','');parsed=urlsplit(value)
    return value if not parsed.netloc and not parsed.scheme and '\\' not in value and parsed.path.startswith(('/arbeit','/cycles/','/mitarbeitende','/fuehrungskraefte','/stammdaten/abgleich')) else url_for('parts.index')


def render(template,**values):
    return render_template(template,active_nav='parts',back=back_link(),csrf_token=session['goal_csrf'],**values)


@bp.get('')
def index():
    filters={k:request.args.get(k,'') for k in ('q','manager','kind','org_unit')}
    filters.update(state=request.args.get('state','open'),year=request.args.get('year',type=int),page=request.args.get('page',1,type=int),page_size=request.args.get('page_size',25,type=int))
    return render('parts/index.html',filters=filters,page_url=lambda p:url_for('parts.index',**{**filters,'page':p}),**part_queries.listing(get_db(),**filters))


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
