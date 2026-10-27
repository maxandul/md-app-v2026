"""Withdrawn approvals cannot leak into new output or disappear from follow-up."""
import hashlib
import unittest
from pathlib import Path
from tests import test_goal_workflow as fixtures
from tests.test_word_dispatch import FakeOutlook
from webapp.services import goal_review as review,goal_followups as followups,goal_delivery as delivery,goal_queries
from webapp.services import goal_withdrawals as withdrawals
from webapp.services.word_packages import prior_goals


class GoalWithdrawalsTest(unittest.TestCase):
    setUp=fixtures.GoalWorkflowTest.setUp
    tearDown=fixtures.GoalWorkflowTest.tearDown
    stage=fixtures.GoalWorkflowTest.stage
    confirm=fixtures.GoalWorkflowTest.confirm
    generate=fixtures.GoalWorkflowTest.generate
    ready=fixtures.GoalWorkflowTest.ready
    act=fixtures.GoalWorkflowTest.act
    pending_return=fixtures.GoalWorkflowTest.pending_return

    def withdraw(self,source,**updates):
        impact=withdrawals.impact(self.db,source)
        args=dict(expected_revision=review.get(self.db,source)['revision'],expected_impact=review.digest(impact),
                  reason='Falsche Person oder falsches Zieljahr am Original festgestellt',checked=True)
        args.update(updates)
        return withdrawals.withdraw(self.db,source,**args)

    def resolve(self,withdrawal_id,**updates):
        item=withdrawals.get(self.db,withdrawal_id)
        check=withdrawals.checks(self.db,item)[0]
        args=dict(outcome='no_change',reason='Keine Weitergabe erfolgt; bisherige Unterlagen benötigen keine Korrektur',
            expected_evidence=check['evidence_token'],withdrawal_id=withdrawal_id,effects_checked=True)
        args.update(updates)
        return followups.decide(self.db,item['confirmed_revision_id'],check['case_id'],**args)

    def test_reassigns_person_and_year_without_overwriting_original_or_confirmed_revision(self):
        source=self.stage();rev=self.confirm(source)
        before=dict(self.db.execute('SELECT * FROM hr_goal_revisions WHERE id=?',(rev,)).fetchone())
        original=Path(review.get(self.db,source)['stored_path']).read_bytes()
        withdrawal=self.withdraw(source)
        item=review.get(self.db,source)
        self.assertEqual(item['status'],'draft')
        self.assertTrue(review.withdrawn(self.db,rev))
        self.assertEqual(before,dict(self.db.execute('SELECT * FROM hr_goal_revisions WHERE id=?',(rev,)).fetchone()))
        self.assertEqual(original,Path(item['stored_path']).read_bytes())
        person=self.db.execute("SELECT id FROM employment_assignments WHERE person_number='111115'").fetchone()[0]
        new=self.confirm(source,employment_id=person,goal_year=2024)
        self.assertEqual(prior_goals(self.db,employee_pn='111115',assignment='4',year=2024)[2]['hr_goal_revision_id'],new)
        self.assertEqual(review.sources(self.db,before['employment_id'],2025),[])
        self.assertEqual(goal_queries.source_state(self.db,source),'withdrawal')
        self.assertEqual(goal_queries.listing(self.db,q='111113',year=2025)['total'],1)
        self.assertEqual(goal_queries.listing(self.db,q='111115',year=2024)['total'],1)
        with self.assertRaisesRegex(ValueError,'zurückgenommen'):followups.revision(self.db,rev)
        self.resolve(withdrawal)
        self.assertEqual(prior_goals(self.db,employee_pn='111113',assignment='1',year=2025),([],[],{}))
        self.assertFalse(withdrawals.unresolved(self.db,source))

    def test_prepared_group_cancelled_but_files_approvals_and_membership_preserved(self):
        source,rev,output,group=self.ready()
        row=dict(self.db.execute('SELECT * FROM hr_goal_outputs WHERE id=?',(output,)).fetchone())
        data=Path(row['stored_path']).read_bytes()
        self.withdraw(source)
        from webapp.db import init_db
        init_db(self.db,hr_goals=True)
        self.assertEqual(delivery.get(self.db,group)['status'],'cancelled')
        self.assertEqual(row,dict(self.db.execute('SELECT * FROM hr_goal_outputs WHERE id=?',(output,)).fetchone()))
        self.assertEqual(data,Path(row['stored_path']).read_bytes())
        self.assertEqual([o['id'] for o in delivery.members(self.db,group)],[output])
        with self.assertRaisesRegex(ValueError,'zurückgenommen'):followups.validate_output(self.db,output,self.paths)
        with self.assertRaises(ValueError):self.act(group,adapter=FakeOutlook())

    def test_cancelled_mixed_group_releases_other_valid_person_output(self):
        source=self.stage();rev=self.confirm(source);one=self.generate(rev)['output_id']
        other=self.stage('other.docx','Andere Person')
        employment=self.db.execute("SELECT id FROM employment_assignments WHERE person_number='111112'").fetchone()[0]
        other_rev=self.confirm(other,employment_id=employment)
        case=self.db.execute("SELECT case_id FROM dialog_cases WHERE employee_pn='111112' AND manager_pn='111116'").fetchone()[0]
        two=self.generate(other_rev,case)['output_id']
        for output in (one,two):followups.approve(self.db,output,self.paths)
        groups,errors=delivery.prepare(self.db,[one,two],self.paths)
        self.assertFalse(errors);self.assertEqual(len(groups),1)
        self.withdraw(source)
        self.assertEqual(len(delivery.members(self.db,groups[0])),2)
        self.assertIsNone(followups.output_dispatch(self.db,two))
        new,errors=delivery.prepare(self.db,[two],self.paths)
        self.assertFalse(errors);self.assertNotEqual(new,groups)

    def test_open_outlook_kept_and_closure_requires_actual_resolution(self):
        source,rev,output,group=self.ready();fake=FakeOutlook();self.act(group,adapter=fake)
        withdrawal=self.withdraw(source)
        self.assertEqual(delivery.get(self.db,group)['status'],'draft_created')
        self.assertEqual(len(fake.calls),1)
        with self.assertRaisesRegex(ValueError,'Outlook'):self.resolve(withdrawal)
        self.act(group,action='cancelled')
        self.resolve(withdrawal)
        self.assertFalse(withdrawals.unresolved(self.db,source))

    def test_sent_history_survives_and_new_return_reopens_withdrawal_check(self):
        source,rev,output,group=self.ready();self.act(group,adapter=FakeOutlook());self.act(group,action='sent_confirmed')
        withdrawal=self.withdraw(source)
        self.assertEqual(delivery.get(self.db,group)['status'],'sent_confirmed')
        with self.assertRaisesRegex(ValueError,'weitergegebene'):self.resolve(withdrawal,effects_checked=False)
        self.resolve(withdrawal,reason='Empfänger hat die fehlerhafte Vorlage nicht verwendet; Inhalt des bestehenden Rückblicks geprüft')
        self.assertFalse(withdrawals.unresolved(self.db,source))
        self.pending_return()
        self.assertTrue(withdrawals.unresolved(self.db,source))
        self.assertEqual(goal_queries.source_state(self.db,source),'withdrawal')

    def test_changed_impact_or_revision_prevents_stale_withdrawal(self):
        source=self.stage();self.confirm(source);snapshot=withdrawals.impact(self.db,source)
        self.pending_return()
        with self.assertRaisesRegex(ValueError,'Ausgaben, Versand'):self.withdraw(source,expected_impact=review.digest(snapshot))
        self.assertEqual(review.get(self.db,source)['status'],'confirmed')
        old=review.get(self.db,source)['revision'];self.confirm(source)
        with self.assertRaisesRegex(ValueError,'inzwischen'):self.withdraw(source,expected_revision=old)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM hr_goal_withdrawals').fetchone()[0],0)

    def test_reupload_and_discard_do_not_hide_unresolved_old_effects(self):
        source=self.stage();rev=self.confirm(source);self.withdraw(source)
        row=review.get(self.db,source)
        duplicate=review.stage(self.db,row['stored_path'],filename='duplicate.docx',batch_id=self.group,origin_key='again')
        self.assertEqual(duplicate,source);self.assertEqual(review.get(self.db,source)['status'],'draft')
        review.save(self.db,source,expected_revision=row['revision'],status='discarded',employment_id=row['employment_id'],
            goal_year=row['goal_year'],goals=row['goals'],note='Dieses Original wird nicht weiter verwendet')
        self.assertEqual(goal_queries.source_state(self.db,source),'withdrawal')
        self.assertEqual(goal_queries.listing(self.db)['total'],1)

    def test_legacy_raw_import_cannot_reappear_after_withdrawal(self):
        from tests.test_word_packages import WordPackagesTest
        source=self.stage();item=review.get(self.db,source)
        WordPackagesTest.add_goals(self,source_hash=item['sha256'])
        self.confirm(source);withdrawal=self.withdraw(source)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM historical_goals').fetchone()[0],1)
        self.assertEqual(review.sources(self.db,item['employment_id'],2025),[])
        from webapp.services.packages import _prior_goals
        with self.assertRaises(ValueError):_prior_goals(self.db,employee_pn='111113',employment_assignment='1',review_year=2025)
        self.resolve(withdrawal)
        self.assertEqual(_prior_goals(self.db,employee_pn='111113',employment_assignment='1',review_year=2025),([],[]))

    def test_legacy_manager_dispatch_is_included_and_remains_open(self):
        from webapp.services.word_dispatch import prepare_word_batch,dispatch_word_packages
        source=self.stage();self.confirm(source)
        _,batch=prepare_word_batch(self.db,cycle_id=self.cycle_id,manager_pns=['111116'],template_paths=self.paths,output_dir=self.root/'legacy')
        package=batch['packages'][0]['id']
        dispatch_word_packages(self.db,cycle_id=self.cycle_id,package_ids=[package],template_paths=self.paths,
            sender_email='hr@example.invalid',adapter=FakeOutlook())
        withdrawal=self.withdraw(source)
        open_items=withdrawals.open_outlook(self.db,withdrawal)
        self.assertEqual([(r['kind'],r['id']) for r in open_items],[('package',package)])
        page=self.client.get(f'/arbeit/ziele/ruecknahmen/{withdrawal}')
        self.assertEqual(page.status_code,200)
        self.assertIn(f'/versand?cycle_id={self.cycle_id}',page.text)
        with self.assertRaisesRegex(ValueError,'Outlook'):self.resolve(withdrawal)

    def test_duplicate_withdrawal_and_wrong_decision_context_rejected(self):
        source=self.stage();rev=self.confirm(source);withdrawal=self.withdraw(source)
        with self.assertRaisesRegex(ValueError,'aktive Freigabe'):self.withdraw(source)
        other=self.stage('other.docx','Andere Fassung');other_rev=self.confirm(other)
        with self.assertRaisesRegex(ValueError,'gehört nicht'):
            followups.decide(self.db,other_rev,self.case_id,outcome='no_change',reason='Prüfung',expected_evidence=review.digest([]),
                withdrawal_id=withdrawal,effects_checked=True)

    def test_routes_preserve_history_and_protect_post(self):
        source=self.stage();self.confirm(source)
        self.assertIn('Falsche Freigabe zurücknehmen',self.client.get(f'/arbeit/ziele/{source}').text)
        response=self.client.get(f'/arbeit/ziele/{source}/ruecknahme')
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.client.post(f'/arbeit/ziele/{source}/ruecknahme').status_code,400)
        affected=withdrawals.impact(self.db,source)
        response=self.client.post(f'/arbeit/ziele/{source}/ruecknahme',data={'csrf_token':self.csrf,'revision':review.get(self.db,source)['revision'],
            'impact':review.digest(affected),'reason':'Zuordnung am Original als falsch erkannt','checked':'yes'},follow_redirects=True)
        self.assertEqual(response.status_code,200);self.assertIn('Folgen der Rücknahme klären',response.text)
        self.assertIn('Freigabe zurückgenommen',self.client.get(f'/arbeit/ziele/{source}').text)
        withdrawal=self.db.execute('SELECT id FROM hr_goal_withdrawals WHERE source_id=?',(source,)).fetchone()[0]
        url=f'/arbeit/ziele/ruecknahmen/{withdrawal}'
        self.assertEqual(self.client.post(url).status_code,400)
        response=self.client.post(url,data={'csrf_token':self.csrf,'case_id':self.case_id,'evidence':review.digest([]),
            'outcome':'no_change','reason':'Keine Ausgabe oder manuelle Weitergabe erfolgt','checked':'yes'},follow_redirects=True)
        self.assertEqual(response.status_code,200);self.assertIn('Auswirkungen geprüft',response.text)
        self.assertFalse(withdrawals.unresolved(self.db,source))

    def test_historical_output_case_is_reviewable_after_period_changed(self):
        source,rev,output,group=self.ready()
        with self.db:
            self.db.execute('UPDATE cycles SET review_year=2026 WHERE id=?',(self.cycle_id,))
            self.db.execute("UPDATE dialog_cases SET period_end='2026-12-31' WHERE case_id=?",(self.case_id,))
        self.assertEqual(followups.targets(self.db,rev),[])
        withdrawal=self.withdraw(source)
        self.assertEqual([c['case_id'] for c in withdrawals.checks(self.db,withdrawals.get(self.db,withdrawal))],[self.case_id])
        self.resolve(withdrawal)
        self.assertFalse(withdrawals.unresolved(self.db,source))

    def test_competing_source_requires_explicit_choice_after_old_effects_checked(self):
        source=self.stage();self.confirm(source)
        other=self.stage('competing.docx','Andere unabhängige Quelle');self.confirm(other)
        self.confirm(source)
        withdrawal=self.withdraw(source);self.resolve(withdrawal)
        self.assertTrue(withdrawals.unresolved(self.db,source))
        self.assertIn('Auswahl ausdrücklich neu festlegen',self.client.get(f'/arbeit/ziele/ruecknahmen/{withdrawal}').text)
        self.confirm(other,note='Andere Quelle nach Rücknahme am Original geprüft und ausgewählt')
        self.assertFalse(withdrawals.unresolved(self.db,source))

    def test_migration_from_001_preserves_existing_source_and_original(self):
        from tests import test_word_packages as old_fixtures
        from tests.test_goal_import import word
        import webapp.migrations as migrations
        from unittest.mock import patch
        old=old_fixtures.WordPackagesTest();old.setUp()
        try:
            first=Path(migrations.__file__).with_suffix('')/'001_hr_goals.sql'
            with patch.object(migrations.Path,'glob',return_value=[first]):migrations.migrate(old.db)
            group=review.batch(old.db,'pre-upgrade','Vor Migration 002')
            original=word(old.root/'before.docx')
            source=review.stage(old.db,original,filename=original.name,batch_id=group,origin_key='pre-upgrade')
            before={t:[tuple(r) for r in old.db.execute('SELECT * FROM '+t)] for t in ('dialog_cases','hr_goal_sources','hr_goal_revisions')}
            checksum=hashlib.sha256(original.read_bytes()).hexdigest()
            migrations.migrate(old.db);migrations.migrate(old.db)
            for table,rows in before.items():self.assertEqual(rows,[tuple(r) for r in old.db.execute('SELECT * FROM '+table)])
            self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),checksum)
            self.assertEqual(old.db.execute('SELECT COUNT(*) FROM schema_migrations').fetchone()[0],4)
            self.assertEqual(review.get(old.db,source)['status'],'draft')
        finally:old.tearDown()

    def test_without_old_case_requires_explicit_manual_effect_check(self):
        source=self.stage();self.confirm(source,goal_year=2024)
        withdrawal=self.withdraw(source)
        self.assertIsNone(withdrawals.checks(self.db,withdrawals.get(self.db,withdrawal))[0]['case_id'])
        with self.assertRaisesRegex(ValueError,'weitergegebene'):self.resolve(withdrawal,outcome='no_output',effects_checked=False)
        self.resolve(withdrawal,outcome='no_output',reason='Keine Ausgabe oder manuelle Weitergabe festgestellt')
        self.assertFalse(withdrawals.unresolved(self.db,source))

    def test_required_correction_can_finish_on_withdrawn_revision_without_reenabling_it(self):
        source=self.stage();rev=self.confirm(source)
        def document(sha,previous=None):
            with self.db:
                if previous:self.db.execute('UPDATE official_documents SET is_current=0 WHERE id=?',(previous,))
                return self.db.execute('''INSERT INTO official_documents(case_id,cycle_id,employee_pn,manager_pn,
                    document_kind,variant,original_filename,stored_path,sha256,received_at,handoff_status,replaces_document_id)
                    VALUES (?,?,'111113','111116','review','digital','review.pdf','preserved',?,'2026-10-27','staged',?)''',
                    (self.case_id,self.cycle_id,sha,previous)).lastrowid
        old=document('old-review');withdrawal=self.withdraw(source)
        self.resolve(withdrawal,outcome='request_correction',reason='Falsche Ziele im alten Rückblick korrigieren lassen',
            recipient_email='person-111116@example.invalid',requested_at='2026-10-27')
        with self.assertRaisesRegex(ValueError,'neuer'):self.resolve(withdrawal,outcome='corrected',corrected_document_id=old)
        corrected=document('corrected-review',old)
        self.resolve(withdrawal,outcome='corrected',corrected_document_id=corrected,reason='Neuen Rücklauf am Original und auf entfernte falsche Ziele geprüft')
        self.assertFalse(withdrawals.unresolved(self.db,source))
        with self.assertRaisesRegex(ValueError,'zurückgenommen'):followups.inputs(self.db,rev,self.case_id,self.paths)


if __name__=='__main__':unittest.main()
