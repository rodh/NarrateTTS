# Ideation: NarrateTTS — Local Text-to-Speech Web App

## Problem
User wants to convert text or URLs into listenable audio locally, without cloud APIs, costs, or privacy trade-offs.

## Who
Single user, personal use, self-hosted on their own Mac.

## Constraints
- Open-source TTS only — no cloud providers
- Runs locally on M3 Mac
- Web app as primary interface, API as secondary
- Output: MP3 + in-browser streaming playback
- Personal scale — no multi-user, no auth complexity needed

## Triggers / timing
User encounters long articles, docs, or text they want to listen to instead of read. Ad-hoc, on-demand usage.

## Success criteria
- **Good enough:** Paste text or URL → get audio instantly, play in browser
- **Great:** Fast TTS inference on M3, clean extraction from arbitrary URLs, smooth streaming playback, minimal config

## What we know
- M3 Mac with Metal/CoreML support
- Local-first architecture
- Open-source TTS models (Piper, Coqui, Bark-style, etc.)
- Web UI + local API

## Open territory
- Which TTS model strikes the right balance of quality vs speed on M3?
- How to handle URL extraction robustly across different site types?
- Should the app bundle models or let user pick?
- Single-turn conversion vs persistent queue/history?
