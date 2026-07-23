# knossos/epub/search.py

from __future__ import annotations

from dataclasses import dataclass

from knossos.epub.book import Chapter, chapter_to_text

SNIPPET_RADIUS = 60  # characters of context on each side of a match


@dataclass
class SearchResult:
    chapter_index: int  # position in the reading-order list (matches ReaderScreen.current_index)
    chapter_title: str
    snippet: str         # short excerpt with the match roughly centered


def search_book(chapters: list[Chapter], query: str, chapter_titles: dict[int, str] | None = None) -> list[SearchResult]:
    """
    Search all chapters for a query string (case-insensitive substring match).
    Returns one result per match, in chapter order.

    chapter_titles, if provided, maps chapter list-position -> a human title
    (e.g. from the TOC), so results can show something more useful than
    "Chapter N". Falls back to a generic label if not given or no entry exists.
    """
    if not query.strip():
        return []

    query_lower = query.lower()
    results: list[SearchResult] = []

    for position, chapter in enumerate(chapters):
        text = chapter_to_text(chapter)
        text_lower = text.lower()

        start = 0
        while True:
            index = text_lower.find(query_lower, start)
            if index == -1:
                break

            snippet_start = max(0, index - SNIPPET_RADIUS)
            snippet_end = min(len(text), index + len(query) + SNIPPET_RADIUS)
            snippet = text[snippet_start:snippet_end].replace("\n", " ").strip()
            if snippet_start > 0:
                snippet = "…" + snippet
            if snippet_end < len(text):
                snippet = snippet + "…"

            title = None
            if chapter_titles:
                title = chapter_titles.get(position)
            title = title or f"Chapter {position + 1}"

            results.append(SearchResult(chapter_index=position, chapter_title=title, snippet=snippet))

            start = index + len(query)  # avoid re-matching inside the same occurrence

    return results
