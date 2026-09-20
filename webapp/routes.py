"""HTTP-Routen der lokalen MD-Verwaltungsanwendung."""

from __future__ import annotations

import shutil
import uuid
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
    url_for,
)
from werkzeug.utils import secure_filename

from .auth import login_required
from .db import get_db
from .services.cycles import (
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
    import_returned_package,
    manager_package_state,
)
from .services.documents import (
    confirm_digital_signature,
    import_handwritten_scan,
    import_official_pdf,
)
from .services.sap_import import import_sap_workbook
from .services.sap_export import create_sap_upload_file


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
    data = dashboard_data(get_db())
    selected_cycle_id = request.args.get("cycle_id", type=int)
    if selected_cycle_id is None and data["cycles"]:
        selected_cycle_id = data["cycles"][0]["id"]
    return render_template(
        "dialogs.html",
        active_nav="dialogs",
        now_year=datetime.now().year,
        selected_cycle_id=selected_cycle_id,
        events=dialog_event_rows(get_db(), selected_cycle_id),
        event_types=EVENT_TYPE_LABELS,
        scopes=SCOPE_LABELS,
        **data,
    )


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
            review_due_date=request.form.get("review_due_date", ""),
            outlook_due_date=request.form.get("outlook_due_date", ""),
            cycle_id=cycle_id,
        )
    except (TypeError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.dialogs", cycle_id=cycle_id) if cycle_id else url_for("main.dialogs"))
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
    return render_template(
        "dispatch.html", active_nav="dispatch", managers=managers,
        org_units=org_units, **data
    )


@bp.get("/ruecklaeufe")
def returns_overview():
    return render_template(
        "returns.html",
        active_nav="returns",
        **cockpit_overview(
            get_db(), selected_cycle_id=request.args.get("cycle_id", type=int)
        ),
    )


@bp.get("/sap-export")
def sap_exports():
    return render_template(
        "sap_exports.html",
        active_nav="sap_export",
        **dashboard_data(get_db()),
    )


@bp.get("/auswertungen")
def analytics():
    return render_template(
        "analytics.html",
        active_nav="analytics",
        **dashboard_data(get_db()),
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
        "cycle.html", cycle=cycle, managers=manager_rows, active_nav="dialogs"
    )


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


@bp.post("/cycles/<int:cycle_id>/sap-export")
def download_sap_export(cycle_id: int):
    try:
        path = create_sap_upload_file(
            get_db(),
            cycle_id=cycle_id,
            template_path=Path(current_app.root_path).parent / "templates" / "massenupload.xlsx",
            output_dir=_storage_dir("sap_exports"),
        )
    except (LookupError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("main.cycle_detail", cycle_id=cycle_id))
    return send_file(
        path,
        as_attachment=True,
        download_name=path.name,
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
    response = send_file(
        path,
        as_attachment=True,
        download_name=path.name,
        mimetype="application/zip",
    )
    response.headers["X-MD-START-Count"] = str(counts["start"])
    response.headers["X-MD-Update-Count"] = str(counts["update"])
    return response


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
