def test_voices_endpoint_works(client):
    resp = client.get("/api/voices")
    assert resp.status_code == 200
    assert "voices" in resp.json()
