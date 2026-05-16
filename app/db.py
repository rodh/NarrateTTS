import sqlite3
import json
from pathlib import Path
from datetime import datetime

from app.config import DATA_DIR


DB_PATH = DATA_DIR / "library.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT,
            title TEXT NOT NULL,
            text TEXT,
            word_count INTEGER DEFAULT 0,
            audio_path TEXT,
            status TEXT DEFAULT 'queued',
            error TEXT,
            duration_seconds REAL,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
        CREATE INDEX IF NOT EXISTS idx_items_created ON items(created_at DESC);

        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS playlist_items (
            playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
            item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
            position INTEGER NOT NULL DEFAULT 0,
            added_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (playlist_id, item_id)
        );

        CREATE INDEX IF NOT EXISTS idx_playlist_items_pos ON playlist_items(playlist_id, position);
    """)
    conn.commit()
    try:
        conn.execute("ALTER TABLE items ADD COLUMN play_position REAL DEFAULT 0")
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE items ADD COLUMN summary TEXT DEFAULT ''")
        conn.commit()
    except Exception:
        pass
    conn.close()


def add_item(source_url: str | None, title: str, text: str, status: str = "queued") -> int:
    word_count = len(text.split())
    conn = get_connection()
    cursor = conn.execute(
        """INSERT INTO items (source_url, title, text, word_count, status)
           VALUES (?, ?, ?, ?, ?)""",
        (source_url, title, text, word_count, status),
    )
    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return item_id


def get_item(item_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_items(limit: int = 50, offset: int = 0):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM items ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_items():
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM items").fetchone()
    conn.close()
    return row["cnt"]


def update_item(item_id: int, **kwargs):
    allowed = {"status", "audio_path", "error", "duration_seconds", "updated_at", "summary"}
    sets = []
    values = []
    for k, v in kwargs.items():
        if k in allowed:
            sets.append(f"{k} = ?")
            values.append(v)
    values.append(datetime.now().isoformat())
    sets.append("updated_at = ?")
    values.append(item_id)
    conn = get_connection()
    conn.execute(f"UPDATE items SET {', '.join(sets)} WHERE id = ?", values)
    conn.commit()
    conn.close()


def update_play_position(item_id: int, position: float):
    """Update play_position only if new value exceeds current (high-water mark)."""
    conn = get_connection()
    conn.execute(
        "UPDATE items SET play_position = ?, updated_at = datetime('now') WHERE id = ? AND (play_position IS NULL OR play_position < ?)",
        (position, item_id, position),
    )
    conn.commit()
    conn.close()


def delete_item(item_id: int):
    conn = get_connection()
    item = conn.execute("SELECT audio_path FROM items WHERE id = ?", (item_id,)).fetchone()
    if item and item["audio_path"]:
        Path(item["audio_path"]).unlink(missing_ok=True)
    conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


# --- Playlist Functions ---


def create_playlist(name: str, description: str = "") -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO playlists (name, description) VALUES (?, ?)",
        (name, description),
    )
    playlist_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return playlist_id


def list_playlists() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.*, COUNT(pi.item_id) as item_count
        FROM playlists p
        LEFT JOIN playlist_items pi ON p.id = pi.playlist_id
        GROUP BY p.id
        ORDER BY p.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_playlist(playlist_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM playlists WHERE id = ?", (playlist_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_playlist(playlist_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
    conn.commit()
    conn.close()


def add_item_to_playlist(playlist_id: int, item_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT COALESCE(MAX(position), -1) + 1 as next_pos FROM playlist_items WHERE playlist_id = ?",
        (playlist_id,),
    ).fetchone()
    next_pos = row["next_pos"]
    conn.execute(
        "INSERT OR IGNORE INTO playlist_items (playlist_id, item_id, position) VALUES (?, ?, ?)",
        (playlist_id, item_id, next_pos),
    )
    conn.commit()
    conn.close()


def remove_item_from_playlist(playlist_id: int, item_id: int):
    conn = get_connection()
    conn.execute(
        "DELETE FROM playlist_items WHERE playlist_id = ? AND item_id = ?",
        (playlist_id, item_id),
    )
    conn.commit()
    conn.close()


def list_playlist_items(playlist_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT i.* FROM items i
        JOIN playlist_items pi ON i.id = pi.item_id
        WHERE pi.playlist_id = ? AND i.status = 'completed'
        ORDER BY pi.position
    """, (playlist_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_item_playlists(item_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.id, p.name FROM playlists p
        JOIN playlist_items pi ON p.id = pi.playlist_id
        WHERE pi.item_id = ?
    """, (item_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_items_playlist_map() -> dict[int, list[dict]]:
    """Return {item_id: [{id, name}, ...]} for all playlist assignments."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT pi.item_id, p.id, p.name FROM playlist_items pi
        JOIN playlists p ON p.id = pi.playlist_id
        ORDER BY pi.item_id
    """).fetchall()
    conn.close()
    result: dict[int, list[dict]] = {}
    for r in rows:
        result.setdefault(r["item_id"], []).append({"id": r["id"], "name": r["name"]})
    return result


def get_playlist_by_name(name: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM playlists WHERE name = ?", (name,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_completed_items(limit: int = 500) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM items WHERE status = 'completed' ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
