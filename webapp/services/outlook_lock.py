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


def check_goal_workflow(connection, case_ids):
    """Legacy routes must respect an active supplementary dispatch or override."""
    from webapp.migrations import available
    if not available(connection):
        return
    for case_id in case_ids:
        if connection.execute('''SELECT 1 FROM hr_goal_dispatches d
            JOIN hr_goal_dispatch_outputs m ON m.dispatch_id=d.id
            JOIN hr_goal_outputs o ON o.id=m.output_id
            WHERE o.case_id=? AND d.status IN ('processing','draft_created','failed')''',(case_id,)).fetchone():
            raise ValueError('Für diese Person ist ein Zielnachreichungs-Versand in Outlook offen. Diesen zuerst klären.')
        if connection.execute('''SELECT 1 FROM hr_part_responsibilities r
            JOIN document_obligations o ON o.id=r.obligation_id
            JOIN dialog_events e ON e.id=o.dialog_event_id WHERE e.legacy_case_id=?''',(case_id,)).fetchone():
            raise ValueError('Abweichende Rückblick-Verantwortung: bitte den Versand unter Zielnachreichungen verwenden.')

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
