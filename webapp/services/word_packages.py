"""Erstellt versionierte Word-Ausgaben; Erzeugung ist kein Versandnachweis."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import uuid
from datetime import date, datetime
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from .packages import _filename_part, _secondary_employment_text, bounded_review_period
from .word_templates import render_word_form


def load_word_config(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
        templates = content["templates"]
        if not isinstance(templates, dict) or set(templates) - {"review", "outlook", "probation"}:
            raise ValueError("Unbekannte Vorlagenart")
        result = {}
        for key, value in templates.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError("Vorlagenpfad ist leer")
            template = Path(value).expanduser()
            result[key] = str(template if template.is_absolute() else path.parent / template)
        return result
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError("Word-Konfiguration nicht lesbar; erwartet wird ein JSON-Objekt mit «templates».") from exc


def word_template_status(paths: dict) -> dict:
    names = {"review": "Rückblick", "outlook": "Ausblick", "probation": "Rückblick Probezeit"}
    missing = [name for kind, name in names.items() if not paths.get(kind) or not Path(paths[kind]).is_file()]
    return {"ready": not missing, "missing": missing}


def prior_goals(connection, *, employee_pn: str, assignment: str, year: int):
    """Eindeutige Quelle für den Zielzeitraum; mehrere Quellen nicht vermischen."""
    previous = connection.execute(
        """SELECT dc.case_id, dc.data_json FROM dialog_cases dc
           JOIN cycles c ON c.id = dc.cycle_id
           WHERE dc.employee_pn = ? AND dc.employment_assignment = ?
             AND c.outlook_year = ? AND dc.data_json <> ''""",
        (employee_pn, assignment, year),
    ).fetchall()
    sources = []
    for row in previous:
        try:
            outlook = json.loads(row["data_json"]).get("outlook") or {}
            performance = outlook.get("performance_goals") or []
            development = outlook.get("development_goals") or []
            if not isinstance(performance, list) or not isinstance(development, list):
                raise ValueError()
            # Leere Platzhalter zählen nicht als Quelle.
            performance = [g for g in performance if any(str(g.get(k, "") or "").strip() for k in ("title", "criteria", "steps", "target_date"))]
            development = [g for g in development if any(str(g.get(k, "") or "").strip() for k in ("title", "criteria", "steps", "target_date"))]
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"Vorjahresdaten für PN {employee_pn} sind nicht lesbar.") from exc
        if performance or development:
            source = {"case_id": row["case_id"]}
            if outlook.get('word_pdf_import_id'):
                source['word_pdf_import_id'] = outlook['word_pdf_import_id']
            sources.append((performance, development, source))
    pdf_versions = connection.execute(
        """SELECT * FROM word_pdf_goal_versions WHERE employee_pn=? AND assignment_number=?
           AND goal_year=? AND is_current=1""", (employee_pn, assignment, year)
    ).fetchall()
    for version in pdf_versions:
        if version['case_id'] and any(source[2].get('case_id') == version['case_id'] for source in sources):
            continue
        goals = json.loads(version['goals_json'])
        sources.append((goals['performance_goals'], goals['development_goals'], {'word_pdf_import_id': version['import_id']}))
    historical = connection.execute(
        """SELECT * FROM historical_goals WHERE employee_pn = ? AND goal_year = ?
           AND (assignment_number = ? OR assignment_number = '')
           ORDER BY legacy_form_import_id, goal_kind, sequence, id""",
        (employee_pn, year, assignment),
    ).fetchall()
    if any(not row["assignment_number"] for row in historical):
        count = connection.execute(
            "SELECT COUNT(*) FROM employment_assignments WHERE person_number = ? AND active = 1",
            (employee_pn,),
        ).fetchone()[0]
        if count != 1:
            raise ValueError(f"Vorjahresziele für PN {employee_pn} sind keiner eindeutigen Anstellung zugeordnet.")
    for source_id in dict.fromkeys(row["legacy_form_import_id"] for row in historical):
        rows = [dict(row) for row in historical if row["legacy_form_import_id"] == source_id]
        sources.append(([g for g in rows if g["goal_kind"] == "performance"], [g for g in rows if g["goal_kind"] == "development"], {"legacy_form_import_id": source_id}))
    if len(sources) > 1:
        raise ValueError(f"Für PN {employee_pn}, Ans. {assignment}, Zieljahr {year} liegen mehrere Zielquellen vor. Bitte vor der Word-Erzeugung klären.")
    return sources[0] if sources else ([], [], {})


def _date_text(value):
    return date.fromisoformat(value).strftime("%d.%m.%Y")


def create_word_package(connection: sqlite3.Connection, *, cycle_id: int, manager_pn: str,
                        template_paths: dict, output_dir: Path, case_id: str = "") -> tuple[Path, dict]:
    cycle = connection.execute("SELECT * FROM cycles WHERE id = ?", (cycle_id,)).fetchone()
    if not cycle:
        raise LookupError("Jahresprozess nicht gefunden.")
    manager = connection.execute("SELECT * FROM employees WHERE pn = ?", (manager_pn,)).fetchone()
    if not manager:
        raise ValueError("Die Stammdaten der Führungskraft fehlen.")
    cases = connection.execute(
        """SELECT dc.*, e.first_name, e.last_name, e.position, e.org_unit,
                  e.entry_date, e.exit_date, e.probation_end, e.secondary_employment,
                  COALESCE(de.event_type, 'annual') AS event_type
           FROM dialog_cases dc JOIN employees e ON e.pn = dc.employee_pn
           LEFT JOIN dialog_events de ON de.legacy_case_id = dc.case_id
           WHERE dc.cycle_id = ? AND dc.manager_pn = ? AND dc.active = 1
             AND (? = '' OR dc.case_id = ?) ORDER BY e.last_name, e.first_name, dc.id""",
        (cycle_id, manager_pn, case_id, case_id),
    ).fetchall()
    if not cases:
        raise LookupError("Keine aktiven MD-Fälle für diese Auswahl gefunden.")
    numbers = list(dict.fromkeys([manager_pn, *(row["employee_pn"] for row in cases)]))
    conflicts = connection.execute(
        f"SELECT COUNT(*) FROM sap_import_issues WHERE sap_import_id = ? AND status = 'open' AND severity = 'blocking' AND person_number IN ({','.join('?' for _ in numbers)})",
        (cycle["sap_import_id"], *numbers),
    ).fetchone()[0]
    if conflicts:
        raise ValueError("Vor der Word-Erzeugung müssen die offenen SAP-Zuordnungskonflikte geklärt werden.")
    export_id = "WORD-" + uuid.uuid4().hex
    directory = output_dir / export_id
    directory.mkdir(parents=True)
    manifest = {"export_id": export_id, "cycle_id": cycle_id, "manager_pn": manager_pn,
                "created_at": datetime.now().astimezone().isoformat(timespec="seconds"), "documents": [], "skipped_cases": []}
    filename = f"MD_Word_{cycle['review_year']}_{cycle['outlook_year']}_{_filename_part(manager_pn)}_{export_id[-8:]}.zip"
    path = directory / filename
    try:
        with ZipFile(path, "w", ZIP_DEFLATED) as bundle:
            for case in cases:
                assignment = case["employment_assignment"]
                if not assignment:
                    raise ValueError(f"Bei PN {case['employee_pn']} fehlt die Anstellungsnummer.")
                scope = case["official_scope"] or case["suggested_scope"]
                if scope == "none":
                    manifest["skipped_cases"].append(case["case_id"])
                    continue
                if scope not in {"full", "review_only", "outlook_only"}:
                    raise ValueError("Unbekannter MD-Umfang.")
                is_probation = case["event_type"] == "probation_review"
                kinds = (["probation" if is_probation else "review"] if scope in {"full", "review_only"} else [])
                if scope in {"full", "outlook_only"}:
                    kinds.append("outlook")
                for kind in kinds:
                    template_path = template_paths.get(kind)
                    if not template_path or not Path(template_path).is_file():
                        raise ValueError(f"Die Word-Vorlage «{kind}» ist noch nicht lokal konfiguriert.")
                    year = cycle["outlook_year"] if kind == "outlook" else cycle["review_year"]
                    if case["period_start"] and case["period_end"] and (kind != "outlook" or case["event_type"] != "annual"):
                        start, end = case["period_start"], case["period_end"]
                    elif kind == "probation":
                        start, end = case["entry_date"], case["probation_end"]
                        if not start or not end:
                            raise ValueError("Für den Probezeit-Rückblick fehlt der bestätigte Zeitraum.")
                    else:
                        start, end = bounded_review_period(year, case["entry_date"], case["exit_date"])
                    if date.fromisoformat(start) > date.fromisoformat(end):
                        raise ValueError("Der Dokumentzeitraum endet vor seinem Beginn.")
                    year = date.fromisoformat(end).year
                    performance, development, source = prior_goals(connection, employee_pn=case["employee_pn"], assignment=assignment, year=year) if kind == "review" else ([], [], {})
                    fields = {
                        "name": f"{case['first_name']} {case['last_name']}".strip(), "pn": case["employee_pn"],
                        "funktion": case["position"], "oe": case["org_unit"],
                        "name_vg": f"{manager['first_name']} {manager['last_name']}".strip(), "pn_vg": manager_pn,
                        "datum_von": _date_text(start), "datum_bis": _date_text(end),
                        "nebenbeschaeftigung": _secondary_employment_text(connection, employee_pn=case["employee_pn"], employment_assignment=assignment, fallback=case["secondary_employment"]),
                    }
                    document = render_word_form(Path(template_path), kind=kind, fields=fields, performance_goals=performance, development_goals=development)
                    label = {"review": "Rueckblick", "outlook": "Ausblick", "probation": "Rueckblick_Probezeit"}[kind]
                    document_name = f"{label}_{year}_{_filename_part(case['last_name'])}_{_filename_part(case['first_name'])}_Ans{_filename_part(assignment)}_{_filename_part(case['employee_pn'])}.docx"
                    if document_name in bundle.namelist():
                        raise ValueError("Die Auswahl enthält mehrere Ereignisse mit demselben Dokumentnamen. Bitte die Fallzuordnung klären.")
                    bundle.writestr(document_name, document)
                    manifest["documents"].append({"case_id": case["case_id"], "kind": kind, "filename": document_name,
                        "period_start": start, "period_end": end, "sha256": hashlib.sha256(document).hexdigest(),
                        "template_sha256": hashlib.sha256(Path(template_path).read_bytes()).hexdigest(),
                        "goal_source": source, "performance_goals": len(performance), "development_goals": len(development)})
        if not manifest["documents"]:
            raise ValueError("Für die Auswahl sind keine Rückblick- oder Ausblickvorlagen vorgesehen.")
        manifest["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        (directory / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        shutil.rmtree(directory)
        raise
    return path, manifest
