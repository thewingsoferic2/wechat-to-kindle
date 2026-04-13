"""
Sends EPUB files to a Kindle email address via Gmail SMTP.
"""

import logging
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")


def send_to_kindle(kindle_email: str, epub_bytes: bytes, filename: str) -> None:
    if not SMTP_USER or not SMTP_PASS:
        raise RuntimeError("未配置 SMTP_USER / SMTP_PASS 环境变量")

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL or SMTP_USER
    msg["To"] = kindle_email
    msg["Subject"] = filename.replace(".epub", "")
    msg.attach(MIMEText(
        "请在您的 Kindle 设备上查看推送的文章。\n\nSent by WechatToKindle.",
        "plain", "utf-8",
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

    logger.info(f"Email sent via Gmail SMTP to {kindle_email}")
