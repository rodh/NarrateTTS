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
    """)
    conn.commit()
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
    allowed = {"status", "audio_path", "error", "duration_seconds", "updated_at"}
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


def delete_item(item_id: int):
    conn = get_connection()
    item = conn.execute("SELECT audio_path FROM items WHERE id = ?", (item_id,)).fetchone()
    if item and item["audio_path"]:
        Path(item["audio_path"]).unlink(missing_ok=True)
    conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
