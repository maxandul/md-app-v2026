"""Persönliche HR-Anmeldung und Benutzerverwaltung.

Die Umsetzung übernimmt die im ABW-Tool bewährten Grundsätze: starke Passwort-Hashes,
zeitkonstante Prüfung unbekannter Konten, temporäre Passwörter, Sitzungsentzug
über eine Versionsnummer und eine kleine IP-basierte Anmeldesperre.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db


bp = Blueprint("auth", __name__, url_prefix="/auth")
ROLE_HR_ADMIN = "hr_admin"
ROLE_SYSTEM_ADMIN = "system_admin"
_MAX_FAILURES = 10
_WINDOW_SECONDS = 300
_LOCK_SECONDS = 300
_attempts: dict[str, dict[str, float | int]] = {}
_attempt_lock = threading.Lock()
_dummy_hash = generate_password_hash(secrets.token_hex(16), method="scrypt")


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _client_key() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    return (forwarded.split(",", 1)[0].strip() if forwarded else request.remote_addr) or "unknown"


def _remaining_lock(key: str) -> int:
    now = time.time()
    with _attempt_lock:
        record = _attempts.get(key)
        if not record:
            return 0
        locked_until = float(record.get("locked_until", 0))
        if locked_until > now:
            return max(1, int(locked_until - now))
        if now - float(record.get("last", 0)) > _WINDOW_SECONDS:
            _attempts.pop(key, None)
        return 0


def _failed_login(key: str) -> None:
    now = time.time()
    with _attempt_lock:
        record = _attempts.get(key)
        if not record or now - float(record.get("last", 0)) > _WINDOW_SECONDS:
            record = {"failures": 0, "last": now, "locked_until": 0}
        record["failures"] = int(record["failures"]) + 1
        record["last"] = now
        if int(record["failures"]) >= _MAX_FAILURES:
            record["failures"] = 0
            record["locked_until"] = now + _LOCK_SECONDS
        _attempts[key] = record


def hash_password(password: str) -> str:
    return generate_password_hash(password, method="scrypt")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return check_password_hash(password_hash, password)
    except (TypeError, ValueError):
        return False


def audit(action: str, object_type: str = "", object_id: str = "", **details) -> None:
    connection = get_db()
    connection.execute(
        """
        INSERT INTO audit_log (user_id, action, object_type, object_id, details_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            g.user["id"] if getattr(g, "user", None) else None,
            action,
            object_type,
            object_id,
            json.dumps(details, ensure_ascii=False, sort_keys=True),
            _now(),
        ),
    )
    connection.commit()


def load_logged_in_user() -> None:
    g.user = None
    user_id = session.get("user_id")
    if user_id is None:
        return
    user = get_db().execute("SELECT * FROM app_users WHERE id = ?", (user_id,)).fetchone()
    if (
        not user
        or not user["active"]
        or int(session.get("session_version", 0)) != user["session_version"]
    ):
        session.clear()
        return
    g.user = user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_app.config.get("AUTH_DISABLED"):
            return view(*args, **kwargs)
        if g.user is None:
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapped


def system_admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_app.config.get("AUTH_DISABLED") and g.user["role"] != ROLE_SYSTEM_ADMIN:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@bp.route("/setup", methods=("GET", "POST"))
def setup():
    if get_db().execute("SELECT 1 FROM app_users LIMIT 1").fetchone():
        abort(404)
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")
        error = None
        if not email or "@" not in email:
            error = "Bitte eine gültige geschäftliche E-Mail-Adresse eingeben."
        elif len(password) < 12:
            error = "Das Passwort muss mindestens 12 Zeichen lang sein."
        elif password != confirmation:
            error = "Die beiden Passwörter stimmen nicht überein."
        if error:
            flash(error, "error")
        else:
            now = _now()
            cursor = get_db().execute(
                """
                INSERT INTO app_users
                    (email, password_hash, role, active, password_temporary, created_at, updated_at)
                VALUES (?, ?, ?, 1, 0, ?, ?)
                """,
                (email, hash_password(password), ROLE_SYSTEM_ADMIN, now, now),
            )
            get_db().commit()
            session.clear()
            session["user_id"] = cursor.lastrowid
            session["session_version"] = 1
            flash("Das erste Administrationskonto wurde erstellt.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("auth/setup.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if not get_db().execute("SELECT 1 FROM app_users LIMIT 1").fetchone():
        return redirect(url_for("auth.setup"))
    if request.method == "POST":
        key = _client_key()
        remaining = _remaining_lock(key)
        if remaining:
            flash(f"Zu viele Fehlversuche. Bitte in {remaining // 60 + 1} Minute(n) erneut versuchen.", "error")
            return render_template("auth/login.html"), 429
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM app_users WHERE email = ? COLLATE NOCASE", (email,)
        ).fetchone()
        valid = verify_password(password, user["password_hash"]) if user and user["active"] else check_password_hash(_dummy_hash, password)
        if not user or not user["active"] or not valid:
            _failed_login(key)
            flash("E-Mail-Adresse oder Passwort ist falsch.", "error")
        else:
            with _attempt_lock:
                _attempts.pop(key, None)
            session.clear()
            session["user_id"] = user["id"]
            session["session_version"] = user["session_version"]
            session.permanent = False
            audit("login", "app_user", str(user["id"]))
            next_url = request.args.get("next", "")
            return redirect(next_url if next_url.startswith("/") and not next_url.startswith("//") else url_for("main.dashboard"))
    return render_template("auth/login.html")


