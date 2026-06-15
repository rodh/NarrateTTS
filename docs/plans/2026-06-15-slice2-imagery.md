# Slice 2 — Imagery Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** Capture each article's `og:image` and give the UI helpers to render item art — the article photo when present, otherwise a deterministic source gradient + favicon — and show that art as a thumbnail on library rows.

**Architecture:** Backend parses `og:image`/`twitter:image` during extraction and stores it on the item (`items.image_url`, threaded through `add_item` and `_create_conversion`). A new `static/js/imagery.js` provides `faviconUrl`, `gradientFor`, and `itemArt(item)`; the library render uses `itemArt` for a thumbnail. Waveform peaks are NOT in this slice (built in Slice 5 with the Now-Playing screen).

**Tech Stack:** FastAPI, SQLite, `urllib.parse`, regex; vanilla ES modules.

**Spec:** `docs/plans/2026-06-15-player-forward-redesign-design.md` (Imagery pipeline).

---

## File Structure

| File | Responsibility |
| --- | --- |
| `app/extractor.py` (modify) | `_extract_og_image(html, base_url)`; `extract_from_url` returns `image_url`. |
| `app/db.py` (modify) | `items.image_url` column (migration); `add_item(... image_url=None)`. |
| `app/main.py` (modify) | `_create_conversion` threads `image_url` into `add_item`. |
| `static/js/imagery.js` (new) | `faviconUrl(url)`, `gradientFor(url)`, `itemArt(item)`. |
| `static/js/library.js` (modify) | Render an item thumbnail via `itemArt`. |
| `tests/test_imagery.py` (new) | og:image parsing + add_item persistence. |

---

## Task 1: Parse og:image during extraction

**Files:** Modify `app/extractor.py`; Create `tests/test_imagery.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_imagery.py
from app.extractor import _extract_og_image

def test_extracts_og_image():
    html = '<html><head><meta property="og:image" content="https://x.com/a.jpg"></head></html>'
    assert _extract_og_image(html, "https://x.com/post") == "https://x.com/a.jpg"

def test_falls_back_to_twitter_image():
    html = '<meta name="twitter:image" content="/rel/b.png">'
    assert _extract_og_image(html, "https://x.com/post") == "https://x.com/rel/b.png"

def test_returns_none_when_absent():
    assert _extract_og_image("<html><head></head></html>", "https://x.com/post") is None
```

- [ ] **Step 2: Run → fail**

Run: `.venv/bin/python -m pytest tests/test_imagery.py -q`
Expected: ImportError (`_extract_og_image` not defined).

- [ ] **Step 3: Implement**

In `app/extractor.py`, add `from urllib.parse import urljoin` (top, alongside the
existing `urlparse` import) and:

```python
def _extract_og_image(html: str, base_url: str) -> str | None:
    """Find an og:image / twitter:image URL in page HTML, resolved to absolute."""
    import re
    for prop in ("og:image", "twitter:image", "twitter:image:src"):
        p = re.escape(prop)
        m = (re.search(r'<meta[^>]+(?:property|name)=["\']' + p + r'["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
             or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']' + p + r'["\']', html, re.I))
        if m:
            return urljoin(base_url, m.group(1).strip())
    return None
```

Then in `extract_from_url`, after computing `text`, also compute the image and include
it in the return dict:

```python
    image_url = _extract_og_image(response.text, url)
    return {"title": title, "text": text.strip(), "image_url": image_url}
```

- [ ] **Step 4: Run → pass**

Run: `.venv/bin/python -m pytest tests/test_imagery.py -q`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/extractor.py tests/test_imagery.py
git commit -m "feat: extract og:image during url extraction"
```

---

## Task 2: Persist image_url on items

**Files:** Modify `app/db.py`, `app/main.py`; extend `tests/test_imagery.py`

- [ ] **Step 1: Write failing test**

```python
# append to tests/test_imagery.py
def test_add_item_persists_image_url(temp_db):
    from app.db import init_db, add_item, get_item
    init_db()
    iid = add_item(source_url="https://x.com/p", title="T", text="body", image_url="https://x.com/a.jpg")
    assert get_item(iid)["image_url"] == "https://x.com/a.jpg"
```

- [ ] **Step 2: Run → fail**

Run: `.venv/bin/python -m pytest tests/test_imagery.py::test_add_item_persists_image_url -q`
Expected: fail (`add_item` has no `image_url`; column missing).

- [ ] **Step 3: Implement migration + add_item**

In `app/db.py` `init_db()`, add an idempotent migration alongside the existing ones:

```python
    try:
        conn.execute("ALTER TABLE items ADD COLUMN image_url TEXT")
        conn.commit()
    except Exception:
        pass
