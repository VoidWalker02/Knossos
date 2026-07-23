# knossos/ui/screens/library.py

from __future__ import annotations

from pathlib import Path

from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal

from textual.widgets import Header, Footer, ListView, ListItem, Label, DataTable, Input, Static

from knossos.library import scan_libraries, LibraryEntry
from knossos.config import get_paths
from knossos.db import connect, get_book_id_by_path, load_progress

SORT_MODES = ["title", "author", "source"]


class LibraryScreen(Screen):


    CSS = """
    #library-body {
        height: 1fr;
    }
    #library-table {
        width: 2fr;
    }
    #details-panel {
        width: 1fr;
        border-left: solid $panel;
        padding: 1 2;
    }
    """


    """Shows scanned EPUBs from a directory; selecting one opens it for reading."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("o", "open_opds", "Browse OPDS"),
        ("s", "cycle_sort", "Sort"),
        ("/", "start_filter", "Filter"),
        ("escape", "close_filter", "Close filter"),
    ]
   

    
    def __init__(self, library_dirs: list[Path]) -> None:
        super().__init__()
        self.library_dirs = library_dirs
        self.all_entries: list[LibraryEntry] = []
        self.sort_mode_index = 0
        self.filter_query = ""
        self.row_key_to_entry: dict[str, LibraryEntry] = {}
        self.db_conn = None

 


    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="filter-bar"):
            yield Input(placeholder="Filter by title/author...", id="filter-input")
        with Horizontal(id="library-body"):
            yield DataTable(id="library-table", cursor_type="row")
            with Vertical(id="details-panel"):
                yield Static("Select a book to see details.", id="details-content")
        yield Footer()



    def on_mount(self) -> None:
        self.title = "Knossos — Library"
        self.all_entries = scan_libraries(self.library_dirs)
        self.query_one("#filter-bar", Vertical).display = False

        paths = get_paths()
        self.db_conn = connect(paths.db_file)

        table = self.query_one("#library-table", DataTable)
        table.add_columns("Title", "Author", "Source")
        table.zebra_stripes = True

        self.refresh_table()
        table.focus()
     
    def current_sort_mode(self) -> str:
        return SORT_MODES[self.sort_mode_index]

    def sorted_filtered_entries(self) -> list[LibraryEntry]:
        entries = self.all_entries

        if self.filter_query:
            query = self.filter_query.lower()
            entries = [
                e for e in entries
                if query in e.title.lower() or (e.author and query in e.author.lower())
            ]

        mode = self.current_sort_mode()
        if mode == "title":
            entries = sorted(entries, key=lambda e: e.title.lower())
        elif mode == "author":
            entries = sorted(entries, key=lambda e: (e.author or "").lower())
        elif mode == "source":
            entries = sorted(entries, key=lambda e: (str(e.source_dir), e.title.lower()))

        return entries

    def refresh_table(self) -> None:
        entries = self.sorted_filtered_entries()
        mode = self.current_sort_mode()
        self.sub_title = f"Sorted by {mode} — {len(entries)} book(s)"

        table = self.query_one("#library-table", DataTable)
        table.clear()
        self.row_key_to_entry = {}

        for entry in entries:
            row_key = str(entry.path)
            table.add_row(
                entry.title,
                entry.author or "—",
                entry.source_dir.name,
                key=row_key,
            )
            
            self.row_key_to_entry[row_key] = entry
    


    def action_cycle_sort(self) -> None:
        self.sort_mode_index = (self.sort_mode_index + 1) % len(SORT_MODES)
        self.refresh_table()

    def action_start_filter(self) -> None:
        filter_bar = self.query_one("#filter-bar", Vertical)
        filter_bar.display = True
        self.query_one("#filter-input", Input).focus()

      

    def action_close_filter(self) -> None:
        filter_bar = self.query_one("#filter-bar", Vertical)
        if filter_bar.display:
            self.filter_query = ""
            self.query_one("#filter-input", Input).value = ""
            filter_bar.display = False
            self.refresh_table()
            self.query_one("#library-table", DataTable).focus()      

    
    def on_input_changed(self, event: Input.Changed) -> None:
        self.filter_query = event.value
        self.refresh_table()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.query_one("#library-table", DataTable).focus()

    # knossos/ui/screens/library.py (expand the debug temporarily)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        key = str(event.row_key.value)
        
        entry = self.row_key_to_entry.get(key)
        if entry is not None:
            self.app.open_book(entry.path)  

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Fires as the cursor moves (not just on Enter) — updates the
        details panel to reflect whatever row is currently highlighted."""
        entry = self.row_key_to_entry.get(str(event.row_key.value))
        if entry is not None:
            self._show_details(entry)

    

    def _show_details(self, entry: LibraryEntry) -> None:
        book_id = get_book_id_by_path(self.db_conn, str(entry.path.resolve()))
        progress_line = "Not started yet."
        if book_id is not None:
            progress = load_progress(self.db_conn, book_id)
            if progress is not None:
                chapter_index, _scroll_y = progress
                progress_line = f"Last opened at chapter {chapter_index + 1}."

        details = (
            f"[bold]{entry.title}[/bold]\n\n"
            f"Author: {entry.author or 'Unknown'}\n"
            f"Source: {entry.source_dir.name}\n\n"
            f"{progress_line}\n\n"
            f"[dim]{entry.path}[/dim]"
        )
        self.query_one("#details-content", Static).update(details)



    def on_list_view_selected(self, event: ListView.Selected) -> None:
        self.app.open_book(event.item.book_path)

    def action_open_opds(self) -> None:
        self.app.open_opds_browser()

    def action_quit(self) -> None:
        self.app.exit()


