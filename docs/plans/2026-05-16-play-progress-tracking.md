# Play Progress Tracking Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Track playback high-water mark per item, display progress bars and icon states in the list, enable row-tap play/pause with synced icons.

**Architecture:** Add `play_position` column to SQLite `items` table. New PATCH endpoint saves position (high-water-mark only). Frontend tracks position on timeupdate, debounces saves, renders progress bar + icon states per item.

**Tech Stack:** FastAPI (Python), SQLite, vanilla JS, Tailwind CSS

---

### Task 1: Add play_position column to DB

**Files:**
- Modify: `app/db.py`

**Step 1: Add column to schema and migration logic**

In `app/db.py`, update `init_db()` to add the column if it doesn't exist (SQLite doesn't support `ADD COLUMN IF NOT EXISTS`, so use a try/except or check pragma):

```python
# After the existing CREATE TABLE/INDEX statements in init_db():
try:
    conn.execute("ALTER TABLE items ADD COLUMN play_position REAL DEFAULT 0")
except Exception:
    pass  # Column already exists
```

Also add `"play_position"` to the `allowed` set in `update_item()`, and add a new function:

```python
def update_play_position(item_id: int, position: float):
    """Update play_position only if new value exceeds current (high-water mark)."""
    conn = get_connection()
    conn.execute(
        "UPDATE items SET play_position = ?, updated_at = datetime('now') WHERE id = ? AND (play_position IS NULL OR play_position < ?)",
        (position, item_id, position),
    )
    conn.commit()
    conn.close()
```

**Step 2: Verify**

Run: `python -c "from app.db import init_db; init_db(); print('OK')"`

Expected: OK, no errors. Check that existing DB gains the column.

**Step 3: Commit**

```bash
git add app/db.py
git commit -m "feat: add play_position column with high-water-mark update"
```

---

### Task 2: Add PATCH /api/items/{item_id}/progress endpoint

**Files:**
- Modify: `app/main.py`

**Step 1: Add the endpoint**

```python
from app.db import update_play_position  # add to existing import

@app.patch("/api/items/{item_id}/progress")
async def api_update_progress(item_id: int, payload: dict):
    position = payload.get("position")
    if position is None or not isinstance(position, (int, float)) or position < 0:
        raise HTTPException(status_code=400, detail="Invalid position")
    update_play_position(item_id, float(position))
    return {"ok": True}
```

**Step 2: Verify**

Start the server and test with curl:

```bash
# Create a test item first (or use existing), then:
curl -X PATCH http://127.0.0.1:8090/api/items/1/progress \
  -H "Content-Type: application/json" \
  -d '{"position": 45.2}'

# Verify it saved:
curl http://127.0.0.1:8090/api/items/1 | python -m json.tool | grep play_position
```

Expected: `"play_position": 45.2`

Test high-water mark (sending a lower value should not overwrite):

```bash
curl -X PATCH http://127.0.0.1:8090/api/items/1/progress \
  -H "Content-Type: application/json" \
  -d '{"position": 20.0}'

curl http://127.0.0.1:8090/api/items/1 | python -m json.tool | grep play_position
```

Expected: still `"play_position": 45.2`

**Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add PATCH endpoint for play position progress"
```

---

### Task 3: Frontend — progress bar and icon states in list

**Files:**
- Modify: `index.html`

**Step 1: Add CSS for progress bar**

In the `<style>` block, add:

```css
.progress-bar {
    height: 2px;
    border-radius: 1px;
    transition: width 0.3s ease;
}
```

**Step 2: Update the render() function**

Replace the `actions` variable logic and add progress bar to each item card. The key changes:

1. Compute progress percentage: `const pct = (item.duration_seconds > 0) ? (item.play_position || 0) / item.duration_seconds : 0;`
2. Determine if finished: `const isFinished = pct >= 0.8;`
3. Determine if currently playing: `const isPlaying = currentItemId === item.id && audio && !audio.paused;`
4. Choose icon: playing → pause, finished → checkmark, default → play triangle
5. Add progress bar HTML after the metadata row

The icon markup:

```javascript
let iconSvg;
if (item.status !== 'completed' || !item.audio_path) {
    iconSvg = ''; // no icon for non-completed items
} else if (isPlaying) {
    iconSvg = `<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>`;
} else if (isFinished) {
    iconSvg = `<svg class="w-5 h-5 text-green-400" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>`;
} else {
    iconSvg = `<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><polygon points="5,3 19,12 5,21"/></svg>`;
}
```

The progress bar (inside item card, after metadata div):

```javascript
let progressHtml = '';
if (item.status === 'completed' && item.duration_seconds > 0) {
    const barPct = Math.min(pct * 100, 100);
    const barColor = isFinished ? 'bg-green-500' : 'bg-gray-500';
    progressHtml = `<div class="w-full bg-gray-800 rounded-full mt-1.5"><div class="progress-bar ${barColor}" style="width: ${barPct}%"></div></div>`;
}
```

**Step 3: Make row tap trigger play**

Change the row's `onclick` from `selectItem(id)` to play logic. For completed items, tapping the row plays/pauses. Update the `onclick`:

```javascript
const rowAction = (item.status === 'completed' && item.audio_path)
    ? `onclick="playItem(${item.id}, '${item.audio_path.split('/').pop()}')"`
    : '';
