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


def init_db(connection: sqlite3.Connection | None = None) -> None:
    owns_connection = connection is None
    if connection is None:
        connection = get_db()
    schema_path = Path(__file__).with_name("schema.sql")
    connection.executescript(schema_path.read_text(encoding="utf-8"))
    employee_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(employees)").fetchall()
    }
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
    cycle_columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(cycles)").fetchall()
    }
    for column in ("review_due_date", "outlook_due_date"):
        if column not in cycle_columns:
            connection.execute(
                f"ALTER TABLE cycles ADD COLUMN {column} TEXT NOT NULL DEFAULT ''"
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
    connection.commit()
    from .services.dialog_events import backfill_dialog_model

    backfill_dialog_model(connection)
    if owns_connection:
        connection.close()
        g.pop("db", None)


@click.command("init-db")
def init_db_command() -> None:
    init_db()
    click.echo("SQLite-Datenbank initialisiert.")


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    with app.app_context():
        init_db()
