"""Importiert den SAP-Excel-Export in normalisierte SQLite-Tabellen."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = {
    "ID_NO_ZERO",
    "Rufname",
    "Nachname",
    "Dir. Vorgesetzter (PN)",
    "lange ID/Nummer",
}


@dataclass(frozen=True)
class ImportResult:
    import_id: int
    row_count: int
    employee_count: int
    reporting_line_count: int
    warnings: list[str]


def clean(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return re.sub(r"\.0$", "", str(value).strip())


def iso_date(value: Any) -> str:
    if not clean(value):
        return ""
    try:
        return pd.Timestamp(value).date().isoformat()
    except (TypeError, ValueError):
        return ""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _first_value(rows: pd.DataFrame, column: str) -> str:
    if column not in rows:
        return ""
    for value in rows[column]:
        text = clean(value)
        if text:
            return text
    return ""


def _first_date(rows: pd.DataFrame, column: str) -> str:
    if column not in rows:
        return ""
    for value in rows[column]:
        text = iso_date(value)
        if text:
            return text
    return ""


def import_sap_workbook(
    connection: sqlite3.Connection,
    path: Path,
    *,
    original_filename: str,
    stored_filename: str,
    imported_at: datetime | None = None,
) -> ImportResult:
    imported_at = imported_at or datetime.now().astimezone()
    digest = file_sha256(path)
    duplicate = connection.execute(
        "SELECT id, imported_at FROM sap_imports WHERE sha256 = ? ORDER BY id DESC LIMIT 1",
        (digest,),
    ).fetchone()
    if duplicate:
        raise ValueError(
            f"Diese SAP-Datei wurde bereits importiert (Import {duplicate['id']} vom "
            f"{duplicate['imported_at']})."
        )

    frame = pd.read_excel(path, dtype=object)
    frame.columns = [str(column).strip() for column in frame.columns]
    missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Im SAP-Export fehlen Spalten: {', '.join(missing)}")

    frame["_pn"] = frame["ID_NO_ZERO"].map(clean)
    frame["_manager_pn"] = frame["Dir. Vorgesetzter (PN)"].map(clean)
    warnings: list[str] = []
    missing_pn = int((frame["_pn"] == "").sum())
    missing_manager = int((frame["_manager_pn"] == "").sum())
    if missing_pn:
        warnings.append(f"{missing_pn} Zeile(n) ohne Personalnummer wurden übersprungen.")
    if missing_manager:
        warnings.append(
            f"{missing_manager} Zeile(n) ohne direkte vorgesetzte Person erzeugen keine Führungslinie."
        )

    valid_people = frame[frame["_pn"] != ""]
    person_groups = list(valid_people.groupby("_pn", sort=False))
    raw_lines = frame[(frame["_pn"] != "") & (frame["_manager_pn"] != "")]
    line_frame = raw_lines.drop_duplicates(subset=["_pn", "_manager_pn"], keep="first")
    duplicate_lines = len(raw_lines) - len(line_frame)
    if duplicate_lines:
        warnings.append(
            f"{duplicate_lines} doppelte SAP-Zeile(n) derselben Führungslinie wurden zusammengeführt."
        )

    known_people = {pn for pn, _rows in person_groups}
    unknown_managers = sorted(set(line_frame["_manager_pn"]) - known_people)
    if unknown_managers:
        warnings.append(
            f"{len(unknown_managers)} vorgesetzte Person(en) sind nicht als eigene Person im Export enthalten."
        )

    timestamp = imported_at.isoformat(timespec="seconds")
    cursor = connection.execute(
        """
        INSERT INTO sap_imports (
            original_filename, stored_filename, sha256, imported_at, row_count,
            employee_count, reporting_line_count, warning_count, warnings_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            original_filename,
            stored_filename,
            digest,
            timestamp,
            len(frame),
            len(person_groups),
            len(line_frame),
            len(warnings),
            json.dumps(warnings, ensure_ascii=False),
        ),
    )
    import_id = int(cursor.lastrowid)

    for pn, rows in person_groups:
        values = (
            pn,
            _first_value(rows, "Rufname"),
            _first_value(rows, "Nachname"),
            _first_value(rows, "lange ID/Nummer"),
            _first_value(rows, "Plans. Bez."),
            _first_value(rows, "OE Bez."),
            _first_value(rows, "BsGrd"),
            _first_date(rows, "Eintritt"),
            _first_date(rows, "Austritt"),
            _first_date(rows, "Ende Probezeit"),
            _first_value(rows, "Ans."),
            _first_value(rows, "Bewilligung für"),
            import_id,
            timestamp,
        )
        connection.execute(
            """
            INSERT INTO employees (
                pn, first_name, last_name, email, position, org_unit,
                employment_degree, entry_date, exit_date, probation_end,
                employment_assignment, secondary_employment, last_import_id, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pn) DO UPDATE SET
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                email=excluded.email,
                position=excluded.position,
                org_unit=excluded.org_unit,
                employment_degree=excluded.employment_degree,
                entry_date=excluded.entry_date,
                exit_date=excluded.exit_date,
                probation_end=excluded.probation_end,
                employment_assignment=excluded.employment_assignment,
                secondary_employment=excluded.secondary_employment,
                last_import_id=excluded.last_import_id,
                updated_at=excluded.updated_at
            """,
            values,
        )

    for _, row in line_frame.iterrows():
        connection.execute(
            """
            INSERT INTO reporting_lines (
                sap_import_id, employee_pn, manager_pn, org_unit, position
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                import_id,
                clean(row.get("_pn")),
                clean(row.get("_manager_pn")),
                clean(row.get("OE Bez.")),
                clean(row.get("Plans. Bez.")),
            ),
        )

    connection.commit()
    return ImportResult(
        import_id=import_id,
        row_count=len(frame),
        employee_count=len(person_groups),
        reporting_line_count=len(line_frame),
        warnings=warnings,
    )
