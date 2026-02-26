"""Static menu and note data."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.constant import (
    DISH_META_BY_ID as _DISH_META_BY_ID_RAW,
    DISH_NOTE_OVERRIDES,
    MENU_DISH_IDS_BY_MODE,
    MODE_NOTE_DEFAULTS,
    NOTE_CATALOG,
    NOTE_PRINT_PREFIX_TO_SYMBOL_BY_ID,
    NOTE_PRINT_PREFIX_TO_SYMBOL_BY_TEXT,
    NOTE_PRINT_SPICY_SYMBOL_OVERRIDES,
)
from app.models import MenuItem


@dataclass(frozen=True)
class DishMeta:
    """Canonical text metadata for a dish."""

    display_name: str
    aliases: list[str]
    print_label: str | None = None


DISH_META_BY_ID: dict[str, DishMeta] = {
    dish_id: DishMeta(
        display_name=str(meta["display_name"]),
        aliases=list(meta["aliases"]),  # type: ignore[arg-type]
        print_label=str(meta["print_label"]) if meta["print_label"] is not None else None,
    )
    for dish_id, meta in _DISH_META_BY_ID_RAW.items()
}


def display_name_for_dish(dish_id: str) -> str:
    """Get display name for a dish id."""
    meta = DISH_META_BY_ID.get(dish_id)
    if meta is None:
        return dish_id
    return meta.display_name


def print_label_override_for_dish(dish_id: str) -> str | None:
    """Get optional explicit print label for a dish id."""
    meta = DISH_META_BY_ID.get(dish_id)
    if meta is None:
        return None
    return meta.print_label


def print_note_alias_for_id(note_id: str) -> str:
    """Return a compact print alias for a note id."""
    if note_id in NOTE_PRINT_SPICY_SYMBOL_OVERRIDES:
        return NOTE_PRINT_SPICY_SYMBOL_OVERRIDES[note_id]

    qualifier_tokens = {"no", "less", "more", "add"}

    for prefix, symbol in NOTE_PRINT_PREFIX_TO_SYMBOL_BY_ID.items():
        if note_id.startswith(prefix):
            remainder = note_id[len(prefix) :]
            tokens = [token for token in remainder.split("_") if token and token not in qualifier_tokens]
            item_text = " ".join(tokens).strip().lower()
            if not item_text:
                item_text = remainder.replace("_", " ").strip().lower()
            return f"{symbol} {item_text}"

    return NOTE_CATALOG.get(note_id, note_id.replace("_", " ").title())


def print_note_alias_for_text(note_text: str) -> str:
    """Return compact print alias for free-form note text (case-insensitive)."""
    raw = note_text.strip()
    if not raw:
        return ""

    tokens = [token for token in re.split(r"[^a-z0-9]+", raw.lower()) if token]
    if not tokens:
        return raw

    first = tokens[0]
    if first in NOTE_PRINT_PREFIX_TO_SYMBOL_BY_TEXT:
        run_count = 1
        for token in tokens[1:]:
            if token != first:
                break
            run_count += 1

        if first in {"more", "less"}:
            symbol = NOTE_PRINT_PREFIX_TO_SYMBOL_BY_TEXT[first] * max(1, run_count)
        else:
            symbol = NOTE_PRINT_PREFIX_TO_SYMBOL_BY_TEXT[first]

        item_tokens = tokens[run_count:]
        item_text = " ".join(item_tokens).strip()
        if not item_text:
            item_text = " ".join(tokens).strip()
        return f"{symbol} {item_text}"

    return raw.lower()

MENU_BY_MODE: dict[str, list[MenuItem]] = {
    mode: [MenuItem(dish_id, display_name_for_dish(dish_id)) for dish_id in dish_ids]
    for mode, dish_ids in MENU_DISH_IDS_BY_MODE.items()
}

# Compatibility export: derived from canonical dish metadata.
SEARCH_ALIASES_BY_DISH: dict[str, list[str]] = {
    dish_id: list(meta.aliases) for dish_id, meta in DISH_META_BY_ID.items() if meta.aliases
}
