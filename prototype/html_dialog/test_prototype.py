from __future__ import annotations

import re
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from generate_package import (
    build_payload,
    choose_manager,
    json_for_script,
    load_sap_data,
    manager_index,
    output_filename,
    render_html,
)
from validate_package import extract_payload, validate_payload
from create_demo import build_demo
from tests.sample_data import create_sap_sample


class HtmlDialogPrototypeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        sap_path = create_sap_sample(Path(self.temp_dir.name) / "EXPORT_TEST.xlsx")
        self.frame = load_sap_data(sap_path)
        self.manager_pn, self.pack = choose_manager(manager_index(self.frame), "111116")
        self.payload = build_payload(
            self.manager_pn,
            self.pack,
            2025,
            created_at=datetime(2025, 9, 17, 12, 0, tzinfo=timezone.utc),
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_duplicate_sap_rows_create_one_case_per_employee(self) -> None:
        personal_numbers = [item["employee"]["pn"] for item in self.payload["employees"]]
        self.assertEqual(personal_numbers, ["111111", "111112", "111113"])
        self.assertEqual(len(personal_numbers), len(set(personal_numbers)))

    def test_probation_package_uses_its_own_dialog_type_and_scope(self) -> None:
        payload = build_payload(
            self.manager_pn,
            self.pack,
            2025,
            created_at=datetime(2025, 9, 17, 12, 0, tzinfo=timezone.utc),
            dialog_type="probation",
        )
        employee = next(item for item in payload["employees"] if item["employee"]["pn"] == "111112")
        self.assertEqual(employee["dialog_type"], "probation")
        self.assertEqual(employee["suggestion"]["scope"], "review_only")
        self.assertTrue(employee["case_id"].endswith("-probezeit"))

    def test_html_is_self_contained_and_roundtrips(self) -> None:
        html = render_html(self.payload)
        self.assertNotIn("__MD_PACKAGE_JSON__", html)
        self.assertNotRegex(html, re.compile(r"src=[\"']https?://", re.I))
        external_links = re.findall(r"href=[\"'](https?://[^\"']+)", html, re.I)
        self.assertEqual(
            external_links,
            ["https://ktzuerich.sharepoint.com/sites/vd/SitePages/Mitarbeitenden-Dialog-(MD).aspx#spezialf%C3%A4lle"],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "package.html"
            path.write_text(html, encoding="utf-8")
            extracted = extract_payload(path)
        self.assertEqual(extracted, self.payload)

    def test_json_embedding_escapes_script_endings(self) -> None:
        payload = {"text": "</script><script>alert('x')</script>"}
        encoded = json_for_script(payload)
        self.assertNotIn("</script>", encoded.lower())
        self.assertIn("\\u003c", encoded)

    def test_initial_package_is_structurally_valid_but_incomplete(self) -> None:
        result = validate_payload(self.payload)
        self.assertTrue(result.valid)
        self.assertEqual(result.summary["employees"], 3)
        self.assertEqual(result.summary["status_counts"]["offen"], 3)
        self.assertTrue(any("noch nie" in warning for warning in result.warnings))

    def test_start_filename_is_unmistakable(self) -> None:
        filename = output_filename(self.payload)
        self.assertEqual(
            filename,
            "MD_Dialog_2025_2026_Nachname6_Rufname6_111116_START.html",
        )
        self.assertEqual(self.payload["package"]["revision"], 0)

    def test_filename_transliterates_umlauts(self) -> None:
        self.payload["package"]["manager_last_name"] = "Müller"
        self.payload["package"]["manager_first_name"] = "Zoë"
        self.assertEqual(
            output_filename(self.payload),
            "MD_Dialog_2025_2026_Muller_Zoe_111116_START.html",
        )

    def test_saved_filename_and_pdf_titles_keep_year_and_pn(self) -> None:
        template = (Path(__file__).parent / "template.html").read_text(encoding="utf-8")
        self.assertIn("_BEARBEITET_${revision}_${stamp}.html", template)
        self.assertIn("`Rueckblick_${state.package.rb_year}`", template)
        self.assertIn("`Ausblick_${state.package.ab_year}`", template)
        self.assertIn("_${filenamePart(person.pn)}`", template)

    def test_no_md_can_be_exported_as_administrative_pdf(self) -> None:
        template = (Path(__file__).parent / "template.html").read_text(encoding="utf-8")
        self.assertIn('data-action="print-no-md"', template)
        self.assertIn("isNoMd ? 'KEIN_MD'", template)
        self.assertIn("Sie wird nicht an das Personaldossier übergeben.", template)
        self.assertIn("`scope=${employee.scope || ''}`", template)

    def test_completed_employee_is_recognised(self) -> None:
        employee = self.payload["employees"][0]
        employee["scope"] = "full"
        employee["dialog_date"] = "2025-12-10"
        for goal in employee["previous_goals"]:
            goal["achievement"] = "Erreicht"
            goal["review"] = "Ziel wurde erreicht."
        for goal in employee["previous_development_goals"]:
            goal["achievement"] = "Erreicht"
            goal["review"] = "Entwicklungsziel wurde erreicht."
        employee["review"]["performance"] = "Die Leistung war sehr gut."
        employee["review"]["overall_rating"] = "B – sehr gut"
        employee["review"]["agreement"] = "Ja"
        employee["review"]["secondary_employment_current"] = "Ja"
        goal = employee["outlook"]["performance_goals"][0]
        goal.update(
            {
                "title": "Abläufe verbessern",
                "criteria": "Zwei Verbesserungen sind umgesetzt.",
                "target_date": "2026-12-31",
            }
        )
        result = validate_payload(self.payload)
        self.assertEqual(result.summary["status_counts"]["vollstaendig"], 1)
        self.assertEqual(result.summary["status_counts"]["offen"], 2)

    def test_demo_covers_required_usability_scenarios(self) -> None:
        demo = build_demo()
        scopes = {item["scope"] for item in demo["employees"]}
        self.assertTrue({"", "full", "outlook_only", "review_only", "none"}.issubset(scopes))
        self.assertTrue(any(item["checkpoint_notes"] for item in demo["employees"]))
        self.assertTrue(any(item["meta"]["archived"] for item in demo["employees"]))
        self.assertTrue(any(item["review"]["agreement"] == "Nein" for item in demo["employees"]))

    def test_template_has_guided_steps_and_collapsed_archive(self) -> None:
        template = (Path(__file__).parent / "template.html").read_text(encoding="utf-8")
        self.assertIn("1 · Grundlagen", template)
        self.assertIn("Prüfen und PDF", template)
        self.assertIn('id="archive-list"', template)
        self.assertNotIn('id="employee-search"', template)
        self.assertEqual(template.count("const sectionName ="), 1)


if __name__ == "__main__":
    unittest.main()
