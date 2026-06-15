# Slice 5 — Now-Playing + Real Waveform — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** A full-screen Now-Playing overlay with big artwork, title/source, a **real waveform** (decoded peaks) you can tap/drag to scrub, and the transport (speed · back-30 · play/pause · forward-30 · queue) — kept in sync with the existing mini-player.

**Architecture:** Add a fixed `#now-playing` overlay to `index.html` (opened by tapping the mini-player, closed by a chevron). Extend `static/js/player.js`: compute waveform peaks once per item via the Web Audio API (`decodeAudioData` → downsample → cache in `localStorage`), render them as height-scaled bars with an orange played-fill, and update both the mini-player and Now-Playing UIs from the existing `timeupdate`/play/pause/speed code. The queue button is present but inert (wired in Slice 6).

**Tech Stack:** Web Audio API, vanilla ES modules, CSS.

**Spec:** `docs/plans/2026-06-15-player-forward-redesign-design.md` (Now-Playing; waveform via client-side Web Audio peaks).

---

## Task 1: Now-Playing overlay markup + CSS

**Files:** Modify `index.html`, `static/css/app.css`

- [ ] **Step 1: Add CSS**

Append to `static/css/app.css`:

```css
/* Now-Playing overlay */
.np-overlay { position:fixed; inset:0; z-index:60; background:var(--bg);
  display:flex; flex-direction:column; padding:14px 20px calc(20px + env(safe-area-inset-bottom));
  transform:translateY(100%); transition:transform .25s ease; }
.np-overlay.open { transform:translateY(0); }
.np-top { display:flex; justify-content:space-between; align-items:center; color:var(--text-muted); font-size:13px; }
.np-icon-btn { background:none; border:0; color:var(--text-secondary); cursor:pointer; padding:6px; }
.np-art { width:100%; aspect-ratio:1; max-height:46vh; border-radius:24px; margin:14px auto 0;
  background-size:cover; background-position:center; }
.np-wave { display:flex; align-items:center; gap:2px; height:48px; margin:22px 0 6px; cursor:pointer; }
.np-wave i { flex:1; min-width:2px; border-radius:2px; background:var(--border-strong, #ccc); }
.np-wave i.on { background:var(--accent); }
.np-times { display:flex; justify-content:space-between; font-size:11px; color:var(--text-muted); }
.np-title { font-size:20px; font-weight:800; text-align:center; line-height:1.25; margin:18px 12px 4px; }
.np-source { text-align:center; font-size:13px; color:var(--text-muted); margin-bottom:20px; }
.np-ctrls { display:flex; align-items:center; justify-content:space-between; margin-top:auto; }
.np-ctrls .ic { background:none; border:0; color:var(--text-secondary); font-size:14px; cursor:pointer; display:flex; flex-direction:column; align-items:center; gap:2px; }
.np-ctrls .ic svg { width:26px; height:26px; }
.np-bigplay { width:64px; height:64px; border-radius:50%; background:var(--accent); color:var(--accent-text);
  display:flex; align-items:center; justify-content:center; border:0; cursor:pointer; }
.np-bigplay svg { width:28px; height:28px; }
/* Make the mini-player title area look tappable */
#player-title { cursor:pointer; }
```

- [ ] **Step 2: Add the overlay markup**

In `index.html`, just before the `<script type="module">` tag, add:

