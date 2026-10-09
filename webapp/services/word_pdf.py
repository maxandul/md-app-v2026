"""Vorprüfung textbasierter Word-PDFs, unabhängig vom Arbeitsmappen-Datenblock.

Die Extraktion schreibt keine Fachdaten. Fehlende oder mehrdeutige Angaben bleiben
offen; insbesondere wird Einigkeit weder abgefragt noch abgeleitet.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .documents import inspect_pdf


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


def inspect_word_pdf(path: Path) -> dict:
    inspection = inspect_pdf(path)
    result = parse_word_pdf_text(inspection.text, page_count=inspection.page_count)
    result.update(extract_form_content(path, result['data'].get('document_kind', ''), probation=result['data'].get('probation')=='ja'))
    result['issues'].extend(result.pop('content_issues'))
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
        dialog_date = _single(rf"Gespräch\s+vom\s*:\s*({DATE})", flat, "Gesprächsdatum", issues)
        data["dialog_date"] = _iso_date(dialog_date, "Gesprächsdatum", issues)
        if data["document_kind"] == "review":
            conducted = re.findall(r"Wird der Rückblick(?: auf (?:die )?Probezeit)? durchgeführt\?\s*(Ja|Nein)\b", flat, re.IGNORECASE)
            data["conducted"] = conducted[0].lower() if len(conducted) == 1 else ""
            if not data["conducted"]:
                issues.append("Durchführung: nicht eindeutig lesbar oder nicht ausgefüllt.")
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
    context = ''
    assessment_done = False
    goal_rows = 0
    for page in read_cells(path):
        cells, runs = page['cells'], page['runs']
        # Nur Überschriften ausserhalb der Eingabefelder setzen den Kontext.
        external = [r for r in runs if not any(c['x0']-.2 <= r['x'] < c['x1'] and c['y0'] <= r['y'] <= c['y1']+.2 for c in cells)]
        lines = []
        for run in sorted(external, key=lambda r: (round(r['y']), r['x'])):
            if not lines or abs(lines[-1][0]-run['y']) > 1.5:
                lines.append([run['y'], run['text']])
            else:
                lines[-1][1] += run['text']
        anchors = []
        for y, text in lines:
            text = re.sub(r'\s+', ' ', text).strip()
            if re.search(r'Leistungsziele|^1\.\s*Zielvereinbarung', text, re.I):
                anchors.append((y, 'performance'))
            for name in COMPETENCY_TAGS.values():
                if re.sub(r'[\s-]+', '', text).startswith(re.sub(r'[\s-]+', '', name)):
                    anchors.append((y, name))
            if re.match(r'\d+(?:\.\d+)*\.\s*(?:Gesamt|Weitere|Bemerkungen|Unterschriften|Entwicklungsperspektiven|Gespräch|Anstellungsentscheid|Bestätigung)', text):
                anchors.append((y, ''))
        rows=[]
        for cell in cells:
            if not rows or abs(rows[-1][0]['y0']-cell['y0'])>.25:
                rows.append([cell])
            else:
                rows[-1].append(cell)
        anchor_index=0
        anchors.sort()
        for row in rows:
            while anchor_index < len(anchors) and anchors[anchor_index][0] < row[0]['y0']:
                context=anchors[anchor_index][1]; assessment_done=False; anchor_index+=1
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
                        fields.append({**evidence,'text':value,'lines':cell['lines']})
                        if kind=='review' and context not in ('','performance') and cell['x1']-cell['x0']>300 and not assessment_done:
                            assessment_done=True
                            assessment=value.removeprefix('Einschätzung:').strip()
                            if assessment.lower().startswith(('klicken sie','klicken oder tippen','bitte wählen')):
                                assessment=''
                            if assessment:
                                assessments[context]=assessment
        # Kontext auch dann übertragen, wenn am Seitenende keine Zelle folgt.
        if anchor_index<len(anchors):
            context=anchors[-1][1]
    if not goal_rows and not probation:
        issues.append('Zieltabellen nicht sicher erkannt. Ältere oder abweichende Vorlage: Ziele anhand des Original-PDF prüfen und nötigenfalls erfassen.')
    return {'performance_goals':performance, 'development_goals':development,
            'assessments':assessments, 'fields':fields, 'content_issues':issues,
            'goal_context':'previous' if kind=='review' else 'agreed'}
