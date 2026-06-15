# Slice 1 — Visual Language + Front-end Restructure — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the existing app in a warm, rounded, orange-accented visual language (light + dark) and split the single `index.html` into a no-build static module bundle — with **zero behavior changes**.

**Architecture:** Move the theme to `static/css/app.css` (retuned CSS custom properties + a few component polish rules), keep the Tailwind CDN for layout utilities, and split the inline `<script>` into ES modules under `static/js/`. Inline `onclick=` handlers in the markup are preserved by exposing the relevant functions on `window` from `main.js`.

**Tech Stack:** FastAPI (serves `/` and `/static`), Tailwind CDN, vanilla ES modules, CSS custom properties.

**Spec:** `docs/plans/2026-06-15-player-forward-redesign-design.md` (Slice 1).

**Behavior source of truth:** the current `index.html` on this branch. Every existing feature must keep working: capture/convert, voices, library render + search, status/progress indicators, retry/reset/delete, playlist picker, playlists tab (create/delete/view/remove), feed URL copy + OPML, settings panel (token reveal/copy/regenerate, Add to iPhone), player (play/pause/seek/skip ±30/speed cycle/progress save/mediaSession), and polling.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `static/css/app.css` (new) | Theme tokens (light/dark) + base + component polish (cards, buttons, pills, inputs, player). Replaces the inline `<style>`. |
| `index.html` (modify) | Shell markup only. Drop the inline `<style>` (link `app.css`) and the inline `<script>` (load `main.js` as a module). Keep existing markup/classes; add rounding/accent where noted. |
| `static/js/api.js` (new) | `fetch` wrappers for the existing endpoints. |
| `static/js/player.js` (new) | Audio element, play/pause/seek/skip/speed, progress save, mediaSession. |
| `static/js/library.js` (new) | Library render + search + item actions (retry/reset/delete/playlist-picker). |
| `static/js/playlists.js` (new) | Playlists tab: list/create/delete/view/remove, feed URL copy, OPML. |
| `static/js/settings.js` (new) | Settings panel: token load/reveal/copy/regenerate. |
| `static/js/main.js` (new) | Imports modules, exposes handler functions on `window`, runs init (loadVoices/loadItems/polling, speed label, visibility/beforeunload listeners, tab switching, add/settings panel toggles). |

---

## Task 1: Theme + component CSS

**Files:**
- Create: `static/css/app.css`

- [ ] **Step 1: Write `static/css/app.css`**

```css
:root {
  --accent: #f1582c;
  --accent-press: #d8451c;
  --accent-text: #ffffff;
  --bg: #faf9f7;
  --surface: #ffffff;
  --surface-2: #f3f1ee;
  --bg-input: #f3f1ee;
  --bg-button: #ece9e4;
  --bg-button-hover: #e0dcd5;
  --border: #ececec;
  --border-subtle: rgba(0,0,0,0.06);
  --border-input: #dcd8d2;
  --border-focus: #b8b2a8;
  --text: #1a1a1a;
  --text-secondary: #4b5563;
  --text-muted: #6b7280;
  --text-faint: #9ca3af;
  --text-accent: #1a1a1a;
  --scrollbar: #d8d4cd;
  --hover-bg: #f3f1ee;
  --radius: 18px;
  --radius-sm: 12px;
  --shadow: 0 1px 3px rgba(0,0,0,0.08);
}
@media (prefers-color-scheme: dark) {
  :root {
    --accent: #ff6a3d;
    --accent-press: #f1582c;
    --accent-text: #1a1a1a;
    --bg: #0f0f10;
    --surface: #1a1a1c;
    --surface-2: #242427;
    --bg-input: #1f1f22;
    --bg-button: #2a2a2e;
    --bg-button-hover: #36363b;
    --border: #2a2a2e;
    --border-subtle: rgba(255,255,255,0.07);
    --border-input: #3a3a40;
    --border-focus: #57575e;
    --text: #ececec;
    --text-secondary: #9ca3af;
    --text-muted: #8b8b93;
    --text-faint: #5c5c63;
    --text-accent: #ffffff;
    --scrollbar: #3a3a40;
    --hover-bg: #1f1f22;
    --shadow: 0 1px 3px rgba(0,0,0,0.4);
  }
}
html { height: 100%; }
body { background: var(--bg); color: var(--text); -webkit-font-smoothing: antialiased; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--scrollbar); border-radius: 3px; }

/* Component polish (used by current markup + future screens) */
.item-card { transition: background 0.15s; border-radius: var(--radius-sm); }
.item-card:hover { background: var(--hover-bg); }

/* Accent button: any element with .btn-accent */
.btn-accent { background: var(--accent); color: var(--accent-text); border-radius: 999px; }
.btn-accent:hover { background: var(--accent-press); }

/* Rounded surfaces */
.surface { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); }
.pill { border-radius: 999px; }
```

