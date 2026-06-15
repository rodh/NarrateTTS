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
