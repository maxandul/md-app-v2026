"""Gemeinsame Dateinamen, Bewilligungen und Zeiträume für Word und SAP."""
from __future__ import annotations
import re
import sqlite3
import unicodedata
from datetime import date
from typing import Any


def _filename_part(value: Any) -> str:
    ascii_value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9_-]+", "_", ascii_value).strip("_") or "Unbekannt"


def _permission_date_text(value) -> str:
    text = str(value or '').strip()
    try:
        return date.fromisoformat(text[:10]).strftime('%d.%m.%Y')
    except ValueError:
        return text


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
                _permission_date_text(row["valid_from"]),
                _permission_date_text(row["valid_to"]),
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
