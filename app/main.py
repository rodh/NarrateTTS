import asyncio
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import HOST, PORT, AUDIO_DIR, STATIC_DIR, TTS_SERVICE_URL, KOKORO_MODEL, FEED_TTL_DAYS
from app.db import (
    init_db, add_item, list_items, get_item, delete_item, update_item,
    count_items, update_play_position, create_playlist, list_playlists,
    get_playlist, delete_playlist, add_item_to_playlist,
    remove_item_from_playlist, list_playlist_items, get_item_playlists,
    list_completed_items, list_feed_items, get_items_playlist_map,
    mark_consumed,
)
from app.feed import generate_feed, generate_opml, get_base_url
from app.extractor import extract_from_url, extract_from_text
from app.summarizer import generate_summary
from app.categorizer import categorize_item

app = FastAPI(title="NarrateTTS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    init_db()


# --- API Routes ---

@app.get("/api/items")
async def api_list_items(limit: int = 50, offset: int = 0):
    return list_items(limit=limit, offset=offset)


@app.get("/api/items/count")
async def api_item_count():
    return {"count": count_items()}


@app.get("/api/items/playlist-map")
async def api_items_playlist_map():
    return get_items_playlist_map()


@app.get("/api/voices")
async def api_voices():
    """Return list of available Kokoro voices."""
    from app.tts_engine import KOKORO_VOICES
    return {"voices": KOKORO_VOICES}


@app.post("/api/convert")
async def api_convert(payload: dict):
    """Convert text or URL to audio.

    Body: {"url": "https://..."} or {"text": "hello world"}
    """
    source_url = payload.get("url")
    text_input = payload.get("text")
    voice = payload.get("voice") or "af_heart"

    if source_url:
        try:
            extracted = await extract_from_url(source_url)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to extract content: {str(e)}")
        title = extracted["title"]
        text = extracted["text"]
    elif text_input:
        extracted = extract_from_text(text_input)
        title = extracted["title"]
        text = extracted["text"]
    else:
        raise HTTPException(status_code=400, detail="Provide 'url' or 'text'")

    item_id = add_item(source_url=source_url, title=title, text=text)

    # Start TTS generation in background
    asyncio.create_task(_process_tts(item_id, text, title, source_url, voice))

    return {"id": item_id, "status": "queued"}


async def _process_tts(item_id: int, text: str, title: str, source_url: str | None, voice: str = "af_heart"):
    """Background task: generate audio for an item."""
    try:
        update_item(item_id, status="processing")

        voice = voice or "af_heart"

        if TTS_SERVICE_URL:
            # Call mlx-audio server (OpenAI-compatible endpoint)
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{TTS_SERVICE_URL}/v1/audio/speech",
                    json={
                        "model": KOKORO_MODEL,
                        "input": text,
                        "voice": voice,
                        "response_format": "mp3",
                        "lang_code": "a" if not voice.startswith("b") else "b",
                        "verbose": False,
                    },
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"TTS service error: {resp.text}")

                filename = f"{item_id}.mp3"
                audio_path = AUDIO_DIR / filename

                with open(audio_path, "wb") as f:
                    f.write(resp.content)

                final_path = str(audio_path)
        else:
            # Fallback to local engine
            from app.tts_engine import engine as local_engine
            wav_path = await local_engine.generate(text, voice=voice)

            # Convert WAV to MP3 if ffmpeg is available
            mp3_path = AUDIO_DIR / f"{item_id}.mp3"
            try:
                import subprocess
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(wav_path), str(mp3_path)],
                    capture_output=True,
                    check=True,
                )
                wav_path.unlink(missing_ok=True)
                final_path = str(mp3_path)
            except (FileNotFoundError, subprocess.CalledProcessError):
                final_path = str(wav_path)

        # Estimate duration from word count (~150 wpm average speech rate)
        word_count = len(text.split())
        duration = round((word_count / 150) * 60, 1)

        # Generate summary (non-blocking, failure is non-fatal)
        try:
            summary = await generate_summary(text, title)
        except Exception:
            summary = ""

        update_item(item_id, status="completed", audio_path=final_path,
                    duration_seconds=duration, summary=summary)

        # Auto-categorize into playlist
        try:
            await categorize_item(item_id, title, summary)
        except Exception:
            pass
    except Exception as e:
        update_item(item_id, status="error", error=str(e))


@app.get("/api/items/{item_id}")
async def api_get_item(item_id: int):
    item = get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.delete("/api/items/{item_id}")
