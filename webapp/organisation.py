"""Lokale Organisationskonfiguration; öffentliche Defaults enthalten keine internen Adressen."""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlsplit


DEFAULTS = {
    'PUBLIC_BASE_URL':'',
    'HR_MAILBOX_EMAIL':'',
    'OUTLOOK_MAILBOX_NAME':'',
    'OUTLOOK_TARGET_FOLDER':'Mitarbeitenden-Dialog',
    'DOSSIER_HANDOFF_ROOT':'',
    'SPECIAL_CASES_URL':'',
}
ENVIRONMENT = {
    'PUBLIC_BASE_URL':'MD_PUBLIC_BASE_URL',
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
    public_url = values.get('PUBLIC_BASE_URL','')
    if public_url:
        parsed = urlsplit(public_url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or any(c.isspace() for c in public_url):
            raise ValueError('PUBLIC_BASE_URL: vollständige HTTP(S)-Adresse ohne Zugangsdaten, Abfrage oder Fragment verwenden.')
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError('PUBLIC_BASE_URL: ungültiger Port.') from exc
    email = values.get('HR_MAILBOX_EMAIL','')
    if email and ('@' not in email or any(ch.isspace() for ch in email) or any(ch in email for ch in '<>"')):
        raise ValueError('Organisationskonfiguration: ungültige HR-Absenderadresse.')
    url = values.get('SPECIAL_CASES_URL','')
    if url:
        parsed = urlsplit(url)
        if parsed.scheme not in ('https','http') or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError('Spezialfälle-Link: eine vollständige HTTP(S)-Adresse ohne Zugangsdaten verwenden.')


def load_organisation(path=None):
    explicit = path or os.environ.get('MD_ORG_CONFIG')
    path = Path(explicit or Path(__file__).resolve().parents[1]/'instance'/'organisation.json').expanduser().resolve()
    aliases = ('organisation_config.json', 'organisatio_config.json')
    notice = ''
    if not explicit:
        found = [candidate for candidate in [path, *(path.parent/name for name in aliases)] if candidate.is_file()]
        if len(found) > 1:
            raise ValueError('Mehrere Organisationskonfigurationen gefunden: '+', '.join(str(p) for p in found)+'. Bitte nur die gewünschte Datei als organisation.json behalten; die übrigen umbenennen oder MD_ORG_CONFIG ausdrücklich setzen.')
        if found:
            path = found[0]
            if path.name != 'organisation.json':
                notice = f'Die Datei {path.name} wird gelesen. Empfohlener Name: organisation.json. Nach Umbenennung Server neu starten.'
    values = dict(DEFAULTS)
    if path.exists():
        try:
            configured = json.loads(path.read_text(encoding='utf-8-sig'))
            if isinstance(configured,dict) and configured.get('LEGACY_WORKBOOKS') in ('enabled','disabled'):
                configured.pop('LEGACY_WORKBOOKS')
                notice = 'Die frühere Arbeitsmappen-Einstellung entfällt. Die App verwendet ausschliesslich den Word-/PDF-Ablauf.'
            if not isinstance(configured,dict) or set(configured)-set(DEFAULTS):
                raise ValueError('Unbekannter Konfigurationsschlüssel')
            values.update(configured)
        except (OSError,ValueError,TypeError) as exc:
            raise ValueError(f'Die Organisationskonfiguration {path} ist nicht lesbar oder enthält unbekannte Schlüssel. Gültiges JSON ohne zusätzliche Backslashes verwenden.') from exc
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
    values['_ORG_CONFIG_PATH'] = str(path)
    values['_ORG_CONFIG_LOADED'] = path.is_file()
    values['_ORG_CONFIG_NOTICE'] = notice
    values['_ORG_ENV_OVERRIDES'] = [name for name in [*ENVIRONMENT.values(), 'MD_ROBOT_INPUT_ROOT'] if name in os.environ]
    return values


def local_configuration():
    from flask import current_app, has_app_context
    settings = current_app.config if has_app_context() else load_organisation()
    return {'hr_email':settings.get('HR_MAILBOX_EMAIL',''), 'special_cases_url':settings.get('SPECIAL_CASES_URL','')}
