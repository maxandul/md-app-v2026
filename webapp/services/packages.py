"""Erzeugt Offline-HTML-Pakete und verarbeitet deren Rücklauf."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
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


def _empty_goal(goal_id: str) -> dict[str, str]:
    return {"id": goal_id, "title": "", "criteria": "", "steps": "", "target_date": ""}


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
    connection: sqlite3.Connection, *, employee_pn: str, review_year: int
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
    if not previous:
        return [], []
    try:
        old_case = json.loads(previous["data_json"])
    except (TypeError, json.JSONDecodeError):
        return [], []

    performance: list[dict[str, str]] = []
    development: list[dict[str, str]] = []
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
    return performance, development


def _new_case(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
    *,
    review_year: int,
    employee_number: int,
) -> dict[str, Any]:
    period_start, period_end = bounded_review_period(
        review_year, row["entry_date"], row["exit_date"]
    )
    previous_goals, previous_development_goals = _prior_goals(
        connection, employee_pn=row["employee_pn"], review_year=review_year
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
            "secondary_employment": row["secondary_employment"],
        },
        "scope": "",
        "dialog_type": "annual",
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
               e.employment_assignment, e.secondary_employment
        FROM dialog_cases dc
        JOIN employees e ON e.pn = dc.employee_pn
        WHERE dc.cycle_id = ? AND dc.manager_pn = ?
        ORDER BY e.last_name, e.first_name, e.pn
        """,
        (cycle_id, manager_pn),
    ).fetchall()
    if not rows:
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


def create_package_file(
    connection: sqlite3.Connection,
    *,
    cycle_id: int,
    manager_pn: str,
    output_dir: Path,
) -> tuple[Path, dict[str, Any]]:
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
            package_id, cycle_id, manager_pn, direction, revision,
            filename, sha256, payload_json, created_at
        ) VALUES (?, ?, ?, 'versand', 0, ?, ?, ?, ?)
        """,
        (
            package["package_id"],
            cycle_id,
            manager_pn,
            filename,
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
        WHERE cycle_id = ? AND manager_pn = ?
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
            package_id, cycle_id, manager_pn, direction, revision,
            filename, sha256, payload_json, created_at
        ) VALUES (?, ?, ?, 'ruecklauf', ?, ?, ?, ?, ?)
        """,
        (
            package["package_id"],
            cycle["id"],
            package["manager_pn"],
            int(package["revision"]),
            original_filename,
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
