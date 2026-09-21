"""Auditansicht sowie geprüfte lokale Backup- und Restore-Verfahren."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from webapp.db import connect_database


BACKUP_VERSION = 1
REQUIRED_TABLES = {"app_users", "audit_log", "dialog_cases", "dialog_events", "official_documents"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _files(root: Path, *, excluded_roots: tuple[Path, ...] = ()):
    excluded = tuple(path.resolve() for path in excluded_roots)
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            resolved = path.resolve()
            if path.is_file() and not any(resolved.is_relative_to(item) for item in excluded):
                yield path


def create_system_backup(
    connection: sqlite3.Connection, *, database_path: Path, storage_root: Path,
    dossier_root: Path, backup_root: Path, created_at: datetime | None = None,
) -> dict[str, Any]:
    created = created_at or datetime.now().astimezone()
    backup_root.mkdir(parents=True, exist_ok=True)
    filename = f"MD_Backup_{created.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.zip"
    target = backup_root / filename
    manifest: dict[str, Any] = {
        "backup_version": BACKUP_VERSION,
        "created_at": created.isoformat(timespec="seconds"),
        "dossier_in_storage": dossier_root.is_relative_to(storage_root),
        "files": [],
    }
    with tempfile.TemporaryDirectory(dir=backup_root) as temp_name:
        snapshot = Path(temp_name) / "database.sqlite3"
        temporary_target = Path(temp_name) / filename
        snapshot_connection = sqlite3.connect(str(snapshot))
        try:
            connection.backup(snapshot_connection)
        finally:
            snapshot_connection.close()
        with zipfile.ZipFile(temporary_target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            entries = [(snapshot, "database.sqlite3")]
            entries.extend(
                (path, f"storage/{path.relative_to(storage_root).as_posix()}")
                for path in _files(storage_root, excluded_roots=(backup_root,))
            )
            if not manifest["dossier_in_storage"]:
                entries.extend(
                    (path, f"dossier/{path.relative_to(dossier_root).as_posix()}")
                    for path in _files(dossier_root, excluded_roots=(backup_root,))
                )
            for path, archive_name in entries:
                archive.write(path, archive_name)
                manifest["files"].append({
                    "path": archive_name, "sha256": _sha256(path), "size": path.stat().st_size,
                })
            archive.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2),
            )
        os.replace(temporary_target, target)
    return {"path": target, "filename": filename, "sha256": _sha256(target), "file_count": len(manifest["files"])}


def list_backups(backup_root: Path) -> list[dict[str, Any]]:
    result = []
    if not backup_root.is_dir():
        return result
    for path in sorted(backup_root.glob("MD_Backup_*.zip"), reverse=True):
        result.append({
            "filename": path.name, "path": str(path), "size": path.stat().st_size,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
        })
    return result


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and "\\" not in name


def validate_backup(path: Path, *, max_uncompressed_bytes: int = 2 * 1024**3) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos if not item.is_dir()]
            if len(names) != len(set(names)) or any(not _safe_member(name) for name in names):
                raise ValueError("Das Backup enthält unsichere oder doppelte Dateipfade.")
            if sum(item.file_size for item in infos) > max_uncompressed_bytes:
                raise ValueError("Das entpackte Backup überschreitet die zulässige Grösse.")
            if "manifest.json" not in names:
                raise ValueError("Im Backup fehlt das Manifest.")
            manifest = json.loads(archive.read("manifest.json"))
            if manifest.get("backup_version") != BACKUP_VERSION:
                raise ValueError("Die Backup-Version wird nicht unterstützt.")
            expected = {item["path"]: item for item in manifest.get("files", [])}
            if set(names) != set(expected) | {"manifest.json"} or "database.sqlite3" not in expected:
                raise ValueError("Manifest und enthaltene Dateien stimmen nicht überein.")
            for name, item in expected.items():
                digest = hashlib.sha256()
                size = 0
                with archive.open(name) as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        size += len(chunk)
                        digest.update(chunk)
                if size != item.get("size") or digest.hexdigest() != item.get("sha256"):
                    raise ValueError(f"Prüfsumme des Backup-Eintrags «{name}» ist ungültig.")
            with tempfile.TemporaryDirectory() as temp_name:
                database_copy = Path(temp_name) / "database.sqlite3"
                with archive.open("database.sqlite3") as source, database_copy.open("wb") as target:
                    shutil.copyfileobj(source, target)
                connection = connect_database(database_copy)
                try:
                    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise ValueError("Die gesicherte Datenbank ist beschädigt.")
                    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
                    if not REQUIRED_TABLES.issubset(tables):
                        raise ValueError("Die gesicherte Datenbank hat nicht die erwartete Struktur.")
                finally:
                    connection.close()
            return manifest
    except (zipfile.BadZipFile, json.JSONDecodeError, AttributeError, KeyError, TypeError) as exc:
        raise ValueError("Die Datei ist kein gültiges MD-Backup.") from exc


def restore_system_backup(
    backup_path: Path, *, database_path: Path, storage_root: Path, dossier_root: Path,
) -> dict[str, Any]:
    manifest = validate_backup(backup_path)
    token = uuid.uuid4().hex[:8]
    new_database = database_path.parent / f".{database_path.name}.restore-{token}"
    new_storage = storage_root.parent / f".{storage_root.name}.restore-{token}"
    external_dossier = not dossier_root.is_relative_to(storage_root)
    new_dossier = dossier_root.parent / f".{dossier_root.name}.restore-{token}"
    old_database = database_path.parent / f".{database_path.name}.rollback-{token}"
    old_storage = storage_root.parent / f".{storage_root.name}.rollback-{token}"
    old_dossier = dossier_root.parent / f".{dossier_root.name}.rollback-{token}"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    new_storage.mkdir(parents=True)
    if external_dossier:
        new_dossier.mkdir(parents=True)
    try:
        with zipfile.ZipFile(backup_path) as archive:
            with archive.open("database.sqlite3") as source, new_database.open("wb") as target:
                shutil.copyfileobj(source, target)
            for item in manifest["files"]:
                name = item["path"]
                if name.startswith("storage/"):
                    target = new_storage / name.removeprefix("storage/")
                elif external_dossier and name.startswith("dossier/"):
                    target = new_dossier / name.removeprefix("dossier/")
                else:
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
        moved: list[tuple[Path, Path]] = []
        try:
            if database_path.exists():
                os.replace(database_path, old_database)
                moved.append((old_database, database_path))
            os.replace(new_database, database_path)
            if storage_root.exists():
                os.replace(storage_root, old_storage); moved.append((old_storage, storage_root))
            os.replace(new_storage, storage_root)
            if external_dossier:
                if dossier_root.exists():
                    os.replace(dossier_root, old_dossier)
                    moved.append((old_dossier, dossier_root))
                os.replace(new_dossier, dossier_root)
            check = connect_database(database_path)
            try:
                if check.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Die wiederhergestellte Datenbank ist beschädigt.")
            finally:
                check.close()
        except Exception:
            for rollback, original in reversed(moved):
                if original.is_dir():
                    shutil.rmtree(original)
                elif original.exists():
                    original.unlink()
                os.replace(rollback, original)
            raise
        for rollback, _original in moved:
            if rollback.is_dir():
                shutil.rmtree(rollback)
            elif rollback.exists():
                rollback.unlink()
    finally:
        for leftover in (new_database, new_storage, new_dossier):
            if leftover.is_dir():
                shutil.rmtree(leftover, ignore_errors=True)
            elif leftover.exists():
                leftover.unlink()
    return {"created_at": manifest["created_at"], "file_count": len(manifest["files"])}


def audit_rows(connection: sqlite3.Connection, *, limit: int = 200) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT al.*, COALESCE(u.email, 'System / nicht angemeldet') AS user_email
        FROM audit_log al LEFT JOIN app_users u ON u.id = al.user_id
        ORDER BY al.created_at DESC, al.id DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["details"] = json.loads(item["details_json"] or "{}")
        except json.JSONDecodeError:
            item["details"] = {}
        result.append(item)
    return result
