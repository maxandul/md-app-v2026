"""A paged shipping ledger over existing records; it grants no new approvals."""
from .hr_views import page

LABELS = {'prepared':'Dateien erstellt – noch kein Outlook-Entwurf',
          'processing':'Outlook-Ausgang unklar – zuerst prüfen',
          'draft_created':'Outlook-Entwurf erstellt – Versand unbestätigt',
          'failed':'Versuch fehlgeschlagen – Outlook prüfen',
          'sent_confirmed':'Versand dieser Ausgabe bestätigt', 'cancelled':'Vorgang verworfen'}
KINDS = {'regular':'Reguläres Paket','person':'Einzelausgabe','goals':'Nachgereichte Ziele'}


def listing(db, *, q='',state='open',kind='',year=None,page_number=1):
    query='''SELECT 'regular' AS kind,p.id,p.cycle_id,'' AS case_id,p.manager_pn,
        COALESCE(d.recipient_email,m.email,'') AS recipient_email,
        COALESCE(m.first_name||' '||m.last_name,'Name nicht hinterlegt') AS manager_name,
        COALESCE(m.org_unit,'') AS org_unit,'Vorlagen für den Durchlauf' AS context,
        COALESCE(d.status,CASE WHEN p.discarded_at<>'' THEN 'cancelled' ELSE 'prepared' END) AS status,COALESCE(d.updated_at,p.created_at) AS stamp,
        c.review_year||'/'||c.outlook_year AS years,json_array(c.review_year) AS review_years,
        (p.discarded_at='' AND p.id=(SELECT MAX(x.id) FROM word_dispatch_packages x
            WHERE x.cycle_id=p.cycle_id AND x.manager_pn=p.manager_pn AND x.discarded_at='')) AS current,
        (SELECT x.id FROM word_dispatch_packages x JOIN word_mail_deliveries sent ON sent.package_id=x.id
            WHERE x.cycle_id=p.cycle_id AND x.manager_pn=p.manager_pn AND sent.status='sent_confirmed'
            ORDER BY sent.updated_at DESC,x.id DESC LIMIT 1) AS last_sent_id,
        p.discarded_at
        FROM word_dispatch_packages p JOIN cycles c ON c.id=p.cycle_id
        LEFT JOIN employees m ON m.pn=p.manager_pn LEFT JOIN word_mail_deliveries d ON d.package_id=p.id
        UNION ALL SELECT 'person',p.id,c.cycle_id,p.case_id,
        json_extract(p.manifest_json,'$.manager_pn'),p.recipient_email,
        COALESCE(m.first_name||' '||m.last_name,'Name nicht hinterlegt'),COALESCE(m.org_unit,''),
        e.first_name||' '||e.last_name,p.status,p.updated_at,
        cy.review_year||'/'||cy.outlook_year,json_array(cy.review_year),1,NULL,''
        FROM word_person_corrections p JOIN dialog_cases c ON c.case_id=p.case_id
        JOIN cycles cy ON cy.id=c.cycle_id JOIN persons e ON e.person_number=c.employee_pn
        LEFT JOIN employees m ON m.pn=json_extract(p.manifest_json,'$.manager_pn')
        UNION ALL SELECT 'goals',g.id,NULL,'',g.manager_pn,g.recipient_email,
        COALESCE(m.first_name||' '||m.last_name,'Name nicht hinterlegt'),COALESCE(m.org_unit,''),
        'Rückblicke mit nachgereichten Zielen',g.status,g.updated_at,
        (SELECT group_concat(DISTINCT cy.review_year||'/'||cy.outlook_year)
            FROM hr_goal_dispatch_outputs x JOIN hr_goal_outputs o ON o.id=x.output_id
            JOIN dialog_cases c ON c.case_id=o.case_id JOIN cycles cy ON cy.id=c.cycle_id WHERE x.dispatch_id=g.id),
        (SELECT json_group_array(DISTINCT cy.review_year)
            FROM hr_goal_dispatch_outputs x JOIN hr_goal_outputs o ON o.id=x.output_id
            JOIN dialog_cases c ON c.case_id=o.case_id JOIN cycles cy ON cy.id=c.cycle_id WHERE x.dispatch_id=g.id),
        1,NULL,'' FROM hr_goal_dispatches g LEFT JOIN employees m ON m.pn=g.manager_pn'''
    where=[];params=[]
    if state=='open':where.extend(["status NOT IN ('sent_confirmed','cancelled')",'current=1'])
    elif state=='sent':where.append("status='sent_confirmed'")
    elif state=='clarify':where.append("status IN ('processing','failed')")
    elif state!='all':raise ValueError('Unbekannter Versandstand.')
    if kind:
        if kind not in KINDS:raise ValueError('Unbekannte Versandart.')
        where.append('kind=?');params.append(kind)
    if q:
        where.append("manager_name||' '||recipient_email||' '||org_unit||' '||context LIKE ?")
        params.append('%'+q.strip()+'%')
    if year:where.append('EXISTS(SELECT 1 FROM json_each(review_years) WHERE value=?)');params.append(year)
    sql='SELECT * FROM ('+query+')'+(' WHERE '+' AND '.join(where) if where else '')
    return page(db,sql,params,number=page_number,order='stamp DESC,kind,id DESC')
