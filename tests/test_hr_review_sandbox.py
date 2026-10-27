"""The guided walkthrough must never reach production configuration or Outlook."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from review_hr_ab import create_review_app
from webapp.db import get_db
from webapp.services import goal_review as review,goal_followups as followups,goal_delivery as delivery
from webapp.services.word_packages import goal_sources_fingerprint


class HRReviewSandboxTest(unittest.TestCase):
    def test_isolated_walkthrough_blocks_external_actions_and_preserves_existing_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'guided'
            with patch.dict(os.environ,{'MD_ORG_CONFIG':str(Path(temp)/'missing-prod-config.json'),
                         'MD_DOSSIER_HANDOFF_ROOT':str(Path(temp)/'must-not-exist')}):
                app=create_review_app(root)
            self.assertFalse((Path(temp)/'must-not-exist').exists())
            self.assertNotIn('mail_scan_worker',app.extensions)
            client=app.test_client()
            response=client.get('/arbeit/ziele')
            self.assertEqual(response.status_code,200)
            self.assertIn('HR-TEST',response.text);self.assertIn('Lena',response.text)
            with client.session_transaction() as session:csrf=session['goal_csrf']
            with app.app_context():
                db=get_db()
                self.assertEqual(db.execute('SELECT COUNT(*) FROM hr_goal_sources').fetchone()[0],5)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM hr_goal_revisions WHERE employment_id IS NULL').fetchone()[0],1)
                source=review.get(db,1)
                with ZipFile(source['stored_path']) as doc:self.assertIn('[Content_Types].xml',doc.namelist())
                rev=review.save(db,1,expected_revision=0,status='confirmed',employment_id=source['employment_id'],
                    goal_year=2025,goals=source['goals'],checked=True,note='Testprüfung',
                    expected_sources=goal_sources_fingerprint(review.sources(db,source['employment_id'],2025)))
                case=followups.targets(db,rev)[0]['case_id'];_,fingerprint,_=followups.inputs(db,rev,case,app.config['WORD_TEMPLATE_PATHS'])
                output=followups.generate(db,[(rev,case,fingerprint)],template_paths=app.config['WORD_TEMPLATE_PATHS'],output_dir=root/'data'/'outputs')[0]
                self.assertFalse(output['error'],output)
                followups.approve(db,output['output_id'],app.config['WORD_TEMPLATE_PATHS'])
                groups,errors=delivery.prepare(db,[output['output_id']],app.config['WORD_TEMPLATE_PATHS'])
                self.assertFalse(errors)
            with patch('webapp.services.goal_delivery.OutlookDraftAdapter') as outlook:
                response=client.post(f'/arbeit/ziele/versand/{groups[0]}',data={'csrf_token':csrf,'action':'draft','checked':'yes'})
                self.assertEqual(response.status_code,403);outlook.assert_not_called()
            self.assertEqual(client.post('/ruecklaeufe').status_code,403)
            self.assertEqual(client.get('/arbeit/ziele',environ_overrides={'REMOTE_ADDR':'192.0.2.1'}).status_code,403)
            marker=root/'preserve.txt';marker.write_text('preserve',encoding='utf-8')
            with self.assertRaises(FileExistsError):create_review_app(root)
            self.assertEqual(marker.read_text(encoding='utf-8'),'preserve')


if __name__=='__main__':unittest.main()
