"""Betriebssystem-Sperre: auch nach Absturz automatisch freigegeben."""
from contextlib import contextmanager
from pathlib import Path
import os

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
