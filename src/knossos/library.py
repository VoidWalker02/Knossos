# knossos/library.py

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from textual.containers import Vertical

from knossos.epub.book import load_book, get_metadata


@dataclass
class LibraryEntry:
    path: Path
    title: str
    author: str | None
    source_dir: Path
    identifier: str | None = None
    duplicate_paths: list[Path] = field(default_factory=list)

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

        entries.append(
            LibraryEntry(
                path=path, title=meta.title, author=meta.author,
                source_dir=directory, identifier=meta.identifier,
            )
        )
    return entries

def scan_libraries(directories: list[Path]) -> list[LibraryEntry]:
    seen_paths: set[Path] = set()
    entries: list[LibraryEntry] = []

    for directory in directories:
        if not directory.exists():
            continue
        for entry in scan_directory(directory):
            resolved = entry.path.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            entries.append(entry)

    _annotate_duplicates(entries)
    return sorted(entries, key=lambda e: e.title)


def _annotate_duplicates(entries: list[LibraryEntry]) -> None:
    """
    Group entries by identifier and record when the same book (by EPUB
    identifier) appears at more than one path — e.g. copies in two
    different configured library folders. Entries with no identifier are
    skipped, since we have no reliable way to know they're duplicates.
    """
    by_identifier: dict[str, list[LibraryEntry]] = {}
    for entry in entries:
        if entry.identifier:
            by_identifier.setdefault(entry.identifier, []).append(entry)

    for group in by_identifier.values():
        if len(group) > 1:
            for entry in group:
                entry.duplicate_paths = [e.path for e in group if e.path != entry.path]    

