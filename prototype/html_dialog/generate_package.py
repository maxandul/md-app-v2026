"""Erzeugt eine selbständige MD-HTML-Datei pro vorgesetzter Person.

Der Prototyp liest die vorhandene SAP-EXPORT.xlsx, gruppiert die direkt
unterstellten Mitarbeitenden und bettet alle Daten in eine einzige, offline
funktionsfähige HTML-Datei ein. Es werden keine externen Ressourcen geladen.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from webapp.competency_model import COMPETENCY_MODEL
except ModuleNotFoundError:  # Direkter Aufruf ausserhalb des Projektordners
    COMPETENCY_MODEL = []


PROTOTYPE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PROTOTYPE_DIR.parent.parent
DEFAULT_SAP_PATH = PROJECT_ROOT / "sap_stammdaten" / "EXPORT.XLSX"
DEFAULT_TEMPLATE_PATH = PROTOTYPE_DIR / "template.html"

COMPETENCIES = [
    "Entwicklungsfähigkeit",
    "Selbstmanagement",
    "Werteorientierung",
    "Fach- und Spezialwissen",
    "Planungs- und Organisationsfähigkeit",
    "Problemlösefähigkeit",
    "Ergebnisorientiertes Handeln",
    "Leistungsorientierung",
    "Leistungskonstanz",
    "Gestaltungsfähigkeit",
    "Kommunikationsfähigkeit",
    "Beziehungsmanagement",
    "Konfliktmanagement",
]

NO_MD_REASONS = [
    "Austritt",
    "Pensionierung",
    "Wechsel der vorgesetzten Person",
    "Neueintritt",
    "Längere Abwesenheit",
    "Anderer Grund",
]


def _clean(value: Any) -> str:
    """Wandelt SAP-Werte ohne NaN/NaT-Artefakte in Text um."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return re.sub(r"\.0$", "", text)


def _iso_date(value: Any) -> str:
    """Gibt ein Datum als YYYY-MM-DD zurück oder einen leeren Text."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    try:
        return pd.Timestamp(value).date().isoformat()
    except (TypeError, ValueError):
        return ""


def load_sap_data(path: Path) -> pd.DataFrame:
    """Lädt und normalisiert den SAP-Export für den Prototyp."""
    frame = pd.read_excel(path, dtype=object)
    frame.columns = [str(column).strip() for column in frame.columns]

    required = {
        "ID_NO_ZERO",
        "Rufname",
        "Nachname",
        "Dir. Vorgesetzter (PN)",
        "lange ID/Nummer",
    }
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Fehlende SAP-Spalten: {', '.join(missing)}")

    frame["_pn"] = frame["ID_NO_ZERO"].map(_clean)
    frame["_manager_pn"] = frame["Dir. Vorgesetzter (PN)"].map(_clean)
    return frame


def manager_index(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Erstellt einen Index mit eindeutigen Mitarbeitenden pro Führungslinie."""
    people_by_pn: dict[str, pd.Series] = {}
    for _, row in frame.iterrows():
        pn = _clean(row.get("_pn"))
        if pn and pn not in people_by_pn:
            people_by_pn[pn] = row

    result: dict[str, dict[str, Any]] = {}
    for manager_pn, rows in frame.groupby("_manager_pn", dropna=False):
        manager_pn = _clean(manager_pn)
        if not manager_pn:
            continue
        # Ein Mitarbeitender kann im SAP-Beispielexport mehrfach vorkommen.
        # Im Paket darf jeder Fall pro Führungslinie nur einmal erscheinen.
        employees = rows.drop_duplicates(subset=["_pn"], keep="first").copy()
        result[manager_pn] = {
            "manager": people_by_pn.get(manager_pn),
            "employees": employees,
        }
    return result


def choose_manager(
    index: dict[str, dict[str, Any]], manager_pn: str | None
) -> tuple[str, dict[str, Any]]:
    """Wählt explizit oder automatisch eine Führungslinie für den Prototyp."""
    if manager_pn:
        key = _clean(manager_pn)
        if key not in index:
            raise ValueError(f"Keine direkt unterstellten Personen für VG-PN {key} gefunden.")
        if index[key]["manager"] is None:
            raise ValueError(f"VG-PN {key} ist nicht als Person im SAP-Export vorhanden.")
        return key, index[key]

    candidates = [
        (pn, item)
        for pn, item in index.items()
        if item["manager"] is not None and len(item["employees"]) > 0
    ]
    if not candidates:
        raise ValueError("Keine vollständige Führungslinie im SAP-Export gefunden.")
    candidates.sort(key=lambda pair: (-len(pair[1]["employees"]), pair[0]))
    return candidates[0]


