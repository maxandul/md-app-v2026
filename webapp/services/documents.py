"""Importiert offizielle PDF-Rückläufe und steuert die Dossier-Bereitstellung."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader


DOCUMENT_NAMES = {
    "review": "Rückblick",
    "outlook": "Ausblick",
    "no_md": "Kein MD",
}

SCOPE_NAMES = {
    "full": "Rückblick und Ausblick",
    "review_only": "Nur Rückblick",
    "outlook_only": "Nur Ausblick",
    "none": "Kein MD",
    "": "Noch nicht bekannt",
}

DATA_KEYS = (
    "version",
    "document",
    "case_id",
    "package_id",
    "pn",
    "ans",
    "year",
    "scope",
    "period_start",
    "period_end",
    "dialog_date",
    "dialog_type",
    "review_competencies",
    "development_competencies",
    "rating",
    "agreement",
    "handwritten_scan_required",
    "no_md_reason",
)


@dataclass(frozen=True)
class PdfInspection:
    text: str
    data: dict[str, str]
    page_count: int
    fill_sign_detected: bool
    fill_sign_count: int


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _object(value: Any) -> Any:
    return value.get_object() if hasattr(value, "get_object") else value


def inspect_pdf(path: Path) -> PdfInspection:
    try:
        reader = PdfReader(path)
    except Exception as exc:
        raise ValueError("Die Datei ist kein lesbares PDF.") from exc
    if reader.is_encrypted:
        raise ValueError("Verschlüsselte PDFs können nicht verarbeitet werden.")

    texts: list[str] = []
    fill_sign_count = 0
    for page in reader.pages:
        try:
            texts.append(page.extract_text() or "")
        except Exception as exc:
            raise ValueError("Der PDF-Text konnte nicht ausgelesen werden.") from exc
        contents = page.get_contents()
        streams = contents if isinstance(contents, list) else [contents]
        for stream in streams:
            if stream is not None:
                fill_sign_count += stream.get_data().count(b"/ADBE_FillSign BMC")

    root = reader.trailer["/Root"]
    fill_sign_detected = bool(root.get("/ADBE_FillSignInfo")) or fill_sign_count > 0
    text = "\n".join(texts)
    return PdfInspection(
        text=text,
        data=extract_data_block(text),
        page_count=len(reader.pages),
        fill_sign_detected=fill_sign_detected,
        fill_sign_count=fill_sign_count,
    )


def extract_data_block(text: str) -> dict[str, str]:
    start = text.find("MD-DATENBLOCK")
    if start < 0:
        return {}
    segment = text[start : start + 5000]
    data: dict[str, str] = {}
    for key in DATA_KEYS:
        match = re.search(rf"(?:^|;)\s*{re.escape(key)}\s*=\s*([^;\r\n]*)", segment)
        if match:
            data[key] = re.sub(r"\s+", " ", match.group(1)).strip()
    return data


def _document_kind(value: str) -> str:
    mapping = {
        "RUECKBLICK": "review",
        "AUSBLICK": "outlook",
        "KEIN_MD": "no_md",
    }
    try:
        return mapping[value.upper()]
    except KeyError as exc:
        raise ValueError(f"Unbekannter Dokumenttyp im MD-Datenblock: {value or 'leer'}") from exc


def _required(data: dict[str, str], key: str) -> str:
    value = data.get(key, "").strip()
    if not value:
        raise ValueError(f"Im MD-Datenblock fehlt «{key}».")
    return value


def _safe_filename_part(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_")
    return text or "Unbekannt"


def _handoff_filename(case: sqlite3.Row, document_kind: str, *, scan: bool) -> str:
    year = case["review_year"] if document_kind == "review" else case["outlook_year"]
    prefix = "Rueckblick" if document_kind == "review" else "Ausblick"
    middle = "_HANDSCAN" if scan else ""
    return (
        f"{prefix}_{year}_{_safe_filename_part(case['last_name'])}_"
        f"{_safe_filename_part(case['first_name'])}{middle}_"
        f"{_safe_filename_part(case['employee_pn'])}.pdf"
    )


def _case_row(connection: sqlite3.Connection, case_id: str) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT dc.*, c.review_year, c.outlook_year,
               e.first_name, e.last_name, e.employment_assignment
        FROM dialog_cases dc
        JOIN cycles c ON c.id = dc.cycle_id
        JOIN employees e ON e.pn = dc.employee_pn
        WHERE dc.case_id = ?
        """,
        (case_id,),
    ).fetchone()
    if not row:
        raise ValueError("Die Fall-ID des PDFs ist in dieser Datenbank nicht vorhanden.")
    return row


