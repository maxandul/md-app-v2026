"""Gemeinsame Absenderprüfung für den Word- und Erinnerungsversand."""
DEFAULT_SENDER = ""


def configured_sender(value=""):
    if not value:
        from webapp.organisation import local_configuration
        value = local_configuration()['hr_email']
    if not value or '@' not in value or any(ch.isspace() for ch in value):
        raise ValueError("Bitte die HR-Absenderadresse lokal konfigurieren.")
    return value
