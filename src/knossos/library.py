# knossos/library.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from knossos.epub.book import load_book, get_metadata


@dataclass
class LibraryEntry:
    path: Path
    title: str
    author: str | None


def scan_directory(directory: Path) -> list[LibraryEntry]:
    """
    Scan a directory (recursively) for .epub files and extract basic metadata
    from each. Files that fail to parse (corrupt/malformed EPUBs) are skipped
    rather than aborting the whole scan.
    """
    entries: list[LibraryEntry] = []

    for path in sorted(directory.rglob("*.epub")):
        try:
            book = load_book(path)
            meta = get_metadata(book)
        except Exception:
            # Prototype-level tolerance: one bad file shouldn't kill the
            # whole library scan. Worth logging properly once we have
            # real logging set up.
            continue

        entries.append(LibraryEntry(path=path, title=meta.title, author=meta.author))

    return entries