def _store_current_document(
    connection: sqlite3.Connection,
    *,
    case: sqlite3.Row,
    document_kind: str,
    variant: str,
    original_filename: str,
    stored_path: Path,
    digest: str,
    received_at: str,
    inspection: PdfInspection | None,
    signature_checked: bool,
    scan_required: bool,
    handoff_status: str,
    handoff_filename: str = "",
    handoff_at: str = "",
    replacement_reason: str = "",
) -> int:
    duplicate = connection.execute(
        "SELECT id FROM official_documents WHERE sha256 = ?", (digest,)
    ).fetchone()
    if duplicate:
        raise ValueError("Dieses PDF wurde bereits importiert.")
    current = connection.execute(
        """
        SELECT * FROM official_documents
        WHERE case_id = ? AND document_kind = ? AND variant = ? AND is_current = 1
        """,
        (case["case_id"], document_kind, variant),
    ).fetchone()
    replacement_reason = replacement_reason.strip()
    if current:
        if not replacement_reason:
            raise ValueError(
                "Für diesen Dokumenttyp besteht bereits eine aktuelle Version. "
                "Die neue Version muss in der Einzelfallansicht mit einem "
                "Ersetzungsgrund importiert werden."
            )
        if current["handoff_status"] == "staged":
            raise ValueError(
                "Die aktuelle Version wurde bereits für die Personaldossier-Ablage "
                "bereitgestellt. Eine Ersetzung muss zuerst mit dem nachgelagerten "
                "Ablageprozess geklärt werden."
            )
        connection.execute(
            "UPDATE official_documents SET is_current = 0, replaced_at = ? WHERE id = ?",
            (received_at, current["id"]),
        )
    event = connection.execute(
        "SELECT id, event_id FROM dialog_events WHERE legacy_case_id = ? ORDER BY id LIMIT 1",
        (case["case_id"],),
    ).fetchone()
    obligation = None
    if event:
        if document_kind == "no_md":
            connection.execute(
                """
                UPDATE document_obligations
                SET status = 'waived', updated_at = ?
                WHERE dialog_event_id = ? AND required = 1
                  AND document_kind IN ('review', 'outlook')
                """,
                (received_at, event["id"]),
            )
        obligation = connection.execute(
            """
            SELECT id FROM document_obligations
            WHERE dialog_event_id = ? AND document_kind = ?
            """,
            (event["id"], document_kind),
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
                    f"{event['event_id']}-{document_kind}", event["id"], document_kind,
                    int(document_kind == "no_md"), received_at, received_at,
                ),
            )
            obligation = {"id": int(cursor.lastrowid)}
    cursor = connection.execute(
        """
        INSERT INTO official_documents (
            case_id, dialog_event_id, document_obligation_id,
            cycle_id, employee_pn, manager_pn, document_kind, variant,
            original_filename, stored_path, sha256, received_at, data_block_json,
            extracted_text, fill_sign_detected, fill_sign_count, signature_checked,
            scan_required, handoff_status, handoff_filename, handoff_at,
            replaces_document_id, replacement_reason, replaced_at, is_current
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            case["case_id"],
            event["id"] if event else None,
            obligation["id"] if obligation else None,
            case["cycle_id"],
            case["employee_pn"],
            case["manager_pn"],
            document_kind,
            variant,
            original_filename,
            str(stored_path),
            digest,
            received_at,
            json.dumps(inspection.data if inspection else {}, ensure_ascii=False),
            inspection.text if inspection else "",
            int(inspection.fill_sign_detected) if inspection else 0,
            inspection.fill_sign_count if inspection else 0,
            int(signature_checked),
            int(scan_required),
            handoff_status,
            handoff_filename,
            handoff_at,
            current["id"] if current else None,
            replacement_reason,
            "",
        ),
    )
    document_id = int(cursor.lastrowid)
    if obligation:
        obligation_status = "complete" if variant in {"scan", "administrative"} else "received"
        connection.execute(
            """
            UPDATE document_obligations
            SET status = ?, fulfilled_document_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (obligation_status, document_id, received_at, obligation["id"]),
        )
    return document_id


