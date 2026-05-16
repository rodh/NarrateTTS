# Skip & Speed Controls Design

## Problem

The audio player has play/pause and progress tracking but no way to skip through content or adjust playback speed.

## Goal

Add skip-back-30s, skip-forward-30s, and playback speed controls (0.75x, 1x, 1.25x, 1.5x, 2x) to the audio player UI. Speed persists across tracks and sessions.

## Constraints

- Skip increments fixed at 30 seconds
- Speed preference persists across tracks and sessions
- Must not break existing play/pause, progress tracking, or row-tap-to-play

## Design

### UI Layout

Player bar changes from:

```
[play/pause]    Title
                0:00 ─────── 3:45
```

To:

```
[back30] [play/pause] [fwd30]    Title              [1x]
                                  0:00 ─────── 3:45
```

- Skip buttons flank the play/pause button (smaller, no background fill)
- Speed button at far right, shows current speed text (e.g. "1x", "1.5x")
- Tap speed button to cycle: 1x -> 1.25x -> 1.5x -> 2x -> 0.75x -> 1x

### Skip Behavior

- Back: `audio.currentTime = Math.max(0, audio.currentTime - 30)`
- Forward: `audio.currentTime = Math.min(audio.duration, audio.currentTime + 30)`
- If skip forward reaches duration, trigger ended behavior (save progress, reset icon)
- Skip updates high-water mark if new position exceeds it

### Speed Persistence

- Stored in `localStorage` key `narrateTTS_playbackSpeed`
- Applied to `audio.playbackRate` on every `playItem()` call
- Default: 1.0 if no stored value

### Mobile Responsiveness

- Skip buttons use compact SVG icons (no text labels)
- Speed button shows minimal text ("1x", "1.25x", etc.)
- All controls fit within existing player bar height
