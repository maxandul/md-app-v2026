"""Opt-in A/B navigation. All links address the same persisted source/output."""
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import json
import secrets
import uuid
from flask import Blueprint,abort,current_app,flash,g,redirect,render_template,request,session,url_for,send_file
from .auth import login_required
from .db import get_db
from .services import goal_review as review, goal_followups as followups, goal_delivery as delivery, goal_queries
from .services import goal_withdrawals as withdrawals
from .services.part_responsibilities import assign_review
from .services.word_packages import goal_sources_fingerprint
from .services.goal_batches import save_upload

bp=Blueprint('goal_work',__name__,url_prefix='/arbeit/ziele')


@bp.before_app_request
def protect_legacy_goal_aliases():
    aliases={'main.legacy_goal_upload','main.create_goal_batch','main.upload_goal_batch_file','main.legacy_goal_preview','main.upload_sap_import','main.add_dialog_event','main.word_pdf_review','main.upload_word_pdfs','main.feedback_collection'}
    if current_app.config.get('HR_GOAL_WORKFLOW') and request.method=='POST' and request.endpoint in aliases:
        token=request.form.get('csrf_token','') or request.headers.get('X-CSRF-Token','')
        expected=session.get('goal_csrf','')
        if not expected or not secrets.compare_digest(token,expected):
            abort(400,'Die Seite ist abgelaufen. Bitte Zielnachreichungen neu öffnen.')


@bp.before_request
@login_required
def protect():
    if not current_app.config.get('HR_GOAL_WORKFLOW'):
        abort(404)
    if g.user and g.user['password_temporary']:
        return redirect(url_for('auth.change_password'))
    session.setdefault('goal_csrf',secrets.token_urlsafe(32))
    if request.method=='POST' and not secrets.compare_digest(request.form.get('csrf_token',''),session['goal_csrf']):
        abort(400,'Die Seite ist abgelaufen. Bitte neu laden.')


def actor():
    return g.user['id'] if g.user else None


def root(name):
    directory=Path(current_app.config['STORAGE_ROOT'])/'goal_workflow'/name
    directory.mkdir(parents=True,exist_ok=True)
    return directory


def back_link():
    value=request.values.get('back','')
    parsed=urlsplit(value)
    return value if not parsed.netloc and not parsed.scheme and '\\' not in value and parsed.path.startswith(('/arbeit','/mitarbeitende','/fuehrungskraefte')) else url_for('goal_work.index')


def render(template,**kwargs):
    return render_template(template,active_nav='goal_work',csrf_token=session['goal_csrf'],back=back_link(),
        state_labels={'prepared':'Vorbereitet','processing':'Outlook-Übernahme läuft','draft_created':'Outlook-Entwurf erstellt',
          'failed':'Outlook-Ausgang klären','sent_confirmed':'Versand bestätigt','cancelled':'Verworfen',
          'no_change':'Keine Korrektur nötig','waiting':'Rückfrage offen','request_correction':'Korrigierter Rücklauf angefordert',
          'corrected':'Korrigierter Rücklauf bearbeitet','no_output':'Keine Ausgabe nötig','resume':'Bearbeitung fortsetzen',
          'draft':'Prüfentwurf','confirmed':'Ziele bestätigt','discarded':'Quelle verworfen'},**kwargs)


@bp.get('')
def index():
    args={k:request.args.get(k,'') for k in ('q','org_unit')}
    args.update(state=request.args.get('state','open'),year=request.args.get('year',type=int),
                batch_id=request.args.get('batch_id',type=int),page=request.args.get('page',1,type=int),page_size=request.args.get('page_size',25,type=int))
    result=goal_queries.listing(get_db(),**args)
    def page_url(page):
        return url_for('goal_work.index',**{**args,'page':page})
    group=get_db().execute('SELECT * FROM hr_goal_batches WHERE id=?',(args['batch_id'],)).fetchone()
    return render('goal_work/index.html',filters=args,group=group,page_url=page_url,**result)