def refresh_dialog_event_status(connection: sqlite3.Connection, case_id: str) -> None:
    event = connection.execute(
        "SELECT id FROM dialog_events WHERE legacy_case_id = ? ORDER BY id LIMIT 1",
        (case_id,),
    ).fetchone()
    if not event:
        return
    obligations = connection.execute(
        "SELECT document_kind, required, status FROM document_obligations WHERE dialog_event_id = ?",
        (event["id"],),
    ).fetchall()
    required = [item for item in obligations if item["required"]]
    if required and all(item["status"] in {"complete", "waived"} for item in required):
        status = "no_md" if any(
            item["document_kind"] == "no_md" and item["status"] == "complete"
            for item in required
        ) else "completed"
    elif any(item["status"] != "open" for item in obligations):
        status = "in_progress"
    else:
        status = "open"
    connection.execute(
        "UPDATE dialog_events SET status = ?, updated_at = ? WHERE id = ?",
        (status, datetime.now().astimezone().isoformat(timespec="seconds"), event["id"]),
    )


def _current_documents(connection: sqlite3.Connection, case_id: str) -> dict[tuple[str, str], sqlite3.Row]:
    rows = connection.execute(
        """
        SELECT * FROM official_documents
        WHERE case_id = ? AND is_current = 1
        """,
        (case_id,),
    ).fetchall()
    return {(row["document_kind"], row["variant"]): row for row in rows}


def refresh_case_status(connection: sqlite3.Connection, case_id: str) -> str:
    case = _case_row(connection, case_id)
    documents = _current_documents(connection, case_id)
    scope = case["official_scope"]
    if scope == "none":
        status = "kein_md" if ("no_md", "administrative") in documents else "in_bearbeitung"
    else:
        expected = {
            "full": ["review", "outlook"],
            "review_only": ["review"],
            "outlook_only": ["outlook"],
        }.get(scope, [])
        complete = bool(expected)
        for kind in expected:
            digital = documents.get((kind, "digital"))
            if not digital or not digital["signature_checked"]:
                complete = False
                continue
            if digital["scan_required"]:
                scan = documents.get((kind, "scan"))
                if not scan or scan["handoff_status"] != "staged":
                    complete = False
            elif digital["handoff_status"] != "staged":
                complete = False
        status = "vollstaendig" if complete else "in_bearbeitung"
    connection.execute(
        "UPDATE dialog_cases SET status = ?, updated_at = ? WHERE case_id = ?",
        (status, datetime.now().astimezone().isoformat(timespec="seconds"), case_id),
    )
    refresh_dialog_event_status(connection, case_id)
    return status


def update_scope_obligations(
    connection: sqlite3.Connection, *, case_id: str, scope: str, timestamp: str
) -> None:
    event = connection.execute(
        "SELECT id FROM dialog_events WHERE legacy_case_id = ? ORDER BY id LIMIT 1",
        (case_id,),
    ).fetchone()
    if not event:
        return
    required_kinds = {
        "full": {"review", "outlook"},
        "review_only": {"review"},
        "outlook_only": {"outlook"},
        "none": set(),
    }[scope]
    for kind in ("review", "outlook"):
        obligation = connection.execute(
            """
            SELECT id, status FROM document_obligations
            WHERE dialog_event_id = ? AND document_kind = ?
            """,
            (event["id"], kind),
        ).fetchone()
        if not obligation:
            continue
        required = int(kind in required_kinds)
        status = obligation["status"]
        if required and status == "waived":
            status = "open"
        elif not required and status != "complete":
            status = "waived"
        connection.execute(
            """
            UPDATE document_obligations
            SET required = ?, status = ?, updated_at = ? WHERE id = ?
            """,
            (required, status, timestamp, obligation["id"]),
        )
    connection.execute(
        "UPDATE dialog_events SET required_scope = ?, updated_at = ? WHERE id = ?",
        (scope, timestamp, event["id"]),
    )


