"""Gefilterte operative und anonymisierte MD-Auswertungen."""

from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
from collections import Counter
from datetime import date
from typing import Any

from .dialog_events import EVENT_TYPE_LABELS


def _json(value: str | None) -> dict[str, Any]:
    try:
        result = json.loads(value or "{}")
        return result if isinstance(result, dict) else {}
    except json.JSONDecodeError:
        return {}


def _rating(value: Any) -> str:
    match = re.match(r"^\s*([A-E])\b", str(value or ""), re.IGNORECASE)
    return match.group(1).upper() if match else ""


def _names(items: Any) -> set[str]:
    if not isinstance(items, list):
        return set()
    return {
        str(item.get("competency", "")).strip()
        for item in items if isinstance(item, dict) and item.get("competency")
    }


def _pipe_names(value: Any) -> set[str]:
    return {part.strip() for part in str(value or "").split("|") if part.strip()}


def analysis_options(connection: sqlite3.Connection) -> dict[str, Any]:
    return {
        "cycles": connection.execute(
            "SELECT id, review_year, outlook_year FROM cycles ORDER BY review_year DESC"
        ).fetchall(),
        "org_units": [
            row["org_unit"] for row in connection.execute(
                """
                SELECT DISTINCT org_unit FROM employment_assignments
                WHERE org_unit <> '' ORDER BY org_unit
                """
            ).fetchall()
        ],
        "event_types": EVENT_TYPE_LABELS,
    }


def _source_rows(
    connection: sqlite3.Connection, *, cycle_id: int | None = None,
    org_unit: str = "", event_type: str = "",
) -> list[sqlite3.Row]:
    where = ["de.status <> 'cancelled'"]
    params: list[Any] = []
    if cycle_id is not None:
        where.append("de.cycle_id = ?")
        params.append(cycle_id)
    if org_unit:
        where.append("ea.org_unit = ?")
        params.append(org_unit)
    if event_type:
        if event_type not in EVENT_TYPE_LABELS:
            raise ValueError("Die gewählte Dialogart ist ungültig.")
        where.append("de.event_type = ?")
        params.append(event_type)
    return connection.execute(
        f"""
        SELECT de.id AS event_id, de.event_type, de.required_scope,
               de.dialog_date AS event_dialog_date, de.legacy_case_id,
               c.id AS cycle_id, c.review_year, c.outlook_year,
               ea.person_number AS employee_pn, ea.assignment_number,
               ea.org_unit, p.first_name, p.last_name,
               dc.status AS case_status, dc.dialog_date AS case_dialog_date,
               dc.overall_rating_code, dc.data_json,
               (SELECT od.data_block_json FROM official_documents od
                WHERE od.dialog_event_id = de.id AND od.document_kind = 'review'
                  AND od.is_current = 1
                ORDER BY CASE od.variant WHEN 'digital' THEN 0 ELSE 1 END, od.id DESC
                LIMIT 1) AS review_document_data,
               (SELECT od.data_block_json FROM official_documents od
                WHERE od.dialog_event_id = de.id AND od.document_kind = 'outlook'
                  AND od.is_current = 1
                ORDER BY CASE od.variant WHEN 'digital' THEN 0 ELSE 1 END, od.id DESC
                LIMIT 1) AS outlook_document_data
        FROM dialog_events de
        LEFT JOIN cycles c ON c.id = de.cycle_id
        JOIN employment_assignments ea ON ea.id = de.employment_id
        JOIN persons p ON p.person_number = ea.person_number
        LEFT JOIN dialog_cases dc ON dc.case_id = de.legacy_case_id
        WHERE {' AND '.join(where)}
        ORDER BY c.review_year DESC, ea.org_unit, p.last_name, p.first_name
        """,
        params,
    ).fetchall()


def _valid_date(value: Any) -> str:
    try:
        return date.fromisoformat(str(value or "")).isoformat()
    except ValueError:
        return ""