```

Update `add_item` to accept and store it:

```python
def add_item(source_url: str | None, title: str, text: str, status: str = "queued", image_url: str | None = None) -> int:
    word_count = len(text.split())
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO items (source_url, title, text, word_count, status, image_url)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (source_url, title, text, word_count, status, image_url),
    )
    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return item_id
```

- [ ] **Step 4: Thread image_url through `_create_conversion`**

In `app/main.py` `_create_conversion`, pass the extracted image through (the text path
has no image):

```python
    title = extracted["title"]
    text = extracted["text"]
    item_id = add_item(source_url=url, title=title, text=text, image_url=extracted.get("image_url"))
```

- [ ] **Step 5: Run → pass + full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass (29+).

- [ ] **Step 6: Commit**

```bash
git add app/db.py app/main.py tests/test_imagery.py
git commit -m "feat: persist image_url on items, thread through conversion"
```

---

## Task 3: Front-end imagery helpers + library thumbnails

**Files:** Create `static/js/imagery.js`; Modify `static/js/library.js`

- [ ] **Step 1: Create `static/js/imagery.js`**

```js
// Deterministic source-derived art with og:image override.
function domainOf(url) {
  try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return ''; }
}
function hashStr(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return Math.abs(h); }

export function faviconUrl(sourceUrl) {
  const d = domainOf(sourceUrl);
  return d ? `https://www.google.com/s2/favicons?domain=${d}&sz=64` : '';
}

const PALETTES = [
  ['#f1582c', '#b51d6e'], ['#2563eb', '#06b6d4'], ['#16a34a', '#84cc16'],
  ['#7c3aed', '#ec4899'], ['#0891b2', '#3b82f6'], ['#ea580c', '#facc15'],
];
export function gradientFor(sourceUrl) {
  const [a, b] = PALETTES[hashStr(domainOf(sourceUrl) || 'text') % PALETTES.length];
  return `linear-gradient(135deg, ${a}, ${b})`;
}

export function letterFor(item) {
  const d = domainOf(item.source_url || '');
  return (d ? d[0] : (item.title || '?')[0]).toUpperCase();
}

// Returns an HTML string for a square art tile of the given pixel size.
export function itemArt(item, size = 44) {
  const r = Math.round(size * 0.27);
  if (item.image_url) {
    return `<div style="width:${size}px;height:${size}px;border-radius:${r}px;background:url('${item.image_url}') center/cover;flex:0 0 auto"></div>`;
  }
  const fav = faviconUrl(item.source_url || '');
  const favHtml = fav ? `<img src="${fav}" style="width:18px;height:18px;border-radius:5px" onerror="this.style.display='none'">` : '';
  return `<div style="width:${size}px;height:${size}px;border-radius:${r}px;background:${gradientFor(item.source_url || '')};display:flex;align-items:center;justify-content:center;flex:0 0 auto">${favHtml || `<span style="color:#fff;font-weight:700">${letterFor(item)}</span>`}</div>`;
}
```

- [ ] **Step 2: Show a thumbnail in the library render**

In `static/js/library.js`, `import { itemArt } from './imagery.js';` and in the item-row
template, insert `${itemArt(item)}` at the start of the row's flex content (before the
title block), so each row leads with the art tile. Keep all other markup/behavior.

- [ ] **Step 3: Commit**

```bash
git add static/js/imagery.js static/js/library.js
git commit -m "feat(ui): source-derived item art (gradient+favicon, og:image when present)"
```

---

## Task 4: Verify

- [ ] **Step 1: Restart server + asset check**

```bash
OLD=$(lsof -nP -iTCP:8090 -sTCP:LISTEN -t); [ -n "$OLD" ] && kill "$OLD"; sleep 2
cd /Users/rodhoward/NarrateTTS && set -a && source .env && set +a
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8090 > /tmp/narrate_8090.log 2>&1 &
sleep 3; curl -s -o /dev/null -w "imagery.js %{http_code}\n" http://localhost:8090/static/js/imagery.js
```
Expected: `200`.

- [ ] **Step 2: Full test suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass.

- [ ] **Step 3: Confirm new captures store image_url**

```bash
.venv/bin/python -c "import sqlite3; c=sqlite3.connect('data/library.db'); print([r[0] for r in c.execute('PRAGMA table_info(items)').fetchall()])" | grep -q image_url && echo "image_url column present"
```
Expected: `image_url column present`.