def import_official_pdf(
    connection: sqlite3.Connection,
    *,
    path: Path,
    original_filename: str,
    accepted_dir: Path,
    received_at: datetime | None = None,
    replacement_reason: str = "",
) -> dict[str, Any]:
    inspection = inspect_pdf(path)
    if not inspection.data:
        raise ValueError("Kein MD-Datenblock gefunden. Handschriftliche Scans bitte beim Fall hochladen.")

    data = inspection.data
    case = _case_row(connection, _required(data, "case_id"))
    if _required(data, "pn") != case["employee_pn"]:
        raise ValueError("Die Personalnummer im PDF stimmt nicht mit der Fall-ID überein.")
    if data.get("ans") and data["ans"] != case["employment_assignment"]:
        raise ValueError("Ans. im PDF stimmt nicht mit dem aktuellen SAP-Datenstand überein.")

    package_id = _required(data, "package_id")
    sent = connection.execute(
        """
        SELECT id FROM package_events
        WHERE package_id = ? AND cycle_id = ? AND manager_pn = ? AND direction = 'versand'
        ORDER BY id DESC LIMIT 1
        """,
        (package_id, case["cycle_id"], case["manager_pn"]),
    ).fetchone()
    if not sent:
        raise ValueError("Die Paket-ID ist für diesen Fall nicht als Versand registriert.")

    document_kind = _document_kind(_required(data, "document"))
    expected_year = case["outlook_year"] if document_kind == "outlook" else case["review_year"]
    if int(_required(data, "year")) != expected_year:
        raise ValueError("Das Dokumentjahr stimmt nicht mit dem Jahresprozess überein.")

    scope = data.get("scope", "").strip()
    if document_kind == "no_md":
        scope = "none"
    if scope and scope not in {"full", "review_only", "outlook_only", "none"}:
        raise ValueError("Der MD-Umfang im PDF ist unbekannt.")
    if document_kind == "no_md" and not data.get("no_md_reason"):
        raise ValueError("In der Kein-MD-Bestätigung fehlt der Grund.")

    declared_scan_required = data.get("handwritten_scan_required", "NEIN").upper() == "JA"
    derived_scan_required = (
        data.get("rating", "").upper() in {"D", "E"}
        or data.get("agreement", "").upper() == "NEIN"
    )
    scan_required = False if document_kind == "no_md" else derived_scan_required
    if document_kind != "no_md" and declared_scan_required != derived_scan_required:
        raise ValueError(
            "Die Scanpflicht im PDF widerspricht Gesamtbeurteilung oder Einigkeitsstatus."
        )
    variant = "administrative" if document_kind == "no_md" else "digital"
    handoff_status = "not_applicable" if document_kind == "no_md" else "needs_signature_check"
    timestamp = (received_at or datetime.now().astimezone()).isoformat(timespec="seconds")
    digest = file_sha256(path)
    accepted_dir.mkdir(parents=True, exist_ok=True)
    stored_path = accepted_dir / f"{timestamp[:19].replace(':', '').replace('-', '')}_{digest[:10]}_{Path(original_filename).name}"

    try:
        shutil.move(str(path), str(stored_path))
        document_id = _store_current_document(
            connection,
            case=case,
            document_kind=document_kind,
            variant=variant,
            original_filename=original_filename,
            stored_path=stored_path,
            digest=digest,
            received_at=timestamp,
            inspection=inspection,
            signature_checked=document_kind == "no_md",
            scan_required=scan_required,
            handoff_status=handoff_status,
            replacement_reason=replacement_reason,
        )
        if scope:
            connection.execute(
                "UPDATE dialog_cases SET official_scope = ? WHERE case_id = ?",
                (scope, case["case_id"]),
            )
            update_scope_obligations(
                connection, case_id=case["case_id"], scope=scope, timestamp=timestamp
            )
        if document_kind == "review":
            connection.execute(
                """
                UPDATE dialog_cases
                SET dialog_date = ?, period_start = ?, period_end = ?,
                    overall_rating_code = ?, agreement = ?
                WHERE case_id = ?
                """,
                (
                    data.get("dialog_date", ""),
                    data.get("period_start", ""),
                    data.get("period_end", ""),
                    data.get("rating", "").upper(),
                    data.get("agreement", "").upper(),
                    case["case_id"],
                ),
            )
        refresh_case_status(connection, case["case_id"])
        connection.commit()
    except Exception:
        connection.rollback()
        if stored_path.exists() and not path.exists():
            shutil.move(str(stored_path), str(path))
        raise

    return {
        "document_id": document_id,
        "cycle_id": case["cycle_id"],
        "case_id": case["case_id"],
        "employee_pn": case["employee_pn"],
        "document_kind": document_kind,
        "scan_required": scan_required,
        "fill_sign_detected": inspection.fill_sign_detected,
        "fill_sign_count": inspection.fill_sign_count,
    }


