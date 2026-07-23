# knossos/covers.py

from __future__ import annotations

import hashlib
from pathlib import Path

from knossos.config import Paths
from knossos.epub.book import load_book, get_cover_image_bytes


def _cache_key(identifier: str) -> str:
    """Stable, filesystem-safe cache filename for a given book path or URL."""
    return hashlib.sha256(identifier.encode("utf-8")).hexdigest()


def get_local_cover_path(paths: Paths, book_path: Path) -> Path | None:
    """
    Return a cached cover image file for a local EPUB, extracting and
    caching it on first access. Returns None if the book has no cover
    or extraction fails.
    """
    cache_dir = paths.cache_dir / "covers"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_file = cache_dir / f"{_cache_key(str(book_path.resolve()))}.img"
    if cache_file.exists():
        return cache_file

    try:
        book = load_book(book_path)
        cover_bytes = get_cover_image_bytes(book)
    except Exception:
        return None

    if cover_bytes is None:
        return None

    cache_file.write_bytes(cover_bytes)
    return cache_file
