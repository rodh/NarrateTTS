# Mobile Capture — "Send to NarrateTTS" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one-tap iOS Share-Sheet capture: a signed `.shortcut` with token + endpoint baked in, served from `GET /api/shortcut`, that POSTs shared URLs/text to a token-gated `POST /api/shortcut`.

**Architecture:** Port the proven "Send to Distill" pattern from `howlab-tools` to NarrateTTS's FastAPI/SQLite/vanilla-JS stack. A new `app/shortcuts.py` builds a binary-plist Shortcut via stdlib `plistlib` and signs it via the macOS `shortcuts` CLI. A single global API token lives in SQLite. A shared conversion helper in `app/main.py` backs both `/api/convert` and the new `/api/shortcut`. A gear-panel in `index.html` hosts the "Add to iPhone" card.

**Tech Stack:** Python 3.11, FastAPI, SQLite (stdlib `sqlite3`), stdlib `plistlib`/`secrets`/`subprocess`, pytest + FastAPI `TestClient`, Tailwind (CDN) + vanilla JS. **No new runtime dependencies.**

**Spec:** `docs/plans/2026-06-15-mobile-capture-shortcut-design.md`

---

## File Structure

| File | Responsibility |
| --- | --- |
| `app/shortcuts.py` (new) | Build the Shortcut plist, serialize to binary, sign via CLI. No web/db imports. |
| `app/db.py` (modify) | `api_token` table + `ensure_token` / `regenerate_token` / `verify_token`. |
| `app/main.py` (modify) | `_create_conversion` helper; refactor `/api/convert`; add `/api/shortcut` (POST+GET) and `/api/settings/token` (GET+POST). |
| `index.html` (modify) | Header gear button + Settings panel with the "Add to iPhone" card. |
| `.env.example` (modify) | Document `TTS_VOICE`. |
| `requirements-dev.txt` (new) | `pytest`. |
| `tests/conftest.py` (new) | Temp-DB fixture + `client` fixture with network stubs. |
| `tests/test_shortcuts.py` (new) | Unit tests for `app/shortcuts.py`. |
| `tests/test_token_store.py` (new) | Unit tests for the token store. |
| `tests/test_shortcut_api.py` (new) | API tests for capture + settings + download. |
| `README.md` (modify) | "Capture from your phone" setup section. |

---

## Task 1: Test infrastructure

**Files:**
- Create: `requirements-dev.txt`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Add the dev requirements file**

Create `requirements-dev.txt`:

```
pytest
```

- [ ] **Step 2: Install pytest into the venv**

Run: `.venv/bin/pip install -r requirements-dev.txt`
Expected: installs `pytest` (and `pluggy`/`iniconfig`), ends with "Successfully installed".

- [ ] **Step 3: Create the empty tests package marker**

Create `tests/__init__.py` (empty file).

- [ ] **Step 4: Write `tests/conftest.py`**

The app reads its DB path from the module global `app.db.DB_PATH`. Tests redirect it
to a temp file so they never touch `data/library.db`. The `client` fixture also stubs
the two network calls (`_process_tts` → external TTS, `extract_from_url` → HTTP fetch).

```python
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point the DB at a throwaway file for the duration of a test."""
    import app.db as db
    db_path = tmp_path / "test_library.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    return db_path


@pytest.fixture
def client(temp_db, monkeypatch):
    """A TestClient with the temp DB and all network calls stubbed."""
    import app.main as main

    async def _noop_tts(*args, **kwargs):
        return None

    async def _fake_extract(url):
        return {"title": "Example Article", "text": "Body text here."}

    monkeypatch.setattr(main, "_process_tts", _noop_tts)
    monkeypatch.setattr(main, "extract_from_url", _fake_extract)

    # Entering the context manager runs the startup event → init_db() on temp DB.
    with TestClient(main.app) as c:
        yield c
```

- [ ] **Step 5: Write a smoke test**

Create `tests/test_smoke.py`:

```python
def test_voices_endpoint_works(client):
    resp = client.get("/api/voices")
    assert resp.status_code == 200
    assert "voices" in resp.json()
```

- [ ] **Step 6: Run the smoke test**

Run: `.venv/bin/python -m pytest tests/test_smoke.py -v`
Expected: 1 passed. (Confirms the fixtures, temp DB, and startup wiring all work.)

