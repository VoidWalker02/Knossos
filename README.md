#Knossos

A terminal-based EPUB reader with library management, precise annotations, bookmarks, dictionary lookup, and OPDS support, built with Python and [Textual](https://github.com/Textualize/textual).

Knossos aims to be a fast, keyboard-driven way to read and manage an EPUB collection from the terminal, whether your books live in local folders or on a remote OPDS catalog (in my case, a self-hosted [Calibre](https://calibre-ebook.com/download) content server).

## Features

**Reading**

- EPUB parsing (metadata, spine/reading order, table of contents) via `ebooklib`, keyed by each book's stable `dc:identifier` where available, so a book keeps its history even if the file is moved, renamed, or reached via a different path.
- Terminal reading view with bold/italic emphasis preserved as real styling.
- Chapter navigation and jump-to-chapter via the table of contents.
- Adjustable reading column width and paragraph spacing, both live-adjustable and persisted.
- Full-text search within the current book, with contextual snippets and one-key jump-to-match.
- In-app dictionary lookup, look up any word via a free online dictionary API without leaving the reader.
- Per-chapter scroll memory, plus persistent reading progress saved across restarts and automatically restored.

**Annotations & bookmarks**

- **Precise, cursor-based highlighting** — select any exact passage with your terminal's native click-and-drag text selection, press a key, and it becomes an annotation. 
- Highlighted passages are visually flagged whenever you scroll past them again.
- Add, edit, or delete a note on any annotation.
- Jump to an annotation and land close to its actual position.
- Bookmarks: save, browse, jump to, and delete named or auto-labeled bookmarks per book.
- **"Your marks"**, a single view combining every bookmark and annotation across your entire library, sorted by recency, with one-key jump to any of them.

**Library**

- Point Knossos at one or more directories, it recursively scans for `.epub` files and presents them in a sortable (title/author/source), filterable table with a live details panel.
- Sorting by source visually groups books under a header per folder.
- **Duplicate detection** — the same book appearing in more than one configured folder (matched by its stable EPUB identifier) is collapsed into a single row, with the other copies' locations noted in the details panel.
- **Continue reading** — jump straight back into your most recently opened book with one key.
- **Full-text search across your entire library**, not just the currently open book.

**OPDS (remote catalogs)**

- Browse a Calibre OPDS server: navigate folders and drill into acquisition feeds, with the same table and details panel treatment as the local library (author, format, file size, publish date, description where available).
- Download and open a book directly from a remote catalog, downloaded books flow through the same progress/bookmark/annotation system as local files.
- Server-side search against a Calibre catalog's OPDS search feed.
- Multiple configured OPDS servers, switchable at runtime.
- **Resilient to a flaky or offline server** — feeds are cached to disk, a temporarily unreachable server falls back to the last successfully cached copy rather than failing outright.

**Customization**

- Cycle built-in dark/light themes, or choose from Textual's full built-in theme set (Nord, Dracula, Gruvbox, Catppuccin, and more) via the command palette (`ctrl+p`).
- Two custom themes built for reading comfort: `knossos-sepia` (warm, paper-like) and `knossos-night`!.
- Theme choice persists across restarts regardless of how it was set.
- Config file (`config.toml`) for default library folders, OPDS servers, theme, reading width, and paragraph spacing, lets Knossos launch with zero arguments.
- **Configurable keybindings** — Change the keybindings for each action in the config file to your preference. 

## Planned

- **Footnote support** — detect footnote references and their targets, jump to a footnote and back to where you were reading.
- **Cloud progress sync** — a small self-hosted sync service, keyed by each book's identifier, syncing on open/close. 
- **Reading stats/dashboard** — Get reading statistics, finished books, streaks, etc.
- **Export** — bookmarks/annotations to markdown or plain text.
- **Packaging** — PyPI and Homebrew distribution.

## Requirements

- Python 3.10+
- macOS or Linux

## Installation

From the project root:

```bash
pip install -e .
```

This installs Knossos in editable mode along with its dependencies (`textual`, `ebooklib`, `lxml`, `html2text`, `httpx`, `platformdirs`, `toml`).

## Usage

Launch Knossos:

```bash
knossos
```

If you have `library_dirs` set in your config file (see below), Knossos opens straight into your library. Otherwise, pass a directory explicitly:

```bash
knossos /path/to/your/books
```

### Configuration

Knossos reads a `config.toml` file for default settings, library folders, OPDS servers, theme, reading width, and paragraph spacing, so it can be launched with no arguments.

**Location** (created automatically the first time Knossos runs):

- **Linux**: `~/.config/knossos/config.toml` (respects `XDG_CONFIG_HOME` if set)
- **macOS**: `~/Library/Application Support/knossos/config.toml`

Example, based on a real working setup:

```toml
library_dirs = [
    "/Users/moraisi/Downloads",
    "/Users/moraisi/Documents/Books",
]
theme = "dracula"
max_width = 135
paragraph_spacing = 1

[[opds_servers]]
url = "http://100.122.21.102:8080/opds"
```

Notes:

- `library_dirs` is a list, add as many local folders as you like, Knossos merges and deduplicates books across all of them.
- `theme` accepts any theme name Knossos knows about, built-in Textual themes (`nord`, `dracula`, `gruvbox`, `catppuccin-mocha`, etc.), Knossos's own (`knossos-sepia`, `knossos-night`), or whatever you last picked via the command palette (`ctrl+p`), which is saved here automatically.
- `max_width` is the reading column width in terminal columns, `paragraph_spacing` controls blank lines between paragraphs, both adjustable live in the reader (`+`/`-` and `[`/`]` respectively), which updates this file automatically.
- `[[opds_servers]]` is a repeatable table, add one block per server. `name` is optional (shown in place of the URL when switching servers with `s`), omit it and the raw URL is used instead.
- All fields are optional, Knossos falls back sensibly if any are missing, and a missing config file entirely is treated the same as an empty one.

### Keybindings

**Library view**

|Key|Action|
|---|---|
|`↑`/`↓`|Move selection|
|`Enter`|Open book|
|`s`|Cycle sort mode (title / author / source)|
|`/`|Filter by title or author|
|`Escape`|Close filter|
|`o`|Browse OPDS|
|`f`|Search across your whole library|
|`c`|Continue reading (jump to most recent book)|
|`m`|View all bookmarks and annotations ("your marks")|
|`ctrl+t`|Toggle dark/light theme|
|`ctrl+p`|Command palette (full theme picker, etc.)|
|`q`|Quit|

**Reader view**

|Key|Action|
|---|---|
|`↑`/`↓`, `PgUp`/`PgDn`|Scroll within chapter|
|`n` / `p`|Next / previous chapter|
|`t`|Toggle table of contents|
|`/`|Search within this book|
|`+` / `-`|Widen / narrow reading column|
|`[` / `]`|Decrease / increase paragraph spacing|
|`z`|Look up a word (dictionary)|
|Click + drag|Select a passage of text (native Textual selection)|
|`h`|Turn the current selection into an annotation|
|`H`|Toggle annotations panel|
|`r`|Edit the highlighted annotation's note|
|`b`|Add a bookmark at current position|
|`B`|Toggle bookmarks panel|
|`d`|Delete highlighted bookmark/annotation (while that panel is open)|
|`Escape`|Close any open panel, or return to the library|
|`q`|Quit (progress is saved automatically)|

**OPDS browser**

|Key|Action|
|---|---|
|`↑`/`↓`|Move selection|
|`Enter`|Open a folder, or download + open a book|
|`/`|Search this server (if supported)|
|`s`|Switch to next configured server|
|`Escape`|Go back a folder, or return to the library|
|`q`|Quit|

**Your marks view**

|Key|Action|
|---|---|
|`↑`/`↓`|Move selection|
|`Enter`|Jump to that bookmark/annotation|
|`Escape`|Back to library|

## Data storage

Knossos stores its SQLite database in an OS-standard data directory (via `platformdirs`), see Configuration above for the config file's location specifically:

- **Linux**: `~/.local/share/knossos/knossos.db` , respects `XDG_DATA_HOME` if set
- **macOS**: `~/Library/Application Support/knossos/knossos.db`

This includes your library index, reading progress, bookmarks, and annotations, keyed primarily by each book's EPUB identifier (falling back to file path for books that lack one). No data is stored alongside your EPUB files. Cached OPDS feeds live separately under the platform's cache directory.

## Project structure

```
knossos/
├── pyproject.toml
├── README.md
├── books/                       # example/test EPUBs (not part of the package)
├── opds_downloads/              # books downloaded via the OPDS browser
├── src/
│   └── knossos/
│       ├── app.py               # Textual App + ReaderScreen, theming, keymap application
│       ├── config.py            # cross-platform paths, config file load/save
│       ├── db.py                 # SQLite schema: books (by identifier), progress,
│       │                        # bookmarks, annotations, migrations
│       ├── library.py            # local directory scanning, multi-folder merge,
│       │                        # identifier-based duplicate collapsing
│       ├── library_search.py     # full-text search across the whole library
│       ├── dictionary.py         # online dictionary lookup client
│       ├── covers.py             # (experimental, unused) cover image extraction
│       ├── themes.py             # custom Textual themes (knossos-sepia, knossos-night)
│       ├── epub/
│       │   ├── book.py           # EPUB loading, metadata, spine, TOC, text/markup
│       │   │                    # conversion, paragraph spacing, highlight rendering
│       │   └── search.py         # in-book full-text search
│       ├── opds/
│       │   ├── client.py         # OPDS HTTP fetch (with error handling) + download
│       │   ├── feed.py           # Atom/OPDS feed parsing (nav vs. acquisition, search)
│       │   └── cache.py          # on-disk feed caching with TTL + stale fallback
│       └── ui/
│           └── screens/
│               ├── library.py         # library table, sort/filter, details panel
│               ├── library_search.py  # library-wide search screen
│               ├── marks.py           # combined bookmarks + annotations view
│               └── opds.py            # OPDS browser table, details panel, search
└── tests/
`````
