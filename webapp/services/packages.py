"""Erzeugt Offline-HTML-Pakete und verarbeitet deren Rücklauf."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
import uuid
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from prototype.html_dialog.generate_package import output_filename, render_html
from prototype.html_dialog.validate_package import (
    employee_status,
    extract_payload,
    validate_payload,
)

from webapp.competency_model import COMPETENCY_MODEL, COMPETENCY_NAMES


NO_MD_REASONS = [
    "Austritt",
    "Pensionierung",
    "Wechsel der vorgesetzten Person",
    "Neueintritt",
    "Längere Abwesenheit",
    "Anderer Grund",
]


def _filename_part(value: Any) -> str:
    ascii_value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9_-]+", "_", ascii_value).strip("_") or "Unbekannt"


def _empty_goal(goal_id: str) -> dict[str, str]:
    return {"id": goal_id, "title": "", "criteria": "", "steps": "", "target_date": ""}


def _secondary_employment_text(
    connection: sqlite3.Connection, *, employee_pn: str,
    employment_assignment: str, fallback: str = "",
) -> str:
    rows = connection.execute(
        """
        SELECT p.valid_from, p.valid_to, p.permission, p.permission_for
        FROM secondary_activity_permissions p
        JOIN employment_assignments ea ON ea.id = p.employment_id
        WHERE ea.person_number = ? AND ea.assignment_number = ?
        ORDER BY p.valid_from, p.valid_to, p.id
        """,
        (employee_pn, employment_assignment),
    ).fetchall()
    entries: list[str] = []
    for row in rows:
        description = " · ".join(
            dict.fromkeys(
                value.strip() for value in (
                    str(row["permission_for"] or ""),
                    str(row["permission"] or ""),
                ) if value.strip()
            )
        )
        period = "–".join(
            value for value in (
                str(row["valid_from"] or "").strip(),
                str(row["valid_to"] or "").strip(),
            ) if value
        )
        text = description or "Nebenbeschäftigung/öffentliches Amt"
        if period:
            text += f" ({period})"
        entries.append(text)
    return "\n".join(entries) if entries else str(fallback or "")


def bounded_review_period(
    review_year: int, entry_date: str = "", exit_date: str = ""
) -> tuple[str, str]:
    """Liefert den Jahreszeitraum, begrenzt auf die bekannte Anstellung."""
    period_start = date(review_year, 1, 1)
    period_end = date(review_year, 12, 31)
    if entry_date:
        period_start = max(period_start, date.fromisoformat(entry_date))
    if exit_date:
        period_end = min(period_end, date.fromisoformat(exit_date))
    if period_start > period_end:
        raise ValueError(
            f"Für {review_year} liegt kein Zeitraum innerhalb der bekannten Anstellung vor."
        )
    return period_start.isoformat(), period_end.isoformat()


def _prior_goals(
    connection: sqlite3.Connection, *, employee_pn: str,
    employment_assignment: str, review_year: int,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    previous = connection.execute(
        """
        SELECT dc.data_json
        FROM dialog_cases dc
        JOIN cycles c ON c.id = dc.cycle_id
        WHERE dc.employee_pn = ? AND c.outlook_year = ? AND dc.data_json <> ''
        ORDER BY c.review_year DESC, dc.updated_at DESC
        LIMIT 1
        """,
        (employee_pn, review_year),
    ).fetchone()
    performance: list[dict[str, str]] = []
    development: list[dict[str, str]] = []
    if previous:
        try:
            old_case = json.loads(previous["data_json"])
        except (TypeError, json.JSONDecodeError):
            old_case = {}
        outlook = old_case.get("outlook") or {}
        for destination, prefix, sources in (
            (performance, "previous", outlook.get("performance_goals") or []),
            (development, "previous-development", outlook.get("development_goals") or []),
        ):
            for index, goal in enumerate(sources, start=1):
                title = str(goal.get("title", "")).strip()
                if not title:
                    continue
                destination.append({
                    "id": f"{prefix}-{employee_pn}-{index}",
                    "imported": True,
                    "title": title,
                    "criteria": str(goal.get("criteria", "")),
                    "steps": str(goal.get("steps", "")),
                    "target_date": str(goal.get("target_date", "")),
                    "competency": str(goal.get("competency", "")),
                    "achievement": "",
                    "review": "",
                })
        if performance or development:
            return performance, development

    rows = connection.execute(
        """
        SELECT * FROM historical_goals
        WHERE employee_pn = ? AND goal_year = ?
          AND (assignment_number = ? OR assignment_number = '')
        ORDER BY goal_kind, sequence, id
        """,
        (employee_pn, review_year, employment_assignment),
    ).fetchall()
    for row in rows:
        destination = performance if row["goal_kind"] == "performance" else development
        prefix = "legacy-previous" if row["goal_kind"] == "performance" else "legacy-development"
        destination.append({
            "id": f"{prefix}-{row['id']}",
            "imported": True,
            "title": row["title"],
            "criteria": row["criteria"],
            "steps": row["steps"],
            "target_date": row["target_date"],
            "competency": row["competency"],
            "achievement": "",
            "review": "",
        })
    return performance, development


def _new_case(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
    *,
    review_year: int,
    employee_number: int,
) -> dict[str, Any]:
    if row["period_start"] and row["period_end"]:
        period_start, period_end = row["period_start"], row["period_end"]
    else:
        period_start, period_end = bounded_review_period(
            review_year, row["entry_date"], row["exit_date"]
        )
    previous_goals, previous_development_goals = _prior_goals(
        connection, employee_pn=row["employee_pn"],
        employment_assignment=row["employment_assignment"], review_year=review_year,
    )
    return {
        "case_id": row["case_id"],
        "employee": {
            "pn": row["employee_pn"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "full_name": " ".join(
                part for part in (row["first_name"], row["last_name"]) if part
            ),
            "position": row["position"],
            "org_unit": row["org_unit"],
            "employment_degree": row["employment_degree"],
            "entry_date": row["entry_date"],
            "exit_date": row["exit_date"],
            "probation_end": row["probation_end"],
            "employment_assignment": row["employment_assignment"],
            "secondary_employment": _secondary_employment_text(
                connection,
                employee_pn=row["employee_pn"],
                employment_assignment=row["employment_assignment"],
                fallback=row["secondary_employment"],
            ),
        },
        # Der aus den Stammdaten abgeleitete Mindestumfang ist die sichere
        # Ausgangsauswahl. Führungskräfte können zusätzliche Teile wählen oder
        # einen Pflichtteil nur mit dokumentierter Begründung weglassen.
        "scope": row["suggested_scope"],
        "dialog_type": "probation" if str(row["event_type"] or "").startswith("probation_") else "annual",
        "scope_reason": "",
        "no_md_reason": "",
        "no_md_note": "",
        "suggestion": {
            "scope": row["suggested_scope"],
            "reason": row["suggestion_reason"],
            "is_special": row["suggested_scope"] != "full" or "Probezeit" in row["suggestion_reason"],
        },
        "period_start": period_start,
        "period_end": period_end,
        "previous_goals": previous_goals,
        "previous_development_goals": previous_development_goals,
        "review": {
            "dialog_date": "",
            "employment_continued": "",
            "general_notes": "",
            "performance": "",
            "competencies": [],
            "overall_rating": "",
            "agreement": "",
            "manager_comment": "",
            "employee_comment": "",
            "next_level_conversation": "Nein",
            "next_level_comment": "",
            "secondary_employment_current": "",
            "secondary_employment_note": "",
        },
        "outlook": {
            "dialog_date": "",
            "performance_goals": [_empty_goal(f"goal-{employee_number}-1")],
            "open_goals_text": "",
            "development_goals": [],
            "nep": "",
            "nep_notes": "",
            "general_notes": "",
        },
        "meta": {"updated_at": "", "pdf_exported_at": "", "archived": False, "closed": False, "closed_at": ""},
        "document_tracking": {
            "review": {"status": "preparation", "note": ""},
            "outlook": {"status": "preparation", "note": ""},
            "no_md": {"status": "preparation", "note": ""},
        },
    }


def build_manager_payload(
    connection: sqlite3.Connection,
    *,
    cycle_id: int,
    manager_pn: str,
    created_at: datetime | None = None,
    allow_empty: bool = False,
) -> dict[str, Any]:
    cycle = connection.execute("SELECT * FROM cycles WHERE id = ?", (cycle_id,)).fetchone()
    if not cycle:
        raise LookupError("Jahresprozess nicht gefunden.")
    manager = connection.execute("SELECT * FROM employees WHERE pn = ?", (manager_pn,)).fetchone()
    manager_first_name = manager["first_name"] if manager else ""
    manager_last_name = manager["last_name"] if manager else ""
    manager_name = " ".join(
        part for part in (manager_first_name, manager_last_name) if part
    ) or f"VG {manager_pn}"
    manager_email = manager["email"] if manager else ""

    rows = connection.execute(
        """
        SELECT dc.*, e.first_name, e.last_name, e.position, e.org_unit,
               e.employment_degree, e.entry_date, e.exit_date, e.probation_end,
               e.employment_assignment, e.secondary_employment,
               COALESCE(de.event_type, 'annual') AS event_type
        FROM dialog_cases dc
        JOIN employees e ON e.pn = dc.employee_pn
        LEFT JOIN dialog_events de ON de.legacy_case_id = dc.case_id
        WHERE dc.cycle_id = ? AND dc.manager_pn = ? AND dc.active = 1
        ORDER BY e.last_name, e.first_name, e.pn
        """,
        (cycle_id, manager_pn),
    ).fetchall()
    if not rows and not allow_empty:
        raise LookupError("Für diese Führungslinie sind keine MD-Fälle vorhanden.")

    employees: list[dict[str, Any]] = []
    for number, row in enumerate(rows, start=1):
        if row["data_json"]:
            try:
                employees.append(json.loads(row["data_json"]))
                continue
            except json.JSONDecodeError:
                pass
        employees.append(
            _new_case(
                connection,
                row,
                review_year=cycle["review_year"],
                employee_number=number,
            )
        )

    timestamp = created_at or datetime.now().astimezone()
    return {
        "schema_version": "1.0",
        "app_version": "0.3.0-mvp",
        "package": {
            "package_id": (
                f"MD-{cycle['review_year']}-{manager_pn}-{uuid.uuid4().hex[:8].upper()}"
            ),
            "cycle_id": cycle_id,
            "manager_pn": manager_pn,
            "manager_name": manager_name,
            "manager_first_name": manager_first_name,
            "manager_last_name": manager_last_name,
            "manager_email": manager_email,
            "rb_year": cycle["review_year"],
            "ab_year": cycle["outlook_year"],
            "created_at": timestamp.isoformat(timespec="seconds"),
            "saved_at": "",
            "revision": 0,
            "s_mime_required": True,
            "business_device_only": True,
        },
        "configuration": {
            "competencies": COMPETENCY_NAMES,
            "competency_model": COMPETENCY_MODEL,
            "no_md_reasons": NO_MD_REASONS,
        },
        "employees": employees,
    }


def _workbook_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Reduziert ein Paket auf die Angaben, die HR mit Updates steuert."""
    result: dict[str, Any] = {}
    package = payload.get("package") or payload.get("update") or {}
    goal_keys = ("id", "title", "criteria", "steps", "target_date", "competency", "imported")

    def goal_sources(goals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {key: goal.get(key, "") for key in goal_keys if key in goal}
            for goal in goals
        ]

    for item in payload.get("employees") or []:
        case_id = str(item.get("case_id", ""))
        result[case_id] = {
            "employee": item.get("employee") or {},
            "dialog_type": item.get("dialog_type", "annual"),
            "suggestion": item.get("suggestion") or {},
            "period_start": item.get("period_start", ""),
            "period_end": item.get("period_end", ""),
            "previous_goals": goal_sources(item.get("previous_goals") or []),
            "previous_development_goals": goal_sources(
                item.get("previous_development_goals") or []
            ),
        }
    return {
        "manager": {
            "manager_name": package.get("manager_name", ""),
            "manager_first_name": package.get("manager_first_name", ""),
            "manager_last_name": package.get("manager_last_name", ""),
        },
        "employees": result,
    }