- [ ] **Step 7: Commit**

```bash
git add requirements-dev.txt tests/__init__.py tests/conftest.py tests/test_smoke.py
git commit -m "test: add pytest infrastructure with temp-db + stubbed client fixtures"
```

---

## Task 2: Token store in `app/db.py`

**Files:**
- Modify: `app/db.py` (add table to `init_db`; add three functions)
- Create: `tests/test_token_store.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_token_store.py`:

```python
def test_ensure_token_mints_and_is_stable(temp_db):
    from app.db import init_db, ensure_token
    init_db()
    t1 = ensure_token()
    t2 = ensure_token()
    assert t1 == t2
    assert len(t1) == 64  # secrets.token_hex(32)


def test_regenerate_changes_token_and_invalidates_old(temp_db):
    from app.db import init_db, ensure_token, regenerate_token, verify_token
    init_db()
    old = ensure_token()
    new = regenerate_token()
    assert new != old
    assert verify_token(new) is True
    assert verify_token(old) is False


def test_verify_token_rejects_empty_and_wrong(temp_db):
    from app.db import init_db, ensure_token, verify_token
    init_db()
    ensure_token()
    assert verify_token("") is False
    assert verify_token("not-the-token") is False
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_token_store.py -v`
Expected: FAIL with `ImportError: cannot import name 'ensure_token'`.

- [ ] **Step 3: Add the `api_token` table to `init_db`**

In `app/db.py`, inside the `conn.executescript("""...""")` block in `init_db()`, add
this table definition (alongside the existing `items`/`playlists` tables):

```sql
        CREATE TABLE IF NOT EXISTS api_token (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            token TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
```

- [ ] **Step 4: Add the token functions**

At the top of `app/db.py`, add to the imports:

```python
import secrets
import hmac
```

At the end of `app/db.py`, add:

```python
# --- API Token (single global token for shortcut capture) ---


def ensure_token() -> str:
    """Return the API token, minting one on first use."""
    conn = get_connection()
    row = conn.execute("SELECT token FROM api_token WHERE id = 1").fetchone()
    if row:
        conn.close()
        return row["token"]
    token = secrets.token_hex(32)
    conn.execute("INSERT INTO api_token (id, token) VALUES (1, ?)", (token,))
    conn.commit()
    conn.close()
    return token


def regenerate_token() -> str:
    """Replace the token with a fresh one, invalidating any installed shortcut."""
    token = secrets.token_hex(32)
    conn = get_connection()
    conn.execute(
        "INSERT INTO api_token (id, token, created_at) VALUES (1, ?, datetime('now')) "
        "ON CONFLICT(id) DO UPDATE SET token = excluded.token, created_at = excluded.created_at",
        (token,),
    )
    conn.commit()
    conn.close()
    return token


def verify_token(value: str) -> bool:
    """Constant-time check of a presented token against the stored one."""
    if not value:
        return False
    conn = get_connection()
    row = conn.execute("SELECT token FROM api_token WHERE id = 1").fetchone()
    conn.close()
    if not row:
        return False
    return hmac.compare_digest(value, row["token"])
```

- [ ] **Step 5: Run to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_token_store.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add app/db.py tests/test_token_store.py
git commit -m "feat: add single global API token store in db"
```

---

## Task 3: Settings token endpoints

**Files:**
- Modify: `app/main.py` (import token functions; add two routes)
- Create: `tests/test_shortcut_api.py` (first tests)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_shortcut_api.py`:

