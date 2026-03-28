"""
WeChat article fetcher.
Fetches article content from mp.weixin.qq.com URLs.
"""

import re
import time
import logging
from dataclasses import dataclass
from typing import Optional

import httpx
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


@dataclass
class Article:
    title: str
    author: str
    content_html: str
    cover_url: Optional[str]
    url: str


def is_wechat_url(url: str) -> bool:
    return "mp.weixin.qq.com" in url or "weixin.qq.com" in url


def fetch_article(url: str) -> Article:
    """Fetch and parse a WeChat public account article."""
    logger.info(f"Fetching article: {url}")

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        resp = client.get(url)
        resp.raise_for_status()
        html = resp.text

    return _parse_article(html, url)


def _parse_article(html: str, url: str) -> Article:
    soup = BeautifulSoup(html, "html.parser")

    # Extract title
    title = _extract_title(soup)

    # Extract author
    author = _extract_author(soup)

    # Extract cover image
    cover_url = _extract_cover(soup)

    # Extract main content
    content_html = _extract_content(soup)

    return Article(
        title=title,
        author=author,
        content_html=content_html,
        cover_url=cover_url,
        url=url,
    )


def _extract_title(soup: BeautifulSoup) -> str:
    # WeChat article title selectors
    for selector in [
        "#activity-name",
        ".rich_media_title",
        "h1.title",
        "h1",
    ]:
        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)

    # Fallback to <title> tag
    title_tag = soup.find("title")
    if title_tag:
        text = title_tag.get_text(strip=True)
        # Remove " - 微信公众号" suffix
        return re.sub(r"\s*[-–]\s*微信公众[号平台].*$", "", text).strip()

    return "未知标题"


def _extract_author(soup: BeautifulSoup) -> str:
    for selector in [
        "#js_name",
        ".account_nickname_inner",
        ".rich_media_meta_nickname",
        'a[id="js_name"]',
    ]:
        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)
    return "未知作者"


def _extract_cover(soup: BeautifulSoup) -> Optional[str]:
    # Try og:image meta tag first
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        return og_image["content"]

    # Try first image in content
    content = soup.select_one("#js_content")
    if content:
        img = content.find("img")
        if img:
            return img.get("data-src") or img.get("src")

    return None


def _extract_content(soup: BeautifulSoup) -> str:
    # Main content container for WeChat articles
    content_div = soup.select_one("#js_content") or soup.select_one(".rich_media_content")

    if not content_div:
        # Fallback: grab body
        content_div = soup.find("body")

    if not content_div:
        return "<p>无法提取文章内容</p>"

    # Clean up the content
    _clean_content(content_div)

    return str(content_div)


def _clean_content(tag: Tag) -> None:
    """Remove scripts, ads, and fix image sources."""
    # Remove unwanted elements
    for selector in ["script", "style", "iframe", ".qr_code_pc_outer"]:
        for el in tag.select(selector):
            el.decompose()

    # Fix lazy-loaded images: data-src -> src
    for img in tag.find_all("img"):
        data_src = img.get("data-src")
        if data_src:
            img["src"] = data_src
            del img["data-src"]

        # Remove srcset/sizes to avoid broken references
        for attr in ["srcset", "data-srcset", "data-w", "data-ratio"]:
            if img.has_attr(attr):
                del img[attr]

        # Ensure images are styled for Kindle width
        img["style"] = "max-width:100%;height:auto;"
