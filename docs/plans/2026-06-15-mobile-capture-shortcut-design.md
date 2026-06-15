# Mobile Capture — "Send to NarrateTTS" iOS Shortcut

**Date:** 2026-06-15
**Status:** Design (approved for planning)
**Slice:** A of the daily-loop improvements (capture → process → organize → listen)

## Problem

NarrateTTS's daily loop is lopsided. Listening happens anywhere (a podcast app
subscribes to the RSS feed over Tailscale), but content can only be **captured at
the desk** via the desktop Safari extension. There is no way to save an article or
selection from the phone, which is where most reading-to-listen intent occurs.

This slice closes the missing half: **one-tap capture from the iOS Share Sheet**,
with zero manual setup, mirroring the proven "Send to Distill" pattern from the
user's `howlab-tools` project.

## Goal

From an iPhone: open NarrateTTS in Safari → **Add to iPhone** → from then on, share
any link or selected text to **Send to NarrateTTS** and it becomes a queued TTS job
that flows into the existing feed. No token pasting, no "Allow Untrusted Shortcuts".

## Non-goals (later slices / explicitly out of scope)

- Web-UI login / session auth (see "Auth boundary" below).
- Slice B: triage-console reframe of the web app, surfacing summaries in the UI.
- Android capture.
- Choosing voice/playlist at capture time (capture is zero-decision; the server
  applies a default voice and existing auto-categorization sorts the item).

## Background: the mechanism being ported

From `howlab-tools` (`app/api/shortcut/route.ts`, `lib/db/tokens.ts`):

1. `GET /api/shortcut` builds a **binary-plist `.shortcut` file** in memory with the
   API endpoint and the user's bearer **token baked in** as literal strings inside
   the workflow actions.
2. It **signs** the file with the macOS CLI `/usr/bin/shortcuts sign --mode anyone`.
   A signed shortcut installs in one tap, without the "Allow Untrusted Shortcuts"
   setting. Signing failure (non-macOS host) falls back to serving the unsigned file
   with an `X-Shortcut-Unsigned: true` header.
3. The file is served as `application/octet-stream` with a `.shortcut`
   `Content-Disposition`, which iOS Safari recognizes as an installable shortcut.
4. The installed shortcut is an `ActionExtension` (appears in the Share Sheet) with
   three actions: a URL action, a `POST` "Get Contents of URL" with
   `Authorization: Bearer <token>` and JSON body `{ input: <shared input> }`, and a
   "Show Notification" confirmation.
5. `POST /api/shortcut` authenticates the bearer token, detects URL vs. text, and
   creates a job.

### Stack translation (Node → Python)

| howlab-tools (Next.js/TS)            | NarrateTTS (FastAPI/Python)                          |
| ------------------------------------ | --------------------------------------------------- |
| `bplist-creator` (npm)               | **`plistlib.dumps(plist, fmt=FMT_BINARY)`** (stdlib)|
| `execFile('/usr/bin/shortcuts', …)`  | `subprocess.run(['/usr/bin/shortcuts', …])`         |
| `api_tokens` table (per-user)        | single global token row in SQLite                   |
| cookie/session auth on GET endpoints | inherits NarrateTTS's no-login posture (tailnet)    |

**No new Python dependencies are required.**

## Architecture

```
iPhone Share Sheet (URL or selected text)
        │
        ▼
 "Send to NarrateTTS" Shortcut ── HTTPS POST ──▶ POST /api/shortcut
   (token baked in)                Authorization: Bearer <token>
        │                          { "input": "<shared>" }
        ▼                                   │
  notification:                      verify_token → 401 if bad
  "🎧 Saved to NarrateTTS"           detect url vs text
                                     reuse existing conversion path
                                     (DEFAULT_VOICE) → add_item (queued)
                                     background Kokoro TTS + summary
                                     auto-categorize → appears in /feed
```

Install path (browser, on the tailnet):

