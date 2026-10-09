"""Lokale Organisationskonfiguration; öffentliche Defaults enthalten keine internen Adressen."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlsplit


DEFAULTS = {
    'HR_MAILBOX_EMAIL':'',
    'OUTLOOK_MAILBOX_NAME':'',
    'OUTLOOK_TARGET_FOLDER':'Mitarbeitenden-Dialog',
    'DOSSIER_HANDOFF_ROOT':'',
    'SPECIAL_CASES_URL':'',
}
ENVIRONMENT = {
    'HR_MAILBOX_EMAIL':'MD_HR_MAILBOX_EMAIL',
    'OUTLOOK_MAILBOX_NAME':'MD_OUTLOOK_MAILBOX',
    'OUTLOOK_TARGET_FOLDER':'MD_OUTLOOK_TARGET_FOLDER',
    'DOSSIER_HANDOFF_ROOT':'MD_DOSSIER_HANDOFF_ROOT',
    'SPECIAL_CASES_URL':'MD_SPECIAL_CASES_URL',
}


def validate_organisation(values):
    for key in DEFAULTS:
        if not isinstance(values.get(key,''),str):
            raise ValueError(f'Organisationskonfiguration: {key} muss Text enthalten.')
    email = values.get('HR_MAILBOX_EMAIL','')
    if email and ('@' not in email or any(ch.isspace() for ch in email) or any(ch in email for ch in '<>"')):
        raise ValueError('Organisationskonfiguration: ungültige HR-Absenderadresse.')
    url = values.get('SPECIAL_CASES_URL','')
    if url:
        parsed = urlsplit(url)
        if parsed.scheme not in ('https','http') or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError('Spezialfälle-Link: eine vollständige HTTP(S)-Adresse ohne Zugangsdaten verwenden.')


def load_organisation(path=None):
    path = Path(path or os.environ.get('MD_ORG_CONFIG') or Path(__file__).resolve().parents[1]/'instance'/'organisation.json')
    values = dict(DEFAULTS)
    if path.exists():
        try:
            configured = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(configured,dict) or set(configured)-set(DEFAULTS):
                raise ValueError('Unbekannter Konfigurationsschlüssel')
            values.update(configured)
        except (OSError,ValueError,TypeError) as exc:
            raise ValueError('Die lokale Organisationskonfiguration ist nicht lesbar oder enthält unbekannte Schlüssel.') from exc
        if values['DOSSIER_HANDOFF_ROOT'] and not Path(values['DOSSIER_HANDOFF_ROOT']).is_absolute():
            # Windows-Laufwerk-/UNC-Pfade auch beim Prüfen auf Linux nicht umdeuten.
            value = values['DOSSIER_HANDOFF_ROOT']
            if not (len(value)>2 and value[1]==':') and not value.startswith('\\\\'):
                values['DOSSIER_HANDOFF_ROOT'] = str(path.parent/value)
    for key,variable in ENVIRONMENT.items():
        if variable in os.environ:
            values[key] = os.environ[variable]
    if 'MD_ROBOT_INPUT_ROOT' in os.environ:
        values['DOSSIER_HANDOFF_ROOT'] = os.environ['MD_ROBOT_INPUT_ROOT']
    validate_organisation(values)
    return values


def workbook_configuration():
    # Auch der eigenständige HTML-Generator verwendet dieselbe lokale Datei.
    from flask import current_app, has_app_context
    settings = current_app.config if has_app_context() else load_organisation()
    return {'hr_email':settings.get('HR_MAILBOX_EMAIL',''), 'special_cases_url':settings.get('SPECIAL_CASES_URL','')}
