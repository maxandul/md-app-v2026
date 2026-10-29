"""Grouped Outlook drafts: a prepared group is neither a draft nor a sent mail."""
from pathlib import Path
from . import goal_review as review
from . import goal_followups as followups
from .part_responsibilities import stamp
from .outlook_lock import package_lock, serialized_goal_delivery
from .word_dispatch import _mail_html
from webapp.adapters.outlook import OutlookDraftAdapter


def prepare(connection,output_ids,template_paths,*,user_id=None):
    groups={}
    excluded=[]
    existing=set()
    connection.execute('BEGIN IMMEDIATE')
    try:
        for output_id in dict.fromkeys(output_ids):
            try:
                output,data=followups.validate_output(connection,output_id,template_paths)
                if not output['approved_at']:
                    raise ValueError('Ausgabe zuerst am erzeugten Dokument prüfen.')
                current=followups.output_dispatch(connection,output_id)
                if current:
                    existing.add(current['id'])
                    continue
                if not data['recipient_email'] or '@' not in data['recipient_email']:
                    raise ValueError('Die E-Mail-Adresse der Rückblick-Verantwortung fehlt.')
                groups.setdefault((data['manager_pn'],data['recipient_email']),[]).append((output,data))
            except (ValueError,OSError) as exc:
                excluded.append({'output_id':output_id,'error':str(exc)})
        for (manager,email),items in groups.items():
            names='\n'.join(f"• {d['first_name']} {d['last_name']} (Ans. {d['employment_assignment']})" for _,d in items)
            subject=f'MD: {len(items)} aktualisierte Rückblicke'
            body=f"Hallo {items[0][1]['manager_name']}\n\nIm Anhang erhältst du aktualisierte Rückblicke für:\n{names}\n\nBitte verwende diese Fassungen. Falls du bisherige Formulare bereits bearbeitet hast, gleiche die Inhalte vor dem Ersetzen ab.\n\nFreundliche Grüsse\nHR"
            cur=connection.execute('''INSERT INTO hr_goal_dispatches(manager_pn,recipient_email,subject,body_text,user_id,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?)''',(manager,email,subject,body,user_id,stamp(),stamp()))
            group_id=cur.lastrowid
            for output,_ in items:
                connection.execute('INSERT INTO hr_goal_dispatch_outputs VALUES (?,?)',(group_id,output['id']))
            review.event(connection,'dispatch_prepared',dispatch_id=group_id,user_id=user_id,outputs=[o['id'] for o,_ in items])
            existing.add(group_id)
        connection.commit()
        return sorted(existing),excluded
    except Exception:
        connection.rollback()
        raise


def get(connection,dispatch_id):
    row=connection.execute('SELECT * FROM hr_goal_dispatches WHERE id=?',(dispatch_id,)).fetchone()
    if not row:
        raise ValueError('Versandgruppe nicht gefunden.')
    return dict(row)


def members(connection,dispatch_id):
    return [dict(r) for r in connection.execute('''SELECT o.* FROM hr_goal_outputs o
        JOIN hr_goal_dispatch_outputs m ON m.output_id=o.id WHERE m.dispatch_id=? ORDER BY o.id''',(dispatch_id,))]


