"""Domain models for receipt-order."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MenuItem:
    """A searchable menu item."""

    dish_id: str
    name: str


@dataclass
class OrderEntry:
    """A registered order row with optional selected notes."""

    dish_id: str
    name: str
    mode: str | None = None
    selected_notes: set[str] = field(default_factory=set)
