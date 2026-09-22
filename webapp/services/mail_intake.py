"""Sichert und klassifiziert eingehende Outlook-Nachrichten idempotent."""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Iterable

from werkzeug.utils import secure_filename

from webapp.adapters.outlook import InboundMessage, OutlookInboxAdapter
from webapp.services.documents import import_official_pdf, inspect_pdf
from webapp.services.feedback import (
    create_feedback_bundles_for_message,
    import_feedback_pdf,
)


STATUS_LABELS = {
    "new": "Neu",
    "ready_to_move": "Verarbeitet – Verschieben ausstehend",
    "review_required": "HR-Prüfung erforderlich",
    "moved": "Verarbeitet und in Outlook verschoben",
    "ignored": "Ohne MD-Bezug ignoriert",
    "failed": "Fehlgeschlagen",
}


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.astimezone()
    return value.isoformat(timespec="seconds")


def _kind(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return "md_pdf"
    if suffix in {".html", ".htm"}:
        return "html_workbook"
    return "other"


def _md_hint(value: str) -> bool:
    folded = value.casefold().replace("ü", "ue")
    return any(
        word in folded
        for word in ("rueckblick", "ausblick", "mitarbeitenden-dialog", "mitarbeitendendialog", "kein_md", "probezeit", "feedback")
    )


def _existing_attachment_path(
    connection: sqlite3.Connection, digest: str
) -> str:
    row = connection.execute(
        """
        SELECT stored_path FROM inbound_mail_attachments
        WHERE sha256 = ? AND status IN ('imported', 'duplicate')
        ORDER BY id LIMIT 1
        """,
        (digest,),
    ).fetchone()
    if row:
        return row["stored_path"]
    row = connection.execute(
        "SELECT stored_path FROM official_documents WHERE sha256 = ? LIMIT 1",
        (digest,),
    ).fetchone()
    return row["stored_path"] if row else ""


def _insert_attachment(
    connection: sqlite3.Connection,
    *,
    message_id: int,
    index: int,
    filename: str,
    stored_path: str,
    digest: str,
    file_kind: str,
    status: str,
    created_at: str,
    error_message: str = "",
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO inbound_mail_attachments (
            mail_message_id, attachment_index, original_filename, stored_path,
            sha256, file_kind, status, error_message, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            message_id, index, filename, stored_path, digest, file_kind,
            status, error_message, created_at,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def process_inbound_messages(
    connection: sqlite3.Connection,
    *,
    messages: Iterable[InboundMessage],
    inbox_dir: Path,
    pdf_dir: Path,
    target_folder: str,
    handoff_dir: Path | None = None,
    move_message: Callable[[str, str], str] | None = None,
) -> dict[str, Any]:
    """Importiert nur MD-relevante Inhalte und kennzeichnet gemischte Mails."""
    result: dict[str, Any] = {
        "read": 0,
        "stored": 0,
        "ready": 0,
        "moved": 0,
        "review": 0,
        "ignored": 0,
        "duplicates": 0,
        "feedback_bundles": 0,
        "failed": 0,
        "errors": [],
    }
    inbox_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    handoff_dir = handoff_dir or pdf_dir
    handoff_dir.mkdir(parents=True, exist_ok=True)

    for message in messages:
        result["read"] += 1
        entry_id = str(message.entry_id or "").strip()
        if not entry_id:
            result["failed"] += 1
            result["errors"].append("Outlook-Nachricht ohne EntryID übersprungen.")
            continue
        duplicate = connection.execute(
            """
            SELECT id FROM inbound_mail_messages
            WHERE outlook_entry_id = ?
               OR (internet_message_id <> '' AND internet_message_id = ?)
            LIMIT 1
            """,
            (entry_id, message.internet_message_id or ""),
        ).fetchone()
        if not duplicate:
            duplicate = connection.execute(
                """
                SELECT outlook_entry_id AS id FROM ignored_mail_messages
                WHERE outlook_entry_id = ?
                   OR (internet_message_id <> '' AND internet_message_id = ?)
                LIMIT 1
                """,
                (entry_id, message.internet_message_id or ""),
            ).fetchone()
        if duplicate:
            result["duplicates"] += 1
            continue

        received_at = _timestamp(message.received_at)
        created_at = datetime.now().astimezone().isoformat(timespec="seconds")
        cursor = connection.execute(
            """
            INSERT INTO inbound_mail_messages (
                outlook_entry_id, internet_message_id, sender_email, subject,
                received_at, status, target_folder, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'new', ?, ?, ?)
            """,
            (
                entry_id, message.internet_message_id or "", message.sender_email,
                message.subject, received_at, target_folder, created_at, created_at,
            ),
        )
        message_id = int(cursor.lastrowid)
        connection.commit()

        message_dir = inbox_dir / f"mail-{message_id:06d}"
        needs_review = False
        contains_probation = False
        md_relevant = False
        foreign_attachments: list[tuple[Any, str, str]] = []

        with TemporaryDirectory(prefix="md-intake-") as temporary:
            temporary_dir = Path(temporary)
            for attachment in message.attachments:
                filename = Path(attachment.filename or f"Anhang-{attachment.index}").name
                digest = hashlib.sha256(attachment.content).hexdigest()
                file_kind = _kind(filename)
                hint = _md_hint(filename)
                probation = "probezeit" in f"{filename} {message.subject}".casefold()
                contains_probation = contains_probation or probation
                existing_path = _existing_attachment_path(connection, digest)
                if existing_path:
                    _insert_attachment(
                        connection,
                        message_id=message_id,
                        index=attachment.index,
                        filename=filename,
                        stored_path=existing_path,
                        digest=digest,
                        file_kind=file_kind,
                        status="duplicate",
                        created_at=created_at,
                        error_message="MD-Datei wurde bereits früher verarbeitet.",
                    )
                    md_relevant = True
                    result["duplicates"] += 1
                    continue

                temporary_path = temporary_dir / f"{attachment.index:02d}"
                temporary_path.write_bytes(attachment.content)
                if file_kind == "md_pdf":
                    try:
                        inspection = inspect_pdf(temporary_path)
                        is_feedback = inspection.data.get("document", "").upper() == "FEEDBACK"
                        if is_feedback:
                            imported = import_feedback_pdf(
                                connection,
                                path=temporary_path,
                                original_filename=filename,
                                accepted_dir=pdf_dir / "feedback",
                                source_message_id=message_id,
                                received_at=received_at,
                            )
                        else:
                            imported = import_official_pdf(
                                connection,
                                path=temporary_path,
                                original_filename=filename,
                                accepted_dir=pdf_dir,
                                handoff_dir=handoff_dir,
                                received_at=message.received_at,
                            )
                    except Exception as exc:
                        try:
                            has_md_data = bool(inspect_pdf(temporary_path).data)
                        except Exception:
                            has_md_data = False
                        if hint or has_md_data:
                            message_dir.mkdir(parents=True, exist_ok=True)
                            safe_name = secure_filename(filename) or f"Anhang-{attachment.index}"
                            stored_path = message_dir / f"{attachment.index:02d}_{safe_name}"
                            shutil.move(str(temporary_path), str(stored_path))
                            _insert_attachment(
                                connection,
                                message_id=message_id,
                                index=attachment.index,
                                filename=filename,
                                stored_path=str(stored_path),
                                digest=digest,
                                file_kind=file_kind,
                                status="review_required",
                                created_at=created_at,
                                error_message=str(exc),
                            )
                            md_relevant = True
                            needs_review = True
                            result["stored"] += 1
                        else:
                            foreign_attachments.append((attachment, filename, digest))
                    else:
                        if is_feedback:
                            stored_path = imported["stored_path"]
                        else:
                            document = connection.execute(
                                "SELECT stored_path FROM official_documents WHERE id = ?",
                                (imported["document_id"],),
                            ).fetchone()
                            stored_path = document["stored_path"]
                        _insert_attachment(
                            connection,
                            message_id=message_id,
                            index=attachment.index,
                            filename=filename,
                            stored_path=stored_path,
                            digest=digest,
                            file_kind=file_kind,
                            status="imported",
                            created_at=created_at,
                        )
                        if not is_feedback:
                            connection.execute(
                                """
                                UPDATE inbound_mail_attachments
                                SET official_document_id = ?
                                WHERE mail_message_id = ? AND attachment_index = ?
                                """,
                                (imported["document_id"], message_id, attachment.index),
                            )
                        connection.commit()
                        md_relevant = True
                        result["stored"] += 1
                elif hint:
                    message_dir.mkdir(parents=True, exist_ok=True)
                    safe_name = secure_filename(filename) or f"Anhang-{attachment.index}"
                    stored_path = message_dir / f"{attachment.index:02d}_{safe_name}"
                    shutil.move(str(temporary_path), str(stored_path))
                    _insert_attachment(
                        connection,
                        message_id=message_id,
                        index=attachment.index,
                        filename=filename,
                        stored_path=str(stored_path),
                        digest=digest,
                        file_kind=file_kind,
                        status="review_required",
                        created_at=created_at,
                        error_message="MD-bezogene, aber nicht automatisch verarbeitbare Datei.",
                    )
                    md_relevant = True
                    needs_review = True
                    result["stored"] += 1
                else:
                    foreign_attachments.append((attachment, filename, digest))

        try:
            bundles = create_feedback_bundles_for_message(
                connection,
                message_id=message_id,
                handoff_dir=handoff_dir,
                created_at=created_at,
            )
        except Exception as exc:
            connection.execute(
                """
                UPDATE inbound_mail_attachments
                SET status = 'review_required', error_message = ?
                WHERE mail_message_id = ? AND stored_path IN (
                    SELECT stored_path FROM feedback_submissions
                    WHERE source_message_id = ? AND bundle_id IS NULL
                )
                """,
                (str(exc), message_id, message_id),
            )
            connection.commit()
            needs_review = True
            result["errors"].append(str(exc))
        else:
            result["feedback_bundles"] += len(bundles)

        if not md_relevant:
            connection.execute("DELETE FROM inbound_mail_messages WHERE id = ?", (message_id,))
            connection.execute(
                """
                INSERT OR IGNORE INTO ignored_mail_messages (
                    outlook_entry_id, internet_message_id, ignored_at
                ) VALUES (?, ?, ?)
                """,
                (entry_id, message.internet_message_id or "", created_at),
            )
            connection.commit()
            if message_dir.exists():
                shutil.rmtree(message_dir)
            result["ignored"] += 1
            continue

        for attachment, filename, digest in foreign_attachments:
            _insert_attachment(
                connection,
                message_id=message_id,
                index=attachment.index,
                filename=filename,
                stored_path="",
                digest=digest,
                file_kind="other",
                status="review_required",
                created_at=created_at,
                error_message=(
                    "Fremdanlage nicht gespeichert. Die MD-Dokumente dieser E-Mail "
                    "wurden bereits verarbeitet; bitte nur diese Fremdanlage manuell prüfen."
                ),
            )
            needs_review = True

        if needs_review:
            message_status = "review_required"
            result["review"] += 1
        else:
            message_status = "ready_to_move"
            result["ready"] += 1
        connection.execute(
            """
            UPDATE inbound_mail_messages
            SET status = ?, contains_probation = ?, updated_at = ?
            WHERE id = ?
            """,
            (message_status, int(contains_probation), created_at, message_id),
        )
        connection.commit()
        if message_status == "ready_to_move" and move_message is not None:
            try:
                new_entry_id = move_message(entry_id, target_folder)
            except Exception as exc:
                connection.execute(
                    """
                    UPDATE inbound_mail_messages
                    SET error_message = ?, updated_at = ? WHERE id = ?
                    """,
                    (str(exc), created_at, message_id),
                )
                connection.commit()
                result["errors"].append(str(exc))
            else:
                connection.execute(
                    """
                    UPDATE inbound_mail_messages
                    SET outlook_entry_id = ?, status = 'moved', updated_at = ? WHERE id = ?
                    """,
                    (new_entry_id or entry_id, created_at, message_id),
                )
                connection.commit()
                result["moved"] += 1
    return result


def scan_outlook_inbox(
    connection: sqlite3.Connection,
    *,
    mailbox_name: str,
    target_folder: str,
    inbox_dir: Path,
    pdf_dir: Path,
    handoff_dir: Path,
    adapter: OutlookInboxAdapter | None = None,
) -> dict[str, Any]:
    outlook = adapter or OutlookInboxAdapter()
    messages = outlook.read_messages(mailbox_name=mailbox_name)
    return process_inbound_messages(
        connection,
        messages=messages,
        inbox_dir=inbox_dir,
        pdf_dir=pdf_dir,
        handoff_dir=handoff_dir,
        target_folder=target_folder,
        move_message=lambda entry_id, folder: outlook.move_message(
            mailbox_name=mailbox_name,
            entry_id=entry_id,
            target_folder=folder,
        ),
    )


def resolve_inbound_message(
    connection: sqlite3.Connection,
    *,
    message_id: int,
    mailbox_name: str,
    target_folder: str,
    adapter: OutlookInboxAdapter | None = None,
) -> dict[str, Any]:
    message = connection.execute(
        "SELECT * FROM inbound_mail_messages WHERE id = ?", (message_id,)
    ).fetchone()
    if not message:
        raise LookupError("Die Outlook-Nachricht wurde nicht gefunden.")
    if message["status"] not in {"review_required", "ready_to_move", "failed"}:
        raise ValueError("Diese Outlook-Nachricht ist bereits erledigt.")
    outlook = adapter or OutlookInboxAdapter()
    new_entry_id = outlook.move_message(
        mailbox_name=mailbox_name,
        entry_id=message["outlook_entry_id"],
        target_folder=target_folder,
    )
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    connection.execute(
        """
        UPDATE inbound_mail_messages
        SET outlook_entry_id = ?, status = 'moved', error_message = '', updated_at = ?
        WHERE id = ?
        """,
        (new_entry_id or message["outlook_entry_id"], timestamp, message_id),
    )
    connection.commit()
    return {"id": message_id, "status": "moved", "target_folder": target_folder}


def mail_inbox_overview(
    connection: sqlite3.Connection,
    *,
    page: int = 1,
    query: str = "",
    status: str = "",
    per_page: int = 50,
) -> dict[str, Any]:
    page = max(1, page)
    where: list[str] = []
    params: list[Any] = []
    query = query.strip()
    if query:
        where.append("(m.sender_email LIKE ? OR m.subject LIKE ?)")
        params.extend((f"%{query}%", f"%{query}%"))
    if status in STATUS_LABELS:
        where.append("m.status = ?")
        params.append(status)
    condition = "WHERE " + " AND ".join(where) if where else ""
    total = connection.execute(
        f"SELECT COUNT(*) AS count FROM inbound_mail_messages m {condition}", params
    ).fetchone()["count"]
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, pages)
    message_rows = connection.execute(
        f"""
        SELECT m.*,
               COUNT(a.id) AS attachment_count,
               SUM(CASE WHEN a.status = 'review_required' THEN 1 ELSE 0 END) AS review_count
        FROM inbound_mail_messages m
        LEFT JOIN inbound_mail_attachments a ON a.mail_message_id = m.id
        {condition}
        GROUP BY m.id
        ORDER BY m.received_at DESC, m.id DESC
        LIMIT ? OFFSET ?
        """,
        (*params, per_page, (page - 1) * per_page),
    ).fetchall()
    messages: list[dict[str, Any]] = []
    for row in message_rows:
        item = dict(row)
        item["status_label"] = STATUS_LABELS.get(item["status"], item["status"])
        item["attachments"] = [
            dict(attachment)
            for attachment in connection.execute(
                """
                SELECT * FROM inbound_mail_attachments
                WHERE mail_message_id = ? ORDER BY attachment_index
                """,
                (item["id"],),
            ).fetchall()
        ]
        messages.append(item)
    counts = {
        row["status"]: row["count"]
        for row in connection.execute(
            "SELECT status, COUNT(*) AS count FROM inbound_mail_messages GROUP BY status"
        ).fetchall()
    }
    return {
        "mail_messages": messages,
        "mail_status_counts": counts,
        "mail_total": total,
        "mail_page": page,
        "mail_pages": pages,
        "mail_query": query,
        "selected_mail_status": status,
        "mail_status_labels": STATUS_LABELS,
    }
