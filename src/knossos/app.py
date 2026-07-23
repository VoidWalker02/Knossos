# knossos/app.py

from __future__ import annotations

import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Static, ListView, ListItem, Label
from textual.screen import Screen

from knossos.config import get_paths
from knossos.db import connect, get_or_create_book, save_progress, load_progress
from knossos.epub.book import (
    load_book,
    get_metadata,
    get_reading_order,
    get_toc,
    chapter_to_text,
    chapter_to_markup,
)
from knossos.db import (
    connect,
    get_or_create_book,
    save_progress,
    load_progress,
    add_bookmark,
    list_bookmarks,
    delete_bookmark,
)
from knossos.ui.screens.library import LibraryScreen

from knossos.ui.screens.opds import OPDSScreen


from knossos.config import get_paths, load_config, save_config

from textual.widgets import Input
from textual.containers import Vertical

from knossos.epub.search import search_book, SearchResult

from knossos.themes import ALL_THEMES

DEFAULT_MAX_WIDTH = 80
MIN_MAX_WIDTH = 40
MAX_MAX_WIDTH = 200
WIDTH_STEP = 5

class ReaderScreen(Screen):
    """The actual reading view. Paging, TOC, scroll memory, progress persistence."""


    CSS = """
    ReaderScreen {
        align: center top;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("n", "next_chapter", "Next chapter"),
        ("p", "prev_chapter", "Prev chapter"),
        ("t", "toggle_toc", "Table of contents"),
        ("b", "add_bookmark", "Add bookmark"),
        ("B", "toggle_bookmarks", "View bookmarks"),
        ("d", "delete_bookmark", "Delete bookmark"),
        ("slash", "start_search", "Search"),
        ("+", "widen_text", "Widen text"),
        ("-", "narrow_text", "Narrow text"),
        ("escape", "back_to_library", "Library"),
    ]

    def __init__(self, book_path: Path) -> None:
        super().__init__()
        self.book_path = book_path
        self.chapters = []
        self.toc = []
        self.current_index = 0
        self.scroll_positions: dict[int, float] = {}
        self.db_conn = None
        self.book_id: int | None = None
        self.max_width = DEFAULT_MAX_WIDTH  # actual value set in on_mount from config


    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="reader-pane"):
            yield Static(id="reader-content")
        yield ListView(id="toc-panel")
        yield ListView(id="bookmarks-panel")
        with Vertical(id="search-panel"):
            yield Input(placeholder="Search this book...", id="search-input")
            yield ListView(id="search-results")
        yield Footer()

    def on_mount(self) -> None:
        book = load_book(self.book_path)
        meta = get_metadata(book)
        self.title = meta.title

        self.chapters = get_reading_order(book)
        self.toc = get_toc(book, self.chapters)

        paths = get_paths()
        self.db_conn = connect(paths.db_file)
        self.book_id = get_or_create_book(
            self.db_conn,
            path=str(self.book_path.resolve()),
            title=meta.title,
            author=meta.author,
        )

        saved = load_progress(self.db_conn, self.book_id)
        if saved is not None:
            self.current_index, initial_scroll = saved
            self.scroll_positions[self.current_index] = initial_scroll
        else:
            self.current_index = 0

        app_config = self.app.config
        self.max_width = app_config.max_width or DEFAULT_MAX_WIDTH
        self._apply_reader_width()

        self.build_toc_panel()
        self.query_one("#toc-panel", ListView).display = False
        self.query_one("#bookmarks-panel", ListView).display = False
        self.query_one("#search-panel", Vertical).display = False

        self.render_current_chapter()

    def build_toc_panel(self) -> None:
        toc_panel = self.query_one("#toc-panel", ListView)
        for entry in self.toc:
            indent = "  " * entry.level
            item = ListItem(Label(f"{indent}{entry.title}"))
            item.chapter_position = entry.chapter_position
            toc_panel.append(item)

    def render_current_chapter(self) -> None:
        chapter = self.chapters[self.current_index]
        text = chapter_to_markup(chapter)
        self.query_one("#reader-content", Static).update(text)
        self.sub_title = f"Chapter {self.current_index + 1} / {len(self.chapters)}"

        reader_pane = self.query_one("#reader-pane", VerticalScroll)
        saved_position = self.scroll_positions.get(self.current_index)
        if saved_position is not None:
            reader_pane.scroll_to(y=saved_position, animate=False)
        else:
            reader_pane.scroll_home(animate=False)

    def _save_scroll_position(self) -> None:
        reader_pane = self.query_one("#reader-pane", VerticalScroll)
        self.scroll_positions[self.current_index] = reader_pane.scroll_y

    def _persist_progress(self) -> None:
        if self.db_conn is not None and self.book_id is not None:
            reader_pane = self.query_one("#reader-pane", VerticalScroll)
            save_progress(
                self.db_conn,
                self.book_id,
                chapter_index=self.current_index,
                scroll_y=reader_pane.scroll_y,
            )
            self.db_conn.close()
            self.db_conn = None

    def action_next_chapter(self) -> None:
        if self.current_index < len(self.chapters) - 1:
            self._save_scroll_position()
            self.current_index += 1
            self.render_current_chapter()

    def action_prev_chapter(self) -> None:
        if self.current_index > 0:
            self._save_scroll_position()
            self.current_index -= 1
            self.render_current_chapter()

    def _apply_reader_width(self) -> None:
        reader_pane = self.query_one("#reader-pane", VerticalScroll)
        reader_pane.styles.width = self.max_width

    def action_widen_text(self) -> None:
        self.max_width = min(self.max_width + WIDTH_STEP, MAX_MAX_WIDTH)
        self._apply_reader_width()
        self._save_max_width()

    def action_narrow_text(self) -> None:
        self.max_width = max(self.max_width - WIDTH_STEP, MIN_MAX_WIDTH)
        self._apply_reader_width()
        self._save_max_width()

    def _save_max_width(self) -> None:
        self.app.config.max_width = self.max_width
        save_config(self.app.paths, self.app.config)
        self.notify(f"Text width: {self.max_width}")

    def action_add_bookmark(self) -> None:
        reader_pane = self.query_one("#reader-pane", VerticalScroll)
        chapter_title = self._chapter_title_for(self.current_index)
        add_bookmark(
            self.db_conn,
            self.book_id,
            chapter_index=self.current_index,
            scroll_y=reader_pane.scroll_y,
            label=chapter_title,
        )
        self.notify(f"Bookmark added: {chapter_title}")

    def action_start_search(self) -> None:
        reader_pane = self.query_one("#reader-pane", VerticalScroll)
        search_panel = self.query_one("#search-panel", Vertical)

        reader_pane.display = False
        search_panel.display = True
        self.query_one("#search-input", Input).focus()


    def _chapter_title_for(self, chapter_index: int) -> str:
        """Best-effort human-readable label for a chapter, using the TOC
        if there's a matching entry, otherwise uses generic fallback."""
        for entry in self.toc:
            if entry.chapter_position == chapter_index:
                return entry.title
        return f"Chapter {chapter_index + 1}"

    def action_toggle_bookmarks(self) -> None:
        panel = self.query_one("#bookmarks-panel", ListView)
        reader_pane = self.query_one("#reader-pane", VerticalScroll)
        showing = panel.display

        if not showing:
            self._refresh_bookmarks_panel()

        panel.display = not showing
        reader_pane.display = showing

    def _refresh_bookmarks_panel(self) -> None:
        panel = self.query_one("#bookmarks-panel", ListView)
        panel.clear()
        for row in list_bookmarks(self.db_conn, self.book_id):
            label_text = row["label"] or f"Chapter {row['chapter_index'] + 1}"
            item = ListItem(Label(label_text))
            item.bookmark_id = row["id"]
            item.chapter_index = row["chapter_index"]
            item.scroll_y = row["scroll_y"]
            panel.append(item)

    def action_delete_bookmark(self) -> None:
        panel = self.query_one("#bookmarks-panel", ListView)

        # Only meaningful while the bookmarks panel is open and something's highlighted.
        if not panel.display:
            return

        highlighted = panel.highlighted_child
        if highlighted is None:
            return

        delete_bookmark(self.db_conn, highlighted.bookmark_id)
        self.notify("Bookmark deleted")
        self._refresh_bookmarks_panel()

    def action_toggle_toc(self) -> None:
        toc_panel = self.query_one("#toc-panel", ListView)
        reader_pane = self.query_one("#reader-pane", VerticalScroll)
        showing = toc_panel.display
        toc_panel.display = not showing
        reader_pane.display = showing

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        toc_panel = self.query_one("#toc-panel", ListView)
        bookmarks_panel = self.query_one("#bookmarks-panel", ListView)

        self._save_scroll_position()

        if event.list_view is toc_panel:
            self.current_index = event.item.chapter_position
            self.action_toggle_toc()
        elif event.list_view is bookmarks_panel:
            self.current_index = event.item.chapter_index
            self.scroll_positions[self.current_index] = event.item.scroll_y
            self.action_toggle_bookmarks()

        self.render_current_chapter()

    def action_back_to_library(self) -> None:
        search_panel = self.query_one("#search-panel", Vertical)
        toc_panel = self.query_one("#toc-panel", ListView)
        bookmarks_panel = self.query_one("#bookmarks-panel", ListView)

        if search_panel.display:
            self._close_search()
            return

        if toc_panel.display:
            self.action_toggle_toc()
            return

        if bookmarks_panel.display:
            self.action_toggle_bookmarks()
            return

        # Nothing overlaying the reader — actually leave to the library.
        self._persist_progress()    
        self.app.pop_screen()
    
    def action_quit(self) -> None:
        self._persist_progress()
        self.app.exit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value
        chapter_titles = {entry.chapter_position: entry.title for entry in self.toc}
        results = search_book(self.chapters, query, chapter_titles=chapter_titles)

        results_list = self.query_one("#search-results", ListView)
        results_list.clear()

        for result in results[:50]:  # cap displayed results to keep the panel usable
            item = ListItem(Label(f"[{result.chapter_title}] {result.snippet}"))
            item.chapter_index = result.chapter_index
            results_list.append(item)

        results_list.focus()
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        toc_panel = self.query_one("#toc-panel", ListView)
        bookmarks_panel = self.query_one("#bookmarks-panel", ListView)
        search_results = self.query_one("#search-results", ListView)

        self._save_scroll_position()

        if event.list_view is toc_panel:
            self.current_index = event.item.chapter_position
            self.action_toggle_toc()
        elif event.list_view is bookmarks_panel:
            self.current_index = event.item.chapter_index
            self.scroll_positions[self.current_index] = event.item.scroll_y
            self.action_toggle_bookmarks()
        elif event.list_view is search_results:
            self.current_index = event.item.chapter_index
            self._close_search()

        self.render_current_chapter()

    def _close_search(self) -> None:
        self.query_one("#search-panel", Vertical).display = False
        self.query_one("#reader-pane", VerticalScroll).display = True 

