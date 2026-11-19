"""Use the stored, verified document bytes for Outlook attachments."""
from contextlib import contextmanager
import hashlib
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from zipfile import ZipFile


MAX_SINGLE_ATTACHMENTS = 5


def individual_attachments(documents):
    names = [PurePosixPath(doc['filename']).name for doc in documents]
    return (
        0 < len(names) <= MAX_SINGLE_ATTACHMENTS
        and len({name.casefold() for name in names}) == len(names)
    )


def package_documents(manifest):
    return [*manifest.get('documents', []), *manifest.get('attachments', [])]


@contextmanager
def outlook_attachments(archive_path, documents):
    """Keep original filenames, bundling duplicate names that need ZIP folders."""
    archive_path = Path(archive_path)
    if not individual_attachments(documents):
        yield [archive_path]
        return
    with TemporaryDirectory(prefix='md-mail-', dir=archive_path.parent) as directory:
        attachments = []
        with ZipFile(archive_path) as archive:
            for document in documents:
                raw = archive.read(document['filename'])
                if hashlib.sha256(raw).hexdigest() != document['sha256']:
                    raise ValueError('Eine Word-Datei im Paket wurde verändert. Bitte die Ausgabe prüfen.')
                name = PurePosixPath(document['filename']).name
                if not name.lower().endswith('.docx') or '\\' in name or ':' in name:
                    raise ValueError('Ungültiger Dateiname für einen Word-Anhang.')
                path = Path(directory) / name
                path.write_bytes(raw)
                attachments.append(path)
        yield attachments
