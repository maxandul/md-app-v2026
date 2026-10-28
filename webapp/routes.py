"""HTTP-Routen der lokalen MD-Verwaltungsanwendung."""

from __future__ import annotations

import json
import secrets
import shutil
import uuid
from io import BytesIO
from datetime import datetime
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from .auth import audit, login_required, system_admin_required
from .db import close_db, connect_database, get_db
from .services import hr_workflow as workflow
from .services.mail_schedule import run_scan, schedule_state
from .services.cycles import (
    CYCLE_STATUS_LABELS,
    change_cycle_status,
    create_cycle,
    cycle_overview,
    dashboard_data,
    manager_case_overview,
    synchronize_open_cycles,
)
from .services.cockpit import cockpit_overview
from .services.dialog_events import (
    EVENT_TYPE_LABELS,
    SCOPE_LABELS,
    create_manual_event,
    dialog_event_rows,
    set_leading_sap_event,
)
from .services.packages import (
    create_package_batch,
    create_package_file,
    create_replacement_package_file,
    create_update_file,
    import_returned_package,
    manager_package_state,
)
from .services.documents import (
    confirm_digital_signature,
    import_handwritten_scan,
    import_official_pdf,
    inspect_pdf,
)
from .services.sap_import import import_sap_workbook
from .services.word_pdf import inspect_word_pdf
from .services.word_pdf_imports import stage_pdf, matching_cases, confirm_import
from .services.legacy_forms import COMPETENCY_TAGS
from .services.word_packages import create_word_package, word_template_status
from .services.word_dispatch import DEFAULT_WORD_SUBJECT, DEFAULT_WORD_BODY, word_message, discard_word_package, prepare_word_batch, word_dispatch_candidates, dispatch_word_packages, confirm_word_draft_sent, discard_word_draft
from .services.sap_export import (
    create_sap_upload_batch,
    get_sap_export_batch,
    sap_export_batches,
)
from .services.mail_dispatch import create_outlook_drafts, dispatch_candidates
from .services.mail_intake import (
    mail_inbox_overview,
    resolve_inbound_message,
    scan_outlook_inbox,
)
from .services.feedback import feedback_overview
from .services import word_feedback
from .services.case_review import case_review_detail, correct_case_data
from .services.deadlines import extend_deadlines
from .services.reminders import (
    confirm_reminder_sent,
    create_reminder_drafts,
    reminder_candidates,
)
from .services.analytics import analysis_options, analytics_csv, analytics_data
from .services.operations import (
    audit_rows,
    create_system_backup,
    list_backups,
    restore_system_backup,
)


bp = Blueprint("main", __name__)


@bp.before_request
@login_required
def protect_hr_cockpit():
    """Alle fachlichen Routen verlangen ein persönliches HR-Konto."""
    if not current_app.config.get("AUTH_DISABLED") and g.user and g.user["password_temporary"]:
        return redirect(url_for("auth.change_password"))
    chosen = request.args.get('cycle_id',type=int) or (request.view_args or {}).get('cycle_id')
    if chosen and get_db().execute('SELECT 1 FROM cycles WHERE id=?',(chosen,)).fetchone():
        session['active_cycle_id']=chosen
    return None


@bp.url_defaults
def preserve_cycle(endpoint, values):
    if endpoint in {'main.dashboard','main.dialogs','main.dispatch','main.returns_overview','main.worklist','main.analytics'} and 'cycle_id' not in values and not values.get('unassigned') and session.get('active_cycle_id'):
        values['cycle_id']=session['active_cycle_id']


def _storage_dir(name: str) -> Path:
    path = Path(current_app.config["STORAGE_ROOT"]) / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _handoff_dir() -> Path:
    path = Path(current_app.config["DOSSIER_HANDOFF_ROOT"])
    path.mkdir(parents=True, exist_ok=True)
    return path


def _stored_name(original: str) -> str:
    safe = secure_filename(original) or "datei"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{uuid.uuid4().hex[:8]}_{safe}"


def _backup_root() -> Path:
    path = Path(current_app.config["BACKUP_ROOT"])
    path.mkdir(parents=True, exist_ok=True)
    return path


def _manager_pns_for_org_unit(connection, cycle_id: int, org_unit: str) -> list[str]:
    """Löst eine OE in alle darunterliegenden Führungskräfte des Durchlaufs auf."""
    from webapp.migrations import available as parts_available
    part_managers=set()
    if parts_available(connection):
        part_managers={r['manager_pn'] for r in connection.execute('''SELECT DISTINCT o.manager_pn FROM hr_resolved_obligations o
            JOIN employees m ON m.pn=o.manager_pn WHERE o.cycle_id=? AND o.active=1 AND o.required=1
            AND o.event_status<>'cancelled' AND (o.form_org_unit=? OR m.org_unit=?) ORDER BY o.manager_pn''',(cycle_id,org_unit,org_unit))}
    available = {
        row["manager_pn"]
        for row in connection.execute(
            "SELECT DISTINCT manager_pn FROM dialog_cases WHERE cycle_id = ? AND active = 1",
            (cycle_id,),
        ).fetchall()
    }
    frontier = {
        row["pn"]
        for row in connection.execute(
            "SELECT pn FROM employees WHERE active = 1 AND org_unit = ?",
            (org_unit,),
        ).fetchall()
    }
    selected = available.intersection(frontier)
    while frontier:
        placeholders = ",".join("?" for _ in frontier)
        reports = {
            row["employee_pn"]
            for row in connection.execute(
                f"""
                SELECT employee_pn FROM dialog_cases
                WHERE cycle_id = ? AND active = 1
                  AND manager_pn IN ({placeholders})
                """,
                (cycle_id, *frontier),
            ).fetchall()
        }
        next_frontier = reports.intersection(available).difference(selected)
        selected.update(next_frontier)
        frontier = next_frontier
    return sorted(selected|part_managers)


@bp.get("/")
def dashboard():
    selected_cycle_id = request.args.get("cycle_id", type=int)
    return render_template(
        "dashboard.html",
        now_year=request.args.get('next_year',datetime.now().year,type=int),
        active_nav="overview",
        **cockpit_overview(get_db(), selected_cycle_id=selected_cycle_id),
    )


@bp.get("/stammdaten")
def master_data():
    if current_app.config.get('HR_GOAL_WORKFLOW') and request.args.get('history')!='yes':return redirect(url_for('sap_work.index'))
    return render_template(
        "master_data.html",
        active_nav="master_data",
        **dashboard_data(get_db()),
    )