def _suggested_scope(row: pd.Series, rb_year: int) -> tuple[str, str]:
    """Leitet nur einen Hinweis ab; die vorgesetzte Person bestätigt den Umfang."""
    exit_date = _iso_date(row.get("Austritt"))
    probation_end = _iso_date(row.get("Ende Probezeit"))
    if exit_date:
        parsed = date.fromisoformat(exit_date)
        if date(rb_year, 10, 1) <= parsed <= date(rb_year + 1, 1, 31):
            return "review_only", f"Austritt am {parsed.strftime('%d.%m.%Y')}."
    if probation_end:
        parsed = date.fromisoformat(probation_end)
        if parsed.year == rb_year and parsed <= date(rb_year, 6, 30):
            return "full", f"Probezeit endete am {parsed.strftime('%d.%m.%Y')}; regulärer Rückblick und Ausblick zum Jahresende."
        if date(rb_year, 7, 1) <= parsed < date(rb_year + 1, 3, 1):
            tense = "endete" if parsed.year == rb_year else "endet"
            return "outlook_only", f"Probezeit {tense} am {parsed.strftime('%d.%m.%Y')}; im Jahresdialog ist nur der Ausblick auf das neue Jahr verpflichtend."
    return "full", "Standardfall gemäss SAP-Stammdaten."


def _suggested_probation_scope(row: pd.Series, rb_year: int) -> tuple[str, str]:
    probation_end = _iso_date(row.get("Ende Probezeit"))
    if not probation_end:
        return "review_only", "Probezeitrückblick; Ende der Probezeit ist nicht in den Stammdaten hinterlegt."
    parsed = date.fromisoformat(probation_end)
    if parsed <= date(parsed.year, 6, 30):
        return "full", f"Probezeit endet am {parsed.strftime('%d.%m.%Y')}; Probezeitrückblick und Ausblick auf das restliche Jahr."
    return "review_only", f"Probezeit endet am {parsed.strftime('%d.%m.%Y')}; bis zum Jahresende verbleiben sechs Monate oder weniger."


def _bounded_review_period(row: pd.Series, rb_year: int) -> tuple[str, str]:
    period_start = date(rb_year, 1, 1)
    period_end = date(rb_year, 12, 31)
    entry_date = _iso_date(row.get("Eintritt"))
    exit_date = _iso_date(row.get("Austritt"))
    if entry_date:
        period_start = max(period_start, date.fromisoformat(entry_date))
    if exit_date:
        period_end = min(period_end, date.fromisoformat(exit_date))
    if period_start > period_end:
        raise ValueError(
            f"Für PN {_clean(row.get('ID_NO_ZERO'))} liegt {rb_year} kein Zeitraum "
            "innerhalb der bekannten Anstellung vor."
        )
    return period_start.isoformat(), period_end.isoformat()


def _sample_previous_goals(employee_no: int, rb_year: int) -> list[dict[str, str]]:
    """Liefert ausschliesslich für den Prototyp synthetische Vorjahresziele."""
    samples = [
        (
            "Abläufe im eigenen Verantwortungsbereich vereinfachen",
            "Mindestens zwei konkrete Verbesserungen sind umgesetzt und dokumentiert.",
            "Prozess aufnehmen, Verbesserungen priorisieren und im Team erproben.",
        ),
        (
            "Zusammenarbeit und Wissenstransfer stärken",
            "Relevantes Wissen ist dokumentiert und wird regelmässig im Team geteilt.",
            "Kurze Austauschtermine etablieren und zentrale Unterlagen aktualisieren.",
        ),
        (
            "Fachwissen gezielt weiterentwickeln",
            "Die vereinbarte Weiterbildung ist abgeschlossen und wird in der Praxis angewendet.",
            "Weiterbildung auswählen, besuchen und Erkenntnisse im Arbeitsalltag einsetzen.",
        ),
    ]
    count = 2 if employee_no % 2 == 0 else 3
    goals: list[dict[str, str]] = []
    for index, (title, criteria, steps) in enumerate(samples[:count], start=1):
        goals.append(
            {
                "id": f"previous-{employee_no + 1}-{index}",
                "imported": True,
                "title": title,
                "criteria": criteria,
                "steps": steps,
                "target_date": f"{rb_year}-12-31",
                "achievement": "",
                "review": "",
            }
        )
    return goals


