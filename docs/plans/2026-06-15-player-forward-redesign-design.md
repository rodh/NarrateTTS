# Player-Forward Redesign

**Date:** 2026-06-15
**Status:** Design (approved for planning)
**Companion mockups:** `.superpowers/brainstorm/29888-1781531581/content/` (card-imagery, home-layout, now-playing)

## Problem

NarrateTTS works but looks and navigates like a utility: a flat library list, a
two-tab bar, and a minimal bottom player. The user wants a polished, player-forward
experience inspired by a modern podcast app — a Home/Explore, feed (show) detail
pages, and a real Now-Playing screen — while keeping the personal capture-and-listen
purpose (the web app is where you capture and listen; an external podcast app still
consumes the RSS feeds).

## Goal

Reframe the web app around listening: a Home that resumes and surfaces recent
captures, browsable feeds with detail pages, a full-screen Now-Playing with a real
waveform, and continuous playback — all in a warm, rounded visual language across
light and dark.

## Domain mapping

| Reference (podcast app) | NarrateTTS |
| --- | --- |
| Show / podcast | Playlist (a "feed") |
| Episode | Item (a narrated article) |
| Show art | Generated playlist artwork |
| Episode image | Article `og:image` (when present) else source gradient + favicon |

## Settled decisions (validated via mockups)

- **Item imagery:** source-derived gradient + favicon chip by default; the article's
  `og:image` when a usable one exists.
- **Home:** hybrid — "Continue listening" hero → "Your feeds" horizontal row →
  "Recently added" list.
- **Now-Playing:** full-screen; **real waveform** (decoded audio peaks) with an orange
  played-fill; transport = speed · back-30 · play/pause · forward-30 · queue.
- **Queue:** continuous and contextual — playing from a feed plays through that feed;
  playing from Recent/Library plays through that list.
- **Theme:** keep auto `prefers-color-scheme`; orange accent (`~#f1582c`) + warm
  neutrals in light, deep neutrals in dark; rounded 16–20px cards.
- **Front-end structure:** split the single `index.html` into a no-build static
  bundle (shell + ES module JS + CSS), still served by FastAPI.

## Information architecture

Bottom nav with five slots: **Home · Feeds · ＋ · Library · Settings** (＋ = capture).
Now-Playing is a full-screen overlay reachable from any play affordance and from a
mini-player bar.

Screens:
- **Home** — Continue-listening hero (most recent in-progress item), "Your feeds" row
  (playlist artwork cards), "Recently added" (item cards).
- **Feeds** — grid/list of playlists (feed artwork + name + count).
- **Feed-detail** — feed artwork, name, description, **Subscribe** (copy RSS URL) +
  OPML, and the feed's item list; edit/delete feed; remove items.
- **Library** — all items (search + the existing status/progress affordances), the
  triage surface; item rows reuse the new card style.
- **Settings** — the existing iOS Shortcut card + token (gear panel content moves here),
  plus theme is automatic.
- **Now-Playing** — full-screen player (below).

## Visual language

CSS custom properties define both themes. Tokens: `--accent` (orange), warm
`--bg/--surface/--text/--muted` for light, deep equivalents for dark, `--radius`
(18px), shadow, and a type scale (display 20–22 bold, body 13–15, meta 11–12).
Components: card, hero, feed-art tile, item row, mini-player, transport button, pill.

## Imagery pipeline

- **`og:image`:** during `extract_from_url`, parse the page HTML for
  `<meta property="og:image">` (and `twitter:image` fallback); store on the item as
  `image_url` (nullable). `add_item` accepts it; new `image_url` column on `items`.
- **Favicon + gradient:** derived **client-side** from the item's `source_url` domain
  — favicon via the domain's `/favicon.ico` (or a favicon service) with a lettered
  fallback; gradient from a hash of the domain (deterministic palette). No storage.
- **Waveform peaks:** computed **client-side** via the Web Audio API
  (`decodeAudioData` → downsample to ~120 peaks) on first play of an item, cached in
  `localStorage` keyed by item id. A flat placeholder shows until peaks are ready.
  (Server-side precompute is a possible later optimization; not required now.)

## Player & queue model

A single `player` module owns: the `Audio` element, current item, the **queue** (an
ordered list of item ids + an index), playback rate, and progress persistence (reuse
the existing high-water-mark `/progress` PATCH).

- Starting playback takes a context: `(items[], startIndex)`. The list is whatever the
  user tapped from (a feed's items, Recent, or Library search results).
- On `ended`: save progress, advance index, autoplay the next completed item in the
  queue; stop at the end of the queue.
- Mini-player bar (persistent, above bottom nav) shows current item + play/pause +
  progress; tapping it opens Now-Playing.
- Now-Playing renders the real waveform, transport, and queue (the upcoming list).
- `mediaSession` metadata/handlers updated per item (already present); next/prev wired
  to the queue.

## Front-end structure (no build step)

```
index.html              # shell: bottom nav, screen containers, mini-player, NP overlay
static/css/app.css      # tokens + components (light/dark)
static/js/api.js        # fetch wrappers for existing endpoints
static/js/router.js     # hash routing + screen show/hide
static/js/player.js     # Audio + queue + waveform + progress
static/js/render/*.js   # per-screen render (home, feeds, feed-detail, library, settings)
static/js/main.js       # init, wiring
```

Served by FastAPI: `/` returns `index.html`; `/static` is already mounted. ES modules,
no bundler.

## Data model / backend changes

- `items.image_url TEXT` (nullable) — added in `init_db` as an idempotent migration.
- `extract_from_url` returns `image_url`; `add_item(... image_url=None)` persists it;
  item JSON already returns all columns, so the API needs no new fields.
- No other endpoint changes required (items, feeds/playlists, progress, feed/OPML, and
  the shortcut/capture endpoints all stand).

## Implementation slices (each becomes its own plan)

1. **Visual language + front-end restructure** — define tokens/components in
   `app.css`; split `index.html` into the module layout above; re-implement the
   *current* screens (library, playlists, capture, player, settings/shortcut) in the
   new structure and look. No new screens yet. Ships a working, restyled app.
2. **Imagery pipeline** — `og:image` capture (+ `image_url` column/migration);
   client-side favicon + domain-gradient helpers; client-side waveform-peak
   computation + cache. Apply to item cards.
3. **IA + bottom nav + routing + Home** — five-slot bottom nav, hash router,
   mini-player bar, and the hybrid Home screen.
4. **Feed-detail screen** — artwork, description, subscribe/RSS + OPML, item list,
   edit/delete/remove.
5. **Now-Playing full-screen + real waveform** — full player screen using the
   computed peaks and the transport set.
6. **Continuous contextual queue** — queue model in `player.js`, autoplay-next,
   next/prev, queue view in Now-Playing.

Slices 1–2 are foundations; 3 establishes navigation; 4–6 complete the player. Each
slice leaves the app working.

## Out of scope (for now)

- Server-side waveform precompute / ffmpeg dependency.
- On-device page-text capture for paywalled/JS pages (separate, earlier-noted item).
- Multi-user, auth, social/discovery features from the reference (listeners counts,
  "follow", contributors).
- Shuffle / repeat modes (queue is linear; can add later).

## Testing approach

- Backend: extend extractor tests for `og:image` parsing (incl. missing/`twitter:image`
  fallback) and `add_item`/migration for `image_url`. Existing suite stays green.
- Front-end: vanilla, no framework — verify per slice by running the app and exercising
  each screen (the `run`/`verify` skills), since there's no JS test harness. Keep render
  functions small and pure (data → DOM string) so they're easy to reason about.
