# NarrateTTS

Local text-to-speech. Paste a URL or text, get audio instantly. Self-hosted — no cloud APIs, no costs, no privacy trade-offs.

Uses [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) via a standalone [mlx-audio](https://github.com/Blaizzy/mlx-audio) service for natural-sounding voices with native Metal/MLX GPU acceleration.

## Quick Start

```bash
# One-time setup (installs dependencies)
./install.sh

# Run
./start.sh
```

App runs at `http://localhost:8090`. It calls a standalone mlx-audio TTS service
set via `TTS_SERVICE_URL` (default `http://macstudio1.lab:8203`).

## How It Works

1. **Submit** text or a URL → Kokoro TTS generates audio in the background
2. **Poll** job status until it's complete
3. **Play** the generated MP3 in your browser

## Capture from your phone (iOS Shortcut)

NarrateTTS can capture straight from the iOS Share Sheet:

1. Open NarrateTTS in **Safari on your iPhone**.
2. Tap the **gear icon → Add to iPhone**. iOS installs the *Send to NarrateTTS*
   shortcut (the API token is baked in — no setup).
3. From any app, **Share → Send to NarrateTTS** to narrate a link or selected text.

The shortcut POSTs to the token-gated `POST /api/shortcut`. If you ever need to
rotate the token, use **Regenerate token** in the gear panel, then re-add the
shortcut on your phone.

> The "Add to iPhone" install signs the shortcut via the macOS `shortcuts` CLI, so
> the server must run on macOS for one-tap install. On other platforms the file is
> served unsigned (requires Settings → Shortcuts → *Allow Untrusted Shortcuts*).

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
NarrateTTS App (port 8090)  →  standalone mlx-audio service (TTS_SERVICE_URL)
FastAPI, web UI, jobs            Kokoro-82M, MLX GPU accel
                                 OpenAI-compatible API
```

The TTS service runs separately (e.g. on a Mac for Metal/MLX GPU acceleration);
NarrateTTS is a pure client and can run anywhere it can reach `TTS_SERVICE_URL`.

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
