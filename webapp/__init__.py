"""Flask-Anwendung für die administrative MD-Verarbeitung."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Flask

from . import db


def _secret_key(instance_path: str) -> str:
    configured = os.environ.get("MD_SECRET_KEY", "").strip()
    if configured:
        return configured
    path = Path(instance_path) / "secret_key"
    if path.exists():
        stored = path.read_text(encoding="utf-8").strip()
        if stored:
            return stored
    path.parent.mkdir(parents=True, exist_ok=True)
    generated = secrets.token_hex(32)
    path.write_text(generated, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return generated


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=_secret_key(app.instance_path),
        DATABASE=str(Path(app.instance_path) / "md.sqlite3"),
        STORAGE_ROOT=str(Path(app.instance_path) / "data"),
        BACKUP_ROOT=str(Path(app.instance_path) / "backups"),
        MAX_CONTENT_LENGTH=25 * 1024 * 1024,
        MAX_BACKUP_CONTENT_LENGTH=2 * 1024 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=os.environ.get("MD_COOKIE_SECURE", "0") == "1",
        PERMANENT_SESSION_LIFETIME=8 * 60 * 60,
        AUTH_DISABLED=False,
        ANALYTICS_MIN_GROUP_SIZE=max(
            1, int(os.environ.get("MD_ANALYTICS_MIN_GROUP_SIZE", "5"))
        ),
        HR_MAILBOX_EMAIL=os.environ.get("MD_HR_MAILBOX_EMAIL", "hr@vd.zh.ch"),
        OUTLOOK_MAILBOX_NAME=os.environ.get("MD_OUTLOOK_MAILBOX", "VD-GS HR"),
        OUTLOOK_TARGET_FOLDER=os.environ.get(
            "MD_OUTLOOK_TARGET_FOLDER", "12 Mitarbeitenden-Dialog"
        ),
    )
    if test_config:
        app.config.update(test_config)

    if "DOSSIER_HANDOFF_ROOT" not in (test_config or {}):
        app.config["DOSSIER_HANDOFF_ROOT"] = os.environ.get(
            "MD_DOSSIER_HANDOFF_ROOT",
            str(Path(app.config["STORAGE_ROOT"]) / "dossier_ready"),
        )

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["STORAGE_ROOT"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["BACKUP_ROOT"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["DOSSIER_HANDOFF_ROOT"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    from .auth import bp as auth_bp, load_logged_in_user
    from .routes import bp

    app.before_request(load_logged_in_user)
    app.register_blueprint(auth_bp)
    app.register_blueprint(bp)

    @app.after_request
    def add_security_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; img-src 'self' data:; "
            "script-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        )
        return response

    return app
