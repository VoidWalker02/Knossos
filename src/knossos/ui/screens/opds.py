# knossos/ui/screens/opds.py

from __future__ import annotations

import re
from pathlib import Path

from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label

from knossos.opds.client import fetch_feed, download_book
from knossos.opds.feed import parse_feed, OPDSFeed, OPDSEntry
from knossos.config import get_paths, load_config

OPDS_ROOT_URL = "http://100.122.21.102:8080/opds"
DOWNLOAD_DIR = Path(__file__).resolve().parents[3] / "opds_downloads"


def _safe_filename(title: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", title).strip()
    cleaned = re.sub(r"[\s]+", "_", cleaned)
    return cleaned or "book"


class OPDSScreen(Screen):
    """Browse a remote OPDS (Calibre) catalog: drill into sub-feeds,
    download and open books."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, root_url: str | None = None) -> None:
        super().__init__()
        if root_url is None:
            config = load_config(get_paths())
            root_url = config.opds_root_url or OPDS_ROOT_URL  # fall back to hardcoded default if unset
        self.root_url = root_url       

        self.feed_stack: list[str] = []  # URLs to return to on "back"
        self.current_feed: OPDSFeed | None = None
        self._current_url: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield ListView(id="opds-list")
        yield Footer()

    def on_mount(self) -> None:
        self.load_feed(self.root_url)

    def load_feed(self, url: str) -> None:
        """Fetch and parse a feed, then populate the list view with its entries."""
        xml = fetch_feed(url)
        self.current_feed = parse_feed(xml, url)
        self._current_url = url

        self.title = "Knossos — OPDS"
        self.sub_title = self.current_feed.title

        list_view = self.query_one("#opds-list", ListView)
        list_view.clear()

        for entry in self.current_feed.entries:
            prefix = "📁 " if entry.is_navigation else "📖 "
            item = ListItem(Label(f"{prefix}{entry.title}"))
            item.opds_entry = entry
            list_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        entry: OPDSEntry = event.item.opds_entry

        if entry.is_navigation:
            self.feed_stack.append(self._current_url)
            self.load_feed(entry.navigation_link.href)
        elif entry.is_acquisition:
            self.download_and_open(entry)

    def download_and_open(self, entry: OPDSEntry) -> None:
        acquisition_link = entry.acquisition_links[0]
        filename = _safe_filename(entry.title) + ".epub"
        destination = DOWNLOAD_DIR / filename

        self.notify(f"Downloading {entry.title}...")
        saved_path = download_book(acquisition_link.href, destination)
        self.notify(f"Downloaded to {saved_path.name}")

        self.app.open_book(saved_path)

    def action_go_back(self) -> None:
        if self.feed_stack:
            previous_url = self.feed_stack.pop()
            self.load_feed(previous_url)
        else:
            self.app.pop_screen()
