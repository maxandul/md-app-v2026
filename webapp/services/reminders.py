"""Überfällige Pflichten und sichere Outlook-Erinnerungsentwürfe."""

from __future__ import annotations

import html
import sqlite3
from datetime import date, datetime
from typing import Any

from webapp.adapters.outlook import OutlookDraftAdapter
from webapp.services.mail_dispatch import DEFAULT_SENDER, configured_sender


def _message(candidate: dict[str, Any], sender_email: str) -> tuple[str, str]:
    subject = f"Mitarbeitenden-Dialog: Erinnerung an {candidate['overdue_count']} überfällige Unterlage(n)"
    name = html.escape(candidate["manager_name"])
    oldest = html.escape(candidate["oldest_due_date"])
    kinds = html.escape(candidate["document_kinds"])
    details = ''.join('<li>'+html.escape(value)+'</li>' for value in candidate.get('missing_details', []))
    body = f"""
    <p>Guten Tag {name}</p>
    <p>Für deine Mitarbeitenden sind noch {candidate['overdue_count']} Unterlage(n)
    zum Mitarbeitenden-Dialog überfällig. Bereits bei HR eingegangene Unterlagen werden nicht nochmals angefordert. Die älteste Frist war am {oldest}.</p>
    <p><strong>Betroffene Dokumentarten:</strong> {kinds}</p>
    <ul>{details}</ul>
    <p>Bitte sende die fehlenden PDFs mit den gemäss Formular erforderlichen Unterschriften an
    <a href="mailto:{html.escape(sender_email)}">{html.escape(sender_email)}</a>.
    Bei einer offenen Scanpflicht benötigen wir den handschriftlich unterzeichneten Scan.
    Rücksendungen müssen S/MIME-verschlüsselt erfolgen.</p>
    <p>Freundliche Grüsse<br>Human Resources</p>
    """
    return subject, "".join(line.strip() for line in body.splitlines())


def reminder_candidates(
    connection: sqlite3.Connection, *, cycle_id: int, today: date | None = None,
    sender_email: str = DEFAULT_SENDER,
) -> list[dict[str, Any]]:
    cutoff = (today or date.today()).isoformat()
    rows = connection.execute(
        """
        WITH overdue AS (
            SELECT ma.manager_person_number AS manager_pn, o.id AS obligation_id,
                   o.document_kind, o.due_date
            FROM document_obligations o
            JOIN dialog_events de ON de.id = o.dialog_event_id
            JOIN manager_assignments ma ON ma.id = de.manager_assignment_id
            WHERE de.cycle_id = ? AND o.required = 1
              AND o.status IN ('open', 'rejected', 'scan_pending') AND de.status <> 'cancelled'
              AND o.due_date <> '' AND o.due_date < ?
        ), latest AS (
            SELECT manager_pn, MAX(id) AS reminder_id
            FROM reminders WHERE cycle_id = ? GROUP BY manager_pn
        )
        SELECT od.manager_pn, COUNT(*) AS overdue_count,
               MIN(od.due_date) AS oldest_due_date,
               SUM(CASE WHEN od.document_kind = 'review' THEN 1 ELSE 0 END) AS review_count,
               SUM(CASE WHEN od.document_kind = 'outlook' THEN 1 ELSE 0 END) AS outlook_count,
               COALESCE(NULLIF(TRIM(e.first_name || ' ' || e.last_name), ''),
                        NULLIF(TRIM(p.first_name || ' ' || p.last_name), ''),
                        'PN ' || od.manager_pn) AS manager_name,
               COALESCE(NULLIF(e.email, ''), p.email, '') AS recipient_email,
               r.id AS latest_reminder_id, r.status AS latest_status,
               r.updated_at AS latest_updated_at, r.error_message
        FROM overdue od
        LEFT JOIN employees e ON e.pn = od.manager_pn
        LEFT JOIN persons p ON p.person_number = od.manager_pn
        LEFT JOIN latest l ON l.manager_pn = od.manager_pn
        LEFT JOIN reminders r ON r.id = l.reminder_id
        GROUP BY od.manager_pn
        ORDER BY manager_name, od.manager_pn
        """,
        (cycle_id, cutoff, cycle_id),
    ).fetchall()
    from .hr_workflow import pending_pdfs
    review_pending = bool(pending_pdfs(connection))
    result = []
    for row in rows:
        item = dict(row)
        kinds = []
        if item["review_count"]:
            kinds.append(f"Rückblick ({item['review_count']})")
        if item["outlook_count"]:
            kinds.append(f"Ausblick ({item['outlook_count']})")
        item["document_kinds"] = ", ".join(kinds)
        item["draft_open"] = item["latest_status"] == "draft_created"
        item["ready"] = bool(item["recipient_email"] and not item["draft_open"] and not review_pending)
        item['readiness_error'] = 'Zuerst den offenen PDF-Eingang prüfen; er könnte bereits gesuchte Unterlagen enthalten.' if review_pending else ''
        details = connection.execute("""SELECT p.first_name,p.last_name,ea.person_number,ea.assignment_number,o.document_kind,o.status,o.due_date
            FROM document_obligations o JOIN dialog_events de ON de.id=o.dialog_event_id
            JOIN employment_assignments ea ON ea.id=de.employment_id JOIN persons p ON p.person_number=ea.person_number
            JOIN manager_assignments ma ON ma.id=de.manager_assignment_id
            WHERE de.cycle_id=? AND ma.manager_person_number=? AND o.required=1
              AND o.status IN ('open','rejected','scan_pending') AND de.status<>'cancelled'
              AND o.due_date<>'' AND o.due_date<? ORDER BY p.last_name,p.first_name,o.id""",(cycle_id,item['manager_pn'],cutoff)).fetchall()
        item['missing_details'] = [f"{d['first_name']} {d['last_name']} (PN {d['person_number']}, Ans. {d['assignment_number']}): "
            f"{'Rückblick' if d['document_kind']=='review' else 'Ausblick'} – "
            f"{ {'open':'noch ausstehend','rejected':'Korrektur erforderlich','scan_pending':'unterschriebener Scan ausstehend'}[d['status']] }, Frist {d['due_date']}" for d in details]
        item["subject"], item["body_html"] = _message(item, sender_email)
        item["obligation_ids"] = [
            value["id"] for value in connection.execute(
                """
                SELECT o.id FROM document_obligations o
                JOIN dialog_events de ON de.id = o.dialog_event_id
                JOIN manager_assignments ma ON ma.id = de.manager_assignment_id
                WHERE de.cycle_id = ? AND ma.manager_person_number = ?
                  AND o.required = 1 AND o.status IN ('open', 'rejected', 'scan_pending') AND de.status <> 'cancelled'
                  AND o.due_date <> '' AND o.due_date < ?
                ORDER BY o.id
                """,
                (cycle_id, item["manager_pn"], cutoff),
            ).fetchall()
        ]
        result.append(item)
    return result


