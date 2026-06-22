"""Monochrome icon set and state palette for the TUI.

Deliberately no emoji — these are text-weight glyphs that render as a single
monochrome cell in a terminal, so the look stays consistent with the rest of
the UI and respects the user's no-emoji preference. Keep every glyph here so
the look can be retuned in one place.
"""
from __future__ import annotations

# Phase / step state markers.
ICON_DONE = "●"      # completed
ICON_ACTIVE = "◐"    # in progress (the furthest-along phase with content)
ICON_PENDING = "○"   # not started
ICON_SUB_DONE = "●"
ICON_SUB_ACTIVE = "◐"
ICON_SUB_PENDING = "○"

# Verdicts / booleans.
ICON_OK = "✓"
ICON_FAIL = "✗"
ICON_NEUTRAL = "•"
ICON_WARN = "▲"

# Structure / navigation.
ICON_ARROW = "→"
ICON_BRANCH = "⎇"
ICON_VBAR = "│"
ICON_BULLET = "▪"

# Bar-chart fill (eighths give sub-cell resolution).
BAR_FULL = "█"
BAR_PARTIALS = ("", "▏", "▎", "▍", "▌", "▋", "▊", "▉")
BAR_EMPTY = "·"

# State -> Rich style.
STYLE_DONE = "green"
STYLE_ACTIVE = "bold yellow"
STYLE_PENDING = "grey46"
STYLE_DIM = "grey46"
STYLE_ACCENT = "cyan"
STYLE_REVIEW = "magenta"
STYLE_OK = "green"
STYLE_FAIL = "red"
STYLE_WARN = "yellow"


def state_icon(state: str) -> str:
    return {
        "done": ICON_DONE,
        "active": ICON_ACTIVE,
        "pending": ICON_PENDING,
    }.get(state, ICON_PENDING)


def state_style(state: str) -> str:
    return {
        "done": STYLE_DONE,
        "active": STYLE_ACTIVE,
        "pending": STYLE_PENDING,
    }.get(state, STYLE_PENDING)
