# Slice 4 — Feed-detail Screen — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** A routed Feed-detail screen (`#/feed/:id`) showing the feed's artwork, name, description, Subscribe (copy RSS URL) + OPML, and its item list (art + play), with remove-item and delete-feed.

**Architecture:** Add a `#screen-feed-detail` container and teach `router.js` a non-nav `feed` route (highlights the Feeds tab). `playlists.js` gains `renderFeedDetail(id)` (reuses the existing `copyFeedUrl`/`removeFromPlaylist`/`confirmDeletePlaylist` and the item-art/play patterns); the Feeds list and Home feed tiles navigate to `#/feed/:id`. No backend change (single-playlist meta is read from the existing `/api/playlists` list).

**Tech Stack:** FastAPI, vanilla ES modules.

**Spec:** `docs/plans/2026-06-15-player-forward-redesign-design.md` (Feed-detail).

---

## Task 1: Router supports the feed route

**Files:** Modify `static/js/router.js`, `index.html`

- [ ] **Step 1: Add the feed-detail screen container**

In `index.html`, inside `#screen-host` after `#screen-settings`, add:

```html
    <section id="screen-feed-detail" class="px-4 sm:px-6 py-4 hidden"></section>
```

- [ ] **Step 2: Teach the router the `feed` route**

Replace `static/js/router.js` with:

```js
const NAV_SCREENS = ['home', 'feeds', 'library', 'settings'];
const ALL_SCREENS = [...NAV_SCREENS, 'feed-detail'];

export function navigate(hash) { location.hash = hash; }
export function currentRoute() { return (location.hash || '#/home').replace(/^#\/?/, '') || 'home'; }

export function initRouter(onShow) {
  const handle = () => {
    const route = currentRoute();
    const name = route.split('/')[0];
    const target = NAV_SCREENS.includes(name) ? name : (name === 'feed' ? 'feed-detail' : 'home');
    ALL_SCREENS.forEach(s => {
      const el = document.getElementById('screen-' + s);
      if (el) el.classList.toggle('hidden', s !== target);
    });
    const navTarget = name === 'feed' ? 'feeds' : target;
    document.querySelectorAll('[data-nav]').forEach(b =>
      b.classList.toggle('nav-active', b.dataset.nav === navTarget));
    onShow(name, route);
  };
  window.addEventListener('hashchange', handle);
  handle();
}
```

- [ ] **Step 3: Route `feed` in `main.js`**

In `static/js/main.js`, update the `initRouter` callback to handle the feed route:

```js
  initRouter((name, route) => {
    if (name === 'home') home.render();
    else if (name === 'feeds') playlists.loadPlaylists();
    else if (name === 'library') library.render();
    else if (name === 'settings') settings.loadShortcutToken();
    else if (name === 'feed') playlists.renderFeedDetail(route.split('/')[1]);
  });
```

(The callback signature is now `(name, route)`; the router already passes both.)

- [ ] **Step 4: Commit**

```bash
git add static/js/router.js static/js/main.js index.html
git commit -m "feat(ui): route #/feed/:id to a feed-detail screen"
```

---

## Task 2: Feed-detail render + navigation

**Files:** Modify `static/js/playlists.js`

- [ ] **Step 1: Add `renderFeedDetail(id)` and update refresh/delete to use routing**

In `static/js/playlists.js`:
- `import { navigate } from './router.js';`, `import { itemArt } from './imagery.js';`,
  `import { playItem } from './player.js';`, and `getPlaylists, getPlaylistItems` from `./api.js`.
- Make the Feeds list tiles/rows (in `renderPlaylists`) open the detail via
  `onclick="navigate('#/feed/' + id)"` instead of `viewPlaylist(id)`.
- Add:

