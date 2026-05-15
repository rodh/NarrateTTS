# Design: Replace Piper TTS with Kokoro TTS

## Problem
Piper TTS voice quality is too robotic/synthetic for long-form article narration.

## Decision
Replace Piper with Kokoro-82M via `mlx-audio`, which provides native Apple Silicon (MLX) acceleration and significantly more natural voices.

## Constraints
- M3 Mac, local-only, no cloud APIs
- Long-form articles (1000+ words) are the primary use case
- 1-2 minute generation time is acceptable
- A few voice options needed (male/female, US/UK)

## Why Kokoro
- 82M params — fast, ~500MB footprint
- Native MLX support for Apple Silicon via `mlx-audio` / `kokoro-mlx`
- 44% win rate on TTS Arena V2 (competitive with much larger models)
- ~10 English voices (male/female, US/UK accents)
- Auto-chunking handles long text natively
- Counterargument considered: Orpheus (3B) sounds more human, but requires CUDA/vllm (bad fit for M3), has stitching artifacts on long text

## Architecture

```
NarrateTTS App (port 8090)  →  mlx-audio server (port 8100)
FastAPI, web UI, jobs            Kokoro-82M, MLX GPU accel
                                 OpenAI-compatible API
```

Both run natively (not Docker) to leverage Metal/MLX. Docker can't access Apple GPU.

## Changes

### Remove
- `tts-service/` directory (replaced by mlx-audio server)
- `piper-tts` dependency
- Piper voice resolution code, model download logic
- WAV→MP3 ffmpeg conversion (mlx-audio returns MP3 directly)
- 2500-char text truncation (Kokoro handles long text)

### Modify
- `app/main.py`: `_process_tts()` calls `POST /v1/audio/speech` with `{"input": text, "voice": voice, "response_format": "mp3"}`
- `app/main.py`: `/api/voices` returns Kokoro voice list
- `app/tts_engine.py`: Replace `PiperEngine` with `KokoroEngine` using `kokoro-mlx` directly (local fallback)
- `requirements.txt`: Replace `piper-tts` with `mlx-audio`
- `start.sh`: Launch mlx-audio server + main app
- `docker-compose.yml`: Remove tts-service, update narrate-tts
- `index.html`: Replace voice list with Kokoro voices, default to `af_heart`
- `README.md`: Update setup instructions

### Kokoro Voices
| ID | Display Name |
|----|-------------|
| af_heart | Heart (F) |
| af_bella | Bella (F) |
| af_nicole | Nicole (F) |
| af_sarah | Sarah (F) |
| am_adam | Adam (M) |
| am_michael | Michael (M) |
| bf_emma | Emma (F, UK) |
| bm_george | George (M, UK) |

Default: `af_heart`

### API Contract (mlx-audio server)
```
POST /v1/audio/speech
Content-Type: application/json

{"model": "kokoro", "input": "text here", "voice": "af_heart", "response_format": "mp3"}

→ Returns: audio/mpeg body
```
