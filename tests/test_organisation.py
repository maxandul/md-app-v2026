from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from webapp import create_app
from webapp.organisation import load_organisation
from prototype.html_dialog.generate_package import render_html


class OrganisationTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.config=self.root/'organisation.json'
        self.env=patch.dict(os.environ,{'MD_ORG_CONFIG':str(self.config)})
        self.env.start()
    def tearDown(self):
        self.env.stop();self.tmp.cleanup()
    def write(self,values):
        self.config.write_text(json.dumps(values),encoding='utf-8')

    def test_neutral_defaults_and_relative_paths(self):
        values=load_organisation()
        self.assertEqual(values['HR_MAILBOX_EMAIL'],'')
        self.assertEqual(values['SPECIAL_CASES_URL'],'')
        self.write({'DOSSIER_HANDOFF_ROOT':'local/input','HR_MAILBOX_EMAIL':'hr@example.invalid'})
        self.assertEqual(load_organisation()['DOSSIER_HANDOFF_ROOT'],str(self.root/'local/input'))
        with patch.dict(os.environ,{'MD_HR_MAILBOX_EMAIL':'override@example.invalid'}):
            self.assertEqual(load_organisation()['HR_MAILBOX_EMAIL'],'override@example.invalid')

    def test_invalid_links_unknown_keys_and_non_string_are_rejected(self):
        for values in ({'SPECIAL_CASES_URL':'javascript:alert(1)'},{'SPECIAL_CASES_URL':'https://user:secret@example.invalid'},
                       {'HR_MAILBOX_EMAIL':'bad\n@example.invalid'},{'unknown':'value'},{'OUTLOOK_MAILBOX_NAME':5},{'PUBLIC_BASE_URL':'javascript:alert(1)'},{'PUBLIC_BASE_URL':'https://user:password@example.invalid'},{'PUBLIC_BASE_URL':'http://example.invalid:bad'},{'LEGACY_WORKBOOKS':'yes'}):
            with self.subTest(values=values):
                self.write(values)
                with self.assertRaises(ValueError):
                    load_organisation()

    def test_windows_utf8_bom_and_missing_config_diagnostics(self):
        self.assertFalse(load_organisation()['_ORG_CONFIG_LOADED'])
        self.assertEqual(load_organisation()['_ORG_CONFIG_PATH'],str(self.config))
        self.config.write_text(json.dumps({'HR_MAILBOX_EMAIL':'hr@example.invalid','OUTLOOK_MAILBOX_NAME':'HR Test'}),encoding='utf-8-sig')
        values=load_organisation()
        self.assertTrue(values['_ORG_CONFIG_LOADED'])
        self.assertEqual(values['OUTLOOK_MAILBOX_NAME'],'HR Test')

    def test_alias_filename_is_loaded_and_ambiguity_rejected(self):
        directory=self.root/'instance';directory.mkdir()
        alias=directory/'organisatio_config.json'
        alias.write_text(json.dumps({'HR_MAILBOX_EMAIL':'hr@example.invalid','OUTLOOK_MAILBOX_NAME':'HR Test','DOSSIER_HANDOFF_ROOT':'data/dossier_ready'}))
        with patch.dict(os.environ,{},clear=True), patch('webapp.organisation.__file__',str(self.root/'webapp/organisation.py')):
            values=load_organisation()
            self.assertEqual(values['OUTLOOK_MAILBOX_NAME'],'HR Test')
            self.assertEqual(values['_ORG_CONFIG_PATH'],str(alias))
            self.assertEqual(values['DOSSIER_HANDOFF_ROOT'],str(directory/'data/dossier_ready'))
            (directory/'organisation.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'Mehrere Organisationskonfigurationen'):
                load_organisation()
            self.assertEqual(load_organisation(alias)['HR_MAILBOX_EMAIL'],'hr@example.invalid')

    def test_html_embeds_configuration_as_json_without_interpolating_script_source(self):
        url='https://intranet.example.invalid/special?x=`${test}</script>'
        self.write({'HR_MAILBOX_EMAIL':'hr@example.invalid','SPECIAL_CASES_URL':url})
        payload={'configuration':{},'package':{'package_id':'test'},'employees':[]}
        page=render_html(payload)
        self.assertIn('hr@example.invalid',page)
        self.assertIn('specialCasesLink()',page)
        self.assertNotIn(url,page)  # Script closing tag is safely escaped in JSON.
        self.assertEqual(page.count('</script>'),2)
        self.assertNotIn('hr_email',payload['configuration'])

    def test_app_settings_override_and_local_handoff_fallback(self):
        self.write({})
        app=create_app({'TESTING':True,'AUTH_DISABLED':True,'SECRET_KEY':'test','DATABASE':str(self.root/'db'),
                        'STORAGE_ROOT':str(self.root/'data'),'BACKUP_ROOT':str(self.root/'backup'),
                        'HR_MAILBOX_EMAIL':'test@example.invalid','WORD_TEMPLATE_PATHS':{}})
        self.assertEqual(app.config['DOSSIER_HANDOFF_ROOT'],str(self.root/'data/dossier_ready'))
        with app.app_context():
            page=render_html({'configuration':{},'package':{},'employees':[]})
        self.assertIn('test@example.invalid',page)

if __name__=='__main__':unittest.main()
