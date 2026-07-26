# knossos/app.py

from __future__ import annotations

import sys
from pathlib import Path

import textwrap

from textual.app import App, ComposeResult
from textual.binding import Binding

from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Static, ListView, ListItem, Label
from textual.screen import Screen

from knossos.config import get_paths
from knossos.db import connect, get_or_create_book, save_progress, load_progress, add_annotation, list_annotations, delete_annotation
from knossos.dictionary import lookup_word

from knossos.epub.book import (
    load_book,
    get_metadata,
    get_reading_order,
    get_toc,
    chapter_to_text,
    chapter_to_markup,
    apply_highlights,
)
from knossos.db import (
    connect,
    get_or_create_book,
    save_progress,
    load_progress,
    add_bookmark,
    list_bookmarks,
    delete_bookmark,
    update_annotation_note,
)
from knossos.ui.screens.library import LibraryScreen

from knossos.ui.screens.opds import OPDSScreen


from knossos.config import get_paths, load_config, save_config

from textual.widgets import Input
from textual.containers import Vertical

from knossos.epub.search import search_book, SearchResult

from knossos.themes import ALL_THEMES

from knossos.epub.book import apply_paragraph_spacing  
from knossos.epub.book import normalize_excerpt


DEFAULT_MAX_WIDTH = 80
MIN_MAX_WIDTH = 40
MAX_MAX_WIDTH = 200
WIDTH_STEP = 5
DEFAULT_PARAGRAPH_SPACING = 1
MIN_PARAGRAPH_SPACING = 0
MAX_PARAGRAPH_SPACING = 4



