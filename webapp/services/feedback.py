"""Verarbeitet Feedbacks an vorgesetzte Personen ohne Mahnlogik."""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import unicodedata
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from webapp.services.documents import file_sha256, inspect_pdf


def _required(data: dict[str, str], key: str) -> str:
    value = str(data.get(key, "")).strip()
    if not value:
        raise ValueError(f"Im Feedback-Datenblock fehlt «{key}».")
    return value


def _filename_part(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_") or "Unbekannt"


def _case_row(connection: sqlite3.Connection, case_id: str) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT dc.case_id, dc.cycle_id, dc.employee_pn, dc.manager_pn,
               c.review_year, c.outlook_year,
               employee.first_name AS employee_first_name,
               employee.last_name AS employee_last_name,
               manager.first_name AS manager_first_name,
               manager.last_name AS manager_last_name
        FROM dialog_cases dc
        JOIN cycles c ON c.id = dc.cycle_id
        JOIN employees employee ON employee.pn = dc.employee_pn
        LEFT JOIN employees manager ON manager.pn = dc.manager_pn
        WHERE dc.case_id = ?
        """,
        (case_id,),
    ).fetchone()
    if not row:
        raise ValueError("Die Fall-ID des Feedbacks ist in dieser Datenbank nicht vorhanden.")
    return row


def import_feedback_pdf(
    connection: sqlite3.Connection,
    *,
    path: Path,
    original_filename: str,
    accepted_dir: Path,
    source_message_id: int,
    received_at: str,
) -> dict[str, Any]:
    """Sichert ein Feedback-PDF und ordnet es der Führungskraft zu."""
    inspection = inspect_pdf(path)
    data = inspection.data
    if data.get("document", "").upper() != "FEEDBACK":
        raise ValueError("Das PDF ist kein Feedback an eine vorgesetzte Person.")

    case = _case_row(connection, _required(data, "case_id"))
    if _required(data, "pn") != case["employee_pn"]:
        raise ValueError("Die Personalnummer im Feedback stimmt nicht mit der Fall-ID überein.")
    if _required(data, "manager_pn") != case["manager_pn"]:
        raise ValueError("Die vorgesetzte Person im Feedback stimmt nicht mit dem MD-Fall überein.")
    if int(_required(data, "year")) != int(case["review_year"]):
        raise ValueError("Das Feedbackjahr stimmt nicht mit dem Jahresprozess überein.")

    sent = connection.execute(
        """
        SELECT id FROM package_events
        WHERE package_id = ? AND cycle_id = ? AND manager_pn = ?
          AND direction = 'versand'
        ORDER BY id DESC LIMIT 1
        """,
        (_required(data, "package_id"), case["cycle_id"], case["manager_pn"]),
    ).fetchone()
    if not sent:
        raise ValueError("Die Paket-ID des Feedbacks ist nicht als Versand registriert.")

    digest = file_sha256(path)
    if connection.execute(
        "SELECT id FROM feedback_submissions WHERE sha256 = ?", (digest,)
    ).fetchone():
        raise ValueError("Dieses Feedback wurde bereits importiert.")

    accepted_dir.mkdir(parents=True, exist_ok=True)
    stored_path = accepted_dir / (
        f"{received_at[:19].replace(':', '').replace('-', '')}_{digest[:10]}_"
        f"{Path(original_filename).name}"
    )
    shutil.move(str(path), str(stored_path))
    try:
        cursor = connection.execute(
            """
            INSERT INTO feedback_submissions (
                cycle_id, case_id, employee_pn, manager_pn, source_message_id,
                original_filename, stored_path, sha256, data_block_json, received_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case["cycle_id"], case["case_id"], case["employee_pn"],
                case["manager_pn"], source_message_id, original_filename,
                str(stored_path), digest, json.dumps(data, ensure_ascii=False), received_at,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        if stored_path.exists() and not path.exists():
            shutil.move(str(stored_path), str(path))
        raise
    return {
        "submission_id": int(cursor.lastrowid),
        "cycle_id": case["cycle_id"],
        "manager_pn": case["manager_pn"],
        "case_id": case["case_id"],
        "stored_path": str(stored_path),
    }


def _cover_page(*, manager_name: str, manager_pn: str, review_year: int, count: int) -> BytesIO:
    target = BytesIO()
    document = canvas.Canvas(target, pagesize=A4)
    width, height = A4
    document.setTitle(f"Feedback an {manager_name}")
    document.setFont("Helvetica-Bold", 10)
    document.setFillColorRGB(0.12, 0.31, 0.47)
    document.drawString(52, height - 62, "VOLKSWIRTSCHAFTSDIREKTION · MITARBEITENDEN-DIALOG")
    document.setFillColorRGB(0, 0, 0)
    document.setFont("Helvetica-Bold", 22)
    document.drawString(52, height - 112, f"Feedback {review_year}")
    document.setFont("Helvetica", 14)
    document.drawString(52, height - 143, f"an {manager_name}")
    document.setFillColorRGB(0.95, 0.96, 0.97)
    document.rect(52, height - 245, width - 104, 65, fill=1, stroke=0)
    document.setFillColorRGB(0, 0, 0)
    document.setFont("Helvetica-Bold", 10)
    document.drawString(68, height - 205, "Personalnummer der vorgesetzten Person")
    document.setFont("Helvetica", 11)
    document.drawString(68, height - 223, manager_pn)
    document.setFont("Helvetica-Bold", 10)
    document.drawString(305, height - 205, "Enthaltene Rückmeldungen")
    document.setFont("Helvetica", 11)
    document.drawString(305, height - 223, str(count))
    document.setFont("Helvetica", 9)
    document.setFillColorRGB(0.35, 0.35, 0.35)
    document.drawString(52, 62, "Die Rückmeldungen wurden im Rahmen des Mitarbeitenden-Dialogs eingereicht.")
    document.save()
    target.seek(0)
    return target


def create_feedback_bundles_for_message(
    connection: sqlite3.Connection,
    *,
    message_id: int,
    handoff_dir: Path,
    created_at: str,
) -> list[dict[str, Any]]:
    """Erstellt je Führungskraft ein Sammel-PDF aus einer eingegangenen Mail."""
    groups = connection.execute(
        """
        SELECT fs.cycle_id, fs.manager_pn, c.review_year,
               COALESCE(NULLIF(TRIM(m.first_name || ' ' || m.last_name), ''), fs.manager_pn) AS manager_name,
               COALESCE(m.first_name, '') AS manager_first_name,
               COALESCE(m.last_name, '') AS manager_last_name,
               COUNT(*) AS submission_count
        FROM feedback_submissions fs
        JOIN cycles c ON c.id = fs.cycle_id
        LEFT JOIN employees m ON m.pn = fs.manager_pn
        WHERE fs.source_message_id = ? AND fs.bundle_id IS NULL
        GROUP BY fs.cycle_id, fs.manager_pn, c.review_year, m.first_name, m.last_name
        """,
        (message_id,),
    ).fetchall()
    results: list[dict[str, Any]] = []
    handoff_dir.mkdir(parents=True, exist_ok=True)
    for group in groups:
        submissions = connection.execute(
            """
            SELECT * FROM feedback_submissions
            WHERE source_message_id = ? AND cycle_id = ? AND manager_pn = ?
              AND bundle_id IS NULL
            ORDER BY id
            """,
            (message_id, group["cycle_id"], group["manager_pn"]),
        ).fetchall()
        prior_count = connection.execute(
            """
            SELECT COUNT(*) AS count FROM feedback_bundles
            WHERE cycle_id = ? AND manager_pn = ?
            """,
            (group["cycle_id"], group["manager_pn"]),
        ).fetchone()["count"]
        suffix = "" if prior_count == 0 else f"_Nachtrag_{prior_count + 1}"
        filename = (
            f"Feedback_{group['review_year']}_"
            f"{_filename_part(group['manager_last_name'])}_"
            f"{_filename_part(group['manager_first_name'])}_"
            f"{_filename_part(group['manager_pn'])}{suffix}.pdf"
        )
        destination = handoff_dir / filename
        if destination.exists():
            raise ValueError(f"Im Roboter-Input existiert bereits «{filename}».")

        writer = PdfWriter()
        cover = _cover_page(
            manager_name=group["manager_name"], manager_pn=group["manager_pn"],
            review_year=group["review_year"], count=len(submissions),
        )
        for page in PdfReader(cover).pages:
            writer.add_page(page)
        for submission in submissions:
            for page in PdfReader(submission["stored_path"]).pages:
                writer.add_page(page)
        with destination.open("wb") as output:
            writer.write(output)
        digest = file_sha256(destination)
        try:
            cursor = connection.execute(
                """
                INSERT INTO feedback_bundles (
                    cycle_id, manager_pn, source_message_id, filename, stored_path,
                    sha256, submission_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    group["cycle_id"], group["manager_pn"], message_id, filename,
                    str(destination), digest, len(submissions), created_at,
                ),
            )
            bundle_id = int(cursor.lastrowid)
            connection.executemany(
                "UPDATE feedback_submissions SET bundle_id = ? WHERE id = ?",
                [(bundle_id, row["id"]) for row in submissions],
            )
            connection.commit()
        except Exception:
            connection.rollback()
            destination.unlink(missing_ok=True)
            raise
        results.append({
            "bundle_id": bundle_id,
            "cycle_id": group["cycle_id"],
            "manager_pn": group["manager_pn"],
            "filename": filename,
            "submission_count": len(submissions),
        })
    return results


def feedback_overview(
    connection: sqlite3.Connection, *, cycle_id: int | None = None
) -> list[dict[str, Any]]:
    where = "WHERE fb.cycle_id = ?" if cycle_id else ""
    params: tuple[Any, ...] = (cycle_id,) if cycle_id else ()
    return [
        dict(row)
        for row in connection.execute(
            f"""
            SELECT fb.*, c.review_year,
                   COALESCE(NULLIF(TRIM(e.first_name || ' ' || e.last_name), ''), fb.manager_pn) AS manager_name
            FROM feedback_bundles fb
            JOIN cycles c ON c.id = fb.cycle_id
            LEFT JOIN employees e ON e.pn = fb.manager_pn
            {where}
            ORDER BY fb.created_at DESC, fb.id DESC
            """,
            params,
        ).fetchall()
    ]
