# Slice 6 — Continuous Contextual Queue — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Playing an item plays through the list it came from (a feed, Home's Recent, or the Library): when one finishes, the next auto-plays. Add lock-screen next/prev and an "Up next" list in Now-Playing.

**Architecture:** `player.js` keeps a `lists` registry (key → ordered playable items) and a `queue`/`queueIndex`. Each screen registers its ordered list and item clicks call `playFromList(key, index)`. The existing `playItem` body is refactored into an internal `_play(id, file)`; `playItem` becomes a single-item wrapper (no queue) and `playFromList` sets the queue then calls `_play`. `ended` advances the queue; `mediaSession` next/prev and the Now-Playing queue button use it.

**Tech Stack:** vanilla ES modules, mediaSession API.

**Spec:** `docs/plans/2026-06-15-player-forward-redesign-design.md` (Player & queue model).

---

## Task 1: Queue model in player.js

**Files:** Modify `static/js/player.js`

Read player.js first. Refactor without changing single-play behavior.

- [ ] **Step 1: Refactor `playItem` → internal `_play`, add queue state + entry points**

- Rename the body of the current `playItem(id, file)` to an internal
  `function _play(id, audioFile) { … }` (keep EVERYTHING it does: pause/replace audio,
  resume from saved position, mediaSession metadata, UI show, waveform compute, progress
  save of the previous item, render refresh).
- Add module state and functions:

```js
const lists = {};         // key -> ordered array of playable item objects
let queue = [];
let queueIndex = -1;

export function setList(key, arr) {
  lists[key] = (arr || []).filter(i => i.status === 'completed' && i.audio_path);
}

function _fileOf(item) { return item.audio_path ? item.audio_path.split('/').pop() : ''; }

export function playFromList(key, index) {
  const arr = lists[key] || [];
  if (!arr.length) return;
  queue = arr;
  queueIndex = Math.max(0, Math.min(index, arr.length - 1));
  const item = queue[queueIndex];
  _play(item.id, _fileOf(item));
}

export function playItem(id, file) {   // single play, clears any queue context
  queue = []; queueIndex = -1;
  _play(id, file);
}

export function nextInQueue() {
  if (queueIndex >= 0 && queueIndex < queue.length - 1) {
    queueIndex++; const it = queue[queueIndex]; _play(it.id, _fileOf(it)); return true;
  }
  return false;
}
export function prevInQueue() {
  if (queueIndex > 0) { queueIndex--; const it = queue[queueIndex]; _play(it.id, _fileOf(it)); return true; }
  return false;
}
export function upNext() { return queueIndex >= 0 ? queue.slice(queueIndex + 1) : []; }
```

- [ ] **Step 2: Autoplay next on `ended`**

In the `ended` handler inside `_play` (formerly `playItem`), after saving progress and
updating icons, attempt to advance:

```js
  // existing: save progress, set play icon, render refresh
  nextInQueue();  // if there is a next item, it auto-plays; otherwise playback stops
```

- [ ] **Step 3: mediaSession next/prev**

Where `_play` sets `navigator.mediaSession` action handlers, add:

```js
  navigator.mediaSession.setActionHandler('nexttrack', () => nextInQueue());
  navigator.mediaSession.setActionHandler('previoustrack', () => prevInQueue());
```

- [ ] **Step 4: Export the new functions**

