"""HR-reviewed Word feedback; no case obligation or reminder is created."""
from __future__ import annotations
import json
import os
import re
import shutil
import uuid
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from .documents import file_sha256, inspect_pdf
from .feedback import _cover_page, _filename_part
from .legacy_forms import COMPETENCY_TAGS
from .word_pdf_imports import now

QUESTIONS = {
    'general': 'Gibt es allgemeine Bemerkungen?',
    'keep': 'Was soll mein/e Vorgesetzte/r unbedingt beibehalten?',
    'wish': 'Was wünsche ich mir von meiner/meinem Vorgesetzten zukünftig?',
    'change': 'Welche Veränderungen sind seit dem letzten Gespräch festzustellen?',
}
FIELDS = {**QUESTIONS, **COMPETENCY_TAGS}


def is_feedback(text, filename=''):
    flat = re.sub(r'\s+', ' ', text)
    if re.search(r'Mitarbeitenden[-–]Dialog\s*\(MD\)\s*[-–]\s*(Rückblick|Ausblick)', flat, re.I):
        return False
    return bool(re.search(r'Mitarbeitenden[-–]Dialog\s*\(MD\)\s*[-–]\s*Feedback', flat, re.I)
                or 'feedback' in filename.casefold())


def inspect_feedback(path, filename=''):
    from .pdf_cells import read_cells
    from .word_pdf import _field_text
    inspection = inspect_pdf(path)
    flat = re.sub(r'\s+', ' ', inspection.text)
    candidates = set(re.findall(r'(?:Personalnummer\s+Vorgesetzte/r|PN\s+VG)\s*:\s*(\d+)\b', flat, re.I))
    file_match = re.search(r'_Feedback_an_.+_(\d+)\.pdf$', filename, re.I)
    if file_match:
        candidates.add(file_match[1])
    issues = ['Führungskraft und Rückblickjahr am Original prüfen. Das Gesprächsdatum bestimmt nicht automatisch das Rückblickjahr.']
    if len(candidates) != 1:
        issues.append('Personalnummer der Führungskraft fehlt oder ist widersprüchlich.')
    if not inspection.text.strip():
        issues.append('Bild-PDF/Scan: keine automatische Texterkennung. Angaben manuell anhand des Originals erfassen.')
    if inspection.data.get('document','').upper() == 'FEEDBACK':
        candidates = {inspection.data.get('manager_pn', '')} - {''}
    fields = {}
    context = ''
    for page in read_cells(path):
        cells = page['cells']
        external = [r for r in page['runs'] if not any(c['x0']-.2 <= r['x'] < c['x1'] and c['y0'] <= r['y'] <= c['y1']+.2 for c in cells)]
        lines = []
        for run in sorted(external, key=lambda r: (round(r['y']), r['x'])):
            if not lines or abs(lines[-1][0] - run['y']) > 1.5:
                lines.append([run['y'], run['text']])
            else:
                lines[-1][1] += run['text']
        anchors = []
        for y, text in lines:
            compact = re.sub(r'[\s-]+', '', text).casefold()
            for key, label in FIELDS.items():
                if re.sub(r'[\s-]+', '', label).casefold() in compact:
                    anchors.append((y, key))
            if 'Administratives' in text:
                anchors.append((y, ''))
        anchors.sort()
        i = 0
        for cell in cells:
            while i < len(anchors) and anchors[i][0] < cell['y0']:
                context = anchors[i][1]; i += 1
            if cell['color'] == 'blue' and cell['x1'] - cell['x0'] > 300:
                value = _field_text(cell['text'])
                if context:
                    fields[context] = (fields.get(context, '') + '\n' + value).strip()
                elif value:
                    issues.append(f"Freitext auf Seite {page['page']} nicht zugeordnet; am Original prüfen.")
        if i < len(anchors):
            context = anchors[-1][1]
    return {'data': {'document_kind': 'feedback', 'manager_pn': next(iter(candidates)) if len(candidates)==1 else '', 'year': inspection.data.get('year','')},
            'text': inspection.text, 'page_count': inspection.page_count, 'issues': issues,
            'feedback_fields': fields}


