"""Outbound sending through Postfix submission (587, STARTTLS, SASL)."""
import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from django.conf import settings


def build_message(
    from_addr: str,
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    attachments: list[tuple[str, bytes, str]] | None = None,  # (filename, data, mime)
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=from_addr.split("@", 1)[1])
    msg.set_content(body)
    for filename, data, mime in attachments or []:
        maintype, _, subtype = mime.partition("/")
        msg.add_attachment(
            data, maintype=maintype or "application",
            subtype=subtype or "octet-stream", filename=filename,
        )
    return msg


def send(msg: EmailMessage) -> None:
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_SUBMISSION_PORT, timeout=30) as s:
        s.starttls()
        s.login(settings.SUBMISSION_USER, settings.SUBMISSION_PASSWORD)
        s.send_message(msg)
