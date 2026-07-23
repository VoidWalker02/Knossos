# knossos/ui/screens/library.py

from __future__ import annotations

from pathlib import Path

from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label

from knossos.library import scan_libraries, LibraryEntry


class LibraryScreen(Screen):
    """Shows scanned EPUBs from a directory; selecting one opens it for reading."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("o", "open_opds", "Browse OPDS"),
    ]

    def __init__(self, library_dirs: Path) -> None:
        super().__init__()
        self.library_dirs = library_dirs
        self.entries = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield ListView(id="library-list")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Knossos — Library"
        self.entries = scan_libraries(self.library_dirs)

        list_view = self.query_one("#library-list", ListView)
        for entry in self.entries:
            label_text = entry.title
            if entry.author:
                label_text += f"  —  {entry.author}"
            item = ListItem(Label(label_text))
            item.book_path = entry.path
            list_view.append(item)



    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.app.open_book(event.item.book_path)

    def action_open_opds(self) -> None:
        self.app.open_opds_browser()

    def action_quit(self) -> None:
        self.app.exit()


