"""Optional hourly inbox scans, independent of open browser windows."""
from datetime import datetime
import json
import os
from pathlib import Path
from threading import Event, Thread

from webapp.db import get_db
from .mail_intake import scan_outlook_inbox
from .outlook_lock import package_lock


def schedule_state(connection):
    return dict(connection.execute('SELECT * FROM mail_scan_schedule WHERE id=1').fetchone())


def due_slot(now):
    # Server's local Windows time; Outlook runs in this same user session.
    if now.weekday() < 5 and 7 <= now.hour <= 17 and now.minute == 30:
        return now.strftime('%Y-%m-%dT%H:30')
    return ''


def run_scan(app, *, automatic=False, now=None):
    now = now or datetime.now().astimezone()
    connection = get_db()
    with package_lock(Path(app.config['DATABASE']).with_suffix('.mail-scan')):
        state = schedule_state(connection)
        slot = due_slot(now)
        if automatic and (not state['enabled'] or not slot or state['last_slot'] == slot):
            return None
        started = now.isoformat(timespec='seconds')
        connection.execute("UPDATE mail_scan_schedule SET last_slot=?, last_started=?, last_finished='', last_error='', last_result='' WHERE id=1",
                           (slot if automatic else state['last_slot'], started))
        connection.commit()
        try:
            root = Path(app.config['STORAGE_ROOT'])
            result = scan_outlook_inbox(connection,
                mailbox_name=app.config['OUTLOOK_MAILBOX_NAME'],
                target_folder=app.config['OUTLOOK_TARGET_FOLDER'],
                inbox_dir=root / 'mail_inbox', pdf_dir=root / 'pdf_processed',
                handoff_dir=Path(app.config['DOSSIER_HANDOFF_ROOT']))
        except Exception as exc:
            connection.rollback()
            connection.execute("UPDATE inbound_mail_messages SET status='failed', error_message=? WHERE status='new'", (str(exc),))
            connection.execute('UPDATE mail_scan_schedule SET last_finished=?, last_error=? WHERE id=1',
                               (datetime.now().astimezone().isoformat(timespec='seconds'), str(exc)))
            connection.commit()
            raise
        connection.execute('UPDATE mail_scan_schedule SET last_finished=?, last_error=?, last_result=? WHERE id=1',
                           (datetime.now().astimezone().isoformat(timespec='seconds'), '\n'.join(result['errors']), json.dumps(result)))
        connection.commit()
        return result


def start_worker(app):
    if app.testing or os.name != 'nt':
        return
    stop = Event()
    def worker():
        while not stop.wait(15):
            try:
                with app.app_context():
                    run_scan(app, automatic=True)
            except Exception:
                app.logger.exception('Automatische Postfachprüfung fehlgeschlagen')
    thread = Thread(target=worker, name='md-inbox-scan', daemon=True)
    app.extensions['mail_scan_worker'] = (thread, stop)
    thread.start()
