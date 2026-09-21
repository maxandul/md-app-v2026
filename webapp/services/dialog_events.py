"""Fachliches Modell für Führungslinien, Dialogereignisse und Dokumentpflichten."""

from __future__ import annotations

import sqlite3
import uuid
from collections import Counter
from datetime import date, datetime


EVENT_TYPE_LABELS = {
    "annual": "Regulärer Mitarbeitenden-Dialog",
    "probation_review": "Rückblick Probezeit",
    "probation_outlook": "Ausblick Probezeit",
    "interim": "Unterjähriger Mitarbeitenden-Dialog",
    "transfer_review": "Abschluss bei Übertritt",
    "departure_review": "Abschluss bei Austritt/Pensionierung",
    "location_meeting": "Standortgespräch",
}

SCOPE_LABELS = {
    "full": "Rückblick und Ausblick",
    "review_only": "Nur Rückblick",
    "outlook_only": "Nur Ausblick",
    "none": "Kein Pflichtgespräch",
}


def default_due_dates(review_year: int) -> tuple[str, str]:
    outlook_year = review_year + 1
    return date(outlook_year, 1, 31).isoformat(), date(outlook_year, 2, 28).isoformat()


def _bounded_period(review_year: int, entry_date: str, exit_date: str) -> tuple[str, str]:
    start = date(review_year, 1, 1)
    end = date(review_year, 12, 31)
    if entry_date:
        start = max(start, date.fromisoformat(entry_date))
    if exit_date:
        end = min(end, date.fromisoformat(exit_date))
    return start.isoformat(), end.isoformat()


def ensure_manager_assignment(
    connection: sqlite3.Connection,
    *,
    employee_pn: str,
    assignment_number: str,
    manager_pn: str,
    source: str,
    sap_import_id: int | None,
    reason: str = "",
    created_at: str,
) -> tuple[int, int]:
    employment = connection.execute(
        """
        SELECT id, entry_date, exit_date
        FROM employment_assignments
        WHERE person_number = ? AND assignment_number = ?
        """,
        (employee_pn, assignment_number),
    ).fetchone()
    if not employment:
        raise ValueError(
            f"Für PN {employee_pn} und Ans. {assignment_number or '–'} fehlt die Anstellung."
        )

    if source == "sap":
        existing = connection.execute(
            """
            SELECT id FROM manager_assignments
            WHERE employment_id = ? AND manager_person_number = ?
              AND source = 'sap' AND sap_import_id = ?
            """,
            (employment["id"], manager_pn, sap_import_id),
        ).fetchone()
    else:
        existing = None
    if existing:
        return int(employment["id"]), int(existing["id"])

    cursor = connection.execute(
        """
        INSERT INTO manager_assignments (
            employment_id, manager_person_number, source, sap_import_id,
            valid_from, valid_to, active, reason, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
        """,
        (
            employment["id"], manager_pn, source, sap_import_id,
            employment["entry_date"], employment["exit_date"], reason,
            created_at, created_at,
        ),
    )
    return int(employment["id"]), int(cursor.lastrowid)


def _ensure_obligations(
    connection: sqlite3.Connection,
    *,
    event_db_id: int,
    event_id: str,
    scope: str,
    review_due_date: str,
    outlook_due_date: str,
    created_at: str,
) -> None:
    expected: list[tuple[str, str]] = []
    if scope in {"full", "review_only"}:
        expected.append(("review", review_due_date))
    if scope in {"full", "outlook_only"}:
        expected.append(("outlook", outlook_due_date))
    if scope == "none":
        expected.append(("no_md", review_due_date))
    for document_kind, due_date in expected:
        connection.execute(
            """
            INSERT OR IGNORE INTO document_obligations (
                obligation_id, dialog_event_id, document_kind, required,
                due_date, status, created_at, updated_at
            ) VALUES (?, ?, ?, 1, ?, 'open', ?, ?)
            """,
            (
                f"{event_id}-{document_kind}", event_db_id, document_kind,
                due_date, created_at, created_at,
            ),
        )