def accept_uploads(uploads,goal_year=None):
    uploads=[u for u in uploads if u and u.filename]
    if not uploads:
        raise ValueError('Bitte mindestens einen alten Ausblick auswählen.')
    group=review.batch(get_db(),'upload:'+uuid.uuid4().hex,'Manuell eingelesene Ausblicke')
    directory=root('originals')/str(group)
    directory.mkdir(parents=True,exist_ok=True)
    errors=[]
    for upload in uploads:
        try:
            file_id=save_upload(directory,upload)
            path=next((directory/'files'/file_id).iterdir())
            review.stage(get_db(),path,filename=Path(upload.filename.replace('\\','/')).name,
                         batch_id=group,origin_key=f'upload:{group}:{file_id}',goal_year=goal_year)
        except (ValueError,OSError) as exc:
            errors.append(f'{upload.filename}: {exc}')
    for error in errors:
        flash(error,'error')
    return redirect(url_for('goal_work.index',batch_id=group,state='all'))


@bp.post('/upload')
def upload():
    try:
        return accept_uploads(request.files.getlist('forms'),request.form.get('goal_year',type=int))
    except ValueError as exc:
        flash(str(exc),'error')
        return redirect(url_for('goal_work.index'))


@bp.get('/lookup')
def lookup():
    q='%'+request.args.get('q','').strip()+'%'
    if request.args.get('kind')=='manager':
        rows=get_db().execute("SELECT pn AS id,first_name||' '||last_name||' · PN '||pn||' · '||org_unit AS label FROM employees WHERE first_name||' '||last_name||' '||pn LIKE ? ORDER BY last_name,first_name,pn LIMIT 25",(q,)).fetchall()
    else:
        rows=get_db().execute('''SELECT ea.id,p.first_name||' '||p.last_name||' · PN '||ea.person_number||' · Ans. '||ea.assignment_number||' · '||ea.org_unit AS label
            FROM employment_assignments ea JOIN persons p ON p.person_number=ea.person_number
            WHERE p.first_name||' '||p.last_name||' '||ea.person_number LIKE ? ORDER BY p.last_name,p.first_name,ea.id LIMIT 25''',(q,)).fetchall()
    return {'results':[dict(r) for r in rows]}


def form_goals():
    result={}
    for kind in ('performance_goals','development_goals'):
        values={field:request.form.getlist(kind+'_'+field) for field in review.FIELDS}
        count=max((len(v) for v in values.values()),default=0)
        result[kind]=[{field:items[i] if i<len(items) else '' for field,items in values.items()} for i in range(count)]
    return result


