"""Task-oriented intake on synthetic originals, without Outlook access."""
import json
import unittest
from urllib.parse import parse_qs,urlsplit
from tests import test_goal_workflow as goals, test_return_review as returns, test_word_pdf_imports as pdfs
from webapp.services import intake_views, hr_workflow, word_pdf_imports, mail_intake


class IntakeViewsTest(unittest.TestCase):
    setUp=goals.GoalWorkflowTest.setUp
    tearDown=goals.GoalWorkflowTest.tearDown
    imported=returns.ReturnReviewTest.imported

    def stage(self,**values):
        path=pdfs.sample_pdf(self.root/'input.pdf',**values)
        return word_pdf_imports.stage_pdf(self.db,path,filename='Eingang.pdf',directory=self.root/'incoming')[0]

    def employment(self):
        return self.db.execute("SELECT * FROM employment_assignments WHERE person_number='111113' AND assignment_number='1'").fetchone()

    def form(self,item,**updates):
        reviewed=pdfs.WordPdfImportsTest.reviewed(self,item)
        values={**reviewed['data'],'scope':'full','source_role':'digital','case_id':self.case_id,
                'assignment':'1','employment_id':str(self.employment()['id']),'action':'confirm','checked':'yes','csrf_token':self.csrf}
        for group in ('performance','development'):
            for field in ('title','criteria','steps','target_date','competency'):
                values[group+'_'+field]=[g.get(field,'') for g in reviewed.get(group+'_goals',[])]
        values.update(updates)
        return values

    def test_views_are_distinct_and_do_not_change_domain_records(self):
        self.stage()
        tables=('dialog_cases','document_obligations','word_pdf_imports','official_documents')
        before={t:[tuple(r) for r in self.db.execute('SELECT * FROM '+t)] for t in tables}
        for tab,title in [('documents','Dokumente zuordnen'),('returns','Nachweise und Ablage'),('mail','Postfachprüfung ist')]:
            page=self.client.get('/ruecklaeufe?tab='+tab)
            self.assertEqual(page.status_code,200)
            self.assertIn(title,page.text)
            self.assertEqual(page.text.count('aria-current="page"'),3)
        self.assertEqual(self.client.get('/ruecklaeufe?tab=unknown').status_code,400)
        for t in tables:self.assertEqual(before[t],[tuple(r) for r in self.db.execute('SELECT * FROM '+t)])

    def test_pdf_search_uses_name_and_distinguishes_recognition(self):
        item=self.stage()
        person=self.db.execute("SELECT first_name,last_name FROM persons WHERE person_number='111113'").fetchone()
        name=person['first_name']+' '+person['last_name']
        rows=intake_views.documents(self.db,query=name)['word_pdf_queue']
        self.assertEqual([r['id'] for r in rows],[item])
        self.assertTrue(rows[0]['current_contexts'])
        page=self.client.get('/ruecklaeufe',query_string={'pdf_q':name})
        self.assertIn('Erkannt – noch am Original prüfen',page.text)
        self.assertEqual(intake_views.documents(self.db,query="' OR 1=1 --")['pdf_total'],0)

    def test_exclusion_removes_pending_count_and_preserves_original_and_back(self):
        item=self.stage();path='/word-pdf-imports/'+str(item)
        original=self.db.execute('SELECT parsed_json,stored_path FROM word_pdf_imports WHERE id=?',(item,)).fetchone()
        back='/ruecklaeufe?tab=documents&pdf_q=Eingang&pdf_page=2'
        response=self.client.post(path,data={'csrf_token':self.csrf,'revision':'0','action':'not_md','back':back},follow_redirects=True)
        self.assertIn('Als kein MD-Dokument ausgeschlossen',response.text)
        self.assertIn('Zurück zur aufrufenden Auswahl',response.text)
        self.assertIn('pdf_q=Eingang&amp;pdf_page=2',response.text)
        self.assertEqual(intake_views.counts(self.db)['pdf'],0)
        self.assertEqual(intake_views.documents(self.db,status='not_md')['pdf_total'],1)
        self.assertEqual(tuple(original),tuple(self.db.execute('SELECT parsed_json,stored_path FROM word_pdf_imports WHERE id=?',(item,)).fetchone()))
        bad=self.client.get(path,query_string={'back':'https://outside.invalid/ruecklaeufe'})
        self.assertNotIn('href="https://outside.invalid',bad.text)

    def test_person_picker_derives_numbers_from_chosen_employment(self):
        item=self.stage();values=self.form(item,action='draft',pn='111114',assignment='untrusted')
        response=self.client.post('/word-pdf-imports/'+str(item),data=values,follow_redirects=True)
        self.assertEqual(response.status_code,200)
        reviewed=json.loads(self.db.execute('SELECT reviewed_json FROM word_pdf_imports WHERE id=?',(item,)).fetchone()[0])
        self.assertEqual(reviewed['data']['pn'],'111113')
        self.assertEqual(reviewed['_draft']['assignment'],'1')
        self.assertEqual(reviewed['_draft']['employment_id'],str(self.employment()['id']))
        self.assertIn('Person und Anstellung',response.text)
        self.assertNotIn('type="text" name="pn"',response.text)

    def test_missing_or_invalid_choice_cannot_confirm(self):
        item=self.stage()
        for value in ('','not-valid','999999'):
            response=self.client.post('/word-pdf-imports/'+str(item),data=self.form(item,employment_id=value))
            self.assertIn('eindeutige Person und Anstellung',response.text)
            self.assertEqual(self.db.execute('SELECT status FROM word_pdf_imports WHERE id=?',(item,)).fetchone()[0],'pending')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM official_documents').fetchone()[0],0)

    def test_named_choice_accepts_intranet_return_without_dispatch(self):
        item=self.stage()
        back='/ruecklaeufe?tab=documents&pdf_q=Eingang'
        response=self.client.post('/word-pdf-imports/'+str(item),data=self.form(item,back=back),follow_redirects=True)
        self.assertEqual(response.status_code,200)
        self.assertIn('/arbeit/ruecklaeufe/',response.request.path)
        self.assertIn('pdf_q=Eingang',response.text)
        self.assertEqual(self.db.execute('SELECT status FROM word_pdf_imports WHERE id=?',(item,)).fetchone()[0],'imported')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM word_dispatch_packages').fetchone()[0],0)
        self.assertEqual(intake_views.counts(self.db)['pdf'],0)

    def test_multiple_employments_are_labelled_without_guessing(self):
        old=self.employment()
        with self.db:self.db.execute('''INSERT INTO employment_assignments(person_number,assignment_number,org_unit,active,last_import_id,updated_at)
            VALUES ('111113','2','Andere OE',1,?,'2026-01-01')''',(old['last_import_id'],))
        choices=intake_views.employment_choices(self.db,person_number='111113')
        self.assertEqual(len(choices),2)
        self.assertTrue(all('Anstellung ' in c['label'] for c in choices))
        self.assertTrue(any('Andere OE' in c['label'] for c in choices))
        item=self.stage()
        page=self.client.get('/word-pdf-imports/'+str(item))
        # The test original has no employment number: both choices stay explicit.
        self.assertIn('Andere OE',page.text)
        self.assertIn('Bitte eindeutig auswählen',page.text)

    def test_return_followup_list_links_to_canonical_document(self):
        doc,item=self.imported()
        value=intake_views.returns(self.db)
        self.assertEqual([r['id'] for r in value['rows']],[doc])
        page=self.client.get('/ruecklaeufe?tab=returns')
        self.assertIn('/arbeit/ruecklaeufe/'+str(doc),page.text)
        queue=intake_views.documents(self.db,status='imported')['word_pdf_queue']
        self.assertTrue(queue[0]['registered'])

    def test_open_mail_filter_includes_failures_but_not_completed_reviews(self):
        with self.db:
            for i,(status,done) in enumerate([('failed',''),('review_required',''),('review_required','2026-01-01')]):
                self.db.execute('''INSERT INTO inbound_mail_messages(outlook_entry_id,internet_message_id,
                    received_at,sender_email,subject,status,review_completed_at,created_at,updated_at)
                    VALUES (?,?,'2026-01-01','test@example.invalid','Test',?,?,'2026-01-01','2026-01-01')''',(str(i),str(i),status,done))
        value=mail_intake.mail_inbox_overview(self.db,status='open')
        self.assertEqual(value['mail_total'],2)
        page=self.client.get('/ruecklaeufe?mail_status=open')
        self.assertIn('E-Mail-Anliegen bearbeiten',page.text)
        self.assertIn('Verarbeitung nicht abgeschlossen',page.text)

    def test_mail_settings_return_to_local_filtered_view_only(self):
        back='/ruecklaeufe?tab=mail&mail_status=failed&mail_page=2#postfach'
        response=self.client.post('/mail-inbox/schedule',data={'enabled':'0','back':back})
        self.assertEqual(response.location,back)
        response=self.client.post('/mail-inbox/schedule',data={'enabled':'0','back':'//outside.invalid/ruecklaeufe'})
        self.assertEqual(urlsplit(response.location).path,'/ruecklaeufe')
        self.assertEqual(parse_qs(urlsplit(response.location).query)['tab'],['mail'])

    def test_excluded_attachment_is_identified_in_mail_without_closing_other_work(self):
        item=self.stage()
        row=self.db.execute('SELECT * FROM word_pdf_imports WHERE id=?',(item,)).fetchone()
        self.client.post('/word-pdf-imports/'+str(item),data={'action':'not_md','revision':'0','csrf_token':self.csrf})
        value=mail_intake.attachment_progress(self.db,{'sha256':row['sha256'],'stored_path':row['stored_path'],
            'original_filename':row['original_filename'],'status':'review_required'})
        self.assertEqual(value['progress'],'Kein MD-Dokument – ausgeschlossen')
        self.assertIn('übrigen Anhänge',value['next_step'])
        self.assertEqual(value['word_pdf_import_id'],item)

    def test_paged_name_search_and_lookup_are_bounded(self):
        item=self.stage()
        original=dict(self.db.execute('SELECT * FROM word_pdf_imports WHERE id=?',(item,)).fetchone())
        original.pop('id')
        with self.db:
            for i in range(30):
                row={**original,'sha256':'page-'+str(i),'original_filename':f'Eingang-{i}.pdf'}
                self.db.execute('INSERT INTO word_pdf_imports ('+','.join(row)+') VALUES ('+','.join('?' for _ in row)+')',list(row.values()))
        person=self.db.execute("SELECT first_name,last_name FROM persons WHERE person_number='111113'").fetchone()
        name=person['first_name']+' '+person['last_name']
        value=intake_views.documents(self.db,query=name,page=2)
        self.assertEqual(value['pdf_total'],31)
        self.assertEqual(len(value['word_pdf_queue']),6)
        page=self.client.get('/ruecklaeufe',query_string={'pdf_q':name,'pdf_page':2})
        self.assertIn('Seite 2 von 2',page.text)
        found=self.client.get('/arbeit/ziele/lookup',query_string={'kind':'employment','q':name}).json['results']
        self.assertTrue(found)
        self.assertLessEqual(len(found),25)
        self.assertIn('Direkt vorgesetzt:',found[0]['label'])
