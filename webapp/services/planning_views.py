"""Read-only planning context over existing imports, conversations and dispatches."""
import json


def sap_progress(db,batch_id=None):
    where='superseded_by IS NULL';params=[]
    if batch_id is not None:where+=' AND batch_id=?';params.append(batch_id)
    return dict(db.execute('''SELECT COUNT(*) AS people,
        COALESCE(SUM(data_status='pending' AND category<>'unchanged'),0) AS data_open,
        COALESCE(SUM(data_status='applied'),0) AS applied,
        COALESCE(SUM(data_status='applied' AND followup_status='open'),0) AS followup_open,
        COALESCE(SUM(data_status='pending' AND category IN ('conflict','missing','excluded')),0) AS clarify
        FROM hr_sap_changes WHERE '''+where,params).fetchone())


def named_snapshots(db,rows):
    """Names in a preview reflect that export; never write manager assignments."""
    if not rows:return rows
    names={str(r['pn']):(r['first_name']+' '+r['last_name']).strip() for r in db.execute('SELECT pn,first_name,last_name FROM employees')}
    batch_ids=sorted({r['batch_id'] for r in rows})
    placeholders=','.join('?' for _ in batch_ids)
    exported={}
    for r in db.execute('SELECT batch_id,person_number,first_name,last_name FROM hr_sap_changes WHERE batch_id IN ('+placeholders+')',batch_ids):
        exported[(r['batch_id'],r['person_number'])]=(r['first_name']+' '+r['last_name']).strip()
    for row in rows:
        for key in ('before','after'):
            value=row.get(key)
            if value is None:value=json.loads(row[key+'_json']);row[key]=value
            for e in value.get('employments',[]):
                e['manager_names']=[(exported.get((row['batch_id'],pn)) if key=='after' else None) or names.get(pn) or 'Name nicht hinterlegt (Personalnummer '+pn+')' for pn in e.get('managers',[])]
    return rows


def cycle_progress(db,cycle_id):
    counts=dict(db.execute('''SELECT COUNT(*) AS parts,
        COALESCE(SUM(required=1 AND status NOT IN ('complete','waived')),0) AS open_parts
        FROM hr_resolved_obligations WHERE cycle_id=? AND active=1 AND event_status<>'cancelled' AND required=1''',(cycle_id,)).fetchone())
    counts['cases']=db.execute('SELECT COUNT(*) FROM dialog_cases WHERE cycle_id=? AND active=1',(cycle_id,)).fetchone()[0]
    counts['prepared']=db.execute('''SELECT COUNT(*) FROM word_dispatch_packages p WHERE cycle_id=? AND discarded_at=''
        AND id=(SELECT MAX(x.id) FROM word_dispatch_packages x WHERE x.cycle_id=p.cycle_id AND x.manager_pn=p.manager_pn AND x.discarded_at='')''',(cycle_id,)).fetchone()[0]
    counts['sent_managers']=db.execute("SELECT COUNT(DISTINCT p.manager_pn) FROM word_dispatch_packages p JOIN word_mail_deliveries d ON d.package_id=p.id WHERE p.cycle_id=? AND d.status='sent_confirmed'",(cycle_id,)).fetchone()[0]
    return counts
