# knossos/opds/feed.py

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urljoin

from lxml import etree

ATOM_NS = "http://www.w3.org/2005/Atom"
NSMAP = {"atom": ATOM_NS}

ACQUISITION_REL_PREFIX = "http://opds-spec.org/acquisition"
NAVIGATION_TYPE_MARKER = "profile=opds-catalog"


@dataclass
class OPDSLink:
    rel: str | None
    href: str
    type: str | None
    length: int | None = None


@dataclass
class OPDSEntry:
    title: str
    links: list[OPDSLink] = field(default_factory=list)
    summary: str | None = None
    author: str | None = None
    published: str | None = None


    @property
    def navigation_link(self) -> OPDSLink | None:
        """The link to follow if this entry leads to another feed (a folder,
        e.g. an author or category), rather than being a book itself."""
        for link in self.links:
            if link.type and NAVIGATION_TYPE_MARKER in link.type:
                return link
        return None

    @property
    def file_size_bytes(self) -> int | None:
        """Size of the first acquisition link's file, if the feed provided one."""
        for link in self.acquisition_links:
            if link.length is not None:
                return link.length
        return None    

    @property
    def acquisition_links(self) -> list[OPDSLink]:
        """Links that point to an actual downloadable book (possibly multiple
        formats — epub, mobi, etc)."""
        return [
            link for link in self.links
            if link.rel and link.rel.startswith(ACQUISITION_REL_PREFIX)
        ]

    @property
    def is_navigation(self) -> bool:
        return self.navigation_link is not None

    @property
    def is_acquisition(self) -> bool:
        return len(self.acquisition_links) > 0


@dataclass
class OPDSFeed:
    title: str
    entries: list[OPDSEntry] = field(default_factory=list)
    next_link: str | None = None  # pagination
    search_template: str | None = None


def _resolve_search_template(raw_href: str, base_url: str) -> str:
    """
    Resolve a templated search URL (containing a literal '{searchTerms}')
    against the feed's base URL, without letting urljoin mangle the curly
    braces (which aren't a normal URL path segment).
    """
    if "{" not in raw_href:
        return urljoin(base_url, raw_href)

    path_part, template_part = raw_href.split("{", 1)
    resolved_path = urljoin(base_url, path_part)
    return resolved_path + "{" + template_part
    


def parse_feed(xml_text: str, base_url: str) -> OPDSFeed:
    root = etree.fromstring(xml_text.encode("utf-8"))

    def resolve(href: str) -> str:
        return urljoin(base_url, href)

    feed_title_el = root.find("atom:title", NSMAP)
    feed_title = feed_title_el.text if feed_title_el is not None else ""

    next_link = None
    search_template = None
    for link_el in root.findall("atom:link", NSMAP):
        rel = link_el.get("rel")
        href = link_el.get("href")
        if not href:
            continue
        if rel == "next":
            next_link = resolve(href)
        elif rel == "search":
            search_template = _resolve_search_template(href, base_url)

    entries: list[OPDSEntry] = []
    for entry_el in root.findall("atom:entry", NSMAP):
        title_el = entry_el.find("atom:title", NSMAP)
        title = title_el.text if title_el is not None else "Untitled"

        summary_el = entry_el.find("atom:summary", NSMAP)
        if summary_el is None:
            summary_el = entry_el.find("atom:content", NSMAP)
        summary = summary_el.text.strip() if summary_el is not None and summary_el.text else None

        author_el = entry_el.find("atom:author/atom:name", NSMAP)
        author = author_el.text.strip() if author_el is not None and author_el.text else None

        published_el = entry_el.find("atom:published", NSMAP)
        published = published_el.text.strip() if published_el is not None and published_el.text else None

        links = []
        for link_el in entry_el.findall("atom:link", NSMAP):
            href = link_el.get("href")
            if not href:
                continue
            length_attr = link_el.get("length")
            links.append(
                OPDSLink(
                    rel=link_el.get("rel"),
                    href=resolve(href),
                    type=link_el.get("type"),
                    length=int(length_attr) if length_attr and length_attr.isdigit() else None,
                )
            )

        entries.append(
            OPDSEntry(title=title, links=links, summary=summary, author=author, published=published)
        )

    return OPDSFeed(title=feed_title, entries=entries, next_link=next_link, search_template=search_template)
