"""Fachlogik für Versandvorschau und sicher vorbereitete Outlook-Entwürfe."""

from __future__ import annotations

import html
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from webapp.adapters.outlook import OutlookDraftAdapter


DEFAULT_SENDER = "hr@vd.zh.ch"


def _message_text(row: sqlite3.Row, *, sender_email: str = DEFAULT_SENDER) -> tuple[str, str]:
    years = f"{row['review_year']}/{row['outlook_year']}"
    if row["package_kind"] == "update":
        subject = f"Mitarbeitenden-Dialog {years}: Update Ihrer Arbeitsmappe"
        introduction = (
            "Für Ihre bestehende Arbeitsmappe liegt ein Update vor. Öffnen Sie Ihre "
            "zuletzt gespeicherte Arbeitsmappe und wählen Sie dort «Update einlesen»."
        )
    else:
        subject = f"Mitarbeitenden-Dialog {years}: Ihre Arbeitsmappe"
        introduction = (
            "Im Anhang erhalten Sie Ihre persönliche Arbeitsmappe für den "
            f"Mitarbeitenden-Dialog {years}."
        )
    manager_name = html.escape(row["manager_name"] or f"PN {row['manager_pn']}")
    review_due = html.escape(row["review_due_date"] or "noch nicht festgelegt")
    outlook_due = html.escape(row["outlook_due_date"] or "noch nicht festgelegt")
    body = f"""
    <p>Guten Tag {manager_name}</p>
    <p>{html.escape(introduction)}</p>
    <p><strong>Fristen</strong><br>
    Rückblick: {review_due}<br>
    Ausblick: {outlook_due}</p>
    <p>Bitte speichern und bearbeiten Sie die Datei ausschliesslich auf Ihrem
    persönlichen Geschäftsgerät. Die Arbeitsmappe bleibt bei Ihnen. An HR senden
    Sie nur die daraus erzeugten und elektronisch unterzeichneten PDFs zurück.</p>
    <p>Bei einer Gesamtbeurteilung D oder E sowie bei Uneinigkeit ist zusätzlich
    ein handschriftlich unterzeichneter Scan erforderlich. Rücksendungen an
    <a href="mailto:{html.escape(sender_email)}">{html.escape(sender_email)}</a> müssen ebenfalls
    S/MIME-verschlüsselt erfolgen.</p>
    <p>Freundliche Grüsse<br>Human Resources</p>
    """
    return subject, "".join(line.strip() for line in body.splitlines())


