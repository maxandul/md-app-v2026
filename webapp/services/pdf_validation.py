"""Conservative, versioned admission profile for the supplied 2026 Word forms.

An OCR text layer is not proof of complete extraction. This module only labels
data; it never writes cases, verifies handwriting or publishes a document.
"""
from __future__ import annotations

import re
from pypdf import PdfReader


PROFILE = 'word-md-2026-v1'


def contains_page_image(path):
    reader = PdfReader(path)
    for page in reader.pages:
        area = float(page.mediabox.width) * float(page.mediabox.height)
        large = False
        objects = page.get('/Resources', {}).get('/XObject', {})
        objects = objects.get_object() if hasattr(objects, 'get_object') else objects

        def operand(op, args, cm, tm):
            nonlocal large
            if op == b'Do' and args and args[0] in objects:
                obj = objects[args[0]].get_object()
                if obj.get('/Subtype') == '/Image' and abs(cm[0]*cm[3]-cm[1]*cm[2]) > area*.35:
                    large = True
        page.extract_text(visitor_operand_before=operand)
        if large:
            return True
    return False


def validate_format(path, parsed):
    from .legacy_forms import COMPETENCY_TAGS
    data, issues = parsed['data'], parsed['issues']
    scanned = contains_page_image(path)
    parsed['source_role'] = 'scan' if scanned else 'digital'
    reasons = []
    if scanned:
        # Reading order in Canon OCR can put the employee PN after "PN VG".
        # Keep OCR in the original-text panel, never as preselected identities.
        parsed['ocr_candidates'] = dict(data)
        parsed['data'] = {k:v for k,v in data.items() if k in ('document_kind','probation')}
        issues.append('Scan/OCR: Person, Führungskraft, Zeitraum und sämtliche Inhalte am Original prüfen. OCR-Angaben werden nicht als bestätigte Feldwerte vorgeschlagen.')
        reasons.append('Scan: vollständige Feld- und Tabellenerkennung nicht nachgewiesen.')
    kind = data.get('document_kind')
    probation = data.get('probation') == 'ja'
    text = re.sub(r'\s+', ' ', parsed['text'].replace('\u00ad',''))
    required_narratives = {'general_comment','performance_comment'}
    if kind == 'outlook':
        required_narratives |= {'career_comment','career_choice'}
    else:
        required_narratives |= {'manager_comment','employee_comment','higher_manager_comment','higher_employee_comment'}
        if not probation:
            required_narratives |= {'sap_comment','sap_activities'}
    coverage = parsed.get('coverage', {})
    structural = (
        not scanned and kind in ('review','outlook')
        and set(coverage.get('competencies', [])) == set(COMPETENCY_TAGS.values())
        and (probation or coverage.get('goal_rows', 0) >= 14)
        and required_narratives <= parsed.get('narratives', {}).keys()
        and 'Bestätigung' in text and 'Administratives' in text
        and 'Unterschrift Mitarbeitende/r' in text and 'Unterschrift vorgesetzte Person' in text
    )
    # All printed page numbers must agree with the actual sequence and count.
    pages = list(PdfReader(path).pages)
    numbered = all(re.search(rf'(?<!\d){i}\s*/\s*{len(pages)}(?!\d)', p.extract_text() or '') for i,p in enumerate(pages,1))
    if not structural or not numbered:
        reasons.append('Formularstruktur oder Vollständigkeit nicht für die automatische Übernahme bestätigt.')
    if not scanned:
        if data.get('conducted')=='ja' and data.get('no_md_reason'):
            issues.append('Durchführung ist Ja, gleichzeitig ist eine Begründung der Nichtdurchführung ausgefüllt. Am Original klären.')
        if kind=='review' and data.get('dialog_date') and data.get('period_start') and data['dialog_date'] < data['period_start']:
            issues.append('Das Gesprächsdatum liegt vor dem Rückblickzeitraum. Datum und Zuordnung klären.')
        if data.get('sap_current')=='ja' and parsed.get('narratives',{}).get('sap_comment'):
            issues.append('Bewilligungen sind als vollständig/aktuell bestätigt, gleichzeitig ist eine Präzisierung ausgefüllt. Am Original klären.')
        if data.get('higher_manager_requested')=='nein' and any(parsed.get('narratives',{}).get(k) for k in ('higher_manager_comment','higher_employee_comment')):
            issues.append('Gespräch mit nächsthöherer Führungskraft ist Nein, dazu sind Gesprächsbemerkungen ausgefüllt. Am Original klären.')
    required = ['pn','manager_pn','period_start','period_end','dialog_date','conducted']
    required += ['career_requested'] if kind=='outlook' else ['higher_manager_requested'] + (['employment_continues'] if probation else ['rating','sap_current'])
    missing = [key for key in required if not data.get(key)]
    if missing:
        reasons.append('Benötigte Angaben nicht eindeutig erkannt: '+', '.join(missing)+'.')
    if data.get('conducted')!='ja':
        reasons.append('Nichtdurchführung oder offene Durchführung erfordert eine manuelle Prüfung.')
    reasons.extend(issues)
    parsed['validation'] = {'profile':PROFILE if structural and numbered else '',
                            'eligible':not reasons, 'reasons':list(dict.fromkeys(reasons))}

