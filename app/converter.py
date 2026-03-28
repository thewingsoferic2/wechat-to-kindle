"""
Converts a list of Article objects into a single EPUB file.
"""

import io
import logging
import uuid
from datetime import datetime
from typing import Optional

import httpx
from ebooklib import epub

from .fetcher import Article

logger = logging.getLogger(__name__)

# Minimal CSS for readable Kindle display
KINDLE_CSS = """
body {
    font-family: serif;
    font-size: 1em;
    line-height: 1.6;
    margin: 0.5em 1em;
    color: #1a1a1a;
}
h1, h2, h3 {
    font-family: sans-serif;
    line-height: 1.3;
    margin-top: 1.2em;
}
p {
    margin: 0.6em 0;
    text-align: justify;
}
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 0.8em auto;
}
blockquote {
    border-left: 3px solid #ccc;
    margin-left: 0.5em;
    padding-left: 1em;
    color: #555;
}
.article-header {
    border-bottom: 1px solid #ddd;
    padding-bottom: 0.8em;
    margin-bottom: 1.2em;
}
.article-meta {
    font-size: 0.85em;
    color: #888;
    font-family: sans-serif;
    margin-top: 0.3em;
}
section.article + section.article {
    border-top: 2px solid #333;
    margin-top: 2em;
    padding-top: 1em;
}
"""


def build_epub(articles: list[Article], book_title: Optional[str] = None) -> bytes:
    """
    Build an EPUB from one or more articles.
    Returns the EPUB file content as bytes.
    """
    book = epub.EpubBook()
    book.set_identifier(str(uuid.uuid4()))

    if book_title:
        book.set_title(book_title)
    elif len(articles) == 1:
        book.set_title(articles[0].title)
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")
        book.set_title(f"微信文章合集 {date_str}")

    book.set_language("zh")

    # Add CSS
    css = epub.EpubItem(
        uid="style",
        file_name="style/kindle.css",
        media_type="text/css",
        content=KINDLE_CSS.encode("utf-8"),
    )
    book.add_item(css)

    chapters = []

    for i, article in enumerate(articles):
        chapter = _make_chapter(book, article, i, css)
        book.add_item(chapter)
        chapters.append(chapter)

    # Table of contents
    book.toc = tuple(epub.Link(c.file_name, c.title, c.id) for c in chapters)

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    book.spine = ["nav"] + chapters

    # Write to bytes buffer
    buf = io.BytesIO()
    epub.write_epub(buf, book)
    return buf.getvalue()


def _make_chapter(
    book: epub.EpubBook,
    article: Article,
    index: int,
    css: epub.EpubItem,
) -> epub.EpubHtml:
    chapter = epub.EpubHtml(
        title=article.title,
        file_name=f"chapter_{index + 1}.xhtml",
        lang="zh",
    )
    chapter.add_item(css)

    # Build chapter HTML
    header_html = f"""
    <div class="article-header">
        <h1>{_escape(article.title)}</h1>
        <div class="article-meta">{_escape(article.author)}</div>
    </div>
    """

    # Optionally embed cover image
    cover_img_html = ""
    if article.cover_url:
        img_data, media_type = _try_fetch_image(article.cover_url)
        if img_data:
            img_name = f"images/cover_{index}.jpg"
            img_item = epub.EpubItem(
                uid=f"cover_img_{index}",
                file_name=img_name,
                media_type=media_type,
                content=img_data,
            )
            book.add_item(img_item)
            cover_img_html = f'<img src="../{img_name}" alt="封面"/>'

    chapter.set_content(
        f"""<?xml version='1.0' encoding='utf-8'?>
        <!DOCTYPE html>
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh">
        <head>
            <title>{_escape(article.title)}</title>
            <link rel="stylesheet" type="text/css" href="../style/kindle.css"/>
        </head>
        <body>
            <section class="article">
                {header_html}
                {cover_img_html}
                {article.content_html}
            </section>
        </body>
        </html>"""
    )

    return chapter


def _try_fetch_image(url: str) -> tuple[Optional[bytes], str]:
    """Fetch image bytes, returning (data, media_type) or (None, '')."""
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            media_type = resp.headers.get("content-type", "image/jpeg").split(";")[0]
            return resp.content, media_type
    except Exception as e:
        logger.warning(f"Failed to fetch image {url}: {e}")
        return None, ""


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
