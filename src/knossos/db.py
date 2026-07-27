# knossos/db.py

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from datetime import datetime, timezone


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



CREATE TABLE IF NOT EXISTS annotations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id         INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_index   INTEGER NOT NULL,
    excerpt         TEXT NOT NULL,
    note            TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
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
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)

    existing_progress_columns = {row["name"] for row in conn.execute("PRAGMA table_info(progress)")}
    if "finished_at" not in existing_progress_columns:
        conn.execute("ALTER TABLE progress ADD COLUMN finished_at TEXT")

    existing_annotation_columns = {row["name"] for row in conn.execute("PRAGMA table_info(annotations)")}
    if "paragraph_index" not in existing_annotation_columns:
        conn.execute("ALTER TABLE annotations ADD COLUMN paragraph_index INTEGER")

    existing_book_columns = {row["name"] for row in conn.execute("PRAGMA table_info(books)")}
    if "identifier" not in existing_book_columns:
        conn.execute("ALTER TABLE books ADD COLUMN identifier TEXT")


    existing_progress_columns = {row["name"] for row in conn.execute("PRAGMA table_info(progress)")}
    if "updated_at" not in existing_progress_columns:
        conn.execute("ALTER TABLE progress ADD COLUMN updated_at TEXT")    

    # Only safe to create this index once the identifier column definitely
    # exists — hence doing it here, after the migration above, rather than
    # as part of the static SCHEMA script.
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_books_identifier
        ON books(identifier) WHERE identifier IS NOT NULL
        """
    )

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


# knossos/db.py (replace get_or_create_book)

def get_or_create_book(
    conn: sqlite3.Connection,
    path: str,
    title: str,
    author: str | None,
    identifier: str | None = None,
) -> int:
    """
    Resolve a book to its db row, preferring its stable EPUB identifier
    (dc:identifier) over file path. This means a book keeps its bookmarks/
    progress/annotations even if it's moved, renamed, or opened from a
    different path on another machine — as long as its identifier matches.

    Falls back to path-based identity for EPUBs that don't have one.
    """
    if identifier:
        row = conn.execute("SELECT id FROM books WHERE identifier = ?", (identifier,)).fetchone()
        if row is not None:
            book_id = row["id"]
            # Path may have changed since we last saw this book — keep it current.
            conn.execute(
                "UPDATE books SET path = ?, title = ?, author = ? WHERE id = ?",
                (path, title, author, book_id),
            )
            conn.commit()
            return book_id

    row = conn.execute("SELECT id, identifier FROM books WHERE path = ?", (path,)).fetchone()
    if row is not None:
        book_id = row["id"]
        if identifier and not row["identifier"]:
            # This path was registered before we tracked identifiers —
            # upgrade it now that we have one.
            conn.execute("UPDATE books SET identifier = ? WHERE id = ?", (identifier, book_id))
            conn.commit()
        return book_id

    cursor = conn.execute(
        "INSERT INTO books (path, identifier, title, author) VALUES (?, ?, ?, ?)",
        (path, identifier, title, author),
    )
    conn.commit()
    return cursor.lastrowid

def save_progress(conn: sqlite3.Connection, book_id: int, chapter_index: int, scroll_y: float) -> str:
    """Saves progress locally and returns the timestamp it was stored
    with, so callers (e.g. sync) can push that exact same value."""
    updated_at = _now_iso()
    conn.execute(
        """
        INSERT INTO progress (book_id, chapter_index, scroll_y, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(book_id) DO UPDATE SET
            chapter_index = excluded.chapter_index,
            scroll_y = excluded.scroll_y,
            updated_at = excluded.updated_at
        """,
        (book_id, chapter_index, scroll_y, updated_at),
    )
    conn.commit()
    return updated_at

def load_progress(conn: sqlite3.Connection, book_id: int) -> tuple[int, float, str | None] | None:
    row = conn.execute(
        "SELECT chapter_index, scroll_y, updated_at FROM progress WHERE book_id = ?",
        (book_id,),
    ).fetchone()
    if row is None:
        return None
    return row["chapter_index"], row["scroll_y"], row["updated_at"]

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



def add_annotation(
    conn: sqlite3.Connection,
    book_id: int,
    chapter_index: int,
    excerpt: str,
    note: str | None = None,
    paragraph_index: int | None = None,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO annotations (book_id, chapter_index, excerpt, note, paragraph_index)
        VALUES (?, ?, ?, ?, ?)
        """,
        (book_id, chapter_index, excerpt, note, paragraph_index),
    )
    conn.commit()
    return cursor.lastrowid


def list_annotations(conn: sqlite3.Connection, book_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT id, chapter_index, excerpt, note, paragraph_index, created_at
        FROM annotations
        WHERE book_id = ?
        ORDER BY created_at DESC
        """,
        (book_id,),
    ).fetchall()


def delete_annotation(conn: sqlite3.Connection, annotation_id: int) -> None:
    conn.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
    conn.commit()




def get_most_recent_book(conn: sqlite3.Connection) -> sqlite3.Row | None:
    """
    Return the book with the most recently updated reading progress
    (path, title, author, chapter_index, scroll_y), or None if no book
    has any recorded progress yet.
    """
    return conn.execute(
        """
        SELECT books.path, books.title, books.author,
               progress.chapter_index, progress.scroll_y, progress.updated_at
        FROM progress
        JOIN books ON books.id = progress.book_id
        ORDER BY progress.updated_at DESC
        LIMIT 1
        """
    ).fetchone()    




def get_book_id_by_identity(conn: sqlite3.Connection, identifier: str | None, path: str) -> int | None:
    """Read-only lookup, preferring identifier over path — used where we
    don't want browsing to register a new book (e.g. a preview panel)."""
    if identifier:
        row = conn.execute("SELECT id FROM books WHERE identifier = ?", (identifier,)).fetchone()
        if row is not None:
            return row["id"]

    row = conn.execute("SELECT id FROM books WHERE path = ?", (path,)).fetchone()
    return row["id"] if row else None


def update_annotation_note(conn: sqlite3.Connection, annotation_id: int, note: str | None) -> None:
    conn.execute("UPDATE annotations SET note = ? WHERE id = ?", (note, annotation_id))
    conn.commit()



def list_all_bookmarks(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT bookmarks.id, bookmarks.chapter_index, bookmarks.scroll_y,
               bookmarks.label, bookmarks.created_at,
               books.id AS book_id, books.path, books.title
        FROM bookmarks
        JOIN books ON books.id = bookmarks.book_id
        ORDER BY bookmarks.created_at DESC
        """
    ).fetchall()


def list_all_annotations(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT annotations.id, annotations.chapter_index, annotations.excerpt,
               annotations.note, annotations.paragraph_index, annotations.created_at,
               books.id AS book_id, books.path, books.title
        FROM annotations
        JOIN books ON books.id = annotations.book_id
        ORDER BY annotations.created_at DESC
        """
    ).fetchall()   



def _now_iso() -> str:
    """Current UTC time as an ISO 8601 string — must match the format
    knossos/sync.py uses, since local and remote timestamps get compared
    directly as strings."""
    return datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None).isoformat()
