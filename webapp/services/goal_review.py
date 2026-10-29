"""Canonical goal intake and immutable human revisions for mail and upload."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from .legacy_forms import parse_legacy_form, COMPETENCY_TAGS, MAX_FORM_BYTES
from .part_responsibilities import stamp
from webapp.migrations import available

FIELDS=('title','criteria','steps','target_date','competency')


def dump(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True)


def digest(value):
    return hashlib.sha256(dump(value).encode()).hexdigest()


def event(connection, action, *, source_id=None, case_id=None, dispatch_id=None, user_id=None, **details):
    connection.execute('''INSERT INTO hr_goal_events(source_id,case_id,dispatch_id,action,details_json,user_id,created_at)
        VALUES (?,?,?,?,?,?,?)''',(source_id,case_id,dispatch_id,action,dump(details),user_id,stamp()))


def batch(connection, origin_key, title, mail_message_id=None):
    with connection:
        connection.execute('''INSERT OR IGNORE INTO hr_goal_batches(origin_key,title,mail_message_id,created_at)
            VALUES (?,?,?,?)''',(origin_key,title,mail_message_id,stamp()))
    return connection.execute('SELECT id FROM hr_goal_batches WHERE origin_key=?',(origin_key,)).fetchone()[0]


def stage(connection, path, *, filename, batch_id, origin_key, attachment_id=None, pdf_import_id=None, goal_year=None):
    """Reference the secured original; duplicate bytes always recover the same review."""
    path=Path(path)
    if path.suffix.lower() not in ('.docx','.docm','.pdf') or path.stat().st_size>MAX_FORM_BYTES:
        raise ValueError('Bitte ein Word- oder PDF-Dokument bis 50 MB wählen.')
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    old=connection.execute('SELECT id FROM hr_goal_sources WHERE sha256=?',(sha,)).fetchone()
    extracted=None
    if not old:
        try:
            extracted=parse_legacy_form(path)
            extracted={k:v for k,v in extracted.items() if k!='path'}
        except Exception as exc:
            extracted={'issues':[f'Auslesung fehlgeschlagen: {exc}'],'document_type':'unknown',
                       'performance_goals':[],'development_goals':[]}
        if extracted.get('document_type')!='outlook':
            extracted.setdefault('issues',[]).append('Verwendung als Ausblick am Original prüfen.')
    connection.execute('BEGIN IMMEDIATE')
    try:
        old=connection.execute('SELECT id FROM hr_goal_sources WHERE sha256=?',(sha,)).fetchone()
        if old:
            source_id=old[0]
        else:
            cur=connection.execute('''INSERT INTO hr_goal_sources(sha256,original_filename,stored_path,extraction_json,created_at)
                VALUES (?,?,?,?,?)''',(sha,filename,str(path),dump(extracted),stamp()))
            source_id=cur.lastrowid
            assignments=connection.execute('''SELECT id FROM employment_assignments WHERE person_number=?
                AND (?='' OR assignment_number=?)''',(extracted.get('employee_pn',''),extracted.get('assignment_number',''),extracted.get('assignment_number',''))).fetchall()
            years=extracted.get('detected_years',[])
            year=years[0] if len(years)==1 else goal_year
            connection.execute('''INSERT INTO hr_goal_revisions(source_id,revision,status,employment_id,goal_year,goals_json,created_at)
                VALUES (?,0,'draft',?,?,?,?)''',(source_id,assignments[0][0] if len(assignments)==1 else None,year,
                dump({k:extracted.get(k,[]) for k in ('performance_goals','development_goals')}),stamp()))
            event(connection,'received',source_id=source_id,origin=origin_key)
        connection.execute('INSERT OR IGNORE INTO hr_goal_batch_sources VALUES (?,?)',(batch_id,source_id))
        legacy=connection.execute('SELECT id FROM legacy_form_imports WHERE sha256=?',(sha,)).fetchone()
        connection.execute('''INSERT OR IGNORE INTO hr_goal_origins(source_id,origin_key,attachment_id,pdf_import_id,legacy_import_id)
            VALUES (?,?,?,?,?)''',(source_id,origin_key,attachment_id,pdf_import_id,legacy[0] if legacy else None))
        connection.commit()
        return source_id
    except Exception:
        connection.rollback()
        raise


def get(connection, source_id):
    row=connection.execute('''SELECT s.*,r.id AS revision_id,r.status,r.employment_id,r.goal_year,
        r.goals_json,r.note,r.issues_resolved,r.created_at AS edited_at,
        ea.person_number,ea.assignment_number,ea.org_unit,p.first_name,p.last_name
        FROM hr_goal_sources s JOIN hr_goal_revisions r ON r.source_id=s.id AND r.revision=s.revision
        LEFT JOIN employment_assignments ea ON ea.id=r.employment_id
        LEFT JOIN persons p ON p.person_number=ea.person_number WHERE s.id=?''',(source_id,)).fetchone()
    if not row:
        raise ValueError('Zielquelle nicht gefunden.')
    result=dict(row)
    result['extraction']=json.loads(result['extraction_json'])
    result['goals']=json.loads(result['goals_json'])
    return result


def validate_goals(goals, *, confirmed):
    cleaned={}
    for kind in ('performance_goals','development_goals'):
        rows=goals.get(kind,[])
        if not isinstance(rows,list) or len(rows)>200:
            raise ValueError('Maximal 200 Ziele je Zielart.')
        cleaned[kind]=[]
        for row in rows:
            if not isinstance(row,dict) or any(not isinstance(row.get(k,''),str) or len(row.get(k,''))>50000 for k in FIELDS):
                raise ValueError('Ungültige Zielangaben.')
            row={k:row.get(k,'').replace('\r\n','\n').strip() for k in FIELDS}
            if not any(row.values()):
                continue
            if confirmed and kind=='development_goals' and row['competency'] and row['competency'] not in COMPETENCY_TAGS.values():
                raise ValueError('Bitte jedem Entwicklungsziel eine bekannte Kompetenz zuordnen.')
            cleaned[kind].append(row)
    return cleaned


def sources(connection, employment_id, year):
    from .word_packages import prior_goals
    employment=connection.execute('SELECT * FROM employment_assignments WHERE id=?',(employment_id,)).fetchone()
    if not employment or not year:
        return []
    return prior_goals(connection,employee_pn=employment['person_number'],assignment=employment['assignment_number'],year=year,sources_only=True)


def save(connection, source_id, *, expected_revision, status, employment_id, goal_year, goals,
         note='', checked=False, expected_sources='', user_id=None):
    from .word_packages import goal_sources_fingerprint
    if status not in ('draft','waiting','confirmed','discarded'):
        raise ValueError('Unbekannte Prüfaktion.')
    confirmed=status=='confirmed'
    cleaned=validate_goals(goals,confirmed=confirmed)
    connection.execute('BEGIN IMMEDIATE')
    try:
        previous=get(connection,source_id)
        if previous['revision']!=expected_revision:
            raise ValueError('Diese Zielquelle wurde inzwischen bearbeitet. Bitte neu laden.')
        if employment_id and not connection.execute('SELECT 1 FROM employment_assignments WHERE id=?',(employment_id,)).fetchone():
            raise ValueError('Anstellung nicht gefunden.')
        if goal_year is not None and not 2020<=goal_year<=2100:
            raise ValueError('Bitte ein Zieljahr zwischen 2020 und 2100 wählen.')
        earlier=connection.execute("""SELECT r.* FROM hr_goal_revisions r WHERE source_id=? AND status='confirmed'
            AND NOT EXISTS(SELECT 1 FROM hr_goal_withdrawals w WHERE w.source_id=r.source_id AND w.through_revision>=r.revision)
            ORDER BY revision DESC LIMIT 1""",(source_id,)).fetchone()
        if earlier and (earlier['employment_id']!=employment_id or earlier['goal_year']!=goal_year or status=='discarded'):
            raise ValueError('Für eine andere Person, Anstellung oder ein anderes Zieljahr zuerst die Freigabe zurücknehmen.')
        if confirmed:
            if not checked or not employment_id or not goal_year:
                raise ValueError('Zuordnung, Zieljahr und sämtliche Angaben am Original prüfen und ausdrücklich bestätigen.')
            if not Path(previous['stored_path']).is_file() or hashlib.sha256(Path(previous['stored_path']).read_bytes()).hexdigest()!=previous['sha256']:
                raise ValueError('Das gesicherte Original fehlt oder wurde verändert.')
            before=sources(connection,employment_id,goal_year)
            if goal_sources_fingerprint(before)!=expected_sources:
                raise ValueError('Die vorhandenen Zielquellen haben sich geändert. Bitte erneut vergleichen.')
        revision=expected_revision+1
        connection.execute('UPDATE hr_goal_sources SET revision=? WHERE id=?',(revision,source_id))
        cur=connection.execute('''INSERT INTO hr_goal_revisions(source_id,revision,status,employment_id,goal_year,
            goals_json,note,issues_resolved,user_id,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (source_id,revision,status,employment_id,goal_year,dump(cleaned),note.strip(),int(checked),user_id,stamp()))
        if confirmed:
            all_sources=sources(connection,employment_id,goal_year)
            employment=connection.execute('SELECT * FROM employment_assignments WHERE id=?',(employment_id,)).fetchone()
            connection.execute('''INSERT INTO workflow_goal_choices VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(employee_pn,assignment_number,goal_year) DO UPDATE SET source_json=excluded.source_json,
                sources_fingerprint=excluded.sources_fingerprint,reason=excluded.reason,updated_at=excluded.updated_at''',
                (employment['person_number'],employment['assignment_number'],goal_year,
                 dump({'hr_goal_revision_id':cur.lastrowid,'hr_goal_source_id':source_id}),
                 goal_sources_fingerprint(all_sources),note.strip() or 'Am Original geprüft',stamp()))
        event(connection,status,source_id=source_id,user_id=user_id,revision_id=cur.lastrowid,note=note)
        connection.commit()
        return cur.lastrowid
    except Exception:
        connection.rollback()
        raise


def confirmed_sources(connection, employee_pn, assignment, year):
    if not available(connection):
        return []
    rows=connection.execute('''SELECT r.* FROM hr_goal_revisions r
        JOIN employment_assignments ea ON ea.id=r.employment_id
        WHERE ea.person_number=? AND ea.assignment_number=? AND r.goal_year=? AND r.status='confirmed'
        AND NOT EXISTS(SELECT 1 FROM hr_goal_withdrawals w WHERE w.source_id=r.source_id AND w.through_revision>=r.revision)
        AND r.revision=(SELECT MAX(r2.revision) FROM hr_goal_revisions r2 WHERE r2.source_id=r.source_id AND r2.status='confirmed')
        ORDER BY r.source_id''',(employee_pn,assignment,year)).fetchall()
    return [(json.loads(r['goals_json'])['performance_goals'],json.loads(r['goals_json'])['development_goals'],
             {'hr_goal_revision_id':r['id'],'hr_goal_source_id':r['source_id']}) for r in rows]


def withdrawn(connection,revision_id):
    return bool(connection.execute('''SELECT 1 FROM hr_goal_revisions r JOIN hr_goal_withdrawals w
        ON w.source_id=r.source_id AND w.through_revision>=r.revision WHERE r.id=?''',(revision_id,)).fetchone())


def retired_original(connection,metadata):
    """Do not revive an old raw import after its reviewed assignment was withdrawn."""
    if not available(connection):
        return False
    if metadata.get('legacy_form_import_id'):
        return bool(connection.execute('''SELECT 1 FROM legacy_form_imports l JOIN hr_goal_sources s ON s.sha256=l.sha256
            JOIN hr_goal_withdrawals w ON w.source_id=s.id WHERE l.id=?''',(metadata['legacy_form_import_id'],)).fetchone())
    if metadata.get('word_pdf_import_id'):
        return bool(connection.execute('''SELECT 1 FROM word_pdf_imports p JOIN hr_goal_sources s ON s.sha256=p.sha256
            JOIN hr_goal_withdrawals w ON w.source_id=s.id WHERE p.id=?''',(metadata['word_pdf_import_id'],)).fetchone())
    return False


def assignment_withdrawn(connection,pn,assignment,year):
    if not available(connection):return False
    return bool(connection.execute('''SELECT 1 FROM hr_goal_withdrawals w JOIN hr_goal_revisions r ON r.source_id=w.source_id
        JOIN employment_assignments ea ON ea.id=r.employment_id
        WHERE ea.person_number=? AND ea.assignment_number=? AND r.goal_year=?
        UNION ALL SELECT 1 FROM hr_goal_withdrawals w JOIN hr_goal_sources s ON s.id=w.source_id
        JOIN legacy_form_imports l ON l.sha256=s.sha256 WHERE l.employee_pn=? AND l.assignment_number=? AND l.goal_year=?''',
        (pn,assignment,year,pn,assignment,year)).fetchone())


def stage_mail(connection,message_id):
    message=connection.execute('SELECT * FROM inbound_mail_messages WHERE id=?',(message_id,)).fetchone()
    group=None
    for row in connection.execute('SELECT * FROM inbound_mail_attachments WHERE mail_message_id=?',(message_id,)).fetchall():
        if Path(row['original_filename']).suffix.lower() not in ('.docx','.docm') or not row['stored_path']:
            continue
        if group is None:
            group=batch(connection,f'mail:{message_id}',message['subject'] or 'Nachgereichte Ausblicke',message_id)
        source_id=stage(connection,row['stored_path'],filename=row['original_filename'],batch_id=group,origin_key=f'attachment:{row["id"]}',attachment_id=row['id'])
        # Mail filing is never the completion of the goal workflow.
        with connection:
            connection.execute("UPDATE inbound_mail_attachments SET status='review_required',error_message=? WHERE id=?",
                               (f'Zielprüfung {source_id}: direkt unter Zielnachreichungen bearbeiten.',row['id']))
    return group
