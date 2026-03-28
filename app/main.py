"""
WechatToKindle — FastAPI backend
"""

import logging
import os
import re
from datetime import datetime
from typing import Annotated

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .converter import build_epub
from .fetcher import fetch_article, is_wechat_url
from .sender import SENDER_EMAIL, send_to_kindle

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="WechatToKindle")

# Serve static files (index.html)
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = os.path.join(static_dir, "index.html")
    with open(index_path, encoding="utf-8") as f:
        return f.read()


@app.get("/config")
async def config():
    """Return public configuration for the frontend."""
    return {"sender_email": SENDER_EMAIL}


@app.post("/send")
async def send(
    request: Request,
    kindle_email: Annotated[str, Form()],
    urls: Annotated[str, Form()],
    book_title: Annotated[str | None, Form()] = None,
):
    # Validate Kindle email
    kindle_email = kindle_email.strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", kindle_email):
        raise HTTPException(status_code=400, detail="Kindle 邮箱地址格式不正确")

    # Parse URLs — one per line, ignore blanks
    url_list = [u.strip() for u in urls.strip().splitlines() if u.strip()]
    if not url_list:
        raise HTTPException(status_code=400, detail="请至少输入一个文章链接")
    if len(url_list) > 20:
        raise HTTPException(status_code=400, detail="每次最多发送 20 篇文章")

    # Validate all URLs are WeChat articles
    for url in url_list:
        if not url.startswith("http"):
            raise HTTPException(status_code=400, detail=f"链接格式不正确: {url}")
        if not is_wechat_url(url):
            raise HTTPException(
                status_code=400,
                detail=f"目前只支持微信公众号文章链接 (mp.weixin.qq.com): {url}",
            )

    # Fetch all articles
    articles = []
    errors = []
    for url in url_list:
        try:
            article = fetch_article(url)
            articles.append(article)
            logger.info(f"Fetched: {article.title}")
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            errors.append(f"获取失败: {url}")

    if not articles:
        raise HTTPException(status_code=422, detail="所有文章链接均获取失败，请检查链接是否有效")

    # Build EPUB
    epub_bytes = build_epub(articles, book_title=book_title or None)

    # Determine filename
    date_str = datetime.now().strftime("%Y%m%d")
    if len(articles) == 1:
        safe_title = re.sub(r'[^\w\u4e00-\u9fff]', '_', articles[0].title)[:40]
        filename = f"{safe_title}_{date_str}.epub"
    else:
        filename = f"微信文章_{date_str}_{len(articles)}篇.epub"

    # Send to Kindle
    try:
        send_to_kindle(kindle_email, epub_bytes, filename)
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        raise HTTPException(status_code=500, detail=f"邮件发送失败: {e}")

    result = {
        "success": True,
        "message": f"成功推送 {len(articles)} 篇文章到 {kindle_email}",
        "articles": [{"title": a.title, "author": a.author} for a in articles],
    }
    if errors:
        result["warnings"] = errors

    return JSONResponse(result)
