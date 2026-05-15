# Kokoro TTS Integration — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace Piper TTS with Kokoro-82M via mlx-audio for significantly more natural-sounding local text-to-speech on Apple Silicon.

**Architecture:** The custom `tts-service/` Docker container is removed entirely. In its place, the `mlx-audio` built-in server runs natively on the Mac (port 8100) with MLX GPU acceleration. The main NarrateTTS app calls it via an OpenAI-compatible `/v1/audio/speech` endpoint. A local `KokoroEngine` fallback uses `kokoro-mlx` directly as a Python library.

**Tech Stack:** `mlx-audio` (pip), Kokoro-82M model (auto-downloaded from HuggingFace), FastAPI, Python 3.11+

**Design doc:** `docs/plans/2026-05-15-kokoro-tts-integration-design.md`

---

### Task 1: Install mlx-audio and verify Kokoro works locally

**Files:**
- Modify: `requirements.txt`

**Step 1: Install mlx-audio in the project venv**

```bash
source .venv/bin/activate
pip install mlx-audio
```

**Step 2: Verify Kokoro generates speech**

```bash
python3 -c "
from mlx_audio.tts.generate import generate_audio
audio = generate_audio(text='Hello, this is a test of Kokoro text to speech.', voice='af_heart', speed=1.0)
print(f'Generated audio: {type(audio)}, length: {len(audio) if hasattr(audio, \"__len__\") else \"stream\"} ')
print('Success!')
"
```

Expected: Model downloads (~500MB first run), then prints success. If the API differs, adapt — check `python3 -c "import mlx_audio; help(mlx_audio)"` for the actual interface.

**Step 3: Verify the mlx-audio server starts**

```bash
mlx_audio.server --port 8100 &
sleep 5
curl -s http://localhost:8100/health || curl -s http://localhost:8100/
kill %1
```

Expected: Server starts and responds. Note the actual health/root endpoint for use in start.sh.

**Step 4: Update requirements.txt**

Replace `piper-tts==1.2.0` with `mlx-audio`:

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
mlx-audio
httpx==0.27.2
readability-lxml==0.8.1
lxml-html-clean==0.4.1
```

**Step 5: Commit**

```bash
git add requirements.txt
git commit -m "deps: replace piper-tts with mlx-audio for Kokoro TTS"
```

---

### Task 2: Replace PiperEngine with KokoroEngine

**Files:**
- Rewrite: `app/tts_engine.py`
- Modify: `app/config.py`

**Step 1: Update config.py**

Remove `MODEL_CACHE_DIR` (mlx-audio handles its own model cache). Remove `GENERATION_DIR` alias:

```python
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = BASE_DIR / "audio"
DATA_DIR = BASE_DIR / "data"

# TTS settings
DEFAULT_VOICE = os.environ.get("TTS_VOICE", "af_heart")

# TTS Service (set to empty string to use local engine)
TTS_SERVICE_URL = os.environ.get("TTS_SERVICE_URL", "")

# Server settings
HOST = "127.0.0.1"
PORT = 8090

# Ensure directories exist
AUDIO_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
```

**Step 2: Rewrite tts_engine.py**

Replace PiperEngine with KokoroEngine that uses mlx-audio directly:

```python
import asyncio
import hashlib
from pathlib import Path

from app.config import AUDIO_DIR, DEFAULT_VOICE

# Kokoro voices available in mlx-audio
KOKORO_VOICES = [
    {"id": "af_heart", "name": "Heart (F)"},
    {"id": "af_bella", "name": "Bella (F)"},
    {"id": "af_nicole", "name": "Nicole (F)"},
    {"id": "af_sarah", "name": "Sarah (F)"},
    {"id": "af_sky", "name": "Sky (F)"},
    {"id": "am_adam", "name": "Adam (M)"},
    {"id": "am_michael", "name": "Michael (M)"},
    {"id": "bf_emma", "name": "Emma (F, UK)"},
    {"id": "bf_isabella", "name": "Isabella (F, UK)"},
    {"id": "bm_george", "name": "George (M, UK)"},
    {"id": "bm_lewis", "name": "Lewis (M, UK)"},
]