def analytics_data(
    connection: sqlite3.Connection, *, cycle_id: int | None = None,
    org_unit: str = "", event_type: str = "", minimum_group_size: int = 5,
) -> dict[str, Any]:
    rows = _source_rows(
        connection, cycle_id=cycle_id, org_unit=org_unit, event_type=event_type
    )
    timings: list[dict[str, Any]] = []
    rating_cases: dict[str, str] = {}
    competency_cases: dict[str, tuple[set[str], set[str]]] = {}
    for row in rows:
        payload = _json(row["data_json"])
        review_doc = _json(row["review_document_data"])
        outlook_doc = _json(row["outlook_document_data"])
        review = payload.get("review") if isinstance(payload.get("review"), dict) else {}
        outlook = payload.get("outlook") if isinstance(payload.get("outlook"), dict) else {}
        case_key = row["legacy_case_id"] or f"event-{row['event_id']}"

        parts: list[tuple[str, str]] = []
        if row["event_type"] == "location_meeting":
            parts.append(("Standortgespräch", row["event_dialog_date"]))
        else:
            if row["required_scope"] in {"full", "review_only"}:
                parts.append(("Rückblick", row["case_dialog_date"] or review.get("dialog_date") or review_doc.get("dialog_date")))
            if row["required_scope"] in {"full", "outlook_only"}:
                parts.append(("Ausblick", outlook.get("dialog_date") or outlook_doc.get("dialog_date") or row["event_dialog_date"]))
        for part, raw_date in parts:
            dialog_date = _valid_date(raw_date)
            if not dialog_date:
                continue
            parsed = date.fromisoformat(dialog_date)
            iso = parsed.isocalendar()
            timings.append({
                "cycle": f"{row['review_year']}/{row['outlook_year']}" if row["cycle_id"] else str(row["review_year"]),
                "org_unit": row["org_unit"] or "–",
                "event_type": EVENT_TYPE_LABELS.get(row["event_type"], row["event_type"]),
                "dialog_part": part,
                "dialog_date": dialog_date,
                "calendar_week": f"{iso.year}-KW{iso.week:02d}",
                "month": parsed.strftime("%Y-%m"),
                "employee_name": f"{row['first_name']} {row['last_name']}".strip(),
                "employee_pn": row["employee_pn"],
                "assignment_number": row["assignment_number"],
            })

        rating = _rating(row["overall_rating_code"] or review.get("overall_rating") or review_doc.get("rating"))
        if rating and case_key not in rating_cases:
            rating_cases[case_key] = rating

        review_names = _names(review.get("competencies"))
        review_names.update(_names(payload.get("previous_development_goals")))
        review_names.update(_pipe_names(review_doc.get("review_competencies")))
        development_names = _names(outlook.get("development_goals"))
        development_names.update(_pipe_names(outlook_doc.get("development_competencies")))
        if review_names or development_names:
            competency_cases[case_key] = (review_names, development_names)

    group_size = len(rating_cases)
    ratings_suppressed = 0 < group_size < minimum_group_size
    rating_counts = Counter(rating_cases.values())
    ratings = [
        {
            "rating": rating,
            "count": None if ratings_suppressed else rating_counts.get(rating, 0),
            "percent": None if ratings_suppressed or not group_size else round(rating_counts.get(rating, 0) * 100 / group_size, 1),
        }
        for rating in "ABCDE"
    ]

    competency_group_size = len(competency_cases)
    competencies_suppressed = 0 < competency_group_size < minimum_group_size
    competency_counts: Counter[tuple[str, str]] = Counter()
    if not competencies_suppressed:
        for review_names, development_names in competency_cases.values():
            competency_counts.update((name, "Im Rückblick thematisiert") for name in review_names)
            competency_counts.update((name, "Als Entwicklungsziel vereinbart") for name in development_names)
    competencies = [
        {
            "competency": name, "usage": usage, "count": count,
            "percent": round(count * 100 / competency_group_size, 1) if competency_group_size else 0,
        }
        for (name, usage), count in sorted(
            competency_counts.items(), key=lambda item: (item[0][1], -item[1], item[0][0])
        )
    ]
    return {
        "timings": timings,
        "ratings": ratings,
        "rating_group_size": group_size,
        "ratings_suppressed": ratings_suppressed,
        "competencies": competencies,
        "competency_group_size": competency_group_size,
        "competencies_suppressed": competencies_suppressed,
        "minimum_group_size": minimum_group_size,
    }


def analytics_csv(report: str, data: dict[str, Any]) -> tuple[str, bytes]:
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    if report == "timings":
        headers = ["Durchlauf", "Organisationseinheit", "Dialogart", "Gesprächsteil", "Gesprächsdatum", "Kalenderwoche", "Monat", "Name", "Personalnummer", "Ans."]
        writer.writerow(headers)
        for row in data["timings"]:
            writer.writerow([row[key] for key in ("cycle", "org_unit", "event_type", "dialog_part", "dialog_date", "calendar_week", "month", "employee_name", "employee_pn", "assignment_number")])
        name = "MD_Gespraechszeitpunkte.csv"
    elif report == "ratings":
        writer.writerow(["Gesamtbeurteilung", "Anzahl", "Anteil Prozent", "Grundgesamtheit"])
        for row in data["ratings"]:
            writer.writerow([row["rating"], "unterdrückt" if row["count"] is None else row["count"], "" if row["percent"] is None else row["percent"], data["rating_group_size"] if not data["ratings_suppressed"] else "unterdrückt"])
        name = "MD_Gesamtbeurteilungen.csv"
    elif report == "competencies":
        writer.writerow(["Kompetenz", "Verwendung", "Anzahl Fälle", "Anteil Prozent"])
        if data["competencies_suppressed"]:
            writer.writerow(["Unterdrückt", f"Mindestgruppengrösse {data['minimum_group_size']} nicht erreicht", "", ""])
        for row in data["competencies"]:
            writer.writerow([row["competency"], row["usage"], row["count"], row["percent"]])
        name = "MD_Kompetenzen.csv"
    else:
        raise ValueError("Die gewählte Auswertung ist ungültig.")
    return name, output.getvalue().encode("utf-8-sig")
