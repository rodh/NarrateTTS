import os
import re
from email.utils import formatdate
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import Request


ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
_CDATA_PLACEHOLDER = "CDATA_{}_CDATA"


def get_base_url(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host"))
    return f"{proto}://{host}"


def _rfc2822(dt_str: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_str)
        return formatdate(dt.timestamp(), localtime=True)
    except (ValueError, TypeError):
        return formatdate()


def _format_duration(seconds: float) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def generate_feed(items: list[dict], title: str, description: str, link: str, base_url: str) -> str:
    rss = Element("rss", version="2.0")
    rss.set("xmlns:itunes", ITUNES_NS)

    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = title
    SubElement(channel, "description").text = description
    SubElement(channel, "link").text = link
    SubElement(channel, "generator").text = "NarrateTTS"
    SubElement(channel, "language").text = "en"
    SubElement(channel, "lastBuildDate").text = formatdate(localtime=True)
    SubElement(channel, f"{{{ITUNES_NS}}}author").text = "NarrateTTS"
    SubElement(channel, f"{{{ITUNES_NS}}}explicit").text = "false"
    SubElement(channel, f"{{{ITUNES_NS}}}type").text = "episodic"
    cat = SubElement(channel, f"{{{ITUNES_NS}}}category")
    cat.set("text", "Technology")
    img = SubElement(channel, f"{{{ITUNES_NS}}}image")
    img.set("href", f"{base_url}/static/artwork.png")

    for item in items:
        if not item.get("audio_path"):
            continue

        audio_file = os.path.basename(item["audio_path"])
        audio_url = f"{base_url}/audio/{audio_file}"

        # Get file size
        try:
            file_size = str(os.path.getsize(item["audio_path"]))
        except OSError:
            file_size = "0"

        entry = SubElement(channel, "item")
        SubElement(entry, "title").text = item.get("title", "Untitled")
        SubElement(entry, "guid", isPermaLink="false").text = f"narratetts-{item['id']}"
        SubElement(entry, "pubDate").text = _rfc2822(item.get("created_at", ""))

        summary = item.get("summary", "")
        if summary:
            # Use placeholder — replaced with CDATA after serialization
            placeholder = _CDATA_PLACEHOLDER.format(item["id"])
            SubElement(entry, "description").text = placeholder
            # itunes:summary is plain text — strip HTML tags
            plain = re.sub(r'<[^>]+>', '', summary)
            plain = re.sub(r'\s+', ' ', plain).strip()
            SubElement(entry, f"{{{ITUNES_NS}}}summary").text = plain

        source_url = item.get("source_url")
        if source_url:
            SubElement(entry, "link").text = source_url

        enclosure = SubElement(entry, "enclosure")
        enclosure.set("url", audio_url)
        enclosure.set("length", file_size)
        enclosure.set("type", "audio/mpeg")

        duration = item.get("duration_seconds") or 0
        if duration > 0:
            SubElement(entry, f"{{{ITUNES_NS}}}duration").text = _format_duration(duration)

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(rss, encoding="unicode")

    # Replace CDATA placeholders with actual CDATA sections
    for item in items:
        summary = item.get("summary", "")
        if summary:
            placeholder = _CDATA_PLACEHOLDER.format(item["id"])
            xml = xml.replace(placeholder, f"<![CDATA[{summary}]]>")

    return xml