```html
  <div id="now-playing" class="np-overlay">
    <div class="np-top">
      <button class="np-icon-btn" onclick="closeNowPlaying()" title="Close">
        <svg width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 9l6 6 6-6"/></svg>
      </button>
      <span style="font-weight:600;color:var(--text)">Now Playing</span>
      <span style="width:24px"></span>
    </div>
    <div id="np-art" class="np-art"></div>
    <div id="np-wave" class="np-wave" onclick="seekWaveform(event)"></div>
    <div class="np-times"><span id="np-time">0:00</span><span id="np-duration">0:00</span></div>
    <div id="np-title" class="np-title"></div>
    <div id="np-source" class="np-source"></div>
    <div class="np-ctrls">
      <button class="ic" onclick="cycleSpeed()"><span id="np-speed" style="font-weight:700;font-size:15px">1x</span></button>
      <button class="ic" onclick="skipBack()"><svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M11 19l-7-7 7-7M20 19l-7-7 7-7"/></svg></button>
      <button class="np-bigplay" onclick="togglePlay()">
        <svg id="np-play-icon" fill="currentColor" viewBox="0 0 24 24"><polygon points="6,4 20,12 6,20"/></svg>
        <svg id="np-pause-icon" class="hidden" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
      </button>
      <button class="ic" onclick="skipForward()"><svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M13 5l7 7-7 7M4 5l7 7-7 7"/></svg></button>
      <button class="ic" onclick="navigate('#/feeds')" title="Queue"><svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h10M4 18h10M16 14l5 3-5 3z"/></svg></button>
    </div>
  </div>
```

- [ ] **Step 3: Commit**

```bash
git add index.html static/css/app.css
git commit -m "feat(ui): now-playing overlay markup + styles"
```

---

## Task 2: Waveform + Now-Playing logic in player.js

**Files:** Modify `static/js/player.js`

Read the current `player.js` first. Integrate the following, reusing existing state
(`audio`, `currentItemId`) and the existing `updatePlayerUI`, `togglePlay`,
`cycleSpeed`, `formatTime`, and `playItem`.

- [ ] **Step 1: Add imagery import + waveform/now-playing code**

At the top: `import { itemArt } from './imagery.js';` is NOT needed; instead add a
helper to compute the big-art background. Add this code to `player.js`:

```js
let currentPeaks = null;

function bigArtStyle(item) {
  if (item && item.image_url) return `background-image:url('${item.image_url}')`;
  // gradient fallback consistent with imagery.js palette
  return `background-image:linear-gradient(135deg,#f1582c,#5b2c91)`;
}

async function computePeaks(url, itemId, n = 80) {
  const key = 'peaks_' + itemId;
  const cached = localStorage.getItem(key);
  if (cached) { try { return JSON.parse(cached); } catch {} }
  try {
    const buf = await (await fetch(url)).arrayBuffer();
    const Ctx = window.AudioContext || window.webkitAudioContext;
    const ctx = new Ctx();
    const audioBuf = await ctx.decodeAudioData(buf);
    const data = audioBuf.getChannelData(0);
    const block = Math.max(1, Math.floor(data.length / n));
    const peaks = [];
    for (let i = 0; i < n; i++) {
      let max = 0;
      for (let j = 0; j < block; j++) { const v = Math.abs(data[i * block + j] || 0); if (v > max) max = v; }
      peaks.push(max);
    }
    ctx.close();
    const m = Math.max(...peaks, 0.01);
    const norm = peaks.map(p => p / m);
    localStorage.setItem(key, JSON.stringify(norm));
    return norm;
  } catch (e) {
    return Array.from({ length: n }, () => 0.35); // flat fallback
  }
}

function renderWaveBars(peaks) {
  const wave = document.getElementById('np-wave');
  if (!wave) return;
  wave.innerHTML = peaks.map(p => `<i style="height:${Math.max(8, Math.round(p * 100))}%"></i>`).join('');
}

function updateWaveProgress() {
  const wave = document.getElementById('np-wave');
  if (!wave || !audio || !audio.duration) return;
  const frac = audio.currentTime / audio.duration;
  const bars = wave.children;
  const lit = Math.floor(frac * bars.length);
  for (let i = 0; i < bars.length; i++) bars[i].classList.toggle('on', i <= lit);
}

export function seekWaveform(event) {
  const wave = document.getElementById('np-wave');
  if (!wave || !audio || !audio.duration) return;
  const rect = wave.getBoundingClientRect();
  const frac = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
  audio.currentTime = frac * audio.duration;
}

