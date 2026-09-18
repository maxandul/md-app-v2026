"""Liest und validiert eine zurückgesendete MD-HTML-Datei.

Das Skript führt noch keinen Datenbankimport durch. Es demonstriert den
maschinenlesbaren Rücklauf und prüft die wichtigsten Identitäts-, Schema- und
Vollständigkeitsmerkmale, bevor Daten später in SQLite übernommen werden.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class PackageDataParser(HTMLParser):
    """Extrahiert den JSON-Block mit id=md-data aus einer HTML-Datei."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._capture = False
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        attributes = dict(attrs)
        if attributes.get("id") == "md-data" and attributes.get("type") == "application/json":
            self._capture = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._capture:
            self._capture = False

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._parts.append(data)

    @property
    def json_text(self) -> str:
        return "".join(self._parts).strip()


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return not self.errors


def extract_payload(path: Path) -> dict[str, Any]:
    parser = PackageDataParser()
    parser.feed(path.read_text(encoding="utf-8"))
    if not parser.json_text:
        raise ValueError("Kein JSON-Datenblock mit id='md-data' gefunden.")
    data = json.loads(parser.json_text)
    if not isinstance(data, dict):
        raise ValueError("Der MD-Datenblock ist kein JSON-Objekt.")
    return data


def _filled(value: Any) -> bool:
    return bool(str(value or "").strip())


def _section_status(
    employee: dict[str, Any], section: str, include_dialog_date: bool = True
) -> tuple[bool, list[str]]:
    missing: list[str] = []
    section_data = employee.get(section, {})
    dialog_date = section_data.get("dialog_date") or employee.get("dialog_date")
    if include_dialog_date and not _filled(dialog_date):
        missing.append("Gesprächsdatum")
    if section == "review":
        review = employee.get("review", {})
        if employee.get("dialog_type") == "probation":
            if not _filled(review.get("performance")):
                missing.append("Rückblick auf Leistung und Einführungsziele")
            if not _filled(review.get("employment_continued")):
                missing.append("Anstellungsentscheid")
            if not _filled(review.get("agreement")):
                missing.append("Einigkeit zum Anstellungsentscheid")
            return not missing, missing
        for index, goal in enumerate(employee.get("previous_goals", []), start=1):
            if not _filled(goal.get("title")):
                missing.append(f"Bezeichnung Vorjahresziel {index}")
            if not _filled(goal.get("criteria")):
                missing.append(f"Messkriterien Vorjahresziel {index}")
            if not _filled(goal.get("achievement")):
                missing.append(f"Zielerreichung Vorjahresziel {index}")
            if not _filled(goal.get("review")):
                missing.append(f"Rückblick Vorjahresziel {index}")
        for index, goal in enumerate(employee.get("previous_development_goals", []), start=1):
            if not _filled(goal.get("competency")):
                missing.append(f"Kompetenz Entwicklungsziel {index}")
            if not _filled(goal.get("title")):
                missing.append(f"Bezeichnung Entwicklungsziel {index}")
            if not _filled(goal.get("criteria")):
                missing.append(f"Messkriterien Entwicklungsziel {index}")
            if not _filled(goal.get("achievement")):
                missing.append(f"Zielerreichung Entwicklungsziel {index}")
            if not _filled(goal.get("review")):
                missing.append(f"Rückblick Entwicklungsziel {index}")
        if not _filled(review.get("performance")):
            missing.append("Leistungsrückblick")
        if not _filled(review.get("overall_rating")):
            missing.append("Gesamteindruck")
        if not _filled(review.get("agreement")):
            missing.append("Einigkeit zur Gesamtbeurteilung")
        if not _filled(review.get("secondary_employment_current")):
            missing.append("Aktualität Nebenbeschäftigungen/öffentliche Ämter")
    else:
        outlook = employee.get("outlook", {})
        goals = outlook.get("performance_goals", [])
        if not goals:
            missing.append("Mindestens ein Leistungsziel")
        for index, goal in enumerate(goals, start=1):
            if not _filled(goal.get("title")):
                missing.append(f"Bezeichnung Leistungsziel {index}")
            if not _filled(goal.get("criteria")):
                missing.append(f"Messkriterien Leistungsziel {index}")
            if not _filled(goal.get("target_date")):
                missing.append(f"Termin Leistungsziel {index}")
        for index, goal in enumerate(outlook.get("development_goals", []), start=1):
            for key, label in (
                ("competency", "Kompetenz"),
                ("title", "Bezeichnung"),
                ("criteria", "Messkriterien"),
                ("target_date", "Termin"),
            ):
                if not _filled(goal.get(key)):
                    missing.append(f"{label} Entwicklungsziel {index}")
    return not missing, missing


