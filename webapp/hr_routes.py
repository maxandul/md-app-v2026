"""Read-only entry points for the consolidated HR workspace."""
from urllib.parse import urlsplit
from flask import Blueprint, abort, render_template, request, url_for
from .db import get_db
from .goal_routes import protect
from .services import hr_views as views
from .services.dialog_events import EVENT_TYPE_LABELS

bp=Blueprint('hr',__name__)
bp.before_request(protect)

def filters(*names):
    result={key:request.args.get(key,'').strip() for key in names}
    result.update(page_number=request.args.get('page',1,type=int),page_size=request.args.get('page_size',25,type=int))
    return result

def year_filter(values):
    values['year']=request.args.get('year',type=int)
    return values

def back_link(default):
    value=request.args.get('back','');parsed=urlsplit(value)
    return value if value.startswith('/') and not value.startswith('//') and '\\' not in value and not parsed.netloc and not parsed.scheme else default

def render(template, data, **values):
    def page_url(number):
        args=request.args.to_dict();args['page']=number
        return url_for(request.endpoint,**request.view_args,**args)
    return render_template(template,**data,states=views.STATES,page_url=page_url,**values)

def task_link(row):
    target=row['target'];key=row['record_id']
    if target=='goal':return url_for('goal_work.source',source_id=key,back=request.full_path)
    if target=='return':return url_for('return_work.detail',document_id=key,back=request.full_path)
    if target=='pdf':return url_for('main.word_pdf_review',import_id=key)
    if target=='mail':return url_for('main.returns_overview',mail_q=row['context'],mail_status='all')+'#postfach'
    if target=='sap':return url_for('sap_work.index',batch_id=key)
    if target=='unassigned':return url_for('main.dialogs',unassigned='yes')
    if target=='part':
        part=get_db().execute('SELECT case_id,document_kind FROM hr_resolved_obligations WHERE id=?',(key,)).fetchone()
        return url_for('parts.detail',case_id=part['case_id'],kind=part['document_kind'],back=request.full_path)
    if target=='feedback':return url_for('main.feedback_collection',cycle_id=row['cycle_id'],manager_pn=row['manager_pn'])
    if target=='sap_export':return url_for('main.sap_exports',cycle_id=row['cycle_id'])
    return url_for('main.dispatch',cycle_id=row['cycle_id'])

@bp.get('/arbeit')
def work():
    args=year_filter(filters('q','kind','org_unit','manager','due'));args['state']=request.args.get('state','open')
    args['cycle_id']=request.args.get('cycle_id',type=int)
    try:data=views.work(get_db(),**args)
    except ValueError:abort(400,'Unbekannte Arbeitsansicht.')
    for row in data['rows']:row['href']=task_link(row)
    return render('hr/work.html',data,active_nav='work',filters=args,kinds=views.KINDS)

@bp.get('/mitarbeitende')
def people():
    args=filters('q','org_unit');args['state']=request.args.get('state','open')
    return render('hr/directory.html',views.people(get_db(),**args),active_nav='people',filters=args,mode='people',title='Mitarbeitende')

@bp.get('/fuehrungskraefte')
def managers():
    args=filters('q');args['state']=request.args.get('state','open')
    return render('hr/directory.html',views.managers(get_db(),**args),active_nav='managers',filters=args,mode='managers',title='Führungskräfte')

def part_list(person='',manager=''):
    args=year_filter(filters('kind','org_unit'));args['state']=request.args.get('state','open')
    data=views.parts(get_db(),person=person,manager=manager,**args)
    subject=get_db().execute('SELECT first_name,last_name FROM persons WHERE person_number=?',(person or manager,)).fetchone()
    if not subject:abort(404)
    assignments=get_db().execute('SELECT * FROM employment_assignments WHERE person_number=? ORDER BY assignment_number',(person,)).fetchall() if person else []
    return render('hr/parts.html',data,active_nav='people' if person else 'managers',filters=args,subject=subject,person=person,manager=manager,assignments=assignments,event_labels=EVENT_TYPE_LABELS,
        back=back_link(url_for('hr.people' if person else 'hr.managers')))

@bp.get('/mitarbeitende/<pn>')
def person(pn):return part_list(person=pn)

@bp.get('/fuehrungskraefte/<pn>')
def manager(pn):return part_list(manager=pn)

@bp.get('/arbeit/feedback')
def feedback():
    args=year_filter(filters('q','manager'));args['state']=request.args.get('state','all')
    return render('hr/feedback.html',views.feedback(get_db(),**args),active_nav='feedback',filters=args)

@bp.get('/arbeit/uebergaben')
def handoffs():
    args=year_filter(filters('q'));args['state']=request.args.get('state','open')
    data=views.handoffs(get_db(),**args)
    for row in data['rows']:
        if row['target']=='return':row['href']=url_for('return_work.detail',document_id=row['id'],back=request.full_path)
        elif row['target']=='feedback_bundle':row['href']=url_for('main.feedback_bundle_download',bundle_id=row['id'])
        else:row['href']=url_for('main.case_detail',cycle_id=row['cycle_id'],case_id=row['case_id'])
    return render('hr/handoffs.html',data,active_nav='handoffs',filters=args)
