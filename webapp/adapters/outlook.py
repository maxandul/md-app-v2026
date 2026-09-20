"""Gekapselte Outlook-COM-Anbindung für verschlüsselte Entwürfe."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PR_SECURITY_FLAGS = "http://schemas.microsoft.com/mapi/proptag/0x6E010003"
SECFLAG_ENCRYPTED = 0x1


class OutlookUnavailableError(RuntimeError):
    """Outlook beziehungsweise pywin32 steht nicht zur Verfügung."""


class EncryptionVerificationError(RuntimeError):
    """Der Entwurf weist nach dem Speichern kein Verschlüsselungsflag auf."""


@dataclass(frozen=True)
class DraftResult:
    entry_id: str
    encryption_flag_verified: bool


class OutlookDraftAdapter:
    """Erzeugt Entwürfe; ein automatischer Versand ist absichtlich nicht möglich."""

    def create_encrypted_draft(
        self,
        *,
        sender_email: str,
        recipient_email: str,
        subject: str,
        body_html: str,
        attachments: list[Path],
    ) -> DraftResult:
        try:
            import pythoncom
            import win32com.client as win32
        except ImportError as exc:
            raise OutlookUnavailableError(
                "Die Outlook-Integration benötigt Windows, klassisches Outlook und pywin32."
            ) from exc

        missing = [str(path) for path in attachments if not path.is_file()]
        if missing:
            raise FileNotFoundError("Anhang nicht gefunden: " + ", ".join(missing))

        pythoncom.CoInitialize()
        mail = None
        try:
            outlook = win32.Dispatch("Outlook.Application")
            mail = outlook.CreateItem(0)
            mail.SentOnBehalfOfName = sender_email
            mail.To = recipient_email
            mail.Subject = subject
            mail.HTMLBody = body_html
            for attachment in attachments:
                mail.Attachments.Add(str(attachment.resolve()))
            mail.PropertyAccessor.SetProperty(PR_SECURITY_FLAGS, SECFLAG_ENCRYPTED)
            mail.Save()
            security_flags = int(
                mail.PropertyAccessor.GetProperty(PR_SECURITY_FLAGS) or 0
            )
            verified = bool(security_flags & SECFLAG_ENCRYPTED)
            if not verified:
                try:
                    mail.Delete()
                except Exception:
                    pass
                raise EncryptionVerificationError(
                    "Outlook hat den Entwurf nicht als S/MIME-verschlüsselt gespeichert."
                )
            return DraftResult(
                entry_id=str(getattr(mail, "EntryID", "") or ""),
                encryption_flag_verified=True,
            )
        except (EncryptionVerificationError, FileNotFoundError):
            raise
        except Exception as exc:
            if mail is not None:
                try:
                    mail.Delete()
                except Exception:
                    pass
            raise OutlookUnavailableError(
                "Der verschlüsselte Outlook-Entwurf konnte nicht erstellt werden: "
                f"{exc}"
            ) from exc
        finally:
            pythoncom.CoUninitialize()

    def send(self, *_args, **_kwargs) -> None:
        raise EncryptionVerificationError(
            "Der automatische Versand ist bis zum S/MIME-Integrationstest gesperrt."
        )
