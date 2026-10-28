"""Synthetic multi-year volume check, no personal data or external integrations."""
import time
import unittest
from tests import test_goal_workflow as fixtures
from webapp.services import goal_queries


class GoalWorkflowVolumeTest(unittest.TestCase):
    setUp=fixtures.GoalWorkflowTest.setUp
    tearDown=fixtures.GoalWorkflowTest.tearDown

    def test_thousand_people_five_years_two_parts_and_versions(self):
        db=self.db
        exemplars={t:dict(db.execute('SELECT * FROM '+t+' LIMIT 1').fetchone()) for t in
            ('persons','employees','employment_assignments','cycles','dialog_cases','dialog_events','document_obligations')}
        def clone(table,**updates):
            data={k:v for k,v in exemplars[table].items() if k!='id'};data.update(updates)
            return db.execute('INSERT INTO '+table+' ('+','.join(data)+') VALUES ('+','.join('?' for _ in data)+')',tuple(data.values())).lastrowid
        with db:
            cycles={year:clone('cycles',review_year=year,outlook_year=year+1) for year in range(2020,2025)}
            for number in range(1000):
                pn=str(700000+number)
                clone('persons',person_number=pn,first_name='Synthetisch',last_name=str(number))
                clone('employees',pn=pn,first_name='Synthetisch',last_name=str(number))
                employment=clone('employment_assignments',person_number=pn,assignment_number='1')
                for year,cycle in cycles.items():
                    case=f'volume-{year}-{pn}'
                    clone('dialog_cases',case_id=case,cycle_id=cycle,employee_pn=pn,employment_assignment='1',
                          period_start=f'{year}-01-01',period_end=f'{year}-12-31')
                    event=clone('dialog_events',event_id=case,cycle_id=cycle,legacy_case_id=case,employment_id=employment,
                                review_year=year,period_start=f'{year}-01-01',period_end=f'{year}-12-31')
                    for kind in ('review','outlook'):
                        clone('document_obligations',obligation_id=case+'-'+kind,dialog_event_id=event,document_kind=kind)
                    if number%10==0:
                        extra=clone('dialog_events',event_id=case+'-probation',cycle_id=cycle,legacy_case_id=None,
                            employment_id=employment,review_year=year,event_type='probation_review')
                        clone('document_obligations',obligation_id=case+'-probation',dialog_event_id=extra,document_kind='review')
                    source=db.execute('''INSERT INTO hr_goal_sources(sha256,original_filename,stored_path,extraction_json,revision,created_at)
                        VALUES (?,?,'synthetic-only','{}',1,?)''',(case,case+'.docx',str(year))).lastrowid
                    for revision,status in ((0,'draft'),(1,'confirmed' if number%2 else 'waiting')):
                        db.execute('''INSERT INTO hr_goal_revisions(source_id,revision,status,employment_id,goal_year,goals_json,created_at)
                            VALUES (?,?,?,?,?,'{"performance_goals":[],"development_goals":[]}',?)''',
                            (source,revision,status,employment,year,str(year)))
        start=time.perf_counter();first=goal_queries.listing(db);elapsed=time.perf_counter()-start
        start=time.perf_counter();filtered=goal_queries.listing(db,q='700123');search=time.perf_counter()-start
        second=goal_queries.listing(db,page=2)
        self.assertEqual(first['total'],5000);self.assertEqual(len(first['rows']),25)
        self.assertEqual(filtered['total'],5)
        self.assertFalse({r['id'] for r in first['rows']}&{r['id'] for r in second['rows']})
        self.assertEqual(db.execute("SELECT COUNT(*) FROM document_obligations WHERE obligation_id LIKE 'volume-%'").fetchone()[0],10500)
        print(f'\nVOLUME: 1000 people / 5 years / 10500 parts / 10000 source revisions; open={elapsed:.3f}s search={search:.3f}s')
        from webapp.services import part_queries
        start=time.perf_counter();parts=part_queries.listing(db);part_elapsed=time.perf_counter()-start
        start=time.perf_counter();person=part_queries.listing(db,q='700123',state='all');part_search=time.perf_counter()-start
        self.assertEqual(person['total'],10);self.assertEqual(len(parts['rows']),25)
        next_page=part_queries.listing(db,page=2)
        self.assertFalse({r['id'] for r in parts['rows']}&{r['id'] for r in next_page['rows']})
        print(f'PARTS: open={part_elapsed:.3f}s search={part_search:.3f}s')


if __name__=='__main__':unittest.main()