class KokoroEngine:
    def __init__(self, voice: str = DEFAULT_VOICE):
        self.voice = voice
        self._model = None

    async def generate(self, text: str, voice: str | None = None) -> Path:
        """Generate audio from text using Kokoro TTS via mlx-audio. Returns path to WAV file."""
        effective_voice = voice or self.voice

        def _synthesize():
            from mlx_audio.tts.generate import generate_audio
            import soundfile as sf

            filename = f"tts_{hashlib.md5(text[:200].encode()).hexdigest()[:12]}.wav"
            output_path = AUDIO_DIR / filename

            audio = generate_audio(
                text=text,
                voice=effective_voice,
                speed=1.0,
            )
            sf.write(str(output_path), audio, 24000)
            return output_path

        return await asyncio.get_event_loop().run_in_executor(None, _synthesize)


engine = KokoroEngine()
```

Note: The exact `generate_audio` API may differ — verify against actual mlx-audio docs during Task 1. Adapt the import path and function signature as needed.

**Step 3: Test the engine locally**

```bash
python3 -c "
import asyncio
from app.tts_engine import engine
path = asyncio.run(engine.generate('This is a test of the Kokoro engine.', voice='af_heart'))
print(f'Generated: {path}')
print(f'Exists: {path.exists()}')
"
```

Expected: Generates a WAV file in the audio/ directory.

**Step 4: Commit**

```bash
git add app/config.py app/tts_engine.py
git commit -m "feat: replace PiperEngine with KokoroEngine using mlx-audio"
```

---

### Task 3: Update main app TTS integration

**Files:**
- Modify: `app/main.py`

**Step 1: Update /api/voices endpoint**

Replace the Piper `subprocess` call with the Kokoro voice list:

```python
@app.get("/api/voices")
async def api_voices():
    """Return list of available Kokoro voices."""
    from app.tts_engine import KOKORO_VOICES
    return {"voices": KOKORO_VOICES}
```

**Step 2: Update /api/convert endpoint**

Change the default voice from `en_US-bryce-medium` to `af_heart`. Remove the 2500-char text truncation:

```python
@app.post("/api/convert")
async def api_convert(payload: dict):
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
    asyncio.create_task(_process_tts(item_id, text, source_url, voice))
    return {"id": item_id, "status": "queued"}
```

**Step 3: Update _process_tts to call Kokoro**

Two paths: (a) call mlx-audio server if TTS_SERVICE_URL is set, (b) use local KokoroEngine as fallback.

```python
async def _process_tts(item_id: int, text: str, source_url: str | None, voice: str = "af_heart"):
    """Background task: generate audio for an item."""
    try:
        update_item(item_id, status="processing")
        voice = voice or "af_heart"

        if TTS_SERVICE_URL:
            # Call mlx-audio server (OpenAI-compatible endpoint)
            async with httpx.AsyncClient(timeout=300) as client:
                resp = await client.post(
                    f"{TTS_SERVICE_URL}/v1/audio/speech",
                    json={"model": "kokoro", "input": text, "voice": voice, "response_format": "mp3"},
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"TTS service error: {resp.text}")

                filename = f"{item_id}.mp3"
                audio_path = AUDIO_DIR / filename
                with open(audio_path, "wb") as f:
                    f.write(resp.content)
                final_path = str(audio_path)
        else:
            # Local engine fallback
            from app.tts_engine import engine as local_engine
            wav_path = await local_engine.generate(text, voice=voice)

            # Convert WAV to MP3 if ffmpeg is available
            mp3_path = AUDIO_DIR / f"{item_id}.mp3"
            try:
                import subprocess
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(wav_path), str(mp3_path)],
                    capture_output=True, check=True,
                )
                wav_path.unlink(missing_ok=True)
                final_path = str(mp3_path)
            except (FileNotFoundError, subprocess.CalledProcessError):
                final_path = str(wav_path)

        word_count = len(text.split())
        duration = round((word_count / 150) * 60, 1)
        update_item(item_id, status="completed", audio_path=final_path, duration_seconds=duration)
    except Exception as e:
        update_item(item_id, status="error", error=str(e))
