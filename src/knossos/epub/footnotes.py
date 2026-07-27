# knossos/epub/footnotes.py

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lxml import etree
from lxml import html as lxml_html

from knossos.epub.book import Chapter

FOOTNOTE_CLASS_MARKERS = ("footnote-number", "superscript", "endnote_marker", "endnote-marker")



@dataclass
class FootnoteReference:
    number: str                        # visible marker text, e.g. "22"
    anchor_id: str                      # target anchor id, e.g. "_idTextAnchor046"
    target_chapter_index: int | None    # reading-order position of the chapter it points to


def _parse_xhtml(content: str):
    try:
        return lxml_html.fromstring(content.encode("utf-8"))
    except (etree.ParserError, ValueError):
        return None


def _normalize_relative_path(path_str: str) -> str:
    """Collapse '..' segments in a relative path string without touching the
    real filesystem. Duplicated from book.py's private helper of the same
    name, rather than importing across modules, to keep footnotes.py
    self-contained."""
    parts = []
    for segment in path_str.split("/"):
        if segment == "..":
            if parts:
                parts.pop()
        elif segment and segment != ".":
            parts.append(segment)
    return "/".join(parts)


def _build_item_name_to_chapter_index(book, chapters: list[Chapter]) -> dict[str, int]:
    """Map each chapter's manifest filename to its position in the reading-
    order list, so an href pointing at a file can be resolved to a chapter
    index the reader actually navigates by."""
    mapping = {}
    for position, chapter in enumerate(chapters):
        item = book.get_item_with_id(chapter.id)
        if item is not None:
            mapping[item.get_name()] = position
    return mapping


def extract_footnote_references(
    book, chapter: Chapter, chapters: list[Chapter]
) -> list[FootnoteReference]:
    tree = _parse_xhtml(chapter.content)
    if tree is None:
        return []

    item_name_to_index = _build_item_name_to_chapter_index(book, chapters)
    current_item = book.get_item_with_id(chapter.id)
    current_dir = Path(current_item.get_name()).parent if current_item is not None else Path("")

    references: list[FootnoteReference] = []

    for link in tree.xpath("//a[@href]"):
        href = link.get("href")
        if not href or "#" not in href:
            continue

        number_spans = [
            span for span in link.xpath(".//span")
            if any(marker in (span.get("class") or "").lower() for marker in FOOTNOTE_CLASS_MARKERS)
        ]
        if not number_spans:
            continue

        number_text = (number_spans[0].text or "").strip()
        if not number_text:
            continue

        file_part, _, anchor_id = href.partition("#")

        if file_part:
            resolved_name = _normalize_relative_path((current_dir / file_part).as_posix())
        elif current_item is not None:
            resolved_name = current_item.get_name()
        else:
            resolved_name = None

        target_index = item_name_to_index.get(resolved_name) if resolved_name else None

        references.append(
            FootnoteReference(number=number_text, anchor_id=anchor_id, target_chapter_index=target_index)
        )

    return references

def extract_footnote_targets(chapter: Chapter) -> dict[str, str]:
    """
    Find every footnote/endnote TARGET in a chapter, keyed by anchor id.
    Handles two known conventions:
      1. <p class="Footnotes"> containing <a id="anchor"/>N. text...
      2. <li class="endnote-numbered" value="N"> containing <a id="anchor"/>
         followed directly by the note's text (no inline "N." prefix, since
         the number lives in the `value` attribute instead).
    """
    tree = _parse_xhtml(chapter.content)
    if tree is None:
        return {}

    targets: dict[str, str] = {}

    # Convention 1: <p class="Footnotes">
    for p in tree.xpath("//p[contains(@class, 'Footnotes')]"):
        anchor_els = p.xpath(".//a[@id]")
        if not anchor_els:
            continue
        anchor_id = anchor_els[0].get("id")
        if not anchor_id:
            continue
        full_text = " ".join(p.itertext()).strip()
        cleaned = re.sub(r"^\d+\.\s*", "", full_text)
        targets[anchor_id] = cleaned

    # Convention 2: <li class="endnote-numbered">
    for li in tree.xpath("//li[contains(@class, 'endnote-numbered')]"):
        anchor_els = li.xpath(".//a[@id]")
        if not anchor_els:
            continue
        anchor_id = anchor_els[0].get("id")
        if not anchor_id:
            continue
        full_text = " ".join(li.itertext()).strip()
        if full_text:
            targets[anchor_id] = full_text

    return targets
