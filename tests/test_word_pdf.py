from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from reportlab.pdfgen import canvas

from webapp import create_app
from webapp.services.word_pdf import parse_word_pdf_text


REVIEW = """Mitarbeitenden-Dialog (MD) - Rückblick
Name: Test PN: 000123
Name VG: Andere Person PN VG: 000456
Wird der Rückblick durchgeführt? Ja
Rückblick auf: 01.01.2026 bis 31.12.2026 Gespräch vom: 15.01.2027
Selbstmanagement Entwicklungsziel Vorjahr Messkriterien Weg zum Ziel Termin
Altes Ziel Einschätzung:
"""


class WordPdfTest(unittest.TestCase):
    def test_person_number_period_and_dialog_year_are_distinct(self):
        result = parse_word_pdf_text(REVIEW)
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["data"]["pn"], "000123")
        self.assertEqual(result["data"]["manager_pn"], "000456")
        self.assertEqual(result["data"]["period_end"], "2026-12-31")
        self.assertEqual(result["data"]["dialog_date"], "2027-01-15")
        self.assertNotIn("agreement", result["data"])
        self.assertNotIn("review_competencies", result["data"])

    def test_conflicting_number_is_not_silently_selected(self):
        result = parse_word_pdf_text(REVIEW + "\nPN: 987654")
        self.assertEqual(result["data"]["pn"], "")
        self.assertEqual(result["status"], "needs_review")

    def test_missing_selection_is_not_no(self):
        result = parse_word_pdf_text(REVIEW.replace("? Ja", "? Bitte wählen."))
        self.assertEqual(result["data"]["conducted"], "")
        self.assertTrue(result["issues"])

    def test_invalid_and_reversed_dates_need_review(self):
        for replacement in ["31.02.2026", "01.01.2028"]:
            with self.subTest(replacement=replacement):
                result = parse_word_pdf_text(REVIEW.replace("01.01.2026", replacement))
                self.assertEqual(result["status"], "needs_review")

    def test_non_md_and_empty_pdf_text_are_not_classified(self):
        for text in ["", "Beliebiger Bericht PN: 12345"]:
            self.assertEqual(parse_word_pdf_text(text)["data"], {})

    def test_outlook_and_soft_hyphen(self):
        text = REVIEW.replace("Rückblick", "Ausblick").replace("Mitarbeitenden", "Mitarbei\u00adtenden")
        self.assertEqual(parse_word_pdf_text(text)["data"]["document_kind"], "outlook")

    def test_preview_handles_mixed_batch_without_persisting_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = create_app({
                "TESTING": True, "AUTH_DISABLED": True, "SECRET_KEY": "test",
                "DATABASE": str(root / "test.sqlite3"),
                "STORAGE_ROOT": str(root / "data"), "BACKUP_ROOT": str(root / "backup"),
                "DOSSIER_HANDOFF_ROOT": str(root / "handoff"),
            })
            pdf = io.BytesIO()
            document = canvas.Canvas(pdf)
            for index, line in enumerate(REVIEW.splitlines()):
                document.drawString(35, 780 - index * 20, line)
            document.save()
            pdf.seek(0)
            response = app.test_client().post("/word-pdf-preview", data={
                "word_pdf_files": [(pdf, "review.pdf"), (io.BytesIO(b"broken"), "broken.pdf")],
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"000123", response.data)
            self.assertIn(b"kein lesbares PDF", response.data)
            self.assertFalse(list((root / "data").rglob("*.pdf")))
            self.assertFalse(list((root / "handoff").iterdir()))


if __name__ == "__main__":
    unittest.main()
