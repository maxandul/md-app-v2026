"""Vorprüfung textbasierter Word-PDFs, unabhängig vom Arbeitsmappen-Datenblock.

Die Vorschau schreibt keine Fachdaten. Fehlende oder mehrdeutige Angaben bleiben
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
    return parse_word_pdf_text(inspection.text, page_count=inspection.page_count)


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
            conducted = re.findall(r"Wird der Rückblick durchgeführt\?\s*(Ja|Nein)\b", flat, re.IGNORECASE)
            data["conducted"] = conducted[0].lower() if len(conducted) == 1 else ""
            if not data["conducted"]:
                issues.append("Durchführung: nicht eindeutig lesbar oder nicht ausgefüllt.")
    if not flat:
        issues.append("Kein lesbarer Text: Scan oder Bild-PDF muss manuell geprüft werden.")
    return {
        "data": data,
        "issues": issues,
        "page_count": page_count,
        "text_length": len(flat),
        "text": text,
        "status": "needs_review" if issues else "basic_fields_readable",
    }
