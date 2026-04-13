"""
Sends EPUB files to a Kindle email address via Elastic Email API.
Uses HTTPS so it works on Render free tier.
"""

import base64
import logging
import os

import httpx

logger = logging.getLogger(__name__)

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "")
ELASTIC_API_KEY = os.environ.get("ELASTIC_API_KEY", "")


def send_to_kindle(kindle_email: str, epub_bytes: bytes, filename: str) -> None:
    if not ELASTIC_API_KEY:
        raise RuntimeError("未配置 ELASTIC_API_KEY 环境变量")

    encoded = base64.b64encode(epub_bytes).decode("utf-8")

    payload = {
        "Recipients": {"To": [kindle_email]},
        "Content": {
            "From": {"Email": SENDER_EMAIL, "Name": "微信推Kindle"},
            "Subject": filename.replace(".epub", ""),
            "Body": [{"ContentType": "PlainText", "Content": "请在您的 Kindle 设备上查看推送的文章。\n\nSent by WechatToKindle."}],
            "Attachments": [
                {
                    "BinaryContent": encoded,
                    "Name": filename,
                    "ContentType": "application/epub+zip",
                }
            ],
        },
    }

    with httpx.Client(timeout=60) as client:
        resp = client.post(
            "https://api.elasticemail.com/v4/emails/transactional",
            headers={
                "X-ElasticEmail-ApiKey": ELASTIC_API_KEY,
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Elastic Email 错误 {resp.status_code}: {resp.text}")

    logger.info(f"Email sent via Elastic Email to {kindle_email}")