- [ ] **Step 2: Verify the file is valid CSS**

Run: `.venv/bin/python -c "open('static/css/app.css').read(); print('ok')"`
Expected: `ok` (file exists and reads). (No CSS compiler; correctness is verified visually in Task 5.)

- [ ] **Step 3: Commit**

```bash
git add static/css/app.css
git commit -m "feat(ui): add warm/orange theme tokens + component css"
```

---

## Task 2: Link `app.css` and re-skin accents in `index.html`

**Files:**
- Modify: `index.html` (head + accent/rounding tweaks)

- [ ] **Step 1: Replace the inline `<style>` block with a stylesheet link**

In `index.html` `<head>`, delete the entire `<style>…</style>` block (the `:root`
vars, dark-mode block, and scrollbar/item-card rules — they now live in `app.css`)
and add, after the Tailwind script tag:

```html
    <link rel="stylesheet" href="/static/css/app.css">
```

- [ ] **Step 2: Re-skin the primary actions to the orange accent**

In `index.html`, give the primary action buttons the accent by changing their
Tailwind background classes to the `.btn-accent` class. Specifically:
- The **Convert** button (`id="convert-btn"`): replace its `bg-[var(--bg-button-hover)] hover:bg-[var(--bg-button)] text-[var(--text-accent)]` classes with `btn-accent`.
- The **player play/pause** button (`id="play-btn"`): replace `bg-[var(--accent-bg)] text-[var(--accent-text)]` with `btn-accent`.
- The **Create** playlist button and **Add to iPhone** link: add `btn-accent` (keep padding utilities).

Leave all other markup, ids, and `onclick` handlers unchanged.

- [ ] **Step 3: Commit**

```bash
git add index.html
git commit -m "feat(ui): link app.css and apply orange accent to primary actions"
```

---

## Task 3: Split player + api into modules

**Files:**
- Create: `static/js/api.js`, `static/js/player.js`

- [ ] **Step 1: Create `static/js/api.js`**

Thin wrappers around the existing endpoints. Export functions used by the other
modules:

```js
export async function getItems(limit = 100) {
  const r = await fetch(`/api/items?limit=${limit}`);
  return r.json();
}
export async function getPlaylistMap() {
  const r = await fetch('/api/items/playlist-map');
  return r.json();
}
export async function getVoices() {
  const r = await fetch('/api/voices');
  return r.json();
}
export async function postConvert(body) {
  return fetch('/api/convert', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}
export async function patchProgress(id, position) {
  return fetch(`/api/items/${id}/progress`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ position }) });
}
export async function deleteItem(id) { return fetch(`/api/items/${id}`, { method: 'DELETE' }); }
export async function retryItem(id) { return fetch(`/api/items/${id}/retry`, { method: 'POST' }); }
export async function getPlaylists() { return (await fetch('/api/playlists')).json(); }
export async function createPlaylist(name) { return fetch('/api/playlists', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) }); }
export async function deletePlaylist(id) { return fetch(`/api/playlists/${id}`, { method: 'DELETE' }); }
export async function getPlaylistItems(id) { return (await fetch(`/api/playlists/${id}/items`)).json(); }
export async function addItemToPlaylist(pid, itemId) { return fetch(`/api/playlists/${pid}/items`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ item_id: itemId }) }); }
export async function removeItemFromPlaylist(pid, itemId) { return fetch(`/api/playlists/${pid}/items/${itemId}`, { method: 'DELETE' }); }
export async function getItemPlaylists(id) { return (await fetch(`/api/items/${id}/playlists`)).json(); }
export async function getToken() { return (await fetch('/api/settings/token')).json(); }
export async function regenerateToken() { return (await fetch('/api/settings/token', { method: 'POST' })).json(); }
```

