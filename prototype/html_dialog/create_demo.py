"""Erzeugt eine direkt öffnbare, rein synthetische Demo-Arbeitsmappe."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

from generate_package import COMPETENCIES, render_html


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from webapp.competency_model import COMPETENCY_MODEL  # noqa: E402


OUTPUT = ROOT / "demo" / "MD_Arbeitsmappe_Demo.html"


def previous_goals() -> list[dict[str, str]]:
    return [
        {
            "id": "previous-1",
            "title": "Bearbeitungszeiten im Fachprozess reduzieren",
            "criteria": "Die mittlere Bearbeitungszeit sinkt um mindestens zehn Prozent.",
            "steps": "Ist-Zustand messen, zwei Verbesserungen testen und Resultate dokumentieren.",
            "target_date": "2025-12-31",
            "achievement": "",
            "review": "",
        },
        {
            "id": "previous-2",
            "title": "Wissenstransfer im Team stärken",
            "criteria": "Vier kurze Wissensaustausche sind durchgeführt und dokumentiert.",
            "steps": "Themen sammeln, Termine planen und Unterlagen zentral ablegen.",
            "target_date": "2025-12-31",
            "achievement": "",
            "review": "",
        },
    ]


def employee(number: str, first: str, last: str, *, position: str, entry: str = "2020-01-01", exit_date: str = "", probation: str = "") -> dict:
    return {
        "case_id": f"2025-990001-{number}",
        "employee": {
            "pn": number,
            "first_name": first,
            "last_name": last,
            "full_name": f"{first} {last}",
            "position": position,
            "org_unit": "Demoorganisation · Fachbereich Services",
            "employment_degree": "100",
            "entry_date": entry,
            "exit_date": exit_date,
            "probation_end": probation,
            "employment_assignment": "1",
            "secondary_employment": "",
        },
        "scope": "",
        "scope_reason": "",
        "no_md_reason": "",
        "no_md_note": "",
        "suggestion": {"scope": "full", "reason": "Regulärer jährlicher Mitarbeitenden-Dialog", "is_special": False},
        "period_start": max("2025-01-01", entry),
        "period_end": min("2025-12-31", exit_date) if exit_date else "2025-12-31",
        "checkpoint_notes": [],
        "previous_goals": previous_goals(),
        "previous_development_goals": [],
        "review": {
            "dialog_date": "",
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
            "performance_goals": [{"id": f"goal-{number}-1", "title": "", "criteria": "", "steps": "", "target_date": ""}],
            "open_goals_text": "",
            "development_goals": [],
            "nep": "",
            "nep_notes": "",
            "general_notes": "",
        },
        "meta": {"updated_at": "", "pdf_exported_at": "", "archived": False},
        "document_tracking": {
            "review": {"status": "preparation", "note": ""},
            "outlook": {"status": "preparation", "note": ""},
            "no_md": {"status": "preparation", "note": ""},
        },
    }


def complete_review(item: dict, *, rating: str = "B – sehr gut", agreement: str = "Ja") -> None:
    for goal in item["previous_goals"]:
        goal["achievement"] = "Erreicht"
        goal["review"] = "Das Ziel wurde erreicht; die Wirkung ist im Arbeitsalltag sichtbar."
    item["review"].update({
        "performance": "Die vereinbarten Aufgaben wurden zuverlässig und in guter Qualität erfüllt.",
        "overall_rating": rating,
        "agreement": agreement,
        "secondary_employment_current": "Ja",
    })


def complete_outlook(item: dict) -> None:
    item["outlook"]["performance_goals"][0].update({
        "title": "Digitale Fallbearbeitung vereinfachen",
        "criteria": "Zwei priorisierte Verbesserungen sind bis Ende Jahr umgesetzt.",
        "steps": "Ablauf aufnehmen, Varianten testen und im Team auswerten.",
        "target_date": "2026-12-31",
    })


def build_demo() -> dict:
    anna = employee("700001", "Anna", "Keller", position="Fachspezialistin Personal")
    anna["scope"] = "full"
    anna["review"]["dialog_date"] = "2026-01-16"
    anna["previous_goals"][0].update({"achievement": "Teilweise erreicht", "review": "Ein erster Verbesserungsschritt ist umgesetzt; die Wirkung wird im ersten Quartal weiter beobachtet."})
    anna["previous_development_goals"] = [{
        "id": "previous-development-anna-1",
        "competency": "Kooperationsfähigkeit",
        "title": "Wissen im Team strukturierter weitergeben",
        "criteria": "Zwei Wissenstransfers wurden durchgeführt.",
        "steps": "Praxisfälle auswählen, Austausch vorbereiten und Erkenntnisse dokumentieren.",
        "target_date": "2025-11-30",
        "achievement": "",
        "review": "",
    }]
    anna["review"]["performance"] = "Anna hat die Jahresziele mit hoher Eigenständigkeit bearbeitet."
    anna["review"]["competencies"] = [{"id": "competency-anna", "competency": "Planungs- und Organisationsfähigkeit", "comment": "Priorisiert auch bei hoher Auslastung nachvollziehbar und hält Zusagen zuverlässig ein."}]

    beat = employee("700002", "Beat", "Meier", position="Projektleiter Digitalisierung")
    beat["scope"] = "full"
    beat["review"]["dialog_date"] = "2026-01-09"
    beat["outlook"]["dialog_date"] = "2026-01-09"
    complete_review(beat, rating="D – genügend", agreement="Nein")
    complete_outlook(beat)
    beat["review"]["manager_comment"] = "Die Gesamtbeurteilung wurde ausführlich besprochen."
    beat["review"]["employee_comment"] = "Die mitarbeitende Person ist mit der Gesamtbeurteilung nicht einverstanden."

    celine = employee("700003", "Céline", "Frei", position="Sachbearbeiterin", entry="2025-08-01", probation="2025-10-31")
    celine["scope"] = "review_only"
    celine["scope_reason"] = "Probezeit beendet; bis Jahresende verbleiben sechs Monate oder weniger."
    celine["suggestion"] = {"scope": "review_only", "reason": "Probezeit endete am 31.10.2025", "is_special": True}
    celine["review"]["dialog_date"] = "2025-11-03"

    david = employee("700004", "David", "Roth", position="Fachspezialist", exit_date="2025-06-30")
    david["scope"] = "none"
    david["no_md_reason"] = "Pensionierung"
    david["no_md_note"] = "Austritt per 30. Juni; kein weiterer MD erforderlich."
    david["suggestion"] = {"scope": "none", "reason": "Pensionierung im ersten Halbjahr", "is_special": True}

    eva = employee("700005", "Eva", "Bühler", position="Teamleiterin")
    eva["suggestion"] = {"scope": "review_only", "reason": "Interner Übertritt per 30.09.2025; abschliessende Standortbestimmung empfohlen", "is_special": True}

    farid = employee("700006", "Farid", "Yilmaz", position="Controller")
    farid["scope"] = "outlook_only"
    farid["scope_reason"] = "Der Probezeitrückblick wurde unterjährig bereits abgeschlossen; am Jahresende folgt der Ausblick."
    farid["suggestion"] = {"scope": "outlook_only", "reason": "Probezeitrückblick wurde unterjährig bereits durchgeführt", "is_special": True}
    farid["checkpoint_notes"] = [
        {"date": "2025-05-14", "title": "Standortgespräch", "text": "Priorisierung bei parallelen Aufträgen besprochen; wöchentliche Planung als Massnahme vereinbart."},
        {"date": "2025-09-18", "title": "Zwischenstand", "text": "Die neue Planungsroutine funktioniert gut. Nächster Fokus: frühzeitige Abstimmung mit Schnittstellen."},
    ]

    gina = employee("700007", "Gina", "Schmid", position="Ehemalige Fachmitarbeiterin", exit_date="2025-03-31")
    gina["scope"] = "review_only"
    gina["scope_reason"] = "Abschluss vor Austritt"
    gina["review"]["dialog_date"] = "2025-03-14"
    complete_review(gina)
    gina["meta"]["archived"] = True

    return {
        "schema_version": "1.0",
        "app_version": "0.3.0-demo",
        "package": {
            "package_id": "MD-2025-990001-DEMO2026",
            "manager_pn": "990001",
            "manager_name": "Laura Muster",
            "manager_first_name": "Laura",
            "manager_last_name": "Muster",
            "manager_email": "laura.muster@example.invalid",
            "rb_year": 2025,
            "ab_year": 2026,
            "created_at": "2026-01-05T08:00:00+01:00",
            "saved_at": "",
            "revision": 0,
            "s_mime_required": True,
            "business_device_only": True,
            "previous_cycles": [
                {"label": "Rückblick 2024 · Ausblick 2025 (Archiv)", "file": "MD_Dialog_2024_2025_Archiv.html"},
                {"label": "Rückblick 2023 · Ausblick 2024 (Archiv)", "file": "MD_Dialog_2023_2024_Archiv.html"},
            ],
        },
        "configuration": {
            "competencies": COMPETENCIES,
            "competency_model": deepcopy(COMPETENCY_MODEL),
            "no_md_reasons": ["Austritt", "Pensionierung", "Wechsel der vorgesetzten Person", "Neueintritt", "Längere Abwesenheit", "Anderer Grund"],
        },
        "employees": [anna, beat, celine, david, eva, farid, gina],
    }


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render_html(build_demo()), encoding="utf-8")
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
