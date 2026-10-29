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

from .form_data import _filename_part, _secondary_employment_text, bounded_review_period
from .word_templates import render_word_form, render_feedback_form


def preparation_templates(paths):
    bundled = Path(__file__).resolve().parents[2] / 'templates' / 'preparation'
    return {kind: Path(paths.get(kind) or bundled / filename) for kind, filename in
            [('reflection', 'MD_Reflexion.docx'), ('feedback', 'MD_Feedback.docx')]}


def load_word_config(path: Path) -> dict[str, str]:
    path = Path(path).expanduser().resolve()
    if not path.exists():
        return {}
    try:
        content = json.loads(path.read_text(encoding="utf-8-sig"))
        templates = content["templates"]
        if not isinstance(templates, dict) or set(templates) - {"review", "outlook", "probation", "reflection", "feedback"}:
            raise ValueError("Unbekannte Vorlagenart")
        result = {}
        for key, value in templates.items():
            if not isinstance(value, str):
                raise ValueError("Vorlagenpfad muss Text sein")
            if not value.strip():
                continue
            template = Path(value.strip()).expanduser()
            result[key] = str((template if template.is_absolute() else path.parent / template).resolve())
        return result
    except json.JSONDecodeError as exc:
        raise ValueError(f"Word-Konfiguration {path}: ungültiges JSON in Zeile {exc.lineno}, Spalte {exc.colno}. "
                         "Die Datei muss mit zwei schliessenden Klammern enden: eine für templates, eine für das äussere Objekt.") from exc
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"Word-Konfiguration {path} nicht lesbar; erwartet wird ein JSON-Objekt mit «templates».") from exc


def word_template_status(paths: dict) -> dict:
    from flask import current_app, has_app_context
    names = {"review": "Rückblick", "outlook": "Ausblick", "probation": "Rückblick Probezeit"}
    files = [{'kind':kind,'name':name,'path':paths.get(kind,''),
              'exists':bool(paths.get(kind) and Path(paths[kind]).is_file())} for kind,name in names.items()]
    missing = [item['name'] for item in files if not item['exists']]
    config = current_app.config if has_app_context() else {}
    config_path = config.get('WORD_CONFIG_PATH','')
    return {"ready": not missing, "missing": missing, 'files':files,
            'config_path':config_path, 'config_loaded':config.get('WORD_CONFIG_LOADED',False),
            'config_error':config.get('WORD_CONFIG_ERROR',''),
            'config_override':config.get('WORD_CONFIG_ENV_OVERRIDE',False),
            'txt_file':bool(config_path and Path(config_path+'.txt').is_file())}


