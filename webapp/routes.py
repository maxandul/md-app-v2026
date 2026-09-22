"""HTTP-Routen der lokalen MD-Verwaltungsanwendung."""

from __future__ import annotations

import json
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
    create_update_file,
    existing_start_file,
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
    return None


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
    return sorted(selected)


@bp.get("/")
def dashboard():
    selected_cycle_id = request.args.get("cycle_id", type=int)
    return render_template(
        "dashboard.html",
        now_year=datetime.now().year,
        active_nav="overview",
        **cockpit_overview(get_db(), selected_cycle_id=selected_cycle_id),
    )


@bp.get("/stammdaten")
def master_data():
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
    if selected_cycle_id is None and data["cycles"]:
        selected_cycle_id = data["cycles"][0]["id"]
    query = request.args.get("q", "").strip()
    event_type = request.args.get("event_type", "").strip()
    event_status = request.args.get("status", "").strip()
    page = max(1, request.args.get("page", default=1, type=int) or 1)
    per_page = 50
    all_events = dialog_event_rows(connection, selected_cycle_id)
    if query:
        needle = query.casefold()
        all_events = [
            item for item in all_events
            if needle in " ".join(
                str(item.get(key, "")) for key in (
                    "first_name", "last_name", "employee_pn", "assignment_number",
                    "manager_name", "manager_pn",
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
        now_year=datetime.now().year,
        selected_cycle_id=selected_cycle_id,
        selected_cycle=selected_cycle,
        events=events,
        event_total=event_total,
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
        event_id = create_manual_event(
            get_db(),
            employee_pn=request.form.get("employee_pn", ""),
            assignment_number=request.form.get("assignment_number", ""),
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
        "dispatch.html", active_nav="dispatch", managers=managers,
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
        active_nav="returns",
        **cockpit,
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


@bp.get("/administration")
@system_admin_required
def administration():
    return render_template(
        "administration.html", active_nav="administration",
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
        row_count=len(data["timings"] if report == "timings" else data["ratings"] if report == "ratings" else data["competencies"]),
    )
    return send_file(
        BytesIO(content), as_attachment=True, download_name=filename,
        mimetype="text/csv; charset=utf-8",
    )


@bp.post("/imports")
def upload_sap_import():
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
        export_batches=sap_export_batches(get_db(), cycle_id=cycle_id),
        cycle_status_labels=CYCLE_STATUS_LABELS,
        active_nav="dialogs"
    )


@bp.post("/cycles/<int:cycle_id>/status")
def set_cycle_status(cycle_id: int):
    try:
        old_status, new_status = change_cycle_status(
            get_db(), cycle_id=cycle_id,
            new_status=request.form.get("status", "").strip(),
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
        active_nav="dialogs",
    )


@bp.get("/cycles/<int:cycle_id>/cases/<case_id>")
def case_detail(cycle_id: int, case_id: str):
    try:
        detail = case_review_detail(get_db(), cycle_id=cycle_id, case_id=case_id)
    except LookupError:
        abort(404)
    return render_template(
        "case_detail.html", active_nav="returns", cycle_id=cycle_id, **detail
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


@bp.post("/cycles/<int:cycle_id>/managers/<manager_pn>/package/redownload")
def redownload_manager_package(cycle_id: int, manager_pn: str):
    try:
        path, event = existing_start_file(
            get_db(), cycle_id=cycle_id, manager_pn=manager_pn
        )
    except (LookupError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(request.referrer or url_for("main.dispatch", cycle_id=cycle_id))
    audit(
        "manager_package_redownloaded", "package", event["package_id"],
        cycle_id=cycle_id, manager_pn=manager_pn, sha256=event["sha256"],
    )
    return send_file(
        path,
        as_attachment=True,
        download_name=event["filename"],
        mimetype="text/html; charset=utf-8",
    )


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
    return redirect(url_for("main.dispatch", cycle_id=cycle_id))


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


@bp.post("/mail-inbox/scan")
def scan_mail_inbox():
    try:
        result = scan_outlook_inbox(
            get_db(),
            mailbox_name=current_app.config["OUTLOOK_MAILBOX_NAME"],
            target_folder=current_app.config["OUTLOOK_TARGET_FOLDER"],
            inbox_dir=_storage_dir("mail_inbox"),
            pdf_dir=_storage_dir("pdf_processed"),
            handoff_dir=_handoff_dir(),
        )
    except Exception as exc:
        flash(str(exc), "error")
    else:
        flash(
            f"Postfach gelesen: {result['read']} Nachricht(en), "
            f"{result['stored']} neue Anhänge gesichert, "
            f"{result['moved']} verarbeitet und verschoben, "
            f"{result['review']} zur HR-Prüfung, {result['ignored']} ohne MD-Bezug ignoriert, "
            f"{result['duplicates']} bereits bekannt, "
            f"{result['feedback_bundles']} Feedback-Sammel-PDF(s) erstellt.",
            "success",
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


@bp.post("/documents/<int:document_id>/signature-checked")
def mark_signature_checked(document_id: int):
    try:
        result = confirm_digital_signature(
            get_db(), document_id=document_id, handoff_dir=_handoff_dir()
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(request.referrer or url_for("main.dashboard"))
    if result["scan_required"]:
        flash("Unterschriften bestätigt. Der handschriftliche Scan ist noch ausstehend.", "success")
    else:
        flash(
            f"Unterschriften bestätigt und «{result['handoff_filename']}» für die Personaldossier-Ablage bereitgestellt.",
            "success",
        )
    return redirect(request.referrer or url_for("main.dashboard"))


@bp.post("/cases/<case_id>/scans/<document_kind>")
def upload_scan(case_id: str, document_kind: str):
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
