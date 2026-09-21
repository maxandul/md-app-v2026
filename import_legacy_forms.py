"""Importiert Ziele aus früheren MD-Word-Formularen in die lokale Datenbank."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from webapp import create_app
from webapp.db import get_db
from webapp.services.legacy_forms import import_legacy_forms, scan_legacy_forms


def _summary(result: dict) -> dict:
    return {
        "goal_year": result["goal_year"],
        "files_found": result["files_found"],
        "status_counts": result["counts"],
        "performance_goals": result["performance_goals"],
        "development_goals": result["development_goals"],
        **({"imported": result["imported"]} if "imported" in result else {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Liest frühere MD-DOCX/DOCM-Dateien. Ohne --apply wird nur eine "
            "Vorschau erstellt; die Datenbank bleibt unverändert."
        )
    )
    parser.add_argument("forms_root", type=Path, help="Ordner mit früheren Word-Formularen")
    parser.add_argument("--goal-year", type=int, required=True, help="Jahr, für das die Ziele gelten")
    parser.add_argument("--database", type=Path, help="Abweichender Pfad zur SQLite-Datenbank")
    parser.add_argument("--apply", action="store_true", help="Eindeutig zugeordnete Ziele importieren")
    parser.add_argument(
        "--report", type=Path,
        help="Optionaler Detailbericht; enthält Dateinamen und Personalnummern und ist geschützt abzulegen",
    )
    args = parser.parse_args()
    if not args.forms_root.is_dir():
        parser.error("Der angegebene Formularordner existiert nicht.")
    config = {"DATABASE": str(args.database)} if args.database else None
    app = create_app(config)
    with app.app_context():
        result = (
            import_legacy_forms(get_db(), forms_root=args.forms_root, goal_year=args.goal_year)
            if args.apply else
            scan_legacy_forms(get_db(), forms_root=args.forms_root, goal_year=args.goal_year)
        )
    print(json.dumps(_summary(result), ensure_ascii=False, indent=2, sort_keys=True))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        report = {
            **_summary(result),
            "items": [
                {
                    "filename": item["filename"],
                    "employee_pn": item["employee_pn"],
                    "assignment_number": item["assignment_number"],
                    "resolved_assignment": item["resolved_assignment"],
                    "status": item["status"],
                    "performance_goals": len(item["performance_goals"]),
                    "development_goals": len(item["development_goals"]),
                    "error": item["error"],
                }
                for item in result["items"]
            ],
        }
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
