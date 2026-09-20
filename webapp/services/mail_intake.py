"""Sichert und klassifiziert eingehende Outlook-Nachrichten idempotent."""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from werkzeug.utils import secure_filename

from webapp.adapters.outlook import InboundMessage, OutlookInboxAdapter
from webapp.services.documents import import_official_pdf
from webapp.services.packages import import_returned_package


STATUS_LABELS = {
    "new": "Neu",
    "ready_to_move": "Vollständig gesichert",
    "review_required": "HR-Prüfung erforderlich",
    "moved": "In Outlook verschoben",
    "ignored": "Ohne Anhang",
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
) -> dict[str, Any]:
    """Sichert alle Anhänge; verändert oder löscht keine Outlook-Nachricht."""
    result: dict[str, Any] = {
        "read": 0,
        "stored": 0,
        "ready": 0,
        "review": 0,
        "ignored": 0,
        "duplicates": 0,
        "failed": 0,
        "errors": [],
    }
    inbox_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

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

        if not message.attachments:
            connection.execute(
                "UPDATE inbound_mail_messages SET status = 'ignored', updated_at = ? WHERE id = ?",
                (created_at, message_id),
            )
            connection.commit()
            result["ignored"] += 1
            continue

        message_dir = inbox_dir / f"mail-{message_id:06d}"
        message_dir.mkdir(parents=True, exist_ok=True)
        needs_review = False
        contains_probation = False

        for attachment in message.attachments:
            filename = Path(attachment.filename or f"Anhang-{attachment.index}").name
            safe_name = secure_filename(filename) or f"Anhang-{attachment.index}"
            digest = hashlib.sha256(attachment.content).hexdigest()
            file_kind = _kind(filename)
            existing_path = _existing_attachment_path(connection, digest)
            probation = "probezeit" in f"{filename} {message.subject}".lower()
            contains_probation = contains_probation or probation
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
                    error_message="Datei wurde bereits früher gesichert.",
                )
                result["duplicates"] += 1
                if probation:
                    needs_review = True
                continue

            stored_path = message_dir / f"{attachment.index:02d}_{safe_name}"
            stored_path.write_bytes(attachment.content)
            attachment_id = _insert_attachment(
                connection,
                message_id=message_id,
                index=attachment.index,
                filename=filename,
                stored_path=str(stored_path),
                digest=digest,
                file_kind=file_kind,
                status="stored",
                created_at=created_at,
            )
            result["stored"] += 1

            if file_kind == "other":
                status = "review_required"
                error = "Zusätzliche oder nicht unterstützte Datei – HR-Prüfung erforderlich."
                needs_review = True
            else:
                try:
                    if file_kind == "md_pdf":
                        imported = import_official_pdf(
                            connection,
                            path=stored_path,
                            original_filename=filename,
                            accepted_dir=pdf_dir,
                            received_at=message.received_at,
                        )
                        document = connection.execute(
                            "SELECT stored_path FROM official_documents WHERE id = ?",
                            (imported["document_id"],),
                        ).fetchone()
                        connection.execute(
                            """
                            UPDATE inbound_mail_attachments
                            SET official_document_id = ?, stored_path = ?
                            WHERE id = ?
                            """,
                            (imported["document_id"], document["stored_path"], attachment_id),
                        )
                    else:
                        import_returned_package(
                            connection, path=stored_path, original_filename=filename
                        )
                    status = "imported"
                    error = ""
                except Exception as exc:
                    status = "review_required"
                    error = str(exc)
                    needs_review = True
            if probation:
                needs_review = True
            connection.execute(
                """
                UPDATE inbound_mail_attachments
                SET status = ?, error_message = ? WHERE id = ?
                """,
                (status, error, attachment_id),
            )
            connection.commit()

        if needs_review or contains_probation:
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
    return result


def scan_outlook_inbox(
    connection: sqlite3.Connection,
    *,
    mailbox_name: str,
    target_folder: str,
    inbox_dir: Path,
    pdf_dir: Path,
    adapter: OutlookInboxAdapter | None = None,
) -> dict[str, Any]:
    outlook = adapter or OutlookInboxAdapter()
    messages = outlook.read_messages(mailbox_name=mailbox_name)
    return process_inbound_messages(
        connection,
        messages=messages,
        inbox_dir=inbox_dir,
        pdf_dir=pdf_dir,
        target_folder=target_folder,
    )


def mail_inbox_overview(connection: sqlite3.Connection) -> dict[str, Any]:
    message_rows = connection.execute(
        """
        SELECT m.*,
               COUNT(a.id) AS attachment_count,
               SUM(CASE WHEN a.status = 'review_required' THEN 1 ELSE 0 END) AS review_count
        FROM inbound_mail_messages m
        LEFT JOIN inbound_mail_attachments a ON a.mail_message_id = m.id
        GROUP BY m.id
        ORDER BY m.received_at DESC, m.id DESC
        LIMIT 100
        """
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
    return {"mail_messages": messages, "mail_status_counts": counts}