class ReaderScreen(Screen):
    """The actual reading view. Paging, TOC, scroll memory, progress persistence."""


    CSS = """
    ReaderScreen {
        align: center top;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", id="reader.quit"),
        Binding("n", "next_chapter", "Next chapter", id="reader.next_chapter"),
        Binding("p", "prev_chapter", "Prev chapter", id="reader.prev_chapter"),
        Binding("t", "toggle_toc", "Table of contents", id="reader.toc"),
        Binding("b", "add_bookmark", "Add bookmark", id="reader.add_bookmark"),
        Binding("B", "toggle_bookmarks", "View bookmarks", id="reader.view_bookmarks"),
        Binding("d", "delete_bookmark", "Delete bookmark", id="reader.delete"),
        Binding("slash", "start_search", "Search", id="reader.search"),
        Binding("+", "widen_text", "Widen text", id="reader.widen"),
        Binding("-", "narrow_text", "Narrow text", id="reader.narrow"),
        Binding("[", "decrease_spacing", "Less spacing", id="reader.spacing_down"),
        Binding("]", "increase_spacing", "More spacing", id="reader.spacing_up"),
        Binding("h", "start_highlight", "Highlight selection", id="reader.highlight"),
        Binding("H", "toggle_annotations", "View annotations", id="reader.view_annotations"),
        Binding("r", "edit_annotation", "Edit note", id="reader.edit_annotation"),
        Binding("z", "start_dictionary_lookup", "Look up word", id="reader.dictionary"),
        Binding("escape", "back_to_library", "Library", id="reader.back"),
    ]

    def __init__(self, book_path: Path, initial_chapter_index: int | None = None) -> None:
        super().__init__()
        self.book_path = book_path
        self.initial_chapter_index = initial_chapter_index
        self.chapters = []
        self.toc = []
        self.current_index = 0
        self.scroll_positions: dict[int, float] = {}
        self.db_conn = None
        self.book_id: int | None = None
        self.max_width = DEFAULT_MAX_WIDTH
        self.paragraph_spacing = DEFAULT_PARAGRAPH_SPACING



    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="reader-pane"):
            yield Static(id="reader-content")
        yield ListView(id="toc-panel")
        yield ListView(id="bookmarks-panel")
        with Vertical(id="search-panel"):
            yield Input(placeholder="Search this book...", id="search-input")
            yield ListView(id="search-results")
        with Vertical(id="highlight-note-bar"):
            yield Input(placeholder="Optional note (Enter to save, empty is fine)...", id="highlight-note-input")
        yield ListView(id="annotations-panel")
        with Vertical(id="dictionary-bar"):
            yield Input(placeholder="Word to look up...", id="dictionary-input")
        with Vertical(id="dictionary-panel"):
            yield Static("", id="dictionary-content")
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
            identifier=meta.identifier,
        )

        saved = load_progress(self.db_conn, self.book_id)
        if saved is not None:
            self.current_index, initial_scroll = saved
            self.scroll_positions[self.current_index] = initial_scroll
        else:
            self.current_index = 0

        app_config = self.app.config
        self.max_width = app_config.max_width or DEFAULT_MAX_WIDTH
        self.paragraph_spacing = (
            app_config.paragraph_spacing
            if app_config.paragraph_spacing is not None
            else DEFAULT_PARAGRAPH_SPACING
        )
        self._apply_reader_width()

        self.build_toc_panel()
        self.query_one("#toc-panel", ListView).display = False
        self.query_one("#bookmarks-panel", ListView).display = False
        self.query_one("#search-panel", Vertical).display = False
        self.query_one("#highlight-note-bar", Vertical).display = False
        self.query_one("#annotations-panel", ListView).display = False
        self.query_one("#dictionary-bar", Vertical).display = False
        self.query_one("#dictionary-panel", Vertical).display = False
        self._pending_highlight_text: str | None = None
        self._pending_highlight_paragraph_index: int | None = None

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
        chapter_excerpts = [
            row["excerpt"] for row in list_annotations(self.db_conn, self.book_id)
            if row["chapter_index"] == self.current_index
        ]
        if chapter_excerpts:
            plain = chapter_to_text(chapter)
            text = apply_highlights(text, plain, chapter_excerpts)




        text = apply_paragraph_spacing(text, self.paragraph_spacing)
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



    # knossos/app.py (new helper method on ReaderScreen)

    def _estimate_scroll_for_paragraph(self, chapter_index: int, paragraph_index: int) -> float:
        """
        Rough estimate of the scroll_y a given paragraph starts at, based on
        wrapping plain (unstyled) text at the current reading width. This is
        an approximation — Rich's actual wrapping algorithm can differ
        slightly (punctuation, unicode width, etc.) — but lands close enough
        to be far better than always jumping to the top of the chapter.
        """
        chapter = self.chapters[chapter_index]
        paragraphs = [p.strip() for p in chapter_to_text(chapter).split("\n\n") if p.strip()]

        lines_before = 0
        for para in paragraphs[:paragraph_index]:
            wrapped = textwrap.wrap(para, width=self.max_width) or [""]
            lines_before += len(wrapped) + self.paragraph_spacing

        return float(lines_before)    

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

    def action_start_highlight(self) -> None:
        selected_text = self.get_selected_text()

        if not selected_text or not selected_text.strip():
            self.notify(
                "No text selected. Click and drag to select a passage first, then press h.",
                severity="warning",
            )
            return

        excerpt = normalize_excerpt(selected_text)
        self._pending_highlight_text = excerpt
        self._pending_highlight_paragraph_index = self._find_paragraph_index_for_excerpt(excerpt)

        reader_pane = self.query_one("#reader-pane", VerticalScroll)
        note_bar = self.query_one("#highlight-note-bar", Vertical)
        reader_pane.display = False
        note_bar.display = True
        self.query_one("#highlight-note-input", Input).focus()


    def _find_paragraph_index_for_excerpt(self, excerpt: str) -> int | None:
        """
        Best-effort: find which paragraph of the current chapter overlaps the
        captured excerpt, for scroll-position estimation. excerpt is already
        normalized (single-spaced) by the caller.
        """
        chapter = self.chapters[self.current_index]
        paragraphs = [p.strip() for p in chapter_to_text(chapter).split("\n\n") if p.strip()]

        for index, para in enumerate(paragraphs):
            normalized_para = normalize_excerpt(para)
            if normalized_para in excerpt or excerpt in normalized_para:
                return index

        return None    


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
        bookmarks_panel = self.query_one("#bookmarks-panel", ListView)
        annotations_panel = self.query_one("#annotations-panel", ListView)

        if bookmarks_panel.display:
            highlighted = bookmarks_panel.highlighted_child
            if highlighted is not None:
                delete_bookmark(self.db_conn, highlighted.bookmark_id)
                self.notify("Bookmark deleted")
                self._refresh_bookmarks_panel()
            return

        if annotations_panel.display:
            highlighted = annotations_panel.highlighted_child
            if highlighted is not None:
                delete_annotation(self.db_conn, highlighted.annotation_id)
                self.notify("Annotation deleted")
                self._refresh_annotations_panel()
                self.render_current_chapter()
            return

        
    def action_toggle_toc(self) -> None:
        toc_panel = self.query_one("#toc-panel", ListView)
        reader_pane = self.query_one("#reader-pane", VerticalScroll)
        showing = toc_panel.display
        toc_panel.display = not showing
        reader_pane.display = showing

   
    def action_back_to_library(self) -> None:
        search_panel = self.query_one("#search-panel", Vertical)
        toc_panel = self.query_one("#toc-panel", ListView)
        bookmarks_panel = self.query_one("#bookmarks-panel", ListView)
        highlight_note_bar = self.query_one("#highlight-note-bar", Vertical)
        annotations_panel = self.query_one("#annotations-panel", ListView)
        dictionary_bar = self.query_one("#dictionary-bar", Vertical)
        dictionary_panel = self.query_one("#dictionary-panel", Vertical)

        if search_panel.display:
            self._close_search()
            return
        if toc_panel.display:
            self.action_toggle_toc()
            return
        if bookmarks_panel.display:
            self.action_toggle_bookmarks()
            return
        if highlight_note_bar.display:
            highlight_note_bar.display = False
            self.query_one("#reader-pane", VerticalScroll).display = True
            self.query_one("#highlight-note-input", Input).value = ""
            self._pending_highlight_text = None
            self._pending_highlight_paragraph_index = None
            self._editing_annotation_id = None
            return        
        if annotations_panel.display:
            self.action_toggle_annotations()
            return
        if dictionary_bar.display:
            dictionary_bar.display = False
            self.query_one("#reader-pane", VerticalScroll).display = True
            return
        if dictionary_panel.display:
            self.action_close_dictionary()
            return

        self._persist_progress()
        self.app.pop_screen()   
    


    def action_quit(self) -> None:
        self._persist_progress()
        self.app.exit()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "dictionary-input":
            word = event.value.strip()
            if word:
                await self._handle_dictionary_submit(word)
            return

        if event.input.id == "highlight-note-input":
            note = event.value.strip() or None

            if self._editing_annotation_id is not None:
                update_annotation_note(self.db_conn, self._editing_annotation_id, note)
                self.notify("Annotation updated.")
                self._editing_annotation_id = None
            else:
                add_annotation(
                    self.db_conn,
                    self.book_id,
                    chapter_index=self.current_index,
                    excerpt=self._pending_highlight_text,
                    note=note,
                    paragraph_index=self._pending_highlight_paragraph_index,
                )
                self.notify("Annotation saved.")

            self._pending_highlight_text = None
            self._pending_highlight_paragraph_index = None
            self.query_one("#highlight-note-input", Input).value = ""
            self.query_one("#highlight-note-bar", Vertical).display = False
            self.query_one("#reader-pane", VerticalScroll).display = True
            self.render_current_chapter()
            return


        query = event.value
        chapter_titles = {entry.chapter_position: entry.title for entry in self.toc}
        results = search_book(self.chapters, query, chapter_titles=chapter_titles)

        results_list = self.query_one("#search-results", ListView)
        results_list.clear()

        for result in results[:50]:
            item = ListItem(Label(f"[{result.chapter_title}] {result.snippet}"))
            item.chapter_index = result.chapter_index
            results_list.append(item)

        results_list.focus()   


    def on_list_view_selected(self, event: ListView.Selected) -> None:
        toc_panel = self.query_one("#toc-panel", ListView)
        bookmarks_panel = self.query_one("#bookmarks-panel", ListView)
        search_results = self.query_one("#search-results", ListView)
        annotations_panel = self.query_one("#annotations-panel", ListView)

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
        elif event.list_view is annotations_panel:
            self.current_index = event.item.chapter_index
            if event.item.paragraph_index is not None:
                self.scroll_positions[self.current_index] = self._estimate_scroll_for_paragraph(
                    event.item.chapter_index, event.item.paragraph_index
                )
            self.action_toggle_annotations()

        self.render_current_chapter()

    def action_toggle_annotations(self) -> None:
        panel = self.query_one("#annotations-panel", ListView)
        reader_pane = self.query_one("#reader-pane", VerticalScroll)
        showing = panel.display

        if not showing:
            self._refresh_annotations_panel()

        panel.display = not showing
        reader_pane.display = showing


    def _refresh_annotations_panel(self) -> None:
        panel = self.query_one("#annotations-panel", ListView)
        panel.clear()
        for row in list_annotations(self.db_conn, self.book_id):
            preview = row["excerpt"][:80] + ("…" if len(row["excerpt"]) > 80 else "")
            label_text = preview
            if row["note"]:
                label_text += f"\n[dim]Note: {row['note']}[/dim]"
            item = ListItem(Label(label_text))
            item.annotation_id = row["id"]
            item.chapter_index = row["chapter_index"]
            item.paragraph_index = row["paragraph_index"]
            item.note = row["note"]
            panel.append(item)    

    def _close_search(self) -> None:
        self.query_one("#search-panel", Vertical).display = False
        self.query_one("#reader-pane", VerticalScroll).display = True

    def action_start_dictionary_lookup(self) -> None:
        reader_pane = self.query_one("#reader-pane", VerticalScroll)
        dictionary_bar = self.query_one("#dictionary-bar", Vertical)

        reader_pane.display = False
        dictionary_bar.display = True
        self.query_one("#dictionary-input", Input).focus()


     
    def action_edit_annotation(self) -> None:
        annotations_panel = self.query_one("#annotations-panel", ListView)
        if not annotations_panel.display:
            return

        highlighted = annotations_panel.highlighted_child
        if highlighted is None:
            return

        self._editing_annotation_id = highlighted.annotation_id
        note_input = self.query_one("#highlight-note-input", Input)
        note_input.value = highlighted.note or ""

        annotations_panel.display = False
        self.query_one("#highlight-note-bar", Vertical).display = True
        note_input.focus()



    async def _handle_dictionary_submit(self, word: str) -> None:
        self.query_one("#dictionary-bar", Vertical).display = False

        panel = self.query_one("#dictionary-panel", Vertical)
        content = self.query_one("#dictionary-content", Static)
        content.update(f"Looking up '{word}'...")
        panel.display = True

        result = await lookup_word(word)

        if result is None:
            content.update(f"No definition found for '{word}'.")
            return

        lines = [f"[bold]{result.word}[/bold]"]
        if result.phonetic:
            lines.append(f"[dim]{result.phonetic}[/dim]")
        lines.append("")

        for d in result.definitions[:5]:  # cap displayed senses to keep the panel readable
            lines.append(f"[italic]{d.part_of_speech}[/italic]  {d.definition}")
            if d.example:
                lines.append(f"  [dim]e.g. \"{d.example}\"[/dim]")
            lines.append("")

        content.update("\n".join(lines))

    def action_close_dictionary(self) -> None:
        panel = self.query_one("#dictionary-panel", Vertical)
        if panel.display:
            panel.display = False
            self.query_one("#reader-pane", VerticalScroll).display = True

    def action_increase_spacing(self) -> None:
        self.paragraph_spacing = min(self.paragraph_spacing + 1, MAX_PARAGRAPH_SPACING)
        self._save_paragraph_spacing()
        self.render_current_chapter()

    def action_decrease_spacing(self) -> None:
        self.paragraph_spacing = max(self.paragraph_spacing - 1, MIN_PARAGRAPH_SPACING)
        self._save_paragraph_spacing()
        self.render_current_chapter()

    def _save_paragraph_spacing(self) -> None:
        self.app.config.paragraph_spacing = self.paragraph_spacing
        save_config(self.app.paths, self.app.config)
        self.notify(f"Paragraph spacing: {self.paragraph_spacing}")        

# knossos/app.py (changes to KnossosApp)

class KnossosApp(App):

    BINDINGS = [
        Binding("ctrl+t", "toggle_theme", "Toggle theme", id="app.toggle_theme"),
    ]

    
    def __init__(self, library_dirs: list[Path]) -> None:
        super().__init__()
        self.library_dirs = library_dirs
        self.paths = get_paths()
        self.config = load_config(self.paths)
        self.current_opds_server_index = 0
        self._theme_restored = False  # guards against saving during initial load

    def on_mount(self) -> None:
        for theme in ALL_THEMES:
            self.register_theme(theme)

        configured_theme = self.config.theme
        if configured_theme in self.available_themes:
            self.theme = configured_theme
        else:
            self.theme = "textual-dark"

        self._theme_restored = True

        if self.config.keybindings:
            self.set_keymap(self.config.keybindings)

        self.push_screen(LibraryScreen(self.library_dirs))
    

    
    def watch_theme(self, old_theme: str, new_theme: str) -> None:
        """Called automatically by Textual whenever self.theme changes —
        whether from our own action_toggle_theme, the command palette's
        theme picker, or anywhere else. Persists the choice either way."""
        if not self._theme_restored:
            return  # don't re-save the value we just loaded from config on startup
        self.config.theme = new_theme
        save_config(self.paths, self.config)

    def action_toggle_theme(self) -> None:
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"
        self.notify(f"Theme: {self.theme}")
        # No need to call save_config here anymore — watch_theme handles it
        # automatically now that it fires on every theme change.


     
     
    
    def open_book(self, book_path: Path, initial_chapter_index: int | None = None) -> None:
        self.push_screen(ReaderScreen(book_path, initial_chapter_index=initial_chapter_index))


    def open_opds_browser(self) -> None:
        if not self.config.opds_servers:
            self.notify("No OPDS servers configured.")
            return
        server = self.config.opds_servers[self.current_opds_server_index]
        self.push_screen(OPDSScreen(root_url=server.url))

    def switch_opds_server(self) -> None:
        """Cycle to the next configured server and re-open the browser on it."""
        if len(self.config.opds_servers) <= 1:
            self.notify("Only one OPDS server configured.")
            return
        self.current_opds_server_index = (self.current_opds_server_index + 1) % len(self.config.opds_servers)
        server = self.config.opds_servers[self.current_opds_server_index]
        self.notify(f"Switched to: {server.display_name}")
        self.pop_screen()
        self.push_screen(OPDSScreen(root_url=server.url))



def main() -> None:
    paths = get_paths()
    config = load_config(paths)

    if len(sys.argv) >= 2:
        library_dirs = [Path(sys.argv[1])]
    elif config.library_dirs:
        library_dirs = [Path(d) for d in config.library_dirs]
    else:
        print("Usage: knossos <path-to-library-directory>")
        print("(or set library_dirs in your config file)")
        sys.exit(1)

    KnossosApp(library_dirs).run()



if __name__ == "__main__":
    main()