@bp.route('/<int:source_id>',methods=['GET','POST'])
def source(source_id):
    db=get_db()
    try:
        item=review.get(db,source_id)
    except ValueError:
        abort(404)
    if request.method=='POST':
        try:
            action=request.form.get('action')
            review.save(db,source_id,expected_revision=request.form.get('revision',type=int),status='confirmed' if action=='confirm_next' else action,
                employment_id=request.form.get('employment_id',type=int),goal_year=request.form.get('goal_year',type=int),
                goals=form_goals(),note=request.form.get('note',''),checked=request.form.get('checked')=='yes',
                expected_sources=request.form.get('sources_fingerprint',''),user_id=actor())
            flash('Zielversion bestätigt. Prüfe jetzt die Folgeaktion.' if action in ('confirmed','confirm_next') else 'Bearbeitungsstand gespeichert.','success')
            if action=='confirm_next':
                group=parse_qs(urlsplit(back_link()).query).get('batch_id',[None])[0]
                next_source=db.execute('''SELECT s.id FROM hr_goal_sources s
                    JOIN hr_goal_revisions r ON r.source_id=s.id AND r.revision=s.revision
                    WHERE s.id<>? AND r.status='draft' AND (? IS NULL OR EXISTS
                    (SELECT 1 FROM hr_goal_batch_sources b WHERE b.source_id=s.id AND b.batch_id=?))
                    ORDER BY s.id LIMIT 1''',(source_id,group,group)).fetchone()
                return redirect(url_for('goal_work.source',source_id=next_source[0],back=back_link()) if next_source else back_link())
            return redirect(url_for('goal_work.source',source_id=source_id,back=back_link()))
        except (ValueError,TypeError) as exc:
            flash(str(exc),'error')
            # Preserve typed text, but retain the old revision so a stale form cannot overwrite a newer save.
            item.update(goals=form_goals(),note=request.form.get('note',''),employment_id=request.form.get('employment_id',type=int),
                        goal_year=request.form.get('goal_year',type=int),revision=request.form.get('revision',type=int))
    known=review.sources(db,item['employment_id'],item['goal_year'])
    history=db.execute('''SELECT r.*,ea.person_number,ea.assignment_number,
        EXISTS(SELECT 1 FROM hr_goal_withdrawals w WHERE w.source_id=r.source_id AND w.through_revision>=r.revision) AS withdrawn
        FROM hr_goal_revisions r LEFT JOIN employment_assignments ea ON ea.id=r.employment_id WHERE source_id=? ORDER BY revision DESC''',(source_id,)).fetchall()
    withdrawn=[dict(r) for r in db.execute('SELECT * FROM hr_goal_withdrawals WHERE source_id=? ORDER BY id DESC',(source_id,))]
    can_withdraw=any(r['status']=='confirmed' and not r['withdrawn'] for r in history)
    origins=db.execute('''SELECT b.* FROM hr_goal_batches b JOIN hr_goal_batch_sources bs ON bs.batch_id=b.id WHERE bs.source_id=? ORDER BY b.id''',(source_id,)).fetchall()
    group=parse_qs(urlsplit(back_link()).query).get('batch_id',[None])[0] or (origins[-1]['id'] if origins else None)
    context=goal_queries.listing(db,batch_id=group,state='all',page_size=100) if group else {'rows':[],'total':0}
    confirmed_ids=[r['id'] for r in context['rows'] if r['status']=='confirmed']
    selected=db.execute('''SELECT ea.id,p.first_name||' '||p.last_name||' · PN '||ea.person_number||' · Ans. '||ea.assignment_number||' · '||ea.org_unit AS label
        FROM employment_assignments ea JOIN persons p ON p.person_number=ea.person_number WHERE ea.id=?''',(item['employment_id'],)).fetchone()
    return render('goal_work/source.html',item=item,known_sources=known,fingerprint=goal_sources_fingerprint(known),
                  history=history,origins=origins,selected=selected,competencies=review.COMPETENCY_TAGS.values(),
                  context=context,confirmed_ids=confirmed_ids,context_group=group,withdrawals=withdrawn,can_withdraw=can_withdraw)


@bp.route('/<int:source_id>/ruecknahme',methods=['GET','POST'])
def withdraw(source_id):
    try:
        item=review.get(get_db(),source_id)
        if request.method=='POST':
            withdrawal_id=withdrawals.withdraw(get_db(),source_id,expected_revision=request.form.get('revision',type=int),
                expected_impact=request.form.get('impact',''),reason=request.form.get('reason',''),
                checked=request.form.get('checked')=='yes',user_id=actor())
            flash('Freigabe zurückgenommen. Quelle neu zuordnen und Auswirkungen auf bisherige Unterlagen klären.','success')
            return redirect(url_for('goal_work.withdrawal',withdrawal_id=withdrawal_id,back=back_link()))
        impact=withdrawals.impact(get_db(),source_id)
    except ValueError as exc:
        flash(str(exc),'error')
        return redirect(url_for('goal_work.source',source_id=source_id,back=back_link()))
    return render('goal_work/withdraw.html',item=item,impact=impact,impact_token=review.digest(impact))


