"""Read visible goal tables in old and current MD Word/PDF documents."""
from __future__ import annotations

import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
KEYS = ('title', 'criteria', 'steps', 'target_date')


def visible_text(node):
    """Read once through nested controls; omit placeholders and deleted text."""
    if node.tag in (W + 'del', W + 'sdtPr', W + 'tcPr', W + 'pPr', W + 'rPr'):
        return ''
    if node.tag == W + 'sdt' and node.find('./' + W + 'sdtPr/' + W + 'showingPlcHdr') is not None:
        return ''
    if node.tag == W + 't':
        return node.text or ''
    if node.tag in (W + 'br', W + 'cr', W + 'tab'):
        return '\n' if node.tag != W + 'tab' else '\t'
    text = ''.join(visible_text(child) for child in node)
    return text + ('\n' if node.tag == W + 'p' else '')


def wrapped_children(node, tag):
    for child in node:
        if child.tag == W + tag:
            yield child
        elif child.tag in (W + 'sdt', W + 'sdtContent', W + 'customXml'):
            yield from wrapped_children(child, tag)


def goal_years(text):
    flat = re.sub(r'\s+', ' ', text)
    date = r'(?:\d{2}\.\d{2}\.)?(20\d{2})'
    matches = re.findall(r'Ausblick\s+auf\s*:\s*' + date + r'\s+bis\s*' + date, flat, re.I)
    return sorted({int(year) for pair in matches for year in pair})


def word_tables(path):
    from .legacy_forms import COMPETENCY_TAGS, MAX_WORD_XML_BYTES, _clean_text
    with ZipFile(path) as archive:
        if archive.getinfo('word/document.xml').file_size > MAX_WORD_XML_BYTES:
            raise ValueError('entpackter Word-Inhalt überschreitet die zulässige Grösse')
        xml = archive.read('word/document.xml')
    if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml:
        raise ValueError('Nicht unterstützte XML-Deklaration')
    root = ET.fromstring(xml)
    performance, development, issues = [], [], []
    recognized = False
    for table_index, table in enumerate(root.iter(W + 'tbl'), 1):
        context = ''
        is_goal_table = False
        for row_index, row in enumerate(wrapped_children(table, 'tr'), 1):
            cells = list(wrapped_children(row, 'tc'))
            texts = [_clean_text(visible_text(cell)) for cell in cells]
            location = f'Tabelle {table_index}, Zeile {row_index}'
            excerpt = ' | '.join(texts)
            if len(excerpt) > 500:
                excerpt = excerpt[:500] + ' … (vollständig im Original)'
            competency_heading = False
            if len(texts) == 1:
                label = re.sub(r'[\s-]+', '', texts[0]).casefold()
                for name in COMPETENCY_TAGS.values():
                    if label.startswith(re.sub(r'[\s-]+', '', name).casefold()):
                        context = name
                        competency_heading = True
                if competency_heading:
                    continue
            compact = [re.sub(r'\s+', ' ', text).casefold() for text in texts]
            if len(compact) == 4 and compact[0] in ('ziel', 'leistungsziel', 'entwicklungsziel') and compact[1:] == ['messkriterien', 'weg zum ziel', 'termin']:
                recognized = is_goal_table = True
                if compact[0] != 'entwicklungsziel':
                    context = 'performance'
                continue
            if not is_goal_table or not any(texts):
                continue
            if len(texts) != 4 or not context:
                reason = f'{len(texts)} statt 4 Spalten' if len(texts) != 4 else 'Kompetenz nicht zuordenbar'
                issues.append(f'{location}: nicht übernommen ({reason}). Lesbarer Inhalt: {excerpt}')
                continue
            goal = dict(zip(KEYS, texts))
            goal['source_tag_family'] = 'word_table'
            goal['competency'] = '' if context == 'performance' else context
            (performance if context == 'performance' else development).append(goal)
    return {'performance_goals': performance, 'development_goals': development,
            'recognized': recognized, 'issues': list(dict.fromkeys(issues)), 'text': visible_text(root)}


def pdf_goals(path):
    from .word_pdf import inspect_word_pdf
    parsed = inspect_word_pdf(path)
    issues = []
    if not parsed['text'].strip():
        issues.append('Kein lesbarer Text. Bild-PDF/Scan benötigt Texterkennung oder das ursprüngliche Word-Dokument.')
    performance, development = [], []
    for key, destination in [('performance_goals', performance), ('development_goals', development)]:
        for source in parsed[key]:
            goal = {key: source.get(key, '') for key in KEYS}
            goal['competency'] = source.get('competency', '')
            goal['source_tag_family'] = 'pdf_table'
            goal['evidence'] = source.get('evidence', {})
            destination.append(goal)
    if not performance and not development and parsed['text'].strip() and not parsed.get('coverage',{}).get('goal_rows'):
        issues.append('Keine ausgefüllten Zieltabellen erkannt. Original oder Word-Version prüfen.')
    return {'document_type': parsed['data'].get('document_kind', 'unknown'),
            'employee_pn': parsed['data'].get('pn', ''), 'assignment_number': '',
            'performance_goals': performance, 'development_goals': development,
            'detected_years': goal_years(parsed['text']), 'issues': issues}
