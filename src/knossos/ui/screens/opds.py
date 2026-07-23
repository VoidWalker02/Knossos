# knossos/ui/screens/opds.py

from __future__ import annotations

import re
from pathlib import Path

from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label, DataTable, Static, Input
from textual.containers import Vertical, Horizontal
from urllib.parse import quote



from knossos.opds.client import fetch_feed, download_book
from knossos.opds.feed import parse_feed, OPDSFeed, OPDSEntry
from knossos.config import get_paths, load_config

OPDS_ROOT_URL = "http://100.122.21.102:8080/opds"
DOWNLOAD_DIR = Path(__file__).resolve().parents[3] / "opds_downloads"


def _safe_filename(title: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", title).strip()
    cleaned = re.sub(r"[\s]+", "_", cleaned)
    return cleaned or "book"

def _format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _format_date(iso_string: str) -> str:
    """Show just the date portion of an ISO datetime string, since the time
    component isn't meaningful for a 'published' date."""
    return iso_string.split("T")[0]    


class OPDSScreen(Screen):
    """Browse a remote OPDS (Calibre) catalog: drill into sub-feeds,
    download and open books."""


    CSS = """
    #opds-body {
        height: 1fr;
    }
    #opds-table {
        width: 2fr;
    }
    #opds-details-panel {
        width: 1fr;
        border-left: solid $panel;
        padding: 1 2;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("escape", "go_back", "Back"),
        ("s", "switch_server", "Switch server"),
        ("/", "start_search", "Search"),
    ]

    def __init__(self, root_url: str | None = None) -> None:
        super().__init__()
        if root_url is None:
            config = load_config(get_paths())
            if config.opds_servers:
                root_url = config.opds_servers[0].url
            else:
                root_url = OPDS_ROOT_URL
        self.root_url = root_url
        self.feed_stack: list[str] = []
        self.current_feed: OPDSFeed | None = None
        self._current_url: str | None = None
        self.row_key_to_entry: dict[str, OPDSEntry] = {}
        self.searhing = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="opds-search-bar"):
            yield Input(placeholder="Search this server...", id="opds-search-input")
        with Horizontal(id="opds-body"):
            yield DataTable(id="opds-table", cursor_type="row")
            with Vertical(id="opds-details-panel"):
                yield Static("Highlight an entry to see details.", id="opds-details-content")
        yield Footer()




    def on_mount(self) -> None:
        self.query_one("#opds-search-bar", Vertical).display = False
        table = self.query_one("#opds-table", DataTable)
        table.add_columns("Name", "Type")
        table.zebra_stripes = True
        self.load_feed(self.root_url)
        table.focus()

    
    def load_feed(self, url: str) -> None:
        xml = fetch_feed(url)
        self.current_feed = parse_feed(xml, url)
        self._current_url = url

        self.title = "Knossos — OPDS"
        self.sub_title = self.current_feed.title

        table = self.query_one("#opds-table", DataTable)
        table.clear()
        self.row_key_to_entry = {}

        for index, entry in enumerate(self.current_feed.entries):
            kind = "Folder" if entry.is_navigation else "Book" if entry.is_acquisition else "?"
            row_key = str(index)  # OPDS entries don't have a stable unique id we can rely on; index within this feed is fine
            table.add_row(entry.title, kind, key=row_key)
            self.row_key_to_entry[row_key] = entry

        self.query_one("#opds-details-content", Static).update("Highlight an entry to see details.")


    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        entry = self.row_key_to_entry.get(str(event.row_key.value))
        if entry is not None:
            self._show_details(entry)  

     

    def _show_details(self, entry: OPDSEntry) -> None:
        lines = [f"[bold]{entry.title}[/bold]"]

        if entry.author:
            lines.append(f"by {entry.author}")

        lines.append("")

        if entry.is_navigation:
            lines.append("[dim]Folder — press Enter to browse[/dim]")
        elif entry.is_acquisition:
            formats = ", ".join(
                link.type.split("/")[-1] for link in entry.acquisition_links if link.type
            )
            lines.append(f"Format: {formats or 'unknown'}")

            size = entry.file_size_bytes
            if size is not None:
                lines.append(f"Size: {_format_file_size(size)}")

            if entry.published:
                lines.append(f"Acquired: {_format_date(entry.published)}")

        if entry.summary:
            lines.append("")
            lines.append(entry.summary)

        self.query_one("#opds-details-content", Static).update("\n".join(lines))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        entry = self.row_key_to_entry.get(str(event.row_key.value))
        if entry is None:
            return

        if entry.is_navigation:
            self.feed_stack.append(self._current_url)
            self.load_feed(entry.navigation_link.href)
        elif entry.is_acquisition:
            self.download_and_open(entry)    

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        entry: OPDSEntry = event.item.opds_entry

        if entry.is_navigation:
            self.feed_stack.append(self._current_url)
            self.load_feed(entry.navigation_link.href)
        elif entry.is_acquisition:
            self.download_and_open(entry)

    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if not query or self.current_feed is None or not self.current_feed.search_template:
            return

        search_url = self.current_feed.search_template.replace("{searchTerms}", quote(query))
        self.searching = True
        self.feed_stack.append(self._current_url)  # so escape can back out of search results
        self.load_feed(search_url)

        search_bar = self.query_one("#opds-search-bar", Vertical)
        search_bar.display = False
        self.query_one("#opds-table", DataTable).focus()

    def download_and_open(self, entry: OPDSEntry) -> None:
        acquisition_link = entry.acquisition_links[0]
        filename = _safe_filename(entry.title) + ".epub"
        destination = DOWNLOAD_DIR / filename

        self.notify(f"Downloading {entry.title}...")
        saved_path = download_book(acquisition_link.href, destination)
        self.notify(f"Downloaded to {saved_path.name}")

        self.app.open_book(saved_path)

    def action_switch_server(self) -> None:
        self.app.switch_opds_server()

    def action_start_search(self) -> None:
        if self.current_feed is None or not self.current_feed.search_template:
            self.notify("This server doesn't support search.")
            return
        search_bar = self.query_one("#opds-search-bar", Vertical)
        search_bar.display = True
        self.query_one("#opds-search-input", Input).focus()    

    def action_go_back(self) -> None:
        if self.feed_stack:
            previous_url = self.feed_stack.pop()
            self.load_feed(previous_url)
        else:
            self.app.pop_screen()
