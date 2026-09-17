from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

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


if __name__ == "__main__":
    unittest.main()
