"""Gekapselte Outlook-COM-Anbindung für S/MIME-Versand und Postfacheingang."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory


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


@dataclass(frozen=True)
class InboundAttachment:
    index: int
    filename: str
    content: bytes


@dataclass(frozen=True)
class InboundMessage:
    entry_id: str
    internet_message_id: str
    sender_email: str
    subject: str
    received_at: datetime
    attachments: tuple[InboundAttachment, ...]


def _sender_email(mail) -> str:
    try:
        sender = getattr(mail, "Sender", None)
        if sender and getattr(sender, "AddressEntryUserType", None) == 0:
            exchange_user = sender.GetExchangeUser()
            address = getattr(exchange_user, "PrimarySmtpAddress", "")
            if address:
                return str(address)
    except Exception:
        pass
    try:
        address = mail.PropertyAccessor.GetProperty(
            "http://schemas.microsoft.com/mapi/proptag/0x39FE001E"
        )
        if address:
            return str(address)
    except Exception:
        pass
    return str(
        getattr(mail, "SenderEmailAddress", "")
        or getattr(mail, "SenderName", "")
        or "Unbekannt"
    )


def _normalise_mailbox_name(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def _resolve_inbox(namespace, mailbox_name: str):
    """Findet ein Postfach über Root- oder Store-Anzeigename und liefert Inbox."""
    requested = _normalise_mailbox_name(mailbox_name)
    if not requested:
        raise OutlookUnavailableError("Der konfigurierte Outlook-Postfachname ist leer.")

    try:
        root = namespace.Folders.Item(mailbox_name)
        return root.Store.GetDefaultFolder(6)
    except Exception:
        pass

    available: list[str] = []
    for index in range(1, int(namespace.Folders.Count) + 1):
        try:
            root = namespace.Folders.Item(index)
            root_name = str(getattr(root, "Name", "") or "").strip()
            store = getattr(root, "Store", None)
            store_name = str(getattr(store, "DisplayName", "") or "").strip()
            labels = [label for label in (root_name, store_name) if label]
            available.extend(labels)
            normalised = [_normalise_mailbox_name(label) for label in labels]
            if requested in normalised or any(
                requested in label or label in requested for label in normalised
            ):
                return store.GetDefaultFolder(6)
        except Exception:
            continue

    names = ", ".join(dict.fromkeys(available)) or "keine lesbaren Postfächer"
    raise OutlookUnavailableError(
        f"Das konfigurierte Outlook-Postfach «{mailbox_name}» wurde nicht gefunden. "
        f"Verfügbar: {names}. Bei Bedarf MD_OUTLOOK_MAILBOX anpassen."
    )


class OutlookDraftAdapter:
    """Erzeugt oder versendet S/MIME-markierte Outlook-Nachrichten."""

    def create_encrypted_draft(
        self,
        *,
        sender_email: str,
        recipient_email: str,
        subject: str,
        body_html: str,
        attachments: list[Path],
    ) -> DraftResult:
        return self._create_encrypted_message(
            sender_email=sender_email,
            recipient_email=recipient_email,
            subject=subject,
            body_html=body_html,
            attachments=attachments,
            send_now=False,
        )

    def send_encrypted(
        self,
        *,
        sender_email: str,
        recipient_email: str,
        subject: str,
        body_html: str,
        attachments: list[Path],
    ) -> DraftResult:
        return self._create_encrypted_message(
            sender_email=sender_email,
            recipient_email=recipient_email,
            subject=subject,
            body_html=body_html,
            attachments=attachments,
            send_now=True,
        )

    def _create_encrypted_message(
        self,
        *,
        sender_email: str,
        recipient_email: str,
        subject: str,
        body_html: str,
        attachments: list[Path],
        send_now: bool,
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
            entry_id = str(getattr(mail, "EntryID", "") or "")
            if send_now:
                mail.Send()
            return DraftResult(entry_id=entry_id, encryption_flag_verified=True)
        except (EncryptionVerificationError, FileNotFoundError):
            raise
        except Exception as exc:
            if mail is not None:
                try:
                    mail.Delete()
                except Exception:
                    pass
            action = "versendet" if send_now else "als Entwurf erstellt"
            raise OutlookUnavailableError(
                f"Die verschlüsselte Outlook-Nachricht konnte nicht {action} werden: {exc}"
            ) from exc
        finally:
            pythoncom.CoUninitialize()

class OutlookInboxAdapter:
    """Liest Nachrichten/Anhänge und verschiebt abschliessend verarbeitete Mails."""

    def read_messages(
        self, *, mailbox_name: str, limit: int = 1000
    ) -> list[InboundMessage]:
        try:
            import pythoncom
            import win32com.client as win32
        except ImportError as exc:
            raise OutlookUnavailableError(
                "Die Outlook-Integration benötigt Windows, klassisches Outlook und pywin32."
            ) from exc

        pythoncom.CoInitialize()
        try:
            namespace = win32.Dispatch("Outlook.Application").GetNamespace("MAPI")
            inbox = _resolve_inbox(namespace, mailbox_name)
            items = inbox.Items
            items.Sort("[ReceivedTime]", True)
            messages: list[InboundMessage] = []
            for position in range(1, min(int(items.Count), limit) + 1):
                mail = items.Item(position)
                if int(getattr(mail, "Class", 0) or 0) != 43:
                    continue
                attachments: list[InboundAttachment] = []
                with TemporaryDirectory(prefix="md-mail-") as temporary:
                    temporary_dir = Path(temporary)
                    for index in range(1, int(mail.Attachments.Count) + 1):
                        attachment = mail.Attachments.Item(index)
                        filename = str(getattr(attachment, "FileName", "") or "").strip()
                        if not filename:
                            filename = f"Anhang-{index}"
                        temporary_path = temporary_dir / f"attachment-{index}"
                        attachment.SaveAsFile(str(temporary_path))
                        attachments.append(
                            InboundAttachment(index, filename, temporary_path.read_bytes())
                        )
                try:
                    internet_message_id = str(
                        mail.PropertyAccessor.GetProperty(
                            "http://schemas.microsoft.com/mapi/proptag/0x1035001E"
                        )
                        or ""
                    )
                except Exception:
                    internet_message_id = ""
                received_at = getattr(mail, "ReceivedTime", None)
                if not isinstance(received_at, datetime):
                    received_at = datetime.now().astimezone()
                messages.append(
                    InboundMessage(
                        entry_id=str(getattr(mail, "EntryID", "") or ""),
                        internet_message_id=internet_message_id,
                        sender_email=_sender_email(mail),
                        subject=str(getattr(mail, "Subject", "") or ""),
                        received_at=received_at,
                        attachments=tuple(attachments),
                    )
                )
            return messages
        except Exception as exc:
            raise OutlookUnavailableError(
                f"Das Outlook-Postfach konnte nicht gelesen werden: {exc}"
            ) from exc
        finally:
            pythoncom.CoUninitialize()

    def move_message(
        self, *, mailbox_name: str, entry_id: str, target_folder: str
    ) -> str:
        try:
            import pythoncom
            import win32com.client as win32
        except ImportError as exc:
            raise OutlookUnavailableError(
                "Die Outlook-Integration benötigt Windows, klassisches Outlook und pywin32."
            ) from exc

        pythoncom.CoInitialize()
        try:
            namespace = win32.Dispatch("Outlook.Application").GetNamespace("MAPI")
            inbox = _resolve_inbox(namespace, mailbox_name)
            try:
                destination = inbox.Folders.Item(target_folder)
            except Exception:
                destination = inbox.Parent.Folders.Item(target_folder)
            store_id = str(getattr(inbox.Store, "StoreID", "") or "")
            message = namespace.GetItemFromID(entry_id, store_id)
            moved = message.Move(destination)
            return str(getattr(moved, "EntryID", "") or entry_id)
        except Exception as exc:
            raise OutlookUnavailableError(
                f"Die Outlook-Nachricht konnte nicht nach «{target_folder}» verschoben werden: {exc}"
            ) from exc
        finally:
            pythoncom.CoUninitialize()
