# Slice 3 — Bottom Nav + Routing + Home — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Replace the two top tabs with a five-slot bottom nav (Home · Feeds · ＋ · Library · Settings), add a hash router that swaps full-screen views, add a persistent mini-player above the nav, and build the hybrid Home screen (Continue-listening hero → Your feeds row → Recently added).

**Architecture:** Wrap today's working library/feeds(playlists)/settings markup in `#screen-*` containers and add `#screen-home`. A new `static/js/router.js` shows/hides screens by `location.hash` and highlights the nav; `static/js/home.js` renders Home from the shared `items` array + the playlists API. The existing `#player` bar is repositioned as the mini-player above the nav (controls unchanged). No new backend.

**Tech Stack:** FastAPI, Tailwind CDN, vanilla ES modules, CSS custom properties.

**Spec:** `docs/plans/2026-06-15-player-forward-redesign-design.md` (IA, Home, Player & queue model — mini-player only here; full queue is Slice 6, Now-Playing is Slice 5).

**Behavior to preserve:** everything from Slices 1–2 keeps working; we only relocate it under the new nav. Feed-detail (`#/feed/:id`) and Now-Playing (`#/playing`) routes are reserved but not built here (router tolerates them by falling back to Home).

---

## File Structure

| File | Responsibility |
| --- | --- |
| `index.html` (modify) | New shell: slim header, `#screen-home/-feeds/-library/-settings`, `#add-panel` overlay, `#player` mini bar, bottom `#bottom-nav`. |
| `static/css/app.css` (modify) | `.bottom-nav`, `.nav-item`/`.nav-active`, `.nav-center`, mini-player position, Home components (`.hero`, `.feed-tile`, `.section-label`). |
| `static/js/router.js` (new) | hash routing + screen show/hide + nav highlight + `navigate()`. |
| `static/js/home.js` (new) | render Continue hero + feeds row + recently-added. |
| `static/js/main.js` (modify) | init router instead of `switchTab`; per-screen data load; expose `navigate`. |
| `static/js/library.js` (modify) | export `getItems()` accessor (return the live `items` array) for Home. |

---

## Task 1: Shell restructure (index.html + CSS)

**Files:** Modify `index.html`, `static/css/app.css`

- [ ] **Step 1: Add CSS for nav, mini-player, and Home components**

Append to `static/css/app.css`:

```css
/* Bottom nav */
.bottom-nav { display:flex; justify-content:space-around; align-items:center; gap:4px;
  border-top:1px solid var(--border); background:var(--surface);
  padding:8px 8px calc(8px + env(safe-area-inset-bottom)); }
.nav-item { display:flex; flex-direction:column; align-items:center; gap:2px; flex:1;
  font-size:10px; color:var(--text-faint); background:none; border:0; cursor:pointer; }
.nav-item svg { width:22px; height:22px; }
.nav-item.nav-active { color:var(--accent); }
.nav-center { width:46px; height:46px; border-radius:50%; background:var(--accent);
  color:var(--accent-text); display:flex; align-items:center; justify-content:center;
  margin-top:-18px; flex:0 0 auto; box-shadow:var(--shadow); }
.nav-center svg { width:24px; height:24px; }

/* Home */
.section-label { font-size:11px; letter-spacing:.08em; text-transform:uppercase;
  color:var(--text-faint); font-weight:700; margin:18px 4px 8px; }
.hero { border-radius:var(--radius); padding:16px; color:#fff; min-height:96px;
  display:flex; flex-direction:column; justify-content:space-between; cursor:pointer; }
.hero-prog { height:4px; background:rgba(255,255,255,.35); border-radius:2px; margin-top:10px; }
.hero-prog > i { display:block; height:100%; background:#fff; border-radius:2px; }
.feed-row { display:flex; gap:12px; overflow-x:auto; padding:2px 4px 4px; }
.feed-tile { width:104px; flex:0 0 auto; cursor:pointer; }
.feed-tile .art { height:104px; border-radius:14px; }
.feed-tile p { margin:6px 2px 0; font-size:12px; font-weight:600; line-height:1.2; }
```

