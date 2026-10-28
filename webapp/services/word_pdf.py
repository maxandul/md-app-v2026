"""Vorprüfung textbasierter Word-PDFs, unabhängig vom Arbeitsmappen-Datenblock.

Die Extraktion schreibt keine Fachdaten. Fehlende oder mehrdeutige Angaben bleiben
offen; insbesondere wird Einigkeit weder abgefragt noch abgeleitet.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .documents import inspect_pdf


# Stable keys are shared by extraction, review and character-count exports.
NARRATIVE_FIELDS = {
    'general_comment': ('Allgemeine Bemerkungen', r'Gibt es allgemeine Bemerkungen'),
    'performance_comment': ('Leistung / ergänzender Freitext', r'Optionales Freitext-Feld|Wie wird die bisherige Leistung eingeschätzt|Wie wird die Leistung'),
    'manager_comment': ('Bemerkungen der Führungskraft', r'Gibt es Bemerkungen der vorgesetzten Person'),
    'employee_comment': ('Bemerkungen der Mitarbeitenden', r'Gibt es Bemerkungen des/der Mitarbeitenden\?'),
    'higher_manager_comment': ('Bemerkungen der nächsthöheren Führungskraft', r'Gibt es Bemerkungen der nächsthöheren vorgesetzten Person'),
    'higher_employee_comment': ('Bemerkungen zum Gespräch mit der nächsthöheren Führungskraft', r'Gibt es Bemerkungen des/der Mitarbeitenden zum Gespräch'),
    'sap_comment': ('Präzisierung zu Bewilligungen', r'Falls nicht vollständig und/oder aktuell, bitte präzisieren'),
    'sap_activities': ('Aufgeführte Nebenbeschäftigungen / öffentliche Ämter', r'Aktuell bewilligte und als derzeit ausgeübt erfasste Nebenbeschäftigungen'),
    'career_comment': ('Bemerkungen zur Laufbahnentwicklung', r'Gibt es Bemerkungen bezüglich laufbahnorientierter Entwicklung'),
    'career_choice': ('Laufbahnwunsch laut Formular', r'Besteht ein Wunsch bezüglich laufbahnorientierter Entwicklung'),
}


def _answer(pattern, text):
    values = re.findall(pattern + r'\s*(Ja|Nein)\b', text, re.I)
    return values[0].lower() if len(values) == 1 else ''


def _field_text(value):
    value = value.strip()
    return '' if value.lower().startswith(('klicken sie', 'klicken oder tippen', 'bitte wählen')) else value


DATE = r"\d{2}\.\d{2}\.\d{4}"


def _single(pattern: str, text: str, label: str, issues: list[str]) -> str:
    values = set(re.findall(pattern, text, re.IGNORECASE))
    if len(values) != 1:
        issues.append(f"{label}: nicht eindeutig lesbar oder nicht ausgefüllt.")
        return ""
    return values.pop()


def _iso_date(value: str, label: str, issues: list[str]) -> str:
    if not value:
        return ""
    try:
        return datetime.strptime(value, "%d.%m.%Y").date().isoformat()
    except ValueError:
        issues.append(f"{label}: ungültiges Datum.")
        return ""


def merge_goal_continuations(goals):
    """Join a title-less continuation at the top of the next PDF page."""
    merged = []
    for goal in goals:
        previous = merged[-1] if merged else None
        evidence = goal.get('evidence', {})
        prior = previous.get('evidence', {}) if previous else {}
        if (previous and not goal.get('title')
            and previous.get('competency', '') == goal.get('competency', '')
            and evidence.get('page', 0) == prior.get('last_page', prior.get('page', 0)) + 1
            and evidence.get('top', 1000) < 150):
            for field in ('title', 'criteria', 'steps', 'target_date'):
                if goal.get(field):
                    previous[field] = (previous.get(field, '') + '\n' + goal[field]).strip()
            prior['last_page'] = evidence['page']
        else:
            merged.append(goal)
    return merged


def inspect_word_pdf(path: Path) -> dict:
    inspection = inspect_pdf(path)
    result = parse_word_pdf_text(inspection.text, page_count=inspection.page_count)
    result.update(extract_form_content(path, result['data'].get('document_kind', ''), probation=result['data'].get('probation')=='ja'))
    for key in ('performance_goals', 'development_goals'):
        result[key] = merge_goal_continuations(result[key])
    result['data']['no_md_reason'] = result.pop('no_md_reason', '')
    result['issues'].extend(result.pop('content_issues'))
    result['data'].update(result.pop('scalar_fields', {}))
    from .pdf_validation import validate_format
    validate_format(path, result)
    result['status'] = 'needs_review'
    return result


def parse_word_pdf_text(text: str, *, page_count: int = 0) -> dict:
    # Nur für Anker/Einzelwerte normalisieren. Rohtext für die spätere
    # Tabellenrekonstruktion erhalten; echte Bindestriche nicht blind entfernen.
    flat = re.sub(r"\s+", " ", text.replace("\u00ad", "")).strip()
    issues: list[str] = []
    data: dict[str, str] = {}
    kinds = set(re.findall(
        r"Mitarbeitenden[-–]Dialog\s*\(MD\)\s*[-–]\s*(Rückblick|Ausblick)",
        flat, re.IGNORECASE,
    ))
    kinds = {kind.casefold() for kind in kinds}
    if len(kinds) != 1:
        issues.append("Kein eindeutiger Word-MD-Dokumenttyp erkannt.")
    else:
        data["document_kind"] = "review" if "rückblick" in kinds else "outlook"
        data['probation'] = 'ja' if re.search(r'Rückblick auf (?:die )?Probezeit', flat, re.I) else 'nein'
        data["pn"] = _single(r"\bPN\s*:\s*(\d+)\b", flat, "Personalnummer", issues)
        data["manager_pn"] = _single(r"\bPN\s+VG\s*:\s*(\d+)\b", flat, "Personalnummer VG", issues)
        periods = set(re.findall(
            rf"(?:Rückblick|Ausblick)\s+auf\s*:\s*({DATE})\s+bis\s*({DATE})", flat,
            re.IGNORECASE,
        ))
        if len(periods) == 1:
            start, end = periods.pop()
            data["period_start"] = _iso_date(start, "Zeitraum von", issues)
            data["period_end"] = _iso_date(end, "Zeitraum bis", issues)
            if data["period_start"] > data["period_end"] and data["period_end"]:
                issues.append("Der Zeitraum endet vor seinem Beginn.")
        else:
            issues.append("Zeitraum: nicht eindeutig lesbar oder nicht ausgefüllt.")
        label = 'Rückblick' if data['document_kind'] == 'review' else 'Ausblick'
        data['conducted'] = _answer(rf'Wird der {label}(?: auf (?:die )?Probezeit)? durchgeführt\?', flat)
        if not data['conducted']:
            issues.append('Durchführung: nicht eindeutig lesbar oder nicht ausgefüllt.')
        date_issues = [] if data['conducted'] == 'nein' else issues
        dialog_date = _single(rf"Gespräch\s+vom\s*:\s*({DATE})", flat, "Gesprächsdatum", date_issues)
        data['dialog_date'] = _iso_date(dialog_date, 'Gesprächsdatum', date_issues)
        if data['document_kind'] == 'review':
            data['higher_manager_requested'] = _answer(r'Ist ein Gespräch mit der nächsthöheren vorgesetzten Person gewünscht\?', flat)
            data['sap_current'] = _answer(r'Sind die oben aufgeführten Bewilligungen vollständig und aktuell\?(?:\s*\(Nur relevant beim ordentlichen MD mit automatisiertem Versand\))?', flat)
        else:
            data['career_requested'] = _answer(r'Besteht ein Wunsch bezüglich laufbahnorientierter Entwicklung\?', flat)
    if not flat:
        issues.append("Kein lesbarer Text: Scan oder Bild-PDF muss manuell geprüft werden.")
    if data.get('probation') == 'ja':
        decision = re.findall(r'Wird das Arbeitsverhältnis weitergeführt\?\s*(Ja|Nein)\b', flat, re.I)
        data['employment_continues'] = decision[0].lower() if len(decision)==1 else ''
    return {
        "data": data,
        "issues": issues,
        "page_count": page_count,
        "text_length": len(flat),
        "text": text,
        "status": "needs_review" if issues else "basic_fields_readable",
    }


def extract_form_content(path: Path, kind: str, *, probation: bool = False) -> dict:
    from .pdf_cells import read_cells
    from .legacy_forms import COMPETENCY_TAGS
    performance, development, assessments, fields, issues = [], [], {}, [], []
    narratives, scalar_fields, field_evidence = {}, {}, {}
    competency_anchors = set()
    no_md_reason = ''
    context = ''
    assessment_done = False
    goal_rows = 0
    for page in read_cells(path):
        cells, runs = page['cells'], page['runs']
        # Nur Überschriften ausserhalb der Eingabefelder setzen den Kontext.
        external = [r for r in runs if not any(c['x0']-.2 <= r['x'] < c['x1'] and c['y0'] <= r['y'] <= c['y1']+.2 for c in cells)]
        lines = page['external_lines']
        anchors = []
        narrative_anchors = []
        for index, (y, text) in enumerate(lines):
            text = re.sub(r'\s+', ' ', text).strip()
            # Labels can wrap, including the employee's higher-manager comment.
            label = text
            if index+1 < len(lines) and lines[index+1][0]-y < 18:
                label += ' ' + lines[index+1][1]
            for key, (_label, pattern) in NARRATIVE_FIELDS.items():
                if key != 'career_choice' and re.match(pattern, label, re.I):
                    narrative_anchors.append((y, key))
            if 'Falls nein, hier Begründung' in text:
                narrative_anchors.append((y, 'no_md_reason'))
            if re.search(r'Leistungsziele|^1\.\s*Zielvereinbarung', text, re.I):
                anchors.append((y, 'performance'))
            for name in COMPETENCY_TAGS.values():
                if re.sub(r'[\s-]+', '', text).startswith(re.sub(r'[\s-]+', '', name)):
                    anchors.append((y, name))
                    competency_anchors.add(name)
            if re.match(r'\d+(?:\.\d+)*\.\s*(?:Gesamt|Weitere|Bemerkungen|Unterschriften|Entwicklungsperspektiven|Laufbahn|Nebenbeschäftigungen|Gespräch|Anstellungsentscheid|Bestätigung)', text):
                anchors.append((y, ''))
        for key, pattern in (
            ('rating', r'Der Gesamteindruck ist'),
            ('sap_current', r'Sind die oben aufgeführten Bewilligungen vollständig\s*und aktuell'),
            ('career_choice', NARRATIVE_FIELDS['career_choice'][1]),
        ):
            for y, label in lines:
                if not re.match(pattern, label, re.I):
                    continue
                matches = [c for c in cells if c['color']=='blue' and c['x1']-c['x0']<200 and c['y0']<=y<=c['y1']+.2]
                if len(matches)!=1 or key in field_evidence:
                    issues.append('Antwortfeld nicht eindeutig zugeordnet: '+key)
                    scalar_fields[key] = ''
                    continue
                value = _field_text(matches[0]['text'])
                field_evidence[key] = {'page':page['page'],'top':round(matches[0]['y0'],1),'text':value}
                if key=='rating':
                    scalar_fields[key] = {'vorzüglich':'A','sehr gut':'B','gut':'C','genügend':'D','ungenügend':'E'}.get(value.casefold(), '')
                elif key=='sap_current':
                    scalar_fields[key] = value.lower() if value.lower() in ('ja','nein') else ''
                else:
                    narratives['career_choice'] = value
                    scalar_fields['career_requested'] = ('ja' if value in ('Ja','KNF I','KNF II','Führungsverantwortung','Fachführungsverantwortung','Projektverantwortung','Stellvertretung','Anderer Entwicklungswunsch') else 'nein' if value in ('Nein','Kein Entwicklungswunsch') else '')
        rows=[]
        for cell in cells:
            if not rows or abs(rows[-1][0]['y0']-cell['y0'])>.25:
                rows.append([cell])
            else:
                rows[-1].append(cell)
        narrative_index = 0
        narrative_key = ''
        narrative_anchors.sort()
        anchor_index=0
        anchors.sort()
        for row in rows:
            while anchor_index < len(anchors) and anchors[anchor_index][0] < row[0]['y0']:
                context=anchors[anchor_index][1]; assessment_done=False; anchor_index+=1
            while narrative_index < len(narrative_anchors) and narrative_anchors[narrative_index][0] < row[0]['y0']:
                narrative_key = narrative_anchors[narrative_index][1]
                narrative_index += 1
            row.sort(key=lambda c:c['x0'])
            evidence = {'page': page['page'], 'top': round(row[0]['y0'],1)}
            if len(row)==4 and all(c['color']==('blue' if kind=='outlook' else 'grey') for c in row) and context:
                goal_rows+=1
                values=[c['text'] for c in row]
                if not any(values):
                    continue
                goal=dict(zip(('title','criteria','steps','target_date'), values))
                # Tabellen-Zielnummer ist keine Nummerierung innerhalb des Ziels.
                goal['title']=re.sub(r'^\d+\.\s+', '', goal['title'])
                goal['evidence']=evidence
                if context=='performance':
                    performance.append(goal)
                else:
                    goal['competency']=context; development.append(goal)
            else:
                for cell in row:
                    value=cell['text']
                    if cell['color']=='blue':
                        assigned = False
                        fields.append({**evidence,'text':value,'lines':cell['lines']})
                        if narrative_key and cell['x1']-cell['x0']>300:
                            assigned = True
                            if narrative_key == 'no_md_reason':
                                no_md_reason = _field_text(value)
                            elif narrative_key in narratives:
                                issues.append('Freitextfeld mehrfach erkannt: ' + NARRATIVE_FIELDS[narrative_key][0])
                            else:
                                narratives[narrative_key] = _field_text(value)
                            narrative_key = ''
                        if kind=='review' and context=='performance' and cell['x1']-cell['x0']>300 and not assessment_done:
                            assigned = True
                            assessment_done = True
                            narratives['performance_comment'] = _field_text(value.removeprefix('Einschätzung:'))
                        if kind=='review' and context not in ('','performance') and cell['x1']-cell['x0']>300 and not assessment_done:
                            assigned = True
                            assessment_done=True
                            assessment=value.removeprefix('Einschätzung:').strip()
                            if assessment.lower().startswith(('klicken sie','klicken oder tippen','bitte wählen')):
                                assessment=''
                            if assessment:
                                assessments[context]=assessment
                        if not assigned and cell['x1']-cell['x0']>300 and _field_text(value):
                            issues.append(f"Freitext auf Seite {page['page']} nicht eindeutig zugeordnet. Mögliche Fortsetzung: im Original prüfen und im passenden Feld ergänzen.")
        # Kontext auch dann übertragen, wenn am Seitenende keine Zelle folgt.
        if anchor_index<len(anchors):
            context=anchors[-1][1]
            assessment_done=False
    if not goal_rows and not probation:
        issues.append('Zieltabellen nicht sicher erkannt. Ältere oder abweichende Vorlage: Ziele anhand des Original-PDF prüfen und nötigenfalls erfassen.')
    return {'performance_goals':performance, 'development_goals':development,
            'assessments':assessments, 'narratives':narratives, 'no_md_reason':no_md_reason, 'fields':fields, 'content_issues':issues,
            'goal_context':'previous' if kind=='review' else 'agreed', 'scalar_fields':scalar_fields,
            'field_evidence':field_evidence, 'coverage':{'goal_rows':goal_rows,'competencies':sorted(competency_anchors)}}
