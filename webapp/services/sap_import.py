"""SAP-Export prüfen, klassifizieren und als aktuellen Datenstand synchronisieren."""

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


REQUIRED_COLUMNS = {"ID_NO_ZERO", "Rufname", "Nachname", "Dir. Vorgesetzter (PN)", "lange ID/Nummer"}
CORE_FIELDS = ("Rufname", "Nachname", "lange ID/Nummer", "BsGrd", "BG", "Eintritt", "Austritt", "Ende Probezeit")
PERMISSION_FIELDS = ("Beginn Bewilligung", "Ende Bewilligung", "Bewilligung", "Bewilligung für")


@dataclass(frozen=True)
class ImportResult:
    import_id: int
    row_count: int
    employee_count: int
    reporting_line_count: int
    warnings: list[str]
    ignored_bg_zero_count: int = 0
    exact_duplicate_count: int = 0
    multiple_employment_count: int = 0
    multiple_permission_count: int = 0
    conflict_count: int = 0


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


def _column(frame: pd.DataFrame, *candidates: str) -> str | None:
    names = {str(name).strip().casefold(): str(name) for name in frame.columns}
    return next((names[item.casefold()] for item in candidates if item.casefold() in names), None)


def _first_value(rows: pd.DataFrame, column: str | None) -> str:
    if not column or column not in rows:
        return ""
    return next((text for value in rows[column] if (text := clean(value))), "")


def _first_date(rows: pd.DataFrame, column: str) -> str:
    if column not in rows:
        return ""
    return next((text for value in rows[column] if (text := iso_date(value))), "")


def _signature(row: pd.Series, columns: list[str]) -> tuple[str, ...]:
    return tuple(clean(row.get(column)) for column in columns)


def _issue(kind: str, severity: str, row: pd.Series | None = None, **details: Any) -> dict[str, Any]:
    return {
        "type": kind,
        "severity": severity,
        "pn": clean(row.get("_pn")) if row is not None else clean(details.pop("pn", "")),
        "ans": clean(row.get("_assignment")) if row is not None else clean(details.pop("ans", "")),
        "rows": [int(row["_source_row"])] if row is not None else details.pop("rows", []),
        "details": details,
    }


def _classify(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, int], list[str]]:
    issues: list[dict[str, Any]] = []
    warnings: list[str] = []
    counts = {"bg_zero": 0, "exact": 0, "multiple_employment": 0, "permissions": 0, "conflicts": 0}

    degree_column = _column(frame, "BG", "BsGrd", "Beschäftigungsgrad", "Beschaeftigungsgrad")
    if degree_column:
        values = frame[degree_column].map(clean).str.replace(",", ".", regex=False)
        zero_mask = pd.to_numeric(values, errors="coerce") == 0
        counts["bg_zero"] = int(zero_mask.sum())
        frame = frame[~zero_mask].copy()
        if counts["bg_zero"]:
            warnings.append(f"{counts['bg_zero']} Zeile(n) mit BG 0 wurden fachlich ignoriert.")

    missing_pn = frame[frame["_pn"] == ""]
    if len(missing_pn):
        warnings.append(f"{len(missing_pn)} Zeile(n) ohne Personalnummer wurden übersprungen.")
        issues.append(_issue("missing_person_number", "blocking", rows=missing_pn["_source_row"].astype(int).tolist()))
    missing_manager = frame[frame["_manager_pn"] == ""]
    if len(missing_manager):
        warnings.append(f"{len(missing_manager)} Zeile(n) ohne direkte vorgesetzte Person erzeugen keine Führungslinie.")
        issues.extend(_issue("missing_manager", "warning", row) for _, row in missing_manager.iterrows())

    business_columns = [column for column in frame.columns if not column.startswith("_")]
    duplicate_mask = frame.duplicated(subset=business_columns, keep="first")
    counts["exact"] = int(duplicate_mask.sum())
    issues.extend(_issue("exact_duplicate", "info", row) for _, row in frame[duplicate_mask].iterrows())
    if counts["exact"]:
        warnings.append(f"{counts['exact']} vollständig identische Zeile(n) wurden dedupliziert.")
        frame = frame[~duplicate_mask].copy()

    core_columns = [column for name in CORE_FIELDS if (column := _column(frame, name))]
    permission_columns = [column for name in PERMISSION_FIELDS if (column := _column(frame, name))]
    for pn, person_rows in frame[frame["_pn"] != ""].groupby("_pn", sort=False):
        assignments = sorted({item for item in person_rows["_assignment"] if item})
        if len(assignments) > 1:
            counts["multiple_employment"] += 1
            issues.append(_issue("multiple_employment", "info", pn=pn, rows=person_rows["_source_row"].astype(int).tolist(), assignments=assignments))
        for assignment, rows in person_rows.groupby("_assignment", sort=False, dropna=False):
            core_signatures = {_signature(row, core_columns) for _, row in rows.iterrows()}
            if len(core_signatures) > 1:
                counts["conflicts"] += 1
                issues.append(_issue("conflicting_duplicate", "blocking", pn=pn, ans=assignment, rows=rows["_source_row"].astype(int).tolist(), different_core_variants=len(core_signatures)))
            permission_signatures = {_signature(row, permission_columns) for _, row in rows.iterrows()} if permission_columns else set()
            permission_signatures = {item for item in permission_signatures if any(item)}
            if len(permission_signatures) > 1:
                counts["permissions"] += 1
                issues.append(_issue("multiple_permissions", "info", pn=pn, ans=assignment, rows=rows["_source_row"].astype(int).tolist(), permission_variants=len(permission_signatures)))
    if counts["conflicts"]:
        warnings.append(f"{counts['conflicts']} widersprüchliche Dublette(n) müssen durch HR geklärt werden.")
    return frame, issues, counts, warnings