@serialized_goal_delivery
def act(connection,dispatch_id,*,action,template_paths,lock_root,sender_email='',subject='',body='',
        checked=False,reason='',user_id=None,adapter=None):
    # Shared lock covers overlapping groups and interrupted Outlook calls.
    with package_lock(Path(lock_root)/'goal-dispatch'):
        connection.execute('BEGIN IMMEDIATE')
        try:
            group=get(connection,dispatch_id)
            outputs=members(connection,dispatch_id)
            if action in ('sent_confirmed','cancelled'):
                if not checked:
                    raise ValueError('Bitte den tatsächlichen Outlook-Stand prüfen und den Nachweis festhalten.')
                if group['status']==action:
                    connection.rollback()
                    return
                allowed=('processing','draft_created','failed') if action=='sent_confirmed' else ('prepared','processing','draft_created','failed')
                if group['status'] not in allowed:
                    raise ValueError('Dieser Versandstand kann nicht so abgeschlossen werden.')
                # Confirm the historical external effect even if data changed afterwards.
                connection.execute('UPDATE hr_goal_dispatches SET status=?,resolution_note=?,user_id=?,updated_at=? WHERE id=?',
                                   (action,reason.strip(),user_id,stamp(),dispatch_id))
                review.event(connection,action,dispatch_id=dispatch_id,user_id=user_id,reason=reason,outputs=[r['id'] for r in outputs])
                connection.commit()
                return
            if action!='draft' or group['status']!='prepared':
                raise ValueError('Bestehenden Outlook-Vorgang zuerst klären; es wird kein zweiter Entwurf erstellt.')
            if not outputs or not checked:
                raise ValueError('Empfänger, enthaltene Dokumente und Nachricht zuerst prüfen.')
            if '@' not in sender_email or not subject.strip() or not body.strip():
                raise ValueError('HR-Absender, Betreff und Nachricht sind erforderlich.')
            for output in outputs:
                _,data=followups.validate_output(connection,output['id'],template_paths)
                if (data['manager_pn'],data['recipient_email'])!=(group['manager_pn'],group['recipient_email']):
                    raise ValueError('Empfänger geändert. Gruppe abbrechen und Auswahl erneut prüfen.')
                if not output['approved_at']:
                    raise ValueError('Eine Ausgabe wurde noch nicht geprüft.')
                if connection.execute('''SELECT 1 FROM hr_goal_dispatches d
                    JOIN hr_goal_dispatch_outputs m ON m.dispatch_id=d.id JOIN hr_goal_outputs o ON o.id=m.output_id
                    WHERE o.case_id=? AND d.id<>? AND d.status IN ('processing','draft_created','failed')''',
                    (output['case_id'],dispatch_id)).fetchone():
                    raise ValueError('Für diese Person ist ein anderer Outlook-Vorgang offen.')
                if connection.execute("SELECT 1 FROM word_person_corrections p,json_each(p.manifest_json,'$.documents') j WHERE p.case_id=? AND p.status IN ('processing','draft_created','failed') AND json_extract(j.value,'$.kind') IN ('review','probation')",(output['case_id'],)).fetchone():
                    raise ValueError('Für diese Person ist eine bisherige Einzelkorrektur in Outlook offen.')
                if connection.execute('''SELECT 1 FROM word_mail_deliveries d JOIN word_dispatch_packages p ON p.id=d.package_id,
                    json_each(p.manifest_json,'$.documents') j WHERE json_extract(j.value,'$.case_id')=?
                    AND json_extract(j.value,'$.kind') IN ('review','probation') AND d.status IN ('processing','draft_created','failed')''',(output['case_id'],)).fetchone():
                    raise ValueError('Für diese Person ist ein bisheriges Führungskräftepaket in Outlook offen.')
            connection.execute("UPDATE hr_goal_dispatches SET status='processing',subject=?,body_text=?,sender_email=?,updated_at=? WHERE id=?",
                               (subject.strip(),body.strip(),sender_email,stamp(),dispatch_id))
            review.event(connection,'outlook_started',dispatch_id=dispatch_id,user_id=user_id)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        try:
            result=(adapter or OutlookDraftAdapter()).create_encrypted_draft(sender_email=sender_email,
                recipient_email=group['recipient_email'],subject=subject.strip(),body_html=_mail_html(body),
                attachments=[Path(o['stored_path']) for o in outputs])
            if not result.encryption_flag_verified:
                raise ValueError('Verschlüsselungsmarkierung nicht bestätigt. Bestehenden Outlook-Vorgang prüfen.')
            with connection:
                connection.execute("UPDATE hr_goal_dispatches SET status='draft_created',outlook_entry_id=?,updated_at=? WHERE id=?",
                                   (result.entry_id,stamp(),dispatch_id))
                review.event(connection,'draft_created',dispatch_id=dispatch_id,user_id=user_id,entry_id=result.entry_id)
        except Exception as exc:
            with connection:
                connection.execute("UPDATE hr_goal_dispatches SET status='failed',error_message=?,updated_at=? WHERE id=?",
                                   (str(exc),stamp(),dispatch_id))
            raise ValueError(f'Outlook-Ausgang unklar: {exc}. Bestehenden Vorgang prüfen, bevor du ihn erneut vorbereitest.') from exc