def _latest_start_event(
    connection: sqlite3.Connection, *, cycle_id: int, manager_pn: str
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT * FROM package_events
        WHERE cycle_id = ? AND manager_pn = ? AND direction = 'versand'
          AND package_kind = 'start'
        ORDER BY id DESC LIMIT 1
        """,
        (cycle_id, manager_pn),
    ).fetchone()


def _latest_outbound_event(
    connection: sqlite3.Connection, *, cycle_id: int, manager_pn: str
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT * FROM package_events
        WHERE cycle_id = ? AND manager_pn = ? AND direction = 'versand'
        ORDER BY id DESC LIMIT 1
        """,
        (cycle_id, manager_pn),
    ).fetchone()


def existing_start_file(
    connection: sqlite3.Connection, *, cycle_id: int, manager_pn: str
) -> tuple[Path, sqlite3.Row]:
    """Liefert die unveränderte, bereits erzeugte START-Datei erneut aus."""
    event = _latest_start_event(
        connection, cycle_id=cycle_id, manager_pn=manager_pn
    )
    if not event:
        raise LookupError("Für diese Führungskraft wurde noch keine START-Datei erzeugt.")
    path = Path(event["stored_path"] or "")
    if not path.is_file():
        raise ValueError(
            "Die gespeicherte START-Datei ist nicht mehr verfügbar. "
            "Bitte stelle das System aus einer Sicherung wieder her."
        )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != event["sha256"]:
        raise ValueError(
            "Die gespeicherte START-Datei stimmt nicht mehr mit ihrer Prüfsumme überein."
        )
    return path, event


