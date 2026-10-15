"""COM boundary regression: one unreadable mail must not abort the scan."""
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace, ModuleType
from unittest.mock import Mock, patch
import unittest

from webapp.adapters.outlook import OutlookInboxAdapter


class Items:
    def __init__(self, values):
        self.values = values
        self.Count = len(values)
    def Sort(self, *args):
        pass
    def Item(self, index):
        value = self.values[index - 1]
        if isinstance(value, Exception):
            raise value
        return value


def mail(attachments=(), **kwargs):
    return SimpleNamespace(Class=43, Subject='Test MD', EntryID='test-entry',
        SenderEmailAddress='test@example.invalid', ReceivedTime=datetime(2026, 10, 13),
        PropertyAccessor=SimpleNamespace(GetProperty=lambda _: ''),
        Attachments=Items(list(attachments)), **kwargs)


class OutlookReadTest(unittest.TestCase):
    def run_scan(self, values):
        com = ModuleType('pythoncom')
        com.CoInitialize = Mock(); com.CoUninitialize = Mock()
        win = ModuleType('win32com'); win.__path__ = []
        client = ModuleType('win32com.client'); win.client = client
        namespace = Mock()
        client.Dispatch = Mock(return_value=SimpleNamespace(GetNamespace=lambda _: namespace))
        adapter = OutlookInboxAdapter()
        with patch.dict('sys.modules', {'pythoncom': com, 'win32com': win, 'win32com.client': client}), patch(
            'webapp.adapters.outlook._resolve_inbox', return_value=SimpleNamespace(Items=Items(values))):
            messages = adapter.read_messages(mailbox_name='Test')
        com.CoUninitialize.assert_called_once()
        return messages, adapter

    def test_item_failure_does_not_hide_later_mail(self):
        messages, adapter = self.run_scan([RuntimeError('digitale ID -2146893792'), mail()])
        self.assertEqual(len(messages), 1)
        self.assertEqual(len(adapter.read_errors), 1)
        self.assertIn('Position 1', adapter.read_errors[0])
        self.assertIn('S/MIME', adapter.read_errors[0])

    def test_attachment_failure_discards_partial_message_and_continues(self):
        good = SimpleNamespace(FileName='Rueckblick.pdf', SaveAsFile=lambda p: Path(p).write_bytes(b'test'))
        bad = SimpleNamespace(FileName='Ausblick.pdf', SaveAsFile=Mock(side_effect=RuntimeError('digitale ID -2146893792')))
        messages, adapter = self.run_scan([mail([good, bad]), mail()])
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].attachments, ())
        self.assertEqual(len(adapter.read_errors), 1)
        self.assertIn('Test MD', adapter.read_errors[0])

    def test_non_mail_is_skipped(self):
        messages, adapter = self.run_scan([SimpleNamespace(Class=26), mail()])
        self.assertEqual(len(messages), 1)
        self.assertEqual(adapter.read_errors, [])

    def test_intake_reports_read_failure_without_processing_or_moving_mail(self):
        from tempfile import TemporaryDirectory
        from webapp.services.mail_intake import scan_outlook_inbox
        adapter = SimpleNamespace(read_errors=['S/MIME nicht lesbar'], read_messages=lambda **_: [], move_message=Mock())
        with TemporaryDirectory() as tmp, patch('webapp.services.mail_intake.process_inbound_messages', return_value={'failed': 0, 'errors': []}) as process:
            result = scan_outlook_inbox(None, mailbox_name='Test', target_folder='MD', inbox_dir=Path(tmp), pdf_dir=Path(tmp), handoff_dir=Path(tmp), adapter=adapter)
        self.assertEqual(result['failed'], 1)
        self.assertEqual(result['errors'], ['S/MIME nicht lesbar'])
        process.assert_not_called()
        adapter.move_message.assert_not_called()
