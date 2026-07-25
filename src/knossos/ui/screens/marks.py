# knossos/ui/screens/marks.py

from __future__ import annotations

from pathlib import Path

from textual.screen import Screen
from textual.app import ComposeResult
from textual.widgets import Header, Footer, DataTable

from knossos.db import list_all_bookmarks, list_all_annotations


class MarksScreen(Screen):
    """Browse every bookmark and annotation across your whole library."""

    CSS = """
    MarksScreen {
        align: center top;
    }
    """

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, db_conn) -> None:
        super().__init__()
        self.db_conn = db_conn
        self.row_key_to_mark: dict[str, dict] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="marks-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Knossos — Your Marks"

        table = self.query_one("#marks-table", DataTable)
        table.add_columns("Type", "Book", "Detail", "Date")
        table.zebra_stripes = True

        marks: list[dict] = []

        for row in list_all_bookmarks(self.db_conn):
            label = row["label"] or f"Chapter {row['chapter_index'] + 1}"
            marks.append({
                "kind": "Bookmark",
                "book_path": row["path"],
                "book_title": row["title"],
                "chapter_index": row["chapter_index"],
                "paragraph_index": None,
                "detail": label,
                "created_at": row["created_at"],
            })

        for row in list_all_annotations(self.db_conn):
            preview = row["excerpt"][:60] + ("…" if len(row["excerpt"]) > 60 else "")
            detail = preview + (f"  — {row['note']}" if row["note"] else "")
            marks.append({
                "kind": "Annotation",
                "book_path": row["path"],
                "book_title": row["title"],
                "chapter_index": row["chapter_index"],
                "paragraph_index": row["paragraph_index"],
                "detail": detail,
                "created_at": row["created_at"],
            })

        marks.sort(key=lambda m: m["created_at"], reverse=True)

        self.sub_title = f"{len(marks)} mark(s)"
        self.row_key_to_mark = {}

        for index, mark in enumerate(marks):
            row_key = str(index)
            table.add_row(mark["kind"], mark["book_title"], mark["detail"], mark["created_at"], key=row_key)
            self.row_key_to_mark[row_key] = mark

        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        mark = self.row_key_to_mark.get(str(event.row_key.value))
        if mark is None:
            return

        book_path = Path(mark["book_path"])
        if not book_path.exists():
            self.notify(f"'{mark['book_title']}' was moved or deleted.")
            return

        self.app.open_book(book_path, initial_chapter_index=mark["chapter_index"])

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()    
