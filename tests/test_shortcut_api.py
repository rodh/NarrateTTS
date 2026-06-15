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


def test_download_uses_public_base_url_when_set(client, monkeypatch):
    """When PUBLIC_BASE_URL is configured, the shortcut bakes that exact endpoint,
    regardless of the Host the browser used to download it."""
    import plistlib
    import app.main as main
    monkeypatch.setattr(main, "sign_shortcut", lambda data: (data, False))
    monkeypatch.setattr(main, "PUBLIC_BASE_URL", "https://narrate.howlab.us")

    resp = client.get("/api/shortcut")
    assert resp.status_code == 200
    plist = plistlib.loads(resp.content)
    url = plist["WFWorkflowActions"][0]["WFWorkflowActionParameters"]["WFURLActionURL"]
    assert url == "https://narrate.howlab.us/api/shortcut"


def test_download_strips_trailing_slash_from_public_base_url(client, monkeypatch):
    import plistlib
    import app.main as main
    monkeypatch.setattr(main, "sign_shortcut", lambda data: (data, False))
    monkeypatch.setattr(main, "PUBLIC_BASE_URL", "https://narrate.howlab.us/")

    resp = client.get("/api/shortcut")
    plist = plistlib.loads(resp.content)
    url = plist["WFWorkflowActions"][0]["WFWorkflowActionParameters"]["WFURLActionURL"]
    assert url == "https://narrate.howlab.us/api/shortcut"


def test_extraction_failure_saves_visible_error_item(client, monkeypatch):
    """A URL whose content can't be extracted (paywall/403) should still create a
    visible item with status 'error' instead of silently dropping (HTTP 400)."""
    import app.main as main

    async def _boom(url):
        raise RuntimeError("Client error '403 Forbidden'")

    monkeypatch.setattr(main, "extract_from_url", _boom)

    resp = client.post("/api/convert", json={"url": "https://paywalled.example/secret"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "error"

    items = client.get("/api/items").json()
    match = next(i for i in items if i["id"] == body["id"])
    assert match["status"] == "error"
    assert match["source_url"] == "https://paywalled.example/secret"
    assert "403" in (match["error"] or "")
    assert match["title"]  # has a readable title derived from the URL


def test_retry_reextracts_and_reprocesses(client, monkeypatch):
    """Retrying an extraction-failure item re-extracts, clears the error, fills in
    the content, and moves it back to processing."""
    import app.main as main

    async def _boom(url):
        raise RuntimeError("Client error '403 Forbidden'")

    monkeypatch.setattr(main, "extract_from_url", _boom)
    err = client.post("/api/convert", json={"url": "https://x.example/a"}).json()
    assert err["status"] == "error"

    async def _ok(url):
        return {"title": "Recovered Article", "text": "Now it works fine."}

    monkeypatch.setattr(main, "extract_from_url", _ok)
    r = client.post(f"/api/items/{err['id']}/retry")
    assert r.status_code == 200
    assert r.json()["status"] == "processing"

    item = client.get(f"/api/items/{err['id']}").json()
    assert item["status"] == "processing"
    assert item["title"] == "Recovered Article"
    assert (item["error"] or "") == ""
    assert item["word_count"] == 4


def test_retry_failure_stays_error(client, monkeypatch):
    import app.main as main

    async def _boom(url):
        raise RuntimeError("Client error '403 Forbidden'")

    monkeypatch.setattr(main, "extract_from_url", _boom)
    err = client.post("/api/convert", json={"url": "https://x.example/a"}).json()
    r = client.post(f"/api/items/{err['id']}/retry")
    assert r.status_code == 200
    assert r.json()["status"] == "error"
    item = client.get(f"/api/items/{err['id']}").json()
    assert item["status"] == "error"
    assert "403" in (item["error"] or "")


def test_retry_missing_item_404(client):
    assert client.post("/api/items/999999/retry").status_code == 404
