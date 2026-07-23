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
            # whole library scan. Please do remember to change this later!!!!
            continue

        entries.append(LibraryEntry(path=path, title=meta.title, author=meta.author))

    return entries

def scan_libraries(directories: list[Path]) -> list[LibraryEntry]:

    """Scan multiple directories and merge results, deduplicating by resolved path

    in case the same book is reachable from more than one configured folder."""

    seen_paths: set[Path] = set()

    entries: list[LibraryEntry] = []

    for directory in directories:

        if not directory.exists():

            continue  # a configured folder might be an unmounted drive, etc.

        for entry in scan_directory(directory):

            resolved = entry.path.resolve()

            if resolved in seen_paths:

                continue

            seen_paths.add(resolved)

            entries.append(entry)

    return sorted(entries, key=lambda e: e.title)


