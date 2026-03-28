"""
Sends EPUB files to a Kindle email address via Mailjet API.
Uses HTTPS so it works on Render free tier (SMTP port 587 is blocked there).
"""

import base64
import logging
import os

import httpx

logger = logging.getLogger(__name__)

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "kindle@example.com")
MAILJET_API_KEY = os.environ.get("MAILJET_API_KEY", "")
MAILJET_SECRET_KEY = os.environ.get("MAILJET_SECRET_KEY", "")


def send_to_kindle(kindle_email: str, epub_bytes: bytes, filename: str) -> None:
    if not MAILJET_API_KEY or not MAILJET_SECRET_KEY:
        raise RuntimeError("未配置 MAILJET_API_KEY / MAILJET_SECRET_KEY")
    _send_via_mailjet(kindle_email, epub_bytes, filename)


def _send_via_mailjet(kindle_email: str, epub_bytes: bytes, filename: str) -> None:
    encoded = base64.b64encode(epub_bytes).decode("utf-8")

    payload = {
        "Messages": [
            {
                "From": {"Email": SENDER_EMAIL, "Name": "微信推Kindle"},
                "To": [{"Email": kindle_email}],
                "Subject": filename.replace(".epub", ""),
                "TextPart": "请在您的 Kindle 设备上查看推送的文章。\n\nSent by WechatToKindle.",
                "Attachments": [
                    {
                        "ContentType": "application/epub+zip",
                        "Filename": filename,
                        "Base64Content": encoded,
                    }
                ],
            }
        ]
    }

    with httpx.Client(timeout=60) as client:
        resp = client.post(
            "https://api.mailjet.com/v3.1/send",
            auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY),
            json=payload,
        )

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Mailjet API 错误 {resp.status_code}: {resp.text}")

    logger.info(f"Email sent via Mailjet to {kindle_email}")
