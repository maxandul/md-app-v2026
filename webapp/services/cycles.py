"""Erzeugt Jahresprozesse und liefert Prozessübersichten."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime


CYCLE_STATUS_LABELS = {
    "vorbereitung": "Vorbereitung",
    "versand": "Versand",
    "ruecklauf": "Rücklauf und Verarbeitung",
    "abgeschlossen": "Abgeschlossen",
}

_CYCLE_STATUS_TRANSITIONS = {
    "vorbereitung": {"versand"},
    "versand": {"vorbereitung", "ruecklauf"},
    "ruecklauf": {"versand", "abgeschlossen"},
    "abgeschlossen": {"ruecklauf"},
}


def change_cycle_status(
    connection: sqlite3.Connection, *, cycle_id: int, new_status: str, closure_reason: str = "", closure_owner: str = "", external_checked: bool = False
) -> tuple[str, str]:
    """Ändert die steuernde Prozessphase kontrolliert um genau einen Schritt."""
    cycle = connection.execute(
        "SELECT status FROM cycles WHERE id = ?", (cycle_id,)
    ).fetchone()
    if not cycle:
        raise LookupError("Jahresprozess nicht gefunden.")
    old_status = cycle["status"]
    if new_status == old_status:
        return old_status, new_status
    if new_status not in _CYCLE_STATUS_TRANSITIONS.get(old_status, set()):
        raise ValueError(
            "Die Prozessphase kann nur um einen Schritt vor- oder zurückgesetzt werden."
        )
    if new_status == 'abgeschlossen':
        from .hr_workflow import closure_summary, stamp
        import json
        summary = closure_summary(connection,cycle_id)
        if not external_checked:
            raise ValueError('Bitte zuerst die Abschlussprüfung öffnen und die externe Dossier-/SAP-Verarbeitung prüfen.')
        if any(summary.values()) and (len(closure_reason.strip())<10 or not closure_owner.strip()):
            raise ValueError('Es bestehen offene Aufgaben. Bitte zuerst erledigen oder Restfälle mit Begründung und verantwortlicher Person dokumentieren.')
        connection.execute("""INSERT INTO workflow_cycle_closures(cycle_id,reason,owner,summary_json,created_at) VALUES (?,?,?,?,?)
            ON CONFLICT(cycle_id) DO UPDATE SET reason=excluded.reason,owner=excluded.owner,summary_json=excluded.summary_json,created_at=excluded.created_at""",(cycle_id,closure_reason.strip(),closure_owner.strip(),json.dumps(summary,ensure_ascii=False),stamp()))
    connection.execute(
        "UPDATE cycles SET status = ? WHERE id = ?", (new_status, cycle_id)
    )
    connection.commit()
    return old_status, new_status


def _suggest_scope(exit_date: str, probation_end: str, review_year: int) -> tuple[str, str]:
    if exit_date:
        parsed = date.fromisoformat(exit_date)
        if date(review_year, 10, 1) <= parsed <= date(review_year + 1, 1, 31):
            return (
                "review_only",
                f"Austritt am {parsed.strftime('%d.%m.%Y')}. "
                "Auf Wunsch des Mitarbeitenden kann auf den Rückblick verzichtet werden.",
            )
    if probation_end:
        parsed = date.fromisoformat(probation_end)
        if parsed.year == review_year and parsed < date(review_year, 6, 30):
            return "full", f"Probezeit endete am {parsed.strftime('%d.%m.%Y')}; regulärer Rückblick und Ausblick zum Jahresende."
        if date(review_year, 6, 30) <= parsed < date(review_year + 1, 3, 1):
            tense = "endete" if parsed.year == review_year else "endet"
            return "outlook_only", f"Probezeit {tense} am {parsed.strftime('%d.%m.%Y')}; im Jahresdialog ist nur der Ausblick auf das neue Jahr verpflichtend."
    return "full", "Standardfall gemäss SAP-Stammdaten."


def repair_probation_boundary(connection: sqlite3.Connection) -> int:
    """Korrigiert unbestätigte Jahresfälle am 30. Juni, ohne Rückläufe zu verändern."""
    rows = connection.execute("""SELECT dc.case_id,c.review_year,e.exit_date,e.probation_end,de.id AS event_id
        FROM dialog_cases dc JOIN cycles c ON c.id=dc.cycle_id
        JOIN employees e ON e.pn=dc.employee_pn
        JOIN dialog_events de ON de.legacy_case_id=dc.case_id
        WHERE c.status<>'abgeschlossen' AND dc.active=1 AND dc.official_scope=''
          AND dc.status='offen' AND COALESCE(dc.data_json,'') IN ('','{}')
          AND de.event_type='annual' AND de.source='rule'
          AND e.probation_end=printf('%04d-06-30',c.review_year)
          AND dc.suggestion_reason LIKE 'Probezeit %'
          AND NOT EXISTS (SELECT 1 FROM official_documents od WHERE od.case_id=dc.case_id)
          AND (dc.suggested_scope='full' OR de.required_scope='full' OR de.sap_leading=1
               OR EXISTS (SELECT 1 FROM document_obligations o WHERE o.dialog_event_id=de.id AND o.document_kind='review' AND o.required=1))
        """).fetchall()
    changed=0
    for row in rows:
        from webapp.migrations import available
        if available(connection) and connection.execute('''SELECT 1 FROM hr_part_responsibilities p
            JOIN document_obligations o ON o.id=p.obligation_id WHERE o.dialog_event_id=?''',(row['event_id'],)).fetchone():
            continue
        scope,reason=_suggest_scope(row['exit_date'],row['probation_end'],row['review_year'])
        if scope != 'outlook_only':
            continue
        connection.execute('UPDATE dialog_cases SET suggested_scope=?,suggestion_reason=? WHERE case_id=?',(scope,reason,row['case_id']))
        connection.execute('UPDATE dialog_events SET required_scope=?,source_reason=?,sap_leading=0 WHERE id=?',(scope,reason,row['event_id']))
        connection.execute("UPDATE document_obligations SET required=0,status='waived' WHERE dialog_event_id=? AND document_kind='review' AND status IN ('open','waived')",(row['event_id'],))
        changed+=1
    connection.commit()
    return changed


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
        JOIN employees manager ON manager.pn = rl.manager_pn AND manager.active = 1
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


def synchronize_cycle_with_import(
    connection: sqlite3.Connection,
    *,
    cycle_id: int,
    sap_import_id: int,
    updated_at: datetime | None = None,
) -> dict[str, int]:
    """Gleicht einen offenen Durchlauf mit einem neueren vollständigen SAP-Import ab."""
    cycle = connection.execute(
        "SELECT * FROM cycles WHERE id = ?", (cycle_id,)
    ).fetchone()
    if not cycle:
        raise LookupError("Jahresprozess nicht gefunden.")
    if cycle["status"] == "abgeschlossen":
        return {"added": 0, "reactivated": 0, "deactivated": 0}
    imported = connection.execute(
        "SELECT id FROM sap_imports WHERE id = ?", (sap_import_id,)
    ).fetchone()
    if not imported:
        raise ValueError("Der SAP-Import existiert nicht.")
    timestamp = (updated_at or datetime.now().astimezone()).isoformat(timespec="seconds")
    existing_rows = connection.execute(
        "SELECT * FROM dialog_cases WHERE cycle_id = ?", (cycle_id,)
    ).fetchall()
    existing = {
        (row["employee_pn"], row["employment_assignment"], row["manager_pn"]): row
        for row in existing_rows
    }
    # Preserve explicit A/B part decisions; general SAP staging follows in stage D.
    from webapp.migrations import available
    protected = {}
    if available(connection):
        protected = {r['case_id']: r for r in connection.execute('''SELECT DISTINCT dc.*
            FROM dialog_cases dc JOIN dialog_events e ON e.legacy_case_id=dc.case_id
            JOIN document_obligations o ON o.dialog_event_id=e.id
            JOIN hr_part_responsibilities p ON p.obligation_id=o.id WHERE dc.cycle_id=?''',(cycle_id,))}
    protected_employments = {(r['employee_pn'],r['employment_assignment']) for r in protected.values()}
    lines = connection.execute(
        """
        SELECT rl.employee_pn, rl.manager_pn,
               COALESCE(NULLIF(rl.employment_assignment, ''), NULLIF(e.employment_assignment, ''), '1') AS employment_assignment,
               e.exit_date, e.probation_end
        FROM reporting_lines rl
        JOIN employees e ON e.pn = rl.employee_pn
        JOIN employees manager ON manager.pn = rl.manager_pn AND manager.active = 1
        WHERE rl.sap_import_id = ? AND e.active = 1
        ORDER BY rl.manager_pn, e.last_name, e.first_name, e.pn
        """,
        (sap_import_id,),
    ).fetchall()
    line_counts: dict[tuple[str, str], int] = {}
    for line in lines:
        key = (line["employee_pn"], line["manager_pn"])
        line_counts[key] = line_counts.get(key, 0) + 1

    connection.execute(
        """
        UPDATE dialog_cases SET active = 0, updated_at = ?
        WHERE cycle_id = ? AND NOT EXISTS (
            SELECT 1 FROM dialog_events de
            WHERE de.legacy_case_id = dialog_cases.case_id AND de.source = 'manual'
        )
        """,
        (timestamp, cycle_id),
    )
    added = 0
    reactivated = 0
    for row in protected.values():
        connection.execute('UPDATE dialog_cases SET active=?,updated_at=? WHERE id=?',(row['active'],row['updated_at'],row['id']))
    for line in lines:
        if (line['employee_pn'],line['employment_assignment']) in protected_employments:
            continue
        key = (line["employee_pn"], line["employment_assignment"], line["manager_pn"])
        scope, reason = _suggest_scope(line["exit_date"], line["probation_end"], cycle["review_year"])
        if key in existing:
            if not existing[key]["active"]:
                reactivated += 1
            connection.execute(
                """
                UPDATE dialog_cases
                SET active = 1, suggested_scope = ?, suggestion_reason = ?, updated_at = ?
                WHERE id = ?
                """,
                (scope, reason, timestamp, existing[key]["id"]),
            )
            continue
        case_id = f"{cycle['review_year']}-{line['manager_pn']}-{line['employee_pn']}"
        if line_counts[(line["employee_pn"], line["manager_pn"])] > 1:
            case_id += f"-{line['employment_assignment']}"
        base_case_id = case_id
        suffix = 2
        while connection.execute(
            "SELECT 1 FROM dialog_cases WHERE case_id = ?", (case_id,)
        ).fetchone():
            case_id = f"{base_case_id}-{suffix}"
            suffix += 1
        connection.execute(
            """
            INSERT INTO dialog_cases (
                case_id, cycle_id, employee_pn, employment_assignment, manager_pn,
                suggested_scope, suggestion_reason, status, data_json, active, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'offen', '', 1, ?)
            """,
            (
                case_id, cycle_id, line["employee_pn"], line["employment_assignment"],
                line["manager_pn"], scope, reason, timestamp,
            ),
        )
        added += 1
    active_keys = {
        (line["employee_pn"], line["employment_assignment"], line["manager_pn"])
        for line in lines
    }
    manual_case_ids = {
        row["legacy_case_id"]
        for row in connection.execute(
            """
            SELECT legacy_case_id FROM dialog_events
            WHERE cycle_id = ? AND source = 'manual' AND legacy_case_id IS NOT NULL
            """,
            (cycle_id,),
        ).fetchall()
    }
    deactivated = sum(
        1 for key, row in existing.items()
        if row["active"] and key not in active_keys and row["case_id"] not in manual_case_ids and row['case_id'] not in protected
    )
    connection.execute(
        "UPDATE cycles SET sap_import_id = ? WHERE id = ?", (sap_import_id, cycle_id)
    )
    connection.execute(
        """
        UPDATE dialog_events
        SET status = 'cancelled', updated_at = ?
        WHERE cycle_id = ? AND legacy_case_id IN (
            SELECT case_id FROM dialog_cases WHERE cycle_id = ? AND active = 0
        )
        """,
        (timestamp, cycle_id, cycle_id),
    )
    connection.commit()
    from .dialog_events import sync_cycle_events

    sync_cycle_events(connection, cycle_id)
    repair_probation_boundary(connection)
    return {"added": added, "reactivated": reactivated, "deactivated": deactivated}


def synchronize_open_cycles(
    connection: sqlite3.Connection, *, sap_import_id: int
) -> dict[str, int]:
    totals = {"cycles": 0, "added": 0, "reactivated": 0, "deactivated": 0}
    cycles = connection.execute(
        "SELECT id FROM cycles WHERE status <> 'abgeschlossen' ORDER BY id"
    ).fetchall()
    for cycle in cycles:
        result = synchronize_cycle_with_import(
            connection, cycle_id=cycle["id"], sap_import_id=sap_import_id
        )
        totals["cycles"] += 1
        for key in ("added", "reactivated", "deactivated"):
            totals[key] += result[key]
    return totals


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
        LEFT JOIN dialog_cases dc ON dc.cycle_id = c.id AND dc.active = 1
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
    from webapp.migrations import available
    if available(connection):
        from .part_queries import managers
        return cycle,managers(connection,cycle_id)
    managers = connection.execute(
        """
        WITH case_summary AS (
            SELECT manager_pn,
                   COUNT(*) AS case_count,
                   SUM(CASE WHEN status IN ('vollstaendig', 'kein_md') THEN 1 ELSE 0 END) AS done_count,
                   SUM(CASE WHEN status = 'in_bearbeitung' THEN 1 ELSE 0 END) AS progress_count
            FROM dialog_cases
            WHERE cycle_id = ? AND active = 1
            GROUP BY manager_pn
        ), manager_scope AS (
            SELECT manager_pn FROM case_summary
            UNION
            SELECT DISTINCT manager_pn FROM package_events
            WHERE cycle_id = ? AND direction = 'versand'
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
        SELECT ms.manager_pn,
               COALESCE(NULLIF(TRIM(m.first_name || ' ' || m.last_name), ''), 'VG ' || ms.manager_pn) AS manager_name,
               m.email AS manager_email,
               COALESCE(cs.case_count, 0) AS case_count,
               COALESCE(cs.done_count, 0) AS done_count,
               COALESCE(cs.progress_count, 0) AS progress_count,
               es.sent_at, COALESCE(ds.pdf_received_at, es.returned_at) AS returned_at,
               COALESCE(ds.signature_check_count, 0) AS signature_check_count,
               COALESCE(ds.scan_pending_count, 0) AS scan_pending_count
        FROM manager_scope ms
        LEFT JOIN case_summary cs ON cs.manager_pn = ms.manager_pn
        LEFT JOIN employees m ON m.pn = ms.manager_pn
        LEFT JOIN event_summary es ON es.manager_pn = ms.manager_pn
        LEFT JOIN document_summary ds ON ds.manager_pn = ms.manager_pn
        ORDER BY manager_name, cs.manager_pn
        """,
        (cycle_id, cycle_id, cycle_id, cycle_id),
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
