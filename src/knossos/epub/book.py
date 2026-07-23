# knossos/epub/book.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import ebooklib
import re
from ebooklib import epub
from lxml import etree, html as lxml_html


@dataclass
class BookMetadata:
    title: str
    author: str | None
    language: str | None
    identifier: str | None


def load_book(path: Path) -> epub.EpubBook:
    """Load an EPUB file from disk."""
    return epub.read_epub(str(path))


def get_metadata(book: epub.EpubBook) -> BookMetadata:
    """Extract core metadata from a loaded EPUB."""

    def first(namespace: str, name: str) -> str | None:
        values = book.get_metadata(namespace, name)
        return values[0][0] if values else None

    return BookMetadata(
        title=first("DC", "title") or "Unknown Title",
        author=first("DC", "creator"),
        language=first("DC", "language"),
        identifier=first("DC", "identifier"),
    )
# knossos/epub/book.py (additions)


@dataclass
class Chapter:
    index: int
    id: str
    content: str  # raw XHTML


def get_reading_order(book: epub.EpubBook) -> list[Chapter]:
    """
    Return the book's chapters in spine order (the order the author
    intended them to be read), with raw XHTML content for each.
    """
    chapters: list[Chapter] = []

    for index, (item_id, _linear) in enumerate(book.spine):
        item = book.get_item_with_id(item_id)
        if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        chapters.append(
            Chapter(
                index=index,
                id=item_id,
                content=item.get_content().decode("utf-8", errors="replace"),
            )
        )

    return chapters

import html2text


def chapter_to_text(chapter: Chapter) -> str:
    """Convert a chapter's raw XHTML into readable plain text."""
    converter = html2text.HTML2Text()
    converter.body_width = 0      # don't hard-wrap lines; let the terminal/widget handle it
    converter.ignore_links = True # prototype: don't clutter output with link refs
    converter.ignore_images = True
    return converter.handle(chapter.content)

# Some EPUBs (notably ones exported from Adobe InDesign) mark emphasis via
# CSS classes on <span> elements instead of semantic <em>/<strong> tags.
# html2text only recognizes the semantic tags, so we normalize these known
# class names into real semantic elements before conversion.

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|_(.+?)_")

_EMPHASIS_CLASS_MAP = {
    "italic": "em",
    "bold": "strong",
}



def _normalize_emphasis_spans(xhtml_content: str) -> str:
    """Rewrite <span class="Italic/Bold"> (case-insensitive) into <em>/<strong>."""
    try:
        tree = lxml_html.fromstring(xhtml_content.encode("utf-8"))
    except (etree.ParserError, ValueError):
        # Malformed/unusual markup — fall back to original content rather
        # than crashing the whole chapter conversion over a formatting nicety.
        return xhtml_content

    for span in tree.xpath("//span[@class]"):
        class_name = (span.get("class") or "").strip().lower()
        tag_name = _EMPHASIS_CLASS_MAP.get(class_name)
        if tag_name is not None:
            span.tag = tag_name
            del span.attrib["class"]

    return etree.tostring(tree, encoding="unicode", method="html")


def chapter_to_markup(chapter: Chapter) -> str:
    normalized_content = _normalize_emphasis_spans(chapter.content)

    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.ignore_links = True
    converter.ignore_images = True
    markdown_text = converter.handle(normalized_content)

    # Drop empty emphasis markers left behind when the only content inside
    # was an image (which we strip via ignore_images).
    markdown_text = re.sub(r"\*\*\s*\*\*", "", markdown_text)
    markdown_text = re.sub(r"\*\s*\*", "", markdown_text)

    escaped = markdown_text.replace("[", "\\[")
    escaped = _BOLD_RE.sub(r"[bold]\1[/bold]", escaped)
    escaped = _ITALIC_RE.sub(
        lambda m: f"[italic]{m.group(1) or m.group(2)}[/italic]", escaped
    )

    return escaped


@dataclass
class TocEntry:
    title: str
    chapter_position: int  # index into the list returned by get_reading_order()
    level: int = 0         # nesting depth, for indentation in the UI


def _flatten_toc(items, level=0):
    """Walk ebooklib's nested TOC structure into a flat list of (title, href, level)."""
    flat = []
    for item in items:
        if isinstance(item, epub.Link):
            flat.append((item.title, item.href, level))
        elif isinstance(item, tuple) and len(item) == 2:
            section, children = item
            title = getattr(section, "title", None) or str(section)
            href = getattr(section, "href", None)
            flat.append((title, href, level))
            flat.extend(_flatten_toc(children, level + 1))
    return flat


def get_toc(book: epub.EpubBook, chapters: list[Chapter]) -> list[TocEntry]:
    """
    Build a flat, navigable table of contents.

    `chapters` must be the same list produced by get_reading_order() for this
    book so this map TOC hrefs to *positions in that list*, since that's what
    the reader UI uses to track "current chapter".
    """
    href_to_position: dict[str, int] = {}
    for position, chapter in enumerate(chapters):
        item = book.get_item_with_id(chapter.id)
        if item is not None:
            href_to_position[item.get_name()] = position

    entries = []
    for title, href, level in _flatten_toc(book.toc):
        if not href:
            continue
        file_part = href.split("#")[0]  # strip any #anchor fragment
        position = href_to_position.get(file_part)
        if position is None:
            continue
        entries.append(TocEntry(title=title.strip(), chapter_position=position, level=level))

    return entries
