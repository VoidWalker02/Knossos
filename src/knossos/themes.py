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


# A cool, misty theme — think overcast library reading room, blues and
# slate grays rather than pure black/white.
FOGGLASS_THEME = Theme(
    name="knossos-fogglass",
    primary="#6b8caf",
    secondary="#8fa8bd",
    warning="#c9a04e",
    error="#b8615c",
    success="#7a9e7e",
    accent="#5b7f9e",
    foreground="#dbe4ea",
    background="#1c2228",
    surface="#242b33",
    panel="#2d353e",
    dark=True,
)

# A warm, aged-parchment light theme — leans yellower/browner than the
# existing knossos-sepia, closer to a genuinely old paperback page.
PARCHMENT_THEME = Theme(
    name="knossos-parchment",
    primary="#8a6d3b",
    secondary="#a68a5b",
    warning="#b8860b",
    error="#9c4a3c",
    success="#6f7d4a",
    accent="#7a5c2e",
    foreground="#3a2f1e",
    background="#ede0c0",
    surface="#e2d3ab",
    panel="#d6c495",
    dark=False,
)

# A moodier, high-contrast dark theme with a single deep accent color —
# for late-night reading sessions where you want something with more
# personality than a neutral dark mode.
INKWELL_THEME = Theme(
    name="knossos-inkwell",
    primary="#8c6fb5",
    secondary="#6f5a8a",
    warning="#d4a24c",
    error="#c9605a",
    success="#7fa87f",
    accent="#a888c9",
    foreground="#e6e1ec",
    background="#141018",
    surface="#1e1826",
    panel="#281f33",
    dark=True,
)


ALL_THEMES = [SEPIA_THEME, NIGHT_READ_THEME, FOGGLASS_THEME, PARCHMENT_THEME, INKWELL_THEME]
