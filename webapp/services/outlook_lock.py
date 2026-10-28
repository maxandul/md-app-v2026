"""Betriebssystem-Sperre: auch nach Absturz automatisch freigegeben."""
from contextlib import contextmanager
from pathlib import Path
import os
from functools import wraps


def serialized_goal_delivery(function):
    """One cross-process reservation boundary for old and new Outlook routes."""
    @wraps(function)
    def guarded(connection, *args, **kwargs):
        from webapp.migrations import available
        if not available(connection):
            return function(connection, *args, **kwargs)
        database = next(row[2] for row in connection.execute('PRAGMA database_list') if row[1]=='main')
        if not database:
            raise ValueError('Für Outlook wird eine dauerhaft gespeicherte Datenbank benötigt.')
        with package_lock(Path(database).with_suffix('.dispatch')):
            return function(connection, *args, **kwargs)
    return guarded


def check_goal_workflow(connection, case_ids, *, documents=None, exclude=None):
    """All Word routes respect open Outlook work for the selected parts."""
    from webapp.migrations import available
    if not available(connection):
        return
    selected={(d['case_id'],'review' if d['kind']=='probation' else d['kind']) for d in documents} if documents else None
    for case_id in case_ids:
        if selected is not None and (case_id,'review') not in selected:continue
        if connection.execute('''SELECT 1 FROM hr_goal_dispatches d
            JOIN hr_goal_dispatch_outputs m ON m.dispatch_id=d.id
            JOIN hr_goal_outputs o ON o.id=m.output_id
            WHERE o.case_id=? AND d.status IN ('processing','draft_created','failed')''',(case_id,)).fetchone():
            raise ValueError('Für diese Person ist ein Zielnachreichungs-Versand in Outlook offen. Diesen zuerst klären.')
    import json
    for kind,query in (
        ('person',"SELECT id,manifest_json FROM word_person_corrections WHERE status IN ('processing','draft_created','failed')"),
        ('package',"SELECT p.id,p.manifest_json FROM word_dispatch_packages p JOIN word_mail_deliveries d ON d.package_id=p.id WHERE d.status IN ('processing','draft_created','failed')")):
        for row in connection.execute(query):
            if exclude==(kind,row['id']):continue
            for doc in json.loads(row['manifest_json'])['documents']:
                part=(doc['case_id'],'review' if doc['kind']=='probation' else doc['kind'])
                if (selected is not None and part in selected) or (selected is None and doc['case_id'] in case_ids):
                    raise ValueError('Für diesen Gesprächsteil ist ein anderer Outlook-Vorgang offen. Diesen zuerst klären.')

@contextmanager
def package_lock(path):
    lock=Path(str(path)+'.outlook-lock')
    lock.parent.mkdir(parents=True,exist_ok=True)
    handle=lock.open('a+b')
    handle.seek(0,2)
    if handle.tell()==0:handle.write(b'0');handle.flush()
    handle.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        raise ValueError('Dieser Outlook-Vorgang läuft noch. Warte auf dessen Abschluss. Eine laufende Zustellung kann nicht entsperrt werden.') from exc
    try:yield
    finally:
        if os.name=='nt':
            handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
        else:fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
        handle.close()