```
Safari (iPhone) → NarrateTTS Settings panel → "Add to iPhone"
        │
        ▼
 GET /api/shortcut → build binary plist (endpoint+token) → sign → serve .shortcut
        │
        ▼
 iOS "Add Shortcut" (one tap)
```

## Components

### 1. `app/shortcuts.py` (new) — plist builder + signer

Pure module, no web framework imports, independently testable.

- `build_shortcut_plist(api_url: str, token: str) -> dict` — returns the workflow
  dict, translated field-for-field from howlab's `buildShortcutPlist`:
  - `WFWorkflowTypes: ["ActionExtension"]`
  - `WFWorkflowInputContentItemClasses: ["WFURLContentItem", "WFStringContentItem"]`
  - Action 1 `is.workflow.actions.url` → `api_url`
  - Action 2 `is.workflow.actions.downloadurl` → `POST`, JSON body
    `{ input: <ExtensionInput token string> }`, header `Authorization: Bearer <token>`
  - Action 3 `is.workflow.actions.notification` → title "NarrateTTS", body
    "Saved to NarrateTTS"
  - Icon: keep howlab's glyph/color or pick a NarrateTTS-appropriate pair (cosmetic).
- `serialize_plist(plist: dict) -> bytes` — `plistlib.dumps(plist, fmt=plistlib.FMT_BINARY)`.
- `sign_shortcut(unsigned: bytes) -> tuple[bytes, bool]` — write to a temp file, run
  `/usr/bin/shortcuts sign --mode anyone --input <in> --output <out>`, read back the
  signed bytes; on any failure return `(unsigned, False)`. Always clean up temp files.

### 2. `app/db.py` — single global token

New table:

```sql
CREATE TABLE IF NOT EXISTS api_token (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    token TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
```

Functions:
- `ensure_token() -> str` — return the existing token, minting one
  (`secrets.token_hex(32)`) on first call. Single row, `id = 1`.
- `regenerate_token() -> str` — replace the row with a fresh token.
- `verify_token(value: str) -> bool` — constant-ish comparison against the stored
  token; `False` if no token exists or `value` is empty.

Created in `init_db()` alongside the existing idempotent migrations.

### 3. `app/config.py` — default voice

- `DEFAULT_VOICE = os.environ.get("TTS_VOICE", "af_heart")` (the env var is already
  present-but-commented in `.env.example`). Used by `/api/shortcut`.

### 4. `app/main.py` — endpoints

- `POST /api/shortcut`
  - Read `Authorization` header; require `Bearer <token>`; `verify_token` → `401`
    on failure.
  - Body `{ "input": str }`; `400` if missing/blank.
  - `is_url = bool(re.match(r'^https?://', input, re.I))`.
  - Reuse the existing conversion logic from `/api/convert` (extract → `add_item` →
    background `_process_tts`) with `voice = DEFAULT_VOICE`. Factor the shared body
    into a helper (e.g. `_create_conversion(url=..., text=..., voice=...)`) so
    `/api/convert` and `/api/shortcut` don't duplicate it.
  - Return `{ "id": id, "status": "queued" }`, `201`.
- `GET /api/shortcut`
  - `token = ensure_token()`.
  - Derive `api_url` from request host (https unless host is localhost/private IP),
    suffix `/api/shortcut`.
  - `build_shortcut_plist → serialize_plist → sign_shortcut`.
  - Respond with the bytes, `Content-Type: application/octet-stream`,
    `Content-Disposition: attachment; filename="SendToNarrate.shortcut"`, and
    `X-Shortcut-Unsigned: true` when signing failed.
- `GET /api/settings/token` → `{ "token": ensure_token() }`.
- `POST /api/settings/token` → `{ "token": regenerate_token() }`.

### 5. `index.html` — Settings panel

- Add a **gear icon** in the header next to the existing `+` button; it toggles a
  slide-down **Settings panel** reusing the `add-panel` styling (hidden by default).