- [ ] **Step 2: Create `static/js/player.js`**

Move the playback code verbatim from the current `index.html` script into this module
and export the handlers and shared state. Port these functions unchanged in behavior:
`playItem, togglePlay, seekTo, skipBack, skipForward, cycleSpeed, getStoredSpeed,
updatePlayerUI, saveProgress, debouncedSaveProgress, resetProgress, formatTime`, plus
the module-scoped state `audio, currentItemId, highWaterMark, saveTimeout` and
`SPEED_OPTIONS`. Use `patchProgress` from `api.js` for the network calls. Export every
function the markup's `onclick`/`oninput` handlers reference (`togglePlay, seekTo,
skipBack, skipForward, cycleSpeed, playItem, resetProgress`) plus a `getCurrentItemId()`
accessor and a `setItems(itemsRef)` so the library module can share the items array.

Keep DOM ids identical (`player, play-btn, play-icon, pause-icon, player-title,
player-progress, player-time, player-duration, speed-btn`).

- [ ] **Step 3: Commit**

```bash
git add static/js/api.js static/js/player.js
git commit -m "refactor(ui): extract api and player modules"
```

---

## Task 4: Split library, playlists, settings, and main

**Files:**
- Create: `static/js/library.js`, `static/js/playlists.js`, `static/js/settings.js`, `static/js/main.js`
- Modify: `index.html` (replace inline `<script>` with module load)

- [ ] **Step 1: Create `static/js/library.js`**

Move the library rendering and item-action code from the current `index.html`:
`loadItems, render, renderPreservingScroll, convert, toggleAddPanel, autoResize,
handleInputKey, escapeHtml, deleteItem (UI wrapper), retryItem (UI wrapper),
showPlaylistPicker, togglePlaylistItem, pollUpdates`, plus shared state `items,
playlistMap`. Use `api.js` for network calls and `player.js` for `playItem`/
`getCurrentItemId`/`resetProgress`. Keep render output identical (same DOM, classes,
status dots, progress ring) so behavior is unchanged. Export `items` access via a
getter, and export the handler functions referenced by inline `onclick`/`oninput`
(`render, convert, toggleAddPanel, autoResize, handleInputKey, deleteItem, retryItem,
showPlaylistPicker, togglePlaylistItem, loadItems, pollUpdates`).

- [ ] **Step 2: Create `static/js/playlists.js`**

Move `loadPlaylists, renderPlaylists, createPlaylist, confirmDeletePlaylist,
viewPlaylist, renderPlaylistDetail, removeFromPlaylist, copyFeedUrl` from the current
`index.html`, unchanged. Use `api.js` for network calls. Export the functions inline
handlers reference (`loadPlaylists, createPlaylist, confirmDeletePlaylist, viewPlaylist,
removeFromPlaylist, copyFeedUrl`).

- [ ] **Step 3: Create `static/js/settings.js`**

Move `loadShortcutToken, renderToken, toggleSettingsPanel, toggleTokenReveal,
copyToken, regenerateToken` and state `shortcutToken, tokenRevealed` from the current
`index.html`, unchanged. Use `api.js` (`getToken`, `regenerateToken`). Export the
functions inline handlers reference.

- [ ] **Step 4: Create `static/js/main.js`**

```js
import * as player from './player.js';
import * as library from './library.js';
import * as playlists from './playlists.js';
import * as settings from './settings.js';

// Inline onclick=/oninput= handlers in index.html call globals, so expose them:
Object.assign(window, player, library, playlists, settings);

// Tab switching (ported from current index.html switchTab)
let currentTab = 'library';
function switchTab(tab) {
  currentTab = tab;
  document.getElementById('library').classList.toggle('hidden', tab !== 'library');
  document.getElementById('playlists-view').classList.toggle('hidden', tab !== 'playlists');
  document.getElementById('tab-library').classList.toggle('border-[var(--text-accent)]', tab === 'library');
  document.getElementById('tab-library').classList.toggle('text-[var(--text-accent)]', tab === 'library');
  document.getElementById('tab-library').classList.toggle('border-transparent', tab !== 'library');
  document.getElementById('tab-library').classList.toggle('text-[var(--text-muted)]', tab !== 'library');
  document.getElementById('tab-playlists').classList.toggle('border-[var(--text-accent)]', tab === 'playlists');
  document.getElementById('tab-playlists').classList.toggle('text-[var(--text-accent)]', tab === 'playlists');
  document.getElementById('tab-playlists').classList.toggle('border-transparent', tab !== 'playlists');
  document.getElementById('tab-playlists').classList.toggle('text-[var(--text-muted)]', tab !== 'playlists');
  if (tab === 'playlists') playlists.loadPlaylists();
}
window.switchTab = switchTab;

