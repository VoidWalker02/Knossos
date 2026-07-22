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


class ReaderScreen(Screen):
    """The actual reading view — paging, TOC, scroll memory, progress persistence.
    This is everything ReaderApp used to be, now scoped to a single Screen
    so the app can switch back to the library."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("n", "next_chapter", "Next chapter"),
        ("p", "prev_chapter", "Prev chapter"),
        ("t", "toggle_toc", "Table of contents"),
        ("b", "add_bookmark", "Add bookmark"),
        ("B", "toggle_bookmarks", "View bookmarks"),
        ("d", "delete_bookmark", "Delete bookmark"),
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

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="reader-pane"):
            yield Static(id="reader-content")
        yield ListView(id="toc-panel")
        yield ListView(id="bookmarks-panel")
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

        self.build_toc_panel()
        self.query_one("#toc-panel", ListView).display = False
        self.query_one("#bookmarks-panel", ListView).display = False
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
        text = chapter_to_text(chapter)
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


    def _chapter_title_for(self, chapter_index: int) -> str:
        """Best-effort human-readable label for a chapter, using the TOC
        if we have a matching entry, otherwise a generic fallback."""
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
        self._persist_progress()
        self.app.pop_screen()

    def action_quit(self) -> None:
        self._persist_progress()
        self.app.exit()


class KnossosApp(App):
    """Top-level app: starts on the library screen, opens books into a
    reader screen, and can return to the library from there."""

    def __init__(self, library_dir: Path) -> None:
        super().__init__()
        self.library_dir = library_dir

    def on_mount(self) -> None:
        self.push_screen(LibraryScreen(self.library_dir))

    def open_book(self, book_path: Path) -> None:
        self.push_screen(ReaderScreen(book_path))


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: knossos <path-to-library-directory>")
        sys.exit(1)

    KnossosApp(Path(sys.argv[1])).run()


if __name__ == "__main__":
    main()
