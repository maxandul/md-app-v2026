"""Flask-Anwendung für die administrative MD-Verarbeitung."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask

from . import db


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("MD_SECRET_KEY", "nur-lokal-ersetzen"),
        DATABASE=str(Path(app.instance_path) / "md.sqlite3"),
        STORAGE_ROOT=str(Path(app.instance_path) / "data"),
        MAX_CONTENT_LENGTH=25 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
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
    Path(app.config["DOSSIER_HANDOFF_ROOT"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    from .routes import bp

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