def manager_package_state(
    connection: sqlite3.Connection, *, cycle_id: int, manager_pn: str
) -> dict[str, Any]:
    """Liefert START-/Update-Status ohne eine Datei zu erzeugen."""
    current = build_manager_payload(
        connection, cycle_id=cycle_id, manager_pn=manager_pn, allow_empty=True
    )
    cycle = connection.execute(
        "SELECT sap_import_id FROM cycles WHERE id = ?", (cycle_id,)
    ).fetchone()
    cases = connection.execute(
        """
        SELECT employee_pn, employment_assignment
        FROM dialog_cases
        WHERE cycle_id = ? AND manager_pn = ? AND active = 1
        """,
        (cycle_id, manager_pn),
    ).fetchall()
    issues: list[dict[str, str]] = []
    for case in cases:
        if not str(case["employment_assignment"] or "").strip():
            issues.append({
                "severity": "blocking",
                "message": f"Bei PN {case['employee_pn']} fehlt die Anstellungsnummer.",
            })
    person_numbers = [manager_pn, *(row["employee_pn"] for row in cases)]
    if cycle and person_numbers:
        placeholders = ",".join("?" for _ in person_numbers)
        conflicts = connection.execute(
            f"""
            SELECT person_number, issue_type FROM sap_import_issues
            WHERE sap_import_id = ? AND status = 'open' AND severity = 'blocking'
              AND person_number IN ({placeholders})
            ORDER BY person_number, id
            """,
            (cycle["sap_import_id"], *person_numbers),
        ).fetchall()
        issues.extend(
            {
                "severity": "blocking",
                "message": f"Offener SAP-Konflikt bei PN {row['person_number']} ({row['issue_type']}).",
            }
            for row in conflicts
        )
    manager = connection.execute(
        "SELECT email FROM employees WHERE pn = ? AND active = 1", (manager_pn,)
    ).fetchone()
    if cases and (not manager or not str(manager["email"] or "").strip()):
        issues.append({
            "severity": "warning",
            "message": "Für die Führungskraft fehlt eine geschäftliche E-Mail-Adresse.",
        })
    readiness = {
        "issues": issues,
        "blocking": any(issue["severity"] == "blocking" for issue in issues),
    }
    start = _latest_start_event(
        connection, cycle_id=cycle_id, manager_pn=manager_pn
    )
    if not start:
        return {"state": "start_missing", "label": "START-Datei fehlt", "current": current, **readiness}
    latest = _latest_outbound_event(
        connection, cycle_id=cycle_id, manager_pn=manager_pn
    )
    try:
        previous = json.loads(latest["payload_json"]) if latest else {}
    except json.JSONDecodeError:
        previous = {}
    update_required = _workbook_snapshot(previous) != _workbook_snapshot(current)
    return {
        "state": "update_required" if update_required else "current",
        "label": "Update erforderlich" if update_required else "Aktuell",
        "current": current,
        "start": start,
        "latest": latest,
        **readiness,
    }