def _empty_goal(goal_id: str) -> dict[str, str]:
    return {
        "id": goal_id,
        "title": "",
        "criteria": "",
        "steps": "",
        "target_date": "",
    }


def _sample_previous_development_goals(employee_no: int, rb_year: int) -> list[dict[str, str]]:
    if employee_no % 2:
        return []
    return [{
        "id": f"previous-development-{employee_no + 1}-1",
        "imported": True,
        "competency": "Kooperationsfähigkeit",
        "title": "Wissen im Team strukturiert weitergeben",
        "criteria": "Zwei kurze Wissenstransfers wurden durchgeführt und dokumentiert.",
        "steps": "Praxisfall auswählen, Austausch vorbereiten und Erkenntnisse festhalten.",
        "target_date": f"{rb_year}-11-30",
        "achievement": "",
        "review": "",
    }]


def build_payload(
    manager_pn: str,
    manager_pack: dict[str, Any],
    rb_year: int,
    created_at: datetime | None = None,
    dialog_type: str = "annual",
) -> dict[str, Any]:
    """Erstellt das fachliche Paket, das später in SQLite importiert werden kann."""
    if dialog_type not in {"annual", "probation"}:
        raise ValueError("dialog_type muss 'annual' oder 'probation' sein.")
    created_at = created_at or datetime.now().astimezone()
    manager = manager_pack["manager"]
    if manager is None:
        raise ValueError("Die vorgesetzte Person fehlt im SAP-Export.")

    manager_name = " ".join(
        part for part in [_clean(manager.get("Rufname")), _clean(manager.get("Nachname"))] if part
    )
    manager_first_name = _clean(manager.get("Rufname"))
    manager_last_name = _clean(manager.get("Nachname"))
    package_id = f"MD-{rb_year}-{manager_pn}-{uuid.uuid4().hex[:8].upper()}"
    employees: list[dict[str, Any]] = []

    for employee_no, (_, row) in enumerate(manager_pack["employees"].iterrows()):
        pn = _clean(row.get("_pn"))
        first_name = _clean(row.get("Rufname"))
        last_name = _clean(row.get("Nachname"))
        suggested_scope, suggestion_reason = (
            _suggested_probation_scope(row, rb_year)
            if dialog_type == "probation"
            else _suggested_scope(row, rb_year)
        )
        period_start, period_end = _bounded_review_period(row, rb_year)
        employees.append(
            {
                "case_id": f"{rb_year}-{manager_pn}-{pn}{'-probezeit' if dialog_type == 'probation' else ''}",
                "employee": {
                    "pn": pn,
                    "first_name": first_name,
                    "last_name": last_name,
                    "full_name": " ".join(part for part in [first_name, last_name] if part),
                    "position": _clean(row.get("Plans. Bez.")),
                    "org_unit": _clean(row.get("OE Bez.")),
                    "employment_degree": _clean(row.get("BsGrd")),
                    "entry_date": _iso_date(row.get("Eintritt")),
                    "exit_date": _iso_date(row.get("Austritt")),
                    "probation_end": _iso_date(row.get("Ende Probezeit")),
                    "employment_assignment": _clean(row.get("Ans.")),
                    "secondary_employment": _clean(row.get("Bewilligung für")),
                },
                "scope": "",
                "dialog_type": dialog_type,
                "scope_reason": "",
                "no_md_reason": "",
                "no_md_note": "",
                "suggestion": {
                    "scope": suggested_scope,
                    "reason": suggestion_reason,
                    "is_special": suggested_scope != "full" or "Probezeit" in suggestion_reason,
                },
                "period_start": period_start,
                "period_end": period_end,
                "previous_goals": _sample_previous_goals(employee_no, rb_year),
                "previous_development_goals": _sample_previous_development_goals(employee_no, rb_year),
                "review": {
                    "dialog_date": "",
                    "employment_continued": "",
                    "general_notes": "",
                    "performance": "",
                    "competencies": [],
                    "overall_rating": "",
                    "agreement": "",
                    "manager_comment": "",
                    "employee_comment": "",
                    "next_level_conversation": "Nein",
                    "next_level_comment": "",
                    "secondary_employment_current": "",
                    "secondary_employment_note": "",
                },
                "outlook": {
                    "dialog_date": "",
                    "performance_goals": [_empty_goal(f"goal-{employee_no + 1}-1")],
                    "open_goals_text": "",
                    "development_goals": [],
                    "nep": "",
                    "nep_notes": "",
                    "general_notes": "",
                },
                "meta": {
                    "updated_at": "",
                    "pdf_exported_at": "",
                    "archived": False,
                    "closed": False,
                    "closed_at": "",
                },
                "document_tracking": {
                    "review": {"status": "preparation", "note": ""},
                    "outlook": {"status": "preparation", "note": ""},
                    "no_md": {"status": "preparation", "note": ""},
                },
            }
        )

    return {
        "schema_version": "1.0",
        "app_version": "0.2.0-poc",
        "package": {
            "package_id": package_id,
            "manager_pn": manager_pn,
            "manager_name": manager_name,
            "manager_first_name": manager_first_name,
            "manager_last_name": manager_last_name,
            "manager_email": _clean(manager.get("lange ID/Nummer")),
            "rb_year": rb_year,
            "ab_year": rb_year + 1,
            "created_at": created_at.isoformat(timespec="seconds"),
            "saved_at": "",
            "revision": 0,
            "dialog_type": dialog_type,
            "s_mime_required": True,
            "business_device_only": True,
        },
        "configuration": {
            "competencies": COMPETENCIES,
            "competency_model": COMPETENCY_MODEL,
            "no_md_reasons": NO_MD_REASONS,
        },
        "employees": employees,
    }