@bp.route('/ruecknahmen/<int:withdrawal_id>',methods=['GET','POST'])
def withdrawal(withdrawal_id):
    db=get_db()
    try:item=withdrawals.get(db,withdrawal_id)
    except ValueError:abort(404)
    if request.method=='POST':
        try:
            followups.decide(db,item['confirmed_revision_id'],request.form.get('case_id') or None,
                outcome=request.form.get('outcome'),reason=request.form.get('reason',''),expected_evidence=request.form.get('evidence',''),
                recipient_email=request.form.get('recipient_email',''),requested_at=request.form.get('requested_at',''),
                corrected_document_id=request.form.get('corrected_document_id',type=int),withdrawal_id=withdrawal_id,
                effects_checked=request.form.get('checked')=='yes',user_id=actor())
            flash('Folgeentscheidung zur zurückgenommenen Freigabe gespeichert.','success')
        except ValueError as exc:flash(str(exc),'error')
        return redirect(url_for('goal_work.withdrawal',withdrawal_id=withdrawal_id,back=back_link()))
    return render('goal_work/withdrawal.html',withdrawal=item,checks=withdrawals.checks(db,item),
                  deliveries=withdrawals.deliveries(db,item),open_outlook=withdrawals.open_outlook(db,withdrawal_id),
                  pending_choice=withdrawals.pending_choice(db,item),current=review.get(db,item['source_id']))


@bp.get('/<int:source_id>/original')
def original(source_id):
    try:
        item=review.get(get_db(),source_id)
    except ValueError:
        abort(404)
    path=Path(item['stored_path'])
    if not path.is_file():
        abort(404,'Das gesicherte Original ist nicht erreichbar.')
    return send_file(path,as_attachment=path.suffix.lower()!='.pdf',download_name=item['original_filename'])


@bp.post('/mail/<int:message_id>')
def from_mail(message_id):
    if not get_db().execute('SELECT 1 FROM inbound_mail_messages WHERE id=?',(message_id,)).fetchone():
        abort(404)
    group=review.stage_mail(get_db(),message_id)
    return redirect(url_for('goal_work.index',batch_id=group,state='all'))


@bp.post('/pdf/<int:import_id>')
def from_pdf(import_id):
    row=get_db().execute('SELECT * FROM word_pdf_imports WHERE id=?',(import_id,)).fetchone()
    if not row:
        abort(404)
    data=json.loads(row['reviewed_json'] or row['parsed_json'])
    data=data.get('data',data)
    if data.get('document_kind')!='outlook':
        abort(400,'Nur ein als Ausblick zugeordneter Eingang kann als Zielquelle verwendet werden.')
    group=review.batch(get_db(),f'pdf:{import_id}','Ausblick aus dem PDF-Eingang')
    try:
        source_id=review.stage(get_db(),row['stored_path'],filename=row['original_filename'],batch_id=group,origin_key=f'pdf:{import_id}',pdf_import_id=import_id)
        return redirect(url_for('goal_work.source',source_id=source_id))
    except (ValueError,OSError) as exc:
        flash(str(exc),'error')
        return redirect(url_for('main.word_pdf_review',import_id=import_id))


def selected_sources():
    values=request.values.getlist('source')
    if len(values)>100 or any(not x.isdigit() for x in values):
        abort(400,'Bitte höchstens 100 Zielquellen auswählen.')
    return list(dict.fromkeys(int(x) for x in values))


