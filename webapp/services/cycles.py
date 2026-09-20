"""Erzeugt Jahresprozesse und liefert Prozessübersichten."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime


def _suggest_scope(exit_date: str, probation_end: str, review_year: int) -> tuple[str, str]:
    if exit_date:
        parsed = date.fromisoformat(exit_date)
        if date(review_year, 10, 1) <= parsed <= date(review_year + 1, 1, 31):
            return "review_only", f"Austritt am {parsed.strftime('%d.%m.%Y')}."
    if probation_end:
        parsed = date.fromisoformat(probation_end)
        if parsed.year == review_year and parsed <= date(review_year, 6, 30):
            return "full", f"Probezeit endete am {parsed.strftime('%d.%m.%Y')}; regulärer Rückblick und Ausblick zum Jahresende."
        if date(review_year, 7, 1) <= parsed < date(review_year + 1, 3, 1):
            tense = "endete" if parsed.year == review_year else "endet"
            return "outlook_only", f"Probezeit {tense} am {parsed.strftime('%d.%m.%Y')}; im Jahresdialog ist nur der Ausblick auf das neue Jahr verpflichtend."
    return "full", "Standardfall gemäss SAP-Stammdaten."


def create_cycle(
    connection: sqlite3.Connection,
    *,
    review_year: int,
    sap_import_id: int,
    created_at: datetime | None = None,
    review_due_date: str = "",
    outlook_due_date: str = "",
) -> int:
    if review_year < 2020 or review_year > 2100:
        raise ValueError("Das Rückblickjahr liegt ausserhalb des unterstützten Bereichs.")
    sap_import = connection.execute(
        "SELECT id FROM sap_imports WHERE id = ?", (sap_import_id,)
    ).fetchone()
    if not sap_import:
        raise ValueError("Der gewählte SAP-Import existiert nicht.")

    timestamp = (created_at or datetime.now().astimezone()).isoformat(timespec="seconds")
    from .dialog_events import default_due_dates

    default_review_due, default_outlook_due = default_due_dates(review_year)
    review_due_date = review_due_date or default_review_due
    outlook_due_date = outlook_due_date or default_outlook_due
    try:
        cursor = connection.execute(
            """
            INSERT INTO cycles (
                review_year, outlook_year, sap_import_id, review_due_date,
                outlook_due_date, status, created_at
            ) VALUES (?, ?, ?, ?, ?, 'vorbereitung', ?)
            """,
            (
                review_year, review_year + 1, sap_import_id, review_due_date,
                outlook_due_date, timestamp,
            ),
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"Der Jahresprozess {review_year}/{review_year + 1} existiert bereits.") from exc
    cycle_id = int(cursor.lastrowid)

    lines = connection.execute(
        """
        SELECT rl.employee_pn, rl.manager_pn,
               COALESCE(NULLIF(rl.employment_assignment, ''), NULLIF(e.employment_assignment, ''), '1') AS employment_assignment,
               e.exit_date, e.probation_end
        FROM reporting_lines rl
        JOIN employees e ON e.pn = rl.employee_pn
        WHERE rl.sap_import_id = ?
        ORDER BY rl.manager_pn, e.last_name, e.first_name, e.pn
        """,
        (sap_import_id,),
    ).fetchall()
    line_counts: dict[tuple[str, str], int] = {}
    for line in lines:
        key = (line["employee_pn"], line["manager_pn"])
        line_counts[key] = line_counts.get(key, 0) + 1
    for line in lines:
        scope, reason = _suggest_scope(line["exit_date"], line["probation_end"], review_year)
        case_id = f"{review_year}-{line['manager_pn']}-{line['employee_pn']}"
        if line_counts[(line["employee_pn"], line["manager_pn"])] > 1:
            case_id += f"-{line['employment_assignment']}"
        connection.execute(
            """
            INSERT INTO dialog_cases (
                case_id, cycle_id, employee_pn, employment_assignment, manager_pn,
                suggested_scope, suggestion_reason, status, data_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'offen', '', ?)
            """,
            (
                case_id, cycle_id, line["employee_pn"], line["employment_assignment"],
                line["manager_pn"], scope, reason, timestamp,
            ),
        )
    connection.commit()
    from .dialog_events import sync_cycle_events

    sync_cycle_events(connection, cycle_id)
    return cycle_id


def dashboard_data(connection: sqlite3.Connection) -> dict:
    imports = connection.execute(
        """
        SELECT si.*,
               SUM(CASE WHEN sii.severity = 'blocking' AND sii.status = 'open' THEN 1 ELSE 0 END) AS blocking_issue_count,
               SUM(CASE WHEN sii.severity = 'warning' AND sii.status = 'open' THEN 1 ELSE 0 END) AS open_warning_count,
               COUNT(sii.id) AS issue_count
        FROM sap_imports si
        LEFT JOIN sap_import_issues sii ON sii.sap_import_id = si.id
        GROUP BY si.id
        ORDER BY si.imported_at DESC, si.id DESC
        """
    ).fetchall()
    cycles = connection.execute(
        """
        SELECT c.*,
               COUNT(dc.id) AS case_count,
               COUNT(DISTINCT dc.manager_pn) AS manager_count,
               SUM(CASE WHEN dc.status IN ('vollstaendig', 'kein_md') THEN 1 ELSE 0 END) AS done_count
        FROM cycles c
        LEFT JOIN dialog_cases dc ON dc.cycle_id = c.id
        GROUP BY c.id
        ORDER BY c.review_year DESC
        """
    ).fetchall()
    return {"imports": imports, "cycles": cycles}


def cycle_overview(connection: sqlite3.Connection, cycle_id: int) -> tuple[sqlite3.Row, list]:
    cycle = connection.execute(
        """
        SELECT c.*, si.original_filename, si.imported_at
        FROM cycles c JOIN sap_imports si ON si.id = c.sap_import_id
        WHERE c.id = ?
        """,
        (cycle_id,),
    ).fetchone()
    if not cycle:
        raise LookupError("Jahresprozess nicht gefunden.")
    managers = connection.execute(
        """
        WITH case_summary AS (
            SELECT manager_pn,
                   COUNT(*) AS case_count,
                   SUM(CASE WHEN status IN ('vollstaendig', 'kein_md') THEN 1 ELSE 0 END) AS done_count,
                   SUM(CASE WHEN status = 'in_bearbeitung' THEN 1 ELSE 0 END) AS progress_count
            FROM dialog_cases
            WHERE cycle_id = ?
            GROUP BY manager_pn
        ), event_summary AS (
            SELECT manager_pn,
                   MAX(CASE WHEN direction = 'versand' THEN created_at END) AS sent_at,
                   MAX(CASE WHEN direction = 'ruecklauf' THEN created_at END) AS returned_at
            FROM package_events
            WHERE cycle_id = ?
            GROUP BY manager_pn
        ), document_summary AS (
            SELECT od.manager_pn,
                   MAX(od.received_at) AS pdf_received_at,
                   SUM(CASE
                       WHEN od.variant = 'digital' AND od.is_current = 1
                        AND od.signature_checked = 0 THEN 1 ELSE 0 END
                   ) AS signature_check_count,
                   SUM(CASE
                       WHEN od.variant = 'digital' AND od.is_current = 1
                        AND od.scan_required = 1 AND od.signature_checked = 1
                        AND NOT EXISTS (
                            SELECT 1 FROM official_documents scan
                            WHERE scan.case_id = od.case_id
                              AND scan.document_kind = od.document_kind
                              AND scan.variant = 'scan' AND scan.is_current = 1
                        ) THEN 1 ELSE 0 END
                   ) AS scan_pending_count
            FROM official_documents od
            WHERE od.cycle_id = ?
            GROUP BY od.manager_pn
        )
        SELECT cs.manager_pn,
               COALESCE(NULLIF(TRIM(m.first_name || ' ' || m.last_name), ''), 'VG ' || cs.manager_pn) AS manager_name,
               m.email AS manager_email,
               cs.case_count, cs.done_count, cs.progress_count,
               es.sent_at, COALESCE(ds.pdf_received_at, es.returned_at) AS returned_at,
               COALESCE(ds.signature_check_count, 0) AS signature_check_count,
               COALESCE(ds.scan_pending_count, 0) AS scan_pending_count
        FROM case_summary cs
        LEFT JOIN employees m ON m.pn = cs.manager_pn
        LEFT JOIN event_summary es ON es.manager_pn = cs.manager_pn
        LEFT JOIN document_summary ds ON ds.manager_pn = cs.manager_pn
        ORDER BY manager_name, cs.manager_pn
        """,
        (cycle_id, cycle_id, cycle_id),
    ).fetchall()
    return cycle, managers


def manager_case_overview(
    connection: sqlite3.Connection, cycle_id: int, manager_pn: str
) -> tuple[sqlite3.Row, dict, list, list]:
    cycle, managers = cycle_overview(connection, cycle_id)
    manager_row = next((row for row in managers if row["manager_pn"] == manager_pn), None)
    if manager_row is None:
        raise LookupError("Führungslinie nicht gefunden.")
    manager = dict(manager_row)
    from .documents import case_document_overview

    cases = case_document_overview(
        connection, cycle_id=cycle_id, manager_pn=manager_pn
    )
    events = connection.execute(
        """
        SELECT direction, revision, filename, created_at, sha256
        FROM package_events
        WHERE cycle_id = ? AND manager_pn = ?
        ORDER BY id DESC
        """,
        (cycle_id, manager_pn),
    ).fetchall()
    return cycle, manager, cases, events