```

**Step 4: Remove unused Piper import**

Remove the `import subprocess` at the top of main.py if it was only used for the voices endpoint. Clean up any remaining Piper references.

**Step 5: Test the API**

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8090 &
sleep 2

# Test voices endpoint
curl -s http://localhost:8090/api/voices | python3 -m json.tool

# Test conversion with local engine (no TTS_SERVICE_URL)
curl -s -X POST http://localhost:8090/api/convert \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, this is a test.", "voice": "af_heart"}'

# Wait for processing, then check
sleep 10
curl -s http://localhost:8090/api/items | python3 -m json.tool

kill %1
```

Expected: Voices return Kokoro list. Conversion queues and completes.

**Step 6: Commit**

```bash
git add app/main.py
git commit -m "feat: update main app to use Kokoro TTS via mlx-audio"
```

---

### Task 4: Update frontend voice selector

**Files:**
- Modify: `index.html`

**Step 1: Replace the hardcoded Piper voice list**

Replace the `COMMON_VOICES` array and update `loadVoices()` to use the new `/api/voices` response format (which now returns objects with `id` and `name`):

```javascript
const COMMON_VOICES = [
    { id: "af_heart", name: "Heart (F)" },
    { id: "af_bella", name: "Bella (F)" },
    { id: "af_nicole", name: "Nicole (F)" },
    { id: "af_sarah", name: "Sarah (F)" },
    { id: "af_sky", name: "Sky (F)" },
    { id: "am_adam", name: "Adam (M)" },
    { id: "am_michael", name: "Michael (M)" },
    { id: "bf_emma", name: "Emma (F, UK)" },
    { id: "bf_isabella", name: "Isabella (F, UK)" },
    { id: "bm_george", name: "George (M, UK)" },
    { id: "bm_lewis", name: "Lewis (M, UK)" },
];
```

Update `loadVoices()` to handle the new response format:

```javascript
async function loadVoices() {
    const select = document.getElementById('voice-select');
    try {
        const res = await fetch('/api/voices');
        const data = await res.json();
        const voices = data.voices || [];

        select.innerHTML = '';
        if (voices.length > 0) {
            for (const v of voices) {
                const opt = document.createElement('option');
                opt.value = v.id;
                opt.textContent = v.name;
                select.appendChild(opt);
            }
        } else {
            _fallbackVoices(select);
        }
    } catch (e) {
        _fallbackVoices(select);
    }
}

function _fallbackVoices(select) {
    for (const v of COMMON_VOICES) {
        const opt = document.createElement('option');
        opt.value = v.id;
        opt.textContent = v.name;
        select.appendChild(opt);
    }
}
```

Also update the default `<option>` in the HTML from `en_US-bryce-medium` to `af_heart`:

```html
<select id="voice-select" ...>
    <option value="af_heart" selected>Heart (F)</option>
</select>
```

**Step 2: Test in browser**

Open http://localhost:8090, verify the voice dropdown shows Kokoro voices, submit a test conversion.

**Step 3: Commit**

```bash
git add index.html
git commit -m "feat: update frontend voice selector for Kokoro voices"
```

---

### Task 5: Update start.sh

**Files:**
- Rewrite: `start.sh`

**Step 1: Rewrite start.sh to launch both services**

```bash
#!/usr/bin/env bash
set -e

echo "Setting up NarrateTTS..."

# Create virtual environment if needed
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

# Install dependencies
pip install -q -r requirements.txt

# Check for ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "Warning: ffmpeg not found. Local engine will save as WAV instead of MP3."
    echo "Install with: brew install ffmpeg"
fi

cleanup() {
    echo ""
    echo "Shutting down..."
    [ -n "$TTS_PID" ] && kill "$TTS_PID" 2>/dev/null
    [ -n "$APP_PID" ] && kill "$APP_PID" 2>/dev/null
    wait 2>/dev/null
    echo "Done."
}
trap cleanup EXIT INT TERM

# Start mlx-audio TTS server in background
echo "Starting Kokoro TTS server on http://localhost:8100..."
mlx_audio.server --host 127.0.0.1 --port 8100 &
TTS_PID=$!
sleep 3

# Start main app
export TTS_SERVICE_URL=http://localhost:8100
echo "Starting NarrateTTS on http://localhost:8090..."
uvicorn app.main:app --host 127.0.0.1 --port 8090 &
APP_PID=$!

echo ""
echo "NarrateTTS is running:"
echo "  App:  http://localhost:8090"
echo "  TTS:  http://localhost:8100"
echo ""
echo "Press Ctrl+C to stop."

wait
```