async def api_delete_item(item_id: int):
    delete_item(item_id)
    return {"deleted": item_id}


@app.patch("/api/items/{item_id}/progress")
async def api_update_progress(item_id: int, payload: dict):
    position = payload.get("position")
    if position is None or not isinstance(position, (int, float)) or position < 0:
        raise HTTPException(status_code=400, detail="Invalid position")
    update_play_position(item_id, float(position))
    return {"ok": True}


# --- Feed Endpoints ---

@app.get("/feed")
async def feed_all(request: Request):
    base_url = get_base_url(request)
    items = list_feed_items(FEED_TTL_DAYS)
    xml = generate_feed(
        items,
        title="NarrateTTS",
        description="All narrated articles",
        link=base_url,
        base_url=base_url,
    )
    return Response(content=xml, media_type="application/rss+xml; charset=utf-8")


@app.get("/feed/playlist/{playlist_id}")
async def feed_playlist(playlist_id: int, request: Request):
    playlist = get_playlist(playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    base_url = get_base_url(request)
    items = list_playlist_items(playlist_id, ttl_days=FEED_TTL_DAYS)
    xml = generate_feed(
        items,
        title=f"NarrateTTS - {playlist['name']}",
        description=playlist.get("description", ""),
        link=f"{base_url}/feed/playlist/{playlist_id}",
        base_url=base_url,
    )
    return Response(content=xml, media_type="application/rss+xml; charset=utf-8")


@app.get("/feed/opml")
async def feed_opml(request: Request):
    base_url = get_base_url(request)
    all_playlists = list_playlists()
    xml = generate_opml(all_playlists, base_url)
    return Response(
        content=xml,
        media_type="application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="narratetts.opml"'},
    )


# --- Playlist API ---

@app.get("/api/playlists")
async def api_list_playlists():
    return list_playlists()


@app.post("/api/playlists")
async def api_create_playlist(payload: dict):
    name = payload.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")
    description = payload.get("description", "")
    playlist_id = create_playlist(name, description)
    return {"id": playlist_id, "name": name}


@app.delete("/api/playlists/{playlist_id}")
async def api_delete_playlist(playlist_id: int):
    delete_playlist(playlist_id)
    return {"deleted": playlist_id}


@app.get("/api/playlists/{playlist_id}/items")
async def api_playlist_items(playlist_id: int):
    return list_playlist_items(playlist_id)


@app.post("/api/playlists/{playlist_id}/items")
async def api_add_to_playlist(playlist_id: int, payload: dict):
    item_id = payload.get("item_id")
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id is required")
    add_item_to_playlist(playlist_id, item_id)
    return {"ok": True}


@app.delete("/api/playlists/{playlist_id}/items/{item_id}")
async def api_remove_from_playlist(playlist_id: int, item_id: int):
    remove_item_from_playlist(playlist_id, item_id)
    return {"ok": True}


@app.get("/api/items/{item_id}/playlists")
async def api_item_playlists(item_id: int):
    return get_item_playlists(item_id)


# --- Backfill ---

@app.post("/api/backfill-summaries")
async def api_backfill_summaries():
    """Generate summaries for completed items that don't have one."""
    items = list_completed_items()
    count = 0
    for item in items:
        if item.get("summary"):
            continue
        text = item.get("text", "")
        title = item.get("title", "")
        if not text:
            continue
        try:
            summary = await generate_summary(text, title)
            if summary:
                update_item(item["id"], summary=summary)
                count += 1
        except Exception:
            continue
    return {"backfilled": count}


@app.post("/api/backfill-categories")
async def api_backfill_categories():
    """Auto-categorize completed items that aren't in any playlist."""
    items = list_completed_items()
    count = 0
    for item in items:
        try:
            await categorize_item(item["id"], item.get("title", ""), item.get("summary", ""))
            # Check if it was actually assigned (not skipped)
            if get_item_playlists(item["id"]):
                count += 1
        except Exception:
            continue
    return {"categorized": count}


# --- Audio Serving ---

@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    audio_file = AUDIO_DIR / filename
    if not audio_file.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    # Mark item as consumed on download
    stem = Path(filename).stem
    if stem.isdigit():
        mark_consumed(int(stem))
    return FileResponse(audio_file, media_type="audio/mpeg")


# --- Static Files ---

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --- Web UI ---

@app.get("/")
async def serve_index():
    return FileResponse("index.html")
