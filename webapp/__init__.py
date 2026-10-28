"""Flask-Anwendung für die administrative MD-Verarbeitung."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Flask, request, session

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


def create_app(test_config: dict | None = None, *, instance_path: str | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True, instance_path=instance_path)
    app.config.from_mapping(
        SECRET_KEY=test_config['SECRET_KEY'] if test_config and 'SECRET_KEY' in test_config else _secret_key(app.instance_path),
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
        HR_GOAL_WORKFLOW=os.environ.get("MD_HR_GOAL_WORKFLOW", "0") == "1",
        ANALYTICS_MIN_GROUP_SIZE=max(
            1, int(os.environ.get("MD_ANALYTICS_MIN_GROUP_SIZE", "5"))
        ),
    )
    from .organisation import load_organisation, validate_organisation
    app.config.update(load_organisation())
    if test_config:
        app.config.update(test_config)

    if "WORD_TEMPLATE_PATHS" not in app.config:
        from .services.word_packages import load_word_config
        config_path = Path(os.environ.get("MD_WORD_CONFIG", str(Path(app.instance_path) / "word_config.json")))
        app.config["WORD_TEMPLATE_PATHS"] = load_word_config(config_path)

    validate_organisation(app.config)
    if not app.config.get("DOSSIER_HANDOFF_ROOT"):
        app.config["DOSSIER_HANDOFF_ROOT"] = str(Path(app.config["STORAGE_ROOT"]) / "dossier_ready")

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
    from .goal_routes import bp as goal_bp
    app.register_blueprint(goal_bp)
    from .part_routes import bp as part_bp
    app.register_blueprint(part_bp)
    from .sap_routes import bp as sap_bp
    app.register_blueprint(sap_bp)
    from .return_routes import bp as return_bp
    app.register_blueprint(return_bp)
    from .hr_routes import bp as hr_bp
    app.register_blueprint(hr_bp)

    @app.after_request
    def retain_action_filters(response):
        if request.method == 'POST' and response.status_code in (302,303) and request.referrer:
            from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
            source=urlsplit(request.referrer); target=urlsplit(response.headers.get('Location',''))
            if source.netloc == request.host and (not target.netloc or target.netloc==request.host) and source.path==target.path:
                params=dict(parse_qsl(target.query,keep_blank_values=True))
                allowed={'cycle_id','org_unit','event_type','status','q','kind','mail_q','mail_status','mail_page','pdf_q','pdf_status','pdf_page','page','workflow','unassigned'}
                for key,value in parse_qsl(source.query,keep_blank_values=True):
                    if key in allowed and key not in params:params[key]=value
                response.headers['Location']=urlunsplit((target.scheme,target.netloc,target.path,urlencode(params),target.fragment))
        return response

    @app.after_request
    def add_security_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; img-src 'self' data:; "
            "script-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
        )
        if request.endpoint == 'goal_work.original':
            response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            response.headers['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'self'"
        return response

    @app.context_processor
    def workflow_visibility():
        if app.config.get('HR_GOAL_WORKFLOW'):
            session.setdefault('goal_csrf',secrets.token_urlsafe(32))
        return {'legacy_workbooks_enabled': app.config.get('LEGACY_WORKBOOKS') == 'enabled',
                'goal_csrf_token':session.get('goal_csrf',''),
                'return_review_enabled':bool(app.config.get('HR_GOAL_WORKFLOW'))}

    from .services.mail_schedule import start_worker
    start_worker(app)

    return app