document.addEventListener('visibilitychange', () => { if (document.hidden) player.saveProgress(); });
window.addEventListener('beforeunload', player.saveProgress);

// Init (ported from the bottom of current index.html)
library.loadVoices();
library.loadItems().then(() => {
  if (library.hasProcessing()) library.pollUpdates();
});
document.getElementById('speed-btn').textContent = (player.getStoredSpeed() === 1) ? '1x' : player.getStoredSpeed() + 'x';
```

Add `loadVoices` and a `hasProcessing()` helper to `library.js` (ported from the
current init logic). Keep `loadVoices` writing to `#voice-select` and using
`COMMON_VOICES` fallback exactly as today.

- [ ] **Step 5: Replace the inline `<script>` in `index.html`**

Delete the entire inline `<script>…</script>` block and replace with:

```html
    <script type="module" src="/static/js/main.js"></script>
```

- [ ] **Step 6: Commit**

```bash
git add static/js/library.js static/js/playlists.js static/js/settings.js static/js/main.js index.html
git commit -m "refactor(ui): split library/playlists/settings/main into modules"
```

---

## Task 5: Verify the restyled app works end-to-end

**Files:** none (verification)

- [ ] **Step 1: Restart the server**

```bash
OLD=$(lsof -nP -iTCP:8090 -sTCP:LISTEN -t); [ -n "$OLD" ] && kill "$OLD"; sleep 2
cd /Users/rodhoward/NarrateTTS && set -a && source .env && set +a
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8090 > /tmp/narrate_8090.log 2>&1 &
sleep 3 && curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8090/
```
Expected: `200`.

- [ ] **Step 2: Check no module load errors**

```bash
for f in /static/css/app.css /static/js/main.js /static/js/api.js /static/js/player.js /static/js/library.js /static/js/playlists.js /static/js/settings.js; do
  printf "%s -> " "$f"; curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8090$f"; done
```
Expected: all `200`.

- [ ] **Step 3: Manual verification (use the run/verify skill or a browser at http://localhost:8090)**

Confirm every feature still works and now shows the warm/orange rounded look:
- Capture: open add panel (＋), paste text, Convert → item appears, polls to completed.
- Library: search filters; status dots/progress ring render; play an item (orange play button) → player bar appears, play/pause, seek, skip ±30, speed cycle, progress persists on pause/reload.
- Item actions: add-to-playlist picker, reset progress, delete, retry on an error item.
- Playlists tab: list, create, view detail, remove item, delete playlist, Copy URL, Export OPML.
- Settings (gear): token shows masked, reveal/copy, regenerate, Add to iPhone downloads.
- Dark mode: toggle OS appearance → both themes look right.

- [ ] **Step 4: Run the backend suite (must stay green — no backend changes)**

Run: `.venv/bin/python -m pytest -q`
Expected: `26 passed`.

- [ ] **Step 5: Commit any fixes found during verification**

```bash
git add -A && git commit -m "fix(ui): slice 1 verification fixes"
```
(Skip if nothing needed fixing.)

---

## Self-review notes

- **Spec coverage (Slice 1):** theme tokens + component css (Task 1), accent applied
  (Task 2), front-end split into the module layout from the spec (Tasks 3–4), behavior
  preserved + verified (Task 5). No new screens (correct for Slice 1).
- **No behavior change:** all functions are *moved*, not rewritten; render output and
  DOM ids are identical, so the existing flows keep working. The only functional risk
  is the ES-module/`onclick` boundary — handled by `Object.assign(window, …)` in
  `main.js`.
- **Tailwind retained** for layout utilities; `app.css` owns theme + component polish.
- Backend untouched → pytest stays at 26 passing.
