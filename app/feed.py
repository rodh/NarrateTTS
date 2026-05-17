import os
import re
from email.utils import formatdate
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import Request


ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ET.register_namespace("itunes", ITUNES_NS)
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


def generate_feed(items: list[dict], title: str, description: str, link: str, base_url: str, artwork_file: str = "artwork.png") -> str:
    rss = Element("rss", version="2.0")

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
    img.set("href", f"{base_url}/static/{artwork_file}")

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

        duration = item.get("duration_seconds") or 0
        duration_label = ""
        if duration > 0:
            mins = round(duration / 60)
            if mins < 1:
                duration_label = "Less than 1 min"
            elif mins == 1:
                duration_label = "1 min"
            else:
                duration_label = f"{mins} min"

        summary = item.get("summary", "")
        if summary or duration_label:
            display_summary = summary
            if duration_label:
                prefix_html = f"<p><b>{duration_label}</b></p>"
                display_summary = prefix_html + summary if summary else prefix_html
            # Use placeholder — replaced with CDATA after serialization
            placeholder = _CDATA_PLACEHOLDER.format(item["id"])
            SubElement(entry, "description").text = placeholder
            # itunes:summary is plain text — strip HTML tags
            plain = re.sub(r'<[^>]+>', '', summary)
            plain = re.sub(r'\s+', ' ', plain).strip()
            if duration_label:
                plain = f"{duration_label} — {plain}" if plain else duration_label
            SubElement(entry, f"{{{ITUNES_NS}}}summary").text = plain

        source_url = item.get("source_url")
        if source_url:
            SubElement(entry, "link").text = source_url

        enclosure = SubElement(entry, "enclosure")
        enclosure.set("url", audio_url)
        enclosure.set("length", file_size)
        enclosure.set("type", "audio/mpeg")

        if duration > 0:
            SubElement(entry, f"{{{ITUNES_NS}}}duration").text = _format_duration(duration)

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(rss, encoding="unicode")

    # Replace CDATA placeholders with actual CDATA sections
    for item in items:
        summary = item.get("summary", "")
        dur = item.get("duration_seconds") or 0
        if summary or dur > 0:
            mins = round(dur / 60) if dur > 0 else 0
            if mins < 1 and dur > 0:
                dl = "Less than 1 min"
            elif mins == 1:
                dl = "1 min"
            elif mins > 1:
                dl = f"{mins} min"
            else:
                dl = ""
            display = summary
            if dl:
                display = f"<p><b>{dl}</b></p>{summary}" if summary else f"<p><b>{dl}</b></p>"
            placeholder = _CDATA_PLACEHOLDER.format(item["id"])
            xml = xml.replace(placeholder, f"<![CDATA[{display}]]>")

    return xml


def generate_opml(playlists: list[dict], base_url: str) -> str:
    opml = Element("opml", version="2.0")
    head = SubElement(opml, "head")
    SubElement(head, "title").text = "NarrateTTS Feeds"
    SubElement(head, "dateCreated").text = formatdate(localtime=True)

    body = SubElement(opml, "body")
    group = SubElement(body, "outline", text="NarrateTTS", title="NarrateTTS")

    for p in playlists:
        SubElement(group, "outline", type="rss",
                   text=p["name"], title=p["name"],
                   xmlUrl=f"{base_url}/feed/playlist/{p['id']}")

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(opml, encoding="unicode")
