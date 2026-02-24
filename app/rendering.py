"""Rendering and note-resolution helpers."""

from __future__ import annotations

from rich.text import Text

from app.data import DISH_NOTE_OVERRIDES, MODE_NOTE_DEFAULTS, NOTE_CATALOG
from app.models import OrderEntry


def badge_style(mode: str) -> str:
    """Return a consistent badge style for category tags."""
    if mode == "R":
        return "bold #ffffff on #b23a48"
    if mode == "S":
        return "bold #ffffff on #2f6db5"
    return "bold #0b1f0f on #5fbf72"


def format_order_label(entry: OrderEntry) -> Text:
    """Render an order label with an optional colored mode tag."""
    text = Text()
    if entry.mode in {"R", "G", "S"}:
        text.append(entry.mode, style=badge_style(entry.mode))
        text.append(f" {entry.name}")
    else:
        text.append(entry.name)
    return text


def available_notes_for_order(entry: OrderEntry) -> list[str]:
    """Resolve which note IDs are available for the given dish."""
    note_ids = list(MODE_NOTE_DEFAULTS.get(entry.mode or "", []))
    overrides = DISH_NOTE_OVERRIDES.get(entry.dish_id, {})
    for note_id in overrides.get("remove", []):
        if note_id in note_ids:
            note_ids.remove(note_id)
    for note_id in overrides.get("add", []):
        if note_id not in note_ids:
            note_ids.append(note_id)
    return [note_id for note_id in note_ids if note_id in NOTE_CATALOG]


def format_note_tags(note_ids: list[str]) -> Text:
    """Render selected notes as compact tags."""
    text = Text()
    for idx, note_id in enumerate(note_ids):
        if idx > 0:
            text.append(" ")
        text.append(f"[{NOTE_CATALOG[note_id]}]", style="white")
    return text