- The panel holds one card replicating the howlab "iOS Shortcut" card:
  - Title "iOS Shortcut" + subtitle "SEND TO NARRATETTS FROM THE SHARE SHEET".
  - One-line instructions ("Open this page in Safari on your iPhone, tap **Add to
    iPhone**, then share any link to **Send to NarrateTTS**…").
  - **Add to iPhone** button → `<a href="/api/shortcut" download="SendToNarrate.shortcut">`.
  - **Endpoint** field (read-only, `origin + /api/shortcut`).
  - **Token** row: masked (`token.slice(0,6) + ••• + token.slice(-4)`) with
    reveal-toggle and copy button (fetched from `GET /api/settings/token`).
  - **Regenerate token** action → `POST /api/settings/token` behind a `confirm()`
    warning that the installed shortcut stops working until re-added.
- Vanilla JS in the existing `<script>` block; no framework, matching the file's
  current style.

## Data flow & error handling

- Capture: `POST /api/shortcut` returns immediately after queuing; background TTS
  runs; the item appears in `/feed` once `completed` and within `FEED_TTL_DAYS`.
- Bad/missing token → `401` (shortcut shows a failure notification — iOS surfaces a
  non-2xx from "Get Contents of URL").
- Extraction failure (bad URL / paywall) → `400`, consistent with `/api/convert`.
- Signing unavailable (non-macOS host) → unsigned `.shortcut` + `X-Shortcut-Unsigned`
  header; the install still works if the user has "Allow Untrusted Shortcuts" on.
  The server is on a Mac, so the expected path is signed.

## Auth boundary (explicit)

- The **capture endpoint (`POST /api/shortcut`) is token-gated** — safe even if
  `narrate.howlab.us` is publicly routable, because the bearer token is required.
- The **shortcut download (`GET /api/shortcut`) and token-settings endpoints inherit
  NarrateTTS's existing no-login posture.** This is acceptable while the web host is
  reachable only inside the tailnet. If the web UI is ever exposed publicly, those
  endpoints would leak the token; adding web-UI auth is **out of scope for this
  slice** and is noted here as a known follow-up.

## Testing

The repo currently has **no test infrastructure**. This slice establishes a minimal
one: add `pytest` to a dev requirements list (or `requirements.txt`), create a
`tests/` directory with a `conftest.py` that points the app at a temporary SQLite DB
(so tests never touch `data/library.db`), and use FastAPI's `TestClient` (httpx is
already a dependency). TTS calls to the external service are stubbed/monkeypatched so
tests never hit the network.

- `app/shortcuts.py`
  - `build_shortcut_plist` embeds the exact `api_url`, `Bearer <token>` header, and
    notification text; input classes/types are present.
  - `serialize_plist` round-trips via `plistlib.loads` to the same dict.
  - `sign_shortcut` fallback returns `(unsigned_bytes, False)` when the CLI is absent
    (test by pointing at a non-existent binary or asserting the except path).
- Endpoints (FastAPI `TestClient`)
  - `POST /api/shortcut`: `401` with no/wrong token; `201` with correct token for
    both a URL input and a text input; `DEFAULT_VOICE` applied; `400` on blank input.
  - `GET /api/settings/token` mints and is stable across calls; `POST` rotates it and
    invalidates the old value (`verify_token(old) == False`).
- Manual acceptance: on the iPhone, Settings → Add to iPhone → install; share a real
  article from Safari; confirm a new library item appears and then shows up in the
  subscribed podcast feed.

## Files touched

- `app/shortcuts.py` (new)
- `app/db.py` (token table + functions)
- `app/config.py` (`DEFAULT_VOICE`)
- `app/main.py` (4 endpoints + shared conversion helper)
- `index.html` (gear icon + Settings panel + token JS)
- `.env.example` (uncomment/document `TTS_VOICE`)
- `tests/` (new: `conftest.py` + `test_shortcuts.py` + `test_shortcut_api.py`),
  `pytest` added to requirements
- `README.md` (capture setup section)
