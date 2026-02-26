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
from app.models import MenuItem, OrderConfirmData, OrderEntry, RegisterGroup, RegisterRow
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
    order_selected_member_index = reactive(None)

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
        self.view_group_locked = False
        self.view_group_row_index = None
        self.view_member_anchor_index = None
        self.view_member_cursor_index = None
        self.next_group_id = 1
        self._bulk_note_targets: list[OrderEntry] | None = None
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
                if event.character == "N":
                    self._clear_view_pending_g()
                    self._open_notes_for_view_selection()
                    event.stop()
                    return
                if event.character == "A":
                    self._clear_view_pending_g()
                    self._toggle_takeaway_whole_order()
                    event.stop()
                    return
                if event.character == "J":
                    self._clear_view_pending_g()
                    self._reorder_view_selection_block(1)
                    event.stop()
                    return
                if event.character == "K":
                    self._clear_view_pending_g()
                    self._reorder_view_selection_block(-1)
                    event.stop()
                    return
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
                if key == "d":
                    self._clear_view_pending_g()
                    self._delete_view_selected_rows()
                    event.stop()
                    return
                if key == "n":
                    self._clear_view_pending_g()
                    self._open_notes_for_view_selection()
                    event.stop()
                    return
                if key == "a":
                    self._clear_view_pending_g()
                    self._toggle_takeaway_selection()
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

            if key == "a":
                if event.character == "A":
                    self._toggle_takeaway_whole_order()
                else:
                    self._toggle_takeaway_selection()
                event.stop()
                return

            if key == "t":
                self.registered_orders.append(OrderEntry(dish_id="tteokbokki", name=display_name_for_dish("tteokbokki")))
                self.order_selected_index = len(self.registered_orders) - 1
                self.order_selected_member_index = None
                self._refresh_orders()
                event.stop()
                return

            if key == "d":
                self._delete_selected_order()
                event.stop()
                return

            if event.character == "J":
                self._reorder_selected_row(1)
                event.stop()
                return

            if event.character == "K":
                self._reorder_selected_row(-1)
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
        self.order_selected_member_index = None
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

    def _on_order_number_selected(self, result: OrderConfirmData | None) -> None:
        self._sync_ui_mode()
        if result is None:
            self.system_status = "Submit canceled"
            self._refresh_search()
            self._log_debug("submit_canceled reason=no_order_number")
            return
        self._log_debug(
            f"submit_order_number_selected order_number={result.order_number} not_paid={result.not_paid}"
        )
        self._submit_with_order_number(result.order_number, result.not_paid)

    def _submit_with_order_number(self, order_number: int, not_paid: bool) -> None:
        flat_items = self._flatten_register_rows_for_submit()
        batch = save_order_batch(flat_items, order_number)
        self._log_debug(
            f"submit_saved order_id={batch.order_id} order_number={batch.order_number} not_paid={not_paid} rows={len(flat_items)}"
        )
        try:
            print_order_batch(flat_items, batch.order_number, not_paid=not_paid)
        except Exception as exc:
            update_order_status(batch.order_id, "PRINT_FAILED")
            self.system_status = f"Saved {batch.order_id[:8]} but print failed: {exc}"
            self._refresh_search()
            self._log_debug(f"submit_print_failed order_id={batch.order_id} error={exc!r}")
            return

        update_order_status(batch.order_id, "PRINTED")
        self.registered_orders.clear()
        self.order_selected_index = None
        self.order_selected_member_index = None
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

        path = self._selection_path_list()
        if not path:
            return
        current_path_idx = self._current_selection_path_index(path)
        if current_path_idx is None:
            current_path_idx = 0 if delta > 0 else len(path) - 1
        else:
            current_path_idx = (current_path_idx + delta) % len(path)
        self._set_selection_path(path[current_path_idx])
        self._refresh_orders()

    def _selection_path_list(self) -> list[tuple[int, int | None]]:
        path: list[tuple[int, int | None]] = []
        for idx, row in enumerate(self.registered_orders):
            path.append((idx, None))
            if isinstance(row, RegisterGroup):
                for member_idx in range(len(row.members)):
                    path.append((idx, member_idx))
        return path

    def _current_selection_path_index(self, path: list[tuple[int, int | None]]) -> int | None:
        if self.order_selected_index is None:
            return None
        current = (self.order_selected_index, self.order_selected_member_index)
        try:
            return path.index(current)
        except ValueError:
            fallback = (self.order_selected_index, None)
            try:
                return path.index(fallback)
            except ValueError:
                return None

    def _set_selection_path(self, path_entry: tuple[int, int | None]) -> None:
        self.order_selected_index, self.order_selected_member_index = path_entry

    def _selected_group_and_member(self) -> tuple[RegisterGroup, int] | None:
        if self.order_selected_index is None or self.order_selected_member_index is None:
            return None
        if not (0 <= self.order_selected_index < len(self.registered_orders)):
            return None
        row = self.registered_orders[self.order_selected_index]
        if not isinstance(row, RegisterGroup):
            return None
        if not (0 <= self.order_selected_member_index < len(row.members)):
            return None
        return (row, self.order_selected_member_index)

    def _reorder_selected_row(self, delta: int) -> None:
        if len(self.registered_orders) < 2:
            return

        if self.order_selected_index is None:
            self.order_selected_index = 0
            self.order_selected_member_index = None
            self._refresh_orders()
            return

        src = self.order_selected_index
        if not (0 <= src < len(self.registered_orders)):
            return

        dst = src + delta
        if not (0 <= dst < len(self.registered_orders)):
            return

        self.registered_orders[src], self.registered_orders[dst] = (
            self.registered_orders[dst],
            self.registered_orders[src],
        )
        self.order_selected_index = dst
        self.order_selected_member_index = None
        self._refresh_orders()

    def _reorder_view_selection_block(self, delta: int) -> None:
        if not self.view_mode_active or len(self.registered_orders) < 2:
            return
        bounds = self._view_range_bounds()
        if bounds is None:
            return
        start, end = bounds
        dst_start = start + delta
        dst_end = end + delta
        if dst_start < 0 or dst_end >= len(self.registered_orders):
            self._log_debug(
                f"view_reorder_noop reason=boundary start={start} end={end} delta={delta}"
            )
            return

        block = self.registered_orders[start : end + 1]
        del self.registered_orders[start : end + 1]
        insert_at = start + 1 if delta > 0 else start - 1
        self.registered_orders[insert_at:insert_at] = block

        if self.view_anchor_index is not None:
            self.view_anchor_index += delta
        if self.view_cursor_index is not None:
            self.view_cursor_index += delta
        self.order_selected_index = self.view_cursor_index
        self._refresh_orders()
        self._log_debug(
            f"view_reorder_ok start={start} end={end} delta={delta} new_start={start + delta} new_end={end + delta}"
        )

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
        if self.order_selected_member_index is not None:
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
        self.order_selected_member_index = None
        if self.view_mode_active:
            self.view_anchor_index = idx
            self.view_cursor_index = idx
        self._refresh_orders()
        self._log_debug(f"group_remove id={row.group_id} at={idx} restored={len(members)}")

    def _copy_for_submit(self, item: OrderEntry, group_id: int | None) -> OrderEntry:
        copied = OrderEntry(
            dish_id=item.dish_id,
            name=item.name,
            mode=item.mode,
            selected_notes=set(item.selected_notes),
            is_takeaway=item.is_takeaway,
        )
        if group_id is not None:
            setattr(copied, "_group_id", group_id)
        return copied

    def _all_register_items(self) -> list[OrderEntry]:
        items: list[OrderEntry] = []
        for row in self.registered_orders:
            if isinstance(row, RegisterGroup):
                items.extend(row.members)
            else:
                items.append(row)
        return items

    def _selection_targets_with_context(self) -> list[tuple[OrderEntry, bool]]:
        if self.view_mode_active:
            if self.view_group_locked:
                if self.view_group_row_index is None or not (0 <= self.view_group_row_index < len(self.registered_orders)):
                    return []
                row = self.registered_orders[self.view_group_row_index]
                if not isinstance(row, RegisterGroup):
                    return []
                bounds = self._view_member_range_bounds()
                if bounds is None:
                    return []
                start, end = bounds
                if not (0 <= start <= end < len(row.members)):
                    return []
                return [(item, True) for item in row.members[start : end + 1]]

            bounds = self._view_range_bounds()
            if bounds is None:
                return []
            start, end = bounds
            if not (0 <= start <= end < len(self.registered_orders)):
                return []
            targets: list[tuple[OrderEntry, bool]] = []
            for row in self.registered_orders[start : end + 1]:
                if isinstance(row, RegisterGroup):
                    targets.extend((member, True) for member in row.members)
                else:
                    targets.append((row, False))
            return targets

        selected_member = self._selected_group_and_member()
        if selected_member is not None:
            group, member_idx = selected_member
            return [(group.members[member_idx], True)]

        row = self._selected_row()
        if row is None:
            return []
        if isinstance(row, RegisterGroup):
            return [(member, True) for member in row.members]
        return [(row, False)]

    def _toggle_takeaway_selection(self) -> None:
        targets_with_ctx = self._selection_targets_with_context()
        if not targets_with_ctx:
            return
        has_grouped = any(is_grouped for _, is_grouped in targets_with_ctx)
        has_non_grouped = any(not is_grouped for _, is_grouped in targets_with_ctx)
        if has_grouped and has_non_grouped:
            self._log_debug("takeaway_toggle_noop reason=mixed_group_context")
            return
        for item, _ in targets_with_ctx:
            item.is_takeaway = not item.is_takeaway
        self._refresh_orders()

    def _toggle_takeaway_whole_order(self) -> None:
        items = self._all_register_items()
        if not items:
            return
        make_takeaway = not all(item.is_takeaway for item in items)
        for item in items:
            item.is_takeaway = make_takeaway
        self._refresh_orders()

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

        selected_group_member = self._selected_group_and_member()
        if selected_group_member is not None:
            group, member_idx = selected_group_member
            del group.members[member_idx]
            if group.members:
                self.order_selected_member_index = min(member_idx, len(group.members) - 1)
                self._refresh_orders()
                return
            # Empty group behaves like deleting the group header itself.
            idx = self.order_selected_index
            deleted_group_id = group.group_id
            del self.registered_orders[idx]
            self._close_group_id_gap(deleted_group_id)
            if not self.registered_orders:
                self.order_selected_index = None
                self.order_selected_member_index = None
            else:
                self.order_selected_index = min(idx, len(self.registered_orders) - 1)
                self.order_selected_member_index = None
            self._refresh_orders()
            return

        idx = self.order_selected_index
        if not (0 <= idx < len(self.registered_orders)):
            self.order_selected_index = None
            self.order_selected_member_index = None
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
            self.order_selected_member_index = None
        else:
            self.order_selected_index = min(idx, len(self.registered_orders) - 1)
            self.order_selected_member_index = None

        self._refresh_orders()

    def _delete_view_selected_rows(self) -> None:
        if not self.view_mode_active or not self.registered_orders:
            return
        did_delete = False
        if self.view_group_locked:
            if self.order_selected_member_index is None:
                self._delete_selected_order()
                self._exit_view_mode()
                return
            if self.view_group_row_index is None or not (0 <= self.view_group_row_index < len(self.registered_orders)):
                return
            row = self.registered_orders[self.view_group_row_index]
            if not isinstance(row, RegisterGroup):
                return
            bounds = self._view_member_range_bounds()
            if bounds is None:
                return
            start, end = bounds
            if not (0 <= start <= end < len(row.members)):
                return
            del row.members[start : end + 1]
            did_delete = True
            if row.members:
                next_member = min(start, len(row.members) - 1)
                self.view_member_anchor_index = next_member
                self.view_member_cursor_index = next_member
                self.order_selected_index = self.view_group_row_index
                self.order_selected_member_index = next_member
                self._refresh_orders()
                self._exit_view_mode()
                return
            # Group emptied: remove group and fall back to normal mode selection.
            removed_group_id = row.group_id
            del self.registered_orders[self.view_group_row_index]
            self._close_group_id_gap(removed_group_id)
            if not self.registered_orders:
                self.order_selected_index = None
                self.order_selected_member_index = None
            else:
                self.order_selected_index = min(self.view_group_row_index, len(self.registered_orders) - 1)
                self.order_selected_member_index = None
            self._exit_view_mode()
            return
        bounds = self._view_range_bounds()
        if bounds is None:
            return
        start, end = bounds
        if not (0 <= start <= end < len(self.registered_orders)):
            return

        deleted_rows = self.registered_orders[start : end + 1]
        deleted_group_ids = sorted(
            {row.group_id for row in deleted_rows if isinstance(row, RegisterGroup)}
        )
        del self.registered_orders[start : end + 1]
        did_delete = True

        if deleted_group_ids:
            for group_id in deleted_group_ids:
                self._close_group_id_gap(group_id)
        else:
            self._recompute_next_group_id()

        if not self.registered_orders:
            self.order_selected_index = None
            self.order_selected_member_index = None
            self.view_anchor_index = None
            self.view_cursor_index = None
            self._refresh_orders()
            return

        next_idx = min(start, len(self.registered_orders) - 1)
        self.order_selected_index = next_idx
        self.order_selected_member_index = None
        self.view_anchor_index = next_idx
        self.view_cursor_index = next_idx
        self._refresh_orders()
        if did_delete:
            self._exit_view_mode()

    def _selected_order(self) -> OrderEntry | None:
        selected_group_member = self._selected_group_and_member()
        if selected_group_member is not None:
            group, member_idx = selected_group_member
            return group.members[member_idx]
        row = self._selected_row()
        if row is None or isinstance(row, RegisterGroup):
            return None
        return row

    def _view_selected_plain_items(self) -> list[OrderEntry]:
        if self.view_group_locked:
            if self.view_group_row_index is None:
                return []
            if not (0 <= self.view_group_row_index < len(self.registered_orders)):
                return []
            row = self.registered_orders[self.view_group_row_index]
            if not isinstance(row, RegisterGroup):
                return []
            bounds = self._view_member_range_bounds()
            if bounds is None:
                return []
            start, end = bounds
            if not (0 <= start <= end < len(row.members)):
                return []
            return list(row.members[start : end + 1])

        bounds = self._view_range_bounds()
        if bounds is None:
            return []
        start, end = bounds
        if not (0 <= start <= end < len(self.registered_orders)):
            return []

        items: list[OrderEntry] = []
        for row in self.registered_orders[start : end + 1]:
            if isinstance(row, RegisterGroup):
                return []
            items.append(row)
        return items

    def _can_open_view_notes(self, items: list[OrderEntry]) -> bool:
        if not items:
            return False
        first = items[0]
        return all(item.dish_id == first.dish_id and item.selected_notes == first.selected_notes for item in items)

    def _open_notes_for_selected_order(self) -> None:
        entry = self._selected_order()
        if entry is None:
            return
        self._bulk_note_targets = None
        self.ui_mode = "MODAL"
        self.push_screen(NotesModal(entry, on_change=self._on_notes_modal_change))

    def _open_notes_for_view_selection(self) -> None:
        if self.view_group_locked and self.order_selected_member_index is None:
            # Group header in fallback path: no-op notes.
            self._bulk_note_targets = None
            return
        items = self._view_selected_plain_items()
        if not self._can_open_view_notes(items):
            self._bulk_note_targets = None
            return
        self._bulk_note_targets = items
        self.ui_mode = "MODAL"
        self.push_screen(NotesModal(items[0], on_change=self._on_notes_modal_change))

    def _on_notes_modal_change(self) -> None:
        was_bulk_notes = bool(self._bulk_note_targets)
        if self._bulk_note_targets:
            source_notes = set(self._bulk_note_targets[0].selected_notes)
            for item in self._bulk_note_targets[1:]:
                item.selected_notes = set(source_notes)
        self._bulk_note_targets = None
        if was_bulk_notes and self.view_mode_active:
            self._exit_view_mode()
            return
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

    def _normalize_selection_state(self) -> None:
        if self.order_selected_index is None:
            self.order_selected_member_index = None
            return
        if not (0 <= self.order_selected_index < len(self.registered_orders)):
            self.order_selected_index = None
            self.order_selected_member_index = None
            return
        row = self.registered_orders[self.order_selected_index]
        if not isinstance(row, RegisterGroup):
            self.order_selected_member_index = None
            return
        if self.order_selected_member_index is None:
            return
        if not row.members:
            self.order_selected_member_index = None
            return
        self.order_selected_member_index = max(0, min(len(row.members) - 1, self.order_selected_member_index))

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
        self.view_group_locked = False
        self.view_group_row_index = None
        self.view_member_anchor_index = None
        self.view_member_cursor_index = None
        if self.order_selected_member_index is not None:
            row = self.registered_orders[self.order_selected_index]
            if isinstance(row, RegisterGroup) and 0 <= self.order_selected_member_index < len(row.members):
                self.view_group_locked = True
                self.view_group_row_index = self.order_selected_index
                self.view_member_anchor_index = self.order_selected_member_index
                self.view_member_cursor_index = self.order_selected_member_index
                self.view_anchor_index = None
                self.view_cursor_index = None
            else:
                self.order_selected_member_index = None
                self.view_anchor_index = self.order_selected_index
                self.view_cursor_index = self.order_selected_index
        else:
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
        if self.view_group_locked:
            if self.view_group_row_index is not None and 0 <= self.view_group_row_index < len(self.registered_orders):
                self.order_selected_index = self.view_group_row_index
                self.order_selected_member_index = self.view_member_cursor_index
        elif self.view_cursor_index is not None and 0 <= self.view_cursor_index < len(self.registered_orders):
            self.order_selected_index = self.view_cursor_index
            self.order_selected_member_index = None
        self.view_mode_active = False
        self.view_pending_g = False
        self.view_group_locked = False
        self.view_group_row_index = None
        self.view_member_anchor_index = None
        self.view_member_cursor_index = None
        self.view_anchor_index = None
        self.view_cursor_index = None
        self.view_selection_kind = "CHAR"
        self._sync_ui_mode()
        self._refresh_orders()
        self._log_debug("view_mode_exit")

    def _move_view_cursor(self, delta: int) -> None:
        if not self.view_mode_active or not self.registered_orders:
            return
        if self.view_group_locked:
            if self.view_group_row_index is None or not (0 <= self.view_group_row_index < len(self.registered_orders)):
                return
            row = self.registered_orders[self.view_group_row_index]
            if not isinstance(row, RegisterGroup) or not row.members:
                return
            if self.view_member_cursor_index is None:
                self.view_member_cursor_index = 0
            self.view_member_cursor_index = max(0, min(len(row.members) - 1, self.view_member_cursor_index + delta))
            self.order_selected_index = self.view_group_row_index
            self.order_selected_member_index = self.view_member_cursor_index
            self._refresh_orders()
            return
        if self.view_cursor_index is None:
            self.view_cursor_index = self.order_selected_index if self.order_selected_index is not None else 0
        self.view_cursor_index = max(0, min(len(self.registered_orders) - 1, self.view_cursor_index + delta))
        self.order_selected_index = self.view_cursor_index
        self.order_selected_member_index = None
        self._refresh_orders()

    def _jump_view_cursor_to_top(self) -> None:
        if not self.registered_orders:
            return
        if self.view_group_locked:
            return
        self.view_cursor_index = 0
        self.order_selected_index = self.view_cursor_index
        self.order_selected_member_index = None
        self._refresh_orders()

    def _jump_view_cursor_to_bottom(self) -> None:
        if not self.registered_orders:
            return
        if self.view_group_locked:
            return
        self.view_cursor_index = len(self.registered_orders) - 1
        self.order_selected_index = self.view_cursor_index
        self.order_selected_member_index = None
        self._refresh_orders()

    def _clear_view_pending_g(self) -> None:
        if self.view_pending_g:
            self.view_pending_g = False
            self._log_debug("view_mode_g_cleared")

    def _view_range_bounds(self) -> tuple[int, int] | None:
        if not self.view_mode_active or self.view_group_locked:
            return None
        if self.view_anchor_index is None or self.view_cursor_index is None:
            return None
        return (min(self.view_anchor_index, self.view_cursor_index), max(self.view_anchor_index, self.view_cursor_index))

    def _view_member_range_bounds(self) -> tuple[int, int] | None:
        if not self.view_mode_active or not self.view_group_locked:
            return None
        if self.view_member_anchor_index is None or self.view_member_cursor_index is None:
            return None
        return (
            min(self.view_member_anchor_index, self.view_member_cursor_index),
            max(self.view_member_anchor_index, self.view_member_cursor_index),
        )

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
        if item.is_takeaway:
            lines.append("TAW ", style="bold yellow")
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
                self.view_group_locked = False
                self.view_group_row_index = None
                self.view_member_anchor_index = None
                self.view_member_cursor_index = None
                self.view_anchor_index = None
                self.view_cursor_index = None
                self.view_selection_kind = "CHAR"
                self._sync_ui_mode()
            self.order_selected_index = None
            self.order_selected_member_index = None
            orders_widget.update("(no items yet)")
            return

        if self.order_selected_index is not None and self.order_selected_index >= len(self.registered_orders):
            self.order_selected_index = len(self.registered_orders) - 1
        self._normalize_selection_state()

        visible_rows = self._visible_rows(orders_widget)
        start, end = self._window_bounds(len(self.registered_orders), visible_rows, self.order_selected_index)
        view_bounds = self._view_range_bounds()
        view_member_bounds = self._view_member_range_bounds()

        lines = Text()
        if start > 0:
            lines.append("⋮\n", style="dim")

        item_display_index_by_row: dict[int, int] = {}
        running_item_index = 0
        for row_idx, row_obj in enumerate(self.registered_orders):
            if isinstance(row_obj, RegisterGroup):
                continue
            running_item_index += 1
            item_display_index_by_row[row_idx] = running_item_index

        for idx in range(start, end):
            if idx > start:
                lines.append("\n")

            row_start = len(lines)
            row = self.registered_orders[idx]
            if isinstance(row, RegisterGroup):
                header_start = len(lines)
                lines.append(f"g{row.group_id}")
                header_end = len(lines)
                member_blocks: list[tuple[int, int, int]] = []
                for member_idx, member in enumerate(row.members):
                    lines.append("\n")
                    member_start = len(lines)
                    member_prefix = f"  {member_idx + 1}. "
                    self._append_item_with_notes(lines, member, member_prefix, " " * len(member_prefix))
                    member_end = len(lines)
                    member_blocks.append((member_idx, member_start, member_end))
            else:
                display_idx = item_display_index_by_row.get(idx, idx + 1)
                prefix = f"{display_idx}. "
                self._append_item_with_notes(lines, row, prefix, " " * len(prefix))

            row_end = len(lines)
            if isinstance(row, RegisterGroup):
                if self.view_group_locked and self.view_group_row_index == idx and view_member_bounds is not None:
                    selected_member_idx = self.order_selected_member_index
                    if selected_member_idx is None:
                        lines.stylize("reverse", header_start, header_end)
                    else:
                        start_m, end_m = view_member_bounds
                        for member_idx, m_start, m_end in member_blocks:
                            if start_m <= member_idx <= end_m:
                                lines.stylize("reverse", m_start, m_end)
                elif view_bounds is not None:
                    if view_bounds[0] <= idx <= view_bounds[1]:
                        lines.stylize("reverse", row_start, row_end)
                elif idx == self.order_selected_index:
                    if self.order_selected_member_index is None:
                        lines.stylize("reverse", header_start, header_end)
                    else:
                        for member_idx, m_start, m_end in member_blocks:
                            if member_idx == self.order_selected_member_index:
                                lines.stylize("reverse", m_start, m_end)
                                break
            else:
                is_selected = False
                if view_bounds is not None:
                    is_selected = view_bounds[0] <= idx <= view_bounds[1]
                else:
                    is_selected = idx == self.order_selected_index
                if is_selected:
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
