# NarrateTTS

Local text-to-speech. Paste a URL or text, get audio instantly. Runs on Apple Silicon — no cloud APIs, no costs, no privacy trade-offs.

Uses [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) via [mlx-audio](https://github.com/Blaizzy/mlx-audio) for natural-sounding voices with native Metal/MLX GPU acceleration.

## Quick Start

```bash
# One-time setup (installs dependencies, downloads Kokoro model ~500MB)
./install.sh

# Run
./start.sh
```

App runs at `http://localhost:8090`. TTS server runs at `http://localhost:8100`.

## How It Works

1. **Submit** text or a URL → Kokoro TTS generates audio in the background
2. **Poll** job status until it's complete
3. **Play** the generated MP3 in your browser

## Available Voices

| Voice | ID |
|-------|-----|
| Heart (F) | `af_heart` |
| Bella (F) | `af_bella` |
| Nicole (F) | `af_nicole` |
| Sarah (F) | `af_sarah` |
| Sky (F) | `af_sky` |
| Adam (M) | `am_adam` |
| Michael (M) | `am_michael` |
| Emma (F, UK) | `bf_emma` |
| Isabella (F, UK) | `bf_isabella` |
| George (M, UK) | `bm_george` |
| Lewis (M, UK) | `bm_lewis` |

## API Endpoints

### `POST /api/convert`
Submit text or a URL for conversion. Returns `{ id, status: "queued" }`.

Body: `{ text: "...", voice: "af_heart" }` or `{ url: "https://...", voice: "..." }`

### `GET /api/items?limit=50&offset=0`
List all conversion jobs. Returns array of items with `id`, `title`, `status`, `source_url`, `word_count`.

### `GET /api/items/{id}`
Get a single job. Status is one of: `"queued"`, `"processing"`, `"completed"`, `"error"`.

### `GET /api/voices`
List available voices. Returns `{ voices: [{id: "af_heart", name: "Heart (F)"}, ...] }`.

### `GET /audio/{filename}`
Serve a completed audio file.

## Architecture

```
NarrateTTS App (port 8090)  →  mlx-audio server (port 8100)
FastAPI, web UI, jobs            Kokoro-82M, MLX GPU accel
                                 OpenAI-compatible API
```

Both services run natively on Apple Silicon for full Metal/MLX GPU acceleration. Docker is available as a fallback but uses CPU inference (no MLX in Docker on Mac).

## Integration Pattern

```
UI ──POST /api/convert──▶ NarrateTTS (queues job)
     │
UI ◀─GET /api/items/{id}── Poll until completed
     │
UI ◀─GET /audio/{filename}── Play MP3
```

## Requirements

- Apple Silicon Mac (M1/M2/M3/M4)
- Python 3.11+
- ~500MB disk for Kokoro model (auto-downloaded on install)