- [ ] **Step 2: Restructure the `<body>`**

Replace the body's structure as below. **Relocate existing inner markup, don't rewrite
it:** move the current library list container (`<main id="library">`), the feeds list
(`<main id="playlists-view">`), the Settings card markup (currently inside
`#settings-panel`), and keep `#add-panel` and the `#player` bar. The header loses its
old tab bar, gear, and inline ＋ (the nav owns capture + settings now); keep the search
input but move it into the Library screen.

Target structure:

```html
<body class="flex flex-col overflow-hidden" style="height:100dvh">
  <header class="flex items-center gap-2 px-4 sm:px-6 py-3 border-b border-[var(--border)]">
    <img src="/static/apple-touch-icon.png" alt="" class="w-7 h-7 rounded">
    <h1 class="text-lg font-semibold tracking-tight">NarrateTTS</h1>
  </header>

  <!-- Add Panel (overlay dropdown, toggled by nav ＋) -->
  <div id="add-panel" class="hidden border-b border-[var(--border)] bg-[var(--bg-panel)] px-4 sm:px-6 py-4 overflow-hidden">
    <!-- KEEP the existing add-panel inner markup (textarea #url-input, #voice-select, #convert-btn) -->
  </div>

  <main class="flex-1 overflow-y-auto" id="screen-host">
    <section id="screen-home" class="px-4 sm:px-6 py-4 hidden"></section>

    <section id="screen-feeds" class="px-4 sm:px-6 py-4 hidden">
      <div id="playlists-view"><!-- KEEP existing feeds/playlists render target --></div>
    </section>

    <section id="screen-library" class="px-4 sm:px-6 py-4 hidden">
      <input id="search" type="text" placeholder="Search..." class="w-full mb-3 bg-[var(--bg-input)] border border-[var(--border-input)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[var(--border-focus)]" oninput="render()">
      <div id="library"><!-- KEEP existing library render target --></div>
    </section>

    <section id="screen-settings" class="px-4 sm:px-6 py-4 hidden">
      <!-- KEEP the existing Settings/iOS-Shortcut card markup (endpoint, token, reveal/copy, regenerate, Add to iPhone) -->
    </section>
  </main>

  <!-- Mini-player (KEEP existing #player inner markup; it now sits above the nav) -->
  <div id="player" class="hidden border-t border-[var(--border)] px-4 sm:px-6 py-2"><!-- existing player controls --></div>

  <nav id="bottom-nav" class="bottom-nav">
    <button class="nav-item" data-nav="home" onclick="navigate('#/home')">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M3 12l9-9 9 9M5 10v10h5v-6h4v6h5V10"/></svg>Home</button>
    <button class="nav-item" data-nav="feeds" onclick="navigate('#/feeds')">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h10"/></svg>Feeds</button>
    <button class="nav-item" style="flex:0 0 auto" onclick="toggleAddPanel()" title="Capture">
      <span class="nav-center"><svg fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" d="M12 5v14m-7-7h14"/></svg></span></button>
    <button class="nav-item" data-nav="library" onclick="navigate('#/library')">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 5h16v14H4zM4 9h16"/></svg>Library</button>
    <button class="nav-item" data-nav="settings" onclick="navigate('#/settings')">
      <svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path stroke-linecap="round" stroke-linejoin="round" d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-2.92.68 2 2 0 11-3.86 0 1.65 1.65 0 00-2.92-.68l-.06.06a2 2 0 11-2.83-2.83l.06-.06A1.65 1.65 0 004.6 15a1.65 1.65 0 00-1.51-1H3a2 2 0 110-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.6a1.65 1.65 0 001-1.51V3a2 2 0 114 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06A1.65 1.65 0 0019.4 9c.14.31.22.65.22 1z"/></svg>Settings</button>
  </nav>

  <script type="module" src="/static/js/main.js"></script>
</body>
```

