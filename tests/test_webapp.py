from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import load_workbook
from reportlab.pdfgen import canvas

from prototype.html_dialog.generate_package import render_html
from prototype.html_dialog.validate_package import extract_payload
from webapp import create_app
from webapp.db import get_db
from webapp.adapters.outlook import (
    DraftResult,
    EncryptionVerificationError,
    OutlookDraftAdapter,
)
from webapp.services.cycles import create_cycle, cycle_overview
from webapp.services.cockpit import cockpit_overview
from webapp.services.dialog_events import set_leading_sap_event
from webapp.services.documents import (
    confirm_digital_signature,
    import_handwritten_scan,
    import_official_pdf,
)
from webapp.services.mail_dispatch import create_outlook_drafts, dispatch_candidates
from webapp.services.packages import (
    build_manager_payload,
    create_package_file,
    create_update_file,
    manager_package_state,
)
from webapp.services.sap_export import create_sap_upload_file
from webapp.services.sap_import import import_sap_workbook

from tests.sample_data import create_sap_sample


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FakeOutlookDraftAdapter:
    def __init__(self, *, encryption_flag_verified: bool = True) -> None:
        self.encryption_flag_verified = encryption_flag_verified
        self.calls: list[dict] = []

    def create_encrypted_draft(self, **message) -> DraftResult:
        self.calls.append(message)
        return DraftResult(
            entry_id=f"draft-{len(self.calls)}",
            encryption_flag_verified=self.encryption_flag_verified,
        )


def write_test_pdf(path: Path, data_block: str) -> None:
    document = canvas.Canvas(str(path))
    document.drawString(40, 800, "Mitarbeitenden-Dialog Test")
    document.drawString(40, 770, data_block)
    document.save()


class WebAppIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.sap_sample = create_sap_sample(root / "EXPORT_TEST.xlsx")
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "DATABASE": str(root / "test.sqlite3"),
                "STORAGE_ROOT": str(root / "data"),
                "AUTH_DISABLED": True,
            }
        )
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _prepare_cycle(self) -> int:
        with self.app.app_context():
            connection = get_db()
            imported = import_sap_workbook(
                connection,
                self.sap_sample,
                original_filename="EXPORT.XLSX",
                stored_filename="test_EXPORT.XLSX",
                imported_at=datetime(2025, 9, 17, 12, 0, tzinfo=timezone.utc),
            )
            return create_cycle(
                connection,
                review_year=2025,
                sap_import_id=imported.import_id,
                created_at=datetime(2025, 9, 17, 12, 1, tzinfo=timezone.utc),
            )

    def test_dashboard_starts_with_empty_database(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Mitarbeitenden-Dialoge verwalten", response.get_data(as_text=True))
        self.assertIn("SAP-Stammdaten importieren", response.get_data(as_text=True))
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")

    def test_main_navigation_and_module_pages(self) -> None:
        self._prepare_cycle()
        pages = {
            "/": "Übersicht",
            "/stammdaten": "SAP-Datenstände",
            "/dialoge": "Durchläufe und Dialogpflichten",
            "/versand": "Arbeitsmappen bereitstellen",
            "/ruecklaeufe": "PDFs prüfen und verarbeiten",
            "/sap-export": "Massenuploads erstellen",
            "/auswertungen": "Prozess- und Organisationsauswertungen",
        }
        for path, heading in pages.items():
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                page = response.get_data(as_text=True)
                self.assertIn(heading, page)
                self.assertIn("Stammdaten", page)
                self.assertIn("Rückläufe", page)

    def test_operational_overview_counts_missing_workbooks(self) -> None:
        cycle_id = self._prepare_cycle()
        with self.app.app_context():
            data = cockpit_overview(get_db(), selected_cycle_id=cycle_id)
            self.assertEqual(data["metrics"]["workbooks_missing"], 3)
            self.assertEqual(data["metrics"]["cases_open"], 9)
            self.assertEqual(
                len([task for task in data["tasks"] if task["kind"] == "Arbeitsmappe"]),
                3,
            )

        package = self.client.post(f"/cycles/{cycle_id}/managers/111116/package")
        package.close()
        with self.app.app_context():
            data = cockpit_overview(get_db(), selected_cycle_id=cycle_id)
            self.assertEqual(data["metrics"]["workbooks_missing"], 2)

    def test_start_and_update_files_are_detected_and_generated(self) -> None:
        cycle_id = self._prepare_cycle()
        with self.app.app_context(), tempfile.TemporaryDirectory() as temp:
            connection = get_db()
            create_package_file(
                connection, cycle_id=cycle_id, manager_pn="111116",
                output_dir=Path(temp) / "packages",
            )
            self.assertEqual(
                manager_package_state(
                    connection, cycle_id=cycle_id, manager_pn="111116"
                )["state"],
                "current",
            )
            connection.execute(
                "UPDATE employees SET org_unit = 'abt-neu' WHERE pn = '111111'"
            )
            connection.commit()
            self.assertEqual(
                manager_package_state(
                    connection, cycle_id=cycle_id, manager_pn="111116"
                )["state"],
                "update_required",
            )
            path, payload = create_update_file(
                connection, cycle_id=cycle_id, manager_pn="111116",
                output_dir=Path(temp) / "packages",
            )
            self.assertEqual(path.suffix, ".json")
            self.assertEqual(payload["schema_version"], "1.0-update")
            self.assertEqual(payload["update"]["manager_pn"], "111116")
            self.assertEqual(
                manager_package_state(
                    connection, cycle_id=cycle_id, manager_pn="111116"
                )["state"],
                "current",
            )

    def test_new_sap_import_marks_existing_workbook_for_update(self) -> None:
        cycle_id = self._prepare_cycle()
        with self.app.app_context(), tempfile.TemporaryDirectory() as temp:
            create_package_file(
                get_db(), cycle_id=cycle_id, manager_pn="111116",
                output_dir=Path(temp) / "packages",
            )
        workbook = load_workbook(self.sap_sample)
        worksheet = workbook.active
        headers = {cell.value: cell.column for cell in worksheet[1]}
        for row in range(2, worksheet.max_row + 1):
            if str(worksheet.cell(row, headers["ID_NO_ZERO"]).value) == "111111":
                worksheet.cell(row, headers["OE Bez."], "abt-neu")
        changed = self.sap_sample.with_name("EXPORT_CHANGED.xlsx")
        workbook.save(changed)
        with changed.open("rb") as source:
            response = self.client.post(
                "/imports",
                data={"sap_file": (source, "EXPORT_CHANGED.xlsx")},
                content_type="multipart/form-data",
                follow_redirects=True,
            )
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            self.assertEqual(
                manager_package_state(
                    get_db(), cycle_id=cycle_id, manager_pn="111116"
                )["state"],
                "update_required",
            )

    def test_batch_download_contains_required_start_files(self) -> None:
        cycle_id = self._prepare_cycle()
        response = self.client.post(
            f"/cycles/{cycle_id}/packages/batch",
            data={"selection_mode": "all"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/zip")
        with zipfile.ZipFile(io.BytesIO(response.data)) as archive:
            names = archive.namelist()
        response.close()
        self.assertEqual(len(names), 3)
        self.assertTrue(all(name.startswith("START/") for name in names))

    def test_outlook_draft_is_prepared_and_logged_without_sending(self) -> None:
        cycle_id = self._prepare_cycle()
        with self.app.app_context():
            connection = get_db()
            package_path, _payload = create_package_file(
                connection,
                cycle_id=cycle_id,
                manager_pn="111116",
                output_dir=Path(self.app.config["STORAGE_ROOT"]) / "packages",
            )
            candidates = dispatch_candidates(
                connection, cycle_id=cycle_id, sender_email="md-test@vd.zh.ch"
            )
            candidate = next(
                row for row in candidates if row["manager_pn"] == "111116"
            )
            self.assertTrue(candidate["ready"])
            adapter = FakeOutlookDraftAdapter()
            result = create_outlook_drafts(
                connection,
                cycle_id=cycle_id,
                package_event_ids=[candidate["package_event_id"]],
                sender_email="md-test@vd.zh.ch",
                adapter=adapter,
            )
            self.assertEqual(result, {"created": 1, "failed": 0, "errors": []})
            self.assertEqual(adapter.calls[0]["attachments"], [package_path])
            self.assertEqual(adapter.calls[0]["sender_email"], "md-test@vd.zh.ch")
            delivery = connection.execute(
                "SELECT * FROM mail_deliveries WHERE package_event_id = ?",
                (candidate["package_event_id"],),
            ).fetchone()
            self.assertEqual(delivery["status"], "draft_created")
            self.assertEqual(delivery["encryption_flag_verified"], 1)
            self.assertEqual(delivery["outlook_entry_id"], "draft-1")

        page = self.client.get(f"/versand?cycle_id={cycle_id}")
        self.assertIn("Entwurf erstellt", page.get_data(as_text=True))
        self.assertIn("Automatischer Versand ist gesperrt", page.get_data(as_text=True))

    def test_missing_recipient_blocks_outlook_draft(self) -> None:
        cycle_id = self._prepare_cycle()
        with self.app.app_context():
            connection = get_db()
            connection.execute("UPDATE employees SET email = '' WHERE pn = '111116'")
            connection.commit()
            create_package_file(
                connection,
                cycle_id=cycle_id,
                manager_pn="111116",
                output_dir=Path(self.app.config["STORAGE_ROOT"]) / "packages",
            )
            candidate = next(
                row for row in dispatch_candidates(connection, cycle_id=cycle_id)
                if row["manager_pn"] == "111116"
            )
            adapter = FakeOutlookDraftAdapter()
            result = create_outlook_drafts(
                connection,
                cycle_id=cycle_id,
                package_event_ids=[candidate["package_event_id"]],
                adapter=adapter,
            )
            self.assertEqual(result["created"], 0)
            self.assertEqual(result["failed"], 1)
            self.assertEqual(adapter.calls, [])
            self.assertIn("E-Mail-Adresse fehlt", result["errors"][0])

    def test_outlook_adapter_never_sends_automatically(self) -> None:
        with self.assertRaisesRegex(
            EncryptionVerificationError, "automatische Versand"
        ):
            OutlookDraftAdapter().send()

    def test_cycle_creates_dialog_events_and_separate_obligations(self) -> None:
        cycle_id = self._prepare_cycle()
        with self.app.app_context():
            connection = get_db()
            cycle = connection.execute(
                "SELECT review_due_date, outlook_due_date FROM cycles WHERE id = ?",
                (cycle_id,),
            ).fetchone()
            self.assertEqual(cycle["review_due_date"], "2026-01-31")
            self.assertEqual(cycle["outlook_due_date"], "2026-02-28")
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM dialog_events WHERE cycle_id = ?",
                    (cycle_id,),
                ).fetchone()["count"],
                9,
            )
            event = connection.execute(
                """
                SELECT de.id FROM dialog_events de
                WHERE de.legacy_case_id = '2025-111116-111111'
                """
            ).fetchone()
            obligations = connection.execute(
                """
                SELECT document_kind, due_date FROM document_obligations
                WHERE dialog_event_id = ? ORDER BY document_kind
                """,
                (event["id"],),
            ).fetchall()
            self.assertEqual(
                [(row["document_kind"], row["due_date"]) for row in obligations],
                [("outlook", "2026-02-28"), ("review", "2026-01-31")],
            )

    def test_manual_dialog_event_can_be_added(self) -> None:
        cycle_id = self._prepare_cycle()
        response = self.client.post(
            "/dialog-events",
            data={
                "employee_pn": "111111",
                "assignment_number": "2",
                "manager_pn": "111118",
                "event_type": "probation_review",
                "required_scope": "review_only",
                "review_year": "2025",
                "period_start": "2025-01-01",
                "period_end": "2025-03-31",
                "review_due_date": "2025-04-15",
                "outlook_due_date": "",
                "cycle_id": str(cycle_id),
                "reason": "Probezeitfall gemäss HR-Abklärung",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Rückblick Probezeit", response.get_data(as_text=True))
        with self.app.app_context():
            connection = get_db()
            event = connection.execute(
                """
                SELECT * FROM dialog_events
                WHERE source = 'manual' AND event_type = 'probation_review'
                """
            ).fetchone()
            self.assertIsNotNone(event)
            obligation = connection.execute(
                "SELECT * FROM document_obligations WHERE dialog_event_id = ?",
                (event["id"],),
            ).fetchone()
            self.assertEqual(obligation["document_kind"], "review")
            self.assertEqual(obligation["due_date"], "2025-04-15")
            payload = build_manager_payload(
                connection, cycle_id=cycle_id, manager_pn="111118"
            )
            manual_case = next(
                item for item in payload["employees"]
                if item["case_id"] == event["event_id"]
            )
            self.assertEqual(manual_case["dialog_type"], "probation")
            self.assertEqual(manual_case["suggestion"]["scope"], "review_only")
            set_leading_sap_event(connection, event["id"])

    def test_sap_import_cycle_and_manager_counts(self) -> None:
        cycle_id = self._prepare_cycle()
        with self.app.app_context():
            connection = get_db()
            cycle, managers = cycle_overview(connection, cycle_id)
            self.assertEqual(cycle["review_year"], 2025)
            counts = {row["manager_pn"]: row["case_count"] for row in managers}
            self.assertEqual(counts["111116"], 3)
            self.assertEqual(sum(counts.values()), 9)
            assignment = connection.execute(
                "SELECT employment_assignment FROM employees WHERE pn = '111111'"
            ).fetchone()["employment_assignment"]
            self.assertEqual(assignment, "2")
        response = self.client.get(f"/cycles/{cycle_id}/managers/111116")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Rufname1 Nachname1", response.get_data(as_text=True))

    def test_review_period_is_clipped_to_entry_and_exit(self) -> None:
        cycle_id = self._prepare_cycle()
        with self.app.app_context():
            connection = get_db()
            exit_payload = build_manager_payload(
                connection, cycle_id=cycle_id, manager_pn="111116"
            )
            exiting = next(
                item for item in exit_payload["employees"] if item["employee"]["pn"] == "111112"
            )
            self.assertEqual(exiting["period_start"], "2025-01-01")
            self.assertEqual(exiting["period_end"], "2025-10-31")

            entry_payload = build_manager_payload(
                connection, cycle_id=cycle_id, manager_pn="111118"
            )
            entrant = next(
                item for item in entry_payload["employees"] if item["employee"]["pn"] == "111114"
            )
            self.assertEqual(entrant["period_start"], "2025-09-01")
            self.assertEqual(entrant["period_end"], "2025-12-31")

    def test_sap_export_uses_only_required_columns_and_clipped_period(self) -> None:
        cycle_id = self._prepare_cycle()
        with self.app.app_context(), tempfile.TemporaryDirectory() as temp:
            connection = get_db()
            payload = build_manager_payload(
                connection, cycle_id=cycle_id, manager_pn="111116"
            )
            employee = next(
                item for item in payload["employees"] if item["employee"]["pn"] == "111112"
            )
            employee["scope"] = "review_only"
            employee["scope_reason"] = "Austritt"
            employee["dialog_date"] = "2026-01-21"
            employee["review"]["overall_rating"] = "D – genügend"
            employee["review"]["agreement"] = "Nein"
            connection.execute(
                """
                UPDATE dialog_cases
                SET status = 'vollstaendig', data_json = ?
                WHERE cycle_id = ? AND employee_pn = '111112' AND manager_pn = '111116'
                """,
                (json.dumps(employee, ensure_ascii=False), cycle_id),
            )
            event = connection.execute(
                "SELECT id FROM dialog_events WHERE legacy_case_id = '2025-111116-111112'"
            ).fetchone()
            set_leading_sap_event(connection, event["id"])
            connection.commit()
            path = create_sap_upload_file(
                connection,
                cycle_id=cycle_id,
                template_path=PROJECT_ROOT / "templates" / "massenupload.xlsx",
                output_dir=Path(temp),
                created_at=datetime(2026, 2, 2, 10, 30, tzinfo=timezone.utc),
            )

            worksheet = load_workbook(path).active
            self.assertEqual(worksheet.max_row, 2)
            self.assertEqual(worksheet["A2"].value, 111112)
            self.assertEqual(worksheet["B2"].value, 1)
            self.assertEqual(worksheet["C2"].value.date().isoformat(), "2025-01-01")
            self.assertEqual(worksheet["D2"].value.date().isoformat(), "2025-10-31")
            self.assertEqual(worksheet["E2"].value, 1)
            self.assertEqual(worksheet["F2"].value.date().isoformat(), "2026-01-21")
            self.assertEqual(worksheet["G2"].value.date().isoformat(), "2025-01-01")
            self.assertEqual(worksheet["H2"].value.date().isoformat(), "2025-10-31")
            self.assertEqual(worksheet["I2"].value, "D")
            self.assertTrue(all(worksheet.cell(2, column).value is None for column in range(10, 15)))

    def test_pdf_only_return_is_read_and_staged_for_dossier_handoff(self) -> None:
        cycle_id = self._prepare_cycle()
        with self.app.app_context(), tempfile.TemporaryDirectory() as temp:
            connection = get_db()
            root = Path(temp)
            _package_path, payload = create_package_file(
                connection,
                cycle_id=cycle_id,
                manager_pn="111116",
                output_dir=root / "packages",
            )
            pdf_path = root / "review.pdf"
            write_test_pdf(
                pdf_path,
                "MD-DATENBLOCK ; version=1 ; document=RUECKBLICK ; "
                "case_id=2025-111116-111111 ; "
                f"package_id={payload['package']['package_id']} ; pn=111111 ; ans=2 ; "
                "year=2025 ; scope=review_only ; period_start=2025-01-01 ; "
                "period_end=2025-12-31 ; dialog_date=2026-01-21 ; rating=B ; "
                "agreement=JA ; handwritten_scan_required=NEIN ; no_md_reason=",
            )
            imported = import_official_pdf(
                connection,
                path=pdf_path,
                original_filename="Rueckblick_2025_Nachname1_Rufname1_111111.pdf",
                accepted_dir=root / "processed",
            )
            self.assertFalse(pdf_path.exists())
            case = connection.execute(
                "SELECT * FROM dialog_cases WHERE case_id = '2025-111116-111111'"
            ).fetchone()
            self.assertEqual(case["official_scope"], "review_only")
            self.assertEqual(case["overall_rating_code"], "B")
            self.assertEqual(case["status"], "in_bearbeitung")

            staged = confirm_digital_signature(
                connection,
                document_id=imported["document_id"],
                handoff_dir=root / "dossier_ready",
            )
            self.assertEqual(
                staged["handoff_filename"],
                "Rueckblick_2025_Nachname1_Rufname1_111111.pdf",
            )
            self.assertTrue((root / "dossier_ready" / staged["handoff_filename"]).exists())
            status = connection.execute(
                "SELECT status FROM dialog_cases WHERE case_id = '2025-111116-111111'"
            ).fetchone()["status"]
            self.assertEqual(status, "vollstaendig")
            obligation = connection.execute(
                "SELECT status FROM document_obligations WHERE fulfilled_document_id = ?",
                (imported["document_id"],),
            ).fetchone()
            self.assertEqual(obligation["status"], "complete")

    def test_required_scan_replaces_digital_pdf_for_dossier_handoff(self) -> None:
        cycle_id = self._prepare_cycle()
        with self.app.app_context(), tempfile.TemporaryDirectory() as temp:
            connection = get_db()
            root = Path(temp)
            _package_path, payload = create_package_file(
                connection,
                cycle_id=cycle_id,
                manager_pn="111116",
                output_dir=root / "packages",
            )
            pdf_path = root / "review-d.pdf"
            write_test_pdf(
                pdf_path,
                "MD-DATENBLOCK ; version=1 ; document=RUECKBLICK ; "
                "case_id=2025-111116-111111 ; "
                f"package_id={payload['package']['package_id']} ; pn=111111 ; ans=2 ; "
                "year=2025 ; scope=review_only ; period_start=2025-01-01 ; "
                "period_end=2025-12-31 ; dialog_date=2026-01-21 ; rating=D ; "
                "agreement=NEIN ; handwritten_scan_required=JA ; no_md_reason=",
            )
            imported = import_official_pdf(
                connection,
                path=pdf_path,
                original_filename="Rueckblick_2025_Nachname1_Rufname1_111111.pdf",
                accepted_dir=root / "processed",
            )
            confirmed = confirm_digital_signature(
                connection,
                document_id=imported["document_id"],
                handoff_dir=root / "dossier_ready",
            )
            self.assertTrue(confirmed["scan_required"])
            self.assertEqual(list((root / "dossier_ready").glob("*.pdf")), [])
            obligation = connection.execute(
                "SELECT status FROM document_obligations WHERE fulfilled_document_id = ?",
                (imported["document_id"],),
            ).fetchone()
            self.assertEqual(obligation["status"], "scan_pending")

            scan_path = root / "scan.pdf"
            write_test_pdf(scan_path, "Handschriftlich unterzeichnet")
            scan = import_handwritten_scan(
                connection,
                case_id="2025-111116-111111",
                document_kind="review",
                path=scan_path,
                original_filename="scan.pdf",
                handoff_dir=root / "dossier_ready",
            )
            self.assertEqual(
                scan["handoff_filename"],
                "Rueckblick_2025_Nachname1_Rufname1_HANDSCAN_111111.pdf",
            )
            handoff_files = [path.name for path in (root / "dossier_ready").glob("*.pdf")]
            self.assertEqual(handoff_files, [scan["handoff_filename"]])
            digital = connection.execute(
                "SELECT * FROM official_documents WHERE id = ?", (imported["document_id"],)
            ).fetchone()
            self.assertTrue(Path(digital["stored_path"]).exists())
            self.assertNotEqual(Path(digital["stored_path"]).parent, root / "dossier_ready")
            obligation = connection.execute(
                "SELECT status, fulfilled_document_id FROM document_obligations WHERE id = ?",
                (digital["document_obligation_id"],),
            ).fetchone()
            self.assertEqual(obligation["status"], "complete")
            self.assertEqual(obligation["fulfilled_document_id"], scan["document_id"])

    def test_no_md_pdf_closes_case_without_dossier_handoff(self) -> None:
        cycle_id = self._prepare_cycle()
        with self.app.app_context(), tempfile.TemporaryDirectory() as temp:
            connection = get_db()
            root = Path(temp)
            _package_path, payload = create_package_file(
                connection,
                cycle_id=cycle_id,
                manager_pn="111116",
                output_dir=root / "packages",
            )
            pdf_path = root / "no-md.pdf"
            write_test_pdf(
                pdf_path,
                "MD-DATENBLOCK ; version=1 ; document=KEIN_MD ; "
                "case_id=2025-111116-111112 ; "
                f"package_id={payload['package']['package_id']} ; pn=111112 ; ans=1 ; "
                "year=2025 ; scope=none ; period_start=2025-01-01 ; "
                "period_end=2025-10-31 ; dialog_date= ; rating= ; agreement= ; "
                "handwritten_scan_required=NEIN ; no_md_reason=Austritt",
            )
            imported = import_official_pdf(
                connection,
                path=pdf_path,
                original_filename="Kein_MD_2025_Nachname2_Rufname2_111112.pdf",
                accepted_dir=root / "processed",
            )
            self.assertEqual(imported["document_kind"], "no_md")
            case = connection.execute(
                "SELECT status, official_scope FROM dialog_cases WHERE case_id = '2025-111116-111112'"
            ).fetchone()
            self.assertEqual(case["status"], "kein_md")
            self.assertEqual(case["official_scope"], "none")
            self.assertFalse((root / "dossier_ready").exists())

    def test_package_download_and_saved_return_roundtrip(self) -> None:
        cycle_id = self._prepare_cycle()
        response = self.client.post(f"/cycles/{cycle_id}/managers/111116/package")
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "MD_Dialog_2025_2026_Nachname6_Rufname6_111116_START.html",
            response.headers["Content-Disposition"],
        )

        with tempfile.TemporaryDirectory() as temp:
            start_path = Path(temp) / "start.html"
            start_path.write_bytes(response.data)
            payload = extract_payload(start_path)
        response.close()
        payload["package"]["revision"] = 1
        payload["package"]["saved_at"] = "2025-09-17T12:30:00+00:00"
        returned_html = render_html(payload).encode("utf-8")
        response = self.client.post(
            "/returns",
            data={
                "return_file": (
                    io.BytesIO(returned_html),
                    "MD_Dialog_2025_2026_Nachname6_Rufname6_111116_BEARBEITET_v01_20250917_1230.html",
                )
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Rücklauf von Rufname6 Nachname6", response.get_data(as_text=True))

        duplicate_response = self.client.post(
            "/returns",
            data={
                "return_file": (
                    io.BytesIO(returned_html),
                    "MD_Dialog_2025_2026_Nachname6_Rufname6_111116_BEARBEITET_v01_20250917_1230.html",
                )
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertIn("wurde bereits importiert oder ist veraltet", duplicate_response.get_data(as_text=True))

        with self.app.app_context():
            connection = get_db()
            events = connection.execute(
                "SELECT direction FROM package_events ORDER BY id"
            ).fetchall()
            self.assertEqual([row["direction"] for row in events], ["versand", "ruecklauf"])
            _cycle, managers = cycle_overview(connection, cycle_id)
            manager = next(row for row in managers if row["manager_pn"] == "111116")
            self.assertEqual(manager["case_count"], 3)

    def test_start_file_cannot_be_imported_as_return(self) -> None:
        cycle_id = self._prepare_cycle()
        package = self.client.post(f"/cycles/{cycle_id}/managers/111116/package")
        package_data = package.data
        package.close()
        response = self.client.post(
            "/returns",
            data={"return_file": (io.BytesIO(package_data), "START.html")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        self.assertIn("Die Datei ist noch eine Startdatei", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
