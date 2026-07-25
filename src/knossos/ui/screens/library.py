# knossos/ui/screens/library.py

from __future__ import annotations

from pathlib import Path

from rich.text import Text


from textual.screen import Screen
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal

from textual.widgets import Header, Footer, ListView, ListItem, Label, DataTable, Input, Static

from knossos.library import scan_libraries, LibraryEntry
from knossos.config import get_paths
from knossos.db import connect, get_book_id_by_path, load_progress
from knossos.db import get_most_recent_book
from knossos.ui.screens.library_search import LibrarySearchScreen



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
        ("f", "full_search", "Search library"),
        ("c", "continue_reading", "Continue reading"),

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

        if mode == "source":
            self._populate_grouped_by_source(table, entries)
        else:
            self._populate_flat(table, entries)



    def _populate_flat(self, table: DataTable, entries: list[LibraryEntry]) -> None:
        for entry in entries:
            row_key = str(entry.path)
            table.add_row(entry.title, entry.author or "—", entry.source_dir.name, key=row_key)
            self.row_key_to_entry[row_key] = entry

    def _populate_grouped_by_source(self, table: DataTable, entries: list[LibraryEntry]) -> None:
        current_source: Path | None = None
        header_index = 0

        for entry in entries:
            if entry.source_dir != current_source:
                current_source = entry.source_dir
                header_index += 1
                header_text = Text(f"— {current_source} —", style="bold italic $accent")
                # Header rows get a distinct, unmatched key prefix so they're
                # never looked up in row_key_to_entry (and therefore never
                # "openable" — selecting one is silently a no-op).
                table.add_row(header_text, "", "", key=f"header:{header_index}")

            row_key = str(entry.path)
            table.add_row(entry.title, entry.author or "—", "", key=row_key)
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

    def action_continue_reading(self) -> None:
        row = get_most_recent_book(self.db_conn)
        if row is None:
            self.notify("No reading progress yet — open a book first.")
            return

        book_path = Path(row["path"])
        if not book_path.exists():
            self.notify(f"'{row['title']}' was moved or deleted.")
            return

        self.app.open_book(book_path)


    def action_full_search(self) -> None:
        self.app.push_screen(LibrarySearchScreen(self.all_entries))    

    
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


