"""
Sends EPUB files to a Kindle email address via Brevo (formerly Sendinblue) API.
Uses HTTPS so it works on Render free tier (SMTP port 587 is blocked there).
"""

import base64
import logging
import os

import httpx

logger = logging.getLogger(__name__)

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "kindle@example.com")
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")


def send_to_kindle(kindle_email: str, epub_bytes: bytes, filename: str) -> None:
    if not BREVO_API_KEY:
        raise RuntimeError(
            "未配置 BREVO_API_KEY，请在 Render 环境变量中添加。"
        )
    _send_via_brevo(kindle_email, epub_bytes, filename)


def _send_via_brevo(kindle_email: str, epub_bytes: bytes, filename: str) -> None:
    encoded = base64.b64encode(epub_bytes).decode("utf-8")

    payload = {
        "sender": {"email": SENDER_EMAIL, "name": "微信推Kindle"},
        "to": [{"email": kindle_email}],
        "subject": filename.replace(".epub", ""),
        "textContent": "请在您的 Kindle 设备上查看推送的文章。\n\nSent by WechatToKindle.",
        "attachment": [{"content": encoded, "name": filename}],
    }

    with httpx.Client(timeout=60) as client:
        resp = client.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": BREVO_API_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Brevo API 错误 {resp.status_code}: {resp.text}")

    logger.info(f"Email sent via Brevo to {kindle_email}")