```

Remove the separate play button from actions — the icon is now informational (part of the row, not a separate button).

**Step 4: Verify**

Reload the page in browser. Items with `play_position > 0` should show a progress bar. Tapping a row should start playback.

**Step 5: Commit**

```bash
git add index.html
git commit -m "feat: add progress bars, icon states, and row-tap playback"
```

---

### Task 4: Frontend — debounced progress saving and resume

**Files:**
- Modify: `index.html`

**Step 1: Add progress tracking state and save logic**

Add these variables near the top of the script:

```javascript
let highWaterMark = 0;
let saveTimeout = null;
```

Add save function:

```javascript
function saveProgress() {
    if (!currentItemId || highWaterMark <= 0) return;
    fetch(`/api/items/${currentItemId}/progress`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ position: highWaterMark })
    }).catch(e => console.error('Save progress failed:', e));
}

function debouncedSaveProgress() {
    if (saveTimeout) clearTimeout(saveTimeout);
    saveTimeout = setTimeout(saveProgress, 5000);
}
```

**Step 2: Update timeupdate handler to track high-water mark**

Modify `updatePlayerUI()`:

```javascript
function updatePlayerUI() {
    if (!audio || !audio.duration) return;
    const pct = (audio.currentTime / audio.duration) * 100;
    document.getElementById('player-progress').value = pct;
    document.getElementById('player-time').textContent = formatTime(audio.currentTime);
    document.getElementById('player-duration').textContent = formatTime(audio.duration);

    // Track high-water mark
    if (audio.currentTime > highWaterMark) {
        highWaterMark = audio.currentTime;
        debouncedSaveProgress();
    }
}
```

**Step 3: Save on pause and page unload**

In `togglePlay()`, after `audio.pause()`:

```javascript
saveProgress();
```

Add at the bottom of the script:

```javascript
document.addEventListener('visibilitychange', () => {
    if (document.hidden) saveProgress();
});
window.addEventListener('beforeunload', saveProgress);
```

**Step 4: Resume from saved position**

In `playItem()`, after creating the Audio object and before `audio.play()`:

```javascript
// Reset high-water mark for this item
const item = items.find(i => i.id === id);
highWaterMark = item?.play_position || 0;

// Resume from saved position
if (highWaterMark > 0) {
    audio.currentTime = highWaterMark;
}
```

Note: `audio.currentTime` can be set before play on most browsers, but to be safe with streaming, also add a `canplay` listener as fallback:

```javascript
if (highWaterMark > 0) {
    audio.addEventListener('canplay', function seekOnce() {
        if (audio.currentTime < highWaterMark) {
            audio.currentTime = highWaterMark;
        }
        audio.removeEventListener('canplay', seekOnce);
    });
}
```

**Step 5: Re-render list when progress changes**

After `saveProgress()` succeeds, update the local items array so the progress bar reflects reality without a full reload:

```javascript
function saveProgress() {
    if (!currentItemId || highWaterMark <= 0) return;
    // Update local state immediately
    const item = items.find(i => i.id === currentItemId);
    if (item && highWaterMark > (item.play_position || 0)) {
        item.play_position = highWaterMark;
    }
    fetch(`/api/items/${currentItemId}/progress`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ position: highWaterMark })
    }).catch(e => console.error('Save progress failed:', e));
}
```

Also re-render on play/pause state changes so the icon updates (call `render()` after play/pause toggling).

**Step 6: Verify**

1. Play an item partway, pause — check progress bar appears
2. Reload page — progress bar persists
3. Play again — resumes from saved position
4. Listen past 80% — bar turns green, icon becomes checkmark
5. Open on different device — same progress shows

**Step 7: Commit**

```bash
git add index.html
git commit -m "feat: debounced progress saving, resume, and list sync"
```

---

### Task 5: Handle edge cases and polish

**Files:**
- Modify: `index.html`

**Step 1: Handle audio ended event**

When audio ends naturally, set high-water mark to duration and save:

```javascript
audio.addEventListener('ended', () => {
    highWaterMark = audio.duration;
    saveProgress();
    document.getElementById('play-icon').classList.remove('hidden');
    document.getElementById('pause-icon').classList.add('hidden');
    render(); // Update icon to checkmark
});
```

**Step 2: Ensure render() reflects current play state**

The `render()` function needs access to `currentItemId` and `audio.paused` to determine icon state. These are already global, so no changes needed — just ensure `render()` is called after state changes (play, pause, ended).

**Step 3: Prevent re-render from resetting scroll position**

Store and restore scroll position around renders triggered by playback state changes:

```javascript
function renderPreservingScroll() {
    const library = document.getElementById('library');
    const scrollTop = library.scrollTop;
    render();
    library.scrollTop = scrollTop;
}
```

Use `renderPreservingScroll()` instead of `render()` in play/pause/ended handlers.

**Step 4: Verify**

1. Play to end — checkmark appears, progress saved as 100%
2. Scroll position doesn't jump when icon updates during playback
3. Items still deletable (delete button still works alongside row tap)

**Step 5: Commit**

```bash
git add index.html
git commit -m "fix: handle audio ended, preserve scroll on re-render"
```
