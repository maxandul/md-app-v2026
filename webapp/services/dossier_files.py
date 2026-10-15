"""Originale erhalten; ausschliesslich vollständige Kopien an RPA übergeben."""
import hashlib
import os
from pathlib import Path
import shutil
import uuid


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def publish_copy(source, destination):
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if digest(source) == digest(destination):
            return False
        raise ValueError(f'Im Übergabeordner existiert bereits eine andere Datei «{destination.name}». Bitte die Dossierverarbeitung klären.')
    temporary = destination.parent / ('.md-' + uuid.uuid4().hex + '.tmp')
    try:
        shutil.copyfile(source, temporary)
        if os.name == 'nt':
            os.rename(temporary, destination)
        else:
            os.link(temporary, destination)
        return True
    finally:
        temporary.unlink(missing_ok=True)
