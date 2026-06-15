# Replace bundled TTS server with standalone service

**Date:** 2026-06-14

## Goal

Remove the in-app mlx-audio TTS server and the in-process `KokoroEngine`
fallback. NarrateTTS becomes a pure client of a standalone mlx-audio (Kokoro)
service running at `http://macstudio1.lab:8203`.

## Context

Previously `start.sh` launched `python -m mlx_audio.server` on port 8100 and the
app talked to it via `TTS_SERVICE_URL`. An in-process `KokoroEngine`
(`app/tts_engine.py`) served as a fallback when `TTS_SERVICE_URL` was empty.

The standalone service was verified to expose the identical OpenAI-compatible
API (`POST /v1/audio/speech`), accept all fields the app sends (`model`,
`input`, `voice`, `response_format`, `lang_code`, `verbose`), and return a
playable 128kbps MP3. No request-shape changes are needed — only the URL.

## Changes

1. **`app/main.py`** — Remove the `else:` local-engine fallback branch
   (incl. the WAV→MP3 ffmpeg step). The remote call becomes unconditional. Add a
   guard so an empty `TTS_SERVICE_URL` fails loudly. Update the `/api/voices`
   import to the new `KOKORO_VOICES` location.
2. **`app/tts_engine.py`** — Delete the file. Move `KOKORO_VOICES` into
   `config.py`; the `KokoroEngine` class and `mlx_audio` import are removed.
3. **`app/config.py`** — Default `TTS_SERVICE_URL` to
   `http://macstudio1.lab:8203` (env-overridable). Add `KOKORO_VOICES`.
4. **`start.sh`** — Remove the `mlx_audio.server` launch, `TTS_PID`, its cleanup
   `kill`, and the port-8100 echo. Export the new `TTS_SERVICE_URL`.
5. **`requirements.txt`** — Remove `mlx-audio` and the now-unused inference
   deps: `webrtcvad`, `misaki`, `num2words`, `spacy`, `phonemizer`,
   `setuptools<81`.
6. **`install.sh`** — Remove the Kokoro model pre-download and the spacy model
   download.
7. **`README.md`** — Update architecture description to reference the external
   service.

## Out of scope

- `Dockerfile` / `docker-compose.yml` — they only run uvicorn on 8090 and never
  launched the TTS server.
- `docs/plans/*` historical records — left as-is.

## Verification

- App starts with mlx-audio uninstalled.
- `/api/voices` returns the voice list.
- A real `/api/convert` job produces a playable MP3 from the remote service.
