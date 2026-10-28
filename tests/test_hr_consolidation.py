"""Consolidated HR views on synthetic data; no external services."""
import time
import unittest
from urllib.parse import urlsplit, parse_qs
from tests import test_goal_workflow as fixtures
from tests import test_return_review as return_fixtures
from tests import test_part_consumers as part_fixtures
from tests import test_word_feedback as feedback_fixtures
from webapp.services import hr_views as views, return_review, word_feedback

class ConsolidationTest(unittest.TestCase):
    setUp=fixtures.GoalWorkflowTest.setUp
    tearDown=fixtures.GoalWorkflowTest.tearDown
    imported=return_fixtures.ReturnReviewTest.imported
    current=return_fixtures.ReturnReviewTest.current
    attach=return_fixtures.ReturnReviewTest.attach
    confirm=return_fixtures.ReturnReviewTest.confirm
    publish=return_fixtures.ReturnReviewTest.publish
    assign=part_fixtures.PartConsumersTest.assign

    def person_pn(self):
        return self.db.execute('SELECT employee_pn FROM dialog_cases WHERE case_id=?',(self.case_id,)).fetchone()[0]

    def test_all_entry_points_render_without_changing_domain_records(self):
        tables=('official_documents','document_obligations','dialog_cases','word_feedback_submissions')
        before={t:[tuple(r) for r in self.db.execute('SELECT * FROM '+t)] for t in tables}
        paths=('/arbeit','/mitarbeitende','/fuehrungskraefte','/arbeit/feedback','/arbeit/uebergaben',
               '/auswertungen','/mitarbeitende/'+self.person_pn(),'/fuehrungskraefte/111116')
        for path in paths:
            with self.subTest(path=path):self.assertEqual(self.client.get(path).status_code,200)
        for table in tables:self.assertEqual(before[table],[tuple(r) for r in self.db.execute('SELECT * FROM '+table)])

    def test_new_default_and_old_bookmarks_preserve_filters(self):
        self.assertEqual(urlsplit(self.client.get('/').location).path,'/arbeit')
        planning=self.client.get('/?view=cycles')
        self.assertEqual(planning.status_code,200);self.assertIn('/cycles',planning.text)
        self.assertIn('view=cycles',self.client.get('/arbeit').text)
        response=self.client.get('/aufgaben?q=Test&state=waiting&page=3')
        self.assertEqual(urlsplit(response.location).path,'/arbeit')
        self.assertEqual(parse_qs(urlsplit(response.location).query)['state'],['waiting'])
        page=self.client.get('/arbeit?q=keine-passende-Person')
        self.assertIn('Keine passenden Aufgaben',page.text)
        self.assertIn('Mitarbeitende',page.text);self.assertIn('Führungskräfte',page.text)

    def test_part_views_use_separate_managers_and_keep_feedback_scope(self):
        self.assign('outlook')
        old=views.parts(self.db,person=self.person_pn(),manager='111116')
        new=views.parts(self.db,person=self.person_pn(),manager='111114')
        self.assertEqual([r['document_kind'] for r in old['rows']],['review'])
        self.assertEqual([r['document_kind'] for r in new['rows']],['outlook'])
        self.assertEqual(new['rows'][0]['part']['manager_pn'],'111114')
        self.assertTrue(any(r['manager_pn']=='111114' for r in views.managers(self.db)['rows']))

    def test_old_years_are_open_by_default_even_when_cycle_is_closed(self):
        with self.db:self.db.execute("UPDATE cycles SET status='abgeschlossen',review_year=2020,outlook_year=2021 WHERE id=?",(self.cycle_id,))
        rows=views.work(self.db,kind='Gesprächsteil',year=2020)['rows']
        self.assertTrue(any(r['person_number']==self.person_pn() for r in rows))
        self.assertTrue(views.parts(self.db,person=self.person_pn(),year=2020)['total'])

    def test_completed_parts_remain_in_person_history(self):
        with self.db:self.db.execute("UPDATE document_obligations SET status='complete' WHERE dialog_event_id IN (SELECT id FROM dialog_events WHERE legacy_case_id=?)",(self.case_id,))
        self.assertEqual(views.parts(self.db,person=self.person_pn())['total'],0)
        self.assertEqual(views.parts(self.db,person=self.person_pn(),state='all')['total'],2)
        self.assertEqual(self.client.get('/mitarbeitende/'+self.person_pn()+'?state=all').status_code,200)

    def test_return_task_moves_from_waiting_to_history_without_separate_completion(self):
        doc,_=self.imported()
        self.attach(doc)
        return_review.inspect_signatures(self.db,doc,action='requested',reason='Unterschrift telefonisch angefordert',
            recipient='Führungskraft',requested_at='2026-01-15',**self.current(doc))
        rows=views.work(self.db,kind='Rücklauf',state='waiting')['rows']
        self.assertEqual([r['record_id'] for r in rows],[doc])
        self.assertEqual(rows[0]['title'],'Nachgefordert')
        self.confirm(doc);self.publish(doc)
        self.assertEqual(views.work(self.db,kind='Rücklauf',state='open')['total'],0)
        self.assertEqual(views.work(self.db,kind='Rücklauf',state='waiting')['total'],0)
        self.assertEqual([r['record_id'] for r in views.work(self.db,kind='Rücklauf',state='done')['rows']],[doc])
        self.assertEqual(views.handoffs(self.db,state='done')['rows'][0]['id'],doc)

    def test_goals_share_the_existing_waiting_state(self):
        source=fixtures.GoalWorkflowTest.stage(self)
        fixtures.GoalWorkflowTest.confirm(self,source,status='waiting')
        waiting=views.work(self.db,kind='Ziele',state='waiting')
        self.assertEqual(waiting['total'],1);self.assertEqual(waiting['rows'][0]['record_id'],source)
        self.assertEqual(views.work(self.db,kind='Ziele',state='open')['total'],0)

    def test_feedback_addendum_and_history_do_not_create_obligations(self):
        count=self.db.execute('SELECT COUNT(*) FROM document_obligations').fetchone()[0]
        item=feedback_fixtures.WordFeedbackTest.stage(self)
        word_feedback.confirm_feedback(self.db,item,cycle_id=self.cycle_id,manager_pn='111116',fields={'keep':'Mehr Austausch'})
        self.db.commit()
        self.assign('review')
        rows=views.feedback(self.db,manager='111116',state='open')['rows']
        self.assertEqual(rows[0]['pending'],1)
        bundle=word_feedback.bundle_feedback(self.db,cycle_id=self.cycle_id,manager_pn='111116',expected_ids=[item],
            handoff_dir=self.root/'handoff',archive_dir=self.root/'archive')
        self.assertEqual(views.feedback(self.db,manager='111116',state='open')['total'],0)
        self.assertEqual(views.feedback(self.db,manager='111116')['rows'][0]['bundles'],1)
        page=self.client.get(f'/feedback-collections/{self.cycle_id}/111116')
        self.assertEqual(page.status_code,200);self.assertIn('Bereitgestellte Bündel',page.text);self.assertNotIn('Erwartet:',page.text)
        self.assertIn(f'/feedback-bundles/{bundle}/download',page.text)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM document_obligations').fetchone()[0],count)
        next_item=feedback_fixtures.WordFeedbackTest.stage(self,name='Zweite Person',filename='Nachtrag.pdf')
        word_feedback.confirm_feedback(self.db,next_item,cycle_id=self.cycle_id,manager_pn='111116',fields={'keep':'Nachtrag'})
        self.db.commit()
        self.assertEqual(views.feedback(self.db,manager='111116',state='open')['rows'][0]['pending'],1)

    def test_collection_action_still_requires_csrf_and_review(self):
        self.assertEqual(self.client.post(f'/feedback-collections/{self.cycle_id}/111116',data={'checked':'yes'}).status_code,400)

    def test_back_link_keeps_list_position_and_rejects_external_target(self):
        back='/arbeit?state=waiting&page=2'
        response=self.client.get(f'/arbeit/dialogteile/{self.case_id}/review',query_string={'back':back})
        self.assertIn('/arbeit?state=waiting&amp;page=2',response.text)
        response=self.client.get('/mitarbeitende/'+self.person_pn(),query_string={'back':'//example.org'})
        self.assertNotIn('href="//example.org"',response.text)

    def test_paging_and_search_do_not_interpolate_user_input(self):
        self.assertEqual(views.people(self.db,q="' OR 1=1 --",state='all')['total'],0)
        result=views.people(self.db,page_number=-1,page_size=777,state='all')
        self.assertEqual(result['page'],1);self.assertEqual(result['page_size'],25)
        self.assertEqual(views.work(self.db,q="' OR 1=1 --",state='all')['total'],0)

    def test_operational_counts_use_part_form_org_and_document_state(self):
        self.assign('outlook')
        part=self.db.execute("SELECT form_org_unit FROM hr_resolved_obligations WHERE case_id=? AND document_kind='outlook'",(self.case_id,)).fetchone()[0]
        rows=views.operational_counts(self.db,cycle_id=self.cycle_id)
        self.assertTrue(any(r['form_org_unit']==part and r['document_kind']=='outlook' for r in rows))
        self.assertIn('Arbeitsstand nach Gesprächsteil',self.client.get('/auswertungen').text)

    def test_authentication_and_feature_flag_still_apply(self):
        self.app.config['HR_GOAL_WORKFLOW']=False
        self.assertEqual(self.client.get('/arbeit').status_code,404)
        self.app.config['HR_GOAL_WORKFLOW']=True
        self.app.config['AUTH_DISABLED']=False
        self.assertIn(self.client.get('/arbeit').status_code,(302,303))

    def test_delivery_label_uses_canonical_proof_when_legacy_flag_differs(self):
        doc,_=self.imported(rating='A');self.publish(doc)
        with self.db:self.db.execute("UPDATE official_documents SET handoff_status='needs_signature_check' WHERE id=?",(doc,))
        row=views.handoffs(self.db,state='done')['rows'][0]
        self.assertEqual(row['id'],doc);self.assertEqual(row['label'],'Lokal bereitgestellt')
        self.assertEqual(views.work(self.db,kind='Rücklauf',state='done')['rows'][0]['title'],'Für Dossier bereitgestellt')

    def test_person_lists_all_assignments_without_invented_feedback_author(self):
        person=self.db.execute('SELECT * FROM persons WHERE person_number=?',(self.person_pn(),)).fetchone()
        with self.db:self.db.execute('INSERT INTO employment_assignments(person_number,assignment_number,org_unit,last_import_id,updated_at) VALUES (?,?,?,?,?)',
            (self.person_pn(),'2','Zweite OE',person['last_import_id'],person['updated_at']))
        row=next(r for r in views.people(self.db,q=self.person_pn())['rows'] if r['person_number']==self.person_pn())
        self.assertEqual(row['assignments'],2)
        page=self.client.get('/mitarbeitende/'+self.person_pn())
        self.assertIn('Zweite OE',page.text)
        self.assertNotIn('Feedback-Sammlungen und Nachträge',page.text)

    def test_volume_1000_people_five_years_and_10000_parts(self):
        def clone(table, row, **values):
            record=dict(row);record.pop('id',None);record.update(values)
            names=list(record)
            return self.db.execute('INSERT INTO '+table+' ('+','.join(names)+') VALUES ('+','.join('?' for _ in names)+')',list(record.values())).lastrowid
        case=self.db.execute('SELECT * FROM dialog_cases WHERE case_id=?',(self.case_id,)).fetchone()
        employee=self.db.execute('SELECT * FROM employees WHERE pn=?',(case['employee_pn'],)).fetchone()
        person=self.db.execute('SELECT * FROM persons WHERE person_number=?',(case['employee_pn'],)).fetchone()
        employment=self.db.execute('SELECT * FROM employment_assignments WHERE person_number=?',(case['employee_pn'],)).fetchone()
        event=self.db.execute('SELECT * FROM dialog_events WHERE legacy_case_id=?',(self.case_id,)).fetchone()
        manager_assignment=self.db.execute('SELECT * FROM manager_assignments WHERE id=?',(event['manager_assignment_id'],)).fetchone()
        obligations=self.db.execute('SELECT * FROM document_obligations WHERE dialog_event_id=?',(event['id'],)).fetchall()
        cycle=self.db.execute('SELECT * FROM cycles WHERE id=?',(self.cycle_id,)).fetchone()
        with self.db:
            cycles=[(year,clone('cycles',cycle,review_year=year,outlook_year=year+1)) for year in range(2019,2024)]
            for n in range(1000):
                pn=str(800000+n)
                clone('employees',employee,pn=pn,first_name='Volumenperson',last_name=f'{n:04}')
                clone('persons',person,person_number=pn,first_name='Volumenperson',last_name=f'{n:04}')
                employment_id=clone('employment_assignments',employment,person_number=pn)
                manager_id=clone('manager_assignments',manager_assignment,employment_id=employment_id)
                for year,cycle_id in cycles:
                    case_id=f'volume-{pn}-{year}'
                    clone('dialog_cases',case,case_id=case_id,employee_pn=pn,cycle_id=cycle_id)
                    event_id=clone('dialog_events',event,event_id=case_id,legacy_case_id=case_id,cycle_id=cycle_id,employment_id=employment_id,manager_assignment_id=manager_id,review_year=year)
                    for o in obligations:clone('document_obligations',o,obligation_id=case_id+'-'+o['document_kind'],dialog_event_id=event_id)
        statements=[]
        self.db.set_trace_callback(statements.append)
        start=time.perf_counter()
        people=views.people(self.db,q='Volumenperson',page_number=2,page_size=25)
        work=views.work(self.db,q='Volumenperson',kind='Gesprächsteil',page_number=2,page_size=100)
        elapsed=time.perf_counter()-start
        self.db.set_trace_callback(None)
        self.assertEqual(people['total'],1000);self.assertEqual(len(people['rows']),25)
        self.assertEqual(work['total'],10000);self.assertEqual(len(work['rows']),100)
        self.assertTrue(any('LIMIT 100 OFFSET 100' in s for s in statements))
        print(f'F volume: 1000 people / 5 years / 10000 parts; two paged queries {elapsed:.3f}s (CI, not HR workstation)')