def employee_status(employee: dict[str, Any]) -> tuple[str, list[str]]:
    scope = employee.get("scope", "")
    missing: list[str] = []
    if not scope:
        return "offen", ["Umfang"]
    if scope == "none":
        if not _filled(employee.get("no_md_reason")):
            missing.append("Grund für kein MD")
        if employee.get("no_md_reason") == "Anderer Grund" and not _filled(employee.get("no_md_note")):
            missing.append("Erläuterung zum anderen Grund")
        return ("kein_md" if not missing else "offen"), missing
    if scope in {"review_only", "outlook_only"} and not _filled(employee.get("scope_reason")):
        missing.append("Begründung für abweichenden Umfang")
    if scope in {"full", "review_only"}:
        _, section_missing = _section_status(employee, "review")
        missing.extend(section_missing)
    if scope in {"full", "outlook_only"}:
        _, section_missing = _section_status(employee, "outlook")
        missing.extend(section_missing)
    return ("vollstaendig" if not missing else "offen"), missing


def validate_payload(payload: dict[str, Any]) -> ValidationResult:
    result = ValidationResult()
    if payload.get("schema_version") != "1.0":
        result.errors.append(f"Nicht unterstützte schema_version: {payload.get('schema_version')!r}")

    package = payload.get("package")
    if not isinstance(package, dict):
        result.errors.append("Paketmetadaten fehlen.")
        package = {}
    for key in ("package_id", "manager_pn", "manager_name", "rb_year", "ab_year", "created_at"):
        if not _filled(package.get(key)):
            result.errors.append(f"Paketmetadatum fehlt: {key}")
    revision = package.get("revision", 0)
    if not isinstance(revision, int) or revision < 0:
        result.errors.append("Paketmetadatum revision muss eine nichtnegative Ganzzahl sein.")
    if package.get("s_mime_required") is not True:
        result.warnings.append("Das Paket ist nicht als S/MIME-pflichtig gekennzeichnet.")
    if not _filled(package.get("saved_at")):
        result.warnings.append("Die Datei wurde offenbar noch nie über «Zwischenstand speichern» exportiert.")

    employees = payload.get("employees")
    if not isinstance(employees, list) or not employees:
        result.errors.append("Keine Mitarbeitenden im Paket vorhanden.")
        employees = []

    case_ids: set[str] = set()
    personal_numbers: set[str] = set()
    status_counts = {"vollstaendig": 0, "kein_md": 0, "offen": 0}
    incomplete: list[dict[str, Any]] = []

    for index, employee in enumerate(employees, start=1):
        case_id = str(employee.get("case_id", "")).strip()
        person = employee.get("employee") or {}
        pn = str(person.get("pn", "")).strip()
        name = str(person.get("full_name", "")).strip() or f"Datensatz {index}"
        if not case_id:
            result.errors.append(f"{name}: case_id fehlt.")
        elif case_id in case_ids:
            result.errors.append(f"Doppelte case_id: {case_id}")
        case_ids.add(case_id)
        if not pn:
            result.errors.append(f"{name}: Personalnummer fehlt.")
        elif pn in personal_numbers:
            result.errors.append(f"Doppelte Personalnummer im Paket: {pn}")
        personal_numbers.add(pn)

        status, missing = employee_status(employee)
        status_counts[status] += 1
        if missing:
            incomplete.append({"case_id": case_id, "pn": pn, "name": name, "missing": missing})

    result.summary = {
        "package_id": package.get("package_id", ""),
        "manager_pn": package.get("manager_pn", ""),
        "manager_name": package.get("manager_name", ""),
        "rb_year": package.get("rb_year", ""),
        "ab_year": package.get("ab_year", ""),
        "saved_at": package.get("saved_at", ""),
        "revision": revision,
        "employees": len(employees),
        "status_counts": status_counts,
        "incomplete": incomplete,
    }
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path, help="Zurückgesendete MD-HTML-Datei")
    parser.add_argument("--json", action="store_true", help="Prüfergebnis als JSON ausgeben")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = extract_payload(args.html)
        result = validate_payload(payload)
    except Exception as exc:
        print(f"FEHLER: {exc}")
        return 2

    if args.json:
        print(
            json.dumps(
                {
                    "valid": result.valid,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "summary": result.summary,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        summary = result.summary
        print(f"Paket: {summary['package_id']}")
        print(f"Vorgesetzte Person: {summary['manager_name']} ({summary['manager_pn']})")
        print(f"Durchlauf: {summary['rb_year']}/{summary['ab_year']}")
        print(f"Mitarbeitende: {summary['employees']}")
        print(
            "Status: "
            f"{summary['status_counts']['vollstaendig']} vollständig, "
            f"{summary['status_counts']['kein_md']} kein MD, "
            f"{summary['status_counts']['offen']} offen"
        )
        for warning in result.warnings:
            print(f"WARNUNG: {warning}")
        for error in result.errors:
            print(f"FEHLER: {error}")
        for item in summary["incomplete"]:
            print(f"OFFEN: {item['name']} ({item['pn']}): {', '.join(item['missing'])}")

    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
