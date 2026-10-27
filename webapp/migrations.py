"""Versioned, transactional, additive migrations. No inferred historical approvals."""
from pathlib import Path
import hashlib
from datetime import datetime, timezone


def migrate(connection):
    connection.execute('''CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY, sha256 TEXT NOT NULL, applied_at TEXT NOT NULL)''')
    connection.commit()
    for path in sorted(Path(__file__).with_suffix('').glob('*.sql')):
        sql = path.read_text(encoding='utf-8')
        digest = hashlib.sha256(sql.encode()).hexdigest()
        try:
            connection.execute('BEGIN IMMEDIATE')
            previous = connection.execute('SELECT sha256 FROM schema_migrations WHERE version=?', (path.stem,)).fetchone()
            if previous:
                if previous[0] != digest:
                    raise ValueError(f'Migration {path.stem} wurde nachträglich verändert.')
            else:
                # execute() keeps DDL and ledger in the same transaction (executescript does not).
                for statement in sql.split(';'):
                    if statement.strip():
                        connection.execute(statement)
                connection.execute('INSERT INTO schema_migrations VALUES (?,?,?)',
                                   (path.stem, digest, datetime.now(timezone.utc).isoformat()))
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def available(connection):
    return bool(connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='hr_goal_sources'").fetchone())
