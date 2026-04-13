"""
Sends EPUB files to a Kindle email address via Resend API.
"""

import base64
import logging
import os

import httpx

logger = logging.getLogger(__name__)

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "kindle@wx2kindle.xyz")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")


def send_to_kindle(kindle_email: str, epub_bytes: bytes, filename: str) -> None:
    if not RESEND_API_KEY:
        raise RuntimeError("未配置 RESEND_API_KEY 环境变量")

    encoded = base64.b64encode(epub_bytes).decode("utf-8")

    payload = {
        "from": f"微信推Kindle <{SENDER_EMAIL}>",
        "to": [kindle_email],
        "subject": filename.replace(".epub", ""),
        "text": "请在您的 Kindle 设备上查看推送的文章。\n\nSent by WechatToKindle.",
        "attachments": [{"filename": filename, "content": encoded}],
    }

    with httpx.Client(timeout=60) as client:
        resp = client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Resend API 错误 {resp.status_code}: {resp.text}")

    logger.info(f"Email sent via Resend to {kindle_email}")
