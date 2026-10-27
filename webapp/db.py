"""SQLite-Verbindung und Schema-Initialisierung."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import click
from flask import Flask, current_app, g


def connect_database(path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(path), detect_types=sqlite3.PARSE_DECLTYPES)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect_database(current_app.config["DATABASE"])
    return g.db


def close_db(_error: BaseException | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db(connection: sqlite3.Connection | None = None, *, hr_goals: bool = False) -> None:
    owns_connection = connection is None
    if connection is None:
        connection = get_db()
    schema_path = Path(__file__).with_name("schema.sql")
    connection.executescript(schema_path.read_text(encoding="utf-8"))
    employee_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(employees)").fetchall()
    }
    if "salutation" not in employee_columns:
        connection.execute("ALTER TABLE employees ADD COLUMN salutation TEXT NOT NULL DEFAULT ''")
    if "employment_assignment" not in employee_columns:
        connection.execute(
            "ALTER TABLE employees ADD COLUMN employment_assignment TEXT NOT NULL DEFAULT ''"
        )
    if "active" not in employee_columns:
        connection.execute(
            "ALTER TABLE employees ADD COLUMN active INTEGER NOT NULL DEFAULT 1"
        )
    reporting_line_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(reporting_lines)").fetchall()
    }
    if "employment_assignment" not in reporting_line_columns:
        connection.execute(
            "ALTER TABLE reporting_lines ADD COLUMN employment_assignment TEXT NOT NULL DEFAULT ''"
        )
    case_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(dialog_cases)").fetchall()
    }
    for column in (
        "employment_assignment",
        "official_scope",
        "dialog_date",
        "period_start",
        "period_end",
        "overall_rating_code",
        "agreement",
    ):
        if column not in case_columns:
            connection.execute(
                f"ALTER TABLE dialog_cases ADD COLUMN {column} TEXT NOT NULL DEFAULT ''"
            )
    if "active" not in case_columns:
        connection.execute(
            "ALTER TABLE dialog_cases ADD COLUMN active INTEGER NOT NULL DEFAULT 1"
        )
    cycle_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(cycles)").fetchall()
    }
    for column in ("review_due_date", "outlook_due_date"):
        if column not in cycle_columns:
            connection.execute(
                f"ALTER TABLE cycles ADD COLUMN {column} TEXT NOT NULL DEFAULT ''"
            )
    event_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(dialog_events)").fetchall()
    }
    if "dialog_date" not in event_columns:
        connection.execute(
            "ALTER TABLE dialog_events ADD COLUMN dialog_date TEXT NOT NULL DEFAULT ''"
        )
    document_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(official_documents)").fetchall()
    }
    if "dialog_event_id" not in document_columns:
        connection.execute(
            "ALTER TABLE official_documents ADD COLUMN dialog_event_id INTEGER REFERENCES dialog_events(id)"
        )
    if "document_obligation_id" not in document_columns:
        connection.execute(
            "ALTER TABLE official_documents ADD COLUMN document_obligation_id INTEGER REFERENCES document_obligations(id)"
        )
    if "replaces_document_id" not in document_columns:
        connection.execute(
            "ALTER TABLE official_documents ADD COLUMN replaces_document_id INTEGER REFERENCES official_documents(id)"
        )
    for column in ("replacement_reason", "replaced_at"):
        if column not in document_columns:
            connection.execute(
                f"ALTER TABLE official_documents ADD COLUMN {column} TEXT NOT NULL DEFAULT ''"
            )
    package_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(package_events)").fetchall()
    }
    if "package_kind" not in package_columns:
        connection.execute(
            "ALTER TABLE package_events ADD COLUMN package_kind TEXT NOT NULL DEFAULT 'start'"
        )
        connection.execute(
            "UPDATE package_events SET package_kind = 'return' WHERE direction = 'ruecklauf'"
        )
    if "stored_path" not in package_columns:
        connection.execute(
            "ALTER TABLE package_events ADD COLUMN stored_path TEXT NOT NULL DEFAULT ''"
        )
    word_package_columns = {row['name'] for row in connection.execute('PRAGMA table_info(word_dispatch_packages)')}
    if 'discarded_at' not in word_package_columns:
        connection.execute("ALTER TABLE word_dispatch_packages ADD COLUMN discarded_at TEXT NOT NULL DEFAULT ''")
    inbound_mail_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(inbound_mail_messages)").fetchall()
    }
    if "review_completed_at" not in inbound_mail_columns:
        connection.execute(
            "ALTER TABLE inbound_mail_messages "
            "ADD COLUMN review_completed_at TEXT NOT NULL DEFAULT ''"
        )
    if 'review_note' not in inbound_mail_columns:
        connection.execute("ALTER TABLE inbound_mail_messages ADD COLUMN review_note TEXT NOT NULL DEFAULT ''")
    from .migrations import available
    if hr_goals or available(connection):
        # Do not replay legacy startup data rewrites in the new workflow.
        connection.commit()
        from .migrations import migrate
        migrate(connection)
        if owns_connection:
            connection.close()
            g.pop("db", None)
        return
    # Offene Altfälle an die aktuelle Scanregel anpassen; bereits bereitgestellte Dateien bleiben unangetastet.
    connection.execute("""UPDATE official_documents SET scan_required=0,signature_checked=0,handoff_status='needs_signature_check'
        WHERE is_current=1 AND variant='digital' AND scan_required=1 AND handoff_status IN ('waiting_scan','needs_signature_check')
        AND (document_kind<>'review' OR UPPER(COALESCE(json_extract(data_block_json,'$.rating'),'')) NOT IN ('D','E'))""")
    connection.commit()
    from .services.dialog_events import backfill_dialog_model

    backfill_dialog_model(connection)
    from .services.cycles import repair_probation_boundary
    repair_probation_boundary(connection)
    import json
    for feedback in connection.execute('SELECT * FROM feedback_submissions WHERE bundle_id IS NULL').fetchall():
        parsed={'data':{'document_kind':'feedback','manager_pn':feedback['manager_pn']},'issues':[],'feedback_fields':{},'text':''}
        connection.execute("""INSERT OR IGNORE INTO word_pdf_imports(original_filename,stored_path,sha256,parsed_json,reviewed_json,status,created_at)
            VALUES (?,?,?,?,?,'imported',?)""",(feedback['original_filename'],feedback['stored_path'],feedback['sha256'],json.dumps(parsed),json.dumps({'cycle_id':feedback['cycle_id'],'manager_pn':feedback['manager_pn'],'feedback_fields':{}}),feedback['received_at']))
        imported=connection.execute('SELECT id FROM word_pdf_imports WHERE sha256=?',(feedback['sha256'],)).fetchone()
        connection.execute('INSERT OR IGNORE INTO word_feedback_submissions(import_id,cycle_id,manager_pn) VALUES (?,?,?)',(imported['id'],feedback['cycle_id'],feedback['manager_pn']))
    connection.commit()
    if owns_connection:
        connection.close()
        g.pop("db", None)


@click.command("init-db")
def init_db_command() -> None:
    init_db(hr_goals=current_app.config.get("HR_GOAL_WORKFLOW", False))
    click.echo("SQLite-Datenbank initialisiert.")


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    with app.app_context():
        init_db(hr_goals=app.config.get("HR_GOAL_WORKFLOW", False))
