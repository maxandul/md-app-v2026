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
)
from .services.packages import create_package_file, import_returned_package
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


@bp.get("/")
def dashboard():
    return render_template(
        "dashboard.html",
        now_year=datetime.now().year,
        **dashboard_data(get_db()),
    )


@bp.post("/imports")
def upload_sap_import():
    upload = request.files.get("sap_file")
    if not upload or not upload.filename:
        flash("Bitte wähle einen SAP-Excel-Export aus.", "error")
        return redirect(url_for("main.dashboard"))
    if not upload.filename.lower().endswith(".xlsx"):
        flash("Der SAP-Import muss eine XLSX-Datei sein.", "error")
        return redirect(url_for("main.dashboard"))

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
        return redirect(url_for("main.dashboard"))

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
    flash(message, "success")
    return redirect(url_for("main.dashboard"))


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
    return render_template("import_detail.html", imported=imported, issues=issues)


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
        return redirect(url_for("main.dashboard"))
    flash(f"Jahresprozess {review_year}/{review_year + 1} wurde angelegt.", "success")
    return redirect(url_for("main.cycle_detail", cycle_id=cycle_id))


@bp.get("/cycles/<int:cycle_id>")
def cycle_detail(cycle_id: int):
    try:
        cycle, managers = cycle_overview(get_db(), cycle_id)
    except LookupError:
        abort(404)
    return render_template("cycle.html", cycle=cycle, managers=managers)


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


@bp.post("/returns")
def upload_return():
    upload = request.files.get("return_file")
    if not upload or not upload.filename:
        flash("Bitte wähle die zurückgesendete HTML-Datei aus.", "error")
        return redirect(url_for("main.dashboard"))
    if not upload.filename.lower().endswith(('.html', '.htm')):
        flash("Der Rücklauf muss eine gespeicherte HTML-Datei sein.", "error")
        return redirect(url_for("main.dashboard"))

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
        return redirect(url_for("main.dashboard"))

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
        return redirect(url_for("main.dashboard"))

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
    return redirect(url_for("main.dashboard"))


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
            f"Unterschriften bestätigt und «{result['handoff_filename']}» für RPA bereitgestellt.",
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
        f"Handschriftlicher Scan «{result['handoff_filename']}» für RPA bereitgestellt.",
        "success",
    )
    return redirect(request.referrer or url_for("main.dashboard"))


@bp.app_errorhandler(413)
def file_too_large(_error):
    flash("Die Datei ist grösser als 25 MB.", "error")
    return redirect(url_for("main.dashboard"))
