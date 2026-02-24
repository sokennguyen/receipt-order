"""Main Textual app class."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.events import Key
from textual.reactive import reactive
from textual.widgets import Header, Static

from app.data import MENU_BY_MODE, NOTE_CATALOG
from app.models import MenuItem, OrderEntry
from app.notes_modal import NotesModal
from app.persistence import bootstrap_schema, save_order_batch, update_order_status
from app.printer import check_printer_dependencies, print_order_batch
from app.rendering import badge_style, format_note_tags, format_order_label


class ReceiptOrderApp(App):
    """A Textual app for searching and registering restaurant order items."""

    TITLE = "Receipt Order"
    SUB_TITLE = "Gimbap / Ramyun"

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-layout {
        height: 1fr;
    }

    #orders-pane {
        width: 3fr;
        border: round $primary;
        padding: 1;
    }

    #search-pane {
        width: 2fr;
        border: round $secondary;
        padding: 1;
    }

    #search-bar {
        border: heavy $secondary;
        padding: 0 1;
        margin-bottom: 1;
        height: 3;
    }

    #results {
        height: 1fr;
        border: tall $surface;
        padding: 0 1;
    }

    #orders-list {
        height: 1fr;
        border: tall $surface;
        padding: 0 1;
    }

    .pane-title {
        text-style: bold;
        margin-bottom: 1;
    }
    """

    input_state = reactive("normal")
    mode = reactive("G")
    query = reactive("")
    selected_index = reactive(0)
    order_selected_index = reactive(None)

    BINDINGS = [
        ("tab", "cycle_results(1)", "Next result"),
        ("up", "cycle_results(-1)", "Previous result"),
        ("down", "cycle_results(1)", "Next result"),
        ("enter", "register_selected", "Register item"),
        ("backspace", "backspace_query", "Delete query char"),
        Binding("ctrl+s", "submit_and_print", "Submit + Print", priority=True),
        ("ctrl+c", "cancel_active_mode", "Exit active mode"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.registered_orders: list[OrderEntry] = []
        self.system_status = ""
        self._debug_log_path = Path("/tmp/receipt-debug.log")
        self._log_debug("app_init")

    def _log_debug(self, message: str) -> None:
        try:
            ts = datetime.now(timezone.utc).isoformat()
            self._debug_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._debug_log_path.open("a", encoding="utf-8") as fh:
                fh.write(f"{ts} {message}\n")
        except Exception:
            # Logging must never interfere with app flow.
            return

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-layout"):
            with Vertical(id="orders-pane"):
                yield Static("Registered Orders", classes="pane-title")
                yield Static("(no items yet)", id="orders-list")
            with Vertical(id="search-pane"):
                yield Static(id="search-bar")
                yield Static(id="results")

    def on_mount(self) -> None:
        bootstrap_schema()
        _, msg = check_printer_dependencies()
        self.system_status = msg
        self._log_debug(f"on_mount printer_status={msg!r}")
        self._refresh_all()

    def on_key(self, event: Key) -> None:
        if isinstance(self.screen, NotesModal):
            return

        self._log_debug(
            f"on_key key={event.key!r} char={event.character!r} printable={event.is_printable} state={self.input_state!r}"
        )

        if event.key == "ctrl+s":
            self._log_debug("on_key detected ctrl+s -> action_submit_and_print")
            self.action_submit_and_print()
            event.stop()
            return

        if not event.is_printable or len(event.character) != 1 or not event.character.isalnum():
            return

        key = event.character.lower()
        if self.input_state == "normal":
            if key == "t":
                self.registered_orders.append(OrderEntry(dish_id="tteokbokki", name="Tteokbokki"))
                self.order_selected_index = len(self.registered_orders) - 1
                self._refresh_orders()
                event.stop()
                return

            if key == "d":
                self._delete_selected_order()
                event.stop()
                return

            if key == "j":
                self._move_order_selection(1)
                event.stop()
                return

            if key == "k":
                self._move_order_selection(-1)
                event.stop()
                return

            if key == "n":
                self._open_notes_for_selected_order()
                event.stop()
                return

            if key not in {"g", "r"}:
                return

            self.mode = key.upper()
            self.input_state = "active"
            self.query = ""
            self.selected_index = 0
            self._refresh_search()
            event.stop()
            return

        self.query += event.character
        self.selected_index = 0
        self._refresh_search()
        event.stop()

    def action_cancel_active_mode(self) -> None:
        if isinstance(self.screen, NotesModal):
            return
        if self.input_state == "normal":
            return

        self.input_state = "normal"
        self.query = ""
        self.selected_index = 0
        self._refresh_search()

    def action_cycle_results(self, delta: int) -> None:
        if isinstance(self.screen, NotesModal):
            return
        if self.input_state != "active":
            return

        results = self._filtered_results()
        if not results:
            self.selected_index = 0
            self._refresh_results(results)
            return
        self.selected_index = (self.selected_index + delta) % len(results)
        self._refresh_results(results)

    def action_register_selected(self) -> None:
        if isinstance(self.screen, NotesModal):
            return
        if self.input_state != "active":
            return

        results = self._filtered_results()
        if not results:
            return

        item = results[self.selected_index]
        self.registered_orders.append(OrderEntry(dish_id=item.dish_id, name=item.name, mode=self.mode))
        self.order_selected_index = len(self.registered_orders) - 1
        self._refresh_orders()

    def action_backspace_query(self) -> None:
        if isinstance(self.screen, NotesModal):
            return
        if self.input_state != "active":
            return

        if not self.query:
            return
        self.query = self.query[:-1]
        self.selected_index = 0
        self._refresh_search()

    def action_submit_and_print(self) -> None:
        self._log_debug(
            f"submit_enter state={self.input_state!r} rows={len(self.registered_orders)} screen={type(self.screen).__name__}"
        )
        if isinstance(self.screen, NotesModal):
            self._log_debug("submit_blocked reason=notes_modal")
            return
        if self.input_state != "normal":
            self.system_status = "Submit only in NORMAL mode (Ctrl+C to exit active)"
            self._refresh_search()
            self._log_debug("submit_blocked reason=not_normal")
            return
        if not self.registered_orders:
            self.system_status = "Nothing to submit"
            self._refresh_search()
            self._log_debug("submit_blocked reason=no_rows")
            return

        batch = save_order_batch(self.registered_orders)
        self._log_debug(f"submit_saved order_id={batch.order_id} rows={len(batch.items)}")
        try:
            print_order_batch(batch.items)
        except Exception as exc:
            update_order_status(batch.order_id, "PRINT_FAILED")
            self.system_status = f"Saved {batch.order_id[:8]} but print failed: {exc}"
            self._refresh_search()
            self._log_debug(f"submit_print_failed order_id={batch.order_id} error={exc!r}")
            return

        update_order_status(batch.order_id, "PRINTED")
        self.registered_orders.clear()
        self.order_selected_index = None
        self.system_status = f"Saved + printed: {batch.order_id[:8]}"
        self._refresh_orders()
        self._refresh_search()
        self._log_debug(f"submit_printed order_id={batch.order_id}")

    def _filtered_results(self) -> list[MenuItem]:
        source = MENU_BY_MODE[self.mode]
        if not self.query:
            return source
        q = self.query.lower()
        return [item for item in source if q in item.name.lower()]

    def _refresh_all(self) -> None:
        self._refresh_orders()
        self._refresh_search()

    def _move_order_selection(self, delta: int) -> None:
        if not self.registered_orders:
            return

        if self.order_selected_index is None:
            self.order_selected_index = 0 if delta > 0 else len(self.registered_orders) - 1
        else:
            self.order_selected_index = (self.order_selected_index + delta) % len(self.registered_orders)
        self._refresh_orders()

    def _delete_selected_order(self) -> None:
        if not self.registered_orders or self.order_selected_index is None:
            return

        idx = self.order_selected_index
        if not (0 <= idx < len(self.registered_orders)):
            self.order_selected_index = None
            self._refresh_orders()
            return

        del self.registered_orders[idx]

        if not self.registered_orders:
            self.order_selected_index = None
        else:
            self.order_selected_index = min(idx, len(self.registered_orders) - 1)

        self._refresh_orders()

    def _selected_order(self) -> OrderEntry | None:
        if self.order_selected_index is None:
            return None
        if not (0 <= self.order_selected_index < len(self.registered_orders)):
            return None
        return self.registered_orders[self.order_selected_index]

    def _open_notes_for_selected_order(self) -> None:
        entry = self._selected_order()
        if entry is None:
            return
        self.push_screen(NotesModal(entry, on_change=self._refresh_orders))

    def _visible_rows(self, widget: Static) -> int:
        height = widget.size.height
        if height <= 0:
            return 8
        return max(1, height)

    def _window_bounds(self, total: int, rows: int, selected: int | None) -> tuple[int, int]:
        if total <= 0:
            return (0, 0)

        rows = max(1, rows)
        if total <= rows:
            return (0, total)

        if selected is None:
            start = 0
        else:
            half = rows // 2
            start = selected - half
            start = max(0, start)
            start = min(start, total - rows)

        return (start, start + rows)

    def _refresh_orders(self) -> None:
        try:
            orders_widget = self.query_one("#orders-list", Static)
        except NoMatches:
            return
        if not self.registered_orders:
            self.order_selected_index = None
            orders_widget.update("(no items yet)")
            return

        if self.order_selected_index is not None and self.order_selected_index >= len(self.registered_orders):
            self.order_selected_index = len(self.registered_orders) - 1

        visible_rows = self._visible_rows(orders_widget)
        start, end = self._window_bounds(len(self.registered_orders), visible_rows, self.order_selected_index)

        lines = Text()
        if start > 0:
            lines.append("⋮\n", style="dim")

        for idx in range(start, end):
            if idx > start:
                lines.append("\n")

            pointer = "➤ " if idx == self.order_selected_index else "  "
            lines.append(pointer)
            lines.append(f"{idx + 1}. ")
            lines.append_text(format_order_label(self.registered_orders[idx]))

            selected_note_ids = [note_id for note_id in NOTE_CATALOG if note_id in self.registered_orders[idx].selected_notes]
            if selected_note_ids:
                lines.append("\n      ")
                lines.append_text(format_note_tags(selected_note_ids))

        if end < len(self.registered_orders):
            lines.append("\n⋮", style="dim")

        orders_widget.update(lines)

    def _refresh_search(self) -> None:
        self._refresh_search_bar()
        if self.input_state == "normal":
            self._refresh_results([])
            return
        self._refresh_results(self._filtered_results())

    def _refresh_search_bar(self) -> None:
        bar = self.query_one("#search-bar", Static)
        if self.input_state == "normal":
            status = self.system_status or "Ready"
            bar.update(f"Press R or G to search. Ctrl+S submit/print.\\n{status}")
            return

        shown_query = self.query or ""
        text = Text()
        text.append(self.mode, style=badge_style(self.mode))
        text.append(f": {shown_query}")
        bar.update(text)

    def _refresh_results(self, results: list[MenuItem]) -> None:
        results_widget = self.query_one("#results", Static)
        if self.input_state == "normal":
            results_widget.update("")
            return

        if not results:
            results_widget.update("No results")
            return

        if self.selected_index >= len(results):
            self.selected_index = 0

        visible_rows = self._visible_rows(results_widget)
        start, end = self._window_bounds(len(results), visible_rows, self.selected_index)

        lines = Text()
        if start > 0:
            lines.append("⋮\n", style="dim")

        for idx in range(start, end):
            if idx > start:
                lines.append("\n")
            pointer = "➤ " if idx == self.selected_index else "  "
            lines.append(f"{pointer}{results[idx].name}")

        if end < len(results):
            lines.append("\n⋮", style="dim")

        results_widget.update(lines)