def confirm_feedback(connection, import_id, *, cycle_id, manager_pn, fields, reason='', user_id=None):
    item = connection.execute('SELECT * FROM word_pdf_imports WHERE id=?', (import_id,)).fetchone()
    if not item or item['status'] != 'pending':
        raise ValueError('Dieses Feedback ist bereits verarbeitet oder nicht vorhanden.')
    if json.loads(item['parsed_json'])['data'].get('document_kind') != 'feedback':
        raise ValueError('Zuerst als Feedback zur Prüfung zuordnen.')
    if not connection.execute('SELECT 1 FROM dialog_cases WHERE cycle_id=? AND manager_pn=?', (cycle_id,manager_pn)).fetchone():
        raise ValueError('Die Führungskraft gehört nicht zum gewählten Jahresprozess.')
    if connection.execute('SELECT status FROM cycles WHERE id=?',(cycle_id,)).fetchone()[0]=='abgeschlossen':
        raise ValueError('Den Jahresprozess für einen Nachtrag zuerst wieder öffnen.')
    if any(key not in FIELDS or not isinstance(value,str) for key,value in fields.items()):
        raise ValueError('Ungültige Feedbackfelder.')
    parsed = json.loads(item['parsed_json'])
    if parsed['data'].get('manager_pn') != manager_pn and len(reason.strip()) < 10:
        raise ValueError('Fehlende oder abweichende Personalnummer bitte mit mindestens 10 Zeichen begründen.')
    if not Path(item['stored_path']).is_file() or file_sha256(Path(item['stored_path'])) != item['sha256']:
        raise ValueError('Das Original fehlt oder wurde verändert.')
    reviewed = {'cycle_id': cycle_id, 'manager_pn': manager_pn, 'feedback_fields': fields,
                'competencies': [name for key,name in COMPETENCY_TAGS.items() if fields.get(key,'').strip()],
                'character_counts': {key:len(value.strip()) for key,value in fields.items()}}
    connection.execute('INSERT INTO word_feedback_submissions(import_id,cycle_id,manager_pn) VALUES (?,?,?)',
                       (import_id,cycle_id,manager_pn))
    connection.execute("""UPDATE word_pdf_imports SET status='imported',reviewed_json=?,review_note=?,reviewed_by=?,reviewed_at=? WHERE id=?""",
        (json.dumps(reviewed,ensure_ascii=False),reason,user_id,now(),import_id))


def collections(connection):
    groups = connection.execute("""SELECT d.cycle_id,d.manager_pn,c.review_year,e.first_name,e.last_name,
        COUNT(DISTINCT CASE WHEN d.active=1 AND COALESCE(NULLIF(d.official_scope,''),d.suggested_scope) IN ('full','review_only') THEN d.employee_pn END) AS expected
        FROM dialog_cases d JOIN cycles c ON c.id=d.cycle_id JOIN employees e ON e.pn=d.manager_pn
        GROUP BY d.cycle_id,d.manager_pn ORDER BY c.review_year DESC,e.last_name,e.first_name""").fetchall()
    result=[]
    for row in groups:
        item=dict(row)
        counts=connection.execute('SELECT COUNT(*) AS total, COALESCE(SUM(bundle_id IS NULL),0) AS unbundled FROM word_feedback_submissions WHERE cycle_id=? AND manager_pn=?',(row['cycle_id'],row['manager_pn'])).fetchone()
        item.update(count=counts['unbundled'], total=counts['total'], bundled=counts['total']-counts['unbundled'])
        item['pending']=connection.execute("""SELECT COUNT(*) FROM word_pdf_imports w LEFT JOIN workflow_pdf_state s ON s.import_id=w.id
            WHERE w.status='pending' AND COALESCE(s.dismissed,0)=0 AND json_extract(w.parsed_json,'$.data.document_kind')='feedback'
            AND json_extract(w.parsed_json,'$.data.manager_pn')=?""",(row['manager_pn'],)).fetchone()[0]
        result.append(item)
    return result