@bp.post("/logout")
def logout():
    if g.user:
        audit("logout", "app_user", str(g.user["id"]))
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/password-change", methods=("GET", "POST"))
@login_required
def change_password():
    if request.method == "POST":
        password = request.form.get("password", "")
        confirmation = request.form.get("confirmation", "")
        if len(password) < 12:
            flash("Das neue Passwort muss mindestens 12 Zeichen lang sein.", "error")
        elif password != confirmation:
            flash("Die beiden Passwörter stimmen nicht überein.", "error")
        else:
            get_db().execute(
                """UPDATE app_users SET password_hash = ?, password_temporary = 0,
                   updated_at = ? WHERE id = ?""",
                (hash_password(password), _now(), g.user["id"]),
            )
            get_db().commit()
            audit("password_changed", "app_user", str(g.user["id"]))
            flash("Das Passwort wurde geändert.", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("auth/password_change.html")


@bp.route("/users", methods=("GET", "POST"))
@system_admin_required
def users():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        role = request.form.get("role", ROLE_HR_ADMIN)
        password = request.form.get("temporary_password", "")
        if not email or "@" not in email or role not in {ROLE_HR_ADMIN, ROLE_SYSTEM_ADMIN}:
            flash("E-Mail-Adresse oder Rolle ist ungültig.", "error")
        elif len(password) < 12:
            flash("Das temporäre Passwort muss mindestens 12 Zeichen lang sein.", "error")
        else:
            now = _now()
            try:
                cursor = get_db().execute(
                    """
                    INSERT INTO app_users
                        (email, password_hash, role, active, password_temporary, created_at, updated_at)
                    VALUES (?, ?, ?, 1, 1, ?, ?)
                    """,
                    (email, hash_password(password), role, now, now),
                )
                get_db().commit()
                audit("user_created", "app_user", str(cursor.lastrowid), email=email, role=role)
                flash("Benutzerkonto wurde angelegt.", "success")
            except Exception:
                get_db().rollback()
                flash("Für diese E-Mail-Adresse besteht bereits ein Konto.", "error")
    rows = get_db().execute(
        "SELECT id, email, role, active, password_temporary, created_at FROM app_users ORDER BY email"
    ).fetchall()
    return render_template("auth/users.html", users=rows, active_nav="administration")


@bp.post("/users/<int:user_id>/reset")
@system_admin_required
def reset_password(user_id: int):
    password = request.form.get("temporary_password", "")
    if len(password) < 12:
        flash("Das temporäre Passwort muss mindestens 12 Zeichen lang sein.", "error")
    else:
        result = get_db().execute(
            """
            UPDATE app_users
            SET password_hash = ?, password_temporary = 1,
                session_version = session_version + 1, updated_at = ?
            WHERE id = ?
            """,
            (hash_password(password), _now(), user_id),
        )
        get_db().commit()
        if not result.rowcount:
            abort(404)
        audit("password_reset", "app_user", str(user_id))
        flash("Passwort wurde zurückgesetzt; bestehende Sitzungen sind beendet.", "success")
    return redirect(url_for("auth.users"))
