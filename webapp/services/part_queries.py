"""Paged views of existing obligations, not a second task ledger."""
from .part_responsibilities import resolve


def listing(connection,*,q='',manager='',kind='',state='open',year=None,org_unit='',page=1,page_size=25):
    where=["o.document_kind IN ('review','outlook')",'o.required=1'];params=[]
    if q:where.append("o.first_name||' '||o.last_name||' '||o.employee_pn LIKE ?");params.append('%'+q+'%')
    if manager:where.append("o.manager_pn||' '||COALESCE(m.first_name,'')||' '||COALESCE(m.last_name,'') LIKE ?");params.append('%'+manager+'%')
    if kind:where.append('o.document_kind=?');params.append(kind)
    if org_unit:where.append('o.form_org_unit=?');params.append(org_unit)
    if year:
        where.append("COALESCE(substr(o.assigned_period_end,1,4),substr(o.legacy_period_end,1,4),CAST(CASE WHEN o.document_kind='outlook' THEN c.outlook_year ELSE c.review_year END AS TEXT))=?")
        params.append(str(year))
    if state!='all':where.extend(["o.status NOT IN ('complete','waived')","o.event_status<>'cancelled'",'o.active=1'])
    base=''' FROM hr_resolved_obligations o LEFT JOIN employees m ON m.pn=o.manager_pn
        LEFT JOIN cycles c ON c.id=o.cycle_id WHERE '''+' AND '.join(where)
    total=connection.execute('SELECT COUNT(*)'+base,params).fetchone()[0]
    page_size=page_size if page_size in (25,50,100) else 25
    pages=max(1,(total+page_size-1)//page_size);page=min(max(page or 1,1),pages)
    rows=[dict(r) for r in connection.execute('''SELECT o.*,COALESCE(m.first_name||' '||m.last_name,'PN '||o.manager_pn) AS manager_name'''
        +base+' ORDER BY o.last_name,o.first_name,o.employee_pn,o.assignment_number,o.id LIMIT ? OFFSET ?',[*params,page_size,(page-1)*page_size])]
    for row in rows:
        row['part']=resolve(connection,row['case_id'],row['document_kind']) if row['case_id'] else None
    return {'rows':rows,'total':total,'page':page,'pages':pages,'page_size':page_size}


def managers(connection,cycle_id):
    return [dict(r) for r in connection.execute('''WITH cases AS (
        SELECT manager_pn,case_id,COUNT(*) AS parts,
          SUM(status NOT IN ('complete','waived')) AS open_parts,SUM(status='received') AS received
        FROM hr_resolved_obligations WHERE cycle_id=? AND active=1 AND required=1
          AND document_kind IN ('review','outlook') AND event_status<>'cancelled' GROUP BY manager_pn,case_id
    ), summary AS (
        SELECT manager_pn,COUNT(*) AS case_count,SUM(parts) AS part_count,SUM(open_parts=0) AS done_count,
          SUM(received>0 AND open_parts>0) AS progress_count FROM cases GROUP BY manager_pn
    ), scope AS (
        SELECT manager_pn FROM summary UNION SELECT manager_pn FROM package_events WHERE cycle_id=?
        UNION SELECT manager_pn FROM word_dispatch_packages WHERE cycle_id=?
        UNION SELECT manager_pn FROM official_documents WHERE cycle_id=?
    ) SELECT s.manager_pn,COALESCE(m.first_name||' '||m.last_name,'PN '||s.manager_pn) AS manager_name,
      m.email AS manager_email,COALESCE(c.case_count,0) AS case_count,COALESCE(c.part_count,0) AS part_count,
      COALESCE(c.done_count,0) AS done_count,COALESCE(c.progress_count,0) AS progress_count,
      (SELECT MAX(created_at) FROM package_events WHERE cycle_id=? AND manager_pn=s.manager_pn AND direction='versand') AS sent_at,
      (SELECT MAX(received_at) FROM official_documents WHERE cycle_id=? AND manager_pn=s.manager_pn) AS returned_at,
      (SELECT COUNT(*) FROM official_documents WHERE cycle_id=? AND manager_pn=s.manager_pn AND is_current=1 AND variant='digital' AND signature_checked=0) AS signature_check_count,
      (SELECT COUNT(*) FROM official_documents WHERE cycle_id=? AND manager_pn=s.manager_pn AND is_current=1 AND handoff_status='waiting_scan') AS scan_pending_count
    FROM scope s LEFT JOIN summary c ON c.manager_pn=s.manager_pn LEFT JOIN employees m ON m.pn=s.manager_pn
    ORDER BY manager_name,s.manager_pn''',(cycle_id,)*8)]