Note: The exact `mlx_audio.server` command syntax may differ. Verify during Task 1 — it might be `python3 -m mlx_audio.server` or similar.

**Step 2: Test startup**

```bash
chmod +x start.sh
./start.sh
```

Verify both services start, then Ctrl+C to test cleanup.

**Step 3: Commit**

```bash
git add start.sh
git commit -m "feat: update start.sh to launch Kokoro TTS + main app"
```

---

### Task 6: Update docker-compose.yml and clean up tts-service/

**Files:**
- Modify: `docker-compose.yml`
- Delete: `tts-service/` directory

**Step 1: Simplify docker-compose.yml**

Remove the `tts-service` container. Keep `narrate-tts` for users who want Docker for the main app (it will use local engine fallback since TTS_SERVICE_URL won't be set inside Docker):

```yaml
services:
  narrate-tts:
    build: .
    ports:
      - "8090:8090"
    volumes:
      - ./audio:/app/audio
      - ./index.html:/app/index.html
    environment:
      - PYTHONUNBUFFERED=1
```

**Step 2: Update Dockerfile**

Remove ffmpeg (mlx-audio returns MP3 directly when using the server). Actually, keep ffmpeg for the local engine WAV→MP3 fallback path:

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y gcc python3-dev ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY index.html .

EXPOSE 8090
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]
```

Note: mlx-audio won't have MLX acceleration inside Docker (no Metal access). The Docker path uses CPU inference as a fallback. The recommended path is native via `start.sh`.

**Step 3: Remove tts-service/ directory**

```bash
rm -rf tts-service/
```

**Step 4: Commit**

```bash
git add docker-compose.yml Dockerfile
git rm -r tts-service/
git commit -m "chore: remove Piper tts-service, simplify Docker setup"
```

---

### Task 7: Update README.md

**Files:**
- Rewrite: `README.md`

**Step 1: Update README**

Update to reflect Kokoro, native setup, and new voice format. Key changes:
- Replace "Piper" references with "Kokoro"
- Primary setup: `./start.sh` (native, recommended)
- Secondary: Docker (CPU fallback, no MLX)
- Update voice list format
- Update API docs for `/api/voices` returning `[{id, name}]`

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README for Kokoro TTS integration"
```

---

### Task 8: End-to-end test

**Step 1: Fresh start**

```bash
# Kill any leftover processes
pkill -f "mlx_audio" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true

# Start fresh
./start.sh
```

**Step 2: Test via browser**

1. Open http://localhost:8090
2. Verify voice dropdown shows Kokoro voices (Heart, Bella, Adam, etc.)
3. Select a voice, paste a URL or type text
4. Click Convert
5. Wait for processing to complete
6. Click play — verify audio sounds natural

**Step 3: Test via API**

```bash
# Voices
curl -s http://localhost:8090/api/voices | python3 -m json.tool

# Convert text
curl -s -X POST http://localhost:8090/api/convert \
  -H "Content-Type: application/json" \
  -d '{"text": "Kokoro is a lightweight text to speech model with natural sounding voices.", "voice": "am_adam"}'

# Poll for completion
sleep 15
curl -s http://localhost:8090/api/items?limit=1 | python3 -m json.tool
```

**Step 4: Test different voices**

Try at least 2-3 voices (af_heart, am_adam, bf_emma) to confirm they all work.

**Step 5: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: end-to-end test fixes for Kokoro integration"
```