@bp.route('/ausgaben',methods=['GET','POST'])
def outputs():
    db=get_db();ids=selected_sources();paths=current_app.config['WORD_TEMPLATE_PATHS']
    errors=[]
    if request.method=='POST':
        try:
            action=request.form.get('action')
            output_ids=list(dict.fromkeys(int(raw) for raw in request.form.getlist('output')))
            if action in ('approve','prepare'):
                if not output_ids:
                    raise ValueError('Bitte mindestens eine Ausgabe auswählen.')
                for output_id in output_ids:
                    selected=db.execute('''SELECT r.source_id FROM hr_goal_outputs o
                        JOIN hr_goal_revisions r ON r.id=o.revision_id WHERE o.id=?''',(output_id,)).fetchone()
                    if not selected or selected[0] not in ids:
                        raise ValueError('Eine Ausgabe gehört nicht zur aktuellen Auswahl.')
            if action=='generate':
                selections=[]
                for raw in request.form.getlist('target'):
                    data=json.loads(raw)
                    if not isinstance(data,list) or len(data)!=3:
                        raise ValueError('Ungültige Auswahl.')
                    rev=followups.revision(db,data[0])
                    if rev['source_id'] not in ids:
                        raise ValueError('Auswahl gehört nicht zu diesen Zielquellen.')
                    selections.append(data)
                if not selections:
                    raise ValueError('Bitte mindestens einen zulässigen Rückblick auswählen.')
                result=followups.generate(db,selections,template_paths=paths,output_dir=root('outputs'),user_id=actor())
                errors=[r['error'] for r in result if r['error']]
                flash(f"{sum(not r['error'] for r in result)} Rückblicke erstellt oder wiedergefunden.",'success')
            elif action=='approve':
                approved=0
                for output_id in output_ids:
                    try:
                        followups.approve(db,output_id,paths,user_id=actor());approved+=1
                    except (ValueError,OSError) as exc:
                        errors.append(f'Ausgabe {output_id}: {exc}')
                flash(f'{approved} Ausgaben für den Versand geprüft.','success')
            elif action=='prepare':
                groups,excluded=delivery.prepare(db,output_ids,paths,user_id=actor())
                errors=[r['error'] for r in excluded]
                if len(groups)==1 and not errors:
                    return redirect(url_for('goal_work.dispatch',dispatch_id=groups[0],back=url_for('goal_work.outputs',source=ids,back=back_link())))
                flash(f'{len(groups)} Versandgruppen vorbereitet oder wiedergefunden.','success')
            else:
                raise ValueError('Unbekannte Aktion.')
        except (ValueError,TypeError) as exc:
            errors.append(str(exc))
    rows=[];sources=[];saved=[];groups={}
    for source_id in ids:
        try:
            item=review.get(db,source_id);sources.append(item)
            if item['status']!='confirmed':
                errors.append(f"{item['original_filename']}: Ziele zuerst bestätigen.")
                continue
            for case in followups.targets(db,item['revision_id']):
                row={**case,'revision_id':item['revision_id'],'source_id':source_id,'error':'','token':'','part':None,'evidence':[]}
                try:
                    row['part']=followups.resolve(db,case['case_id']);row['evidence']=followups.return_evidence(db,row['part'])
                    row['decision']=followups.latest_decision(db,item['revision_id'],case['case_id'])
                    data,fp,_=followups.inputs(db,item['revision_id'],case['case_id'],paths)
                    if followups.decision_effective(row['decision'],row['evidence']) and row['decision']['outcome'] in ('no_change','no_output','waiting','request_correction','corrected'):
                        raise ValueError('Folgeentscheidung dokumentiert; siehe Klärung.')
                    row['token']=review.dump([item['revision_id'],case['case_id'],fp])
                except (ValueError,OSError) as exc:
                    row['error']=str(exc)
                row['evidence_token']=review.digest(row['evidence'])
                rows.append(row)
            for r in db.execute('SELECT * FROM hr_goal_outputs WHERE revision_id=? ORDER BY id DESC',(item['revision_id'],)):
                output=dict(r);output['inputs']=json.loads(r['inputs_json']);output['error']='';output['dispatch']=followups.output_dispatch(db,r['id'])
                try:
                    followups.validate_output(db,r['id'],paths)
                except (ValueError,OSError) as exc:
                    output['error']=str(exc)
                saved.append(output)
                if output['dispatch']:
                    groups[output['dispatch']['id']]=output['dispatch']
        except ValueError as exc:
            errors.append(str(exc))
    return render('goal_work/outputs.html',sources=sources,source_ids=ids,rows=rows,outputs=saved,groups=groups.values(),errors=errors,empty_evidence=review.digest([]))