def bundle_feedback(connection, *, cycle_id, manager_pn, expected_ids, handoff_dir, archive_dir):
    """Freeze the reviewed selection; a later arrival becomes a separate addendum."""
    connection.execute('BEGIN IMMEDIATE')
    destination = None
    archive = None
    pending = None
    try:
        cycle = connection.execute('SELECT * FROM cycles WHERE id=?',(cycle_id,)).fetchone()
        if not cycle or cycle['status']=='abgeschlossen':
            raise ValueError('Jahresprozess nicht vorhanden oder abgeschlossen; für Nachträge zuerst wieder öffnen.')
        rows = connection.execute('''SELECT w.* FROM word_feedback_submissions s JOIN word_pdf_imports w ON w.id=s.import_id
            WHERE s.cycle_id=? AND s.manager_pn=? AND s.bundle_id IS NULL ORDER BY w.id''',(cycle_id,manager_pn)).fetchall()
        if not rows or [r['id'] for r in rows] != expected_ids:
            raise ValueError('Die Sammlung hat sich geändert oder wurde bereits bereitgestellt. Bitte neu prüfen.')
        manager = connection.execute('SELECT * FROM employees WHERE pn=?',(manager_pn,)).fetchone()
        count = connection.execute('SELECT COUNT(*) FROM feedback_bundles WHERE cycle_id=? AND manager_pn=?',(cycle_id,manager_pn)).fetchone()[0]
        suffix = '' if not count else f'_Nachtrag_{count+1}'
        filename = f"Feedback_{cycle['review_year']}_{_filename_part(manager['last_name'])}_{_filename_part(manager['first_name'])}_{_filename_part(manager_pn)}{suffix}.pdf"
        handoff_dir.mkdir(parents=True,exist_ok=True); archive_dir.mkdir(parents=True,exist_ok=True)
        archive = archive_dir / (uuid.uuid4().hex + '.pdf')
        writer = PdfWriter()
        cover = _cover_page(manager_name=f"{manager['first_name']} {manager['last_name']}",manager_pn=manager_pn,review_year=cycle['review_year'],count=len(rows))
        writer.append(PdfReader(cover))
        for row in rows:
            if file_sha256(Path(row['stored_path'])) != row['sha256']:
                raise ValueError('Ein Original wurde verändert. Bündelung abgebrochen.')
            writer.append(PdfReader(row['stored_path']))
        with archive.open('xb') as output:
            writer.write(output)
        target = handoff_dir / filename
        # Publish a complete file atomically; the robot must never see a partial PDF.
        pending = handoff_dir / ('.feedback-' + uuid.uuid4().hex + '.tmp')
        with pending.open('xb') as output, archive.open('rb') as source:
            shutil.copyfileobj(source,output)
        if os.name == 'nt':
            os.rename(pending,target)  # Windows refuses an existing destination.
        else:
            os.link(pending,target)  # Exclusive and atomic on POSIX.
        destination = target
        pending.unlink(missing_ok=True)
        cursor = connection.execute('''INSERT INTO feedback_bundles(cycle_id,manager_pn,filename,stored_path,sha256,submission_count,created_at)
            VALUES (?,?,?,?,?,?,?)''',(cycle_id,manager_pn,filename,str(target),file_sha256(archive),len(rows),now()))
        bundle_id = cursor.lastrowid
        connection.execute('INSERT INTO word_feedback_bundle_archives VALUES (?,?)',(bundle_id,str(archive)))
        connection.executemany('UPDATE word_feedback_submissions SET bundle_id=? WHERE import_id=?',[(bundle_id,row['id']) for row in rows])
        connection.executemany('UPDATE feedback_submissions SET bundle_id=? WHERE sha256=? AND bundle_id IS NULL',[(bundle_id,row['sha256']) for row in rows])
        connection.commit()
        return bundle_id
    except Exception:
        connection.rollback()
        if pending: pending.unlink(missing_ok=True)
        if destination: destination.unlink(missing_ok=True)
        if archive: archive.unlink(missing_ok=True)
        raise
