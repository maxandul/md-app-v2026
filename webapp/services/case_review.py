"""Einzelfallprüfung, begründete Korrekturen und Dokumentversionen."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from typing import Any

from webapp.services.documents import (
    DOCUMENT_NAMES,
    SCOPE_NAMES,
    refresh_case_status,
    update_scope_obligations,
)


CORRECTABLE_FIELDS = {
    "official_scope": "Verbindlicher Umfang",
    "dialog_date": "Gesprächsdatum",
    "period_start": "Zeitraum von",
    "period_end": "Zeitraum bis",
    "overall_rating_code": "Gesamtbeurteilung",
    "agreement": "Einigkeitsstatus",
}

HANDOFF_LABELS = {
    "not_applicable": "Nicht bereitgestellt",
    "needs_signature_check": "Unterschriftenprüfung offen",
    "waiting_scan": "Handschriftlicher Scan ausstehend",
    "staged": "Für Personaldossier-Ablage bereitgestellt",
}

VARIANT_LABELS = {
    "digital": "Elektronisches PDF",
    "scan": "Handschriftlicher Scan",
    "administrative": "Administrative Bestätigung",
}

OBLIGATION_LABELS = {
    "open": "Offen",
    "received": "Eingegangen",
    "review": "HR-Prüfung",
    "scan_pending": "Scan ausstehend",
    "complete": "Vollständig",
    "waived": "Nicht erforderlich",
    "rejected": "Zurückgewiesen",
}


def case_review_detail(
    connection: sqlite3.Connection, *, cycle_id: int, case_id: str
) -> dict[str, Any]:
    case = connection.execute(
        """
        SELECT dc.*, c.review_year, c.outlook_year,
               e.first_name, e.last_name, e.position, e.org_unit,
               e.entry_date, e.exit_date, e.probation_end,
               COALESCE(NULLIF(TRIM(m.first_name || ' ' || m.last_name), ''),
                        'VG ' || dc.manager_pn) AS manager_name
        FROM dialog_cases dc
        JOIN cycles c ON c.id = dc.cycle_id
        JOIN employees e ON e.pn = dc.employee_pn
        LEFT JOIN employees m ON m.pn = dc.manager_pn
        WHERE dc.cycle_id = ? AND dc.case_id = ?
        """,
        (cycle_id, case_id),
    ).fetchone()
    if not case:
        raise LookupError("MD-Fall nicht gefunden.")
    item = dict(case)
    item["scope_label"] = SCOPE_NAMES.get(item["official_scope"], "Noch nicht bekannt")

    documents = []
    for row in connection.execute(
        """
        SELECT od.* FROM official_documents od
        WHERE od.case_id = ?
        ORDER BY od.document_kind, od.variant, od.received_at DESC, od.id DESC
        """,
        (case_id,),
    ).fetchall():
        document = dict(row)
        document["document_name"] = DOCUMENT_NAMES.get(
            document["document_kind"], document["document_kind"]
        )
        document["variant_label"] = VARIANT_LABELS.get(
            document["variant"], document["variant"]
        )
        document["handoff_label"] = HANDOFF_LABELS.get(
            document["handoff_status"], document["handoff_status"]
        )
        try:
            document["data_block"] = json.loads(document["data_block_json"] or "{}")
        except json.JSONDecodeError:
            document["data_block"] = {}
        documents.append(document)

    obligations = []
    for row in connection.execute(
            """
            SELECT o.* FROM document_obligations o
            JOIN dialog_events de ON de.id = o.dialog_event_id
            WHERE de.legacy_case_id = ?
            ORDER BY o.document_kind
            """,
            (case_id,),
        ).fetchall():
        obligation = dict(row)
        obligation["document_name"] = DOCUMENT_NAMES.get(
            obligation["document_kind"], obligation["document_kind"]
        )
        obligation["status_label"] = OBLIGATION_LABELS.get(
            obligation["status"], obligation["status"]
        )
        obligations.append(obligation)
    corrections = [
        dict(row)
        for row in connection.execute(
            """
            SELECT cc.*, COALESCE(u.email, 'System/Testbetrieb') AS user_email
            FROM case_corrections cc
            LEFT JOIN app_users u ON u.id = cc.user_id
            WHERE cc.case_id = ?
            ORDER BY cc.created_at DESC, cc.id DESC
            """,
            (case_id,),
        ).fetchall()
    ]
    for correction in corrections:
        correction["field_label"] = CORRECTABLE_FIELDS.get(
            correction["field_name"], correction["field_name"]
        )
    return {
        "case": item,
        "documents": documents,
        "obligations": obligations,
        "corrections": corrections,
        "correction_locked": any(
            document["is_current"]
            and (document["signature_checked"] or document["handoff_status"] == "staged")
            for document in documents
        ),
    }


def _validate_date(value: str, label: str) -> str:
    value = value.strip()
    if value:
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{label} ist kein gültiges Datum.") from exc
    return value


def correct_case_data(
    connection: sqlite3.Connection,
    *,
    cycle_id: int,
    case_id: str,
    values: dict[str, str],
    reason: str,
    user_id: int | None,
    corrected_at: datetime | None = None,
) -> list[str]:
    reason = reason.strip()
    if len(reason) < 10:
        raise ValueError("Bitte begründe die Korrektur mit mindestens 10 Zeichen.")
    current = connection.execute(
        "SELECT * FROM dialog_cases WHERE cycle_id = ? AND case_id = ?",
        (cycle_id, case_id),
    ).fetchone()
    if not current:
        raise LookupError("MD-Fall nicht gefunden.")
    locked = connection.execute(
        """
        SELECT 1 FROM official_documents
        WHERE case_id = ? AND is_current = 1
          AND (signature_checked = 1 OR handoff_status = 'staged')
        LIMIT 1
        """,
        (case_id,),
    ).fetchone()
    if locked:
        raise ValueError(
            "Freigegebene Dokumentdaten können nicht direkt korrigiert werden. "
            "Bitte importiere eine begründete neue PDF-Version."
        )

    normalized = {
        "official_scope": values.get("official_scope", "").strip(),
        "dialog_date": _validate_date(values.get("dialog_date", ""), "Gesprächsdatum"),
        "period_start": _validate_date(values.get("period_start", ""), "Zeitraum von"),
        "period_end": _validate_date(values.get("period_end", ""), "Zeitraum bis"),
        "overall_rating_code": values.get("overall_rating_code", "").strip().upper(),
        "agreement": values.get("agreement", "").strip().upper(),
    }
    if normalized["official_scope"] not in {"full", "review_only", "outlook_only", "none"}:
        raise ValueError("Bitte wähle einen gültigen verbindlichen Umfang.")
    if normalized["overall_rating_code"] not in {"", "A", "B", "C", "D", "E"}:
        raise ValueError("Die Gesamtbeurteilung muss A bis E oder leer sein.")
    if normalized["agreement"] not in {"", "JA", "NEIN"}:
        raise ValueError("Der Einigkeitsstatus muss JA, NEIN oder leer sein.")
    if (
        normalized["period_start"]
        and normalized["period_end"]
        and normalized["period_start"] > normalized["period_end"]
    ):
        raise ValueError("Der Zeitraum beginnt nach seinem Enddatum.")

    changed = [
        field for field in CORRECTABLE_FIELDS
        if str(current[field] or "") != normalized[field]
    ]
    if not changed:
        raise ValueError("Es wurde keine fachliche Angabe geändert.")
    timestamp = (corrected_at or datetime.now().astimezone()).isoformat(timespec="seconds")
    try:
        connection.execute(
            """
            UPDATE dialog_cases
            SET official_scope = ?, dialog_date = ?, period_start = ?, period_end = ?,
                overall_rating_code = ?, agreement = ?, updated_at = ?
            WHERE case_id = ?
            """,
            (
                normalized["official_scope"], normalized["dialog_date"],
                normalized["period_start"], normalized["period_end"],
                normalized["overall_rating_code"], normalized["agreement"],
                timestamp, case_id,
            ),
        )
        for field in changed:
            connection.execute(
                """
                INSERT INTO case_corrections (
                    case_id, user_id, field_name, old_value, new_value, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id, user_id, field, str(current[field] or ""),
                    normalized[field], reason, timestamp,
                ),
            )
        update_scope_obligations(
            connection,
            case_id=case_id,
            scope=normalized["official_scope"],
            timestamp=timestamp,
        )
        scan_required = (
            normalized["overall_rating_code"] in {"D", "E"}
            or normalized["agreement"] == "NEIN"
        )
        connection.execute(
            """
            UPDATE official_documents
            SET scan_required = ?
            WHERE case_id = ? AND document_kind = 'review' AND variant = 'digital'
              AND is_current = 1 AND signature_checked = 0
            """,
            (int(scan_required), case_id),
        )
        refresh_case_status(connection, case_id)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return changed
