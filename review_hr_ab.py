"""Start an isolated, synthetic HR walkthrough (A/B through E/F). Never opens Outlook or real data.

Run: python review_hr_ab.py
Each start uses a new directory under instance. No production settings are read.
The generated originals/templates demonstrate behaviour, not the final HR layout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import secrets
from unittest.mock import patch
import uuid
from zipfile import ZipFile, ZIP_DEFLATED

import pandas as pd
from flask import abort, redirect, request, url_for

from webapp import create_app
from webapp.db import get_db
from webapp.organisation import DEFAULTS
from webapp.services.cycles import create_cycle
from webapp.services.sap_import import import_sap_workbook
from webapp.services import goal_review
from tests.test_goal_import import word
from tests.test_word_packages import synthetic_template


PEOPLE = [
    ('900001','Lena','Meier','900101'),
    ('900002','Noah','Keller','900101'),
    ('900003','Mira','Steiner','900102'),
    ('900004','Jonas','Weber','900102'),
    ('900005','Alex','Huber','900102'),
    ('900101','Eva','Sommer','000000'),
    ('900102','Luca','Winter','000000'),
]


def complete_word_package(target: Path, xml: bytes) -> None:
    """Wrap synthetic Word XML in a valid repository-owned OOXML container."""
    container = Path(__file__).parent/'templates'/'preparation'/'MD_Reflexion.docx'
    with ZipFile(container) as source, ZipFile(target,'w',ZIP_DEFLATED) as output:
        for item in source.infolist():
            output.writestr(item, xml if item.filename=='word/document.xml' else source.read(item.filename))


def create_review_app(directory: Path):
    directory=directory.resolve()
    # Refuse existing directories rather than risk opening an existing database.
    directory.mkdir(parents=True,exist_ok=False)
    templates=directory/'templates';templates.mkdir()
    paths={}
    for kind,prefix in (('review','rb'),('outlook','ab'),('probation','pz')):
        target=templates/(kind+'.docx')
        synthetic_template(target,prefix)
        with ZipFile(target) as archive:xml=archive.read('word/document.xml')
        complete_word_package(target,xml)
        paths[kind]=str(target)
    settings={**DEFAULTS,'TESTING':True,'AUTH_DISABLED':True,'SECRET_KEY':secrets.token_hex(32),
        'SESSION_COOKIE_SECURE':False,'HR_GOAL_WORKFLOW':True,'HR_REVIEW_SANDBOX':True,
        'DATABASE':str(directory/'review.sqlite3'),'STORAGE_ROOT':str(directory/'data'),
        'BACKUP_ROOT':str(directory/'backups'),'DOSSIER_HANDOFF_ROOT':str(directory/'handoff'),
        'WORD_TEMPLATE_PATHS':paths,'HR_MAILBOX_EMAIL':'hr@example.invalid'}
    with patch('webapp.organisation.load_organisation',return_value=dict(DEFAULTS)):
        app=create_app(settings,instance_path=str(directory))

    @app.before_request
    def walkthrough_boundary():
        if request.remote_addr not in ('127.0.0.1','::1'):
            abort(403,'Der HR-Test ist nur auf diesem Gerät erreichbar.')
        allowed_read={'main.case_detail','main.returns_overview','main.worklist','main.person_word_correction','main.manager_detail','main.dispatch','main.dialogs','main.master_data','main.import_detail','main.cycle_detail','main.dashboard','main.analytics','main.setup_guide','main.help_page','main.help_document','main.sap_exports','main.cycle_closure','main.word_pdf_review','main.word_pdf_original','main.document_original','main.feedback_collection','main.feedback_review','main.feedback_bundle_download','static'}
        goal_endpoint=(request.endpoint or '').startswith('goal_work.')
        part_endpoint=(request.endpoint or '').startswith('parts.')
        sap_endpoint=(request.endpoint or '').startswith('sap_work.')
        workspace_endpoint=(request.endpoint or '').startswith('hr.')
        return_endpoint=(request.endpoint or '').startswith('return_work.')
        allowed_prepare={'main.person_word_correction','main.download_word_package','main.prepare_word_packages','main.change_deadlines','main.add_dialog_event','main.attach_dialog_event','main.cancel_dialog_event','main.add_cycle','main.word_pdf_review','main.upload_word_pdfs'}
        if request.method=='POST':
            if not (goal_endpoint or part_endpoint or sap_endpoint or return_endpoint or request.endpoint in allowed_prepare) or (request.endpoint=='goal_work.dispatch' and request.form.get('action')=='draft'):
                abort(403,'HR-Test: Outlook, Postfachzugriff und externe Übergaben sind gesperrt.')
        elif not goal_endpoint and not part_endpoint and not sap_endpoint and not workspace_endpoint and not return_endpoint and request.endpoint not in allowed_read:
            return redirect(url_for('hr.work'))

    with app.app_context():
        db=get_db()
        rows=[{'ID_NO_ZERO':pn,'Rufname':first,'Nachname':last,'Austritt':None,'BsGrd':100,
               'Eintritt':'2020-01-01','Ende Probezeit':'2020-04-01','OE Bez.':'Testbereich',
               'Dir. Vorgesetzter (PN)':manager,'Ans.':'1','Plans. Bez.':'Testfunktion',
               'lange ID/Nummer':pn+'@example.invalid','Bewilligung für':None}
              for pn,first,last,manager in PEOPLE]
        sap=directory/'synthetic-sap.xlsx';pd.DataFrame(rows).to_excel(sap,index=False)
        from webapp.services import sap_staging
        staged=sap_staging.stage(db,sap,original_filename=sap.name)
        selection={r['id']:r['revision'] for r in db.execute("SELECT * FROM hr_sap_changes WHERE batch_id=? AND category='new'",(staged,))}
        imported=sap_staging.apply(db,selection,reason='Synthetischen Ausgangsstand für die isolierte Übung übernommen')
        create_cycle(db,review_year=2025,sap_import_id=imported)
        batch=goal_review.batch(db,'guided-review','Übungsfall 1 · fünf nachgereichte Ausblicke')
        originals=directory/'data'/'goal_workflow'/'originals';originals.mkdir(parents=True)
        for index,(pn,first,last,_) in enumerate(PEOPLE[:5]):
            target=originals/f'Ausblick_2025_{first}_{last}.docx'
            word(target,title='Projekt abschliessen' if index==0 else f'Testziel von {first}')
            with ZipFile(target) as archive:
                xml=archive.read('word/document.xml').replace(b'111113',pn.encode() if index<4 else b'')
            complete_word_package(target,xml)
            goal_review.stage(db,target,filename=target.name,batch_id=batch,origin_key='guided:'+pn)
        changed=[dict(row) for row in rows if row['ID_NO_ZERO']!=PEOPLE[1][0]]
        changed[0]['OE Bez.']='Neue Test-OE'
        changed[0]['Dir. Vorgesetzter (PN)']=next(pn for pn,first,_,_ in PEOPLE if first=='Luca')
        changed.append({**rows[0],'ID_NO_ZERO':'900199','Rufname':'Nina','Nachname':'Neu',
            'lange ID/Nummer':'900199@example.invalid','Eintritt':'2026-09-01','Ende Probezeit':'2026-11-30'})
        changed_path=directory/'synthetic-sap-changes.xlsx';pd.DataFrame(changed).to_excel(changed_path,index=False)
        sap_staging.stage(db,changed_path,original_filename='Übung D – Wechsel, Eintritt und fehlender Datensatz.xlsx')
        # Two fully synthetic returns for the signature/handoff walkthrough.
        # The separate pending copies are explicitly labelled test evidence.
        from tests.test_word_pdf_imports import sample_pdf
        from webapp.services.word_pdf_imports import stage_pdf,confirm_import
        test_pdfs=directory/'test-pdfs';test_pdfs.mkdir()
        case_id=db.execute("SELECT case_id FROM dialog_cases WHERE employee_pn='900005'").fetchone()[0]
        for kind,year in (('review',2025),('outlook',2026)):
            values=dict(kind=kind,year=year,person_pn='900005',manager_pn='900102',person_name='Alex Huber',manager_name='Luca Winter')
            marker='HR-TEST: Gesamtbeurteilung D (genuegend)' if kind=='review' else 'HR-TEST: fiktiver Ausblick'
            pdf=sample_pdf(test_pdfs/(kind+'.pdf'),marker=marker,**values)
            incoming=stage_pdf(db,pdf,filename=pdf.name,directory=directory/'data'/'pdf_queue')[0]
            parsed=json.loads(db.execute('SELECT parsed_json FROM word_pdf_imports WHERE id=?',(incoming,)).fetchone()[0])
            for key in ('performance_goals','development_goals'):
                for goal in parsed[key]:goal.pop('evidence',None)
            parsed['data']['rating']='D' if kind=='review' else ''
            reviewed={key:parsed[key] for key in ('data','performance_goals','development_goals','assessments')}
            reviewed.update(scope='full',source_role='digital')
            confirm_import(db,incoming,reviewed=reviewed,assignment='1',case_id=case_id,historical=False,
                reason='Synthetische Uebung: Angaben vollstaendig im Testoriginal vorhanden')
            scan=sample_pdf(test_pdfs/(kind+'-testscan.pdf'),marker=marker+' / TEST-Unterschriften Alex + Luca',**values)
            stage_pdf(db,scan,filename=scan.name,directory=directory/'data'/'pdf_queue')
    return app


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=5056)
    args=parser.parse_args()
    directory=Path(__file__).parent/'instance'/('hr-ab-review-'+uuid.uuid4().hex[:10])
    app=create_review_app(directory)
    print(f'HR-TEST: http://127.0.0.1:{args.port}/arbeit',flush=True)
    print(f'Nur synthetische Daten: {directory}',flush=True)
    print('Outlook, Postfachzugriff und externe Übergaben sind gesperrt.',flush=True)
    app.run(host='127.0.0.1',port=args.port,debug=False,use_reloader=False)


if __name__=='__main__':
    main()
