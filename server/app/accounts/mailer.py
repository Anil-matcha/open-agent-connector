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
    return settings.ACCOUNTS_EMAIL_BACKEND in ("console", "smtp", "ses")


def _from_address() -> str:
    return settings.ACCOUNTS_EMAIL_FROM or settings.ACCOUNTS_SMTP_FROM or settings.ACCOUNTS_SMTP_USER


def _send_smtp(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = _from_address()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(settings.ACCOUNTS_SMTP_HOST, settings.ACCOUNTS_SMTP_PORT, timeout=15) as smtp:
        if settings.ACCOUNTS_SMTP_STARTTLS:
            smtp.starttls()
        if settings.ACCOUNTS_SMTP_USER:
            smtp.login(settings.ACCOUNTS_SMTP_USER, settings.ACCOUNTS_SMTP_PASSWORD)
        smtp.send_message(msg)


def _send_ses(to: str, subject: str, body: str) -> None:
    import boto3  # imported lazily so installs that never use SES do not need it

    kwargs = {"region_name": settings.ACCOUNTS_SES_REGION}
    if settings.ACCOUNTS_SES_ACCESS_KEY and settings.ACCOUNTS_SES_SECRET_KEY:
        kwargs["aws_access_key_id"] = settings.ACCOUNTS_SES_ACCESS_KEY
        kwargs["aws_secret_access_key"] = settings.ACCOUNTS_SES_SECRET_KEY
    source = _from_address()
    if not source:
        raise RuntimeError("ACCOUNTS_EMAIL_FROM is not set")
    boto3.client("ses", **kwargs).send_email(
        Source=source,
        Destination={"ToAddresses": [to]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
        },
    )


async def send_email(to: str, subject: str, body: str) -> None:
    backend = settings.ACCOUNTS_EMAIL_BACKEND
    if backend == "console":
        # Development only: this writes one-time codes to the server log.
        logger.warning("[email to %s] %s\n%s", to, subject, body)
        OUTBOX.append((to, subject, body))
        del OUTBOX[:-200]
        return
    if backend in ("smtp", "ses"):
        sender = _send_smtp if backend == "smtp" else _send_ses
        try:
            await asyncio.to_thread(sender, to, subject, body)
        except Exception:  # never let a mail outage break or leak through the request
            logger.exception("Failed to send email to %s", to)
        return
    raise EmailUnavailable("No email backend configured.")
