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
    def test_unassigned_wide_text_is_preserved_and_flagged(self):
        from webapp.services.word_pdf import inspect_word_pdf
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'freitext.pdf'
            c = canvas.Canvas(str(path), pagesize=(595,842))
            c.drawString(40,810,'Mitarbeitenden-Dialog (MD) - Ausblick')
            c.showPage()
            c.setFillColorRGB(.882,.965,1)
            c.rect(40,700,513,50,fill=1,stroke=0)
            c.setFillColorRGB(0,0,0)
            c.drawString(44,725,'Fortsetzung eines langen Kommentars')
            c.save()
            result = inspect_word_pdf(path)
            self.assertTrue(any('Freitext auf Seite 2' in issue for issue in result['issues']))
            self.assertIn('Fortsetzung eines langen Kommentars', [field['text'] for field in result['fields']])

    def test_real_pdf_goal_continuation_keeps_text_and_does_not_merge_new_goal(self):
        from webapp.services.word_pdf import inspect_word_pdf
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'continued.pdf'
            c = canvas.Canvas(str(path), pagesize=(595, 842))
            c.drawString(40, 810, 'Mitarbeitenden-Dialog (MD) - Ausblick')
            c.drawString(40, 700, 'Kommunikationsfähigkeit')
            def row(y, title, steps):
                for x, width, text in [(40,150,title),(191,130,''),(322,160,steps),(483,70,'')]:
                    c.setFillColorRGB(.882,.965,1)
                    c.rect(x,y,width,40,fill=1,stroke=0)
                    c.setFillColorRGB(0,0,0)
                    c.setFont('Helvetica',9)
                    c.drawString(x+4,y+25,text)
            row(60, '1. Wirkung verbessern', 'Erster Schritt')
            c.showPage()
            row(710, '', 'Zweiter Schritt')
            row(600, '2. Eigenes Ziel', 'Anderer Schritt')
            c.save()
            goals = inspect_word_pdf(path)['development_goals']
            self.assertEqual(len(goals), 2)
            self.assertEqual(goals[0]['steps'], 'Erster Schritt\nZweiter Schritt')
            self.assertEqual(goals[0]['evidence']['last_page'], 2)
            self.assertEqual(goals[1]['title'], 'Eigenes Ziel')

    def test_ambiguous_fragments_remain_separate_for_hr_review(self):
        from webapp.services.word_pdf import merge_goal_continuations
        for page, top, competency in [(1,80,'A'),(3,80,'A'),(2,200,'A'),(2,80,'B')]:
            with self.subTest(page=page, top=top, competency=competency):
                goals = [{'title':'Ziel','competency':'A','evidence':{'page':1,'top':700}},
                         {'title':'','steps':'Fortsetzung','competency':competency,'evidence':{'page':page,'top':top}}]
                self.assertEqual(len(merge_goal_continuations(goals)),2)

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
        self.assertEqual(result["issues"], [])

    def test_optional_answers_are_explicit_and_missing_is_unknown(self):
        result=parse_word_pdf_text(REVIEW + """
Ist ein Gespräch mit der nächsthöheren vorgesetzten Person gewünscht? Nein
Sind die oben aufgeführten Bewilligungen vollständig und aktuell?
(Nur relevant beim ordentlichen MD mit automatisiertem Versand) Ja
""")
        self.assertEqual(result['data']['higher_manager_requested'],'nein')
        self.assertEqual(result['data']['sap_current'],'ja')
        self.assertEqual(parse_word_pdf_text(REVIEW)['data']['sap_current'],'')
        result=parse_word_pdf_text(REVIEW.replace('Rückblick','Ausblick') +
                                  ' Besteht ein Wunsch bezüglich laufbahnorientierter Entwicklung? Ja')
        self.assertEqual(result['data']['career_requested'],'ja')

    def test_nonconducted_outlook_needs_no_conversation_date(self):
        text=REVIEW.replace('Rückblick','Ausblick').replace('? Ja','? Nein').replace('15.01.2027','Datum')
        result=parse_word_pdf_text(text)
        self.assertEqual(result['data']['conducted'],'nein')
        self.assertEqual(result['data']['dialog_date'],'')
        self.assertFalse(result['issues'])

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
            app = create_app({"HR_GOAL_WORKFLOW": False,
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
