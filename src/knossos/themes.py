# knossos/themes.py

from __future__ import annotations

from textual.theme import Theme

# A warm, paper-like theme for comfortable long-form reading —
# distinct from Textual's IDE-toned built-in dark theme.
SEPIA_THEME = Theme(
    name="knossos-sepia",
    primary="#8b5a2b",
    secondary="#c9a876",
    warning="#b8860b",
    error="#a0392e",
    success="#6b8e4e",
    accent="#a0522d",
    foreground="#3b2f2f",
    background="#f4ecd8",
    surface="#e8ddc4",
    panel="#ddd0b0",
    dark=False,
)

# A gentler dark mode than Textual's default — softer contrast, warmer
# off-black background, intended to be easier on the eyes for long
# reading sessions than a typical high-contrast IDE dark theme.
NIGHT_READ_THEME = Theme(
    name="knossos-night",
    primary="#c9a876",
    secondary="#8b7355",
    warning="#d4a24c",
    error="#c9605a",
    success="#8bab6c",
    accent="#b8926a",
    foreground="#d8cfc0",
    background="#1e1b16",
    surface="#2a251e",
    panel="#352f26",
    dark=True,
)

ALL_THEMES = [SEPIA_THEME, NIGHT_READ_THEME]