```js
export async function renderFeedDetail(id) {
  const host = document.getElementById('screen-feed-detail');
  host.innerHTML = `<p class="text-sm text-[var(--text-muted)]">Loading…</p>`;
  let playlist = null, items = [];
  try {
    const all = await getPlaylists();
    playlist = all.find(p => String(p.id) === String(id));
    items = await getPlaylistItems(id);
  } catch (e) { host.innerHTML = `<p class="text-sm text-[var(--text-muted)]">Couldn't load feed.</p>`; return; }
  if (!playlist) { host.innerHTML = `<p class="text-sm text-[var(--text-muted)]">Feed not found.</p>`; return; }

  const feedUrl = `${location.origin}/feed/playlist/${playlist.id}`;
  const art = `background:url('/static/artwork-playlist-${playlist.id}.png') center/cover`;
  const itemsHtml = items.length ? items.map(i => `
    <div class="item-card flex items-center gap-3 py-2">
      <div class="cursor-pointer flex items-center gap-3 flex-1 min-w-0" onclick="playItem(${i.id}, '${i.audio_path ? i.audio_path.split('/').pop() : ''}')">
        ${itemArt(i)}
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium truncate">${escapeHtml(i.title)}</p>
          <p class="text-xs text-[var(--text-muted)] truncate">${i.duration_seconds ? Math.round(i.duration_seconds/60)+' min' : ''}</p>
        </div>
      </div>
      <button onclick="removeFromPlaylist(${playlist.id}, ${i.id})" class="text-[var(--text-faint)] hover:text-red-400 transition flex-shrink-0" title="Remove">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" d="M6 18L18 6M6 6l12 12"/></svg>
      </button>
    </div>`).join('') : `<p class="text-sm text-[var(--text-muted)]">No items yet. Add some from the Library.</p>`;

  host.innerHTML = `
    <button onclick="navigate('#/feeds')" class="text-sm text-[var(--text-muted)] hover:text-[var(--text-accent)] transition mb-3">&larr; Feeds</button>
    <div class="flex items-center gap-4 mb-3">
      <div style="width:96px;height:96px;border-radius:var(--radius);${art};flex:0 0 auto"></div>
      <div class="min-w-0">
        <h2 class="text-xl font-bold truncate">${escapeHtml(playlist.name)}</h2>
        <p class="text-xs text-[var(--text-muted)] mt-0.5">${playlist.item_count} item${playlist.item_count !== 1 ? 's' : ''}</p>
      </div>
    </div>
    ${playlist.description ? `<p class="text-sm text-[var(--text-secondary)] mb-3">${escapeHtml(playlist.description)}</p>` : ''}
    <div class="flex items-center gap-2 mb-4">
      <button onclick="copyFeedUrl('${feedUrl}')" class="btn-accent text-sm px-4 py-2 transition">Copy feed URL</button>
      <a href="/feed/opml" download="narratetts.opml" class="text-sm bg-[var(--bg-button)] hover:bg-[var(--bg-button-hover)] px-3 py-2 rounded-full transition">OPML</a>
      <button onclick="confirmDeletePlaylist(${playlist.id})" class="text-[var(--text-faint)] hover:text-red-400 transition ml-auto" title="Delete feed">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
      </button>
    </div>
    ${itemsHtml}`;
}
```

- Update `removeFromPlaylist` so it refreshes the detail screen:
  change its post-delete refresh from `viewPlaylist(playlistId)` to
  `renderFeedDetail(playlistId)`.
- Update `confirmDeletePlaylist` so that after a successful delete it does
  `navigate('#/feeds')` (then `loadPlaylists()` runs via the route).
- Ensure `escapeHtml`, `removeFromPlaylist`, `confirmDeletePlaylist`, `copyFeedUrl`,
  `renderFeedDetail` are exported (they're auto-exposed on `window` by `main.js`'s
  `Object.assign`). The old `viewPlaylist`/`renderPlaylistDetail` may remain unused or
  be removed — remove them if unreferenced.

- [ ] **Step 2: Commit**

```bash
git add static/js/playlists.js
git commit -m "feat(ui): feed-detail screen (art, subscribe, OPML, items, delete)"
```

---

## Task 3: Verify

- [ ] **Step 1: Restart + asset check**

```bash
OLD=$(lsof -nP -iTCP:8090 -sTCP:LISTEN -t); [ -n "$OLD" ] && kill "$OLD"; sleep 2
cd /Users/rodhoward/NarrateTTS && set -a && source .env && set +a
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8090 > /tmp/narrate_8090.log 2>&1 &
sleep 3; curl -s -o /dev/null -w "router %{http_code}\n" http://localhost:8090/static/js/router.js
```
Expected: `200`.

- [ ] **Step 2: Handler audit** — grep `index.html` and the JS-generated markup
  (`playlists.js`, `home.js`) for inline handlers; confirm `navigate`,
  `renderFeedDetail`, `removeFromPlaylist`, `confirmDeletePlaylist`, `copyFeedUrl`,
  `playItem` are all window-reachable. Flag gaps.

- [ ] **Step 3: Full suite** — `.venv/bin/python -m pytest -q` → 30 passed.

- [ ] **Step 4: Note for user (browser):** from Feeds or Home, tap a feed → detail
  shows art/description/items; Copy feed URL works; back returns to Feeds; remove item
  and delete feed work.
