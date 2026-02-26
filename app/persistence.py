"""SQLite persistence for submitted order batches."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from app.config import DB_PATH
from app.data import NOTE_CATALOG
from app.models import OrderEntry


@dataclass(frozen=True)
class SavedOrderBatch:
    """Saved batch metadata and copied items."""

    order_id: str
    created_at: str
    order_number: int
    items: list[OrderEntry]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    db_file = Path(DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def bootstrap_schema() -> None:
    """Create persistence schema if it does not already exist."""
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                order_number INTEGER,
                source TEXT NOT NULL DEFAULT 'tui',
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                line_index INTEGER NOT NULL,
                dish_id TEXT NOT NULL,
                dish_name TEXT NOT NULL,
                mode TEXT,
                FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS order_item_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_item_id INTEGER NOT NULL,
                note_id TEXT NOT NULL,
                note_label TEXT NOT NULL,
                FOREIGN KEY(order_item_id) REFERENCES order_items(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_order_items_order_id_line
                ON order_items(order_id, line_index);

            CREATE INDEX IF NOT EXISTS idx_order_item_notes_item_id
                ON order_item_notes(order_item_id);
            """
        )
        order_columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)")}
        if "order_number" not in order_columns:
            conn.execute("ALTER TABLE orders ADD COLUMN order_number INTEGER")


def save_order_batch(items: Iterable[OrderEntry], order_number: int) -> SavedOrderBatch:
    """Persist a full order batch and return saved batch metadata."""
    if not (0 <= order_number <= 1000):
        raise ValueError("order_number must be between 0 and 1000")

    copied_items = [
        OrderEntry(
            dish_id=item.dish_id,
            name=item.name,
            mode=item.mode,
            selected_notes=set(item.selected_notes),
        )
        for item in items
    ]
    if not copied_items:
        raise ValueError("Cannot save empty order batch")

    order_id = uuid4().hex
    created_at = _utc_now_iso()

    with _connect() as conn:
        with conn:
            conn.execute(
                "INSERT INTO orders (id, created_at, order_number, source, status) VALUES (?, ?, ?, 'tui', 'SAVED')",
                (order_id, created_at, order_number),
            )

            for idx, item in enumerate(copied_items):
                cur = conn.execute(
                    """
                    INSERT INTO order_items (order_id, line_index, dish_id, dish_name, mode)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (order_id, idx, item.dish_id, item.name, item.mode),
                )
                order_item_id = int(cur.lastrowid)

                for note_id in NOTE_CATALOG:
                    if note_id not in item.selected_notes:
                        continue
                    conn.execute(
                        """
                        INSERT INTO order_item_notes (order_item_id, note_id, note_label)
                        VALUES (?, ?, ?)
                        """,
                        (order_item_id, note_id, NOTE_CATALOG[note_id]),
                    )

    return SavedOrderBatch(order_id=order_id, created_at=created_at, order_number=order_number, items=copied_items)


def update_order_status(order_id: str, status: str) -> None:
    """Update status for a persisted order batch."""
    with _connect() as conn:
        with conn:
            conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