def _sync_active_flags(connection: sqlite3.Connection, person_numbers: set[str]) -> None:
    if person_numbers:
        placeholders = ",".join("?" for _ in person_numbers)
        params = tuple(person_numbers)
        connection.execute(f"UPDATE persons SET active = 0 WHERE person_number NOT IN ({placeholders})", params)
        connection.execute(f"UPDATE employees SET active = 0 WHERE pn NOT IN ({placeholders})", params)
        connection.execute(f"UPDATE employment_assignments SET active = 0 WHERE person_number NOT IN ({placeholders})", params)
    else:
        connection.execute("UPDATE persons SET active = 0")
        connection.execute("UPDATE employees SET active = 0")
        connection.execute("UPDATE employment_assignments SET active = 0")


def import_sap_workbook(connection: sqlite3.Connection, path: Path, *, original_filename: str, stored_filename: str, imported_at: datetime | None = None) -> ImportResult:
    imported_at = imported_at or datetime.now().astimezone()
    digest = file_sha256(path)
    duplicate = connection.execute("SELECT id, imported_at FROM sap_imports WHERE sha256 = ? ORDER BY id DESC LIMIT 1", (digest,)).fetchone()
    if duplicate:
        raise ValueError(f"Diese SAP-Datei wurde bereits importiert (Import {duplicate['id']} vom {duplicate['imported_at']}).")

    source = pd.read_excel(path, dtype=object)
    source.columns = [str(column).strip() for column in source.columns]
    missing = sorted(REQUIRED_COLUMNS.difference(source.columns))
    if missing:
        raise ValueError(f"Im SAP-Export fehlen Spalten: {', '.join(missing)}")
    source["_source_row"] = range(2, len(source) + 2)
    source["_pn"] = source["ID_NO_ZERO"].map(clean)
    source["_manager_pn"] = source["Dir. Vorgesetzter (PN)"].map(clean)
    assignment_column = _column(source, "Ans.", "Ans", "Anstellung")
    source["_assignment"] = source[assignment_column].map(clean) if assignment_column else ""
    frame, issues, counts, warnings = _classify(source)

    valid_people = frame[frame["_pn"] != ""]
    person_groups = list(valid_people.groupby("_pn", sort=False))
    raw_lines = frame[(frame["_pn"] != "") & (frame["_manager_pn"] != "")]
    line_frame = raw_lines.drop_duplicates(subset=["_pn", "_manager_pn"], keep="first")
    known_people = {pn for pn, _ in person_groups}
    unknown_managers = sorted(set(line_frame["_manager_pn"]) - known_people)
    if unknown_managers:
        warnings.append(f"{len(unknown_managers)} vorgesetzte Person(en) sind nicht als eigene Person im Export enthalten.")

    timestamp = imported_at.isoformat(timespec="seconds")
    try:
        cursor = connection.execute(
            """INSERT INTO sap_imports (
                original_filename, stored_filename, sha256, imported_at, row_count,
                employee_count, reporting_line_count, warning_count, warnings_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (original_filename, stored_filename, digest, timestamp, len(source), len(person_groups), len(line_frame), len(warnings), json.dumps(warnings, ensure_ascii=False)),
        )
        import_id = int(cursor.lastrowid)
        for item in issues:
            connection.execute(
                """INSERT INTO sap_import_issues (
                    sap_import_id, issue_type, severity, person_number, employment_assignment,
                    row_numbers_json, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (import_id, item["type"], item["severity"], item["pn"], item["ans"], json.dumps(item["rows"]), json.dumps(item["details"], ensure_ascii=False), timestamp),
            )

        _sync_active_flags(connection, {pn for pn, _ in person_groups})
        degree_column = _column(frame, "BG", "BsGrd", "Beschäftigungsgrad", "Beschaeftigungsgrad")
        permission_columns = [column for name in PERMISSION_FIELDS if (column := _column(frame, name))]
        for pn, rows in person_groups:
            first_name = _first_value(rows, "Rufname")
            last_name = _first_value(rows, "Nachname")
            email = _first_value(rows, "lange ID/Nummer")
            connection.execute(
                """INSERT INTO persons (person_number, first_name, last_name, email, active, last_import_id, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(person_number) DO UPDATE SET first_name=excluded.first_name,
                last_name=excluded.last_name, email=excluded.email, active=1,
                last_import_id=excluded.last_import_id, updated_at=excluded.updated_at""",
                (pn, first_name, last_name, email, import_id, timestamp),
            )
            connection.execute(
                """INSERT INTO employees (
                    pn, first_name, last_name, email, position, org_unit, employment_degree,
                    entry_date, exit_date, probation_end, employment_assignment,
                    secondary_employment, last_import_id, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pn) DO UPDATE SET first_name=excluded.first_name,
                last_name=excluded.last_name, email=excluded.email, position=excluded.position,
                org_unit=excluded.org_unit, employment_degree=excluded.employment_degree,
                entry_date=excluded.entry_date, exit_date=excluded.exit_date,
                probation_end=excluded.probation_end, employment_assignment=excluded.employment_assignment,
                secondary_employment=excluded.secondary_employment, active=1,
                last_import_id=excluded.last_import_id, updated_at=excluded.updated_at""",
                (pn, first_name, last_name, email, _first_value(rows, "Plans. Bez."), _first_value(rows, "OE Bez."), _first_value(rows, degree_column), _first_date(rows, "Eintritt"), _first_date(rows, "Austritt"), _first_date(rows, "Ende Probezeit"), _first_value(rows, assignment_column), _first_value(rows, "Bewilligung für"), import_id, timestamp),
            )

            for assignment, employment_rows in rows.groupby("_assignment", sort=False, dropna=False):
                assignment = clean(assignment) or "1"
                result = connection.execute(
                    """INSERT INTO employment_assignments (
                        person_number, assignment_number, position, org_unit, employment_degree,
                        entry_date, exit_date, probation_end, active, last_import_id, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    ON CONFLICT(person_number, assignment_number) DO UPDATE SET
                        position=excluded.position, org_unit=excluded.org_unit,
                        employment_degree=excluded.employment_degree, entry_date=excluded.entry_date,
                        exit_date=excluded.exit_date, probation_end=excluded.probation_end,
                        active=1, last_import_id=excluded.last_import_id, updated_at=excluded.updated_at
                    RETURNING id""",
                    (pn, assignment, _first_value(employment_rows, "Plans. Bez."), _first_value(employment_rows, "OE Bez."), _first_value(employment_rows, degree_column), _first_date(employment_rows, "Eintritt"), _first_date(employment_rows, "Austritt"), _first_date(employment_rows, "Ende Probezeit"), import_id, timestamp),
                )
                employment_id = int(result.fetchone()[0])
                signatures = {_signature(row, permission_columns) for _, row in employment_rows.iterrows()} if permission_columns else set()
                for values in (item for item in signatures if any(item)):
                    padded = list(values) + [""] * (4 - len(values))
                    fingerprint = hashlib.sha256("\x1f".join(values).encode("utf-8")).hexdigest()
                    connection.execute(
                        """INSERT INTO secondary_activity_permissions (
                            employment_id, valid_from, valid_to, permission, permission_for,
                            source_fingerprint, last_import_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(employment_id, source_fingerprint)
                        DO UPDATE SET last_import_id=excluded.last_import_id""",
                        (employment_id, padded[0], padded[1], padded[2], padded[3], fingerprint, import_id),
                    )

        for _, row in line_frame.iterrows():
            connection.execute(
                "INSERT INTO reporting_lines (sap_import_id, employee_pn, manager_pn, org_unit, position) VALUES (?, ?, ?, ?, ?)",
                (import_id, row["_pn"], row["_manager_pn"], clean(row.get("OE Bez.")), clean(row.get("Plans. Bez."))),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise

    return ImportResult(import_id, len(source), len(person_groups), len(line_frame), warnings, counts["bg_zero"], counts["exact"], counts["multiple_employment"], counts["permissions"], counts["conflicts"])
