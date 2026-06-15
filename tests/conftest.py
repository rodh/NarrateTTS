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
