"""
Sends EPUB files to a Kindle email address via Resend API.
Falls back to plain SMTP if RESEND_API_KEY is not set.
"""

import logging
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

logger = logging.getLogger(__name__)

# The "from" address users must whitelist in their Amazon account
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "kindle@example.com")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

# SMTP fallback settings
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")


def send_to_kindle(
    kindle_email: str,
    epub_bytes: bytes,
    filename: str,
) -> None:
    """
    Send an EPUB file to a Kindle email address.
    Raises an exception if sending fails.
    """
    logger.info(f"Sending '{filename}' to {kindle_email}")

    if RESEND_API_KEY:
        _send_via_resend(kindle_email, epub_bytes, filename)
    elif SMTP_USER and SMTP_PASS:
        _send_via_smtp(kindle_email, epub_bytes, filename)
    else:
        raise RuntimeError(
            "No email sender configured. "
            "Please set RESEND_API_KEY or SMTP_USER/SMTP_PASS environment variables."
        )


def _send_via_resend(kindle_email: str, epub_bytes: bytes, filename: str) -> None:
    import base64

    encoded = base64.b64encode(epub_bytes).decode("utf-8")

    payload = {
        "from": SENDER_EMAIL,
        "to": [kindle_email],
        "subject": filename.replace(".epub", ""),
        "text": "请在您的 Kindle 设备上查看推送的文章。\n\nSent by WechatToKindle.",
        "attachments": [
            {
                "filename": filename,
                "content": encoded,
            }
        ],
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Resend API error {resp.status_code}: {resp.text}")

    logger.info("Email sent via Resend")


def _send_via_smtp(kindle_email: str, epub_bytes: bytes, filename: str) -> None:
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL or SMTP_USER
    msg["To"] = kindle_email
    msg["Subject"] = filename.replace(".epub", "")

    msg.attach(MIMEText(
        "请在您的 Kindle 设备上查看推送的文章。\n\nSent by WechatToKindle.",
        "plain",
        "utf-8",
    ))

    attachment = MIMEBase("application", "epub+zip")
    attachment.set_payload(epub_bytes)
    encoders.encode_base64(attachment)
    attachment.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(attachment)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(msg["From"], [kindle_email], msg.as_string())

    logger.info("Email sent via SMTP")
