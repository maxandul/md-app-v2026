"""Sicherer Vorschau- und Importprozess für frühere MD-Word-Formulare."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": WORD_NS}
VALUE = f"{{{WORD_NS}}}val"
FULL_DATE = f"{{{WORD_NS}}}fullDate"
MAX_FORM_BYTES = 50 * 1024 * 1024
MAX_WORD_XML_BYTES = 20 * 1024 * 1024

COMPETENCY_TAGS = {
    "entwicklungsfaehigkeit": "Entwicklungsfähigkeit",
    "werteorientierung": "Werteorientierung",
    "selbstmanagement": "Selbstmanagement",
    "fach_spezialwissen": "Fach- und Spezialwissen",
    "problemloesefaehigkeit": "Problemlösefähigkeit",
    "planungs_organisationsfaehigkeit": "Planungs- und Organisationsfähigkeit",
    "ergebnisorientiertes_handeln": "Ergebnisorientiertes Handeln",
    "leistungskonstanz": "Leistungskonstanz",
    "leistungsorientierung": "Leistungsorientierung",
    "gestaltungsfaehigkeit": "Gestaltungsfähigkeit",
    "kommunikationsfaehigkeit": "Kommunikationsfähigkeit",
    "beziehungsmanagement": "Beziehungsmanagement",
    "konfliktmanagement": "Konfliktmanagement",
}


def _tag_key(value: Any) -> str:
    ascii_value = unicodedata.normalize("NFKD", str(value or "")).encode(
        "ascii", "ignore"
    ).decode()
    return re.sub(r"[^a-z0-9]+", "_", ascii_value.lower()).strip("_")


def _clean_text(value: str) -> str:
    text = re.sub(r"[ \t]+", " ", value.replace("\xa0", " "))
    text = re.sub(r" *\n *", "\n", text).strip()
    if not text or text.lower().startswith(("klicken sie hier", "klicken oder tippen")):
        return ""
    return text


def _control_text(control: ElementTree.Element) -> str:
    if control.find("./w:sdtPr/w:showingPlcHdr", NS) is not None:
        return ""
    date_node = control.find("./w:sdtPr/w:date", NS)
    full_date = date_node.get(FULL_DATE, "") if date_node is not None else ""
    paragraphs = []
    content = control.find("./w:sdtContent", NS)
    if content is not None:
        for paragraph in content.findall(".//w:p", NS):
            parts = [node.text or "" for node in paragraph.findall(".//w:t", NS)]
            text = "".join(parts).strip()
            if text:
                paragraphs.append(text)
    return _clean_text("\n".join(paragraphs) or full_date[:10])


def extract_content_controls(path: Path) -> dict[str, list[str]]:
    """Liest getaggte Word-Content-Controls in stabiler Dokumentreihenfolge."""
    controls: dict[str, list[str]] = {}
    if path.stat().st_size > MAX_FORM_BYTES:
        raise ValueError("Word-Datei überschreitet die zulässige Grösse")
    try:
        with zipfile.ZipFile(path) as archive:
            xml_names = [
                name for name in archive.namelist()
                if re.fullmatch(r"word/(document|header\d+|footer\d+)\.xml", name)
            ]
            xml_size = sum(archive.getinfo(name).file_size for name in xml_names)
            if xml_size > MAX_WORD_XML_BYTES:
                raise ValueError("entpackter Word-Inhalt überschreitet die zulässige Grösse")
            for name in sorted(xml_names, key=lambda item: ("document" not in item, item)):
                root = ElementTree.fromstring(archive.read(name))
                for control in root.findall(".//w:sdt", NS):
                    tag = control.find("./w:sdtPr/w:tag", NS)
                    if tag is None or not tag.get(VALUE):
                        continue
                    controls.setdefault(_tag_key(tag.get(VALUE)), []).append(
                        _control_text(control)
                    )
    except (ElementTree.ParseError, KeyError, zipfile.BadZipFile) as exc:
        raise ValueError("keine lesbare Word-Open-XML-Datei") from exc
    return controls


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _first(controls: dict[str, list[str]], *tags: str) -> str:
    for tag in tags:
        for value in controls.get(_tag_key(tag), []):
            if value:
                return value
    return ""


def _person_number(value: str) -> str:
    text = re.sub(r"\s+", "", value).removesuffix(".0")
    return text if re.fullmatch(r"[A-Za-z0-9_-]+", text) else ""


def _goal_rows(
    controls: dict[str, list[str]], *, prefix: str, competency: str = "",
) -> list[dict[str, str]]:
    fields = {
        "title": controls.get(f"{prefix}_ziel", []),
        "criteria": controls.get(f"{prefix}_kriterien", []),
        "steps": controls.get(f"{prefix}_schritte", []),
        "target_date": controls.get(f"{prefix}_termin", []),
    }
    result = []
    for index in range(max((len(values) for values in fields.values()), default=0)):
        item = {
            key: values[index] if index < len(values) else ""
            for key, values in fields.items()
        }
        if not item["title"]:
            continue
        item["competency"] = competency
        item["source_tag_family"] = prefix
        result.append(item)
    return result


def _performance_goals(controls: dict[str, list[str]]) -> list[dict[str, str]]:
    for source_tag_family, fields in (
        ("ab_ziel", {
            "title": controls.get("ab_ziel", []),
            "criteria": controls.get("ab_ziel_kriterien", []),
            "steps": controls.get("ab_ziel_schritte", []),
            "target_date": controls.get("ab_ziel_termin", []),
        }),
        ("legacy_goal", {
            "title": controls.get("ziel", []),
            "criteria": controls.get("messkriterien_ziel", []),
            "steps": controls.get("schritte_ziel", []),
            "target_date": controls.get("termin_ziel", []),
        }),
    ):
        result = []
        for index in range(max((len(values) for values in fields.values()), default=0)):
            item = {
                key: values[index] if index < len(values) else ""
                for key, values in fields.items()
            }
            if item["title"]:
                item.update({
                    "competency": "", "source_tag_family": source_tag_family,
                })
                result.append(item)
        if result:
            return result
    return []


def parse_legacy_form(path: Path) -> dict[str, Any]:
    controls = extract_content_controls(path)
    pn = _person_number(_first(controls, "ab_pn", "pn", "rb_pn"))
    assignment = _person_number(
        _first(controls, "ab_ans", "ans", "anstellungsnummer", "rb_ans")
    )
    development = []
    for slug, competency in COMPETENCY_TAGS.items():
        development.extend(
            _goal_rows(controls, prefix=f"ab_{slug}", competency=competency)
        )
    performance = _performance_goals(controls)
    document_type = (
        "outlook" if "ab_pn" in controls or performance or development else "unknown"
    )
    return {
        "path": path,
        "filename": path.name,
        "sha256": _sha256(path),
        "document_type": document_type,
        "employee_pn": pn,
        "assignment_number": assignment,
        "performance_goals": performance,
        "development_goals": development,
    }


def _match_assignment(
    connection: sqlite3.Connection, *, employee_pn: str, assignment_number: str,
) -> tuple[str, str]:
    if not employee_pn:
        return "missing_person_number", ""
    assignments = [
        str(row["assignment_number"])
        for row in connection.execute(
            """
            SELECT assignment_number FROM employment_assignments
            WHERE person_number = ? AND active = 1 ORDER BY assignment_number
            """,
            (employee_pn,),
        ).fetchall()
    ]
    if not assignments:
        return "person_not_active", ""
    if assignment_number:
        return (
            ("matched", assignment_number)
            if assignment_number in assignments else ("assignment_not_found", "")
        )
    if len(assignments) > 1:
        return "ambiguous_assignment", ""
    return "matched", assignments[0]


def scan_legacy_forms(
    connection: sqlite3.Connection, *, forms_root: Path, goal_year: int,
) -> dict[str, Any]:
    paths = sorted(
        path for path in forms_root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".docx", ".docm"}
        and not path.name.startswith("~$")
    )
    items = []
    seen_hashes: dict[str, str] = {}
    for path in paths:
        try:
            item = parse_legacy_form(path)
            existing = connection.execute(
                "SELECT 1 FROM legacy_form_imports WHERE sha256 = ?", (item["sha256"],)
            ).fetchone()
            if existing:
                status, resolved_assignment = "already_imported", ""
            elif item["sha256"] in seen_hashes:
                status, resolved_assignment = "duplicate_in_batch", ""
                item["duplicate_of"] = seen_hashes[item["sha256"]]
            elif item["document_type"] != "outlook":
                status, resolved_assignment = "not_outlook", ""
            elif not item["performance_goals"] and not item["development_goals"]:
                status, resolved_assignment = "no_goals", ""
            else:
                status, resolved_assignment = _match_assignment(
                    connection,
                    employee_pn=item["employee_pn"],
                    assignment_number=item["assignment_number"],
                )
            seen_hashes.setdefault(item["sha256"], item["filename"])
            item.setdefault("duplicate_of", "")
            item.update(status=status, resolved_assignment=resolved_assignment, error="")
        except (OSError, ValueError) as exc:
            item = {
                "path": path, "filename": path.name, "sha256": "",
                "document_type": "unknown", "employee_pn": "",
                "assignment_number": "", "performance_goals": [],
                "development_goals": [], "status": "read_error",
                "resolved_assignment": "", "duplicate_of": "", "error": str(exc),
            }
        items.append(item)
    counts: dict[str, int] = {}
    for item in items:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return {
        "goal_year": goal_year,
        "files_found": len(paths),
        "counts": counts,
        "performance_goals": sum(
            len(item["performance_goals"]) for item in items if item["status"] == "matched"
        ),
        "development_goals": sum(
            len(item["development_goals"]) for item in items if item["status"] == "matched"
        ),
        "items": items,
    }


def import_legacy_forms(
    connection: sqlite3.Connection, *, forms_root: Path, goal_year: int,
    imported_at: datetime | None = None,
) -> dict[str, Any]:
    result = scan_legacy_forms(connection, forms_root=forms_root, goal_year=goal_year)
    timestamp = (imported_at or datetime.now().astimezone()).isoformat(timespec="seconds")
    imported = 0
    try:
        for item in result["items"]:
            if item["status"] != "matched":
                continue
            cursor = connection.execute(
                """
                INSERT INTO legacy_form_imports (
                    goal_year, document_type, employee_pn, assignment_number,
                    original_filename, sha256, performance_goal_count,
                    development_goal_count, imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    goal_year, item["document_type"], item["employee_pn"],
                    item["resolved_assignment"], item["filename"], item["sha256"],
                    len(item["performance_goals"]), len(item["development_goals"]),
                    timestamp,
                ),
            )
            for kind, goals in (
                ("performance", item["performance_goals"]),
                ("development", item["development_goals"]),
            ):
                for sequence, goal in enumerate(goals, start=1):
                    connection.execute(
                        """
                        INSERT INTO historical_goals (
                            legacy_form_import_id, employee_pn, assignment_number,
                            goal_year, goal_kind, sequence, competency, title,
                            criteria, steps, target_date, source_tag_family, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            cursor.lastrowid, item["employee_pn"],
                            item["resolved_assignment"], goal_year, kind, sequence,
                            goal.get("competency", ""), goal["title"],
                            goal.get("criteria", ""), goal.get("steps", ""),
                            goal.get("target_date", ""),
                            goal.get("source_tag_family", ""), timestamp,
                        ),
                    )
            imported += 1
        connection.execute(
            """
            INSERT INTO audit_log (user_id, action, object_type, object_id, details_json, created_at)
            VALUES (NULL, 'legacy_forms_imported', 'goal_year', ?, ?, ?)
            """,
            (
                str(goal_year),
                json.dumps({
                    "documents": imported,
                    "performance_goals": result["performance_goals"],
                    "development_goals": result["development_goals"],
                    "status_counts": result["counts"],
                }, ensure_ascii=False, sort_keys=True),
                timestamp,
            ),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    result["imported"] = imported
    return result