def json_for_script(payload: dict[str, Any]) -> str:
    """Serialisiert JSON sicher für ein script[type=application/json]-Element."""
    return (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def render_html(payload: dict[str, Any], template_path: Path = DEFAULT_TEMPLATE_PATH) -> str:
    template = template_path.read_text(encoding="utf-8")
    marker = "__MD_PACKAGE_JSON__"
    if template.count(marker) != 1:
        raise ValueError(f"Die HTML-Vorlage muss den Marker {marker} genau einmal enthalten.")
    return template.replace(marker, json_for_script(payload))


def output_filename(payload: dict[str, Any]) -> str:
    package = payload["package"]
    def filename_part(value: Any) -> str:
        ascii_value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
        return re.sub(r"[^A-Za-z0-9_-]+", "_", ascii_value).strip("_")

    safe_last_name = filename_part(package.get("manager_last_name", ""))
    safe_first_name = filename_part(package.get("manager_first_name", ""))
    safe_name = "_".join(part for part in (safe_last_name, safe_first_name) if part)
    if not safe_name:
        safe_name = filename_part(package["manager_name"])
    prefix = "MD_Probezeit" if package.get("dialog_type") == "probation" else "MD_Dialog"
    return (
        f"{prefix}_{package['rb_year']}_{package['ab_year']}_"
        f"{safe_name}_{package['manager_pn']}_START.html"
    )


def generate(
    sap_path: Path,
    rb_year: int,
    manager_pn: str | None = None,
    output_path: Path | None = None,
    dialog_type: str = "annual",
) -> tuple[Path, dict[str, Any]]:
    frame = load_sap_data(sap_path)
    selected_pn, selected_pack = choose_manager(manager_index(frame), manager_pn)
    payload = build_payload(selected_pn, selected_pack, rb_year, dialog_type=dialog_type)
    target = output_path or (PROTOTYPE_DIR / "output" / output_filename(payload))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_html(payload), encoding="utf-8")
    return target, payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sap", type=Path, default=DEFAULT_SAP_PATH, help="SAP-EXPORT.xlsx")
    parser.add_argument("--manager-pn", help="Personalnummer der vorgesetzten Person")
    parser.add_argument("--rb-year", type=int, default=date.today().year, help="Rückblickjahr")
    parser.add_argument("--output", type=Path, help="Optionale HTML-Zieldatei")
    parser.add_argument("--dialog-type", choices=("annual", "probation"), default="annual", help="Gesprächsart")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target, payload = generate(
        sap_path=args.sap,
        rb_year=args.rb_year,
        manager_pn=args.manager_pn,
        output_path=args.output,
        dialog_type=args.dialog_type,
    )
    print(f"Erstellt: {target}")
    print(
        f"Vorgesetzte Person: {payload['package']['manager_name']} "
        f"({payload['package']['manager_pn']})"
    )
    print(f"Mitarbeitende: {len(payload['employees'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
