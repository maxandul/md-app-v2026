"""Aggregierte Daten fuer die operative HR-Uebersicht."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime

from .cycles import dashboard_data


CYCLE_STATUS_LABELS = {
    "vorbereitung": "Vorbereitung",
    "versand": "Versand",
    "ruecklauf": "Rücklauf",
    "abgeschlossen": "Abgeschlossen",
}


def _selected_cycle(cycles: list[sqlite3.Row], selected_cycle_id: int | None):
    if selected_cycle_id is not None:
        selected = next((row for row in cycles if row["id"] == selected_cycle_id), None)
        if selected is not None:
            return selected
    return next(
        (row for row in cycles if row["status"] != "abgeschlossen"),
        cycles[0] if cycles else None,
    )


def cockpit_overview(
    connection: sqlite3.Connection, *, selected_cycle_id: int | None = None
) -> dict:
    """Liefert nur heute bereits belastbar ableitbare Kennzahlen und Aufgaben."""
    base = dashboard_data(connection)
    cycles = [dict(row) for row in base["cycles"]]
    base["cycles"] = cycles
    selected_cycle = _selected_cycle(cycles, selected_cycle_id)
    latest_import = base["imports"][0] if base["imports"] else None

    metrics = {
        "workbooks_missing": 0,
        "cases_open": 0,
        "obligations_open": 0,
        "obligations_overdue": 0,
        "documents_to_check": 0,
        "scans_pending": 0,
        "dossier_ready": 0,
        "master_data_issues": 0,
        "mail_review_required": 0,
    }
    tasks: list[dict] = []

    mail_reviews = connection.execute(
        """
        SELECT id, sender_email, subject, received_at, contains_probation
        FROM inbound_mail_messages
        WHERE status IN ('review_required', 'failed')
        ORDER BY received_at
        """
    ).fetchall()
    metrics["mail_review_required"] = len(mail_reviews)
    for message in mail_reviews:
        tasks.append(
            {
                "priority": "hoch" if message["contains_probation"] else "mittel",
                "priority_rank": 2 if message["contains_probation"] else 4,
                "kind": "Postfach",
                "title": (
                    "Probezeitrückblick prüfen"
                    if message["contains_probation"]
                    else "E-Mail-Anhänge prüfen"
                ),
                "subject": message["sender_email"],
                "context": message["subject"] or "Ohne Betreff",
                "date": message["received_at"],
                "target": "mail",
            }
        )

    if latest_import:
        issue_rows = connection.execute(
            """
            SELECT sii.*, si.original_filename
            FROM sap_import_issues sii
            JOIN sap_imports si ON si.id = sii.sap_import_id
            WHERE sii.sap_import_id = ? AND sii.status = 'open'
              AND sii.severity IN ('blocking', 'warning')
            ORDER BY CASE sii.severity WHEN 'blocking' THEN 1 ELSE 2 END,
                     sii.person_number, sii.id
            """,
            (latest_import["id"],),
        ).fetchall()
        metrics["master_data_issues"] = len(issue_rows)
        for issue in issue_rows:
            person = f"PN {issue['person_number']}" if issue["person_number"] else "SAP-Import"
            tasks.append(
                {
                    "priority": "hoch" if issue["severity"] == "blocking" else "mittel",
                    "priority_rank": 1 if issue["severity"] == "blocking" else 4,
                    "kind": "Stammdaten",
                    "title": "SAP-Konflikt klären" if issue["severity"] == "blocking" else "SAP-Hinweis prüfen",
                    "subject": person,
                    "context": issue["original_filename"],
                    "date": issue["created_at"],
                    "target": "import",
                    "import_id": issue["sap_import_id"],
                }
            )

    if selected_cycle:
        cycle_id = selected_cycle["id"]
        metrics["cases_open"] = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM dialog_cases
            WHERE cycle_id = ? AND active = 1 AND status IN ('offen', 'in_bearbeitung')
            """,
            (cycle_id,),
        ).fetchone()["count"]
        obligation_summary = connection.execute(
            """
            SELECT
                SUM(CASE WHEN o.required = 1 AND o.status NOT IN ('complete', 'waived') THEN 1 ELSE 0 END) AS open_count,
                SUM(CASE WHEN o.required = 1 AND o.status NOT IN ('complete', 'waived')
                          AND o.due_date <> '' AND o.due_date < ? THEN 1 ELSE 0 END) AS overdue_count
            FROM document_obligations o
            JOIN dialog_events de ON de.id = o.dialog_event_id
            WHERE de.cycle_id = ? AND de.status <> 'cancelled'
            """,
            (date.today().isoformat(), cycle_id),
        ).fetchone()
        metrics["obligations_open"] = obligation_summary["open_count"] or 0
        metrics["obligations_overdue"] = obligation_summary["overdue_count"] or 0

        overdue_managers = connection.execute(
            """
            SELECT ma.manager_person_number AS manager_pn,
                   COALESCE(NULLIF(TRIM(mp.first_name || ' ' || mp.last_name), ''),
                            'VG ' || ma.manager_person_number) AS manager_name,
                   COUNT(*) AS obligation_count, MIN(o.due_date) AS oldest_due
            FROM document_obligations o
            JOIN dialog_events de ON de.id = o.dialog_event_id
            JOIN manager_assignments ma ON ma.id = de.manager_assignment_id
            LEFT JOIN persons mp ON mp.person_number = ma.manager_person_number
            WHERE de.cycle_id = ? AND de.status <> 'cancelled'
              AND o.required = 1 AND o.status NOT IN ('complete', 'waived')
              AND o.due_date <> '' AND o.due_date < ?
            GROUP BY ma.manager_person_number, manager_name
            ORDER BY oldest_due, manager_name
            """,
            (cycle_id, date.today().isoformat()),
        ).fetchall()
        for manager in overdue_managers:
            tasks.append(
                {
                    "priority": "hoch",
                    "priority_rank": 2,
                    "kind": "Frist",
                    "title": "Pflichtdokumente überfällig",
                    "subject": manager["manager_name"],
                    "context": f"{manager['obligation_count']} Dokument(e) ausstehend",
                    "date": manager["oldest_due"],
                    "target": "dialogs",
                    "cycle_id": cycle_id,
                    "manager_pn": manager["manager_pn"],
                }
            )

        missing_workbooks = connection.execute(
            """
            SELECT dc.manager_pn,
                   COALESCE(NULLIF(TRIM(m.first_name || ' ' || m.last_name), ''),
                            'VG ' || dc.manager_pn) AS manager_name,
                   COUNT(*) AS case_count
            FROM dialog_cases dc
            LEFT JOIN employees m ON m.pn = dc.manager_pn
            WHERE dc.cycle_id = ? AND dc.active = 1
              AND NOT EXISTS (
                  SELECT 1 FROM package_events pe
                  WHERE pe.cycle_id = dc.cycle_id
                    AND pe.manager_pn = dc.manager_pn
                    AND pe.direction = 'versand'
              )
            GROUP BY dc.manager_pn, manager_name
            ORDER BY manager_name
            """,
            (cycle_id,),
        ).fetchall()
        metrics["workbooks_missing"] = len(missing_workbooks)
        for manager in missing_workbooks:
            tasks.append(
                {
                    "priority": "mittel",
                    "priority_rank": 5,
                    "kind": "Arbeitsmappe",
                    "title": "START-Datei bereitstellen",
                    "subject": manager["manager_name"],
                    "context": f"{manager['case_count']} Mitarbeitende",
                    "date": selected_cycle["created_at"],
                    "target": "manager",
                    "cycle_id": cycle_id,
                    "manager_pn": manager["manager_pn"],
                }
            )

        documents_to_check = connection.execute(
            """
            SELECT od.id, od.case_id, od.manager_pn, od.employee_pn,
                   od.document_kind, od.received_at,
                   e.first_name, e.last_name,
                   COALESCE(NULLIF(TRIM(m.first_name || ' ' || m.last_name), ''),
                            'VG ' || od.manager_pn) AS manager_name
            FROM official_documents od
            JOIN employees e ON e.pn = od.employee_pn
            LEFT JOIN employees m ON m.pn = od.manager_pn
            WHERE od.cycle_id = ? AND od.variant = 'digital'
              AND od.is_current = 1 AND od.signature_checked = 0
            ORDER BY od.received_at
            """,
            (cycle_id,),
        ).fetchall()
        metrics["documents_to_check"] = len(documents_to_check)
        for document in documents_to_check:
            tasks.append(
                {
                    "priority": "hoch",
                    "priority_rank": 2,
                    "kind": "Rücklauf",
                    "title": "Unterschriften prüfen",
                    "subject": f"{document['first_name']} {document['last_name']}",
                    "context": document["manager_name"],
                    "date": document["received_at"],
                    "target": "manager",
                    "cycle_id": cycle_id,
                    "manager_pn": document["manager_pn"],
                }
            )

        scans_pending = connection.execute(
            """
            SELECT od.case_id, od.manager_pn, od.employee_pn,
                   od.document_kind, od.received_at,
                   e.first_name, e.last_name,
                   COALESCE(NULLIF(TRIM(m.first_name || ' ' || m.last_name), ''),
                            'VG ' || od.manager_pn) AS manager_name
            FROM official_documents od
            JOIN employees e ON e.pn = od.employee_pn
            LEFT JOIN employees m ON m.pn = od.manager_pn
            WHERE od.cycle_id = ? AND od.variant = 'digital'
              AND od.is_current = 1 AND od.scan_required = 1
              AND od.signature_checked = 1
              AND NOT EXISTS (
                  SELECT 1 FROM official_documents scan
                  WHERE scan.case_id = od.case_id
                    AND scan.document_kind = od.document_kind
                    AND scan.variant = 'scan' AND scan.is_current = 1
              )
            ORDER BY od.received_at
            """,
            (cycle_id,),
        ).fetchall()
        metrics["scans_pending"] = len(scans_pending)
        for document in scans_pending:
            tasks.append(
                {
                    "priority": "hoch",
                    "priority_rank": 3,
                    "kind": "Rücklauf",
                    "title": "Handschriftlichen Scan ergänzen",
                    "subject": f"{document['first_name']} {document['last_name']}",
                    "context": document["manager_name"],
                    "date": document["received_at"],
                    "target": "manager",
                    "cycle_id": cycle_id,
                    "manager_pn": document["manager_pn"],
                }
            )

        metrics["dossier_ready"] = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM official_documents
            WHERE cycle_id = ? AND is_current = 1 AND handoff_status = 'staged'
            """,
            (cycle_id,),
        ).fetchone()["count"]

    tasks.sort(key=lambda item: (item["priority_rank"], item["date"] or ""))
    for cycle in cycles:
        cycle["status_label"] = CYCLE_STATUS_LABELS.get(cycle["status"], cycle["status"])

    return {
        **base,
        "selected_cycle": selected_cycle,
        "latest_import": latest_import,
        "metrics": metrics,
        "tasks": tasks,
        "task_count": len(tasks),
        "generated_at": datetime.now().astimezone().isoformat(timespec="minutes"),
    }