Delete the old `<nav>` tab bar, the header gear button (`#settings-btn`), the inline
header ＋ button (`#add-btn`), and the old `#settings-panel` wrapper (its inner card
moved into `#screen-settings`).

- [ ] **Step 3: Commit**

```bash
git add index.html static/css/app.css
git commit -m "feat(ui): bottom nav + screen containers shell"
```

---

## Task 2: Router + main wiring

**Files:** Create `static/js/router.js`; Modify `static/js/main.js`, `static/js/library.js`

- [ ] **Step 1: Create `static/js/router.js`**

```js
const SCREENS = ['home', 'feeds', 'library', 'settings'];

export function navigate(hash) { location.hash = hash; }

export function currentRoute() {
  return (location.hash || '#/home').replace(/^#\/?/, '') || 'home';
}

export function initRouter(onShow) {
  const handle = () => {
    const route = currentRoute();
    const name = route.split('/')[0];
    const target = SCREENS.includes(name) ? name : 'home';
    SCREENS.forEach(s => {
      const el = document.getElementById('screen-' + s);
      if (el) el.classList.toggle('hidden', s !== target);
    });
    document.querySelectorAll('[data-nav]').forEach(b =>
      b.classList.toggle('nav-active', b.dataset.nav === target));
    onShow(target, route);
  };
  window.addEventListener('hashchange', handle);
  handle();
}
```

- [ ] **Step 2: Rewire `static/js/main.js`**

Replace the `switchTab` logic and init with router-driven loading:

```js
import * as player from './player.js';
import * as library from './library.js';
import * as playlists from './playlists.js';
import * as settings from './settings.js';
import * as home from './home.js';
import { initRouter, navigate } from './router.js';

Object.assign(window, player, library, playlists, settings, home);
window.navigate = navigate;

document.addEventListener('visibilitychange', () => { if (document.hidden) player.saveProgress(); });
window.addEventListener('beforeunload', player.saveProgress);

library.loadVoices();

// Load items once up front (Home + Library share the array), then route.
library.loadItems().then(() => {
  if (library.hasProcessing()) library.pollUpdates();
  initRouter((target) => {
    if (target === 'home') home.render();
    else if (target === 'feeds') playlists.loadPlaylists();
    else if (target === 'library') library.render();
    else if (target === 'settings') settings.loadShortcutToken();
  });
});

document.getElementById('speed-btn').textContent = (player.getStoredSpeed() === 1) ? '1x' : player.getStoredSpeed() + 'x';
```

(Remove the old `switchTab` function and its `window.switchTab` assignment.)

- [ ] **Step 3: Export the live items array from `library.js`**

Ensure `static/js/library.js` exports an accessor returning the SAME array instance the
render/poll use (Slice 1 kept it mutated-in-place):

```js
export function getItems() { return items; }
```

- [ ] **Step 4: Commit**

```bash
git add static/js/router.js static/js/main.js static/js/library.js
git commit -m "feat(ui): hash router + per-screen loading"
```

---

## Task 3: Home screen

**Files:** Create `static/js/home.js`

- [ ] **Step 1: Create `static/js/home.js`**