```python
def test_get_token_mints_and_is_stable(client):
    r1 = client.get("/api/settings/token")
    assert r1.status_code == 200
    t1 = r1.json()["token"]
    assert len(t1) == 64
    t2 = client.get("/api/settings/token").json()["token"]
    assert t1 == t2


def test_post_token_regenerates(client):
    old = client.get("/api/settings/token").json()["token"]
    new = client.post("/api/settings/token").json()["token"]
    assert new != old
    assert client.get("/api/settings/token").json()["token"] == new
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_shortcut_api.py -v`
Expected: FAIL with 404 (routes don't exist yet).

- [ ] **Step 3: Import the token functions in `app/main.py`**

In `app/main.py`, extend the existing `from app.db import (...)` block to also import:

```python
    ensure_token, regenerate_token, verify_token,
```

- [ ] **Step 4: Add the settings routes**

In `app/main.py`, after the playlist API routes (before the `# --- Backfill ---`
section), add:

```python
# --- Settings: API token ---


@app.get("/api/settings/token")
async def api_get_token():
    return {"token": ensure_token()}


@app.post("/api/settings/token")
async def api_regenerate_token():
    return {"token": regenerate_token()}
```

- [ ] **Step 5: Run to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_shortcut_api.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_shortcut_api.py
git commit -m "feat: add GET/POST /api/settings/token endpoints"
```

---

## Task 4: Shared conversion helper + refactor `/api/convert`

This extracts the existing convert logic into a reusable helper with **no behavior
change**, so the new capture endpoint can share it.

**Files:**
- Modify: `app/main.py` (add `_create_conversion`; slim down `api_convert`; import `DEFAULT_VOICE`)
- Modify: `tests/test_shortcut_api.py` (add a regression test for `/api/convert`)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_shortcut_api.py`:

```python
def test_convert_text_still_works(client):
    resp = client.post("/api/convert", json={"text": "Hello world from a test."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "queued"
    assert isinstance(body["id"], int)


def test_convert_url_uses_stubbed_extractor(client):
    resp = client.post("/api/convert", json={"url": "https://example.com/article"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "queued"


def test_convert_requires_url_or_text(client):
    resp = client.post("/api/convert", json={})
    assert resp.status_code == 400
```

- [ ] **Step 2: Run to verify the new tests pass or fail meaningfully**

Run: `.venv/bin/python -m pytest tests/test_shortcut_api.py -v -k convert`
Expected: the three `convert` tests PASS (current `/api/convert` already behaves this
way). This locks current behavior before refactoring.

- [ ] **Step 3: Import `DEFAULT_VOICE`**

In `app/main.py`, extend the `from app.config import (...)` line to include
`DEFAULT_VOICE`:

```python
from app.config import HOST, PORT, AUDIO_DIR, STATIC_DIR, TTS_SERVICE_URL, KOKORO_MODEL, KOKORO_VOICES, FEED_TTL_DAYS, DEFAULT_VOICE
```

- [ ] **Step 4: Add the `_create_conversion` helper**

In `app/main.py`, immediately above the existing `@app.post("/api/convert")` route,
add:

```python
async def _create_conversion(url: str | None, text_input: str | None, voice: str) -> dict:
    """Extract content, create a queued item, and kick off background TTS."""
    if url:
        try:
            extracted = await extract_from_url(url)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to extract content: {str(e)}")
    elif text_input:
        extracted = extract_from_text(text_input)
    else:
        raise HTTPException(status_code=400, detail="Provide 'url' or 'text'")

    title = extracted["title"]
    text = extracted["text"]
    item_id = add_item(source_url=url, title=title, text=text)
    asyncio.create_task(_process_tts(item_id, text, title, url, voice))
    return {"id": item_id, "status": "queued"}
```

- [ ] **Step 5: Replace the body of `api_convert`**

In `app/main.py`, replace the existing `api_convert` function body so it delegates to
the helper:

```python
@app.post("/api/convert")
async def api_convert(payload: dict):
    """Convert text or URL to audio.

    Body: {"url": "https://..."} or {"text": "hello world"}
    """
    source_url = payload.get("url")
    text_input = payload.get("text")
    voice = payload.get("voice") or DEFAULT_VOICE
    return await _create_conversion(source_url, text_input, voice)
```

- [ ] **Step 6: Run the full API test file**

Run: `.venv/bin/python -m pytest tests/test_shortcut_api.py -v`
Expected: all tests pass (settings + convert), confirming the refactor preserved behavior.

- [ ] **Step 7: Commit**

```bash
git add app/main.py tests/test_shortcut_api.py
git commit -m "refactor: extract _create_conversion helper shared by convert"
```

---

## Task 5: Capture endpoint `POST /api/shortcut`

**Files:**
- Modify: `app/main.py` (add `re` + `Header` imports; add the route)
- Modify: `tests/test_shortcut_api.py` (add capture tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_shortcut_api.py`:

```python
def _token(client):
    return client.get("/api/settings/token").json()["token"]


def test_shortcut_rejects_missing_token(client):
    resp = client.post("/api/shortcut", json={"input": "https://example.com"})
    assert resp.status_code == 401


def test_shortcut_rejects_wrong_token(client):
    _token(client)  # ensure one exists
    resp = client.post(
        "/api/shortcut",
        json={"input": "https://example.com"},
        headers={"Authorization": "Bearer wrong"},
    )
    assert resp.status_code == 401


def test_shortcut_accepts_url_with_valid_token(client):
    token = _token(client)
    resp = client.post(
        "/api/shortcut",
        json={"input": "https://example.com/article"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "queued"


def test_shortcut_accepts_text_with_valid_token(client):
    token = _token(client)
    resp = client.post(
        "/api/shortcut",
        json={"input": "Just some plain text to narrate."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201


def test_shortcut_rejects_blank_input(client):
    token = _token(client)
    resp = client.post(
        "/api/shortcut",
        json={"input": "   "},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_shortcut_api.py -v -k shortcut`
Expected: FAIL with 404 / 405 (route not defined).

- [ ] **Step 3: Add imports to `app/main.py`**

Add a top-level `import re` near the other stdlib imports. Extend the FastAPI import
line to include `Header`:

```python
from fastapi import FastAPI, HTTPException, Request, Header
```

- [ ] **Step 4: Add the capture route**

In `app/main.py`, immediately after `_create_conversion` (and after `api_convert`),
add:

```python
@app.post("/api/shortcut", status_code=201)
async def api_shortcut(payload: dict, authorization: str | None = Header(default=None)):
    """Token-gated capture endpoint for the iOS Shortcut. Body: {"input": "<url or text>"}."""
    token = ""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not verify_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")

    raw = payload.get("input")
    input_str = raw.strip() if isinstance(raw, str) else ""
    if not input_str:
        raise HTTPException(status_code=400, detail="input is required")

    is_url = bool(re.match(r"^https?://", input_str, re.IGNORECASE))
    return await _create_conversion(
        url=input_str if is_url else None,
        text_input=None if is_url else input_str,
        voice=DEFAULT_VOICE,
    )
```

- [ ] **Step 5: Run to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_shortcut_api.py -v -k shortcut`
Expected: all 5 capture tests pass.

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_shortcut_api.py
git commit -m "feat: add token-gated POST /api/shortcut capture endpoint"
```

---

## Task 6: Plist builder + signer (`app/shortcuts.py`)

**Files:**
- Create: `app/shortcuts.py`
- Create: `tests/test_shortcuts.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_shortcuts.py`:

```python
import plistlib

from app.shortcuts import build_shortcut_plist, serialize_plist, sign_shortcut


def test_plist_embeds_url_and_token():
    plist = build_shortcut_plist("https://narrate.example/api/shortcut", "abc123")
    assert plist["WFWorkflowTypes"] == ["ActionExtension"]
    assert "WFURLContentItem" in plist["WFWorkflowInputContentItemClasses"]

    actions = plist["WFWorkflowActions"]
    url_action = actions[0]["WFWorkflowActionParameters"]["WFURLActionURL"]
    assert url_action == "https://narrate.example/api/shortcut"

    headers = actions[1]["WFWorkflowActionParameters"]["WFHTTPHeaders"]["Value"][
        "WFDictionaryFieldValueItems"
    ]
    auth_value = headers[0]["WFValue"]["Value"]["string"]
    assert auth_value == "Bearer abc123"


def test_serialize_roundtrips_to_binary_plist():
    plist = build_shortcut_plist("https://x/api/shortcut", "tok")
    data = serialize_plist(plist)
    assert isinstance(data, (bytes, bytearray))
    parsed = plistlib.loads(bytes(data))
    assert parsed["WFWorkflowActions"][0]["WFWorkflowActionParameters"]["WFURLActionURL"] == "https://x/api/shortcut"


def test_sign_falls_back_when_cli_unavailable(monkeypatch):
    import app.shortcuts as shortcuts

    def _boom(*args, **kwargs):
        raise FileNotFoundError("no shortcuts binary")

    monkeypatch.setattr(shortcuts.subprocess, "run", _boom)
    payload = b"unsigned-bytes"
    signed, did_sign = sign_shortcut(payload)
    assert signed == payload
    assert did_sign is False
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_shortcuts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.shortcuts'`.

- [ ] **Step 3: Create `app/shortcuts.py`**

```python
"""Build and sign a 'Send to NarrateTTS' iOS Shortcut.

Ports the buildShortcutPlist/sign logic from howlab-tools to Python: the workflow
is an ActionExtension (appears in the Share Sheet) that POSTs the shared input to
/api/shortcut with the API token baked in as a Bearer header. The binary plist is
produced with the stdlib plistlib; signing shells out to the macOS `shortcuts` CLI
so the resulting file installs without "Allow Untrusted Shortcuts".
"""

import plistlib
import subprocess
import tempfile
from pathlib import Path


def build_shortcut_plist(api_url: str, token: str) -> dict:
    """Return the Shortcut workflow dict with the endpoint and token embedded."""
    extension_input = {
        "Value": {
            "string": "￼",  # Object Replacement Character = the shared input
            "attachmentsByRange": {"{0, 1}": {"Type": "ExtensionInput"}},
        },
        "WFSerializationType": "WFTextTokenString",
    }

    return {
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowIcon": {
            "WFWorkflowIconStartColor": 4282601983,
            "WFWorkflowIconGlyphNumber": 59765,
        },
        "WFWorkflowTypes": ["ActionExtension"],
        "WFWorkflowInputContentItemClasses": [
            "WFURLContentItem",
            "WFStringContentItem",
        ],
        "WFWorkflowActions": [
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.url",
                "WFWorkflowActionParameters": {"WFURLActionURL": api_url},
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
                "WFWorkflowActionParameters": {
                    "WFHTTPMethod": "POST",
                    "WFHTTPBodyType": "JSON",
                    "WFHTTPHeaders": {
                        "Value": {
                            "WFDictionaryFieldValueItems": [
                                {
                                    "WFItemType": 0,
                                    "WFKey": {
                                        "Value": {"string": "Authorization"},
                                        "WFSerializationType": "WFTextTokenString",
                                    },
                                    "WFValue": {
                                        "Value": {"string": f"Bearer {token}"},
                                        "WFSerializationType": "WFTextTokenString",
                                    },
                                }
                            ]
                        },
                        "WFSerializationType": "WFDictionaryFieldValue",
                    },
                    "WFJSONValues": {
                        "Value": {
                            "WFDictionaryFieldValueItems": [
                                {
                                    "WFItemType": 0,
                                    "WFKey": {
                                        "Value": {"string": "input"},
                                        "WFSerializationType": "WFTextTokenString",
                                    },
                                    "WFValue": extension_input,
                                }
                            ]
                        },
                        "WFSerializationType": "WFDictionaryFieldValue",
                    },
                },
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.notification",
                "WFWorkflowActionParameters": {
                    "WFNotificationActionBody": "Saved to NarrateTTS",
                    "WFNotificationActionTitle": "NarrateTTS",
                },
            },
        ],
    }


def serialize_plist(plist: dict) -> bytes:
    """Serialize the workflow dict to a binary plist (.shortcut payload)."""
    return plistlib.dumps(plist, fmt=plistlib.FMT_BINARY)


def sign_shortcut(unsigned: bytes) -> tuple[bytes, bool]:
    """Sign the shortcut via the macOS CLI. Returns (bytes, did_sign).

    Falls back to the unsigned bytes (did_sign=False) on any failure, e.g. when the
    server is not macOS or the CLI is unavailable.
    """
    tmp = Path(tempfile.mkdtemp(prefix="narrate-shortcut-"))
    unsigned_path = tmp / "unsigned.shortcut"
    signed_path = tmp / "signed.shortcut"
    try:
        unsigned_path.write_bytes(unsigned)
        subprocess.run(
            [
                "/usr/bin/shortcuts",
                "sign",
                "--mode",
                "anyone",
                "--input",
                str(unsigned_path),
                "--output",
                str(signed_path),
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        return signed_path.read_bytes(), True
    except Exception:
        return unsigned, False
    finally:
        unsigned_path.unlink(missing_ok=True)
        signed_path.unlink(missing_ok=True)
        try:
            tmp.rmdir()
        except OSError:
            pass
```

- [ ] **Step 4: Run to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_shortcuts.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/shortcuts.py tests/test_shortcuts.py
git commit -m "feat: add shortcut plist builder and CLI signer"
```

---

## Task 7: Shortcut download `GET /api/shortcut`

**Files:**
- Modify: `app/main.py` (import builder/signer; add the GET route)
- Modify: `tests/test_shortcut_api.py` (add download tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_shortcut_api.py`:

```python
import plistlib


def test_download_returns_signed_or_unsigned_shortcut(client):
    resp = client.get("/api/shortcut")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/octet-stream")
    assert "SendToNarrate.shortcut" in resp.headers["content-disposition"]
    assert len(resp.content) > 0


def test_download_embeds_current_token_when_unsigned(client, monkeypatch):
    # Force the unsigned path so we can parse the plist back out and assert the token.
    import app.main as main
    monkeypatch.setattr(main, "sign_shortcut", lambda data: (data, False))

    token = client.get("/api/settings/token").json()["token"]
    resp = client.get("/api/shortcut")
    assert resp.headers.get("x-shortcut-unsigned") == "true"

    plist = plistlib.loads(resp.content)
    headers = plist["WFWorkflowActions"][1]["WFWorkflowActionParameters"]["WFHTTPHeaders"][
        "Value"
    ]["WFDictionaryFieldValueItems"]
    assert headers[0]["WFValue"]["Value"]["string"] == f"Bearer {token}"
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_shortcut_api.py -v -k download`
Expected: FAIL — the `GET /api/shortcut` route returns 405 (only POST exists).

- [ ] **Step 3: Import the builder/signer in `app/main.py`**

Add near the other `app.*` imports:

```python
from app.shortcuts import build_shortcut_plist, serialize_plist, sign_shortcut
```

- [ ] **Step 4: Add the GET route**

In `app/main.py`, directly below the `api_shortcut` POST route, add:

```python
def _api_base_url(request: Request) -> str:
    """Reconstruct the externally-visible base URL (honours reverse-proxy headers)."""
    host = request.headers.get(
        "x-forwarded-host", request.headers.get("host", "localhost:8090")
    )
    proto = request.headers.get("x-forwarded-proto")
    if not proto:
        private = host.startswith(("localhost", "127.", "192.168.", "10.", "172."))
        proto = "http" if private else "https"
    return f"{proto}://{host}"


@app.get("/api/shortcut")
async def get_shortcut(request: Request):
    """Serve a 'Send to NarrateTTS' .shortcut with the API token baked in."""
    token = ensure_token()
    api_url = f"{_api_base_url(request)}/api/shortcut"
    plist = build_shortcut_plist(api_url, token)
    signed, did_sign = sign_shortcut(serialize_plist(plist))

    headers = {
        "Content-Disposition": 'attachment; filename="SendToNarrate.shortcut"',
    }
    if not did_sign:
        headers["X-Shortcut-Unsigned"] = "true"
    return Response(
        content=signed,
        media_type="application/octet-stream",
        headers=headers,
    )
```

- [ ] **Step 5: Run to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_shortcut_api.py -v -k download`
Expected: 2 passed.

- [ ] **Step 6: Run the whole suite**

Run: `.venv/bin/python -m pytest -v`
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add app/main.py tests/test_shortcut_api.py
git commit -m "feat: add GET /api/shortcut to download the signed shortcut"
```

---

## Task 8: Web UI — gear button + Settings panel

No automated test (vanilla-JS UI); verified manually in Step 5.

**Files:**
- Modify: `index.html` (header button; settings panel markup; JS functions)

- [ ] **Step 1: Add the gear button to the header**

In `index.html`, inside the header's right-hand `<div class="flex items-center gap-2">`
(the one containing the search input and `add-btn`), add a gear button immediately
before the `add-btn` button:

```html
            <button onclick="toggleSettingsPanel()" id="settings-btn" class="w-8 h-8 flex items-center justify-center rounded-lg bg-[var(--bg-button)] hover:bg-[var(--bg-button-hover)] text-[var(--text-secondary)] hover:text-[var(--text-accent)] transition" title="Settings">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
            </button>
```

- [ ] **Step 2: Add the Settings panel markup**

In `index.html`, immediately after the closing `</div>` of the `add-panel` block (the
`<div id="add-panel" ...> ... </div>`), add:

```html
    <!-- Settings Panel (dropdown) -->
    <div id="settings-panel" class="hidden border-b border-[var(--border)] bg-[var(--bg-panel)] px-4 sm:px-6 py-4 overflow-hidden">
        <div class="max-w-md">
            <div class="flex items-start justify-between gap-4">
                <div>
                    <p class="text-sm font-semibold">iOS Shortcut</p>
                    <p class="text-[11px] uppercase tracking-wide text-[var(--text-faint)] mt-0.5">Send to NarrateTTS from the share sheet</p>
                    <p class="text-sm text-[var(--text-secondary)] mt-2">Open this page in Safari on your iPhone, tap <span class="text-[var(--text-accent)] font-medium">Add to iPhone</span>, then share any link to <span class="text-[var(--text-accent)] font-medium">Send to NarrateTTS</span> — it captures with your token baked in.</p>
                </div>
                <a href="/api/shortcut" download="SendToNarrate.shortcut" class="shrink-0 inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[var(--accent-bg)] text-[var(--accent-text)] font-medium text-sm hover:opacity-80 transition no-underline">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="7" y="2" width="10" height="20" rx="2"/><path stroke-linecap="round" d="M11 18h2"/></svg>
                    Add to iPhone
                </a>
            </div>
            <div class="mt-3 rounded-lg border border-[var(--border-input)] bg-[var(--bg-input)] px-3 py-2">
                <p class="text-[11px] uppercase tracking-wide text-[var(--text-faint)]">Endpoint</p>
                <p id="settings-endpoint" class="font-mono text-xs text-[var(--text-secondary)] truncate">…</p>
            </div>
            <div class="mt-2 flex items-center justify-between gap-2 rounded-lg border border-[var(--border-input)] bg-[var(--bg-input)] px-3 py-2">
                <div class="min-w-0">
                    <p class="text-[11px] uppercase tracking-wide text-[var(--text-faint)]">Token</p>
                    <p id="settings-token" class="font-mono text-xs text-[var(--text-secondary)] truncate">…</p>
                </div>
                <div class="flex items-center gap-1 shrink-0">
                    <button onclick="toggleTokenReveal()" id="token-reveal-btn" class="p-1.5 rounded-md text-[var(--text-faint)] hover:text-[var(--text-accent)] transition" title="Show token">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>
                    </button>
                    <button onclick="copyToken()" id="token-copy-btn" class="p-1.5 rounded-md text-[var(--text-faint)] hover:text-[var(--text-accent)] transition" title="Copy token">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2"/><path stroke-linecap="round" stroke-linejoin="round" d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
                    </button>
                </div>
            </div>
            <button onclick="regenerateToken()" class="mt-2 inline-flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-[var(--text-faint)] hover:text-[var(--text-secondary)] transition">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h5M20 20v-5h-5"/><path stroke-linecap="round" stroke-linejoin="round" d="M20.49 9A9 9 0 105.64 5.64L4 4m16 16l-1.64-1.64A9 9 0 0020.49 9"/></svg>
                Regenerate token
            </button>
        </div>
    </div>
```

- [ ] **Step 3: Add the Settings JS**

In `index.html`, inside the `<script>` block, just before the `// --- Init ---`
comment near the bottom, add:

```javascript
        // --- Settings / Shortcut token ---

        let shortcutToken = null;
        let tokenRevealed = false;

        function renderToken() {
            const el = document.getElementById('settings-token');
            if (!shortcutToken) { el.textContent = '…'; return; }
            el.textContent = tokenRevealed
                ? shortcutToken
                : shortcutToken.slice(0, 6) + '•'.repeat(18) + shortcutToken.slice(-4);
        }

        async function loadShortcutToken() {
            document.getElementById('settings-endpoint').textContent = location.origin + '/api/shortcut';
            try {
                const res = await fetch('/api/settings/token');
                const data = await res.json();
                shortcutToken = data.token;
                renderToken();
            } catch (e) {
                console.error('Failed to load token:', e);
            }
        }

        function toggleSettingsPanel() {
            const panel = document.getElementById('settings-panel');
            const isHidden = panel.classList.toggle('hidden');
            if (!isHidden) loadShortcutToken();
        }

        function toggleTokenReveal() {
            tokenRevealed = !tokenRevealed;
            renderToken();
        }

        function copyToken() {
            if (!shortcutToken) return;
            navigator.clipboard.writeText(shortcutToken).then(() => {
                const btn = document.getElementById('token-copy-btn');
                btn.classList.add('text-[var(--text-accent)]');
                setTimeout(() => btn.classList.remove('text-[var(--text-accent)]'), 1200);
            });
        }

        async function regenerateToken() {
            if (!confirm('Regenerate token? The shortcut already installed on your phone will stop working until you re-add it.')) return;
            try {
                const res = await fetch('/api/settings/token', { method: 'POST' });
                const data = await res.json();
                shortcutToken = data.token;
                tokenRevealed = true;
                renderToken();
            } catch (e) {
                console.error('Regenerate failed:', e);
            }
        }
```

- [ ] **Step 4: Start the app**

Run: `./start.sh` (or however the app is normally launched). Leave it running.

- [ ] **Step 5: Manual verification**

In a desktop browser at `http://localhost:8090`:
1. Click the gear icon → the Settings panel slides down.
2. The Endpoint shows `.../api/shortcut`; the Token shows masked (`abc123••••…`).
3. Click the eye → token reveals; click copy → paste elsewhere to confirm it copied.
4. Click **Add to iPhone** → a `SendToNarrate.shortcut` file downloads.
5. Click **Regenerate token** → confirm dialog → token changes and reveals.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "feat: add Settings panel with Add to iPhone shortcut card"
```

---

## Task 9: Docs

**Files:**
- Modify: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: Document `TTS_VOICE` in `.env.example`**

In `.env.example`, under the TTS section, uncomment/clarify the default-voice line so
it reads:

```
# Default voice used for shortcut/share-sheet captures (web UI can still pick per-item)
TTS_VOICE=af_heart
```

- [ ] **Step 2: Add a capture section to `README.md`**

Add this section to `README.md` (after "How It Works"):

```markdown
## Capture from your phone (iOS Shortcut)

NarrateTTS can capture straight from the iOS Share Sheet:

1. Open NarrateTTS in **Safari on your iPhone**.
2. Tap the **gear icon → Add to iPhone**. iOS installs the *Send to NarrateTTS*
   shortcut (the API token is baked in — no setup).
3. From any app, **Share → Send to NarrateTTS** to narrate a link or selected text.

The shortcut POSTs to the token-gated `POST /api/shortcut`. If you ever need to
rotate the token, use **Regenerate token** in the gear panel, then re-add the
shortcut on your phone.

> The "Add to iPhone" install signs the shortcut via the macOS `shortcuts` CLI, so
> the server must run on macOS for one-tap install. On other platforms the file is
> served unsigned (requires Settings → Shortcuts → *Allow Untrusted Shortcuts*).
```

- [ ] **Step 3: Commit**

```bash
git add .env.example README.md
git commit -m "docs: document TTS_VOICE and the iOS capture shortcut"
```

---

## Task 10: Final verification

- [ ] **Step 1: Run the full test suite**

Run: `.venv/bin/python -m pytest -v`
Expected: all tests pass (`test_smoke`, `test_token_store`, `test_shortcuts`,
`test_shortcut_api`).

- [ ] **Step 2: End-to-end manual acceptance (on the phone)**

1. On the iPhone (on the tailnet), open `https://narrate.howlab.us` in Safari.
2. Gear → **Add to iPhone** → install the shortcut.
3. Open an article in Safari → **Share → Send to NarrateTTS** → see the
   "Saved to NarrateTTS" notification.
4. Back in the web Library, confirm a new item appears and processes to `completed`.
5. Confirm it shows up in your subscribed podcast feed.

- [ ] **Step 3: Confirm signing worked (server on macOS)**

Run: `curl -sD - -o /dev/null http://localhost:8090/api/shortcut | grep -i x-shortcut-unsigned`
Expected: **no output** (header absent → the shortcut was signed). If the header is
present, signing failed — check that `/usr/bin/shortcuts` exists and the server runs
on macOS.

---

## Notes for the implementer

- **DB safety:** tests must never write to `data/library.db`; the `temp_db` fixture
  enforces this by patching `app.db.DB_PATH`. Never remove that patch.
- **No new runtime deps:** everything uses the stdlib (`plistlib`, `secrets`, `hmac`,
  `subprocess`, `re`). Only `pytest` is added, dev-only.
- **Auth boundary (known limitation):** `POST /api/shortcut` is token-gated, but the
  download + token-settings endpoints rely on the host being tailnet-only. Web-UI
  auth is intentionally out of scope for this slice.
