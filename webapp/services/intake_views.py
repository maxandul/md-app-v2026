"""Paged intake views, with recognition kept separate from confirmed assignment."""
from datetime import datetime
from . import hr_workflow, hr_views, person_display, return_review


PDF_STATES = {'pending':'Prüfung offen','dismissed':'Zurückgestellt','not_md':'Kein MD-Dokument',
              'imported':'Übernommen','historical':'Zielquelle','duplicate':'Dublette','all':'Alle'}


def date_label(value, with_time=False):
    if not value:return 'Nicht hinterlegt'
    try:return datetime.fromisoformat(str(value).replace('Z','+00:00')).strftime('%d.%m.%Y %H:%M' if with_time else '%d.%m.%Y')
    except ValueError:return str(value)


def counts(db):
    return dict(pdf=db.execute('''SELECT COUNT(*) FROM word_pdf_imports w
        LEFT JOIN workflow_pdf_state s ON s.import_id=w.id
        WHERE w.status='pending' AND COALESCE(s.dismissed,0)=0
        AND NOT EXISTS(SELECT 1 FROM hr_goal_origins o WHERE o.pdf_import_id=w.id)''').fetchone()[0],
        mail=db.execute("SELECT COUNT(*) FROM inbound_mail_messages WHERE (status='review_required' AND review_completed_at='') OR status IN ('failed','new','ready_to_move')").fetchone()[0],
        returns=db.execute('SELECT COUNT(*) FROM hr_return_status WHERE is_current=1 AND NOT complete').fetchone()[0])


def documents(db, **filters):
    value=hr_workflow.pdf_queue(db,**filters)
    value['word_pdf_queue']=[dict(r) for r in value['word_pdf_queue']]
    person_display.enrich(db,value['word_pdf_queue'])
    for row in value['word_pdf_queue']:
        source=db.execute('SELECT source_id FROM hr_goal_origins WHERE pdf_import_id=?',(row['id'],)).fetchone()
        row['goal_source_id']=source['source_id'] if source else None
        row['registered']=bool(row['official_document_id'] and db.execute('SELECT 1 FROM hr_return_reviews WHERE document_id=?',(row['official_document_id'],)).fetchone())
        row['label']='Kein MD-Dokument' if row['classification']=='not_md' else 'Zurückgestellt' if row['dismissed'] else PDF_STATES.get(row['status'],row['status'])
    return value


def returns(db, *, q='',state='open',page=1):
    where=['s.is_current=1'];params=[]
    if state=='open':where.append('NOT s.complete')
    elif state=='done':where.append('s.complete')
    elif state!='all':raise ValueError('Unbekannter Rücklaufstand.')
    if q:
        where.append("p.first_name||' '||p.last_name||' '||d.original_filename||' '||d.employee_pn LIKE ?")
        params.append('%'+q+'%')
    sql='''SELECT d.id,p.first_name,p.last_name,d.employee_pn,d.original_filename,d.document_kind,
        c.employment_assignment,s.manager_pn,o.form_org_unit AS org_unit,d.received_at,s.complete
        FROM hr_return_status s JOIN official_documents d ON d.id=s.document_id
        JOIN persons p ON p.person_number=d.employee_pn JOIN dialog_cases c ON c.case_id=d.case_id
        LEFT JOIN hr_resolved_obligations o ON o.id=d.document_obligation_id WHERE '''+' AND '.join(where)
    value=hr_views.page(db,sql,params,number=page,order='s.complete,d.received_at,d.id')
    person_display.enrich(db,value['rows'])
    for row in value['rows']:
        row['next_action']=return_review.next_action(return_review.view(db,row['id'],include_history=False))
    return value


def employment_choices(db, *, q='',person_number='',employment_id=None):
    where=[];params=[]
    if employment_id is not None:where.append('a.id=?');params.append(employment_id)
    elif person_number:where.append('a.person_number=?');params.append(person_number)
    else:
        where.append("p.first_name||' '||p.last_name||' '||a.person_number LIKE ?")
        params.append('%'+q.strip()+'%')
    rows=[dict(r) for r in db.execute('''SELECT a.id,a.person_number,a.assignment_number,a.org_unit,a.position,
        a.active,p.first_name,p.last_name FROM employment_assignments a JOIN persons p ON p.person_number=a.person_number
        WHERE '''+' AND '.join(where)+' ORDER BY p.last_name,p.first_name,a.org_unit,a.assignment_number LIMIT 25',params)]
    person_display.enrich(db,rows)
    for row in rows:
        managers=list(dict.fromkeys(c['manager_name'] for c in row['current_contexts'] if c['manager_person_number']))
        row['label']=' · '.join(filter(None,[row['first_name']+' '+row['last_name'],row['org_unit'],row['position'],
            'Direkt vorgesetzt: '+', '.join(managers) if managers else 'Aktuelle Führungskraft offen',
            '' if row['active'] else 'Historische Anstellung','Anstellung '+row['assignment_number']]))
    return rows
