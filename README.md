# NarrateTTS

Local text-to-speech. Paste a URL or text, get audio instantly. Runs on your M3 Mac — no cloud APIs, no costs, no privacy trade-offs.

## Quick Start

```bash
docker compose up -d
```

API runs at `http://localhost:8000`.

## How It Works

1. **Submit** text or a URL → TTS generates audio in the background
2. **Poll** job status until it's complete
3. **Play** the generated MP3 in your app

## API Endpoints

### `POST /api/convert`
Submit text or a URL for conversion. Returns `{ id, status: "queued" }`.

Body: `{ text: "...", voice: "en_US-lessac-medium" }` or `{ url: "https://...", voice: "..." }`

### `GET /api/items?limit=50&offset=0`
List all conversion jobs. Returns array of items with `id`, `title`, `status`, `source_url`, `word_count`.

### `GET /api/items/{id}`
Get a single job. Status is one of: `"queued"`, `"processing"`, `"completed"`, `"error"`.

### `GET /api/voices`
List available Piper voices. Returns `{ voices: ["en_US-lessac-medium", "en_US-arctic-medium", ...] }`.

### `GET /audio/{filename}`
Serve a completed audio file. Use this as the `src` for an `<audio>` element or `new Audio()`.

## Integration Pattern

1. Call `/api/voices` on app init to populate a voice selector
2. Submit text or URL via `/api/convert`
3. Poll `/api/items/{id}` every 2-3 seconds until status is `"completed"` or `"error"`
4. Play the audio via `/audio/{filename}`

```
UI ──POST /api/convert──▶ NarrateTTS (queues job)
     │
UI ◀─GET /api/items/{id}── Poll until completed
     │
UI ◀─GET /audio/{filename}── Play MP3
```

## Frontend Setup

Add to your `.env`:

```
VITE_TTS_URL=http://localhost:8000
```

CORS is already enabled — your Vite dev server on any port will work.
