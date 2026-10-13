import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import List, Tuple

from app.core.config import settings

logger = logging.getLogger("connector.accounts.mail")

# Messages "sent" by the console backend, newest last (bounded). Used by tests.
OUTBOX: List[Tuple[str, str, str]] = []


class EmailUnavailable(Exception):
    pass


def email_enabled() -> bool:
    return settings.ACCOUNTS_EMAIL_BACKEND in ("console", "smtp")


def _send_smtp(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.ACCOUNTS_SMTP_FROM or settings.ACCOUNTS_SMTP_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(settings.ACCOUNTS_SMTP_HOST, settings.ACCOUNTS_SMTP_PORT, timeout=15) as smtp:
        if settings.ACCOUNTS_SMTP_STARTTLS:
            smtp.starttls()
        if settings.ACCOUNTS_SMTP_USER:
            smtp.login(settings.ACCOUNTS_SMTP_USER, settings.ACCOUNTS_SMTP_PASSWORD)
        smtp.send_message(msg)


async def send_email(to: str, subject: str, body: str) -> None:
    backend = settings.ACCOUNTS_EMAIL_BACKEND
    if backend == "console":
        # Development only: this writes one-time codes to the server log.
        logger.warning("[email to %s] %s\n%s", to, subject, body)
        OUTBOX.append((to, subject, body))
        del OUTBOX[:-200]
        return
    if backend == "smtp":
        try:
            await asyncio.to_thread(_send_smtp, to, subject, body)
        except Exception:  # never let a mail outage break or leak through the request
            logger.exception("Failed to send email to %s", to)
        return
    raise EmailUnavailable("No email backend configured.")