def prior_goals(connection, *, employee_pn: str, assignment: str, year: int, sources_only: bool = False):
    """Eindeutige Quelle für den Zielzeitraum; mehrere Quellen nicht vermischen."""
    previous = connection.execute(
        """SELECT dc.case_id, dc.data_json FROM dialog_cases dc
           JOIN cycles c ON c.id = dc.cycle_id
           WHERE dc.employee_pn = ? AND dc.employment_assignment = ?
             AND c.outlook_year = ? AND dc.data_json <> '' ORDER BY dc.case_id""",
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
           AND goal_year=? AND is_current=1 ORDER BY id""", (employee_pn, assignment, year)
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
    from .goal_review import confirmed_sources, retired_original
    sources=[source for source in sources if not retired_original(connection,source[2])]
    corrected_sources = confirmed_sources(connection, employee_pn, assignment, year)
    sources.extend(corrected_sources)
    if sources_only:
        return sources
    from webapp.migrations import available
    if available(connection) and not corrected_sources and connection.execute('''SELECT 1 FROM legacy_form_imports l
        JOIN hr_goal_sources s ON s.sha256=l.sha256 WHERE l.employee_pn=? AND l.assignment_number=? AND l.goal_year=?
        AND NOT EXISTS(SELECT 1 FROM hr_goal_revisions r WHERE r.source_id=s.id AND r.status='confirmed')''',
        (employee_pn,assignment,year)).fetchone():
        raise ValueError('Nachgereichte Zielquelle zuerst am Original prüfen und bestätigen.')
    choice=connection.execute('SELECT * FROM workflow_goal_choices WHERE employee_pn=? AND assignment_number=? AND goal_year=?',(employee_pn,assignment,year)).fetchone()
    if choice:
        fingerprint=goal_sources_fingerprint(sources)
        if fingerprint!=choice['sources_fingerprint']:
            raise ValueError(f'Zielquellen für PN {employee_pn}, Ans. {assignment}, Zieljahr {year} haben sich geändert. Bitte die Auswahl unter Zielquellen erneut prüfen.')
        selected=json.loads(choice['source_json'])
        for source in sources:
            if source[2]==selected:return source
    if len(sources) > 1:
        raise ValueError(f"Für PN {employee_pn}, Ans. {assignment}, Zieljahr {year} liegen mehrere Zielquellen vor. Bitte unter «Stammdaten → Zielquellen» vergleichen und eine Quelle auswählen.")
    return sources[0] if sources else ([], [], {})


def missing_goal_hint(connection, *, employee_pn, assignment, year):
    """Explain empty goals without guessing another year or employment."""
    rows = connection.execute(
        """SELECT goal_year AS year, assignment_number AS assignment FROM historical_goals
           WHERE employee_pn=?
           UNION SELECT goal_year, assignment_number FROM word_pdf_goal_versions
           WHERE employee_pn=? AND is_current=1
           ORDER BY year, assignment""", (employee_pn, employee_pn)
    ).fetchall()
    available = ", ".join(f"{r['year']} / Ans. {r['assignment'] or 'ohne Zuordnung'}" for r in rows)
    hint = (f"PN {employee_pn}, Ans. {assignment}: Keine Vorjahresziele für das "
            f"Rückblickjahr {year} gefunden. Import und Zieljahr unter Stammdaten prüfen.")
    if available:
        hint += f" Vorhandene Importzuordnungen: {available}."
    else:
        hint += " Für diese Personalnummer sind keine Word-/PDF-Zielimporte gespeichert."
    return hint


def _date_text(value):
    return date.fromisoformat(value).strftime("%d.%m.%Y")


def feedback_cases(connection,cycle,manager_pn,cases):
    return [c['case_id'] for c in cases if connection.execute('''SELECT 1 FROM reporting_lines
        WHERE sap_import_id=? AND employee_pn=? AND employment_assignment=? AND manager_pn=?''',
        (cycle['sap_import_id'],c['employee_pn'],c['employment_assignment'],manager_pn)).fetchone()]


def create_word_package(connection: sqlite3.Connection, *, cycle_id: int, manager_pn: str,
                        template_paths: dict, output_dir: Path, case_id: str = "", document_kinds: list[str] | None = None,
                        resolved_review: bool = False) -> tuple[Path, dict]:
    if document_kinds is not None and (not case_id or not document_kinds or not set(document_kinds) <= {'review','probation','outlook'}):
        raise ValueError('Bitte eine Person und mindestens einen gültigen Formulartyp auswählen.')
    from webapp.migrations import available
    from .part_responsibilities import resolve,case_rows,assigned_kinds
    modern=available(connection)
    part = None
    if resolved_review:
        from .part_responsibilities import resolve
        if not case_id or document_kinds != ['review']:
            raise ValueError('Die Zielnachreichung erstellt ausschliesslich ausgewählte Rückblicke.')
        part = resolve(connection, case_id)
        if part['manager_pn'] != manager_pn or part['cycle_id'] != cycle_id:
            raise ValueError('Die Verantwortung hat sich geändert. Bitte Auswahl neu prüfen.')
    cycle = connection.execute("SELECT * FROM cycles WHERE id = ?", (cycle_id,)).fetchone()
    if not cycle:
        raise LookupError("Jahresprozess nicht gefunden.")
    manager = connection.execute("SELECT * FROM employees WHERE pn = ?", (manager_pn,)).fetchone()
    if not manager:
        raise ValueError("Die Stammdaten der Führungskraft fehlen.")
    cases = connection.execute(
        """SELECT dc.*, e.first_name, e.last_name, e.position, COALESCE(fo.org_unit,e.org_unit) AS org_unit,
                  e.entry_date, e.exit_date, e.probation_end, e.secondary_employment,
                  COALESCE(de.event_type, 'annual') AS event_type
           FROM dialog_cases dc JOIN employees e ON e.pn = dc.employee_pn
           LEFT JOIN dialog_events de ON de.legacy_case_id = dc.case_id
           LEFT JOIN dialog_form_org_units fo ON fo.dialog_event_id=de.id
           WHERE dc.cycle_id = ? AND dc.manager_pn = ? AND dc.active = 1
             AND (? = '' OR dc.case_id = ?) ORDER BY e.last_name, e.first_name, dc.id""",
        (cycle_id, part['case_manager_pn'] if part else manager_pn, case_id, case_id),
    ).fetchall()
    if modern:
        cases=case_rows(connection,cycle_id,manager_pn,case_id=case_id)
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
                "created_at": datetime.now().astimezone().isoformat(timespec="seconds"), "documents": [], "skipped_cases": [], "goal_warnings": []}
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
                if modern:
                    kinds=[kind for kind in kinds if kind in assigned_kinds(connection,case['case_id'],manager_pn)]
                if document_kinds is not None:
                    if not set(document_kinds) <= set(kinds):
                        raise ValueError('Die Auswahl passt nicht zum aktuellen Pflichtumfang dieser Person.')
                    kinds = [kind for kind in kinds if kind in document_kinds]
                for kind in kinds:
                    part=resolve(connection,case['case_id'],'review' if kind=='probation' else kind) if modern else None
                    template_path = template_paths.get(kind)
                    if not template_path or not Path(template_path).is_file():
                        raise ValueError(f"Die Word-Vorlage «{kind}» ist noch nicht lokal konfiguriert.")
                    year = cycle["outlook_year"] if kind == "outlook" else cycle["review_year"]
                    if part:
                        start,end=part['period_start'],part['period_end']
                    elif case["period_start"] and case["period_end"] and (kind != "outlook" or case["event_type"] != "annual"):
                        start, end = case["period_start"], case["period_end"]
                    elif kind == "probation":
                        start, end = case["entry_date"], case["probation_end"]
                        if not start or not end:
                            raise ValueError("Für den Probezeit-Rückblick fehlt der bestätigte Zeitraum.")
                    else:
                        start, end = bounded_review_period(year, case["entry_date"], case["exit_date"])
                    if part:
                        start, end = part['period_start'], part['period_end']
                    if date.fromisoformat(start) > date.fromisoformat(end):
                        raise ValueError("Der Dokumentzeitraum endet vor seinem Beginn.")
                    year = date.fromisoformat(end).year
                    performance, development, source = prior_goals(connection, employee_pn=case["employee_pn"], assignment=assignment, year=year) if kind == "review" else ([], [], {})
                    if modern and not resolved_review and source.get('hr_goal_revision_id'):
                        from . import goal_followups
                        revision_id=source['hr_goal_revision_id']
                        goal_followups.inputs(connection,revision_id,case['case_id'],template_paths)
                        decision=goal_followups.latest_decision(connection,revision_id,case['case_id'])
                        if goal_followups.decision_effective(decision,[]):
                            raise ValueError('Die Folgeentscheidung zur Zielnachreichung zuerst prüfen. Keine neue leere Rückblickvorlage erzeugt.')
                    if kind == "review" and not performance and not development:
                        manifest["goal_warnings"].append(missing_goal_hint(connection, employee_pn=case["employee_pn"], assignment=assignment, year=year))
                    fields = {
                        "name": f"{case['first_name']} {case['last_name']}".strip(), "pn": case["employee_pn"],
                        "funktion": case["position"], "oe": part['form_org_unit'] if part else case["org_unit"],
                        "name_vg": f"{manager['first_name']} {manager['last_name']}".strip(), "pn_vg": manager_pn,
                        "datum_von": _date_text(start), "datum_bis": _date_text(end),
                        "nebenbeschaeftigung": _secondary_employment_text(connection, employee_pn=case["employee_pn"], employment_assignment=assignment, fallback=case["secondary_employment"]),
                    }
                    document = render_word_form(Path(template_path), kind=kind, fields=fields, performance_goals=performance, development_goals=development)
                    label = {"review": "Rückblick", "outlook": "Ausblick", "probation": "Rückblick_Probezeit"}[kind]
                    document_name = f"{label}_{year}_{_filename_part(case['last_name'])}_{_filename_part(case['first_name'])}_{_filename_part(case['employee_pn'])}.docx"
                    if resolved_review or modern:
                        document_name = document_name[:-5] + f"_Ans_{_filename_part(assignment)}_{hashlib.sha256(case['case_id'].encode()).hexdigest()[:8]}.docx"
                    person_cases = [c for c in cases if c['employee_pn'] == case['employee_pn'] and (c['official_scope'] or c['suggested_scope']) != 'none']
                    if len(person_cases) > 1:
                        case_number = next(i for i, c in enumerate(person_cases, 1) if c['case_id'] == case['case_id'])
                        document_name = f"Fall_{case_number}/" + document_name
                    if document_name in bundle.namelist():
                        raise ValueError("Die Auswahl enthält mehrere Ereignisse mit demselben Dokumentnamen. Bitte die Fallzuordnung klären.")
                    bundle.writestr(document_name, document)
                    responsibility=({key:part[key] for key in ('obligation_id','kind','manager_pn','recipient_email','form_org_unit','form_org_source','period_start','period_end','responsibility_revision')} if part else {})
                    manifest["documents"].append({**({'responsibility':responsibility} if part else {}),"case_id": case["case_id"], "kind": kind, "filename": document_name,
                        "period_start": start, "period_end": end, "sha256": hashlib.sha256(document).hexdigest(),
                        "template_sha256": hashlib.sha256(Path(template_path).read_bytes()).hexdigest(),
                        "goal_source": source, "performance_goals": len(performance), "development_goals": len(development)})
            if manifest["documents"]:
                manifest['attachments'] = []
                for kind, template in (preparation_templates(template_paths) if document_kinds is None else {}).items():
                    if modern and kind=='feedback' and not feedback_cases(connection,cycle,manager_pn,cases):
                        continue
                    if not template.is_file():
                        raise ValueError(f'Die Beilage «{kind}» fehlt. Vorlage unter templates/preparation prüfen oder in instance/word_config.json konfigurieren.')
                    raw = template.read_bytes()
                    if kind == 'feedback':
                        raw = render_feedback_form(template, manager_name=f"{manager['first_name']} {manager['last_name']}".strip(), manager_pn=manager_pn)
                        name = f"NameMA_Feedback_an_{_filename_part(manager['last_name'])}_{_filename_part(manager['first_name'])}_{_filename_part(manager_pn)}.docx"
                    else:
                        name = 'MD_Reflexion.docx'
                    bundle.writestr(name, raw)
                    manifest['attachments'].append({'kind':kind, 'filename':name, 'sha256':hashlib.sha256(raw).hexdigest(), 'template_sha256':hashlib.sha256(template.read_bytes()).hexdigest()})
        if not manifest["documents"]:
            raise ValueError("Für die Auswahl sind keine Rückblick- oder Ausblickvorlagen vorgesehen.")
        manifest["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        (directory / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        shutil.rmtree(directory)
        raise
    return path, manifest


def goal_sources_fingerprint(sources):
    return hashlib.sha256(json.dumps(sources,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
