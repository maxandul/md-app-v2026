from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from openpyxl import Workbook

from webapp import create_app
from webapp.db import get_db
from webapp.services.sap_import import import_sap_workbook


def write_sap(path: Path, rows: list[dict]) -> Path:
    pd.DataFrame(rows).to_excel(path, index=False)
    return path


def sap_row(pn: str, *, ans: str = "1", bg: int = 100, last_name: str = "Test", permission: str = "", permission_for: str = "") -> dict:
    return {
        "ID_NO_ZERO": pn,
        "Rufname": "Rufname",
        "Nachname": last_name,
        "Dir. Vorgesetzter (PN)": "900001",
        "lange ID/Nummer": f"person-{pn}@example.invalid",
        "Ans.": ans,
        "BG": bg,
        "Eintritt": "2020-01-01",
        "Austritt": None,
        "Ende Probezeit": None,
        "Plans. Bez.": "Funktion",
        "OE Bez.": "Organisation",
        "Beginn Bewilligung": "2026-01-01" if permission else None,
        "Ende Bewilligung": "2026-12-31" if permission else None,
        "Bewilligung": permission,
        "Bewilligung für": permission_for,
    }


class AuthAndSapSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.root = root
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": str(root / "test.sqlite3"),
            "STORAGE_ROOT": str(root / "data"),
            "BACKUP_ROOT": str(root / "backups"),
            "AUTH_DISABLED": False,
        })
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_first_admin_setup_and_login_are_required(self) -> None:
        response = self.client.get("/", follow_redirects=True)
        self.assertIn("Erstes Administrationskonto", response.get_data(as_text=True))

        response = self.client.post("/auth/setup", data={
            "email": "hr@example.invalid",
            "password": "Ein langes Testpasswort 2026!",
            "confirmation": "Ein langes Testpasswort 2026!",
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Mitarbeitenden-Dialoge verwalten", response.get_data(as_text=True))

        self.client.post("/auth/logout")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers["Location"])
        response = self.client.post("/auth/login", data={
            "email": "hr@example.invalid",
            "password": "Ein langes Testpasswort 2026!",
        }, follow_redirects=True)
        self.assertIn("Mitarbeitenden-Dialoge verwalten", response.get_data(as_text=True))

    def test_failed_login_is_audited_without_attempted_identity(self) -> None:
        self.client.post("/auth/setup", data={
            "email": "hr@example.invalid",
            "password": "Ein langes Testpasswort 2026!",
            "confirmation": "Ein langes Testpasswort 2026!",
        })
        self.client.post("/auth/logout")
        self.client.post("/auth/login", data={
            "email": "unbekannt@example.invalid",
            "password": "falsch",
        })
        with self.app.app_context():
            row = get_db().execute(
                "SELECT object_type, object_id, details_json FROM audit_log WHERE action = 'login_failed'"
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["object_type"], "authentication")
            self.assertEqual(row["object_id"], "")
            self.assertEqual(row["details_json"], "{}")

    def test_sap_rows_are_classified_and_absent_people_become_inactive(self) -> None:
        base = sap_row("100001", permission="bewilligt", permission_for="Mandat A")
        rows = [
            base,
            dict(base),
            sap_row("100001", permission="bewilligt", permission_for="Mandat B"),
            sap_row("100001", ans="2"),
            sap_row("100002", bg=0),
            sap_row("100003", last_name="Variante A"),
            sap_row("100003", last_name="Variante B"),
        ]
        first = write_sap(self.root / "first.xlsx", rows)
        with self.app.app_context():
            connection = get_db()
            result = import_sap_workbook(connection, first, original_filename="first.xlsx", stored_filename="first.xlsx", imported_at=datetime(2026, 9, 17, tzinfo=timezone.utc))
            self.assertEqual(result.ignored_bg_zero_count, 1)
            self.assertEqual(result.exact_duplicate_count, 1)
            self.assertEqual(result.multiple_employment_count, 1)
            self.assertEqual(result.multiple_permission_count, 1)
            self.assertEqual(result.conflict_count, 1)
            types = {row["issue_type"] for row in connection.execute("SELECT issue_type FROM sap_import_issues WHERE sap_import_id = ?", (result.import_id,))}
            self.assertTrue({"exact_duplicate", "multiple_employment", "multiple_permissions", "conflicting_duplicate"}.issubset(types))
            self.assertIsNone(connection.execute("SELECT 1 FROM persons WHERE person_number = '100002'").fetchone())

            second = write_sap(self.root / "second.xlsx", [sap_row("100001")])
            import_sap_workbook(connection, second, original_filename="second.xlsx", stored_filename="second.xlsx", imported_at=datetime(2026, 9, 18, tzinfo=timezone.utc))
            inactive = connection.execute("SELECT active FROM persons WHERE person_number = '100003'").fetchone()
            self.assertEqual(inactive["active"], 0)

    def test_unchanged_sap_profile_and_bg_zero_manager_are_supported(self) -> None:
        path = self.root / "standard-export.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.append([
            "ID_NO_ZERO", "Rufname", "Nachname", "Austritt", "AG",
            "Austrittsgrund Anstellung", "BsGrd", "Eintritt", "Ende Probezeit",
            "OE Bez.", "Plans. Bez.", "Dir. Vorgesetzter", "Dir. Vorgesetzter",
            "lange ID/Nummer", "OE Kurzb.", "Beginn", "Ende", "Bewilligung",
            "Bewilligung für", "Bewilligung für", "Bewilligung für",
            "Bewilligung für", "Bewilligung für", "Ans.",
        ])
        sheet.append([
            "900000", "Direktion", "Leitung", None, None, None, 0,
            "2020-01-01", None, "Direktion", "Direktionsleitung", "Extern", "999999",
            "direktion@example.invalid", "DL", None, None, None, None, None, None, None, None, "1",
        ])
        sheet.append([
            "100000", "Amt", "Vorstehend", None, None, None, 100,
            "2020-01-01", None, "Amt", "Amtsvorstehung", "Direktion", "900000",
            "amt@example.invalid", "AMT", None, None, None, None, None, None, None, None, "1",
        ])
        sheet.append([
            "100001", "Mara", "Beispiel", None, None, None, 80,
            "2022-01-01", None, "Team", "Funktion", "Amt", "100000",
            "mara@example.invalid", "TEAM", "2026-01-01", "2026-12-31",
            "Nebenbeschäftigung", "Mandat", "Zusatz", None, None, None, "2",
        ])
        workbook.save(path)

        with self.app.app_context():
            connection = get_db()
            result = import_sap_workbook(
                connection, path, original_filename=path.name,
                stored_filename=path.name,
                imported_at=datetime(2026, 9, 19, tzinfo=timezone.utc),
            )
            self.assertEqual(result.ignored_bg_zero_count, 1)
            self.assertIsNone(
                connection.execute(
                    "SELECT 1 FROM persons WHERE person_number = '900000'"
                ).fetchone()
            )
            lines = connection.execute(
                "SELECT employee_pn, manager_pn FROM reporting_lines ORDER BY employee_pn"
            ).fetchall()
            self.assertEqual(
                [(row["employee_pn"], row["manager_pn"]) for row in lines],
                [("100001", "100000")],
            )
            permission = connection.execute(
                "SELECT permission_for FROM secondary_activity_permissions"
            ).fetchone()
            self.assertEqual(permission["permission_for"], "Mandat\nZusatz")


if __name__ == "__main__":
    unittest.main()
