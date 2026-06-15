from urllib.parse import urljoin, urlparse

import httpx
from readability import Document

from app.config import AUDIO_DIR


def title_from_url(url: str) -> str:
    """A readable fallback title derived from a URL (for failed extractions)."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.replace("www.", "")
        slug = parsed.path.rstrip("/").split("/")[-1]
        slug = slug.replace("-", " ").replace("_", " ").strip()
        return f"{host}: {slug}" if slug else (host or url)
    except Exception:
        return url


# Many sites 403 / serve degraded content to non-browser clients. Present a
# realistic browser identity so server-side extraction succeeds for most pages
# (hard paywalls that require login still won't extract — that's expected).
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


async def extract_from_url(url: str) -> dict[str, str]:
    """Extract article content from a URL.

    Returns dict with 'title' and 'text' keys.
    """
    async with httpx.AsyncClient(timeout=20.0, headers=_BROWSER_HEADERS) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()

    doc = Document(response.text, url=url)
    title = doc.title()
    html = doc.summary()

    # Strip HTML tags to get plain text
    text = _strip_html(html)

    image_url = _extract_og_image(response.text, url)
    return {"title": title, "text": text.strip(), "image_url": image_url}


def _extract_og_image(html: str, base_url: str) -> str | None:
    """Find an og:image / twitter:image URL in page HTML, resolved to absolute."""
    import re
    for prop in ("og:image", "twitter:image", "twitter:image:src"):
        p = re.escape(prop)
        m = (re.search(r'<meta[^>]+(?:property|name)=["\']' + p + r'["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
             or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']' + p + r'["\']', html, re.I))
        if m:
            return urljoin(base_url, m.group(1).strip())
    return None


def extract_from_text(text: str) -> dict[str, str]:
    """Clean pasted text (may contain markdown/HTML) and generate a title."""
    text = _strip_markdown(text)
    text = _strip_html(text)
    words = text.split()
    preview = " ".join(words[:12]).rstrip(".,;:")
    title = f"Text — {preview}{'...' if len(words) > 12 else ''}"
    return {"title": title, "text": text.strip()}


def _strip_markdown(text: str) -> str:
    """Remove common markdown formatting, keeping readable text."""
    import re
    # Remove images ![alt](url)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    # Convert links [text](url) to just text
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    # Remove headings markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", text)
    # Remove inline code backticks
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove code fences
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Remove blockquote markers
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Remove list markers (-, *, numbered)
    text = re.sub(r"^[\s]*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[\s]*\d+\.\s+", "", text, flags=re.MULTILINE)
    return text


def _strip_html(html: str) -> str:
    """Minimal HTML tag stripper."""
    import re
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&\w+;", " ", text)
    # Collapse multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text
