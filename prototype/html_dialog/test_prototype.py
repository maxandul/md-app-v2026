from __future__ import annotations

import re
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from generate_package import (
    build_payload,
    choose_manager,
    json_for_script,
    load_sap_data,
    manager_index,
    output_filename,
    render_html,
    _suggested_scope,
)
from validate_package import employee_status, extract_payload, validate_payload
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

    def test_probation_ending_during_annual_window_requires_only_outlook(self) -> None:
        scope, reason = _suggested_scope(
            pd.Series({"Austritt": None, "Ende Probezeit": "2026-01-31"}),
            2025,
        )
        self.assertEqual(scope, "outlook_only")
        self.assertIn("nur der Ausblick", reason)

    def test_departure_hint_mentions_optional_waiver(self) -> None:
        scope, reason = _suggested_scope(
            pd.Series({"Austritt": "2025-10-31", "Ende Probezeit": None}),
            2025,
        )
        self.assertEqual(scope, "review_only")
        self.assertEqual(
            reason,
            "Austritt am 31.10.2025. Auf Wunsch des Mitarbeitenden kann auf den Rückblick verzichtet werden.",
        )

    def test_only_omitting_a_mandatory_part_requires_a_reason(self) -> None:
        employee = self.payload["employees"][0]
        employee["suggestion"]["scope"] = "review_only"
        employee["scope"] = "full"
        _, missing = employee_status(employee)
        self.assertNotIn("Begründung für weggelassenen Pflichtteil", missing)

        employee["suggestion"]["scope"] = "full"
        employee["scope"] = "review_only"
        _, missing = employee_status(employee)
        self.assertIn("Begründung für weggelassenen Pflichtteil", missing)

    def test_no_dialog_needs_no_reason_when_nothing_is_mandatory(self) -> None:
        employee = self.payload["employees"][0]
        employee["suggestion"]["scope"] = "none"
        employee["scope"] = "none"
        status, missing = employee_status(employee)
        self.assertEqual(status, "kein_md")
        self.assertEqual(missing, [])

    def test_html_is_self_contained_and_roundtrips(self) -> None:
        html = render_html(self.payload)
        self.assertNotIn("__MD_PACKAGE_JSON__", html)
        self.assertNotRegex(html, re.compile(r"src=[\"']https?://", re.I))
        external_links = re.findall(r"href=[\"'](https?://[^\"']+)", html, re.I)
        self.assertEqual(
            external_links,
            [
                "https://ktzuerich.sharepoint.com/sites/vd/SitePages/Mitarbeitenden-Dialog-(MD).aspx#spezialf%C3%A4lle",
            ],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "package.html"
            path.write_text(html, encoding="utf-8")
            extracted = extract_payload(path)
        preparation_template = extracted["configuration"].pop("preparation_template")
        self.assertIn("__MD_PREPARATION_JSON__", preparation_template)
        self.assertIn("Feedback als PDF", preparation_template)
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
        self.assertIn("`Ausblick_${outlookYear(employee)}`", template)
        self.assertIn("_${filenamePart(person.pn)}`", template)

    def test_no_md_can_be_exported_as_administrative_pdf(self) -> None:
        template = (Path(__file__).parent / "template.html").read_text(encoding="utf-8")
        self.assertIn('class="button primary" type="button" data-action="print-no-md"', template)
        self.assertIn('data-action="close-case"', template)
        self.assertIn('Die «Kein MD»-PDFs benötigen keine Unterschrift.', template)
        self.assertIn('E-Mails mit MD-Dokumenten werden automatisch verarbeitet.', template)
        self.assertIn('angepasste Stellenbeschreibungen', template)
        self.assertIn('href="mailto:hr@vd.zh.ch"', template)
        self.assertNotIn('die Feedbacks gesammelt in einer S/MIME', template)
        self.assertIn("isNoMd ? 'KEIN_MD'", template)
        self.assertIn("Sie wird nicht an das Personaldossier übergeben.", template)
        self.assertIn("`scope=${employee.scope || ''}`", template)

    def test_scope_deviation_is_embedded_in_remaining_pdf(self) -> None:
        template = (Path(__file__).parent / "template.html").read_text(encoding="utf-8")
        self.assertIn("function scopeReasonForPrint", template)
        self.assertIn("Bitte vorgängig mit deiner oder deinem HR-Verantwortlichen absprechen", template)
        self.assertNotIn("print-scope-deviation", template)
        self.assertNotIn("Abweichender_Umfang_", template)

    def test_completed_employee_is_recognised(self) -> None:
        employee = self.payload["employees"][0]
        employee["scope"] = "full"
        employee["dialog_date"] = "2025-12-10"
        # Vorjahresziele bleiben bewusst unbeurteilt; sie sind keine
        # Pflichtfelder für den Abschluss des Rückblicks.
        employee["review"]["performance"] = "Die Leistung war sehr gut."
        employee["review"]["overall_rating"] = "B – sehr gut"
        employee["review"]["agreement"] = "Ja"
        employee["outlook"]["agreement"] = "Ja"
        employee["review"]["secondary_employment_current"] = "Ja"
        result = validate_payload(self.payload)
        self.assertEqual(result.summary["status_counts"]["vollstaendig"], 1)
        self.assertEqual(result.summary["status_counts"]["offen"], 2)

    def test_performance_goals_are_optional_until_added(self) -> None:
        employee = self.payload["employees"][0]
        self.assertEqual(employee["outlook"]["performance_goals"], [])
        employee["scope"] = "outlook_only"
        employee["suggestion"]["scope"] = "outlook_only"
        employee["outlook"]["dialog_date"] = "2026-02-10"
        employee["outlook"]["agreement"] = "Ja"
        status, missing = employee_status(employee)
        self.assertEqual(status, "vollstaendig")
        self.assertNotIn("Mindestens ein Leistungsziel", missing)

        employee["outlook"]["performance_goals"].append(
            {"id": "goal-test", "title": "", "criteria": "", "steps": "", "target_date": ""}
        )
        status, missing = employee_status(employee)
        self.assertEqual(status, "offen")
        self.assertIn("Bezeichnung Leistungsziel 1", missing)

        template = (Path(__file__).parent / "template.html").read_text(encoding="utf-8")
        self.assertIn("Noch kein Leistungsziel erfasst.", template)
        self.assertNotIn("Mindestens ein Leistungsziel", template)
        self.assertIn("renderOutlookGoalCards(employee,'outlook.performance_goals')", template)

    def test_demo_covers_required_usability_scenarios(self) -> None:
        demo = build_demo()
        scopes = {item["scope"] for item in demo["employees"]}
        self.assertTrue({"full", "outlook_only", "review_only", "none"}.issubset(scopes))
        self.assertTrue(any(item["checkpoint_notes"] for item in demo["employees"]))
        self.assertTrue(any(item["meta"]["archived"] for item in demo["employees"]))
        self.assertTrue(any(item["meta"]["closed"] for item in demo["employees"]))
        self.assertTrue(any(item["review"]["agreement"] == "Nein" for item in demo["employees"]))

    def test_template_has_guided_steps_and_collapsed_archive(self) -> None:
        template = (Path(__file__).parent / "template.html").read_text(encoding="utf-8")
        self.assertIn("name:'Grundlagen'", template)
        self.assertIn("Prüfen und PDF", template)
        self.assertIn('id="archive-list"', template)
        self.assertIn('id="update-button"', template)
        self.assertIn("function applyUpdate", template)
        self.assertIn("Vorhandene Gesprächsinhalte", template)
        self.assertNotIn('id="employee-search"', template)
        self.assertNotIn("Interne Übertritte", template)
        self.assertIn("Diese Arbeitsmappe und alle deine Eingaben bleiben bei dir.", template)
        self.assertIn("in der Regel im Download-Ordner", template)
        self.assertNotIn("Arbeitsstand sichern:", template)
        self.assertIn("Clientseitige Standalone-Webanwendung", template)
        self.assertIn("Keine automatische Übertragung von Eingabe- oder Dokumentdaten", template)
        self.assertIn("['Paketnummer', pkg.package_id]", template)
        self.assertIn("['Arbeitsmappenversion', version]", template)
        self.assertIn("['Dateistand', fileDateLabel]", template)
        self.assertNotIn('`VG-PN ${pkg.manager_pn}', template)
        self.assertIn("Vorjahresziele unterstützen das Gespräch", template)
        self.assertIn('data-action="close-case"', template)
        self.assertIn('data-action="reopen-case"', template)
        self.assertIn('data-action="go-requirement"', template)
        self.assertIn("Dokumentstand – von dir gepflegt (optional)", template)
        self.assertNotIn("Erzeuge die PDFs, sobald alle Pflichtangaben vorhanden sind", template)
        self.assertNotIn("Rückblick und Ausblick dürfen an unterschiedlichen Daten stattfinden", template)
        self.assertEqual(template.count("const sectionName ="), 1)
        self.assertIn('id="guidance-button"', template)
        self.assertIn('id="guidance-dialog"', template)
        self.assertIn("Prozessübersicht einklappen", template)
        self.assertNotIn(">Verstanden</button>", template)
        self.assertIn('class="info-icon"', template)
        self.assertNotIn("ⓘ", template)
        self.assertIn("Du musst die Feedbacks nicht zu einem PDF zusammenführen.", template)
        self.assertNotIn("openGuidance(true)", template)
        self.assertIn("selectedStep === 'basics' || selectedStep === 'preparation'", template)
        self.assertIn("Prüfe die aktuelle Auswahl.", template)
        self.assertIn("Bestimmungen zu Spezialfällen", template)
        self.assertIn("falls es sich nicht um einen der dokumentierten Spezialfälle handelt", template)
        self.assertIn("Datei frisch per E-Mail erhalten", template)
        self.assertIn("Leite die erhaltenen PDFs S/MIME-verschlüsselt an HR weiter.", template)

    def test_checkpoint_notes_are_local_optional_and_importable(self) -> None:
        template = (Path(__file__).parent / "template.html").read_text(encoding="utf-8")
        self.assertIn("Begleitung im Jahresverlauf", template)
        self.assertIn("Freiwillige lokale Notizen", template)
        self.assertIn('data-action="add-checkpoint"', template)
        self.assertIn('data-action="import-checkpoints"', template)
        self.assertIn('data-action="lock-checkpoint"', template)
        self.assertIn('data-action="edit-checkpoint"', template)
        self.assertIn("Notiz festhalten", template)
        self.assertNotIn("Bei der Übernahme werden Mitarbeitende über Personalnummer + Ans.", template)
        self.assertIn("weder an HR übermittelt noch in PDFs", template)
        self.assertIn("selectedStep !== 'checkpoints'", template)
        self.assertIn("checkpointExpired", template)
        self.assertIn("function checkpointNotesForReview", template)
        self.assertIn("date >= start && date <= end", template)
        self.assertIn("mergeCheckpointNotes(existing.checkpoint_notes, incoming.checkpoint_notes)", template)

        demo_notes = [
            note
            for employee in build_demo()["employees"]
            for note in employee["checkpoint_notes"]
        ]
        self.assertTrue(demo_notes)
        self.assertTrue(all(note.get("id") for note in demo_notes))

    def test_transferred_previous_goals_are_marked_as_imported(self) -> None:
        employee = self.payload["employees"][0]
        self.assertTrue(all(goal["imported"] for goal in employee["previous_goals"]))
        self.assertTrue(all(goal["imported"] for goal in employee["previous_development_goals"]))

    def test_outlook_requires_its_own_agreement(self) -> None:
        employee = self.payload["employees"][0]
        employee["scope"] = "outlook_only"
        employee["suggestion"]["scope"] = "outlook_only"
        employee["outlook"]["dialog_date"] = "2026-02-10"
        employee["review"]["agreement"] = "Ja"
        status, missing = employee_status(employee)
        self.assertEqual(status, "offen")
        self.assertIn("Einigkeit über Ausblick", missing)
        employee["outlook"]["agreement"] = "Nein"
        self.assertEqual(employee_status(employee), ("vollstaendig", []))

    def test_previous_goal_needs_title_but_not_criteria_steps_or_date(self) -> None:
        employee = self.payload["employees"][0]
        employee["scope"] = "review_only"
        employee["suggestion"]["scope"] = "review_only"
        employee["review"].update({"dialog_date":"2026-01-10", "performance":"Besprochen", "overall_rating":"B – sehr gut", "agreement":"Ja", "secondary_employment_current":"Ja"})
        employee["previous_goals"] = [{"id":"manual", "imported":False, "title":"", "agreement_details":"Optional"}]
        employee["previous_development_goals"] = []
        self.assertIn("Bezeichnung Leistungsziel aus dem Vorjahr 1", employee_status(employee)[1])
        employee["previous_goals"][0]["title"] = "Vereinbartes Ziel"
        self.assertEqual(employee_status(employee), ("vollstaendig", []))


if __name__ == "__main__":
    unittest.main()