# knossos/app.py (changes to KnossosApp)

class KnossosApp(App):

    BINDINGS = [
        ("ctrl+t", "toggle_theme", "Toggle theme"),
    ]

    def __init__(self, library_dir: Path) -> None:
        super().__init__()
        self.library_dir = library_dir
        self.paths = get_paths()
        self.config = load_config(self.paths)

    def on_mount(self) -> None:
        for theme in ALL_THEMES:
            self.register_theme(theme)

        configured_theme = self.config.theme
        if configured_theme in self.available_themes:
            self.theme = configured_theme
        else:
            self.theme = "textual-dark"

        self.push_screen(LibraryScreen(self.library_dir))  
    

    def action_toggle_theme(self) -> None:
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"
        self.config.theme = self.theme
        save_config(self.paths, self.config)
        self.notify(f"Theme: {self.config.theme}")

     
     
    
    def open_book(self, book_path: Path) -> None:
        self.push_screen(ReaderScreen(book_path))

    def open_opds_browser(self) -> None:
        self.push_screen(OPDSScreen())
def main() -> None:
    paths = get_paths()
    config = load_config(paths)

    if len(sys.argv) >= 2:
        library_dir = Path(sys.argv[1])
    elif config.library_dir:
        library_dir = Path(config.library_dir)
    else:
        print("Usage: knossos <path-to-library-directory>")
        print("(or set a default library_dir in your config file)")
        sys.exit(1)

    KnossosApp(library_dir).run()


if __name__ == "__main__":
    main()
