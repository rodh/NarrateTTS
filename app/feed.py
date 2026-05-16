import os
from email.utils import formatdate
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import Request


ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"


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

        enclosure = SubElement(entry, "enclosure")
        enclosure.set("url", audio_url)
        enclosure.set("length", file_size)
        enclosure.set("type", "audio/mpeg")

        duration = item.get("duration_seconds") or 0
        if duration > 0:
            SubElement(entry, f"{{{ITUNES_NS}}}duration").text = _format_duration(duration)

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(rss, encoding="unicode")
