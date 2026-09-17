"""Erzeugt vollständig synthetische SAP-Testdaten ohne Personendaten."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def create_sap_sample(path: Path) -> Path:
    rows = [
        ("111111", "Rufname1", "Nachname1", None, 90, "2020-05-01", "2020-07-31", "abt1", "111116", "2"),
        ("111112", "Rufname2", "Nachname2", "2025-10-31", 100, "2020-05-02", None, "abt1", "111116", "1"),
        ("111113", "Rufname3", "Nachname3", None, 100, "2020-05-03", None, "abt1", "111116", "1"),
        ("111114", "Rufname4", "Nachname4", None, 100, "2025-09-01", "2025-11-30", "abt1", "111118", None),
        ("111115", "Rufname5", "Nachname5", None, 100, "2020-05-05", None, "abt2", "111117", "4"),
        ("111116", "Rufname6", "Nachname6", None, 100, "2020-05-06", None, "abt1", "111118", "3"),
        ("111113", "Rufname3", "Nachname3", None, 100, "2020-05-03", None, "abt1", "111116", "1"),
        ("111117", "Rufname7", "Nachname7", None, 100, "2020-05-05", None, "abt2", "111118", "4"),
        ("111112", "Rufname2", "Nachname2", "2025-10-31", 100, "2020-05-02", None, "abt2", "111117", "1"),
        ("111118", "Rufname8", "Nachname8", None, 100, "2020-05-06", None, "gl", "000000", "3"),
        ("111111", "Rufname1", "Nachname1", None, 90, "2020-05-01", "2020-07-31", "abt1", "111117", "2"),
    ]
    frame = pd.DataFrame(
        rows,
        columns=[
            "ID_NO_ZERO",
            "Rufname",
            "Nachname",
            "Austritt",
            "BsGrd",
            "Eintritt",
            "Ende Probezeit",
            "OE Bez.",
            "Dir. Vorgesetzter (PN)",
            "Ans.",
        ],
    )
    frame["Plans. Bez."] = "Fachleiter/in Finanzen u. QM"
    frame["lange ID/Nummer"] = frame["ID_NO_ZERO"].map(
        lambda pn: f"person-{pn}@example.invalid"
    )
    frame["Bewilligung für"] = None
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_excel(path, index=False)
    return path