def dispatch_candidates(
    connection: sqlite3.Connection, *, cycle_id: int, sender_email: str = DEFAULT_SENDER
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        WITH latest AS (
            SELECT manager_pn, MAX(id) AS package_event_id
            FROM package_events
            WHERE cycle_id = ? AND direction = 'versand'
            GROUP BY manager_pn
        )
        SELECT pe.id AS package_event_id, pe.package_kind, pe.filename,
               pe.stored_path, pe.created_at AS package_created_at,
               pe.manager_pn, c.review_year, c.outlook_year,
               c.review_due_date, c.outlook_due_date,
               COALESCE(NULLIF(TRIM(e.first_name || ' ' || e.last_name), ''),
                        'PN ' || pe.manager_pn) AS manager_name,
               e.email AS recipient_email, e.org_unit,
               md.id AS delivery_id, md.status AS delivery_status,
               md.encryption_flag_verified, md.updated_at AS delivery_updated_at,
               md.error_message
        FROM latest l
        JOIN package_events pe ON pe.id = l.package_event_id
        JOIN cycles c ON c.id = pe.cycle_id
        LEFT JOIN employees e ON e.pn = pe.manager_pn
        LEFT JOIN mail_deliveries md ON md.package_event_id = pe.id
        ORDER BY manager_name, pe.manager_pn
        """,
        (cycle_id,),
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        subject, body_html = _message_text(row, sender_email=sender_email)
        item["subject"] = subject
        item["body_html"] = body_html
        item["file_available"] = bool(
            item["stored_path"] and Path(item["stored_path"]).is_file()
        )
        item["ready"] = bool(item["recipient_email"] and item["file_available"])
        result.append(item)
    return result


def create_outlook_drafts(
    connection: sqlite3.Connection,
    *,
    cycle_id: int,
    package_event_ids: list[int],
    sender_email: str = DEFAULT_SENDER,
    adapter: OutlookDraftAdapter | None = None,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    selected = {int(value) for value in package_event_ids}
    if not selected:
        raise ValueError("Bitte wähle mindestens eine vorbereitete Nachricht aus.")
    candidates = {
        row["package_event_id"]: row
        for row in dispatch_candidates(
            connection, cycle_id=cycle_id, sender_email=sender_email
        )
        if row["package_event_id"] in selected
    }
    missing_ids = selected.difference(candidates)
    if missing_ids:
        raise ValueError("Mindestens eine gewählte Versanddatei ist nicht mehr aktuell.")
    outlook = adapter or OutlookDraftAdapter()
    timestamp = (created_at or datetime.now().astimezone()).isoformat(timespec="seconds")
    results = {"created": 0, "failed": 0, "errors": []}
    for event_id in sorted(selected):
        candidate = candidates[event_id]
        if not candidate["recipient_email"]:
            error = "Geschäftliche E-Mail-Adresse fehlt."
        elif not candidate["file_available"]:
            error = "Die vorbereitete Versanddatei wurde nicht gefunden."
        else:
            error = ""
        connection.execute(
            """
            INSERT INTO mail_deliveries (
                package_event_id, sender_email, recipient_email, subject,
                body_html, status, encryption_required,
                encryption_flag_verified, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'prepared', 1, 0, ?, ?)
            ON CONFLICT(package_event_id) DO UPDATE SET
                sender_email = excluded.sender_email,
                recipient_email = excluded.recipient_email,
                subject = excluded.subject,
                body_html = excluded.body_html,
                updated_at = excluded.updated_at
            """,
            (
                event_id, sender_email, candidate["recipient_email"] or "",
                candidate["subject"], candidate["body_html"], timestamp, timestamp,
            ),
        )
        if error:
            connection.execute(
                """
                UPDATE mail_deliveries
                SET status = 'failed', error_message = ?, updated_at = ?
                WHERE package_event_id = ?
                """,
                (error, timestamp, event_id),
            )
            results["failed"] += 1
            results["errors"].append(f"{candidate['manager_name']}: {error}")
            continue
        try:
            draft = outlook.create_encrypted_draft(
                sender_email=sender_email,
                recipient_email=candidate["recipient_email"],
                subject=candidate["subject"],
                body_html=candidate["body_html"],
                attachments=[Path(candidate["stored_path"])],
            )
        except Exception as exc:
            error = str(exc)
            connection.execute(
                """
                UPDATE mail_deliveries
                SET status = 'failed', encryption_flag_verified = 0,
                    error_message = ?, updated_at = ?
                WHERE package_event_id = ?
                """,
                (error, timestamp, event_id),
            )
            results["failed"] += 1
            results["errors"].append(f"{candidate['manager_name']}: {error}")
        else:
            if not draft.encryption_flag_verified:
                error = "Unsicherer Adapterzustand: Verschlüsselungsmarkierung nicht bestätigt."
                connection.execute(
                    """
                    UPDATE mail_deliveries
                    SET status = 'failed', encryption_flag_verified = 0,
                        error_message = ?, updated_at = ?
                    WHERE package_event_id = ?
                    """,
                    (error, timestamp, event_id),
                )
                results["failed"] += 1
                results["errors"].append(f"{candidate['manager_name']}: {error}")
                continue
            connection.execute(
                """
                UPDATE mail_deliveries
                SET status = 'draft_created', encryption_flag_verified = 1,
                    outlook_entry_id = ?, error_message = '', updated_at = ?
                WHERE package_event_id = ?
                """,
                (draft.entry_id, timestamp, event_id),
            )
            results["created"] += 1
    connection.commit()
    return results
