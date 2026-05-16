import re
import logging

import httpx

from app.config import LLM_SERVICE_URL, LLM_MODEL, LLM_API_KEY, LLM_SEMAPHORE
from app.db import (
    get_item_playlists, list_playlists, add_item_to_playlist,
    create_playlist, get_playlist_by_name,
)

logger = logging.getLogger(__name__)


async def categorize_item(item_id: int, title: str, summary: str):
    """Assign item to the best-matching playlist via LLM, or Uncategorized."""
    # Skip if already in a playlist
    if get_item_playlists(item_id):
        return

    playlists = [p for p in list_playlists() if p["name"] != "Uncategorized"]

    if not LLM_SERVICE_URL or not playlists:
        _assign_uncategorized(item_id)
        return

    try:
        playlist_id = await _llm_categorize(title, summary, playlists)
    except Exception as e:
        logger.warning("LLM categorization failed: %s", e)
        playlist_id = None

    if playlist_id:
        add_item_to_playlist(playlist_id, item_id)
    else:
        _assign_uncategorized(item_id)


async def _llm_categorize(title: str, summary: str, playlists: list[dict]) -> int | None:
    """Ask LLM to pick the best playlist. Returns playlist_id or None."""
    clean_summary = re.sub(r"<[^>]+>", "", summary or "")

    numbered = "\n".join(
        f"{i+1}. {p['name']}" + (f" - {p['description']}" if p.get("description") else "")
        for i, p in enumerate(playlists)
    )

    prompt = (
        f"Classify this article into one of the categories below.\n"
        f"Reply with ONLY the category number. If none fit well, reply 0.\n\n"
        f"Categories:\n{numbered}\n\n"
        f"Title: {title}\n"
        f"Summary: {clean_summary}"
    )

    headers = {}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    async with LLM_SEMAPHORE:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{LLM_SERVICE_URL}/v1/chat/completions",
                headers=headers,
                json={
                    "model": LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 5,
                    "temperature": 0.1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()

    match = re.search(r"\d+", content)
    if not match:
        return None

    idx = int(match.group()) - 1
    if idx < 0 or idx >= len(playlists):
        return None

    return playlists[idx]["id"]


def _assign_uncategorized(item_id: int):
    """Add item to the Uncategorized playlist, creating it if needed."""
    playlist = get_playlist_by_name("Uncategorized")
    if not playlist:
        pid = create_playlist("Uncategorized", "Items that don't match any category")
        try:
            from app.artwork import generate_playlist_artwork
            generate_playlist_artwork("Uncategorized", pid)
        except Exception:
            pass
    else:
        pid = playlist["id"]
    add_item_to_playlist(pid, item_id)
