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
