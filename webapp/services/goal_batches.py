"""Bounded browser folder uploads and review of historical goal sources."""
import hashlib
import json
import re
import uuid
from pathlib import Path

from werkzeug.utils import secure_filename
from .legacy_forms import scan_legacy_forms

SUFFIXES = {'.docx', '.docm', '.pdf'}
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_BATCH_BYTES = 1024 * 1024 * 1024
MAX_BATCH_FILES = 5000


def create_batch(root, year):
    if not year or not 2020 <= year <= 2100:
        raise ValueError('Bitte ein Zieljahr zwischen 2020 und 2100 wählen.')
    batch = uuid.uuid4().hex
    directory = root / batch
    directory.mkdir(parents=True)
    (directory / 'year.json').write_text(json.dumps({'year': year}), encoding='utf-8')
    return batch, directory


def save_upload(directory, upload):
    # Client directory names are display-only, never server paths.
    original = upload.filename.replace('\\', '/').split('/')[-1]
    suffix = Path(original).suffix.lower()
    if suffix not in SUFFIXES or original.startswith('~$'):
        raise ValueError('Bitte Word-Dateien (.docx/.docm) oder PDF auswählen.')
    paths = list((directory / 'files').glob('*/*'))
    if len(paths) >= MAX_BATCH_FILES:
        raise ValueError('Maximal 5000 Dateien pro Auswahl. Bitte in kleinere Ordner aufteilen.')
    used = sum(path.stat().st_size for path in paths)
    file_id = uuid.uuid4().hex
    target_dir = directory / 'files' / file_id
    target_dir.mkdir(parents=True)
    target = target_dir / (secure_filename(original) or 'Ausblick' + suffix)
    size = 0
    try:
        with target.open('wb') as out:
            while chunk := upload.stream.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_FILE_BYTES or used + size > MAX_BATCH_BYTES:
                    raise ValueError('Datei zu gross: maximal 20 MB je Datei und 1 GB pro Auswahl.')
                out.write(chunk)
        if not size:
            raise ValueError('Die ausgewählte Datei ist leer.')
    except Exception:
        target.unlink(missing_ok=True)
        target_dir.rmdir()
        raise
    return file_id


def preview(connection, directory, year):
    result = scan_legacy_forms(connection, forms_root=directory, goal_year=year)
    groups = {}
    for item in result['items']:
        if item['status'] == 'matched':
            key = (item['employee_pn'], item['resolved_assignment'])
            groups[key] = groups.get(key, 0) + 1
    for item in result['items']:
        item['competing'] = groups.get((item['employee_pn'], item['resolved_assignment']), 0) > 1
        item['file_id'] = item['path'].parent.name if re.fullmatch('[0-9a-f]{32}', item['path'].parent.name) and item['path'].parent.parent.name == 'files' else ''
    serial = [{k: v for k, v in item.items() if k != 'path'} for item in result['items']]
    fingerprint = hashlib.sha256(json.dumps({'year': year, 'items': serial}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return result, fingerprint


def validate_selection(result, selected):
    candidates = {item['sha256']: item for item in result['items'] if item['status'] == 'matched'}
    if not selected or not selected <= candidates.keys():
        raise ValueError('Bitte mindestens eine eindeutig zugeordnete Quelle auswählen.')
    people = set()
    for digest in selected:
        item = candidates[digest]
        key = item['employee_pn'], item['resolved_assignment']
        if key in people:
            raise ValueError('Pro Person und Anstellung nur eine Quelle auswählen. Word und PDF am Original vergleichen.')
        people.add(key)