def create_reminder_drafts(
    connection: sqlite3.Connection, *, cycle_id: int, manager_pns: list[str],
    sender_email: str = DEFAULT_SENDER, adapter: OutlookDraftAdapter | None = None,
    created_at: datetime | None = None, today: date | None = None,
) -> dict[str, Any]:
    sender_email = configured_sender(sender_email)
    from .hr_workflow import pending_pdfs
    if pending_pdfs(connection):
        raise ValueError('Erinnerungen pausiert: Bitte zuerst alle offenen PDF-Eingänge prüfen oder begründet zurückstellen. So werden eingereichte Unterlagen nicht nochmals angefordert.')
    selected = {value.strip() for value in manager_pns if value.strip()}
    if not selected:
        raise ValueError("Bitte wähle mindestens eine überfällige Führungskraft aus.")
    available = {
        item["manager_pn"]: item for item in reminder_candidates(
            connection, cycle_id=cycle_id, today=today, sender_email=sender_email
        ) if item["manager_pn"] in selected
    }
    if selected.difference(available):
        raise ValueError("Mindestens eine Auswahl ist nicht mehr überfällig oder gültig.")
    if any(item["draft_open"] for item in available.values()):
        raise ValueError("Für mindestens eine Auswahl besteht bereits ein offener Entwurf.")

    outlook = adapter or OutlookDraftAdapter()
    timestamp = (created_at or datetime.now().astimezone()).isoformat(timespec="seconds")
    results = {"created": 0, "failed": 0, "errors": []}
    for manager_pn in sorted(selected):
        item = available[manager_pn]
        cursor = connection.execute(
            """
            INSERT INTO reminders (
                cycle_id, manager_pn, sender_email, recipient_email, subject,
                body_html, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'prepared', ?, ?)
            """,
            (
                cycle_id, manager_pn, sender_email, item["recipient_email"] or "",
                item["subject"], item["body_html"], timestamp, timestamp,
            ),
        )
        reminder_id = cursor.lastrowid
        for obligation_id in item["obligation_ids"]:
            due_date = connection.execute(
                "SELECT due_date FROM document_obligations WHERE id = ?", (obligation_id,)
            ).fetchone()["due_date"]
            connection.execute(
                "INSERT INTO reminder_obligations VALUES (?, ?, ?)",
                (reminder_id, obligation_id, due_date),
            )
        error = "" if item["recipient_email"] else "Geschäftliche E-Mail-Adresse fehlt."
        if not error:
            try:
                draft = outlook.create_encrypted_draft(
                    sender_email=sender_email,
                    recipient_email=item["recipient_email"],
                    subject=item["subject"], body_html=item["body_html"], attachments=[],
                )
                if not draft.encryption_flag_verified:
                    error = "Unsicherer Adapterzustand: Verschlüsselungsmarkierung nicht bestätigt."
            except Exception as exc:
                error = str(exc)
        if error:
            connection.execute(
                "UPDATE reminders SET status = 'failed', error_message = ?, updated_at = ? WHERE id = ?",
                (error, timestamp, reminder_id),
            )
            results["failed"] += 1
            results["errors"].append(f"{item['manager_name']}: {error}")
        else:
            connection.execute(
                """
                UPDATE reminders SET status = 'draft_created', encryption_flag_verified = 1,
                    outlook_entry_id = ?, updated_at = ? WHERE id = ?
                """,
                (draft.entry_id, timestamp, reminder_id),
            )
            results["created"] += 1
    connection.commit()
    return results


def confirm_reminder_sent(
    connection: sqlite3.Connection, *, reminder_id: int,
    confirmed_at: datetime | None = None,
) -> sqlite3.Row:
    reminder = connection.execute(
        "SELECT * FROM reminders WHERE id = ?", (reminder_id,)
    ).fetchone()
    if not reminder:
        raise LookupError("Erinnerung nicht gefunden.")
    if reminder["status"] != "draft_created" or not reminder["encryption_flag_verified"]:
        raise ValueError("Nur ein geprüfter Outlook-Entwurf kann als versendet bestätigt werden.")
    timestamp = (confirmed_at or datetime.now().astimezone()).isoformat(timespec="seconds")
    connection.execute(
        "UPDATE reminders SET status = 'sent_confirmed', updated_at = ? WHERE id = ?",
        (timestamp, reminder_id),
    )
    connection.commit()
    return connection.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