def sync_cycle_events(connection: sqlite3.Connection, cycle_id: int) -> int:
    """Spiegelt bestehende Jahresfälle idempotent ins neue Ereignismodell."""
    cycle = connection.execute("SELECT * FROM cycles WHERE id = ?", (cycle_id,)).fetchone()
    if not cycle:
        raise LookupError("Jahresprozess nicht gefunden.")
    review_due, outlook_due = default_due_dates(cycle["review_year"])
    review_due = cycle["review_due_date"] or review_due
    outlook_due = cycle["outlook_due_date"] or outlook_due
    connection.execute(
        """
        UPDATE cycles SET review_due_date = ?, outlook_due_date = ? WHERE id = ?
        """,
        (review_due, outlook_due, cycle_id),
    )

    rows = connection.execute(
        """
        SELECT dc.*,
               COALESCE(NULLIF(dc.employment_assignment, ''), NULLIF(e.employment_assignment, ''), '1') AS resolved_assignment,
               e.entry_date, e.exit_date
        FROM dialog_cases dc
        JOIN employees e ON e.pn = dc.employee_pn
        WHERE dc.cycle_id = ? AND dc.active = 1
        ORDER BY dc.id
        """,
        (cycle_id,),
    ).fetchall()
    review_counts = Counter(
        (row["employee_pn"], row["resolved_assignment"])
        for row in rows if row["suggested_scope"] in {"full", "review_only"}
    )
    created = 0
    for row in rows:
        timestamp = row["updated_at"] or cycle["created_at"]
        employment_id, manager_assignment_id = ensure_manager_assignment(
            connection,
            employee_pn=row["employee_pn"],
            assignment_number=row["resolved_assignment"],
            manager_pn=row["manager_pn"],
            source="sap",
            sap_import_id=cycle["sap_import_id"],
            reason="Aus dem SAP-Datenstand des Durchlaufs",
            created_at=timestamp,
        )
        period_start, period_end = (
            (row["period_start"], row["period_end"])
            if row["period_start"] and row["period_end"]
            else _bounded_period(cycle["review_year"], row["entry_date"], row["exit_date"])
        )
        event_id = f"{row['case_id']}-annual"
        status = {
            "offen": "open",
            "in_bearbeitung": "in_progress",
            "vollstaendig": "completed",
            "kein_md": "no_md",
        }.get(row["status"], "planned")
        leading = int(
            row["suggested_scope"] in {"full", "review_only"}
            and review_counts[(row["employee_pn"], row["resolved_assignment"])] == 1
        )
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO dialog_events (
                event_id, cycle_id, legacy_case_id, employment_id,
                manager_assignment_id, review_year, event_type, source,
                source_reason, required_scope, period_start, period_end,
                status, sap_leading, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'annual', 'rule', ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id, cycle_id, row["case_id"], employment_id,
                manager_assignment_id, cycle["review_year"], row["suggestion_reason"],
                row["suggested_scope"], period_start, period_end, status, leading,
                timestamp, timestamp,
            ),
        )
        event = connection.execute(
            "SELECT id FROM dialog_events WHERE event_id = ?", (event_id,)
        ).fetchone()
        if not cursor.rowcount:
            connection.execute(
                """
                UPDATE dialog_events
                SET manager_assignment_id = ?, required_scope = ?, period_start = ?,
                    period_end = ?, status = ?, source_reason = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    manager_assignment_id, row["suggested_scope"], period_start,
                    period_end, status, row["suggestion_reason"], timestamp,
                    event["id"],
                ),
            )
        if cursor.rowcount:
            created += 1
        _ensure_obligations(
            connection,
            event_db_id=event["id"],
            event_id=event_id,
            scope=row["suggested_scope"],
            review_due_date=review_due,
            outlook_due_date=outlook_due,
            created_at=timestamp,
        )
    connection.commit()
    return created


def backfill_dialog_model(connection: sqlite3.Connection) -> None:
    cycle_ids = connection.execute("SELECT id FROM cycles ORDER BY id").fetchall()
    for cycle in cycle_ids:
        sync_cycle_events(connection, cycle["id"])
    documents = connection.execute(
        """
        SELECT od.*, de.id AS event_db_id, de.event_id
        FROM official_documents od
        JOIN dialog_events de ON de.legacy_case_id = od.case_id
        WHERE od.is_current = 1
        ORDER BY CASE od.variant WHEN 'digital' THEN 1 WHEN 'administrative' THEN 2 ELSE 3 END,
                 od.id
        """
    ).fetchall()
    for document in documents:
        if document["document_kind"] == "no_md":
            connection.execute(
                """
                UPDATE document_obligations SET status = 'waived'
                WHERE dialog_event_id = ? AND document_kind IN ('review', 'outlook')
                """,
                (document["event_db_id"],),
            )
        obligation = connection.execute(
            """
            SELECT id FROM document_obligations
            WHERE dialog_event_id = ? AND document_kind = ?
            """,
            (document["event_db_id"], document["document_kind"]),
        ).fetchone()
        if not obligation:
            cursor = connection.execute(
                """
                INSERT INTO document_obligations (
                    obligation_id, dialog_event_id, document_kind, required,
                    due_date, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, '', 'open', ?, ?)
                """,
                (
                    f"{document['event_id']}-{document['document_kind']}",
                    document["event_db_id"], document["document_kind"],
                    int(document["document_kind"] == "no_md"),
                    document["received_at"], document["received_at"],
                ),
            )
            obligation = {"id": int(cursor.lastrowid)}
        if document["variant"] in {"scan", "administrative"}:
            status = "complete"
        elif not document["signature_checked"]:
            status = "received"
        elif document["scan_required"] and document["handoff_status"] != "staged":
            status = "scan_pending"
        else:
            status = "complete"
        connection.execute(
            """
            UPDATE official_documents
            SET dialog_event_id = ?, document_obligation_id = ? WHERE id = ?
            """,
            (document["event_db_id"], obligation["id"], document["id"]),
        )
        connection.execute(
            """
            UPDATE document_obligations
            SET status = ?, fulfilled_document_id = ?, updated_at = ? WHERE id = ?
            """,
            (status, document["id"], document["received_at"], obligation["id"]),
        )
    connection.commit()


def create_manual_event(
    connection: sqlite3.Connection,
    *,
    employee_pn: str,
    assignment_number: str,
    manager_pn: str,
    event_type: str,
    required_scope: str,
    review_year: int,
    period_start: str,
    period_end: str,
    reason: str,
    dialog_date: str = "",
    review_due_date: str = "",
    outlook_due_date: str = "",
    cycle_id: int | None = None,
    created_at: datetime | None = None,
) -> str:
    if event_type not in EVENT_TYPE_LABELS:
        raise ValueError("Unbekannte Dialogart.")
    if required_scope not in SCOPE_LABELS:
        raise ValueError("Unbekannter Gesprächsumfang.")
    if not employee_pn.strip() or not assignment_number.strip() or not manager_pn.strip():
        raise ValueError("Personalnummer, Ans. und vorgesetzte Person sind erforderlich.")
    if not reason.strip():
        raise ValueError("Für eine manuelle Zuordnung ist eine Begründung erforderlich.")
    try:
        start = date.fromisoformat(period_start)
        end = date.fromisoformat(period_end)
    except ValueError as exc:
        raise ValueError("Beurteilungsbeginn und -ende müssen gültige Daten sein.") from exc
    if start > end:
        raise ValueError("Der Beurteilungsbeginn liegt nach dem Beurteilungsende.")
    if dialog_date:
        try:
            date.fromisoformat(dialog_date)
        except ValueError as exc:
            raise ValueError("Das Gesprächsdatum muss ein gültiges Datum sein.") from exc
    employment = connection.execute(
        """
        SELECT entry_date, exit_date FROM employment_assignments
        WHERE person_number = ? AND assignment_number = ?
        """,
        (employee_pn.strip(), assignment_number.strip()),
    ).fetchone()
    if not employment:
        raise ValueError(
            f"Für PN {employee_pn.strip()} und Ans. {assignment_number.strip()} fehlt die Anstellung."
        )
    if employment["entry_date"] and start < date.fromisoformat(employment["entry_date"]):
        raise ValueError("Der Beurteilungsbeginn liegt vor dem Eintritt in diese Anstellung.")
    if employment["exit_date"] and end > date.fromisoformat(employment["exit_date"]):
        raise ValueError("Das Beurteilungsende liegt nach dem Austritt aus dieser Anstellung.")
    if cycle_id is not None:
        cycle = connection.execute(
            "SELECT review_year FROM cycles WHERE id = ?", (cycle_id,)
        ).fetchone()
        if not cycle:
            raise ValueError("Der gewählte Durchlauf existiert nicht.")
        if cycle["review_year"] != review_year:
            raise ValueError("Rückblickjahr und gewählter Durchlauf stimmen nicht überein.")
    timestamp = (created_at or datetime.now().astimezone()).isoformat(timespec="seconds")
    employment_id, manager_assignment_id = ensure_manager_assignment(
        connection,
        employee_pn=employee_pn.strip(),
        assignment_number=assignment_number.strip(),
        manager_pn=manager_pn.strip(),
        source="manual",
        sap_import_id=None,
        reason=reason.strip(),
        created_at=timestamp,
    )
    event_id = f"MAN-{review_year}-{employee_pn.strip()}-{uuid.uuid4().hex[:8]}"
    legacy_case_id = None
    if cycle_id is not None:
        legacy_case_id = event_id
        try:
            connection.execute(
                """
                INSERT INTO dialog_cases (
                    case_id, cycle_id, employee_pn, employment_assignment, manager_pn,
                    suggested_scope, suggestion_reason, status, period_start,
                    period_end, data_json, active, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'offen', ?, ?, '', 1, ?)
                """,
                (
                    legacy_case_id, cycle_id, employee_pn.strip(),
                    assignment_number.strip(), manager_pn.strip(), required_scope,
                    reason.strip(), period_start, period_end, timestamp,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Für diese Person, Anstellung und Führungskraft besteht im Durchlauf "
                "bereits ein Arbeitsmappenfall."
            ) from exc
    if required_scope in {"full", "review_only"}:
        connection.execute(
            """
            UPDATE dialog_events SET sap_leading = 0, updated_at = ?
            WHERE employment_id = ? AND review_year = ? AND sap_leading = 1
            """,
            (timestamp, employment_id, review_year),
        )
    cursor = connection.execute(
        """
        INSERT INTO dialog_events (
            event_id, cycle_id, legacy_case_id, employment_id, manager_assignment_id, review_year,
            event_type, source, source_reason, required_scope, period_start,
            period_end, dialog_date, status, sap_leading, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'manual', ?, ?, ?, ?, ?, 'open', 0, ?, ?)
        """,
        (
            event_id, cycle_id, legacy_case_id, employment_id, manager_assignment_id, review_year,
            event_type, reason.strip(), required_scope, period_start, period_end, dialog_date,
            timestamp, timestamp,
        ),
    )
    default_review_due, default_outlook_due = default_due_dates(review_year)
    _ensure_obligations(
        connection,
        event_db_id=cursor.lastrowid,
        event_id=event_id,
        scope=required_scope,
        review_due_date=review_due_date or default_review_due,
        outlook_due_date=outlook_due_date or default_outlook_due,
        created_at=timestamp,
    )
    connection.commit()
    return event_id


def dialog_event_rows(connection: sqlite3.Connection, cycle_id: int | None = None) -> list[dict]:
    params: tuple = ()
    condition = ""
    if cycle_id is not None:
        condition = "WHERE de.cycle_id = ?"
        params = (cycle_id,)
    rows = connection.execute(
        f"""
        SELECT de.*, ea.person_number AS employee_pn, ea.assignment_number,
               p.first_name, p.last_name, ma.manager_person_number AS manager_pn,
               COALESCE(NULLIF(TRIM(mp.first_name || ' ' || mp.last_name), ''),
                        'VG ' || ma.manager_person_number) AS manager_name,
               SUM(CASE WHEN o.required = 1 THEN 1 ELSE 0 END) AS obligation_count,
               SUM(CASE WHEN o.required = 1 AND o.status IN ('complete', 'waived') THEN 1 ELSE 0 END) AS obligation_done_count,
               MIN(CASE WHEN o.required = 1 AND o.status NOT IN ('complete', 'waived') THEN o.due_date END) AS next_due_date,
               MAX(CASE WHEN o.required = 1 AND o.document_kind = 'review' THEN o.due_date END) AS review_due_date,
               MAX(CASE WHEN o.required = 1 AND o.document_kind = 'outlook' THEN o.due_date END) AS outlook_due_date
        FROM dialog_events de
        JOIN employment_assignments ea ON ea.id = de.employment_id
        JOIN persons p ON p.person_number = ea.person_number
        JOIN manager_assignments ma ON ma.id = de.manager_assignment_id
        LEFT JOIN persons mp ON mp.person_number = ma.manager_person_number
        LEFT JOIN document_obligations o ON o.dialog_event_id = de.id
        {condition}
        GROUP BY de.id
        ORDER BY de.review_year DESC, next_due_date, p.last_name, p.first_name
        """,
        params,
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["event_type_label"] = EVENT_TYPE_LABELS.get(item["event_type"], item["event_type"])
        item["scope_label"] = SCOPE_LABELS.get(item["required_scope"], item["required_scope"])
        result.append(item)
    return result


def set_leading_sap_event(connection: sqlite3.Connection, event_db_id: int) -> None:
    event = connection.execute(
        """
        SELECT id, employment_id, review_year, required_scope, legacy_case_id
        FROM dialog_events WHERE id = ?
        """,
        (event_db_id,),
    ).fetchone()
    if not event:
        raise ValueError("Das Dialogereignis wurde nicht gefunden.")
    if event["required_scope"] not in {"full", "review_only"}:
        raise ValueError("Nur ein Ereignis mit Rückblick kann für SAP führend sein.")
    if not event["legacy_case_id"]:
        raise ValueError(
            "Dieses Ereignis ist noch nicht mit einer verarbeitbaren Arbeitsmappe verknüpft."
        )
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    connection.execute(
        """
        UPDATE dialog_events SET sap_leading = 0, updated_at = ?
        WHERE employment_id = ? AND review_year = ?
        """,
        (timestamp, event["employment_id"], event["review_year"]),
    )
    connection.execute(
        "UPDATE dialog_events SET sap_leading = 1, updated_at = ? WHERE id = ?",
        (timestamp, event_db_id),
    )
    connection.commit()