export function openNowPlaying() {
  const item = items.find(i => i.id === currentItemId);
  if (!item) return;
  document.getElementById('np-art').style.cssText += ';' + bigArtStyle(item);
  document.getElementById('np-title').textContent = item.title || '';
  let src = 'Text';
  try { if (item.source_url) src = new URL(item.source_url).hostname.replace(/^www\./, ''); } catch {}
  document.getElementById('np-source').textContent = src;
  document.getElementById('np-speed').textContent = (getStoredSpeed() === 1) ? '1x' : getStoredSpeed() + 'x';
  if (currentPeaks) renderWaveBars(currentPeaks);
  updateWaveProgress();
  syncNpPlayIcon();
  document.getElementById('now-playing').classList.add('open');
}

export function closeNowPlaying() {
  document.getElementById('now-playing').classList.remove('open');
}

function syncNpPlayIcon() {
  const playing = audio && !audio.paused;
  const pi = document.getElementById('np-play-icon'), pa = document.getElementById('np-pause-icon');
  if (pi && pa) { pi.classList.toggle('hidden', playing); pa.classList.toggle('hidden', !playing); }
}
```

- [ ] **Step 2: Hook into existing functions**

- In `playItem(id, file)`: after the audio element is created and metadata wired, kick
  off peak computation and render when ready, and refresh the Now-Playing art/title if
  it's open:
  ```js
  currentPeaks = null;
  computePeaks(`/audio/${file}`, id).then(p => { currentPeaks = p; renderWaveBars(p); updateWaveProgress(); });
  ```
  Add this near where the new `Audio` is set up.
- In `updatePlayerUI()` (the `timeupdate` handler): after updating the mini-player
  progress/time, also update the Now-Playing time/duration and waveform:
  ```js
  const npt = document.getElementById('np-time'); if (npt) npt.textContent = formatTime(audio.currentTime);
  const npd = document.getElementById('np-duration'); if (npd) npd.textContent = formatTime(audio.duration);
  updateWaveProgress();
  ```
- In `togglePlay()` (both branches) and in the `ended` handler: also call
  `syncNpPlayIcon()` so the Now-Playing play/pause icon stays in sync with the mini one.
- In `cycleSpeed()`: after setting the mini `speed-btn` label, also set
  `document.getElementById('np-speed')` text if present.
- Export the new handlers so `main.js` exposes them on window:
  `seekWaveform, openNowPlaying, closeNowPlaying`.

- [ ] **Step 3: Make the mini-player open Now-Playing**

The mini-player `#player-title` should open the overlay on click. In `index.html`, add
`onclick="openNowPlaying()"` to the `<p id="player-title">` element. (It's exported and
window-exposed via main.js.)

- [ ] **Step 4: Commit**

```bash
git add static/js/player.js index.html
git commit -m "feat(ui): real waveform + now-playing player logic"
```

---

## Task 3: Verify

- [ ] **Step 1: Restart + asset check**

```bash
OLD=$(lsof -nP -iTCP:8090 -sTCP:LISTEN -t); [ -n "$OLD" ] && kill "$OLD"; sleep 2
cd /Users/rodhoward/NarrateTTS && set -a && source .env && set +a
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8090 > /tmp/narrate_8090.log 2>&1 &
sleep 3; curl -s -o /dev/null -w "player.js %{http_code}\n" http://localhost:8090/static/js/player.js
```
Expected: `200`.

- [ ] **Step 2: Handler audit** — confirm `openNowPlaying`, `closeNowPlaying`,
  `seekWaveform`, `togglePlay`, `skipBack`, `skipForward`, `cycleSpeed`, `navigate` are
  all window-reachable (the first three are new exports; verify they're in player.js's
  exports so `Object.assign(window, player, ...)` picks them up).

- [ ] **Step 3: Full suite** — `.venv/bin/python -m pytest -q` → 30 passed.

- [ ] **Step 4: Note for user (browser):** play an item → mini-player appears; tap its
  title → Now-Playing slides up with art/title/source; the waveform fills with an
  orange played-region and tapping it scrubs; transport (speed/skip/play-pause) works
  and stays in sync with the mini-player; chevron closes it.
