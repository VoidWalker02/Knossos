# knossos/library_search.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from knossos.epub.book import load_book, get_reading_order, get_toc
from knossos.epub.search import search_book
from knossos.library import LibraryEntry


@dataclass
class LibrarySearchResult:
    book_path: Path
    book_title: str
    chapter_index: int
    chapter_title: str
    snippet: str


def search_library(entries: list[LibraryEntry], query: str) -> list[LibrarySearchResult]:
    """
    Search every book in the library for a query string.

    This loads and converts every chapter of every book to plain text on
    each call — no caching layer, so this can be slow for a large library.
    Fine for a prototype; worth revisiting (e.g. an on-disk search index)
    if this becomes a real bottleneck.
    """
    if not query.strip():
        return []

    results: list[LibrarySearchResult] = []

    for entry in entries:
        try:
            book = load_book(entry.path)
            chapters = get_reading_order(book)
            toc = get_toc(book, chapters)
        except Exception:
            continue

        chapter_titles = {t.chapter_position: t.title for t in toc}
        book_results = search_book(chapters, query, chapter_titles=chapter_titles)

        for r in book_results:
            results.append(
                LibrarySearchResult(
                    book_path=entry.path,
                    book_title=entry.title,
                    chapter_index=r.chapter_index,
                    chapter_title=r.chapter_title,
                    snippet=r.snippet,
                )
            )

    return results
