import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from webapp import create_app
from webapp.db import get_db
from webapp.services.mail_schedule import due_slot, run_scan, schedule_state
from webapp.services.outlook_lock import package_lock


class MailScheduleTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.app = create_app({"HR_GOAL_WORKFLOW": False, 'TESTING': True, 'AUTH_DISABLED': True,
            'DATABASE': str(root/'test.sqlite'), 'STORAGE_ROOT': str(root/'data'),
            'BACKUP_ROOT': str(root/'backup'), 'DOSSIER_HANDOFF_ROOT': str(root/'handoff')})
        self.context = self.app.app_context()
        self.context.push()
        self.addCleanup(self.context.pop)

    def test_boundaries(self):
        for hour, minute, expected in [(7,29,False),(7,30,True),(8,30,True),(17,30,True),(17,31,False),(18,30,False)]:
            self.assertEqual(bool(due_slot(datetime(2026,10,16,hour,minute))),expected)

    def test_weekends_are_excluded(self):
        for day in (17,18):
            self.assertFalse(due_slot(datetime(2026,10,day,7,30)))

    @patch('webapp.services.mail_schedule.scan_outlook_inbox', return_value={'errors': []})
    def test_opt_in_persistent_slot_and_manual_scan(self, scan):
        now = datetime(2026,10,15,7,30)
        self.assertIsNone(run_scan(self.app, automatic=True, now=now))
        db=get_db();db.execute('UPDATE mail_scan_schedule SET enabled=1');db.commit()
        run_scan(self.app,automatic=True,now=now)
        run_scan(self.app,automatic=True,now=now)
        self.assertEqual(scan.call_count,1)
        run_scan(self.app,now=now)
        self.assertEqual(scan.call_count,2)
        self.assertTrue(schedule_state(db)['last_finished'])
        with package_lock(Path(self.app.config['DATABASE']).with_suffix('.mail-scan')):
            with self.assertRaises(ValueError):
                run_scan(self.app,now=now)
        self.assertEqual(scan.call_count,2)

    @patch('webapp.services.mail_schedule.scan_outlook_inbox', side_effect=RuntimeError('Outlook nicht erreichbar'))
    def test_error_visible_and_next_slot_retries(self, scan):
        db=get_db();db.execute('UPDATE mail_scan_schedule SET enabled=1');db.commit()
        for hour in (7,8):
            with self.assertRaises(RuntimeError):
                run_scan(self.app,automatic=True,now=datetime(2026,10,15,hour,30))
        self.assertEqual(scan.call_count,2)
        self.assertEqual(schedule_state(db)['last_error'],'Outlook nicht erreichbar')
        self.assertIn('Outlook nicht erreichbar',self.app.test_client().get('/ruecklaeufe').get_data(as_text=True))
