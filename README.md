# Knossos

A terminal-based EPUB reader with library management, bookmarks, and reading progress, built with Python and [Textual](https://github.com/Textualize/textual).

Knossos aims to be a fast, keyboard-driven way to read and manage a local EPUB collection from the terminal, with planned support for browsing remote libraries via OPDS (in my case, a self-hosted [Calibre](https://calibre-ebook.com/download) instance)

## Features

- **EPUB parsing** — metadata (title, author, language, identifier), reading order (spine), and table of contents extraction, via `ebooklib`.
- **Terminal reading view** — chapter content converted to readable plain text and rendered in a scrollable pane.
- **Chapter navigation** — page forward/backward through a book, or jump directly to any entry in the table of contents.
- **Scroll memory** — returning to a previously visited chapter within a session restores your scroll position.
- **Reading progress persistence** — your position  is saved to a local SQLite database and restored automatically the next time you open the same book.
- **Bookmarks** — bookmarks at any point in a book, browse them in a dedicated panel, and jump to or delete them.
- **Library view** — point Knossos at a directory, and it recursively scans for `.epub` files, extracts metadata for each, and presents them in a browsable list.

## Planned

- **OPDS client** — browse and open books from a remote OPDS catalog (e.g. a Calibre server), not just local files.
- **Customization** — Knossos is pretty bare-bones as is, I intend to work with and implement theming and other forms of customization to the reader.

## Requirements

- Python 3.10+
- macOS or Linux

## Installation

From the project root:

```bash
pip install -e .
```

This installs Knossos in editable mode along with its dependencies (`textual`, `ebooklib`, `lxml`, `html2text`, `platformdirs`).

## Usage

Launch Knossos pointed at a directory containing your EPUB files:

```bash
python -m knossos.app /path/to/your/books
```

Knossos will scan the directory and open the **library view**. Select a book to start reading.

### Keybindings

**Library view**

|Key|Action|
|---|---|
|`↑`/`↓`|Move selection|
|`Enter`|Open book|
|`q`|Quit|

**Reader view**

|Key|Action|
|---|---|
|`↑`/`↓`, `PgUp`/`PgDn`|Scroll within chapter|
|`n`|Next chapter|
|`p`|Previous chapter|
|`t`|Toggle table of contents|
|`b`|Add a bookmark at current position|
|`B`|Toggle bookmarks panel|
|`d`|Delete highlighted bookmark (while bookmarks panel is open)|
|`Escape`|Return to library|
|`q`|Quit (progress is saved automatically)|

## Data storage

Knossos stores its SQLite database and configuration in OS-standard locations (via `platformdirs`):

- **Linux**: `~/.local/share/knossos/` (respects `XDG_DATA_HOME` if set)
- **macOS**: `~/Library/Application Support/knossos/`

This includes your library index, reading progress, and bookmarks. No data is stored alongside your EPUB files.

## Project structure

```
knossos/
├── pyproject.toml
├── README.md
├── src/
│   └── knossos/
│       ├── app.py            # Textual App and Screens 
│       ├── config.py         # Cross-platform config/data directory handling
│       ├── db.py             # SQLite schema, progress, and bookmarks
│       ├── library.py        # Directory scanning for local EPUBs
│       ├── epub/
│       │   └── book.py       # EPUB loading, metadata, spine, TOC, text conversion
│       ├── opds/              # (planned) OPDS client
│       └── ui/
│           └── screens/
│               └── library.py # Library browsing screen
└── tests/
```
