"""A group ZIP preserves approved file bytes, including old filename collisions."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from webapp.services.goal_delivery import _bundle_reviews


class GoalBundleTest(unittest.TestCase):
    def test_flat_archive_keeps_both_case_insensitive_duplicate_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);outputs=[];contents=[b'first approved document',b'second approved document']
            for number,(filename,raw) in enumerate(zip(['Fall_1/Rückblick.docx','Fall_2/rückblick.docx'],contents),1):
                source=root/f'source-{number}.zip'
                with ZipFile(source,'w') as archive:
                    archive.writestr(filename,raw)
                    archive.writestr('Unbeteiligter_Ausblick.docx',b'not selected')
                manifest={'documents':[{'kind':'review','case_id':str(number),'filename':filename,
                                        'sha256':hashlib.sha256(raw).hexdigest()}]}
                outputs.append({'id':number,'case_id':str(number),'stored_path':str(source),'manifest_json':json.dumps(manifest)})
            target=root/'combined.zip';metadata=_bundle_reviews(outputs,target)
            with ZipFile(target) as archive:
                names=archive.namelist()
                self.assertEqual(len({name.casefold() for name in names}),2)
                self.assertTrue(all('/' not in name and name.endswith('.docx') for name in names))
                self.assertEqual([archive.read(name) for name in names],contents)
            self.assertEqual(metadata['document_count'],2)
            self.assertEqual(metadata['sha256'],hashlib.sha256(target.read_bytes()).hexdigest())
            self.assertEqual([item['output_id'] for item in metadata['documents']],[1,2])

    def test_wrong_case_and_modified_document_are_not_packaged(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source.zip';raw=b'approved'
            with ZipFile(source,'w') as archive:archive.writestr('Review.docx',raw)
            document={'kind':'review','case_id':'correct','filename':'Review.docx','sha256':hashlib.sha256(raw).hexdigest()}
            for change in ({'case_id':'wrong'},{'sha256':hashlib.sha256(b'other').hexdigest()}):
                output={'id':1,'case_id':'correct','stored_path':str(source),
                        'manifest_json':json.dumps({'documents':[document|change]})}
                target=root/'combined.zip'
                with self.subTest(change=change),self.assertRaises(ValueError):
                    _bundle_reviews([output],target)
                self.assertFalse(target.exists())
                self.assertFalse(list(root.glob('*.tmp')))
