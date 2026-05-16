# Play Progress Tracking

## Goal

Track playback progress per item so users can see what's been listened to, what's in progress, and what's safe to delete — across devices (MacBook Air, iPhone, iPad).

## Backend Changes

### DB Schema

Add column to `items` table:

```sql
ALTER TABLE items ADD COLUMN play_position REAL DEFAULT 0;
```

`play_position` stores the **furthest second reached** (high-water mark). This means rewinding doesn't lose progress.

### API

**New endpoint:**

```
PATCH /api/items/{item_id}/progress
Body: {"position": 142.5}
```

Server-side logic: only updates if `position > current play_position`. Returns the stored value.

The existing `GET /api/items` response already includes all columns, so `play_position` will automatically appear in list responses.

## Frontend Changes

### List Item Display

Each completed item shows:

1. **Thin progress bar** (2px) below the title/metadata row
   - Width = `play_position / duration_seconds` as percentage
   - Color: gray when <80%, green when >=80%

2. **Icon states** (right side of each item):
   - Unstarted (`play_position == 0`): play triangle
   - In progress (`0 < play_position < 80%`): play triangle (bar provides context)
   - Finished (`>= 80%`): checkmark icon
   - Currently playing: pause icon (overrides all above while active)

### Interaction

- **Row tap** plays that item (or pauses if already playing)
- Remove the separate small play button — the whole row is the tap target
- Bottom player bar remains for seek/scrub/time display

### Progress Saving

- Track local high-water mark on `timeupdate` events
- Debounced `PATCH` to backend every ~5 seconds
- Also save on pause and `beforeunload`/`visibilitychange`

### Resume Behavior

- When playing an item with `play_position > 0`, set `audio.currentTime` to that position before playing

## "Safe to Delete" Definition

An item is considered fully listened when `play_position / duration_seconds >= 0.80` (80%). At that point the progress bar turns green and the icon becomes a checkmark, signaling it can be safely deleted.

## Non-Goals

- No detail view for items
- No cross-device real-time sync (eventual consistency via API is sufficient)
- No configurable threshold UI