@bp.get("/dialoge")
def dialogs():
    connection = get_db()
    data = dashboard_data(connection)
    selected_cycle_id = request.args.get("cycle_id", type=int)
    unassigned = request.args.get('unassigned') == 'yes'
    if unassigned:
        selected_cycle_id = None
    if selected_cycle_id is None and data["cycles"] and not unassigned and not current_app.config.get('HR_GOAL_WORKFLOW'):
        selected_cycle_id = data["cycles"][0]["id"]
    query = request.args.get("q", "").strip()
    event_type = request.args.get("event_type", "").strip()
    event_status = request.args.get("status", "").strip()
    page = max(1, request.args.get("page", default=1, type=int) or 1)
    per_page = 50
    all_events = dialog_event_rows(connection, selected_cycle_id)
    if unassigned:
        all_events = [item for item in all_events if item["cycle_id"] is None]
    if query:
        needle = query.casefold()
        all_events = [
            item for item in all_events
            if needle in " ".join(
                str(item.get(key, "")) for key in (
                    "first_name", "last_name", "employee_pn", "assignment_number",
                    "manager_name", "manager_pn", "part_search_text",
                )
            ).casefold()
        ]
    if event_type:
        all_events = [item for item in all_events if item["event_type"] == event_type]
    if event_status:
        all_events = [item for item in all_events if item["status"] == event_status]
    event_total = len(all_events)
    event_pages = max(1, (event_total + per_page - 1) // per_page)
    page = min(page, event_pages)
    events = all_events[(page - 1) * per_page:page * per_page]
    selected_cycle = next(
        (cycle for cycle in data["cycles"] if cycle["id"] == selected_cycle_id), None
    )
    return render_template(
        "dialogs.html",
        active_nav="dialogs",
        now_year=request.args.get('next_year',datetime.now().year,type=int),
        selected_cycle_id=selected_cycle_id,
        selected_cycle=selected_cycle,
        events=events,
        event_total=event_total,
        unassigned=unassigned,
        event_page=page,
        event_pages=event_pages,
        event_query=query,
        selected_event_type=event_type,
        selected_event_status=event_status,
        cycle_status_labels=CYCLE_STATUS_LABELS,
        reminder_rows=(
            reminder_candidates(
                connection,
                cycle_id=selected_cycle_id,
                sender_email=current_app.config["HR_MAILBOX_EMAIL"],
            )
            if selected_cycle_id else []
        ),
        employee_choices=connection.execute("SELECT a.id,a.assignment_number,a.org_unit,a.position,e.first_name,e.last_name,a.person_number FROM employment_assignments a JOIN employees e ON e.pn=a.person_number WHERE a.active=1 ORDER BY e.last_name,e.first_name,a.org_unit,a.assignment_number").fetchall(),
        manager_choices=connection.execute("SELECT pn,first_name,last_name,org_unit FROM employees WHERE active=1 ORDER BY last_name,first_name,pn").fetchall(),
        event_types=EVENT_TYPE_LABELS,
        scopes=SCOPE_LABELS,
        **data,
    )


@bp.post("/cycles/<int:cycle_id>/deadlines")
def change_deadlines(cycle_id: int):
    try:
        result = extend_deadlines(
            get_db(),
            cycle_id=cycle_id,
            scope=request.form.get("scope", ""),
            document_kind=request.form.get("document_kind", ""),
            new_due_date=request.form.get("new_due_date", ""),
            reason=request.form.get("reason", ""),
            user_id=g.user["id"] if g.user else None,
            manager_pn=request.form.get("manager_pn", ""),
            case_id=request.form.get("case_id", ""),
        )
    except (LookupError, ValueError) as exc:
        flash(str(exc), "error")
    else:
        audit(
            "deadlines_extended", "cycle", str(cycle_id),
            scope=result["scope"], document_kind=result["document_kind"],
            new_due_date=result["new_due_date"], changed=result["changed"],
            reason=result["reason"],
        )
        flash(f"{result['changed']} Frist(en) wurden nachvollziehbar angepasst.", "success")
    return redirect(request.referrer or url_for("main.dialogs", cycle_id=cycle_id))


@bp.post("/cycles/<int:cycle_id>/reminder-drafts")
def prepare_reminder_drafts(cycle_id: int):
    manager_pns = request.form.getlist("manager_pn")
    if request.form.get("selection") == "all":
        manager_pns = [
            item["manager_pn"] for item in reminder_candidates(
                get_db(), cycle_id=cycle_id,
                sender_email=current_app.config["HR_MAILBOX_EMAIL"],
            ) if item["ready"]
        ]
    try:
        result = create_reminder_drafts(
            get_db(), cycle_id=cycle_id,
            manager_pns=manager_pns,
            sender_email=current_app.config["HR_MAILBOX_EMAIL"],
        )
    except (LookupError, ValueError) as exc:
        flash(str(exc), "error")
    else:
        if result["created"]:
            audit(
                "reminder_drafts_created", "cycle", str(cycle_id),
                created=result["created"],
            )
            flash(
                f"{result['created']} S/MIME-markierte(r) Erinnerungsentwurf/-entwürfe "
                "wurden erstellt. Bitte in Outlook prüfen und manuell senden.",
                "success",
            )
        if result["failed"]:
            flash(
                f"{result['failed']} Entwurf/Entwürfe konnten nicht erstellt werden: "
                + " ".join(result["errors"]),
                "error",
            )
    return redirect(url_for("main.dialogs", cycle_id=cycle_id))


@bp.post("/reminders/<int:reminder_id>/sent-confirmed")
def mark_reminder_sent(reminder_id: int):
    try:
        reminder = confirm_reminder_sent(get_db(), reminder_id=reminder_id)
    except (LookupError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(request.referrer or url_for("main.dialogs"))
    audit(
        "reminder_sent_confirmed", "reminder", str(reminder_id),
        cycle_id=reminder["cycle_id"], manager_pn=reminder["manager_pn"],
    )
    flash("Der manuelle Versand wurde bestätigt.", "success")
    return redirect(url_for("main.dialogs", cycle_id=reminder["cycle_id"]))


@bp.post("/dialog-events")
def add_dialog_event():
    cycle_id = request.form.get("cycle_id", type=int)
    try:
        employee_pn=request.form.get('employee_pn','')
        assignment_number=request.form.get('assignment_number','')
        if 'employment_id' in request.form:
            employment=get_db().execute('SELECT person_number,assignment_number FROM employment_assignments WHERE id=? AND active=1',(request.form.get('employment_id'),)).fetchone()
            if not employment: raise ValueError('Bitte eine mitarbeitende Person mit Anstellung auswählen.')
            employee_pn,assignment_number=employment['person_number'],employment['assignment_number']
        event_id = create_manual_event(
            get_db(),
            employee_pn=employee_pn,
            assignment_number=assignment_number,
            manager_pn=request.form.get("manager_pn", ""),
            event_type=request.form.get("event_type", ""),
            required_scope=request.form.get("required_scope", ""),
            review_year=int(request.form.get("review_year", "")),
            period_start=request.form.get("period_start", ""),
            period_end=request.form.get("period_end", ""),
            reason=request.form.get("reason", ""),
            dialog_date=request.form.get("dialog_date", ""),
            review_due_date=request.form.get("review_due_date", ""),
            outlook_due_date=request.form.get("outlook_due_date", ""),
            cycle_id=cycle_id,
            form_org_source=request.form.get("form_org_source","employee"),
        )
    except (TypeError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.dialogs", cycle_id=cycle_id) if cycle_id else url_for("main.dialogs"))
    audit(
        "dialog_event_created", "dialog_event", str(event_id),
        cycle_id=cycle_id, event_type=request.form.get("event_type", ""),
    )
    flash(f"Dialogereignis {event_id} wurde angelegt.", "success")
    return redirect(url_for("main.dialogs", cycle_id=cycle_id) if cycle_id else url_for("main.dialogs"))


@bp.post("/dialog-events/<int:event_id>/leading-sap")
def mark_leading_sap_event(event_id: int):
    try:
        set_leading_sap_event(get_db(), event_id)
    except ValueError as exc:
        flash(str(exc), "error")
    else:
        flash("Das führende SAP-Ereignis wurde festgelegt.", "success")
    return redirect(request.referrer or url_for("main.dialogs"))


@bp.get("/versand")
def dispatch():
    data = cockpit_overview(
        get_db(), selected_cycle_id=request.args.get("cycle_id", type=int)
    )
    managers = []
    if data["selected_cycle"]:
        _cycle, managers = cycle_overview(get_db(), data["selected_cycle"]["id"])
        connection = get_db()
        enriched = []
        for row in managers:
            item = dict(row)
            state = manager_package_state(
                connection,
                cycle_id=data["selected_cycle"]["id"],
                manager_pn=item["manager_pn"],
            )
            item["package_state"] = state["state"]
            item["package_label"] = state["label"]
            item["package_issues"] = state["issues"]
            item["package_blocking"] = state["blocking"]
            item["org_unit"] = connection.execute(
                """
                SELECT COALESCE(NULLIF(m.org_unit, ''), MIN(dc_employee.org_unit), '') AS org_unit
                FROM dialog_cases dc
                LEFT JOIN employees m ON m.pn = dc.manager_pn
                LEFT JOIN employees dc_employee ON dc_employee.pn = dc.employee_pn
                WHERE dc.cycle_id = ? AND dc.manager_pn = ?
                """,
                (data["selected_cycle"]["id"], item["manager_pn"]),
            ).fetchone()["org_unit"]
            enriched.append(item)
        managers = enriched
    org_units = sorted({row["org_unit"] for row in managers if row["org_unit"]})
    mail_candidates = []
    if data["selected_cycle"]:
        mail_candidates = dispatch_candidates(
            get_db(),
            cycle_id=data["selected_cycle"]["id"],
            sender_email=current_app.config["HR_MAILBOX_EMAIL"],
        )
    return render_template(
        "dispatch_legacy.html" if request.args.get('workflow')=='workbook' and current_app.config.get('LEGACY_WORKBOOKS')=='enabled' else "dispatch.html",
        active_nav="dispatch", managers=managers,
        default_word_subject=DEFAULT_WORD_SUBJECT, default_word_body=DEFAULT_WORD_BODY,
        word_candidates=word_dispatch_candidates(get_db(),cycle_id=data['selected_cycle']['id'],template_paths=current_app.config['WORD_TEMPLATE_PATHS']) if data['selected_cycle'] else [],
        word_templates=word_template_status(current_app.config['WORD_TEMPLATE_PATHS']),
        hr_sender=current_app.config['HR_MAILBOX_EMAIL'],
        org_units=org_units, mail_candidates=mail_candidates, **data
    )


@bp.get("/ruecklaeufe")
def returns_overview():
    connection = get_db()
    cockpit = cockpit_overview(
        connection, selected_cycle_id=request.args.get("cycle_id", type=int)
    )
    selected_cycle = cockpit.get("selected_cycle")
    return render_template(
        "returns.html",
        mail_schedule=schedule_state(connection),
        **workflow.pdf_queue(connection,query=request.args.get('pdf_q',''),status=request.args.get('pdf_status','pending'),page=request.args.get('pdf_page',1,type=int)),
        active_nav="returns",
        **cockpit,
        feedback_collections=word_feedback.collections(connection),
        feedback_bundles=feedback_overview(
            connection,
            cycle_id=selected_cycle["id"] if selected_cycle else None,
        ),
        **mail_inbox_overview(
            connection,
            page=request.args.get("mail_page", default=1, type=int) or 1,
            query=request.args.get("mail_q", ""),
            status=request.args.get("mail_status", ""),
        ),
    )


@bp.get("/sap-export")
def sap_exports():
    connection = get_db()
    return render_template(
        "sap_exports.html",
        active_nav="sap_export",
        cycle_status_labels=CYCLE_STATUS_LABELS,
        export_batches=sap_export_batches(connection),
        **dashboard_data(connection),
    )


@bp.get("/auswertungen")
def analytics():
    connection = get_db()
    cycle_id = request.args.get("cycle_id", type=int)
    org_unit = request.args.get("org_unit", "").strip()
    event_type = request.args.get("event_type", "").strip()
    minimum_group_size = current_app.config["ANALYTICS_MIN_GROUP_SIZE"]
    return render_template(
        "analytics.html",
        active_nav="analytics",
        selected_cycle_id=cycle_id,
        selected_org_unit=org_unit,
        selected_event_type=event_type,
        **analysis_options(connection),
        **analytics_data(
            connection, cycle_id=cycle_id, org_unit=org_unit,
            event_type=event_type, minimum_group_size=minimum_group_size,
        ),
    )


@bp.post('/hr-followups/<case_id>/<topic>')
def save_hr_followup(case_id,topic):
    status=request.form.get('status','')
    if topic not in ('career','higher_manager','permissions') or status not in ('offen','kontaktiert','abgeschlossen'): abort(400)
    db=get_db()
    if not db.execute('SELECT 1 FROM dialog_cases WHERE case_id=?',(case_id,)).fetchone(): abort(404)
    try:
        db.execute('BEGIN IMMEDIATE')
        previous=db.execute('SELECT updated_at FROM hr_followups WHERE case_id=? AND topic=?',(case_id,topic)).fetchone()
        if (previous['updated_at'] if previous else '') != request.form.get('revision',''):
            raise ValueError('Der Kontaktstatus wurde inzwischen geändert. Bitte neu laden.')
        db.execute("""INSERT INTO hr_followups(case_id,topic,status,note,updated_at) VALUES (?,?,?,?,?)
            ON CONFLICT(case_id,topic) DO UPDATE SET status=excluded.status,note=excluded.note,updated_at=excluded.updated_at""",
            (case_id,topic,status,request.form.get('note','').strip(),workflow.stamp()))
        db.commit();audit('hr_followup_updated','dialog_case',case_id,topic=topic,status=status)
        flash('Kontaktstatus gespeichert.','success')
    except ValueError as exc:
        db.rollback();flash(str(exc),'error')
    return redirect(url_for('main.analytics',cycle_id=request.form.get('cycle_id'),org_unit=request.form.get('org_unit',''),event_type=request.form.get('event_type',''))+'#hr-klaerungen')


@bp.get("/administration")
@system_admin_required
def administration():
    import socket
    hostname = socket.gethostname()
    port = current_app.config.get('SERVER_BIND_PORT')
    return render_template(
        "administration.html", active_nav="administration",
        server_hostname=hostname,
        public_base_url=current_app.config.get('PUBLIC_BASE_URL',''),
        server_bind_host=current_app.config.get('SERVER_BIND_HOST','Nicht vom Starter gemeldet'),
        server_bind_port=port,
        hostname_url=('http://' + hostname + ':' + str(port)) if port else '',
        audit_entries=audit_rows(get_db()), backups=list_backups(_backup_root()),
    )


@bp.post("/administration/backups")
@system_admin_required
def create_backup():
    result = create_system_backup(
        get_db(), database_path=Path(current_app.config["DATABASE"]),
        storage_root=Path(current_app.config["STORAGE_ROOT"]),
        dossier_root=Path(current_app.config["DOSSIER_HANDOFF_ROOT"]),
        backup_root=_backup_root(),
    )
    audit(
        "system_backup_created", "backup", result["filename"],
        sha256=result["sha256"], file_count=result["file_count"],
    )
    return send_file(
        result["path"], as_attachment=True, download_name=result["filename"],
        mimetype="application/zip",
    )


@bp.post("/administration/backups/<path:filename>/download")
@system_admin_required
def download_backup(filename: str):
    if filename != Path(filename).name:
        abort(404)
    path = _backup_root() / filename
    if not path.is_file() or not filename.startswith("MD_Backup_"):
        abort(404)
    audit("system_backup_downloaded", "backup", filename)
    return send_file(path, as_attachment=True, download_name=filename, mimetype="application/zip")


@bp.post("/administration/restore")
@system_admin_required
def restore_backup():
    request.max_content_length = current_app.config["MAX_BACKUP_CONTENT_LENGTH"]
    upload = request.files.get("backup_file")
    if not upload or not upload.filename or not upload.filename.lower().endswith(".zip"):
        flash("Bitte wähle eine MD-Backup-ZIP-Datei aus.", "error")
        return redirect(url_for("main.administration"))
    if request.form.get("confirmation", "").strip() != "WIEDERHERSTELLEN":
        flash("Bitte bestätige den Restore mit WIEDERHERSTELLEN.", "error")
        return redirect(url_for("main.administration"))
    backup_root = _backup_root()
    uploaded_path = backup_root / f"Restore_Upload_{uuid.uuid4().hex}.zip"
    upload.save(uploaded_path)
    current_email = g.user["email"] if g.user else ""
    try:
        safety = create_system_backup(
            get_db(), database_path=Path(current_app.config["DATABASE"]),
            storage_root=Path(current_app.config["STORAGE_ROOT"]),
            dossier_root=Path(current_app.config["DOSSIER_HANDOFF_ROOT"]),
            backup_root=backup_root,
        )
        audit(
            "system_restore_started", "backup", upload.filename,
            safety_backup=safety["filename"],
        )
        close_db()
        result = restore_system_backup(
            uploaded_path, database_path=Path(current_app.config["DATABASE"]),
            storage_root=Path(current_app.config["STORAGE_ROOT"]),
            dossier_root=Path(current_app.config["DOSSIER_HANDOFF_ROOT"]),
        )
        restored = connect_database(current_app.config["DATABASE"])
        try:
            user = restored.execute(
                "SELECT id FROM app_users WHERE email = ? COLLATE NOCASE", (current_email,)
            ).fetchone()
            restored.execute(
                """
                INSERT INTO audit_log (user_id, action, object_type, object_id, details_json, created_at)
                VALUES (?, 'system_restore_completed', 'backup', ?, ?, ?)
                """,
                (
                    user["id"] if user else None, upload.filename,
                    json.dumps({"source_created_at": result["created_at"], "safety_backup": safety["filename"]}, ensure_ascii=False),
                    datetime.now().astimezone().isoformat(timespec="seconds"),
                ),
            )
            restored.commit()
        finally:
            restored.close()
    except (OSError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.administration"))
    finally:
        uploaded_path.unlink(missing_ok=True)
    session.clear()
    flash("Das Backup wurde wiederhergestellt. Bitte melde dich erneut an.", "success")
    return redirect(url_for("auth.login"))


@bp.post("/auswertungen/export")
def export_analytics():
    report = request.form.get("report", "")
    cycle_id = request.form.get("cycle_id", type=int)
    org_unit = request.form.get("org_unit", "").strip()
    event_type = request.form.get("event_type", "").strip()
    try:
        data = analytics_data(
            get_db(), cycle_id=cycle_id, org_unit=org_unit, event_type=event_type,
            minimum_group_size=current_app.config["ANALYTICS_MIN_GROUP_SIZE"],
        )
        filename, content = analytics_csv(report, data)
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for(
            "main.analytics", cycle_id=cycle_id, org_unit=org_unit,
            event_type=event_type,
        ))
    audit(
        "analytics_exported", "analytics", report,
        cycle_id=cycle_id, org_unit=org_unit, event_type=event_type,
        row_count=len(data["followups"] if report == "followups" else data["career_requests"] if report == "career_requests" else data["form_fields"] if report == "form_fields" else data["timings"] if report == "timings" else data["ratings"] if report == "ratings" else data["competencies"]),
    )
    return send_file(
        BytesIO(content), as_attachment=True, download_name=filename,
        mimetype="text/csv; charset=utf-8",
    )


@bp.post("/imports")
def upload_sap_import():
    if current_app.config.get('HR_GOAL_WORKFLOW'):
        from .sap_routes import upload
        return upload()
    upload = request.files.get("sap_file")
    if not upload or not upload.filename:
        flash("Bitte wähle einen SAP-Excel-Export aus.", "error")
        return redirect(url_for("main.master_data"))
    if not upload.filename.lower().endswith(".xlsx"):
        flash("Der SAP-Import muss eine XLSX-Datei sein.", "error")
        return redirect(url_for("main.master_data"))

    stored_name = _stored_name(upload.filename)
    path = _storage_dir("sap_imports") / stored_name
    upload.save(path)
    try:
        result = import_sap_workbook(
            get_db(),
            path,
            original_filename=upload.filename,
            stored_filename=stored_name,
        )
    except Exception as exc:
        path.unlink(missing_ok=True)
        flash(str(exc), "error")
        return redirect(url_for("main.master_data"))

    message = (
        f"SAP-Import {result.import_id}: {result.employee_count} Personen und "
        f"{result.reporting_line_count} Führungslinien übernommen."
    )
    if result.ignored_bg_zero_count:
        message += f" {result.ignored_bg_zero_count} BG-0-Zeile(n) ignoriert."
    if result.exact_duplicate_count:
        message += f" {result.exact_duplicate_count} identische Dublette(n) dedupliziert."
    if result.conflict_count:
        message += f" {result.conflict_count} Konflikt(e) sind in der Prüfliste offen."
    if result.warnings:
        message += f" {len(result.warnings)} Hinweis(e) beachten."
    synchronized = synchronize_open_cycles(get_db(), sap_import_id=result.import_id)
    if synchronized["cycles"]:
        message += (
            f" {synchronized['cycles']} offene Durchlauf/Durchläufe aktualisiert: "
            f"{synchronized['added']} neue und {synchronized['deactivated']} nicht mehr "
            "aktive Führungslinie(n)."
        )
    audit(
        "sap_import_completed", "sap_import", str(result.import_id),
        employee_count=result.employee_count,
        reporting_line_count=result.reporting_line_count,
        exact_duplicate_count=result.exact_duplicate_count,
        conflict_count=result.conflict_count,
        synchronized_cycles=synchronized["cycles"],
    )
    flash(message, "success")
    return redirect(url_for("main.master_data"))


@bp.get("/imports/<int:import_id>")
def import_detail(import_id: int):
    connection = get_db()
    imported = connection.execute("SELECT * FROM sap_imports WHERE id = ?", (import_id,)).fetchone()
    if not imported:
        abort(404)
    issues = connection.execute(
        """
        SELECT * FROM sap_import_issues
        WHERE sap_import_id = ?
        ORDER BY CASE severity WHEN 'blocking' THEN 1 WHEN 'warning' THEN 2 ELSE 3 END,
                 person_number, employment_assignment, id
        """,
        (import_id,),
    ).fetchall()
    return render_template(
        "import_detail.html", imported=imported, issues=issues, active_nav="master_data"
    )


@bp.post("/cycles")
def add_cycle():
    try:
        review_year = int(request.form.get("review_year", ""))
        sap_import_id = int(request.form.get("sap_import_id", ""))
        cycle_id = create_cycle(
            get_db(), review_year=review_year, sap_import_id=sap_import_id
        )
    except (TypeError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.dialogs"))
    audit("cycle_created", "cycle", str(cycle_id), review_year=review_year)
    flash(f"Jahresprozess {review_year}/{review_year + 1} wurde angelegt.", "success")
    return redirect(url_for("main.cycle_detail", cycle_id=cycle_id))


@bp.get("/cycles/<int:cycle_id>")
def cycle_detail(cycle_id: int):
    try:
        cycle, managers = cycle_overview(get_db(), cycle_id)
    except LookupError:
        abort(404)
    manager_rows = []
    for row in managers:
        item = dict(row)
        state = manager_package_state(
            get_db(), cycle_id=cycle_id, manager_pn=item["manager_pn"]
        )
        item["package_state"] = state["state"]
        item["package_blocking"] = state["blocking"]
        manager_rows.append(item)
    return render_template(
        "cycle.html", cycle=cycle, managers=manager_rows,
        word_status={item['manager_pn']: item for item in word_dispatch_candidates(get_db(),cycle_id=cycle_id,template_paths=current_app.config['WORD_TEMPLATE_PATHS'])},
        export_batches=sap_export_batches(get_db(), cycle_id=cycle_id),
        closure_record=get_db().execute("SELECT * FROM workflow_cycle_closures WHERE cycle_id=?",(cycle_id,)).fetchone(),
        cycle_status_labels=CYCLE_STATUS_LABELS,
        active_nav="dialogs"
    )


@bp.post("/cycles/<int:cycle_id>/status")
def set_cycle_status(cycle_id: int):
    try:
        old_status, new_status = change_cycle_status(
            get_db(), cycle_id=cycle_id,
            new_status=request.form.get("status", "").strip(),
            closure_reason=request.form.get('closure_reason',''),closure_owner=request.form.get('closure_owner',''),external_checked=request.form.get('external_checked')=='yes',
        )
    except LookupError:
        abort(404)
    except ValueError as exc:
        flash(str(exc), "error")
    else:
        audit(
            "cycle_status_changed", "cycle", str(cycle_id),
            old_status=old_status, new_status=new_status,
        )
        flash(
            f"Der Durchlauf befindet sich jetzt in der Phase "
            f"«{CYCLE_STATUS_LABELS[new_status]}».",
            "success",
        )
    return redirect(url_for("main.cycle_detail", cycle_id=cycle_id))


@bp.get("/cycles/<int:cycle_id>/managers/<manager_pn>")
def manager_detail(cycle_id: int, manager_pn: str):
    try:
        cycle, manager, cases, events = manager_case_overview(
            get_db(), cycle_id, manager_pn
        )
    except LookupError:
        abort(404)
    return render_template(
        "manager.html",
        cycle=cycle,
        manager=manager,
        cases=cases,
        events=events,
        package_state=manager_package_state(
            get_db(), cycle_id=cycle_id, manager_pn=manager_pn
        ),
        word_templates=word_template_status(current_app.config["WORD_TEMPLATE_PATHS"]),
        word_packages=get_db().execute("SELECT id,created_at FROM word_dispatch_packages WHERE cycle_id=? AND manager_pn=? ORDER BY id DESC LIMIT 5", (cycle_id,manager_pn)).fetchall(),
        active_nav="dialogs",
    )


@bp.get("/cycles/<int:cycle_id>/cases/<case_id>")
def case_detail(cycle_id: int, case_id: str):
    try:
        detail = case_review_detail(get_db(), cycle_id=cycle_id, case_id=case_id)
    except LookupError:
        abort(404)
    return render_template(
        "case_detail.html", active_nav="dialogs", cycle_id=cycle_id, **detail
    )


@bp.post("/cycles/<int:cycle_id>/cases/<case_id>/correction")
def correct_case(cycle_id: int, case_id: str):
    try:
        changed = correct_case_data(
            get_db(),
            cycle_id=cycle_id,
            case_id=case_id,
            values={
                field: request.form.get(field, "")
                for field in (
                    "official_scope", "dialog_date", "period_start", "period_end",
                    "overall_rating_code", "agreement",
                )
            },
            reason=request.form.get("reason", ""),
            user_id=g.user["id"] if g.user else None,
        )
    except (LookupError, ValueError) as exc:
        flash(str(exc), "error")
    else:
        audit(
            "case_data_corrected", "dialog_case", case_id,
            fields=changed, reason=request.form.get("reason", "").strip(),
        )
        flash(f"{len(changed)} Angabe(n) wurden begründet korrigiert.", "success")
    return redirect(url_for("main.case_detail", cycle_id=cycle_id, case_id=case_id))


@bp.post("/cycles/<int:cycle_id>/cases/<case_id>/replacement-pdf")
def replace_case_pdf(cycle_id: int, case_id: str):
    upload = request.files.get("replacement_pdf")
    reason = request.form.get("replacement_reason", "").strip()
    if not upload or not upload.filename or not upload.filename.lower().endswith(".pdf"):
        flash("Bitte wähle eine korrigierte PDF-Datei aus.", "error")
        return redirect(url_for("main.case_detail", cycle_id=cycle_id, case_id=case_id))
    if len(reason) < 10:
        flash("Bitte begründe die Ersetzung mit mindestens 10 Zeichen.", "error")
        return redirect(url_for("main.case_detail", cycle_id=cycle_id, case_id=case_id))
    stored_name = _stored_name(upload.filename)
    temporary = _storage_dir("pdf_pending") / stored_name
    upload.save(temporary)
    try:
        inspection = inspect_pdf(temporary)
        if inspection.data.get("case_id", "") != case_id:
            raise ValueError("Die korrigierte PDF-Datei gehört zu einem anderen MD-Fall.")
        target_case = get_db().execute(
            "SELECT cycle_id FROM dialog_cases WHERE case_id = ?", (case_id,)
        ).fetchone()
        if not target_case or target_case["cycle_id"] != cycle_id:
            raise ValueError("Der MD-Fall gehört zu einem anderen Durchlauf.")
        result = import_official_pdf(
            get_db(),
            path=temporary,
            original_filename=upload.filename,
            accepted_dir=_storage_dir("pdf_processed"),
            replacement_reason=reason,
        )
    except Exception as exc:
        rejected = _storage_dir("pdf_rejected") / stored_name
        if temporary.exists():
            shutil.move(str(temporary), str(rejected))
        flash(str(exc), "error")
    else:
        audit(
            "document_version_replaced", "official_document",
            str(result["document_id"]), case_id=case_id, reason=reason,
        )
        flash("Die korrigierte PDF-Version wurde übernommen und protokolliert.", "success")
    return redirect(url_for("main.case_detail", cycle_id=cycle_id, case_id=case_id))


@bp.post("/cycles/<int:cycle_id>/sap-export")
def download_sap_export(cycle_id: int):
    try:
        batch = create_sap_upload_batch(
            get_db(),
            cycle_id=cycle_id,
            template_path=Path(current_app.root_path).parent / "templates" / "massenupload.xlsx",
            output_dir=_storage_dir("sap_exports"),
            user_id=g.user["id"] if g.user else None,
        )
    except (LookupError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(request.referrer or url_for("main.sap_exports"))
    audit(
        "sap_export_batch_created", "sap_export_batch", str(batch["id"]),
        cycle_id=cycle_id, row_count=batch["row_count"], sha256=batch["sha256"],
    )
    return send_file(
        batch["path"],
        as_attachment=True,
        download_name=batch["filename"],
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.post("/sap-export-batches/<int:batch_id>/download")
def download_existing_sap_export(batch_id: int):
    try:
        batch = get_sap_export_batch(get_db(), batch_id)
    except (LookupError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.sap_exports"))
    audit(
        "sap_export_batch_downloaded", "sap_export_batch", str(batch_id),
        cycle_id=batch["cycle_id"], sha256=batch["sha256"],
    )
    return send_file(
        Path(batch["stored_path"]), as_attachment=True,
        download_name=batch["filename"],
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@bp.post("/cycles/<int:cycle_id>/managers/<manager_pn>/word-package")
def download_word_package(cycle_id: int, manager_pn: str):
    try:
        case_id = request.form.get('case_id','').strip()
        if case_id:
            path, manifest = create_word_package(
                get_db(), cycle_id=cycle_id, manager_pn=manager_pn,
                template_paths=current_app.config['WORD_TEMPLATE_PATHS'],
                output_dir=_storage_dir('word_packages'), case_id=case_id)
        else:
            _batch, result = prepare_word_batch(get_db(),cycle_id=cycle_id,manager_pns=[manager_pn],
                template_paths=current_app.config['WORD_TEMPLATE_PATHS'],output_dir=_storage_dir('word_dispatch'))
            path, manifest = result['packages'][0]['path'],result['packages'][0]['manifest']
    except (LookupError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.manager_detail", cycle_id=cycle_id, manager_pn=manager_pn))
    audit("word_package_created", "word_package", manifest["export_id"],
          cycle_id=cycle_id, manager_pn=manager_pn,
          document_count=len(manifest["documents"]), sha256=manifest["sha256"])
    flash(f"{len(manifest['documents'])} Word-Vorlage(n) erzeugt. Bestehende Ausgaben bleiben erhalten. Ein Versand wurde nicht ausgelöst.", "success")
    warnings = manifest.get("goal_warnings", [])
    if warnings:
        flash(f"{len(warnings)} Rückblick(e) ohne Vorjahresziele. Details unter Versand beim erzeugten Paket prüfen." if not case_id else warnings[0], "warning")
    if manifest["skipped_cases"]:
        flash(f"{len(manifest['skipped_cases'])} Fall/Fälle ohne Rückblick-/Ausblickpflicht übersprungen.", "info")
    return send_file(path, as_attachment=True, download_name=path.name, mimetype="application/zip")


@bp.post("/cycles/<int:cycle_id>/managers/<manager_pn>/package")
def download_manager_package(cycle_id: int, manager_pn: str):
    try:
        path, payload = create_package_file(
            get_db(),
            cycle_id=cycle_id,
            manager_pn=manager_pn,
            output_dir=_storage_dir("packages"),
        )
    except (LookupError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.cycle_detail", cycle_id=cycle_id))
    audit(
        "manager_package_created", "package", payload["package"]["package_id"],
        cycle_id=cycle_id, manager_pn=manager_pn,
    )
    response = send_file(
        path,
        as_attachment=True,
        download_name=path.name,
        mimetype="text/html; charset=utf-8",
    )
    response.headers["X-MD-Package-ID"] = payload["package"]["package_id"]
    return response


@bp.post("/cycles/<int:cycle_id>/managers/<manager_pn>/package/recreate")
def recreate_manager_package(cycle_id: int, manager_pn: str):
    try:
        path, payload = create_replacement_package_file(
            get_db(), cycle_id=cycle_id, manager_pn=manager_pn,
            output_dir=_storage_dir("packages"),
        )
    except (LookupError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(request.referrer or url_for("main.dispatch", cycle_id=cycle_id))
    audit(
        "manager_package_recreated", "package", payload["package"]["package_id"],
        cycle_id=cycle_id, manager_pn=manager_pn,
    )
    response = send_file(
        path,
        as_attachment=True,
        download_name=path.name,
        mimetype="text/html; charset=utf-8",
    )
    response.headers["X-MD-Package-ID"] = payload["package"]["package_id"]
    return response


@bp.post("/cycles/<int:cycle_id>/managers/<manager_pn>/update")
def download_manager_update(cycle_id: int, manager_pn: str):
    try:
        path, payload = create_update_file(
            get_db(),
            cycle_id=cycle_id,
            manager_pn=manager_pn,
            output_dir=_storage_dir("packages"),
        )
    except (LookupError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.dispatch", cycle_id=cycle_id))
    audit(
        "manager_update_created", "package_update", payload["update"]["update_id"],
        cycle_id=cycle_id, manager_pn=manager_pn,
    )
    response = send_file(
        path,
        as_attachment=True,
        download_name=path.name,
        mimetype="application/json; charset=utf-8",
    )
    response.headers["X-MD-Update-ID"] = payload["update"]["update_id"]
    return response


@bp.post("/cycles/<int:cycle_id>/packages/batch")
def download_package_batch(cycle_id: int):
    manager_pns = request.form.getlist("manager_pn")
    selection_mode = request.form.get("selection_mode", "selected")
    if selection_mode in {"all", "org_unit"}:
        _cycle, available = cycle_overview(get_db(), cycle_id)
        if selection_mode == "all":
            manager_pns = [row["manager_pn"] for row in available]
        else:
            org_unit = request.form.get("org_unit", "").strip()
            manager_pns = _manager_pns_for_org_unit(get_db(), cycle_id, org_unit)
    try:
        path, counts = create_package_batch(
            get_db(),
            cycle_id=cycle_id,
            manager_pns=manager_pns,
            output_dir=_storage_dir("package_batches"),
        )
    except (LookupError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.dispatch", cycle_id=cycle_id))
    audit(
        "package_batch_created", "package_batch", path.name,
        cycle_id=cycle_id, start_count=counts["start"], update_count=counts["update"],
    )
    response = send_file(
        path,
        as_attachment=True,
        download_name=path.name,
        mimetype="application/zip",
    )
    response.headers["X-MD-START-Count"] = str(counts["start"])
    response.headers["X-MD-Update-Count"] = str(counts["update"])
    return response


@bp.post("/cycles/<int:cycle_id>/mail-drafts")
def prepare_mail_drafts(cycle_id: int):
    delivery_mode = request.form.get("delivery_mode", "draft")
    try:
        result = create_outlook_drafts(
            get_db(),
            cycle_id=cycle_id,
            package_event_ids=request.form.getlist("package_event_id", type=int),
            sender_email=current_app.config["HR_MAILBOX_EMAIL"],
            delivery_mode=delivery_mode,
            subject_template=request.form.get("subject_template", ""),
            body_template=request.form.get("body_template", ""),
        )
    except (LookupError, ValueError) as exc:
        flash(str(exc), "error")
    else:
        if result["sent"]:
            audit(
                "workbook_emails_sent", "cycle", str(cycle_id),
                sent=result["sent"],
            )
            flash(
                f"{result['sent']} S/MIME-markierte Nachricht(en) wurden direkt versendet.",
                "success",
            )
        if result["created"]:
            flash(
                f"{result['created']} verschlüsselt markierte Outlook-Entwurf/Entwürfe "
                "wurden erstellt. Bitte Verschlüsselung, Absender und Anhang in Outlook "
                "prüfen und dort manuell senden.",
                "success",
            )
        if result["failed"]:
            flash(
                f"{result['failed']} Entwurf/Entwürfe konnten nicht erstellt werden: "
                + " ".join(result["errors"]),
                "error",
            )
    return redirect(url_for("main.dispatch", cycle_id=cycle_id, workflow="workbook"))


@bp.post("/returns")
def upload_return():
    upload = request.files.get("return_file")
    if not upload or not upload.filename:
        flash("Bitte wähle die zurückgesendete HTML-Datei aus.", "error")
        return redirect(url_for("main.returns_overview"))
    if not upload.filename.lower().endswith(('.html', '.htm')):
        flash("Der Rücklauf muss eine gespeicherte HTML-Datei sein.", "error")
        return redirect(url_for("main.returns_overview"))

    stored_name = _stored_name(upload.filename)
    temporary = _storage_dir("returns_pending") / stored_name
    upload.save(temporary)
    try:
        result = import_returned_package(
            get_db(), path=temporary, original_filename=upload.filename
        )
    except Exception as exc:
        rejected = _storage_dir("returns_rejected") / stored_name
        shutil.move(str(temporary), str(rejected))
        flash(str(exc), "error")
        return redirect(url_for("main.returns_overview"))

    accepted = _storage_dir("returns_accepted") / stored_name
    shutil.move(str(temporary), str(accepted))
    counts = result["summary"]["status_counts"]
    audit(
        "manager_return_imported", "manager", result["manager_pn"],
        cycle_id=result["cycle_id"], revision=result["revision"],
    )
    flash(
        f"Rücklauf von {result['manager_name']} (v{int(result['revision']):02d}) importiert: "
        f"{counts['vollstaendig']} vollständig, {counts['kein_md']} ohne MD, "
        f"{counts['offen']} noch offen.",
        "success",
    )
    return redirect(url_for("main.cycle_detail", cycle_id=result["cycle_id"]))


@bp.post("/word-pdf-preview")
def preview_word_pdfs():
    uploads = [item for item in request.files.getlist("word_pdf_files") if item and item.filename]
    if not uploads:
        flash("Bitte wähle mindestens ein Word-PDF aus.", "error")
        return redirect(url_for("main.returns_overview"))
    results = []
    for upload in uploads:
        result = {"filename": upload.filename}
        if not upload.filename.lower().endswith(".pdf"):
            result["error"] = "Bitte eine PDF-Datei auswählen."
        else:
            temporary = _storage_dir("word_pdf_preview") / _stored_name(upload.filename)
            try:
                upload.save(temporary)
                result.update(inspect_word_pdf(temporary))
            except ValueError as exc:
                result["error"] = str(exc)
            finally:
                temporary.unlink(missing_ok=True)
        results.append(result)
    return render_template("word_pdf_preview.html", active_nav="returns", results=results)


@bp.post("/pdf-returns")
def upload_pdf_returns():
    uploads = [item for item in request.files.getlist("pdf_files") if item and item.filename]
    if not uploads:
        flash("Bitte wähle mindestens ein PDF aus.", "error")
        return redirect(url_for("main.returns_overview"))

    imported: list[dict] = []
    errors: list[str] = []
    for upload in uploads:
        original_filename = upload.filename or "ruecklauf.pdf"
        if not original_filename.lower().endswith(".pdf"):
            errors.append(f"{original_filename}: kein PDF")
            continue
        stored_name = _stored_name(original_filename)
        temporary = _storage_dir("pdf_pending") / stored_name
        upload.save(temporary)
        try:
            imported.append(
                import_official_pdf(
                    get_db(),
                    path=temporary,
                    original_filename=original_filename,
                    accepted_dir=_storage_dir("pdf_processed"),
                    handoff_dir=_handoff_dir(),
                )
            )
        except Exception as exc:
            rejected = _storage_dir("pdf_rejected") / stored_name
            if temporary.exists():
                shutil.move(str(temporary), str(rejected))
            errors.append(f"{original_filename}: {exc}")

    if imported:
        flash(f"{len(imported)} PDF-Rücklauf/Rückläufe wurden ausgelesen.", "success")
    if errors:
        flash(" ".join(errors), "error")
    if len(imported) == 1:
        item = imported[0]
        case = get_db().execute(
            "SELECT manager_pn FROM dialog_cases WHERE case_id = ?", (item["case_id"],)
        ).fetchone()
        return redirect(
            url_for(
                "main.manager_detail",
                cycle_id=item["cycle_id"],
                manager_pn=case["manager_pn"],
            )
        )
    return redirect(url_for("main.returns_overview"))


@bp.post("/mail-inbox/schedule")
def configure_mail_schedule():
    enabled = request.form.get('enabled') == '1'
    if enabled and not current_app.config.get('OUTLOOK_MAILBOX_NAME'):
        flash('Bitte zuerst das Outlook-Postfach konfigurieren.', 'error')
    else:
        get_db().execute('UPDATE mail_scan_schedule SET enabled=? WHERE id=1', (int(enabled),))
        get_db().commit()
        audit('mail_scan_schedule_changed', 'mail_scan_schedule', '1', enabled=enabled)
        flash('Automatische Postfachprüfung aktiviert.' if enabled else 'Automatische Postfachprüfung deaktiviert.', 'success')
    return redirect(url_for('main.returns_overview'))


@bp.post('/mail-inbox/<int:message_id>/retry')
def retry_mail_message(message_id):
    from .services.outlook_lock import package_lock
    try:
        with package_lock(Path(current_app.config['DATABASE']).with_suffix('.mail-scan')):
            db=get_db()
            row=db.execute('SELECT status FROM inbound_mail_messages WHERE id=?',(message_id,)).fetchone()
            if not row or row['status'] not in ('new','failed'):
                raise ValueError('Nur unterbrochene Verarbeitungen können erneut gestartet werden.')
            db.execute("UPDATE inbound_mail_messages SET status='failed' WHERE id=?",(message_id,));db.commit()
        run_scan(current_app)
        flash('Postfach erneut geprüft. Bereits gesicherte Anhänge wurden beibehalten.','success')
    except (ValueError,OSError,RuntimeError) as exc:
        flash(str(exc),'error')
    return redirect(url_for('main.returns_overview')+'#postfach')


@bp.get('/mail-attachments/<int:attachment_id>/original')
def mail_attachment_original(attachment_id):
    row=get_db().execute('SELECT stored_path,original_filename FROM inbound_mail_attachments WHERE id=?',(attachment_id,)).fetchone()
    if not row or not row['stored_path'] or not Path(row['stored_path']).is_file(): abort(404)
    return send_file(row['stored_path'],download_name=row['original_filename'],as_attachment=True)


@bp.post("/mail-inbox/scan")
def scan_mail_inbox():
    try:
        result = run_scan(current_app)
    except Exception as exc:
        flash(str(exc), "error")
    else:
        flash(
            f"Postfach gelesen: {result['read']} Nachricht(en), "
            f"{result['stored']} neue Anhänge gesichert, "
            f"{result['moved']} verarbeitet und verschoben, "
            f"{result['review']} zur HR-Prüfung, {result['ignored']} ohne MD-Bezug ignoriert, "
            f"{result['duplicates']} bereits bekannt, "
            f"{result['feedback_bundles']} Feedback-Sammel-PDF(s) erstellt, "
            f"{result['failed']} Nachricht(en)/Verarbeitungsschritt(e) fehlgeschlagen.",
            "warning" if result["errors"] else "success",
        )
        if result["errors"]:
            flash(" ".join(result["errors"]), "error")
    return redirect(url_for("main.returns_overview"))


@bp.post("/mail-inbox/<int:message_id>/resolve")
def resolve_mail_message(message_id: int):
    try:
        result = resolve_inbound_message(
            get_db(),
            message_id=message_id,
            review_note=request.form.get("review_note", ""),
            mailbox_name=current_app.config["OUTLOOK_MAILBOX_NAME"],
            target_folder=current_app.config["OUTLOOK_TARGET_FOLDER"],
        )
    except (LookupError, ValueError, RuntimeError) as exc:
        flash(str(exc), "error")
    else:
        if result["status"] == "review_completed":
            audit(
                "inbound_mail_review_completed",
                "inbound_mail_message",
                str(message_id),
            )
            flash("Die E-Mail-Prüfung wurde als erledigt markiert.", "success")
        else:
            audit(
                "inbound_mail_moved",
                "inbound_mail_message",
                str(message_id),
                target_folder=result["target_folder"],
            )
            flash("Die Nachricht wurde in Outlook verschoben.", "success")
    return redirect(url_for("main.returns_overview") + "#postfach")


@bp.get('/documents/<int:document_id>/original')
def document_original(document_id):
    document=get_db().execute('SELECT stored_path,original_filename FROM official_documents WHERE id=?',(document_id,)).fetchone()
    if not document or not Path(document['stored_path']).is_file(): abort(404)
    return send_file(document['stored_path'],download_name=document['original_filename'],mimetype='application/pdf')


@bp.post("/documents/<int:document_id>/signature-checked")
def mark_signature_checked(document_id: int):
    from .services.return_review import available as return_model
    if return_model(get_db()):
        return redirect(url_for('return_work.detail',document_id=document_id))
    try:
        result = confirm_digital_signature(
            get_db(), document_id=document_id, handoff_dir=_handoff_dir()
        )
    except OSError:
        get_db().rollback()
        flash('Die Dossierübergabe ist fehlgeschlagen. Prüfe, ob der Ablageordner erreichbar und beschreibbar ist. Der Fall bleibt zur Prüfung offen. Vor einem erneuten Versuch den PDF-Verlauf und Übergabeordner vergleichen; bei Unklarheit die Systemadministration beiziehen.', 'error')
        return redirect(request.referrer or url_for('main.returns_overview'))
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(request.referrer or url_for("main.dashboard"))
    if result["scan_required"]:
        flash("Rückblick D/E: Der unterschriebene Scan muss noch geprüft werden.", "success")
    else:
        flash(
            f"Kopie von «{result['handoff_filename']}» für die Personaldossier-Ablage bereitgestellt.",
            "success",
        )
    return redirect(request.referrer or url_for("main.dashboard"))


@bp.post("/cases/<case_id>/scans/<document_kind>")
def upload_scan(case_id: str, document_kind: str):
    from .services.return_review import available as return_model
    if return_model(get_db()):
        doc=get_db().execute("SELECT id FROM official_documents WHERE case_id=? AND document_kind=? AND variant='digital' AND is_current=1",(case_id,document_kind)).fetchone()
        flash('Den Scan beim Rücklauf zuordnen. Ohne vorhandene Datenquelle den Scan über die PDF-Prüfung vollständig erfassen.','info')
        return redirect(url_for('return_work.detail',document_id=doc['id']) if doc else url_for('main.returns_overview'))
    if request.form.get('scan_checked') != 'yes':
        flash('Bitte Person, Zeitraum, Vollständigkeit und erforderliche Unterschriften am Scan prüfen und bestätigen.', 'error')
        return redirect(request.referrer or url_for('main.returns_overview'))
    upload = request.files.get("scan_file")
    if not upload or not upload.filename:
        flash("Bitte wähle den handschriftlich unterzeichneten PDF-Scan aus.", "error")
        return redirect(request.referrer or url_for("main.dashboard"))
    if not upload.filename.lower().endswith(".pdf"):
        flash("Der handschriftliche Rücklauf muss ein PDF sein.", "error")
        return redirect(request.referrer or url_for("main.dashboard"))

    stored_name = _stored_name(upload.filename)
    temporary = _storage_dir("scan_pending") / stored_name
    upload.save(temporary)
    try:
        result = import_handwritten_scan(
            get_db(),
            case_id=case_id,
            document_kind=document_kind,
            path=temporary,
            original_filename=upload.filename,
            handoff_dir=_handoff_dir(),
        )
    except Exception as exc:
        rejected = _storage_dir("scan_rejected") / stored_name
        if temporary.exists():
            shutil.move(str(temporary), str(rejected))
        flash(str(exc), "error")
        return redirect(request.referrer or url_for("main.dashboard"))
    flash(
        f"Handschriftlicher Scan «{result['handoff_filename']}» für die Personaldossier-Ablage bereitgestellt.",
        "success",
    )
    return redirect(request.referrer or url_for("main.dashboard"))


@bp.app_errorhandler(413)
def file_too_large(_error):
    flash("Die Datei ist grösser als 25 MB.", "error")
    return redirect(url_for("main.dashboard"))


@bp.post("/word-pdf-imports")
def upload_word_pdfs():
    uploads = [item for item in request.files.getlist('word_pdf_files') if item and item.filename]
    if not uploads:
        flash('Bitte mindestens ein PDF auswählen.', 'error')
    ids = []
    for upload in uploads:
        temporary = _storage_dir('word_pdf_preview') / _stored_name(upload.filename)
        try:
            if not upload.filename.lower().endswith('.pdf'):
                raise ValueError('Bitte eine PDF-Datei auswählen.')
            upload.save(temporary)
            item_id, duplicate = stage_pdf(get_db(), temporary, filename=upload.filename, directory=_storage_dir('word_pdf_imports'))
            ids.append(item_id)
            if duplicate:
                flash(f'{upload.filename}: bereits vorhanden; vorhandene Prüfung geöffnet.', 'info')
        except ValueError as exc:
            flash(f'{upload.filename}: {exc}', 'error')
        finally:
            temporary.unlink(missing_ok=True)
    return redirect(url_for('main.word_pdf_review', import_id=ids[0]) if len(ids)==1 else url_for('main.returns_overview'))


def _reviewed_word_form(form):
    data={key:form.get(key,'').strip() for key in ('document_kind','pn','manager_pn','period_start','period_end','dialog_date','conducted','rating','probation','employment_continues','no_md_reason','higher_manager_requested','sap_current','career_requested')}
    from .services.word_pdf import NARRATIVE_FIELDS
    result={'data':data,'scope':form.get('scope',''),'source_role':form.get('source_role','digital'),'assessments':{},'scan_required':form.get('scan_required')=='yes',
            'narratives':{key: form.get('narrative_'+key,'').strip() for key in NARRATIVE_FIELDS if form.get('narrative_present_'+key)=='yes' or form.get('narrative_'+key,'').strip()}}
    for group in ('performance','development'):
        keys=('title','criteria','steps','target_date') + (('competency',) if group=='development' else ())
        columns={key:form.getlist(group+'_'+key) for key in keys}
        rows=[]
        for i in range(len(columns['title'])):
            row={key:(values[i].strip() if i<len(values) else '') for key,values in columns.items()}
            if any(row[key] for key in ('title','criteria','steps','target_date')):
                rows.append(row)
        result[group+'_goals']=rows
    for tag,name in COMPETENCY_TAGS.items():
        text=form.get('assessment_'+tag,'').strip()
        if text:
            result['assessments'][name]=text
    return result


@bp.route('/word-pdf-imports/<int:import_id>', methods=['GET','POST'])
def word_pdf_review(import_id):
    connection=get_db()
    if current_app.config.get('HR_GOAL_WORKFLOW'):
        session.setdefault('goal_csrf',secrets.token_urlsafe(32))
        routed=connection.execute('SELECT source_id FROM hr_goal_origins WHERE pdf_import_id=?',(import_id,)).fetchone()
        if routed:
            return redirect(url_for('goal_work.source',source_id=routed['source_id']))
    item=connection.execute('SELECT * FROM word_pdf_imports WHERE id=?',(import_id,)).fetchone()
    if not item:
        abort(404)
    state=workflow.pdf_state(connection,import_id)
    parsed=json.loads(item['parsed_json'])
    if parsed.get('data',{}).get('document_kind') == 'feedback':
        return redirect(url_for('main.feedback_review', import_id=import_id), code=307 if request.method=='POST' else 302)
    reviewed=json.loads(item['reviewed_json']) if item['reviewed_json'] else parsed
    if request.method=='POST':
        reviewed=_reviewed_word_form(request.form)
    if request.method=='POST' and request.form.get('refresh')!='yes':
        try:
            workflow.lock_pdf(connection,import_id,request.form.get('revision','0'))
            action=request.form.get('action','confirm')
            if current_app.config.get('HR_GOAL_WORKFLOW') and request.form.get('destination')=='historical' and action=='confirm':
                raise ValueError('Bitte den Ausblick über «Diesen Ausblick als Zielquelle bearbeiten» direkt prüfen und bestätigen.')
            if action in ('draft','dismiss','reopen'):
                reason=request.form.get('reason','').strip()
                if action in ('dismiss','reopen') and len(reason)<10:
                    raise ValueError('Bitte das Zurückstellen oder Wiederöffnen mit mindestens 10 Zeichen begründen.')
                if state['dismissed'] and action!='reopen':
                    raise ValueError('Diese Prüfung ist zurückgestellt. Öffne sie zuerst begründet wieder.')
                reviewed['_draft']={key:request.form.get(key,'') for key in ('assignment','case_id','destination','reason')}
                connection.execute('UPDATE word_pdf_imports SET reviewed_json=? WHERE id=?',(json.dumps(reviewed,ensure_ascii=False),import_id))
                workflow.advance_pdf(connection,import_id,dismissed=int(action=='dismiss'),reason=reason)
                connection.commit()
                audit('word_pdf_'+action,'word_pdf_import',str(import_id),reason=reason)
                flash({'draft':'Prüfentwurf gespeichert. Es wurden noch keine Fachdaten übernommen.','dismiss':'Prüfung begründet zurückgestellt. Das Original bleibt erhalten; unter «Zurückgestellt» kannst du sie wieder öffnen.','reopen':'Prüfung wieder geöffnet.'}[action],'success')
                return redirect(url_for('main.word_pdf_review',import_id=import_id))
            if state['dismissed']:
                raise ValueError('Diese Prüfung ist zurückgestellt. Bitte zuerst wieder öffnen.')
            if request.form.get('checked')!='yes':
                raise ValueError('Bitte die Prüfung am Original-PDF bestätigen.')
            confirm_import(connection,import_id,reviewed=reviewed,assignment=request.form.get('assignment','').strip(),case_id=request.form.get('case_id','').strip(),historical=request.form.get('destination')=='historical',reason=request.form.get('reason','').strip(),user_id=g.user['id'] if g.user else None)
            audit('word_pdf_imported','word_pdf_import',str(import_id))
            status = connection.execute('SELECT status FROM word_pdf_imports WHERE id=?',(import_id,)).fetchone()['status']
            if status == 'historical':
                message = 'Nachgereichte Zielquelle übernommen. Neue Word-Ausgaben berücksichtigen diese Ziele; bestehende Ausgaben bleiben unverändert.'
            elif status == 'duplicate':
                message = 'Inhaltliche Dublette erkannt. Es wurden keine zusätzlichen Fachdaten übernommen.'
            elif reviewed['data'].get('conducted') == 'nein':
                message = 'Nichtdurchführung übernommen. Der Nachweis bleibt gespeichert; eine Unterschriften- oder Ablagefreigabe ist dafür nicht vorgesehen.'
            else:
                doc = connection.execute('SELECT official_document_id FROM word_pdf_imports WHERE id=?',(import_id,)).fetchone()
                from .services import return_review
                if return_review.available(connection):
                    flash('Angaben übernommen. Unterschriftennachweis und Bereitstellung hier weiterbearbeiten.','success')
                    return redirect(url_for('return_work.detail',document_id=doc['official_document_id']))
                try:
                    released = confirm_digital_signature(connection, document_id=doc['official_document_id'], handoff_dir=_handoff_dir())
                    message = 'Angaben übernommen. Rückblick D/E: unterschriebenen Scan anfordern und im Fall prüfen; noch keine Roboterübergabe.' if released['scan_required'] else 'Angaben übernommen und Kopie im Roboter-Ordner bereitgestellt. Original bleibt im Projekt. Keine Unterschriftenprüfung erforderlich.'
                except (OSError, ValueError) as exc:
                    connection.rollback()
                    message = 'Angaben übernommen, aber Dossierübergabe noch offen: ' + str(exc) + ' Im Fall «Dossierübergabe erneut versuchen» verwenden.'
            flash(message, 'success')
            return redirect(url_for('main.word_pdf_review',import_id=import_id))
        except (ValueError,LookupError) as exc:
            connection.rollback()
            flash(str(exc),'error')
    candidates=matching_cases(connection,reviewed.get('data',{}))
    assignments=connection.execute('SELECT assignment_number,org_unit FROM employment_assignments WHERE person_number=? ORDER BY assignment_number',(reviewed.get('data',{}).get('pn',''),)).fetchall()
    from .services.word_pdf import NARRATIVE_FIELDS
    from .services import return_review
    evidence_targets=[]
    return_document_id=None
    if return_review.available(connection) and item['official_document_id']:
        registered=connection.execute('SELECT document_id FROM hr_return_reviews WHERE document_id=?',(item['official_document_id'],)).fetchone()
        if registered:return_document_id=registered['document_id']
    if return_review.available(connection) and item['status']=='pending':
        for candidate in candidates:
            for document in connection.execute("SELECT id FROM official_documents WHERE case_id=? AND document_kind=? AND variant='digital' AND is_current=1",(candidate['case_id'],reviewed.get('data',{}).get('document_kind',''))):
                evidence_targets.append(return_review.view(connection,document['id'],include_history=False))
    return render_template('word_pdf_review.html',active_nav='returns',item=item,parsed=parsed,reviewed=reviewed,pdf_state=state,candidates=candidates,evidence_targets=evidence_targets,return_document_id=return_document_id,assignments=assignments,competencies=COMPETENCY_TAGS,narrative_fields=NARRATIVE_FIELDS, scan_cases=connection.execute("SELECT d.case_id,d.cycle_id,e.first_name,e.last_name,d.employee_pn,c.employment_assignment,c.period_start,c.period_end FROM official_documents d JOIN dialog_cases c ON c.case_id=d.case_id JOIN employees e ON e.pn=d.employee_pn WHERE d.is_current=1 AND d.variant='digital' AND d.scan_required=1 AND d.handoff_status='waiting_scan'").fetchall())


@bp.post('/word-pdf-imports/<int:import_id>/scan')
def assign_inbound_scan(import_id):
    db=get_db()
    from .services.return_review import available as return_model
    if return_model(db):
        flash('Den gesicherten Scan in der PDF-Prüfung dem passenden Rücklauf zuordnen; die Unterschriften separat prüfen.','info')
        return redirect(url_for('main.word_pdf_review',import_id=import_id))
    try:
        if request.form.get('scan_checked')!='yes':
            raise ValueError('Bitte Zuordnung, vollständigen Inhalt und Unterschriften am Original-Scan bestätigen.')
        workflow.lock_pdf(db,import_id,request.form.get('revision','0'))
        if workflow.pdf_state(db,import_id)['dismissed']:
            raise ValueError('Bitte den zurückgestellten Eingang zuerst wieder öffnen.')
        item=db.execute('SELECT * FROM word_pdf_imports WHERE id=?',(import_id,)).fetchone()
        result=import_handwritten_scan(db,case_id=request.form.get('case_id',''),document_kind='review',
            path=Path(item['stored_path']),original_filename=item['original_filename'],handoff_dir=_handoff_dir())
        db.execute("UPDATE word_pdf_imports SET status='imported',case_id=?,official_document_id=?,review_note='Unterschriebener Rückblick-Scan geprüft',reviewed_at=? WHERE id=?",(result['case_id'],result['document_id'],workflow.stamp(),import_id))
        workflow.advance_pdf(db,import_id);db.commit()
        audit('inbound_scan_checked','word_pdf_import',str(import_id),case_id=result['case_id'])
        flash('Geprüfter Scan als Kopie im Roboter-Ordner bereitgestellt. Original bleibt erhalten.','success')
    except (ValueError,LookupError,OSError) as exc:
        db.rollback();flash(str(exc),'error')
    return redirect(url_for('main.word_pdf_review',import_id=import_id))


@bp.get('/word-pdf-imports/<int:import_id>/original')
def word_pdf_original(import_id):
    item=get_db().execute('''SELECT w.original_filename,w.stored_path AS original_path,w.sha256,COALESCE(d.stored_path,w.stored_path) AS stored_path
        FROM word_pdf_imports w LEFT JOIN official_documents d ON d.id=w.official_document_id WHERE w.id=?''',(import_id,)).fetchone()
    if not item:
        abort(404)
    from .services.return_review import checked_file
    path=item['original_path'] if Path(item['original_path']).is_file() else item['stored_path']
    try:path=checked_file(path,item['sha256'])
    except ValueError:abort(409,'Das Original fehlt oder wurde verändert.')
    return send_file(path,download_name=item['original_filename'],mimetype='application/pdf')


@bp.post('/cycles/<int:cycle_id>/word-packages/batch')
def prepare_word_packages(cycle_id):
    try:
        selection = request.form.get('selection_mode','selected')
        if selection=='all':
            _cycle, managers = cycle_overview(get_db(),cycle_id)
            numbers = [row['manager_pn'] for row in managers]
        elif selection=='org_unit':
            numbers = _manager_pns_for_org_unit(get_db(),cycle_id,request.form.get('org_unit','').strip())
        elif selection=='selected':
            numbers = request.form.getlist('manager_pn')
        else:
            raise ValueError('Unbekannte Auswahl.')
        batch, result = prepare_word_batch(get_db(),cycle_id=cycle_id,manager_pns=numbers,
            template_paths=current_app.config['WORD_TEMPLATE_PATHS'],output_dir=_storage_dir('word_dispatch'))
        audit('word_dispatch_prepared','cycle',str(cycle_id),package_ids=[p['id'] for p in result['packages']])
        flash(f"{len(result['packages'])} Word-Paket(e) für Outlook vorbereitet. {len(result['skipped'])} Führungslinie(n) ohne Formularpflicht übersprungen.",'success')
        return redirect(url_for('main.dispatch',cycle_id=cycle_id,word_batch=batch.parent.name))
    except (ValueError,LookupError) as exc:
        flash(str(exc),'error')
        return redirect(url_for('main.dispatch',cycle_id=cycle_id))


@bp.get('/word-packages/batch/<batch_id>')
def download_word_batch(batch_id):
    import re
    if not re.fullmatch(r'WORD-BATCH-[0-9a-f]{32}',batch_id):
        abort(404)
    path = _storage_dir('word_dispatch') / batch_id / 'MD_Word_Sammelausgabe.zip'
    if not path.is_file():
        abort(404)
    return send_file(path,as_attachment=True,download_name=path.name)


@bp.get('/word-packages/<int:package_id>/download')
def download_prepared_word_package(package_id):
    row=get_db().execute('SELECT stored_path FROM word_dispatch_packages WHERE id=?',(package_id,)).fetchone()
    if not row or not Path(row['stored_path']).is_file():
        abort(404)
    return send_file(row['stored_path'],as_attachment=True,download_name=Path(row['stored_path']).name)


@bp.post('/cycles/<int:cycle_id>/word-mail-preview')
def preview_word_mail(cycle_id):
    cycle = get_db().execute('SELECT * FROM cycles WHERE id=?', (cycle_id,)).fetchone()
    if not cycle:
        abort(404)
    manager = get_db().execute("""SELECT e.pn, e.first_name, e.salutation, TRIM(e.first_name || ' ' || e.last_name) AS name
        FROM employees e WHERE e.pn=? AND EXISTS
        (SELECT 1 FROM dialog_cases dc WHERE dc.cycle_id=? AND dc.manager_pn=e.pn AND dc.active=1)""",
        (request.form.get('preview_manager_pn', ''), cycle_id)).fetchone()
    if not manager:
        return {'error': 'Bitte eine Führungskraft für die Vorschau auswählen.'}, 400
    row = dict(cycle, manager_pn=manager['pn'], manager_name=manager['name'],
               manager_first_name=manager['first_name'], manager_salutation=manager['salutation'])
    try:
        subject, body = word_message(row, sender_email=current_app.config['HR_MAILBOX_EMAIL'],
            subject_template=request.form.get('subject_template', ''), body_template=request.form.get('body_template', ''))
    except ValueError as exc:
        return {'error': str(exc)}, 400
    return {'subject': subject, 'body_html': body}


@bp.post('/cycles/<int:cycle_id>/word-mail')
def prepare_word_mail(cycle_id):
    try:
        result=dispatch_word_packages(get_db(),cycle_id=cycle_id,package_ids=request.form.getlist('word_package_id',type=int),
            template_paths=current_app.config['WORD_TEMPLATE_PATHS'],sender_email=current_app.config['HR_MAILBOX_EMAIL'],
            delivery_mode=request.form.get('delivery_mode','draft'),subject_template=request.form.get('subject_template',''),
            body_template=request.form.get('body_template',''),retry_confirmed=request.form.get('retry_confirmed')=='yes')
        audit('word_mail_processed','cycle',str(cycle_id),created=result['created'],sent=result['sent'],failed=result['failed'])
        flash(f"{result['created']} Outlook-Entwurf/Entwürfe erstellt, {result['sent']} direkt versendet, {result['failed']} fehlgeschlagen.",'error' if result['failed'] else 'success')
        for error in result['errors']:
            flash(error,'error')
    except (LookupError,ValueError) as exc:
        flash(str(exc),'error')
    return redirect(url_for('main.dispatch',cycle_id=cycle_id))


@bp.post('/word-packages/<int:package_id>/changes')
def resolve_word_change(package_id):
    from .services.dispatch_changes import resolve_change
    db=get_db()
    package=db.execute('SELECT cycle_id FROM word_dispatch_packages WHERE id=?',(package_id,)).fetchone()
    if not package:abort(404)
    try:
        item=next((x for x in word_dispatch_candidates(db,cycle_id=package['cycle_id'],template_paths=current_app.config['WORD_TEMPLATE_PATHS']) if x['id']==package_id),None)
        if not item or item['delivery_status']!='sent_confirmed':
            raise ValueError('Korrekturen hier nur für eine aktuelle, bestätigt versendete Ausgabe dokumentieren.')
        resolve_change(db,package_id=package_id,case_id=request.form.get('case_id',''),signature=request.form.get('signature',''),outcome=request.form.get('outcome',''),reason=request.form.get('reason',''),current_changes=item['source_changes'])
        audit('word_change_resolved','word_package',str(package_id),case_id=request.form.get('case_id'),outcome=request.form.get('outcome'))
        flash('Vorgehen dokumentiert. Der ursprüngliche Versandnachweis bleibt bestehen.','success')
    except ValueError as exc:flash(str(exc),'error')
    return redirect(url_for('main.dispatch',cycle_id=package['cycle_id'])+'#changes-'+str(package_id))


@bp.post('/word-packages/<int:package_id>/discard')
def discard_unused_word_package(package_id):
    row = get_db().execute('SELECT cycle_id FROM word_dispatch_packages WHERE id=?', (package_id,)).fetchone()
    if not row:
        abort(404)
    try:
        discard_word_package(get_db(), package_id)
        audit('word_package_discarded', 'word_package', str(package_id))
        flash('Ausgabe verworfen. Die vorherige nicht verworfene Ausgabe ist wieder massgebend; bestätigte Versände bleiben erhalten.', 'success')
    except ValueError as exc:
        flash(str(exc), 'error')
    return redirect(url_for('main.dispatch', cycle_id=row['cycle_id']))


@bp.post('/word-packages/<int:package_id>/confirm-sent')
def confirm_word_sent(package_id):
    row=get_db().execute('SELECT cycle_id FROM word_dispatch_packages WHERE id=?',(package_id,)).fetchone()
    if not row:
        abort(404)
    try:
        if request.form.get('sent_checked')!='yes':
            raise ValueError('Bitte den tatsächlichen Versand des Entwurfs in Outlook bestätigen.')
        confirm_word_draft_sent(get_db(),package_id)
        audit('word_draft_sent_confirmed','word_package',str(package_id))
        flash('Der manuelle Outlook-Versand ist bestätigt.','success')
    except ValueError as exc:
        flash(str(exc),'error')
    return redirect(url_for('main.dispatch',cycle_id=row['cycle_id']))


@bp.post('/word-packages/<int:package_id>/discard-draft')
def discard_word_mail_draft(package_id):
    row=get_db().execute('SELECT cycle_id FROM word_dispatch_packages WHERE id=?',(package_id,)).fetchone()
    if not row:
        abort(404)
    try:
        if request.form.get('discard_checked')!='yes':
            raise ValueError('Bitte in Outlook prüfen, dass die Nachricht nicht versendet wurde, und einen vorhandenen Entwurf löschen.')
        discard_word_draft(get_db(),package_id)
        audit('word_draft_discarded','word_package',str(package_id))
        flash('Entwurf als verworfen markiert. Ein neues Paket kann erzeugt werden.','success')
    except ValueError as exc:
        flash(str(exc),'error')
    return redirect(url_for('main.dispatch',cycle_id=row['cycle_id']))


@bp.get('/aufgaben')
def worklist():
    data=cockpit_overview(get_db(),selected_cycle_id=request.args.get('cycle_id',type=int))
    kind=request.args.get('kind','');query=request.args.get('q','').casefold()
    rows=[t for t in data['tasks'] if (not kind or t['kind']==kind) and (not query or query in (t['title']+' '+t['subject']+' '+t.get('context','')).casefold())]
    return render_template('worklist.html',active_nav='overview',rows=rows,kind=kind,query=query,kinds=sorted({t['kind'] for t in data['tasks']}),**data)


@bp.get('/einrichtung')
def setup_guide():
    return render_template('setup_guide.html',active_nav='help',checks=workflow.setup_checks(current_app.config,get_db()))


@bp.get('/hilfe')
def help_page():
    from .services.help_content import SECTIONS
    return render_template('help.html',active_nav='help',help_sections=SECTIONS)


@bp.post('/dialog-events/<int:event_id>/attach')
def attach_dialog_event(event_id):
    try:
        cycle_id=request.form.get('cycle_id',type=int)
        reason=request.form.get('reason','')
        case_id=workflow.attach_event(get_db(),event_id,cycle_id,reason)
        audit('event_attached','dialog_event',str(event_id),cycle_id=cycle_id,reason=reason)
        flash('Ereignis zugeordnet. Hier kannst du den Fall prüfen und über die Führungslinie Word-Vorlagen erzeugen.','success')
        return redirect(url_for('main.case_detail',cycle_id=cycle_id,case_id=case_id))
    except ValueError as exc:
        flash(str(exc),'error')
        return redirect(url_for('main.dialogs',unassigned='yes'))


@bp.post('/dialog-events/<int:event_id>/cancel')
def cancel_dialog_event(event_id):
    try:
        workflow.cancel_manual_event(get_db(),event_id,request.form.get('reason',''))
        audit('event_cancelled','dialog_event',str(event_id),reason=request.form.get('reason',''))
        flash('Manuelles Ereignis aufgehoben. Es bleibt nachvollziehbar gespeichert.','success')
    except ValueError as exc:flash(str(exc),'error')
    return redirect(url_for('main.dialogs'))


@bp.get('/hilfe/dokument/<name>')
def help_document(name):
    if name not in {'HR_BETREUUNG.md','BUEROTEST.md','PLAN_B_WORD_PDF.md','BETRIEBSKONZEPT.md','FLASK_SQLITE_MVP.md','ANFORDERUNGEN.md'}:abort(404)
    return send_file(Path(current_app.root_path).parent/'docs'/name,as_attachment=True,download_name=name)


@bp.get('/cycles/<int:cycle_id>/abschluss')
def cycle_closure(cycle_id):
    cycle=get_db().execute('SELECT * FROM cycles WHERE id=?',(cycle_id,)).fetchone()
    if not cycle:abort(404)
    return render_template('cycle_closure.html',active_nav='dialogs',cycle=cycle,summary=workflow.closure_summary(get_db(),cycle_id))


@bp.app_errorhandler(OSError)
def storage_problem(error):
    get_db().rollback()
    reference=uuid.uuid4().hex[:10]
    current_app.logger.exception('Dateisystemfehler %s',reference)
    return render_template('operation_error.html',reference=reference),503


@bp.post('/word-packages/<int:package_id>/resolve-interrupted')
def resolve_interrupted_word(package_id):
    from .services.word_dispatch import resolve_interrupted_delivery
    try:
        if request.form.get('outlook_checked')!='yes':raise ValueError('Bitte in Outlook prüfen, ob die Nachricht bereits verschlüsselt versendet wurde oder ob kein Versand und kein Entwurf mehr offen ist. Alte Serverversionen müssen zuvor beendet sein.')
        resolve_interrupted_delivery(get_db(),package_id,outcome=request.form.get('outcome',''),reason=request.form.get('reason',''))
        audit('word_delivery_resolved','word_package',str(package_id),outcome=request.form.get('outcome'),reason=request.form.get('reason'))
        flash('Outlook-Vorgang geklärt. Dabei wurde keine zusätzliche Nachricht versendet.','success')
    except ValueError as exc:flash(str(exc),'error')
    return redirect(url_for('main.dispatch'))


@bp.route('/zielquellen',methods=['GET','POST'])
def goal_sources():
    from .services.word_packages import prior_goals,goal_sources_fingerprint
    values=request.form if request.method=='POST' else request.args
    pn=values.get('pn','').strip();assignment=values.get('assignment','').strip();year=values.get('year',type=int)
    sources=[];fingerprint=''
    try:
        if pn and assignment and year:
            sources=prior_goals(get_db(),employee_pn=pn,assignment=assignment,year=year,sources_only=True)
            fingerprint=goal_sources_fingerprint(sources)
        if request.method=='POST':
            index=values.get('source',type=int);reason=values.get('reason','').strip()
            if not fingerprint or values.get('fingerprint')!=fingerprint:raise ValueError('Die Quellen haben sich geändert. Bitte die neue Übersicht vergleichen.')
            if index is None or not 0<=index<len(sources) or len(reason)<10:raise ValueError('Bitte eine Quelle wählen und die Entscheidung mit mindestens 10 Zeichen begründen.')
            with get_db():
                get_db().execute("""INSERT INTO workflow_goal_choices VALUES (?,?,?,?,?,?,?) ON CONFLICT(employee_pn,assignment_number,goal_year) DO UPDATE SET source_json=excluded.source_json,sources_fingerprint=excluded.sources_fingerprint,reason=excluded.reason,updated_at=excluded.updated_at""",(pn,assignment,year,json.dumps(sources[index][2]),fingerprint,reason,workflow.stamp()))
            audit('goal_source_selected','person',pn,assignment=assignment,year=year,source=sources[index][2],reason=reason)
            flash('Zielquelle festgelegt. Die nächste Word-Erzeugung verwendet diese Quelle; frühere Ausgaben bleiben unverändert.','success')
    except ValueError as exc:flash(str(exc),'error')
    choice=get_db().execute('SELECT * FROM workflow_goal_choices WHERE employee_pn=? AND assignment_number=? AND goal_year=?',(pn,assignment,year)).fetchone()
    selected_source=json.loads(choice['source_json']) if choice else None
    return render_template('goal_sources.html',active_nav='master_data',sources=sources,pn=pn,assignment=assignment,year=year,fingerprint=fingerprint,choice=choice,selected_source=selected_source)


def _goal_batch_directory(batch_id):
    import re
    if not re.fullmatch('[0-9a-f]{32}', batch_id):
        abort(404)
    directory = _storage_dir('legacy_preview') / batch_id
    if not (directory / 'year.json').is_file():
        abort(404)
    return directory


@bp.route('/alte-ziele', methods=['GET', 'POST'])
def legacy_goal_upload():
    if current_app.config.get('HR_GOAL_WORKFLOW'):
        if request.method=='POST':
            from .goal_routes import accept_uploads
            return accept_uploads(request.files.getlist('forms'),request.form.get('goal_year',type=int))
        return redirect(url_for('goal_work.index')+'#upload')
    from .services.goal_batches import create_batch, save_upload
    if request.method == 'POST':
        try:
            uploads = [u for u in request.files.getlist('forms') if u.filename]
            if not uploads:
                raise ValueError('Bitte mindestens eine Word- oder PDF-Datei wählen.')
            batch, directory = create_batch(_storage_dir('legacy_preview'), request.form.get('goal_year', type=int))
            for upload in uploads:
                save_upload(directory, upload)
            return redirect(url_for('main.legacy_goal_preview', batch_id=batch))
        except ValueError as exc:
            flash(str(exc), 'error')
    return render_template('legacy_goal_upload.html', active_nav='master_data')


@bp.post('/alte-ziele/batches')
def create_goal_batch():
    from .services.goal_batches import create_batch
    try:
        batch, _ = create_batch(_storage_dir('legacy_preview'), request.form.get('goal_year', type=int))
    except ValueError as exc:
        return {'error': str(exc)}, 400
    preview_url=url_for('main.legacy_goal_preview',batch_id=batch)
    if current_app.config.get('HR_GOAL_WORKFLOW'):
        from .services.goal_review import batch as goal_batch
        group=goal_batch(get_db(),'legacy-upload:'+batch,'Eingelesene Ausblicke')
        preview_url=url_for('goal_work.index',batch_id=group,state='all')
    return {'upload_url': url_for('main.upload_goal_batch_file', batch_id=batch), 'preview_url':preview_url}


@bp.post('/alte-ziele/<batch_id>/files')
def upload_goal_batch_file(batch_id):
    from .services.goal_batches import save_upload
    directory = _goal_batch_directory(batch_id)
    upload = request.files.get('file')
    if not upload or not upload.filename:
        return {'error': 'Keine Datei erhalten.'}, 400
    try:
        file_id = save_upload(directory, upload)
        if current_app.config.get('HR_GOAL_WORKFLOW'):
            from .services import goal_review
            group=goal_review.batch(get_db(),'legacy-upload:'+batch_id,'Eingelesene Ausblicke')
            path=next((directory/'files'/file_id).iterdir())
            year=json.loads((directory/'year.json').read_text())['year']
            goal_review.stage(get_db(),path,filename=upload.filename,batch_id=group,origin_key=f'legacy-upload:{batch_id}:{file_id}',goal_year=year)
    except ValueError as exc:
        return {'error': str(exc)}, 400
    return {'file_id': file_id}


@bp.get('/alte-ziele/<batch_id>/original/<file_id>')
def download_goal_original(batch_id, file_id):
    import re
    if not re.fullmatch('[0-9a-f]{32}', file_id):
        abort(404)
    directory = _goal_batch_directory(batch_id) / 'files' / file_id
    paths = list(directory.glob('*'))
    if len(paths) != 1 or not paths[0].is_file():
        abort(404)
    return send_file(paths[0], as_attachment=True, download_name=paths[0].name)


@bp.route('/alte-ziele/<batch_id>', methods=['GET', 'POST'])
def legacy_goal_preview(batch_id):
    from .services.goal_batches import preview, validate_selection
    from .services.legacy_forms import import_legacy_forms
    directory = _goal_batch_directory(batch_id)
    year = json.loads((directory / 'year.json').read_text())['year']
    result, fingerprint = preview(get_db(), directory, year)
    if current_app.config.get('HR_GOAL_WORKFLOW'):
        if request.method=='POST':
            from .services import goal_review
            group=goal_review.batch(get_db(),'legacy-upload:'+batch_id,'Bereits gesicherte Ausblicke')
            for item in result['items']:
                goal_review.stage(get_db(),item['path'],filename=item['filename'],batch_id=group,
                    origin_key=f'legacy-file:{batch_id}:{item["file_id"] or item["sha256"]}',goal_year=year)
            return redirect(url_for('goal_work.index',batch_id=group,state='all'))
        return render_template('goal_work/legacy_bridge.html',active_nav='goal_work',batch_id=batch_id)
    if request.method == 'POST':
        try:
            if request.form.get('checked') != 'yes' or request.form.get('fingerprint') != fingerprint:
                raise ValueError('Bitte die aktuelle Vorschau einschliesslich Zieljahr und Zuordnungen prüfen und bestätigen.')
            selected = set(request.form.getlist('source'))
            validate_selection(result, selected)
            imported = import_legacy_forms(get_db(), forms_root=directory, goal_year=year, selected_hashes=selected)
            audit('legacy_goals_imported', 'goal_batch', batch_id, year=year, imported=imported['imported'])
            flash(f"{imported['imported']} ausgewählte Quelle(n) importiert. Bitte die Word-Dossiers neu erzeugen.", 'success')
            return redirect(url_for('main.legacy_goal_preview', batch_id=batch_id))
        except ValueError as exc:
            flash(str(exc), 'error')
    return render_template('legacy_goal_preview.html', active_nav='master_data', result=result, fingerprint=fingerprint, batch_id=batch_id)


@bp.post('/word-pdf-imports/<int:import_id>/as-feedback')
def classify_feedback(import_id):
    connection=get_db()
    try:
        workflow.lock_pdf(connection,import_id,request.form.get('revision','0'))
        item=connection.execute('SELECT * FROM word_pdf_imports WHERE id=?',(import_id,)).fetchone()
        if not item or item['status']!='pending':
            raise ValueError('Nur offene Prüfungen können zugeordnet werden.')
        parsed=word_feedback.inspect_feedback(Path(item['stored_path']),item['original_filename'])
        connection.execute("UPDATE word_pdf_imports SET parsed_json=?,reviewed_json='' WHERE id=?",(json.dumps(parsed,ensure_ascii=False),import_id))
        workflow.advance_pdf(connection,import_id)
        connection.commit()
        audit('word_pdf_classified_feedback','word_pdf_import',str(import_id))
    except (ValueError,LookupError) as exc:
        connection.rollback(); flash(str(exc),'error')
        return redirect(url_for('main.word_pdf_review',import_id=import_id))
    return redirect(url_for('main.feedback_review',import_id=import_id))


@bp.route('/feedback-imports/<int:import_id>',methods=['GET','POST'])
def feedback_review(import_id):
    connection=get_db()
    item=connection.execute('SELECT * FROM word_pdf_imports WHERE id=?',(import_id,)).fetchone()
    if not item: abort(404)
    parsed=json.loads(item['parsed_json'])
    if parsed.get('data',{}).get('document_kind')!='feedback': abort(404)
    state=workflow.pdf_state(connection,import_id)
    reviewed=json.loads(item['reviewed_json']) if item['reviewed_json'] else {
        'manager_pn':parsed['data'].get('manager_pn',''),'cycle_id':'','feedback_fields':parsed.get('feedback_fields',{})}
    if request.method=='POST':
        reviewed={'manager_pn':request.form.get('manager_pn','').strip(),'cycle_id':request.form.get('cycle_id',''),
                  'feedback_fields':{key:request.form.get('field_'+key,'').strip() for key in word_feedback.FIELDS if request.form.get('present_'+key)=='yes' or request.form.get('field_'+key,'').strip()}}
        reason=request.form.get('reason','').strip()
        try:
            workflow.lock_pdf(connection,import_id,request.form.get('revision','0'))
            action=request.form.get('action','confirm')
            if item['status']!='pending': raise ValueError('Bereits verarbeitet; das Original bleibt erhalten.')
            if state['dismissed'] and action!='reopen': raise ValueError('Bitte die Prüfung zuerst wieder öffnen.')
            if action in ('dismiss','reopen') and len(reason)<10: raise ValueError('Bitte mit mindestens 10 Zeichen begründen.')
            if action=='to_document':
                from .services.word_pdf import inspect_word_pdf
                connection.execute("UPDATE word_pdf_imports SET parsed_json=?,reviewed_json='' WHERE id=?",(json.dumps(inspect_word_pdf(Path(item['stored_path'])),ensure_ascii=False),import_id))
                workflow.advance_pdf(connection,import_id); connection.commit()
                audit('feedback_reclassified','word_pdf_import',str(import_id))
                return redirect(url_for('main.word_pdf_review',import_id=import_id))
            if action in ('draft','dismiss','reopen'):
                reviewed['reason']=reason
                connection.execute('UPDATE word_pdf_imports SET reviewed_json=? WHERE id=?',(json.dumps(reviewed,ensure_ascii=False),import_id))
                workflow.advance_pdf(connection,import_id,dismissed=int(action=='dismiss'),reason=reason)
                connection.commit()
                audit('feedback_'+action,'word_pdf_import',str(import_id))
                flash('Prüfstand gespeichert.','success')
            elif action=='confirm':
                if request.form.get('checked')!='yes': raise ValueError('Bitte Führungskraft, Jahr und Inhalte am Original prüfen und bestätigen.')
                word_feedback.confirm_feedback(connection,import_id,cycle_id=int(reviewed['cycle_id']),manager_pn=reviewed['manager_pn'],fields=reviewed['feedback_fields'],reason=reason,user_id=g.user['id'] if g.user else None)
                workflow.advance_pdf(connection,import_id); connection.commit()
                audit('feedback_confirmed','word_pdf_import',str(import_id),cycle_id=reviewed['cycle_id'],manager_pn=reviewed['manager_pn'])
                flash('Feedback in die Sammlung übernommen. Bündelung unter Rückläufe → Feedbacks.','success')
            else: raise ValueError('Unbekannte Aktion.')
            return redirect(url_for('main.feedback_review',import_id=import_id))
        except (ValueError,LookupError) as exc:
            connection.rollback(); flash(str(exc) or 'Bitte Jahresprozess auswählen.','error')
    submission=connection.execute('SELECT * FROM word_feedback_submissions WHERE import_id=?',(import_id,)).fetchone()
    managers=connection.execute('SELECT DISTINCT e.pn,e.first_name,e.last_name FROM employees e JOIN dialog_cases d ON d.manager_pn=e.pn ORDER BY e.last_name,e.first_name').fetchall()
    cycles=connection.execute('SELECT * FROM cycles ORDER BY review_year DESC').fetchall()
    return render_template('feedback_review.html',active_nav='returns',item=item,parsed=parsed,reviewed=reviewed,pdf_state=state,managers=managers,cycles=cycles,fields=word_feedback.FIELDS,submission=submission)


@bp.route('/feedback-collections/<int:cycle_id>/<manager_pn>',methods=['GET','POST'])
def feedback_collection(cycle_id,manager_pn):
    connection=get_db()
    if request.method=='POST':
        try:
            if request.form.get('checked')!='yes': raise ValueError('Bitte die Zusammenstellung bestätigen.')
            ids=[int(value) for value in request.form.getlist('import_id')]
            bundle_id=word_feedback.bundle_feedback(connection,cycle_id=cycle_id,manager_pn=manager_pn,expected_ids=ids,handoff_dir=_handoff_dir(),archive_dir=_storage_dir('feedback_bundles'))
            audit('feedback_bundle_created','feedback_bundle',str(bundle_id),cycle_id=cycle_id,manager_pn=manager_pn)
            flash('Feedback-Sammel-PDF für die Dossierablage bereitgestellt.','success')
            return redirect(url_for('main.returns_overview',cycle_id=cycle_id)+'#feedbacks')
        except (ValueError,OSError) as exc:
            connection.rollback(); flash(str(exc),'error')
    rows=connection.execute('''SELECT w.* FROM word_feedback_submissions s JOIN word_pdf_imports w ON w.id=s.import_id
        WHERE s.cycle_id=? AND s.manager_pn=? AND s.bundle_id IS NULL ORDER BY w.id''',(cycle_id,manager_pn)).fetchall()
    cycle=connection.execute('SELECT * FROM cycles WHERE id=?',(cycle_id,)).fetchone()
    manager=connection.execute('SELECT * FROM employees WHERE pn=?',(manager_pn,)).fetchone()
    if not cycle or not manager: abort(404)
    pending=connection.execute("SELECT COUNT(*) FROM word_pdf_imports WHERE status='pending' AND json_extract(parsed_json,'$.data.document_kind')='feedback'").fetchone()[0]
    return render_template('feedback_collection.html', collection=next((x for x in word_feedback.collections(connection) if x['cycle_id']==cycle_id and x['manager_pn']==manager_pn),None),active_nav='returns',rows=rows,cycle=cycle,manager=manager,pending=pending)


@bp.get('/feedback-bundles/<int:bundle_id>/download')
def feedback_bundle_download(bundle_id):
    row=get_db().execute('''SELECT b.filename,COALESCE(a.stored_path,b.stored_path) AS path FROM feedback_bundles b
        LEFT JOIN word_feedback_bundle_archives a ON a.bundle_id=b.id WHERE b.id=?''',(bundle_id,)).fetchone()
    if not row or not Path(row['path']).is_file(): abort(404)
    return send_file(row['path'],download_name=row['filename'],mimetype='application/pdf',as_attachment=True)


@bp.post('/feedback-imports/<int:import_id>/reopen')
def reopen_feedback(import_id):
    connection=get_db()
    try:
        reason=request.form.get('reason','').strip()
        if len(reason)<10: raise ValueError('Bitte die Korrektur mit mindestens 10 Zeichen begründen.')
        connection.execute('BEGIN IMMEDIATE')
        state=workflow.pdf_state(connection,import_id)
        row=connection.execute('SELECT * FROM word_feedback_submissions WHERE import_id=?',(import_id,)).fetchone()
        if not row or row['bundle_id'] or str(state['revision'])!=request.form.get('revision'):
            raise ValueError('Bereits gebündelt oder inzwischen geändert. Bitte die Seite neu laden.')
        from .services.sap_staging import available as staged
        if not staged(connection) and connection.execute('SELECT status FROM cycles WHERE id=?',(row['cycle_id'],)).fetchone()[0]=='abgeschlossen':
            raise ValueError('Den Jahresprozess für die Korrektur zuerst wieder öffnen.')
        previous=dict(row)
        connection.execute('DELETE FROM word_feedback_submissions WHERE import_id=?',(import_id,))
        connection.execute("UPDATE word_pdf_imports SET status='pending' WHERE id=?",(import_id,))
        workflow.advance_pdf(connection,import_id,reason=reason)
        connection.commit()
        audit('feedback_correction_opened','word_pdf_import',str(import_id),reason=reason,previous=previous)
        flash('Feedback zur Korrektur geöffnet. Bitte danach erneut bestätigen.','success')
    except ValueError as exc:
        connection.rollback();flash(str(exc),'error')
    return redirect(url_for('main.feedback_review',import_id=import_id))


@bp.route('/cycles/<int:cycle_id>/cases/<case_id>/word-correction', methods=['GET','POST'])
def person_word_correction(cycle_id, case_id):
    from .services import person_corrections as corrections
    db = get_db()
    try:
        case = corrections.person(db,case_id,cycle_id)
    except ValueError:
        abort(404)
    if request.method == 'POST':
        try:
            correction_ids,errors = corrections.prepare_groups(db,case=case,kinds=request.form.getlist('kind'),template_paths=current_app.config['WORD_TEMPLATE_PATHS'],output_dir=_storage_dir('word_corrections'))
            for correction_id in correction_ids:audit('person_word_correction_prepared','word_correction',str(correction_id),case_id=case_id)
            for error in errors:flash(error,'error')
            if correction_ids:flash(f'{len(correction_ids)} Ausgabe(n) nach zuständiger Führungskraft erzeugt. Dateien und Nachricht prüfen, dann Outlook-Entwurf erstellen.','success')
            return redirect(url_for('main.person_word_correction',cycle_id=cycle_id,case_id=case_id)+('#correction-'+str(correction_ids[0]) if correction_ids else ''))
        except (ValueError,LookupError,OSError) as exc:
            flash(str(exc),'error')
    rows = [dict(r) for r in db.execute('SELECT * FROM word_person_corrections WHERE case_id=? ORDER BY id DESC',(case_id,))]
    for row in rows: row['manifest'] = json.loads(row['manifest_json'])
    return render_template('person_word_correction.html',active_nav='dispatch',case=case,corrections=rows)


@bp.get('/word-corrections/<int:correction_id>/download')
def download_person_correction(correction_id):
    row = get_db().execute('SELECT stored_path FROM word_person_corrections WHERE id=?',(correction_id,)).fetchone()
    if not row or not Path(row['stored_path']).is_file(): abort(404)
    return send_file(row['stored_path'],as_attachment=True,download_name=Path(row['stored_path']).name)


@bp.post('/word-corrections/<int:correction_id>/action')
def person_correction_action(correction_id):
    from .services.person_corrections import act
    row = get_db().execute('SELECT p.case_id,dc.cycle_id FROM word_person_corrections p JOIN dialog_cases dc ON dc.case_id=p.case_id WHERE p.id=?',(correction_id,)).fetchone()
    if not row: abort(404)
    try:
        act(get_db(),correction_id=correction_id,action=request.form.get('action'),template_paths=current_app.config['WORD_TEMPLATE_PATHS'],sender_email=current_app.config['HR_MAILBOX_EMAIL'],subject=request.form.get('subject',''),body=request.form.get('body',''),checked=request.form.get('checked')=='yes')
        audit('person_word_correction_action','word_correction',str(correction_id),action_taken=request.form.get('action'))
        flash('Outlook-Entwurf erstellt; in Outlook prüfen und versenden.' if request.form.get('action')=='draft' else 'Outlook-Stand der Einzelausgabe dokumentiert.','success')
    except (ValueError,OSError) as exc: flash(str(exc),'error')
    return redirect(url_for('main.person_word_correction',cycle_id=row['cycle_id'],case_id=row['case_id'])+'#correction-'+str(correction_id))
