"""Verify the Outlook transport at the attachment-count boundary."""
import hashlib
from pathlib import Path
from zipfile import ZipFile

import pytest

from webapp.services.mail_attachments import outlook_attachments


def make_archive(tmp_path, filenames):
    path = tmp_path / 'Vorlagen.zip'
    documents = []
    with ZipFile(path, 'w') as archive:
        for filename in filenames:
            raw = filename.encode()
            archive.writestr(filename, raw)
            documents.append({'filename': filename, 'sha256': hashlib.sha256(raw).hexdigest()})
    return path, documents


def test_five_files_are_individual_and_cleaned_up_after_outlook(tmp_path):
    names = [f'Fall_{i}/Rückblick_{i}.docx' for i in range(5)]
    path, documents = make_archive(tmp_path, names)
    with outlook_attachments(path, documents) as attachments:
        assert [attachment.name for attachment in attachments] == [Path(name).name for name in names]
        assert [attachment.read_bytes() for attachment in attachments] == [name.encode() for name in names]
    assert all(not attachment.exists() for attachment in attachments)
    assert path.is_file()


@pytest.mark.parametrize('names', [
    [f'Rückblick_{i}.docx' for i in range(6)],
    ['Fall_1/Rückblick.docx', 'Fall_2/RÜCKBLICK.docx'],
])
def test_large_packages_and_colliding_names_keep_the_zip(tmp_path, names):
    path, documents = make_archive(tmp_path, names)
    with outlook_attachments(path, documents) as attachments:
        assert attachments == [path]


def test_corrupted_document_is_rejected_before_outlook(tmp_path):
    path, documents = make_archive(tmp_path, ['Rückblick.docx'])
    documents[0]['sha256'] = 'modified'
    with pytest.raises(ValueError, match='Word-Datei im Paket wurde verändert'):
        with outlook_attachments(path, documents):
            pytest.fail('Invalid bytes reached Outlook')
    assert list(tmp_path.iterdir()) == [path]
