import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

DB_PATH = os.getenv("DB_PATH", "searchsage.db")

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    answer_id TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS answers (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    sources TEXT NOT NULL,
    mode TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    answer_id TEXT NOT NULL,
    vote TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    """Return a connection local to the current thread.

    FastAPI runs sync endpoint code in a thread pool executor, so each
    worker thread needs its own sqlite3 connection rather than sharing one
    across threads.
    """
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        _local.conn = conn
    return conn


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db() -> None:
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()


def create_session(session_id: str) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO sessions (id, created_at) VALUES (?, ?)",
            (session_id, _now()),
        )


def session_exists(session_id: str) -> bool:
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return row is not None


def add_message(session_id: str, role: str, content: str, answer_id: Optional[str] = None) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, answer_id, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, answer_id, _now()),
        )


def get_history(session_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]


def save_answer(answer_id: str, session_id: Optional[str], question: str, answer: str,
                 sources: list[str], mode: str) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO answers (id, session_id, question, answer, sources, mode, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (answer_id, session_id, question, answer, json.dumps(sources), mode, _now()),
        )


def get_answer(answer_id: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM answers WHERE id = ?", (answer_id,)).fetchone()
    if row is None:
        return None
    return {
        "answer_id": row["id"],
        "answer": row["answer"],
        "sources": json.loads(row["sources"]),
        "mode": row["mode"],
    }


def save_feedback(answer_id: str, vote: str) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO feedback (answer_id, vote, created_at) VALUES (?, ?, ?)",
            (answer_id, vote, _now()),
        )


def cache_get(key: str) -> Optional[str]:
    conn = get_connection()
    row = conn.execute(
        "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
    ).fetchone()
    if row is None:
        return None
    if row["expires_at"] < _now():
        with transaction() as conn2:
            conn2.execute("DELETE FROM cache WHERE key = ?", (key,))
        return None
    return row["value"]


def cache_set(key: str, value: str, expires_at: str) -> None:
    with transaction() as conn:
        conn.execute(
            "INSERT INTO cache (key, value, expires_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, expires_at = excluded.expires_at",
            (key, value, expires_at),
        )