def build_update_payload(
    connection: sqlite3.Connection,
    *,
    cycle_id: int,
    manager_pn: str,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    state = manager_package_state(
        connection, cycle_id=cycle_id, manager_pn=manager_pn
    )
    if state["blocking"]:
        detail = " ".join(
            issue["message"] for issue in state["issues"]
            if issue["severity"] == "blocking"
        )
        raise ValueError(f"Die Update-Datei kann nicht erzeugt werden: {detail}")
    if state["state"] == "start_missing":
        raise ValueError("Für diese Führungskraft muss zuerst eine START-Datei erzeugt werden.")
    if state["state"] == "current":
        raise ValueError("Die Arbeitsmappe ist bereits aktuell; es ist kein Update erforderlich.")
    current = state["current"]
    start = state["start"]
    timestamp = created_at or datetime.now().astimezone()
    return {
        "schema_version": "1.0-update",
        "update": {
            "update_id": f"UPD-{cycle_id}-{manager_pn}-{uuid.uuid4().hex[:8].upper()}",
            "target_package_id": start["package_id"],
            "cycle_id": cycle_id,
            "manager_pn": manager_pn,
            "manager_name": current["package"]["manager_name"],
            "manager_first_name": current["package"]["manager_first_name"],
            "manager_last_name": current["package"]["manager_last_name"],
            "rb_year": current["package"]["rb_year"],
            "ab_year": current["package"]["ab_year"],
            "created_at": timestamp.isoformat(timespec="seconds"),
        },
        "employees": current["employees"],
    }


def create_update_file(
    connection: sqlite3.Connection,
    *,
    cycle_id: int,
    manager_pn: str,
    output_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    payload = build_update_payload(
        connection, cycle_id=cycle_id, manager_pn=manager_pn
    )
    update = payload["update"]
    safe_manager = _filename_part(update["manager_name"])
    filename = (
        f"MD_Update_{update['rb_year']}_{update['ab_year']}_"
        f"{safe_manager}_{manager_pn}.json"
    )
    path = output_dir / update["update_id"] / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    path.write_bytes(raw)
    connection.execute(
        """
        INSERT INTO package_events (
            package_id, cycle_id, manager_pn, direction, package_kind, revision,
            filename, stored_path, sha256, payload_json, created_at
        ) VALUES (?, ?, ?, 'versand', 'update', 0, ?, ?, ?, ?, ?)
        """,
        (
            update["target_package_id"], cycle_id, manager_pn, filename, str(path),
            hashlib.sha256(raw).hexdigest(),
            json.dumps(payload, ensure_ascii=False), update["created_at"],
        ),
    )
    connection.commit()
    return path, payload


def create_package_batch(
    connection: sqlite3.Connection,
    *,
    cycle_id: int,
    manager_pns: list[str],
    output_dir: Path,
) -> tuple[Path, dict[str, int]]:
    """Erzeugt pro Führungskraft die erforderliche START- oder Update-Datei."""
    unique_manager_pns = list(dict.fromkeys(str(pn).strip() for pn in manager_pns if str(pn).strip()))
    if not unique_manager_pns:
        raise ValueError("Bitte wähle mindestens eine Führungskraft aus.")
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    batch_dir = output_dir / f"batch_{cycle_id}_{stamp}_{uuid.uuid4().hex[:6]}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    counts = {"start": 0, "update": 0, "current": 0}
    for manager_pn in unique_manager_pns:
        state = manager_package_state(
            connection, cycle_id=cycle_id, manager_pn=manager_pn
        )
        if state["blocking"]:
            detail = " ".join(issue["message"] for issue in state["issues"] if issue["severity"] == "blocking")
            raise ValueError(f"Arbeitsmappe für PN {manager_pn} kann nicht erzeugt werden: {detail}")
        if state["state"] == "start_missing":
            path, _payload = create_package_file(
                connection, cycle_id=cycle_id, manager_pn=manager_pn,
                output_dir=batch_dir / "starts",
            )
            counts["start"] += 1
            created.append(path)
        elif state["state"] == "update_required":
            path, _payload = create_update_file(
                connection, cycle_id=cycle_id, manager_pn=manager_pn,
                output_dir=batch_dir / "updates",
            )
            counts["update"] += 1
            created.append(path)
        else:
            counts["current"] += 1
    if not created:
        raise ValueError("Für die Auswahl sind keine START- oder Update-Dateien erforderlich.")
    zip_path = output_dir / f"MD_Arbeitsmappen_{cycle_id}_{stamp}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in created:
            folder = "START" if path.suffix.lower() == ".html" else "UPDATE"
            archive.write(path, arcname=f"{folder}/{path.name}")
    return zip_path, counts


def create_package_file(
    connection: sqlite3.Connection,
    *,
    cycle_id: int,
    manager_pn: str,
    output_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    readiness = manager_package_state(
        connection, cycle_id=cycle_id, manager_pn=manager_pn
    )
    if readiness["state"] != "start_missing":
        raise ValueError(
            "Für diese Führungskraft besteht bereits eine START-Datei. "
            "Erzeuge bei Änderungen eine Update-Datei."
        )
    if readiness["blocking"]:
        detail = " ".join(
            issue["message"] for issue in readiness["issues"]
            if issue["severity"] == "blocking"
        )
        raise ValueError(f"Die START-Datei kann nicht erzeugt werden: {detail}")
    payload = build_manager_payload(
        connection, cycle_id=cycle_id, manager_pn=manager_pn
    )
    html = render_html(payload)
    filename = output_filename(payload)
    package = payload["package"]
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / package["package_id"] / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
    connection.execute(
        """
        INSERT INTO package_events (
            package_id, cycle_id, manager_pn, direction, package_kind, revision,
            filename, stored_path, sha256, payload_json, created_at
        ) VALUES (?, ?, ?, 'versand', 'start', 0, ?, ?, ?, ?, ?)
        """,
        (
            package["package_id"],
            cycle_id,
            manager_pn,
            filename,
            str(path),
            digest,
            json.dumps(payload, ensure_ascii=False),
            datetime.now().astimezone().isoformat(timespec="seconds"),
        ),
    )
    connection.commit()
    return path, payload


def import_returned_package(
    connection: sqlite3.Connection,
    *,
    path: Path,
    original_filename: str,
) -> dict[str, Any]:
    payload = extract_payload(path)
    validation = validate_payload(payload)
    if not validation.valid:
        raise ValueError("Ungültiges MD-Paket: " + " ".join(validation.errors))
    package = payload["package"]
    if int(package.get("revision", 0)) < 1 or not package.get("saved_at"):
        raise ValueError(
            "Die Datei ist noch eine Startdatei. Bitte in der HTML-Datei «Zwischenstand speichern» wählen."
        )

    sent = connection.execute(
        """
        SELECT * FROM package_events
        WHERE package_id = ? AND direction = 'versand'
        ORDER BY id DESC LIMIT 1
        """,
        (package["package_id"],),
    ).fetchone()
    if not sent:
        raise ValueError("Die Paket-ID ist in dieser Datenbank nicht als Versand registriert.")
    if sent["manager_pn"] != str(package["manager_pn"]):
        raise ValueError("Die VG-Personalnummer stimmt nicht mit dem Versandpaket überein.")

    latest_return = connection.execute(
        """
        SELECT r.revision, r.package_id,
               (SELECT s.id FROM package_events s
                WHERE s.package_id = r.package_id AND s.direction = 'versand'
                ORDER BY s.id DESC LIMIT 1) AS source_send_id
        FROM package_events r
        WHERE r.cycle_id = ? AND r.manager_pn = ? AND r.direction = 'ruecklauf'
        ORDER BY r.id DESC LIMIT 1
        """,
        (sent["cycle_id"], package["manager_pn"]),
    ).fetchone()
    if latest_return:
        if sent["id"] < latest_return["source_send_id"]:
            raise ValueError(
                "Diese Startdatei ist älter als der bereits importierte Rücklauf dieser Führungslinie."
            )
        if (
            package["package_id"] == latest_return["package_id"]
            and int(package["revision"]) <= int(latest_return["revision"])
        ):
            raise ValueError(
                f"Version v{int(package['revision']):02d} wurde bereits importiert oder ist veraltet. "
                f"Aktuell ist v{int(latest_return['revision']):02d}."
            )

    cycle = connection.execute(
        "SELECT * FROM cycles WHERE id = ?", (sent["cycle_id"],)
    ).fetchone()
    if (
        not cycle
        or cycle["review_year"] != int(package["rb_year"])
        or cycle["outlook_year"] != int(package["ab_year"])
    ):
        raise ValueError("Rückblick- oder Ausblickjahr stimmt nicht mit dem Jahresprozess überein.")

    expected_rows = connection.execute(
        """
        SELECT case_id, employee_pn FROM dialog_cases
        WHERE cycle_id = ? AND manager_pn = ? AND active = 1
        """,
        (cycle["id"], package["manager_pn"]),
    ).fetchall()
    expected = {row["case_id"]: row["employee_pn"] for row in expected_rows}
    returned = {str(item.get("case_id", "")): item for item in payload["employees"]}
    if set(returned) != set(expected):
        raise ValueError("Die Fälle der Rücksendung stimmen nicht vollständig mit dem Versand überein.")

    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    for case_id, employee in returned.items():
        pn = str((employee.get("employee") or {}).get("pn", ""))
        if pn != expected[case_id]:
            raise ValueError(f"Personalnummer im Fall {case_id} wurde verändert.")
        status, _missing = employee_status(employee)
        db_status = status
        if status == "offen" and employee.get("scope"):
            db_status = "in_bearbeitung"
        connection.execute(
            """
            UPDATE dialog_cases
            SET status = ?, data_json = ?, updated_at = ?
            WHERE case_id = ? AND cycle_id = ?
            """,
            (
                db_status,
                json.dumps(employee, ensure_ascii=False),
                timestamp,
                case_id,
                cycle["id"],
            ),
        )

    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    connection.execute(
        """
        INSERT INTO package_events (
            package_id, cycle_id, manager_pn, direction, package_kind, revision,
            filename, stored_path, sha256, payload_json, created_at
        ) VALUES (?, ?, ?, 'ruecklauf', 'return', ?, ?, ?, ?, ?, ?)
        """,
        (
            package["package_id"],
            cycle["id"],
            package["manager_pn"],
            int(package["revision"]),
            original_filename,
            str(path),
            digest,
            json.dumps(payload, ensure_ascii=False),
            timestamp,
        ),
    )
    connection.commit()
    return {
        "cycle_id": cycle["id"],
        "manager_pn": package["manager_pn"],
        "manager_name": package["manager_name"],
        "revision": package["revision"],
        "warnings": validation.warnings,
        "summary": validation.summary,
    }
