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

from app.data import MENU_BY_MODE, NOTE_CATALOG, SEARCH_ALIASES_BY_DISH, display_name_for_dish
from app.models import MenuItem, OrderEntry, RegisterGroup, RegisterRow
from app.notes_modal import NotesModal
from app.order_number_modal import OrderNumberModal
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

    #mode-footer {
        height: 1;
        padding: 0 1;
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
    ui_mode = reactive("NORMAL")
    view_mode_active = reactive(False)
    view_anchor_index = reactive(None)
    view_cursor_index = reactive(None)
    view_selection_kind = reactive("CHAR")
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
        self.registered_orders: list[RegisterRow] = []
        self.system_status = ""
        self.view_pending_g = False
        self.next_group_id = 1
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
        yield Static(id="mode-footer")

    def on_mount(self) -> None:
        bootstrap_schema()
        _, msg = check_printer_dependencies()
        self.system_status = msg
        self._log_debug(f"on_mount printer_status={msg!r}")
        self._sync_ui_mode()
        self._refresh_all()

    def on_key(self, event: Key) -> None:
        if isinstance(self.screen, (NotesModal, OrderNumberModal)):
            self._sync_ui_mode()
            return

        self._log_debug(
            f"on_key key={event.key!r} char={event.character!r} printable={event.is_printable} state={self.input_state!r}"
        )

        if self.view_mode_active:
            if event.key in {"escape", "q", "ctrl+c"}:
                self._exit_view_mode()
                event.stop()
                return
            if event.is_printable and event.character and len(event.character) == 1:
                if event.character == "C":
                    self._clear_view_pending_g()
                    self._ungroup_selected_group()
                    event.stop()
                    return
                if event.character == "G":
                    self._clear_view_pending_g()
                    self._jump_view_cursor_to_bottom()
                    self._log_debug("view_mode_jump_bottom_G")
                    event.stop()
                    return

                key = event.character.lower()
                if key == "c":
                    self._clear_view_pending_g()
                    self._group_selected_rows()
                    event.stop()
                    return
                if key == "g":
                    if self.view_pending_g:
                        self._clear_view_pending_g()
                        self._jump_view_cursor_to_top()
                        self._log_debug("view_mode_jump_top_gg")
                    else:
                        self.view_pending_g = True
                        self._log_debug("view_mode_g_pending")
                    event.stop()
                    return
                if key == "j":
                    self._clear_view_pending_g()
                    self._move_view_cursor(1)
                    event.stop()
                    return
                if key == "k":
                    self._clear_view_pending_g()
                    self._move_view_cursor(-1)
                    event.stop()
                    return
            self._clear_view_pending_g()
            event.stop()
            return

        if event.key == "ctrl+s":
            self._log_debug("on_key detected ctrl+s -> action_submit_and_print")
            self.action_submit_and_print()
            event.stop()
            return

        if not event.is_printable or len(event.character) != 1 or not event.character.isalnum():
            return

        key = event.character.lower()
        if self.input_state == "normal":
            if key == "v":
                if event.character == "V":
                    self.view_selection_kind = "LINE"
                    self.system_status = "Shift+V not implemented yet"
                    self._refresh_search()
                    self._log_debug("view_mode_shift_v_stub")
                    event.stop()
                    return
                self._enter_view_mode()
                event.stop()
                return

            if key == "c":
                if event.character == "C":
                    self._ungroup_selected_group()
                else:
                    self._group_selected_rows()
                event.stop()
                return

            if key == "t":
                self.registered_orders.append(OrderEntry(dish_id="tteokbokki", name=display_name_for_dish("tteokbokki")))
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

            if key not in {"g", "r", "s"}:
                return

            self.mode = key.upper()
            self.input_state = "active"
            self._sync_ui_mode()
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
        self._sync_ui_mode()
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

        self.ui_mode = "MODAL"
        self.push_screen(OrderNumberModal(), self._on_order_number_selected)

    def _on_order_number_selected(self, order_number: int | None) -> None:
        self._sync_ui_mode()
        if order_number is None:
            self.system_status = "Submit canceled"
            self._refresh_search()
            self._log_debug("submit_canceled reason=no_order_number")
            return
        self._log_debug(f"submit_order_number_selected order_number={order_number}")
        self._submit_with_order_number(order_number)

    def _submit_with_order_number(self, order_number: int) -> None:
        flat_items = self._flatten_register_rows_for_submit()
        batch = save_order_batch(flat_items, order_number)
        self._log_debug(
            f"submit_saved order_id={batch.order_id} order_number={batch.order_number} rows={len(flat_items)}"
        )
        try:
            print_order_batch(flat_items, batch.order_number)
        except Exception as exc:
            update_order_status(batch.order_id, "PRINT_FAILED")
            self.system_status = f"Saved {batch.order_id[:8]} but print failed: {exc}"
            self._refresh_search()
            self._log_debug(f"submit_print_failed order_id={batch.order_id} error={exc!r}")
            return

        update_order_status(batch.order_id, "PRINTED")
        self.registered_orders.clear()
        self.order_selected_index = None
        self.next_group_id = 1
        self.system_status = f"Saved + printed: {batch.order_id[:8]}"
        self._refresh_orders()
        self._refresh_search()
        self._log_debug(f"submit_printed order_id={batch.order_id}")

    def _filtered_results(self) -> list[MenuItem]:
        source = MENU_BY_MODE[self.mode]
        if not self.query:
            return source
        q = self._normalize_search_text(self.query)
        if not q:
            return source

        matched: list[MenuItem] = []
        for item in source:
            normalized_name = self._normalize_search_text(item.name)
            normalized_dish_id = self._normalize_search_text(item.dish_id)
            if q in normalized_name or q in normalized_dish_id:
                matched.append(item)
                continue

            aliases = SEARCH_ALIASES_BY_DISH.get(item.dish_id, [])
            if any(q in self._normalize_search_text(alias) for alias in aliases):
                matched.append(item)

        return matched

    def _normalize_search_text(self, text: str) -> str:
        return "".join(ch for ch in text.lower() if ch.isalnum())

    def _refresh_all(self) -> None:
        self._refresh_orders()
        self._refresh_search()
        self._refresh_footer()

    def watch_ui_mode(self, _new_mode: str) -> None:
        self._refresh_footer()

    def watch_mode(self, _new_mode: str) -> None:
        if self.ui_mode == "SEARCH":
            self._refresh_footer()

    def _search_mode_label(self) -> str:
        labels = {
            "R": "Ramyun",
            "G": "Gimbap",
            "S": "Sides",
        }
        return labels.get(self.mode, self.mode)

    def _move_order_selection(self, delta: int) -> None:
        if not self.registered_orders:
            return

        if self.order_selected_index is None:
            self.order_selected_index = 0 if delta > 0 else len(self.registered_orders) - 1
        else:
            self.order_selected_index = (self.order_selected_index + delta) % len(self.registered_orders)
        self._refresh_orders()

    def _is_group_row(self, row: RegisterRow) -> bool:
        return isinstance(row, RegisterGroup)

    def _selected_row(self) -> RegisterRow | None:
        if self.order_selected_index is None:
            return None
        if not (0 <= self.order_selected_index < len(self.registered_orders)):
            return None
        return self.registered_orders[self.order_selected_index]

    def _view_selected_row_bounds(self) -> tuple[int, int] | None:
        if self.view_mode_active:
            return self._view_range_bounds()
        if self.order_selected_index is None:
            return None
        if not (0 <= self.order_selected_index < len(self.registered_orders)):
            return None
        return (self.order_selected_index, self.order_selected_index)

    def _selection_contains_group(self, start: int, end: int) -> bool:
        return any(self._is_group_row(row) for row in self.registered_orders[start : end + 1])

    def _allocate_group_id(self) -> int:
        group_id = self.next_group_id
        self.next_group_id += 1
        return group_id

    def _recompute_next_group_id(self) -> None:
        max_group_id = 0
        for row in self.registered_orders:
            if isinstance(row, RegisterGroup):
                max_group_id = max(max_group_id, row.group_id)
        self.next_group_id = max_group_id + 1

    def _close_group_id_gap(self, removed_group_id: int) -> None:
        for row in self.registered_orders:
            if isinstance(row, RegisterGroup) and row.group_id > removed_group_id:
                row.group_id = max(1, row.group_id - 1)
        self._recompute_next_group_id()

    def _group_selected_rows(self) -> None:
        if not self.registered_orders:
            return
        bounds = self._view_selected_row_bounds()
        if bounds is None:
            return
        start, end = bounds
        if self._selection_contains_group(start, end):
            self._log_debug("group_create_noop reason=selection_contains_group")
            return

        members: list[OrderEntry] = []
        for row in self.registered_orders[start : end + 1]:
            if isinstance(row, OrderEntry):
                members.append(row)
        if not members:
            return

        group = RegisterGroup(group_id=self._allocate_group_id(), members=members)
        self.registered_orders[start : end + 1] = [group]
        self.order_selected_index = start
        if self.view_mode_active:
            self.view_anchor_index = start
            self.view_cursor_index = start
            self._exit_view_mode()
        else:
            self._refresh_orders()
        self._log_debug(f"group_create id={group.group_id} start={start} count={len(members)}")

    def _ungroup_selected_group(self) -> None:
        if not self.registered_orders:
            return
        idx = self.order_selected_index
        if idx is None or not (0 <= idx < len(self.registered_orders)):
            return
        row = self.registered_orders[idx]
        if not isinstance(row, RegisterGroup):
            return

        members = list(row.members)
        self.registered_orders[idx : idx + 1] = members
        self._close_group_id_gap(row.group_id)
        self.order_selected_index = idx
        if self.view_mode_active:
            self.view_anchor_index = idx
            self.view_cursor_index = idx
        self._refresh_orders()
        self._log_debug(f"group_remove id={row.group_id} at={idx} restored={len(members)}")

    def _copy_for_submit(self, item: OrderEntry, group_id: int | None) -> OrderEntry:
        copied = OrderEntry(dish_id=item.dish_id, name=item.name, mode=item.mode, selected_notes=set(item.selected_notes))
        if group_id is not None:
            setattr(copied, "_group_id", group_id)
        return copied

    def _flatten_register_rows_for_submit(self) -> list[OrderEntry]:
        flattened: list[OrderEntry] = []
        for row in self.registered_orders:
            if isinstance(row, RegisterGroup):
                for member in row.members:
                    flattened.append(self._copy_for_submit(member, row.group_id))
            else:
                flattened.append(self._copy_for_submit(row, None))
        return flattened

    def _delete_selected_order(self) -> None:
        if not self.registered_orders or self.order_selected_index is None:
            return

        idx = self.order_selected_index
        if not (0 <= idx < len(self.registered_orders)):
            self.order_selected_index = None
            self._refresh_orders()
            return

        deleting_group = isinstance(self.registered_orders[idx], RegisterGroup)
        deleted_group_id = self.registered_orders[idx].group_id if deleting_group else None
        del self.registered_orders[idx]
        if deleting_group:
            self._close_group_id_gap(int(deleted_group_id))
        else:
            self._recompute_next_group_id()

        if not self.registered_orders:
            self.order_selected_index = None
        else:
            self.order_selected_index = min(idx, len(self.registered_orders) - 1)

        self._refresh_orders()

    def _selected_order(self) -> OrderEntry | None:
        row = self._selected_row()
        if row is None or isinstance(row, RegisterGroup):
            return None
        return row

    def _open_notes_for_selected_order(self) -> None:
        entry = self._selected_order()
        if entry is None:
            return
        self.ui_mode = "MODAL"
        self.push_screen(NotesModal(entry, on_change=self._on_notes_modal_change))

    def _on_notes_modal_change(self) -> None:
        self._sync_ui_mode()
        self._refresh_orders()

    def _sync_ui_mode(self) -> None:
        if isinstance(self.screen, (NotesModal, OrderNumberModal)):
            self.ui_mode = "MODAL"
        elif self.view_mode_active:
            self.ui_mode = "VIEW"
        elif self.input_state == "active":
            self.ui_mode = "SEARCH"
        else:
            self.ui_mode = "NORMAL"

    def _enter_view_mode(self) -> None:
        if self.input_state != "normal":
            return
        if not self.registered_orders:
            return
        if self.order_selected_index is None or not (0 <= self.order_selected_index < len(self.registered_orders)):
            self.order_selected_index = 0

        self.view_mode_active = True
        self.view_pending_g = False
        self.view_selection_kind = "CHAR"
        self.view_anchor_index = self.order_selected_index
        self.view_cursor_index = self.order_selected_index
        self._sync_ui_mode()
        self._refresh_orders()
        self._log_debug(
            f"view_mode_enter anchor={self.view_anchor_index} cursor={self.view_cursor_index} rows={len(self.registered_orders)}"
        )

    def _exit_view_mode(self) -> None:
        if not self.view_mode_active:
            return
        if self.view_cursor_index is not None and 0 <= self.view_cursor_index < len(self.registered_orders):
            self.order_selected_index = self.view_cursor_index
        self.view_mode_active = False
        self.view_pending_g = False
        self.view_anchor_index = None
        self.view_cursor_index = None
        self.view_selection_kind = "CHAR"
        self._sync_ui_mode()
        self._refresh_orders()
        self._log_debug("view_mode_exit")

    def _move_view_cursor(self, delta: int) -> None:
        if not self.view_mode_active or not self.registered_orders:
            return
        if self.view_cursor_index is None:
            self.view_cursor_index = self.order_selected_index if self.order_selected_index is not None else 0
        self.view_cursor_index = max(0, min(len(self.registered_orders) - 1, self.view_cursor_index + delta))
        self.order_selected_index = self.view_cursor_index
        self._refresh_orders()

    def _jump_view_cursor_to_top(self) -> None:
        if not self.registered_orders:
            return
        self.view_cursor_index = 0
        self.order_selected_index = self.view_cursor_index
        self._refresh_orders()

    def _jump_view_cursor_to_bottom(self) -> None:
        if not self.registered_orders:
            return
        self.view_cursor_index = len(self.registered_orders) - 1
        self.order_selected_index = self.view_cursor_index
        self._refresh_orders()

    def _clear_view_pending_g(self) -> None:
        if self.view_pending_g:
            self.view_pending_g = False
            self._log_debug("view_mode_g_cleared")

    def _view_range_bounds(self) -> tuple[int, int] | None:
        if not self.view_mode_active:
            return None
        if self.view_anchor_index is None or self.view_cursor_index is None:
            return None
        return (min(self.view_anchor_index, self.view_cursor_index), max(self.view_anchor_index, self.view_cursor_index))

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

    def _selected_note_ids(self, item: OrderEntry) -> list[str]:
        return [note_id for note_id in NOTE_CATALOG if note_id in item.selected_notes]

    def _append_item_with_notes(self, lines: Text, item: OrderEntry, prefix: str, note_indent: str) -> None:
        lines.append(prefix)
        lines.append_text(format_order_label(item))
        selected_note_ids = self._selected_note_ids(item)
        if selected_note_ids:
            lines.append(f"\n{note_indent}")
            lines.append_text(format_note_tags(selected_note_ids))

    def _refresh_orders(self) -> None:
        try:
            orders_widget = self.query_one("#orders-list", Static)
        except NoMatches:
            return
        if not self.registered_orders:
            if self.view_mode_active:
                self.view_mode_active = False
                self.view_pending_g = False
                self.view_anchor_index = None
                self.view_cursor_index = None
                self.view_selection_kind = "CHAR"
                self._sync_ui_mode()
            self.order_selected_index = None
            orders_widget.update("(no items yet)")
            return

        if self.order_selected_index is not None and self.order_selected_index >= len(self.registered_orders):
            self.order_selected_index = len(self.registered_orders) - 1

        visible_rows = self._visible_rows(orders_widget)
        start, end = self._window_bounds(len(self.registered_orders), visible_rows, self.order_selected_index)
        view_bounds = self._view_range_bounds()

        lines = Text()
        if start > 0:
            lines.append("⋮\n", style="dim")

        for idx in range(start, end):
            if idx > start:
                lines.append("\n")

            row_start = len(lines)
            row = self.registered_orders[idx]
            if isinstance(row, RegisterGroup):
                global_prefix = f"{idx + 1}. "
                group_col = str(row.group_id)
                first_left = f"{global_prefix}{group_col} │ "
                rest_left = f"{' ' * len(global_prefix)}{' ' * len(group_col)} │ "
                for member_idx, member in enumerate(row.members):
                    if member_idx > 0:
                        lines.append("\n")
                    left = first_left if member_idx == 0 else rest_left
                    member_prefix = f"{left}{member_idx + 1}. "
                    self._append_item_with_notes(lines, member, member_prefix, " " * len(member_prefix))
            else:
                prefix = f"{idx + 1}. "
                self._append_item_with_notes(lines, row, prefix, " " * len(prefix))

            is_selected = False
            if view_bounds is not None:
                is_selected = view_bounds[0] <= idx <= view_bounds[1]
            else:
                is_selected = idx == self.order_selected_index

            if is_selected:
                row_end = len(lines)
                lines.stylize("reverse", row_start, row_end)

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
            bar.update(f"Press R, G, or S to search. Ctrl+S submit/print.\\n{status}")
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

    def _refresh_footer(self) -> None:
        try:
            footer = self.query_one("#mode-footer", Static)
        except NoMatches:
            return
        if self.ui_mode == "SEARCH":
            footer.update(f"Mode: SEARCH ({self._search_mode_label()})")
            return
        footer.update(f"Mode: {self.ui_mode}")
