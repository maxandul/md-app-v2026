"""Paged read models over canonical HR objects; no separately closable tasks."""
from datetime import date
from . import goal_queries, part_responsibilities

STATES = {'open':'Zu bearbeiten','waiting':'Warten auf Rückmeldung','done':'Verlauf','all':'Alle'}
KINDS = ('Ziele','Rücklauf','PDF-Prüfung','Postfach','Gesprächsteil','Versand','Feedback','Stammdaten','Zuordnung','SAP-Export')
PART_LABELS = {'review':'Rückblick','outlook':'Ausblick','no_md':'Kein MD'}

def page(db, sql, params=(), *, number=1, size=25, order='1'):
    size = size if size in (25,50,100) else 25
    total = db.execute('SELECT COUNT(*) FROM ('+sql+')', params).fetchone()[0]
    pages = max(1,(total+size-1)//size)
    number = min(max(number or 1,1),pages)
    rows = [dict(r) for r in db.execute(sql+' ORDER BY '+order+' LIMIT ? OFFSET ?', [*params,size,(number-1)*size])]
    return dict(rows=rows,total=total,page=number,pages=pages,page_size=size)

def quoted(value):
    return "'"+value.replace("'","''")+"'"

def task_select(kind, target, record_id, title, subject, source, where='1=1', **fields):
    values=dict(kind=quoted(kind),target=quoted(target),record_id=record_id,title=quoted(title),
        subject=subject,context="''",stamp="''",due_date="''",state="'open'",cycle_id='NULL',
        manager_pn="''",person_number="''",org_unit="''",year='NULL')
    values.update(fields)
    return 'SELECT '+','.join(value+' AS '+key for key,value in values.items())+' FROM '+source+' WHERE '+where

def task_query(db):
    cache={}
    def state(source_id):
        if source_id not in cache:cache[source_id]=goal_queries.source_state(db,source_id)
        return cache[source_id]
    db.create_function('hr_goal_state',1,state)
    statements=[
        task_select('Ziele','goal','s.id','Ziele / Folgeaktion bearbeiten',
            "COALESCE(p.first_name||' '||p.last_name,s.original_filename)",
            'hr_goal_sources s JOIN hr_goal_revisions r ON r.source_id=s.id AND r.revision=s.revision LEFT JOIN employment_assignments e ON e.id=r.employment_id LEFT JOIN persons p ON p.person_number=e.person_number',
            state="CASE hr_goal_state(s.id) WHEN 'done' THEN 'done' WHEN 'waiting' THEN 'waiting' ELSE 'open' END",
            context='s.original_filename',stamp='s.created_at',person_number="COALESCE(e.person_number,'')",org_unit="COALESCE(e.org_unit,'')",year='r.goal_year'),
        task_select('Rücklauf','return','d.id','Nachweis / Bereitstellung bearbeiten',
            "p.first_name||' '||p.last_name",
            'hr_return_status s JOIN official_documents d ON d.id=s.document_id JOIN persons p ON p.person_number=d.employee_pn LEFT JOIN hr_resolved_obligations o ON o.id=d.document_obligation_id JOIN cycles c ON c.id=d.cycle_id',
            'd.is_current=1',
            context="CASE d.document_kind WHEN 'review' THEN 'Rückblick' ELSE 'Ausblick' END",
            state="CASE WHEN s.complete THEN 'done' WHEN s.required AND s.signature_status='requested' AND NOT s.external_open THEN 'waiting' ELSE 'open' END",
            stamp='d.received_at',due_date="COALESCE(o.due_date,'')",cycle_id='d.cycle_id',manager_pn='s.manager_pn',
            person_number='d.employee_pn',org_unit="COALESCE(o.form_org_unit,'')",
            year="CASE d.document_kind WHEN 'outlook' THEN c.outlook_year ELSE c.review_year END"),
        task_select('PDF-Prüfung','pdf','w.id','Eingang am Original prüfen','w.original_filename',
            'word_pdf_imports w LEFT JOIN workflow_pdf_state s ON s.import_id=w.id',
            "w.status='pending' AND COALESCE(s.dismissed,0)=0 AND NOT EXISTS(SELECT 1 FROM hr_goal_origins g WHERE g.pdf_import_id=w.id)",
            stamp='w.created_at'),
        task_select('Postfach','mail','m.id','Zusätzliche Mailanliegen prüfen','m.sender_email','inbound_mail_messages m',
            "(m.status='review_required' AND m.review_completed_at='') OR m.status='failed'",
            context='m.subject',stamp='m.received_at'),
        task_select('Gesprächsteil','part','o.id','Ausstehenden Gesprächsteil bearbeiten',"o.first_name||' '||o.last_name",
            'hr_resolved_obligations o LEFT JOIN cycles c ON c.id=o.cycle_id',
            "o.required=1 AND o.active=1 AND o.event_status<>'cancelled' AND o.status NOT IN ('complete','waived') AND o.case_id IS NOT NULL AND o.document_kind IN ('review','outlook') AND NOT EXISTS(SELECT 1 FROM official_documents d WHERE d.case_id=o.case_id AND d.document_kind=o.document_kind AND d.is_current=1)",
            context="CASE o.document_kind WHEN 'review' THEN 'Rückblick fehlt' ELSE 'Ausblick fehlt' END",
            stamp='o.created_at',due_date='o.due_date',cycle_id='o.cycle_id',manager_pn='o.manager_pn',person_number='o.employee_pn',org_unit='o.form_org_unit',
            year="COALESCE(CAST(substr(o.assigned_period_end,1,4) AS INTEGER),CASE o.document_kind WHEN 'outlook' THEN c.outlook_year ELSE c.review_year END)"),
        task_select('Versand','dispatch','p.id','Word-Versand fortsetzen',"COALESCE(e.first_name||' '||e.last_name,p.manager_pn)",
            'word_dispatch_packages p LEFT JOIN word_mail_deliveries d ON d.package_id=p.id LEFT JOIN employees e ON e.pn=p.manager_pn JOIN cycles c ON c.id=p.cycle_id',
            "p.discarded_at='' AND p.id=(SELECT MAX(x.id) FROM word_dispatch_packages x WHERE x.cycle_id=p.cycle_id AND x.manager_pn=p.manager_pn AND x.discarded_at='')",
            state="CASE WHEN d.status IN ('sent_confirmed','cancelled') THEN 'done' ELSE 'open' END",
            context="COALESCE(d.status,'prepared')",stamp='p.created_at',cycle_id='p.cycle_id',manager_pn='p.manager_pn',year='c.review_year'),
        task_select('Feedback','feedback','s.cycle_id','Feedback bündeln / Nachtrag prüfen',"e.first_name||' '||e.last_name",
            '(SELECT cycle_id,manager_pn,COUNT(*) AS n FROM word_feedback_submissions WHERE bundle_id IS NULL GROUP BY cycle_id,manager_pn) s JOIN employees e ON e.pn=s.manager_pn JOIN cycles c ON c.id=s.cycle_id',
            context="s.n||' geprüfte Eingänge'",cycle_id='s.cycle_id',manager_pn='s.manager_pn',year='c.review_year'),
        task_select('Stammdaten','sap','b.id','SAP-Abgleich und Folgen prüfen','b.original_filename','hr_sap_batches b',
            "EXISTS(SELECT 1 FROM hr_sap_changes x WHERE x.batch_id=b.id AND x.superseded_by IS NULL AND ((x.data_status='pending' AND x.category<>'unchanged') OR x.followup_status='open'))",
            stamp='b.created_at'),
        task_select('Zuordnung','unassigned','d.id','Ereignis einem Durchlauf zuordnen',"p.first_name||' '||p.last_name",
            'dialog_events d JOIN employment_assignments e ON e.id=d.employment_id JOIN persons p ON p.person_number=e.person_number',
            "d.cycle_id IS NULL AND d.status<>'cancelled'",stamp='d.created_at',person_number='e.person_number',org_unit='e.org_unit',year='d.review_year'),
        task_select('SAP-Export','sap_export','c.id','SAP-Export prüfen',"c.review_year||'/'||c.outlook_year",'cycles c',
            "EXISTS(SELECT 1 FROM dialog_cases d JOIN dialog_events e ON e.legacy_case_id=d.case_id WHERE d.cycle_id=c.id AND d.status='vollstaendig' AND d.official_scope IN ('full','review_only') AND e.sap_leading=1 AND NOT EXISTS(SELECT 1 FROM sap_export_rows r WHERE r.dialog_event_id=e.id))",
            stamp='c.created_at',cycle_id='c.id',year='c.review_year')
    ]
    return ' UNION ALL '.join(statements)

def work(db, *, q='', state='open', kind='', year=None, org_unit='', manager='', due='', cycle_id=None, page_number=1, page_size=25):
    where=[];params=[]
    if state in ('open','waiting','done'):where.append('state=?');params.append(state)
    elif state!='all':raise ValueError('Unbekannte Arbeitsansicht.')
    if cycle_id:where.append('cycle_id=?');params.append(cycle_id)
    if kind:where.append('kind=?');params.append(kind)
    if q:where.append("subject||' '||context||' '||person_number LIKE ?");params.append('%'+q+'%')
    if year:where.append('year=?');params.append(year)
    if org_unit:where.append('org_unit=?');params.append(org_unit)
    if manager:where.append('manager_pn=?');params.append(manager)
    if due=='overdue':where.append("state<>'done' AND due_date<>'' AND due_date<?");params.append(date.today().isoformat())
    elif due=='dated':where.append("due_date<>''")
    sql='SELECT * FROM ('+task_query(db)+')'+(' WHERE '+' AND '.join(where) if where else '')
    return page(db,sql,params,number=page_number,size=page_size,order="CASE WHEN due_date<>'' THEN 0 ELSE 1 END,due_date,stamp,kind,record_id,manager_pn")

def people(db, *, q='', org_unit='', state='open', page_number=1, page_size=25):
    where=[];params=[]
    if q:where.append("p.first_name||' '||p.last_name||' '||p.person_number LIKE ?");params.append('%'+q+'%')
    if org_unit:where.append('EXISTS(SELECT 1 FROM employment_assignments e WHERE e.person_number=p.person_number AND e.org_unit=?)');params.append(org_unit)
    if state=='open':where.append("EXISTS(SELECT 1 FROM hr_resolved_obligations o WHERE o.employee_pn=p.person_number AND o.required=1 AND o.active=1 AND o.event_status<>'cancelled' AND o.status NOT IN ('complete','waived'))")
    sql="""SELECT p.*,(SELECT COUNT(*) FROM employment_assignments e WHERE e.person_number=p.person_number) AS assignments,
        (SELECT COUNT(*) FROM hr_resolved_obligations o WHERE o.employee_pn=p.person_number AND o.required=1 AND o.active=1 AND o.event_status<>'cancelled' AND o.status NOT IN ('complete','waived')) AS open_parts
        FROM persons p"""+(' WHERE '+' AND '.join(where) if where else '')
    return page(db,sql,params,number=page_number,size=page_size,order='last_name,first_name,person_number')

def managers(db, *, q='', state='open', page_number=1, page_size=25):
    sql="""WITH scope AS (SELECT manager_pn FROM hr_resolved_obligations UNION SELECT manager_pn FROM word_feedback_submissions UNION SELECT manager_pn FROM feedback_bundles),
    rows AS (SELECT s.manager_pn,COALESCE(e.first_name,'') AS first_name,COALESCE(e.last_name,s.manager_pn) AS last_name,
       (SELECT COUNT(*) FROM hr_resolved_obligations o WHERE o.manager_pn=s.manager_pn AND o.required=1 AND o.active=1 AND o.event_status<>'cancelled' AND o.status NOT IN ('complete','waived')) AS open_parts,
       (SELECT COUNT(*) FROM word_feedback_submissions f WHERE f.manager_pn=s.manager_pn AND f.bundle_id IS NULL) AS feedback_pending
       FROM scope s LEFT JOIN employees e ON e.pn=s.manager_pn)
       SELECT * FROM rows WHERE 1=1"""
    params=[]
    if state=='open':sql+=' AND (open_parts>0 OR feedback_pending>0)'
    if q:sql+=" AND first_name||' '||last_name||' '||manager_pn LIKE ?";params.append('%'+q+'%')
    return page(db,sql,params,number=page_number,size=page_size,order='open_parts=0,last_name,first_name,manager_pn')

def parts(db, *, person='', manager='', year=None, state='open', kind='', org_unit='', page_number=1, page_size=25):
    where=["o.document_kind IN ('review','outlook')"];params=[]
    for key,value in (('o.employee_pn',person),('o.manager_pn',manager),('o.document_kind',kind),('o.form_org_unit',org_unit)):
        if value:where.append(key+'=?');params.append(value)
    if state=='open':where.extend(["o.required=1","o.active=1","o.event_status<>'cancelled'","o.status NOT IN ('complete','waived')"])
    if year:
        where.append("COALESCE(CAST(NULLIF(substr(o.assigned_period_end,1,4),'') AS INTEGER),CASE o.document_kind WHEN 'outlook' THEN c.outlook_year ELSE c.review_year END)=?")
        params.append(year)
    sql="""SELECT o.*,c.review_year,c.outlook_year FROM hr_resolved_obligations o LEFT JOIN cycles c ON c.id=o.cycle_id WHERE """+' AND '.join(where)
    result=page(db,sql,params,number=page_number,size=page_size,order="o.status IN ('complete','waived'),c.review_year DESC,o.last_name,o.first_name,o.assignment_number,o.id")
    for row in result['rows']:
        row['part']=part_responsibilities.resolve(db,row['case_id'],row['document_kind']) if row['case_id'] else None
    return result

def feedback(db, *, q='', manager='', year=None, state='all', page_number=1, page_size=25):
    sql="""WITH scope AS (
        SELECT cycle_id,manager_pn FROM dialog_cases
        UNION SELECT cycle_id,manager_pn FROM word_feedback_submissions
        UNION SELECT cycle_id,manager_pn FROM feedback_bundles
    ), rows AS (
        SELECT s.*,c.review_year,COALESCE(e.first_name,'') AS first_name,COALESCE(e.last_name,s.manager_pn) AS last_name,
        (SELECT COUNT(*) FROM word_feedback_submissions f WHERE f.cycle_id=s.cycle_id AND f.manager_pn=s.manager_pn AND f.bundle_id IS NULL) AS pending,
        (SELECT COUNT(*) FROM word_feedback_submissions f WHERE f.cycle_id=s.cycle_id AND f.manager_pn=s.manager_pn AND f.bundle_id IS NOT NULL) AS bundled,
        (SELECT COUNT(*) FROM feedback_bundles b WHERE b.cycle_id=s.cycle_id AND b.manager_pn=s.manager_pn) AS bundles
        FROM scope s JOIN cycles c ON c.id=s.cycle_id LEFT JOIN employees e ON e.pn=s.manager_pn
    ) SELECT * FROM rows WHERE 1=1"""
    params=[]
    if q:sql+=" AND first_name||' '||last_name||' '||manager_pn LIKE ?";params.append('%'+q+'%')
    if manager:sql+=' AND manager_pn=?';params.append(manager)
    if year:sql+=' AND review_year=?';params.append(year)
    if state=='open':sql+=' AND pending>0'
    return page(db,sql,params,number=page_number,size=page_size,order='pending=0,review_year DESC,last_name,first_name,cycle_id,manager_pn')

def handoffs(db, *, q='', state='open', year=None, page_number=1, page_size=25):
    sql="""WITH rows AS (
        SELECT d.id,d.document_kind AS kind,d.cycle_id,d.case_id,d.employee_pn AS pn,
        e.first_name||' '||e.last_name AS subject,d.received_at AS stamp,d.handoff_filename AS filename,
        CASE WHEN r.document_id IS NOT NULL THEN 'return' ELSE 'case' END AS target,
        CASE WHEN r.document_id IS NOT NULL THEN r.complete ELSE d.handoff_status='staged' END AS complete,
        CASE WHEN r.external_open THEN 'Externe Ablage klären' WHEN h.status IN ('processing','uncertain') THEN 'Übergabeausgang klären'
            WHEN r.document_id IS NOT NULL AND NOT r.signature_ready THEN 'Unterschriftennachweis offen'
            WHEN d.handoff_status='staged' THEN 'Lokal bereitgestellt' ELSE 'Bereitstellung offen' END AS label,
        CASE d.document_kind WHEN 'outlook' THEN c.outlook_year ELSE c.review_year END AS year
        FROM official_documents d JOIN employees e ON e.pn=d.employee_pn JOIN cycles c ON c.id=d.cycle_id
        LEFT JOIN hr_return_status r ON r.document_id=d.id LEFT JOIN hr_return_handoffs h ON h.document_id=d.id
        WHERE d.is_current=1 AND NOT EXISTS(SELECT 1 FROM hr_return_evidence x WHERE x.legacy_document_id=d.id)
        UNION ALL SELECT b.id,'feedback',b.cycle_id,'',b.manager_pn,e.first_name||' '||e.last_name,b.created_at,b.filename,
            'feedback_bundle',1,'Lokal bereitgestellt',c.review_year FROM feedback_bundles b
            JOIN employees e ON e.pn=b.manager_pn JOIN cycles c ON c.id=b.cycle_id
    ) SELECT * FROM rows WHERE 1=1"""
    params=[]
    if state=='open':sql+=' AND NOT complete'
    elif state=='done':sql+=' AND complete'
    if q:sql+=" AND subject||' '||pn||' '||filename LIKE ?";params.append('%'+q+'%')
    if year:sql+=' AND year=?';params.append(year)
    return page(db,sql,params,number=page_number,size=page_size,order='complete,stamp DESC,kind,id')

def operational_counts(db, *, cycle_id=None, org_unit='', event_type=''):
    where=["o.required=1","o.event_status<>'cancelled'","o.document_kind IN ('review','outlook')"];params=[]
    for key,value in (('o.cycle_id',cycle_id),('o.employee_org_unit',org_unit),('o.event_type',event_type)):
        if value:where.append(key+'=?');params.append(value)
    return [dict(r) for r in db.execute("""SELECT o.document_kind,o.form_org_unit,o.status,COUNT(*) AS count
        FROM hr_resolved_obligations o WHERE """+' AND '.join(where)+' GROUP BY o.document_kind,o.form_org_unit,o.status ORDER BY o.form_org_unit,o.document_kind,o.status',params)]
