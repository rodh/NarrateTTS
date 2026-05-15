import asyncio
import os
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.engine import PiperEngine, DEFAULT_VOICE

TTS_PORT = int(os.environ.get("TTS_PORT", "8100"))

app = FastAPI(title="TTS Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/voices")
async def api_voices():
    """Return list of available Piper voices."""
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
        return {"voices": voices or [DEFAULT_VOICE]}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"voices": [DEFAULT_VOICE]}


@app.post("/api/synthesize")
async def api_synthesize(payload: dict):
    """Synthesize text to audio. Returns MP3 (or WAV if ffmpeg unavailable).

    Body: {"text": "hello world", "voice": "en_US-lessac-medium"}
    """
    text = payload.get("text")
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="'text' is required")

    voice = payload.get("voice") or DEFAULT_VOICE

    if len(text) > 5000:
        text = text[:4900] + "\n\n[continues...]"

    try:
        engine = PiperEngine(voice=voice)
        wav_path = await engine.generate(text, voice=voice)

        # Convert WAV to MP3 if ffmpeg is available
        mp3_path = wav_path.with_suffix(".mp3")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(wav_path), str(mp3_path)],
                capture_output=True,
                check=True,
            )
            wav_path.unlink(missing_ok=True)
            final_path = mp3_path
        except (FileNotFoundError, subprocess.CalledProcessError):
            final_path = wav_path

        return FileResponse(
            str(final_path),
            media_type="audio/mpeg" if final_path.suffix == ".mp3" else "audio/wav",
            filename=f"tts_{final_path.name}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


@app.post("/api/synthesize/queued")
async def api_synthesize_queued(payload: dict):
    """Synthesize text to audio asynchronously. Returns job ID, poll for result.

    Body: {"text": "hello world", "voice": "en_US-lessac-medium"}
    """
    text = payload.get("text")
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="'text' is required")

    voice = payload.get("voice") or DEFAULT_VOICE
    job_id = f"{int(asyncio.get_event_loop().time() * 1000)}"

    if len(text) > 5000:
        text = text[:4900] + "\n\n[continues...]"

    asyncio.create_task(_process_synthesis(job_id, text, voice))

    return {"job_id": job_id, "status": "queued"}


# In-memory job store (replace with Redis for production)
_job_store: dict = {}


async def _process_synthesis(job_id: str, text: str, voice: str):
    try:
        _job_store[job_id] = {"status": "processing"}
        engine = PiperEngine(voice=voice)
        wav_path = await engine.generate(text, voice=voice)

        mp3_path = wav_path.with_suffix(".mp3")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(wav_path), str(mp3_path)],
                capture_output=True,
                check=True,
            )
            wav_path.unlink(missing_ok=True)
            filename = mp3_path.name
        except (FileNotFoundError, subprocess.CalledProcessError):
            filename = wav_path.name

        _job_store[job_id] = {
            "status": "completed",
            "filename": filename,
        }
    except Exception as e:
        _job_store[job_id] = {"status": "error", "error": str(e)}


@app.get("/api/jobs/{job_id}")
async def api_get_job(job_id: str):
    """Poll job status. Returns {status, filename} when completed."""
    job = _job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    audio_file = Path(os.environ.get("TTS_OUTPUT_DIR", "/app/audio")) / filename
    if not audio_file.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    media_type = "audio/mpeg" if filename.endswith(".mp3") else "audio/wav"
    return FileResponse(str(audio_file), media_type=media_type)
