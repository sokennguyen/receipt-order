"""Entry point for the receipt-order Textual app."""

from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.events import Key
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Header, Static


@dataclass(frozen=True)
class MenuItem:
    """A searchable menu item."""

    name: str


@dataclass(frozen=True)
class OrderEntry:
    """A registered order row."""

    name: str
    mode: str | None = None


def badge_style(mode: str) -> str:
    """Return a consistent badge style for category tags."""
    if mode == "R":
        return "bold #ffffff on #b23a48"
    return "bold #0b1f0f on #5fbf72"


def format_order_label(entry: OrderEntry) -> Text:
    """Render an order label with an optional colored mode tag."""
    text = Text()
    if entry.mode in {"R", "G"}:
        text.append(entry.mode, style=badge_style(entry.mode))
        text.append(f" {entry.name}")
    else:
        text.append(entry.name)
    return text


class NotesModal(ModalScreen[None]):
    """Simple centered modal for selected dish notes."""

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
        ("ctrl+c", "close", "Close"),
    ]

    CSS = """
    NotesModal {
        align: center middle;
        background: $background 60%;
    }

    #notes-dialog {
        width: 44;
        height: auto;
        border: round $secondary;
        background: $panel;
        padding: 1 2;
    }

    #notes-title {
        text-style: bold;
        margin-bottom: 1;
    }

    #notes-help {
        margin-top: 1;
        color: $text-muted;
    }
    """

    def __init__(self, order: OrderEntry) -> None:
        super().__init__()
        self.order = order

    def compose(self) -> ComposeResult:
        with Container(id="notes-dialog"):
            yield Static("Notes", id="notes-title")
            yield Static(id="notes-body")
            yield Static("Esc / q / Ctrl+C to close", id="notes-help")

    def on_mount(self) -> None:
        self.query_one("#notes-body", Static).update(format_order_label(self.order))

    def action_close(self) -> None:
        self.dismiss()


MENU_BY_MODE: dict[str, list[MenuItem]] = {
    "G": [
        MenuItem("Pork Gimbap"),
        MenuItem("Tuna Mayo Gimbap"),
        MenuItem("Cheese Gimbap"),
        MenuItem("Bulgogi Gimbap"),
        MenuItem("Kimchi Gimbap"),
    ],
    "R": [
        MenuItem("Classic Ramyun"),
        MenuItem("Shin Ramyun"),
        MenuItem("Cheese Ramyun"),
        MenuItem("Seafood Ramyun"),
        MenuItem("Kimchi Ramyun"),
    ],
}


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
        ("ctrl+c", "cancel_active_mode", "Exit active mode"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.registered_orders: list[OrderEntry] = []

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
        self._refresh_all()

    def on_key(self, event: Key) -> None:
        # While a modal is active, let the modal own keyboard handling.
        if isinstance(self.screen, NotesModal):
            return

        if not event.is_printable or len(event.character) != 1 or not event.character.isalnum():
            return

        key = event.character.lower()
        if self.input_state == "normal":
            if key == "t":
                self.registered_orders.append(OrderEntry(name="Tteokbokki"))
                self.order_selected_index = len(self.registered_orders) - 1
                self._refresh_orders()
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
        if self.input_state == "normal":
            return

        self.input_state = "normal"
        self.query = ""
        self.selected_index = 0
        self._refresh_search()

    def action_cycle_results(self, delta: int) -> None:
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
        if self.input_state != "active":
            return

        results = self._filtered_results()
        if not results:
            return
        item = results[self.selected_index]
        self.registered_orders.append(OrderEntry(name=item.name, mode=self.mode))
        self.order_selected_index = len(self.registered_orders) - 1
        self._refresh_orders()

    def action_backspace_query(self) -> None:
        if self.input_state != "active":
            return

        if not self.query:
            return
        self.query = self.query[:-1]
        self.selected_index = 0
        self._refresh_search()

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
        self.push_screen(NotesModal(entry))

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
        orders_widget = self.query_one("#orders-list", Static)
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
            bar.update("Press R or G to search the menu. Ctrl+Q to quit.")
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


def main() -> None:
    """Run the Textual application."""
    ReceiptOrderApp().run()


if __name__ == "__main__":
    main()
