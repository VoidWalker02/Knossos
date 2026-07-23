# Knossos

A terminal-based EPUB reader with library management, bookmarks, annotations, and OPDS support, built with Python and [Textual](https://github.com/Textualize/textual).

Knossos aims to be a fast, keyboard-driven way to read and manage an EPUB collection from the terminal, whether your books live in local folders or on a remote OPDS catalog (in my case, a self-hosted [Calibre](https://calibre-ebook.com/download) content server).

## Features

**Reading**

- **EPUB parsing** — metadata (title, author, language, identifier), reading order (spine), and table of contents extraction, via `ebooklib`.
- **Terminal reading view** — chapter content converted to readable text and rendered in a scrollable pane, **bold/italic emphasis are preserved** as real styling.
- **Chapter navigation** — page forward/backward through a book, or jump directly to any entry in the table of contents.
- **Scroll memory** — returning to a previously visited chapter within a session restores your scroll position.
- **Reading progress persistence** — your position is saved to a local SQLite database and restored automatically the next time you open the same book.
- **Search within a book** — full-text search across every chapter of the current book, with contextual snippets and one-key jump-to-match.
- **Adjustable text width** — cap the reading column width for comfortable line lengths regardless of terminal size, adjustable on the fly and persisted.

**Organization**

- **Bookmarks** — save named or auto-labeled bookmarks at any point in a book, browse them in a dedicated panel, and jump to or delete them.
- **Annotations** — highlight a paragraph in the current chapter and attach an optional note to it. View, jump to, or delete saved annotations per book.
- **Library view** — point Knossos at one or more directories, and it recursively scans for `.epub` files, extracting metadata for each. Presented as a sortable (title/author/source), filterable table with a live details panel (author, source folder, last-read progress).
- **Multiple library folders** — configure any number of local directories, Knossos merges and deduplicates books across all of them.

**OPDS (remote catalogs)**

- **Browse a Calibre OPDS server** — navigate folders (by title, author, series, etc.) and explore acquisition feeds seamlessly, with the same sortable table and details panel treatment as your local library (author, format, file size, acquisition date, description where available, not all EPUBs contain summaries).
- **Download and open** — selecting a book downloads it and opens it directly in the reader, using the same progress/bookmark/annotation machinery as local books.
- **Server-side search** — search a Calibre catalog directly via its OPDS search feed, when supported.
- **Multiple OPDS servers** — configure more than one server and cycle between them.

**Customization**

- **Themes** — cycle built-in dark/light themes, or pick from Textual's full built-in theme set (Nord, Dracula, Gruvbox, Catppuccin, and more) via the command palette. Knossos also ships two custom themes tuned for reading: `knossos-sepia` (warm, paper-like) and `knossos-night`! Your choice is remembered across restarts, however you choose to set it.
- **Configurable library/server setup** — default library folders and OPDS servers are stored in a config file, so `knossos` can be run with no arguments.

## Planned

Roughly in priority order:

- **Full-text search across the whole library** — not just the currently open book.
- **"Continue reading" quick-launch** — jump straight back into your most recently opened book from the library screen.
- **Chapter-aware highlight rendering** — annotated passages visually flagged when you scroll past them again, not just accessible via the annotations panel.
- **Footnote support** — detect and render footnotes properly instead of stripping them.
- **Configurable keybindings.**
- **OPDS resilience** — more graceful handling of an unreachable server, and feed caching.
- **Reading stats/dashboard** — time spent reading, books finished, streaks.
- **Export** — bookmarks/annotations to markdown or plain text.


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

Knossos reads a TOML config file (location below) for default settings. Example:

```toml
library_dirs = ["/Users/you/Books", "/Volumes/External/More Books"]
theme = "knossos-sepia"
max_width = 90

[[opds_servers]]
url = "http://192.168.1.50:8080/opds"
name = "Home Calibre"

[[opds_servers]]
url = "http://100.x.x.x:8080/opds"
name = "Remote Calibre (Tailscale)"
```

All fields are optional, Knossos will fall back sensibly if any are missing.

### **Location** (created automatically the first time Knossos runs):

- **Linux**: `~/.config/knossos/config.toml` (respects `XDG_CONFIG_HOME` if set)
- **macOS**: `~/Library/Application Support/knossos/config.toml`

If the file doesn't exist yet, create it by hand at that path, or just run Knossos once (pointing it at a directory as an argument) and edit the file afterward.



### Keybindings

**Library view**

| Key      | Action                                    |
| -------- | ----------------------------------------- |
| `↑`/`↓`  | Move selection                            |
| `Enter`  | Open book                                 |
| `s`      | Cycle sort mode (title / author / source) |
| `/`      | Filter by title or author                 |
| `Escape` | Close filter                              |
| `o`      | Browse OPDS                               |
| `ctrl+t` | Toggle dark/light theme                   |
| `ctrl+p` | Command palette (full theme picker, etc.) |
| `q`      | Quit                                      |

**Reader view**

|Key|Action|
|---|---|
|`↑`/`↓`, `PgUp`/`PgDn`|Scroll within chapter|
|`n` / `p`|Next / previous chapter|
|`t`|Toggle table of contents|
|`/`|Search within this book|
|`+` / `-`|Widen / narrow reading column|
|`b`|Add a bookmark at current position|
|`B`|Toggle bookmarks panel|
|`h`|Highlight a paragraph (annotation)|
|`H`|Toggle annotations panel|
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

## Data storage

Knossos stores its SQLite database and config file in OS-standard locations (via `platformdirs`):

- **Linux**: `~/.local/share/knossos/` (data) and `~/.config/knossos/` (config) — respects `XDG_DATA_HOME`/`XDG_CONFIG_HOME` if set
- **macOS**: `~/Library/Application Support/knossos/` (both data and config)

This includes your library index, reading progress, bookmarks, and annotations. No data is stored alongside your EPUB files.

## Project structure

```
knossos/
├── pyproject.toml
├── README.md
├── books/                      # example/test EPUBs (not part of the package)
├── opds_downloads/             # books downloaded via the OPDS browser
├── src/
│   └── knossos/
│       ├── app.py              # Textual App + Screens (reader), theming
│       ├── config.py           # cross-platform paths, config file load/save
│       ├── db.py                # SQLite schema: books, progress, bookmarks, annotations
│       ├── library.py           # local directory scanning (single + multi-folder)
│       ├── covers.py             # (experimental) cover image extraction/caching
│       ├── themes.py            # custom Textual themes (knossos-sepia, knossos-night)
│       ├── epub/
│       │   ├── book.py          # EPUB loading, metadata, spine, TOC, text/markup conversion
│       │   └── search.py        # in-book full-text search
│       ├── opds/
│       │   ├── client.py        # OPDS HTTP fetch + book download
│       │   └── feed.py          # Atom/OPDS feed parsing (nav vs. acquisition, search template)
│       └── ui/
│           └── screens/
│               ├── library.py    # library table, sort/filter, details panel
│               └── opds.py       # OPDS browser table, details panel, search
└── tests/
```
