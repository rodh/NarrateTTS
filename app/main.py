import asyncio
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.config import HOST, PORT, AUDIO_DIR, TTS_SERVICE_URL
from app.db import init_db, add_item, list_items, get_item, delete_item, update_item, count_items
from app.extractor import extract_from_url, extract_from_text

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


@app.get("/api/voices")
async def api_voices():
    """Return list of available Piper voices."""
    import subprocess
    try:
        result = subprocess.run(
            ["piper", "--list_voices"],
            capture_output=True, text=True, timeout=30
        )
        voices = []
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                parts = line.split(" - ", 1)
                voices.append(parts[0].strip())
        return {"voices": voices or [""]}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"voices": [""]}


@app.post("/api/convert")
async def api_convert(payload: dict):
    """Convert text or URL to audio.

    Body: {"url": "https://..."} or {"text": "hello world"}
    """
    source_url = payload.get("url")
    text_input = payload.get("text")
    voice = payload.get("voice") or "en_US-lessac-medium"

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

    # Truncate very long text (Piper has limits)
    if len(text) > 2500:
        text = text[:2400] + "\n\n[continues...]"

    item_id = add_item(source_url=source_url, title=title, text=text)

    # Start TTS generation in background
    asyncio.create_task(_process_tts(item_id, text, source_url, voice))

    return {"id": item_id, "status": "queued"}


async def _process_tts(item_id: int, text: str, source_url: str | None, voice: str = "en_US-lessac-medium"):
    """Background task: generate audio for an item via TTS service."""
    try:
        update_item(item_id, status="processing")

        voice = voice or "en_US-lessac-medium"

        if TTS_SERVICE_URL:
            # Call TTS service
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{TTS_SERVICE_URL}/api/synthesize",
                    json={"text": text, "voice": voice},
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"TTS service error: {resp.text}")

                # TTS service returns the file as response body, save it
                filename = resp.headers.get("filename", f"{item_id}.mp3")
                audio_path = AUDIO_DIR / filename

                # Extract just the basename (service may return "tts_foo.mp3")
                audio_path = AUDIO_DIR / Path(filename).name

                with open(audio_path, "wb") as f:
                    f.write(resp.content)

                final_path = str(audio_path)
        else:
            # Fallback to local engine
            from app.tts_engine import engine as local_engine
            audio_path = await local_engine.generate(text, voice=voice)

            # Convert WAV to MP3 if ffmpeg is available
            mp3_path = AUDIO_DIR / f"{item_id}.mp3"
            wav_path = Path(audio_path)
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

        update_item(item_id, status="completed", audio_path=final_path,
                    duration_seconds=duration)
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


# --- Audio Serving ---

@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    audio_file = AUDIO_DIR / filename
    if not audio_file.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(audio_file, media_type="audio/mpeg")


# --- Web UI ---

@app.get("/")
async def serve_index():
    return FileResponse("index.html")
