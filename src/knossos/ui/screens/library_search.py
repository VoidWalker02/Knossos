# knossos/ui/screens/library_search.py

from __future__ import annotations

from pathlib import Path

from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Header, Footer, Input, DataTable, Static

from knossos.library import LibraryEntry
from knossos.library_search import search_library, LibrarySearchResult


class LibrarySearchScreen(Screen):
    """Search across every book in the library at once."""

    CSS = """
    #ls-body {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, entries: list[LibraryEntry]) -> None:
        super().__init__()
        self.entries = entries
        self.row_key_to_result: dict[str, LibrarySearchResult] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Search your whole library...", id="ls-input")
        yield Static("", id="ls-status")
        yield DataTable(id="ls-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Knossos — Library Search"
        table = self.query_one("#ls-table", DataTable)
        table.add_columns("Book", "Chapter", "Match")
        table.zebra_stripes = True
        self.query_one("#ls-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if not query:
            return

        status = self.query_one("#ls-status", Static)
        status.update(f"Searching {len(self.entries)} book(s)...")

        results = search_library(self.entries, query)

        table = self.query_one("#ls-table", DataTable)
        table.clear()
        self.row_key_to_result = {}

        for index, result in enumerate(results[:200]):
            row_key = str(index)
            table.add_row(result.book_title, result.chapter_title, result.snippet, key=row_key)
            self.row_key_to_result[row_key] = result

        status.update(f"{len(results)} match(es) found" + (" (showing first 200)" if len(results) > 200 else ""))
        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        result = self.row_key_to_result.get(str(event.row_key.value))
        if result is not None:
            self.app.open_book(result.book_path, initial_chapter_index=result.chapter_index)

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()    
