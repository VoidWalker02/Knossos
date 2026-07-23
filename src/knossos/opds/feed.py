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


@dataclass
class OPDSEntry:
    title: str
    links: list[OPDSLink] = field(default_factory=list)

    @property
    def navigation_link(self) -> OPDSLink | None:
        """The link to follow if this entry leads to another feed (a folder,
        e.g. an author or category), rather than being a book itself."""
        for link in self.links:
            if link.type and NAVIGATION_TYPE_MARKER in link.type:
                return link
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


def parse_feed(xml_text: str, base_url: str) -> OPDSFeed:
    """
    Parse a raw OPDS (Atom) feed into structured entries, resolving all
    relative hrefs against base_url so callers get directly-fetchable URLs.
    """
    root = etree.fromstring(xml_text.encode("utf-8"))

    def resolve(href: str) -> str:
        return urljoin(base_url, href)

    feed_title_el = root.find("atom:title", NSMAP)
    feed_title = feed_title_el.text if feed_title_el is not None else ""

    next_link = None
    for link_el in root.findall("atom:link", NSMAP):
        if link_el.get("rel") == "next":
            next_link = resolve(link_el.get("href"))

    entries: list[OPDSEntry] = []
    for entry_el in root.findall("atom:entry", NSMAP):
        title_el = entry_el.find("atom:title", NSMAP)
        title = title_el.text if title_el is not None else "Untitled"

        links = []
        for link_el in entry_el.findall("atom:link", NSMAP):
            href = link_el.get("href")
            if not href:
                continue
            links.append(
                OPDSLink(
                    rel=link_el.get("rel"),
                    href=resolve(href),
                    type=link_el.get("type"),
                )
            )

        entries.append(OPDSEntry(title=title, links=links))

    return OPDSFeed(title=feed_title, entries=entries, next_link=next_link)
