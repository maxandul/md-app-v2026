"""The supported entry point always uses the current HR workflow."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from webapp import create_app
from webapp.db import get_db
from webapp.organisation import DEFAULTS


class StandardAppTest(unittest.TestCase):
    def test_fresh_install_and_restart_use_hr_without_environment_flags(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings = {'TESTING': True, 'AUTH_DISABLED': True, 'SECRET_KEY': 'test',
                        'WORD_TEMPLATE_PATHS': {}}
            with patch.dict(os.environ, {'MD_HR_GOAL_WORKFLOW': '0',
                                        'MD_LEGACY_WORKBOOKS': 'enabled',
                                        'MD_HR_RETURN_AUTOMATION': '0'}), \
                    patch('webapp.organisation.load_organisation', return_value=dict(DEFAULTS)):
                app = create_app(settings, instance_path=str(root))
                self.assertTrue(app.config['HR_GOAL_WORKFLOW'])
                self.assertFalse(app.config['HR_RETURN_AUTOMATION'])
                client = app.test_client()
                self.assertEqual(client.get('/').location, '/arbeit')
                for path in ('/arbeit', '/mitarbeitende', '/fuehrungskraefte',
                             '/stammdaten/abgleich', '/versand?workflow=workbook'):
                    response = client.get(path)
                    self.assertEqual(response.status_code, 200, path)
                    self.assertNotIn('HTML-Arbeitsmappe', response.text)
                with app.app_context():
                    db = get_db()
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0], 5)
                    db.execute("INSERT INTO audit_log(action, object_type, object_id, details_json, created_at) VALUES ('restart-marker','test','1','{}','2026-10-28')")
                    db.commit()
                restarted = create_app(settings, instance_path=str(root))
                with restarted.app_context():
                    self.assertEqual(get_db().execute("SELECT COUNT(*) FROM audit_log WHERE action='restart-marker'").fetchone()[0], 1)
                    self.assertIsNone(get_db().execute('PRAGMA foreign_key_check').fetchone())

    def test_removed_html_actions_are_not_executable_and_login_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch('webapp.organisation.load_organisation', return_value=dict(DEFAULTS)):
            app = create_app({'TESTING': True, 'SECRET_KEY': 'test',
                              'WORD_TEMPLATE_PATHS': {}}, instance_path=temporary)
            client = app.test_client()
            self.assertIn(client.get('/arbeit').status_code, (302, 303))
            self.assertIn('/auth/', client.get('/arbeit').location)
            app.config['AUTH_DISABLED'] = True
            for path in ('/returns', '/cycles/1/managers/123/package',
                         '/cycles/1/managers/123/package/recreate',
                         '/cycles/1/managers/123/update', '/cycles/1/packages/batch',
                         '/cycles/1/mail-drafts'):
                self.assertEqual(client.post(path).status_code, 404, path)

    def test_old_configuration_key_cannot_restore_the_removed_interface(self):
        from webapp.organisation import load_organisation
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / 'organisation.json'
            config.write_text('{"LEGACY_WORKBOOKS":"enabled"}', encoding='utf-8')
            result = load_organisation(config)
            self.assertNotIn('LEGACY_WORKBOOKS', result)
            self.assertIn('entfällt', result['_ORG_CONFIG_NOTICE'])