```js
import { getItems } from './library.js';
import { getPlaylists } from './api.js';
import { itemArt, gradientFor } from './imagery.js';
import { playItem } from './player.js';
import { navigate } from './router.js';

function fmtMeta(item) {
  const d = item.source_url ? (() => { try { return new URL(item.source_url).hostname.replace(/^www\./, ''); } catch { return 'Text'; } })() : 'Text';
  return `${d} · ${item.word_count || 0} words`;
}

function continueItem(items) {
  // most-recently-updated completed item with progress that isn't finished
  return items
    .filter(i => i.status === 'completed' && (i.play_position || 0) > 0 && !i.consumed_at &&
      (!i.duration_seconds || (i.play_position / i.duration_seconds) < 0.95))
    .sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''))[0];
}

export async function render() {
  const host = document.getElementById('screen-home');
  const items = getItems();
  const recent = items.filter(i => i.status === 'completed' && i.audio_path).slice(0, 8);
  const cont = continueItem(items);

  let playlists = [];
  try { playlists = await getPlaylists(); } catch (e) { /* ignore */ }

  const heroHtml = cont ? `
    <div class="section-label">Continue listening</div>
    <div class="hero" style="background:${gradientFor(cont.source_url || '')}" onclick="playItem(${cont.id}, '${cont.audio_path ? cont.audio_path.split('/').pop() : ''}')">
      <div style="font-weight:700;font-size:15px">${escapeHtml(cont.title)}</div>
      <div style="font-size:12px;opacity:.85">${escapeHtml(fmtMeta(cont))}</div>
      <div class="hero-prog"><i style="width:${Math.round(100 * (cont.play_position || 0) / (cont.duration_seconds || 1))}%"></i></div>
    </div>` : '';

  const feedsHtml = playlists.length ? `
    <div class="section-label">Your feeds</div>
    <div class="feed-row">
      ${playlists.map(p => `
        <div class="feed-tile" onclick="navigate('#/feed/${p.id}')">
          <div class="art" style="background:url('/static/artwork-playlist-${p.id}.png') center/cover, ${gradientFor(p.name)}"></div>
          <p>${escapeHtml(p.name)}</p>
        </div>`).join('')}
    </div>` : '';

  const recentHtml = `
    <div class="section-label">Recently added</div>
    ${recent.length ? recent.map(i => `
      <div class="item-card flex items-center gap-3 py-2 cursor-pointer" onclick="playItem(${i.id}, '${i.audio_path ? i.audio_path.split('/').pop() : ''}')">
        ${itemArt(i)}
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium truncate">${escapeHtml(i.title)}</p>
          <p class="text-xs text-[var(--text-muted)] truncate">${escapeHtml(fmtMeta(i))}</p>
        </div>
      </div>`).join('') : `<p class="text-sm text-[var(--text-muted)]">Nothing yet — tap ＋ to capture something.</p>`}`;

  host.innerHTML = heroHtml + feedsHtml + recentHtml;
}

function escapeHtml(str) { const d = document.createElement('div'); d.textContent = str == null ? '' : str; return d.innerHTML; }
```

- [ ] **Step 2: Commit**

```bash
git add static/js/home.js
git commit -m "feat(ui): hybrid Home screen (continue, feeds, recent)"
```

---

## Task 4: Verify

- [ ] **Step 1: Restart + asset check**

```bash
OLD=$(lsof -nP -iTCP:8090 -sTCP:LISTEN -t); [ -n "$OLD" ] && kill "$OLD"; sleep 2
cd /Users/rodhoward/NarrateTTS && set -a && source .env && set +a
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8090 > /tmp/narrate_8090.log 2>&1 &
sleep 3
for f in /static/js/router.js /static/js/home.js /static/js/main.js; do printf "%s " "$f"; curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8090$f"; done
```
Expected: all `200`.

- [ ] **Step 2: Handler audit**

Grep `index.html` for every inline `onclick=`/`oninput=` and confirm each is exported
to `window` (via `Object.assign` of the modules in `main.js`, plus `navigate`). Confirm
`navigate`, `toggleAddPanel`, `render`, `playItem` are reachable. Report any gaps.

- [ ] **Step 3: Full test suite (backend unchanged)**

Run: `.venv/bin/python -m pytest -q`
Expected: 30 passed.

- [ ] **Step 4: Note for user (requires browser):** verify nav switches Home/Feeds/Library/Settings, ＋ opens capture, Home shows continue/feeds/recent, tapping a recent item plays it, mini-player sits above the nav.