Ensure `setList, playFromList, nextInQueue, prevInQueue, upNext` are exported (so
`main.js`'s `Object.assign(window, player, …)` exposes them). `playItem` stays exported.

- [ ] **Step 5: Commit**

```bash
git add static/js/player.js
git commit -m "feat(ui): contextual play queue with autoplay-next + media next/prev"
```

---

## Task 2: Wire screens to play within their list + Up-next view

**Files:** Modify `static/js/library.js`, `static/js/home.js`, `static/js/playlists.js`, `index.html`, `static/css/app.css`

- [ ] **Step 1: Library plays within the filtered list**

In `static/js/library.js`, import `setList, playFromList` from `./player.js`. In
`render()`, after computing the `filtered` array, call `setList('library', filtered)`.
Change each item row's play action from `playItem(${item.id}, '${audioFile}')` to
`playFromList('library', ${index})` (use the row's index within `filtered`). Keep the
in-progress/status visuals unchanged.

- [ ] **Step 2: Home Recent plays within the recent list; hero stays single**

In `static/js/home.js`, import `setList, playFromList` from `./player.js`. After
building `recent`, call `setList('recent', recent)`. Change each recent row's onclick to
`playFromList('recent', ${index})`. The Continue-listening hero keeps
`playItem(cont.id, file)` (single resume — it's not part of a list).

- [ ] **Step 3: Feed-detail plays within the feed**

In `static/js/playlists.js` `renderFeedDetail`, import `setList, playFromList`, call
`setList('feed', items)` after fetching, and change each item's play onclick to
`playFromList('feed', ${index})`.

- [ ] **Step 4: "Up next" in Now-Playing**

In `index.html`, inside the `#now-playing` overlay after the `.np-ctrls` div, add:

```html
    <div id="np-queue" class="np-queue hidden"></div>
```

Add CSS to `static/css/app.css`:

```css
.np-queue { margin-top:16px; max-height:30vh; overflow-y:auto; border-top:1px solid var(--border); padding-top:10px; }
.np-queue .qrow { display:flex; align-items:center; gap:10px; padding:7px 0; }
.np-queue .qrow .qt { font-size:13px; font-weight:600; }
.np-queue .qrow .qm { font-size:11px; color:var(--text-muted); }
```

In `static/js/player.js`, change the overlay's queue button to toggle this list. Add:

```js
export function toggleUpNext() {
  const el = document.getElementById('np-queue');
  if (!el) return;
  const items = upNext();
  el.innerHTML = items.length
    ? `<div class="section-label" style="margin:0 0 6px">Up next</div>` + items.map(i =>
        `<div class="qrow"><div class="qt">${(i.title || '').replace(/</g, '&lt;')}</div></div>`).join('')
    : `<p class="text-sm" style="color:var(--text-muted)">Nothing up next.</p>`;
  el.classList.toggle('hidden');
}
```

In `index.html`, change the overlay's queue button `onclick` from
`navigate('#/feeds')` to `toggleUpNext()`. Export `toggleUpNext` from player.js.

- [ ] **Step 5: Commit**

```bash
git add static/js/library.js static/js/home.js static/js/playlists.js index.html static/css/app.css
git commit -m "feat(ui): play within list (library/recent/feed) + up-next view"
```

---

## Task 3: Verify

- [ ] **Step 1: Restart + asset check**

```bash
OLD=$(lsof -nP -iTCP:8090 -sTCP:LISTEN -t); [ -n "$OLD" ] && kill "$OLD"; sleep 2
cd /Users/rodhoward/NarrateTTS && set -a && source .env && set +a
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8090 > /tmp/narrate_8090.log 2>&1 &
sleep 3; for f in player.js library.js home.js playlists.js; do printf "%s " $f; curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8090/static/js/$f; done
```
Expected: all `200`.

- [ ] **Step 2: Handler audit** — confirm `playFromList`, `setList`, `toggleUpNext`,
  `playItem`, `nextInQueue`, `prevInQueue` are window-reachable; confirm every item-row
  onclick in library/home/feed now calls `playFromList('<key>', <index>)` with the
  index matching the array registered via `setList`.

- [ ] **Step 3: Full suite** — `.venv/bin/python -m pytest -q` → 30 passed.

- [ ] **Step 4: Note for user (browser):** play an item from the Library/a feed/Recent;
  when it finishes the next one auto-plays; the Now-Playing queue button shows "Up
  next"; the Continue hero still resumes a single item; lock-screen next/prev advance.