@bp.post('/entscheidung/<int:revision_id>')
def decide(revision_id):
    source_id=request.form.get('source',type=int)
    try:
        followups.decide(get_db(),revision_id,request.form.get('case_id') or None,outcome=request.form.get('outcome'),
            reason=request.form.get('reason',''),expected_evidence=request.form.get('evidence',''),
            recipient_email=request.form.get('recipient_email',''),requested_at=request.form.get('requested_at',''),
            corrected_document_id=request.form.get('corrected_document_id',type=int),user_id=actor())
        flash('Entscheidung gespeichert. Es wurde keine Nachricht versendet.','success')
    except ValueError as exc:
        flash(str(exc),'error')
    return redirect(url_for('goal_work.outputs',source=source_id,back=back_link()))


@bp.post('/zustaendigkeit/<path:case_id>')
def responsibility(case_id):
    try:
        assign_review(get_db(),case_id,manager_pn=request.form.get('manager_pn',''),form_org_source=request.form.get('form_org_source',''),
            period_start=request.form.get('period_start',''),period_end=request.form.get('period_end',''),
            expected_revision=request.form.get('revision',type=int),reason=request.form.get('reason',''),user_id=actor())
        flash('Rückblick-Zuständigkeit gespeichert. Vorhandene Ausgaben bleiben erhalten und müssen erneut geprüft werden.','success')
    except ValueError as exc:
        flash(str(exc),'error')
    return redirect(url_for('goal_work.outputs',source=request.form.getlist('source'),back=back_link()))


@bp.get('/ausgabe/<int:output_id>')
def download_output(output_id):
    row=get_db().execute('SELECT stored_path FROM hr_goal_outputs WHERE id=?',(output_id,)).fetchone()
    if not row or not Path(row[0]).is_file():
        abort(404)
    return send_file(row[0],as_attachment=True)


@bp.get('/versand')
def dispatches():
    page=max(1,request.args.get('page',1,type=int));state=request.args.get('state','open')
    where="WHERE status NOT IN ('sent_confirmed','cancelled')" if state=='open' else ''
    total=get_db().execute('SELECT COUNT(*) FROM hr_goal_dispatches '+where).fetchone()[0]
    rows=get_db().execute('SELECT * FROM hr_goal_dispatches '+where+' ORDER BY id DESC LIMIT 25 OFFSET ?',((page-1)*25,)).fetchall()
    return render('goal_work/dispatches.html',rows=rows,total=total,page=page,state=state)


@bp.route('/versand/<int:dispatch_id>',methods=['GET','POST'])
def dispatch(dispatch_id):
    db=get_db()
    try:
        group=delivery.get(db,dispatch_id)
    except ValueError:
        abort(404)
    if request.method=='POST':
        try:
            delivery.act(db,dispatch_id,action=request.form.get('action'),template_paths=current_app.config['WORD_TEMPLATE_PATHS'],
                lock_root=root('locks'),sender_email=current_app.config.get('HR_MAILBOX_EMAIL',''),
                subject=request.form.get('subject',''),body=request.form.get('body',''),checked=request.form.get('checked')=='yes',
                reason=request.form.get('reason',''),user_id=actor())
            flash('Versandstand gespeichert. Ein Outlook-Entwurf ist noch kein bestätigter Versand.','success')
        except ValueError as exc:
            flash(str(exc),'error')
        return redirect(url_for('goal_work.dispatch',dispatch_id=dispatch_id,back=back_link()))
    outputs=[]
    for row in delivery.members(db,dispatch_id):
        row['inputs']=json.loads(row['inputs_json']);row['error']=''
        try:
            followups.validate_output(db,row['id'],current_app.config['WORD_TEMPLATE_PATHS'])
        except (ValueError,OSError) as exc:
            row['error']=str(exc)
        outputs.append(row)
    events=db.execute('SELECT * FROM hr_goal_events WHERE dispatch_id=? ORDER BY id',(dispatch_id,)).fetchall()
    return render('goal_work/dispatch.html',group=group,outputs=outputs,events=events)
