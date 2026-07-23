# knossos/db.py

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    path        TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    author      TEXT,
    added_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS progress (
    book_id         INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_index   INTEGER NOT NULL DEFAULT 0,
    scroll_y        REAL NOT NULL DEFAULT 0,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (book_id)
);

CREATE TABLE IF NOT EXISTS bookmarks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_index   INTEGER NOT NULL,
    scroll_y        REAL NOT NULL,
    label           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


"""Currently the only ID for a book is its provided PATH, which is BAD and
will break so long as books are moved. We'll need to change this before implementing
OPDS functionality, luckily epubs have their own identifier and I'll switch to that
when I am not lazy."""

def connect(db_path: Path) -> sqlite3.Connection:
    """Open a connection with sane defaults and ensure schema exists."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


@contextmanager
def session(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Context-managed connection: commits on success, rolls back on error."""
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_or_create_book(conn: sqlite3.Connection, path: str, title: str, author: str | None) -> int:
    """Look up a book by its file path, inserting it if it's not yet known.
    Returns the book's id."""
    row = conn.execute("SELECT id FROM books WHERE path = ?", (path,)).fetchone()
    if row is not None:
        return row["id"]

    cursor = conn.execute(
        "INSERT INTO books (path, title, author) VALUES (?, ?, ?)",
        (path, title, author),
    )
    conn.commit()
    return cursor.lastrowid


def save_progress(conn: sqlite3.Connection, book_id: int, chapter_index: int, scroll_y: float) -> None:
    """Save reading progress for a book."""
    conn.execute(
        """
        INSERT INTO progress (book_id, chapter_index, scroll_y, updated_at)
        VALUES (?, ?, ?, datetime('now'))
        ON CONFLICT(book_id) DO UPDATE SET
            chapter_index = excluded.chapter_index,
            scroll_y = excluded.scroll_y,
            updated_at = excluded.updated_at
        """,
        (book_id, chapter_index, scroll_y),
    )
    conn.commit()


def load_progress(conn: sqlite3.Connection, book_id: int) -> tuple[int, float] | None:
    """Return (chapter_index, scroll_y) for a book, or None if no progress saved yet."""
    row = conn.execute(
        "SELECT chapter_index, scroll_y FROM progress WHERE book_id = ?",
        (book_id,),
    ).fetchone()
    if row is None:
        return None
    return row["chapter_index"], row["scroll_y"]

def add_bookmark(
    conn: sqlite3.Connection,
    book_id: int,
    chapter_index: int,
    scroll_y: float,
    label: str | None = None,
) -> int:
    """Create a new bookmark. Returns the bookmark's id."""
    cursor = conn.execute(
        """
        INSERT INTO bookmarks (book_id, chapter_index, scroll_y, label)
        VALUES (?, ?, ?, ?)
        """,
        (book_id, chapter_index, scroll_y, label),
    )
    conn.commit()
    return cursor.lastrowid


def list_bookmarks(conn: sqlite3.Connection, book_id: int) -> list[sqlite3.Row]:
    """Return all bookmarks for a book, most recently created first."""
    return conn.execute(
        """
        SELECT id, chapter_index, scroll_y, label, created_at
        FROM bookmarks
        WHERE book_id = ?
        ORDER BY created_at DESC
        """,
        (book_id,),
    ).fetchall()


def delete_bookmark(conn: sqlite3.Connection, bookmark_id: int) -> None:
    """Remove a bookmark by its id."""
    conn.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
    conn.commit()



def get_book_id_by_path(conn: sqlite3.Connection, path: str) -> int | None:
    """Look up a book's id by path, without creating one if it doesn't exist.
    Used for read-only lookups (e.g. showing progress in a preview pane)
    where we don't want browsing to silently register books in the db."""
    row = conn.execute("SELECT id FROM books WHERE path = ?", (path,)).fetchone()
    return row["id"] if row else None
