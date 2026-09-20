"""Begründete Fristverlängerungen für Dokumentpflichten."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Any


DOCUMENT_KINDS = {"review": "Rückblick", "outlook": "Ausblick"}
SCOPES = {"cycle", "manager", "case"}


def _valid_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError) as exc:
        raise ValueError("Bitte gib eine gültige neue Frist ein.") from exc


def extend_deadlines(
    connection: sqlite3.Connection,
    *,
    cycle_id: int,
    scope: str,
    document_kind: str,
    new_due_date: str,
    reason: str,
    user_id: int | None = None,
    manager_pn: str = "",
    case_id: str = "",
    changed_at: datetime | None = None,
) -> dict[str, Any]:
    """Verlängert offene Fristen und schreibt je Pflicht eine unveränderliche Spur."""
    if scope not in SCOPES:
        raise ValueError("Der Geltungsbereich der Fristverlängerung ist ungültig.")
    if document_kind not in DOCUMENT_KINDS:
        raise ValueError("Die Dokumentart ist ungültig.")
    reason = reason.strip()
    if len(reason) < 10:
        raise ValueError("Die Begründung muss mindestens 10 Zeichen umfassen.")
    new_due_date = _valid_date(new_due_date)

    where = [
        "de.cycle_id = ?", "o.document_kind = ?", "o.required = 1",
        "o.status NOT IN ('complete', 'waived')",
    ]
    params: list[Any] = [cycle_id, document_kind]
    if scope == "manager":
        if not manager_pn:
            raise ValueError("Die Personalnummer der vorgesetzten Person fehlt.")
        where.append("ma.manager_person_number = ?")
        params.append(manager_pn)
    elif scope == "case":
        if not case_id:
            raise ValueError("Die Fall-ID fehlt.")
        where.append("de.legacy_case_id = ?")
        params.append(case_id)

    rows = connection.execute(
        f"""
        SELECT o.id, o.due_date, ma.manager_person_number AS manager_pn
        FROM document_obligations o
        JOIN dialog_events de ON de.id = o.dialog_event_id
        JOIN manager_assignments ma ON ma.id = de.manager_assignment_id
        WHERE {' AND '.join(where)}
        ORDER BY o.id
        """,
        params,
    ).fetchall()
    if not rows:
        raise ValueError("Für diese Auswahl gibt es keine offene Dokumentpflicht.")
    if any(row["due_date"] and new_due_date <= row["due_date"] for row in rows):
        raise ValueError("Die neue Frist muss nach allen bisherigen Fristen liegen.")

    timestamp = (changed_at or datetime.now().astimezone()).isoformat(timespec="seconds")
    try:
        for row in rows:
            connection.execute(
                "UPDATE document_obligations SET due_date = ?, updated_at = ? WHERE id = ?",
                (new_due_date, timestamp, row["id"]),
            )
            connection.execute(
                """
                INSERT INTO deadline_changes (
                    cycle_id, obligation_id, manager_pn, scope, document_kind,
                    old_due_date, new_due_date, reason, user_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cycle_id, row["id"], row["manager_pn"], scope, document_kind,
                    row["due_date"], new_due_date, reason, user_id, timestamp,
                ),
            )
        if scope == "cycle":
            column = "review_due_date" if document_kind == "review" else "outlook_due_date"
            connection.execute(
                f"UPDATE cycles SET {column} = ? WHERE id = ?",
                (new_due_date, cycle_id),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return {
        "changed": len(rows),
        "scope": scope,
        "document_kind": document_kind,
        "new_due_date": new_due_date,
        "reason": reason,
    }