def confirm_digital_signature(
    connection: sqlite3.Connection,
    *,
    document_id: int,
    handoff_dir: Path,
    checked_at: datetime | None = None,
) -> dict[str, Any]:
    document = connection.execute(
        "SELECT * FROM official_documents WHERE id = ? AND is_current = 1",
        (document_id,),
    ).fetchone()
    if not document or document["variant"] != "digital":
        raise ValueError("Das elektronische PDF wurde nicht gefunden.")
    case = _case_row(connection, document["case_id"])
    timestamp = (checked_at or datetime.now().astimezone()).isoformat(timespec="seconds")
    if document["scan_required"]:
        connection.execute(
            """
            UPDATE official_documents
            SET signature_checked = 1, handoff_status = 'waiting_scan'
            WHERE id = ?
            """,
            (document_id,),
        )
        if document["document_obligation_id"]:
            connection.execute(
                """
                UPDATE document_obligations
                SET status = 'scan_pending', updated_at = ? WHERE id = ?
                """,
                (timestamp, document["document_obligation_id"]),
            )
        handoff_filename = ""
    else:
        source = Path(document["stored_path"])
        handoff_dir.mkdir(parents=True, exist_ok=True)
        handoff_filename = _handoff_filename(case, document["document_kind"], scan=False)
        destination = handoff_dir / handoff_filename
        if destination.exists() and destination.resolve() != source.resolve():
            raise ValueError(f"Im Übergabeordner existiert bereits «{handoff_filename}».")
        if source.resolve() != destination.resolve():
            shutil.move(str(source), str(destination))
        connection.execute(
            """
            UPDATE official_documents
            SET signature_checked = 1, handoff_status = 'staged', stored_path = ?,
                handoff_filename = ?, handoff_at = ?
            WHERE id = ?
            """,
            (str(destination), handoff_filename, timestamp, document_id),
        )
        if document["document_obligation_id"]:
            connection.execute(
                """
                UPDATE document_obligations
                SET status = 'complete', fulfilled_document_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (document_id, timestamp, document["document_obligation_id"]),
            )
    refresh_case_status(connection, document["case_id"])
    connection.commit()
    return {
        "case_id": document["case_id"],
        "cycle_id": document["cycle_id"],
        "scan_required": bool(document["scan_required"]),
        "handoff_filename": handoff_filename,
    }


def import_handwritten_scan(
    connection: sqlite3.Connection,
    *,
    case_id: str,
    document_kind: str,
    path: Path,
    original_filename: str,
    handoff_dir: Path,
    received_at: datetime | None = None,
) -> dict[str, Any]:
    if document_kind not in {"review", "outlook"}:
        raise ValueError("Unbekannter Dokumenttyp für den Scan.")
    case = _case_row(connection, case_id)
    documents = _current_documents(connection, case_id)
    digital = documents.get((document_kind, "digital"))
    if not digital:
        raise ValueError("Zuerst muss das elektronische PDF importiert werden.")
    if not digital["scan_required"]:
        raise ValueError("Für dieses Dokument ist kein handschriftlicher Scan erforderlich.")
    if not digital["signature_checked"]:
        raise ValueError("Zuerst müssen die elektronischen Unterschriften bestätigt werden.")

    inspection = inspect_pdf(path)
    timestamp = (received_at or datetime.now().astimezone()).isoformat(timespec="seconds")
    digest = file_sha256(path)
    handoff_dir.mkdir(parents=True, exist_ok=True)
    handoff_filename = _handoff_filename(case, document_kind, scan=True)
    destination = handoff_dir / handoff_filename
    if destination.exists():
        raise ValueError(f"Im Übergabeordner existiert bereits «{handoff_filename}».")

    try:
        shutil.move(str(path), str(destination))
        document_id = _store_current_document(
            connection,
            case=case,
            document_kind=document_kind,
            variant="scan",
            original_filename=original_filename,
            stored_path=destination,
            digest=digest,
            received_at=timestamp,
            inspection=inspection,
            signature_checked=True,
            scan_required=True,
            handoff_status="staged",
            handoff_filename=handoff_filename,
            handoff_at=timestamp,
        )
        connection.execute(
            "UPDATE official_documents SET handoff_status = 'not_applicable' WHERE id = ?",
            (digital["id"],),
        )
        refresh_case_status(connection, case_id)
        connection.commit()
    except Exception:
        connection.rollback()
        if destination.exists() and not path.exists():
            shutil.move(str(destination), str(path))
        raise
    return {
        "document_id": document_id,
        "cycle_id": case["cycle_id"],
        "case_id": case_id,
        "handoff_filename": handoff_filename,
    }


def _document_state(digital: sqlite3.Row | None, scan: sqlite3.Row | None) -> dict[str, Any]:
    if not digital:
        return {"key": "missing", "label": "Elektronisches PDF fehlt", "digital": None, "scan": scan}
    if not digital["signature_checked"]:
        return {"key": "signature", "label": "Unterschriften prüfen", "digital": digital, "scan": scan}
    if digital["scan_required"] and not scan:
        return {"key": "scan", "label": "Handschriftlicher Scan ausstehend", "digital": digital, "scan": None}
    if digital["scan_required"]:
        return {"key": "staged", "label": "Handschriftlicher Scan bereitgestellt", "digital": digital, "scan": scan}
    return {"key": "staged", "label": "Elektronisches PDF bereitgestellt", "digital": digital, "scan": None}


def case_document_overview(
    connection: sqlite3.Connection, *, cycle_id: int, manager_pn: str
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT dc.*, e.first_name, e.last_name, e.position, e.org_unit,
               e.exit_date, e.probation_end
        FROM dialog_cases dc
        JOIN employees e ON e.pn = dc.employee_pn
        WHERE dc.cycle_id = ? AND dc.manager_pn = ?
        ORDER BY e.last_name, e.first_name, e.pn
        """,
        (cycle_id, manager_pn),
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        documents = _current_documents(connection, row["case_id"])
        scope = row["official_scope"]
        states: list[dict[str, Any]] = []
        if scope == "none":
            no_md = documents.get(("no_md", "administrative"))
            states.append(
                {
                    "kind": "no_md",
                    "name": DOCUMENT_NAMES["no_md"],
                    "key": "no_md" if no_md else "missing",
                    "label": "Kein MD bestätigt" if no_md else "Bestätigung fehlt",
                    "digital": no_md,
                    "scan": None,
                }
            )
        else:
            expected = {
                "full": ["review", "outlook"],
                "review_only": ["review"],
                "outlook_only": ["outlook"],
            }.get(scope, [])
            for kind in expected:
                state = _document_state(
                    documents.get((kind, "digital")), documents.get((kind, "scan"))
                )
                state.update({"kind": kind, "name": DOCUMENT_NAMES[kind]})
                states.append(state)
        item["scope_label"] = SCOPE_NAMES.get(scope, scope or SCOPE_NAMES[""])
        item["document_states"] = states
        result.append(item)
    return result
