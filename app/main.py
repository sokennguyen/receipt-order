"""Entry point for the receipt-order Textual app."""

from __future__ import annotations

from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.reactive import reactive
from textual.widgets import Footer, Header, Static


@dataclass(frozen=True)
class MenuItem:
    """A searchable menu item."""

    name: str


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
        border: heavy $accent;
        padding: 0 1;
        margin-bottom: 1;
        height: 3;
    }

    #results {
        height: 1fr;
        border: tall $surface;
        padding: 0 1;
    }

    .pane-title {
        text-style: bold;
        margin-bottom: 1;
    }
    """

    mode = reactive("G")
    query = reactive("")
    selected_index = reactive(0)

    BINDINGS = [
        ("g", "set_mode('G')", "Mode: Gimbap"),
        ("r", "set_mode('R')", "Mode: Ramyun"),
        ("tab", "cycle_results(1)", "Next result"),
        ("up", "cycle_results(-1)", "Previous result"),
        ("down", "cycle_results(1)", "Next result"),
        ("enter", "register_selected", "Register item"),
        ("backspace", "backspace_query", "Delete query char"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.registered_orders: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-layout"):
            with Vertical(id="orders-pane"):
                yield Static("Registered Orders", classes="pane-title")
                yield Static("(no items yet)", id="orders-list")
            with Vertical(id="search-pane"):
                yield Static(id="search-bar")
                yield Static(id="results")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_all()

    def on_key(self, event: Key) -> None:
        if event.is_printable and len(event.character) == 1 and event.character.isalnum():
            if event.character.lower() in {"g", "r"}:
                return
            self.query += event.character
            self.selected_index = 0
            self._refresh_search()

    def action_set_mode(self, mode: str) -> None:
        if mode not in MENU_BY_MODE:
            return
        self.mode = mode
        self.query = ""
        self.selected_index = 0
        self._refresh_search()

    def action_cycle_results(self, delta: int) -> None:
        results = self._filtered_results()
        if not results:
            self.selected_index = 0
            self._refresh_results(results)
            return
        self.selected_index = (self.selected_index + delta) % len(results)
        self._refresh_results(results)

    def action_register_selected(self) -> None:
        results = self._filtered_results()
        if not results:
            return
        item = results[self.selected_index]
        self.registered_orders.append(f"[{self.mode}] {item.name}")
        self._refresh_orders()

    def action_backspace_query(self) -> None:
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

    def _refresh_orders(self) -> None:
        orders_widget = self.query_one("#orders-list", Static)
        if not self.registered_orders:
            orders_widget.update("(no items yet)")
            return
        lines = [f"{idx}. {label}" for idx, label in enumerate(self.registered_orders, start=1)]
        orders_widget.update("\n".join(lines))

    def _refresh_search(self) -> None:
        self._refresh_search_bar()
        self._refresh_results(self._filtered_results())

    def _refresh_search_bar(self) -> None:
        bar = self.query_one("#search-bar", Static)
        shown_query = self.query or ""
        bar.update(f"MODE: {self.mode}    QUERY: {shown_query}")

    def _refresh_results(self, results: list[MenuItem]) -> None:
        results_widget = self.query_one("#results", Static)
        if not results:
            results_widget.update("No results")
            return

        if self.selected_index >= len(results):
            self.selected_index = 0

        lines = []
        for idx, item in enumerate(results):
            pointer = "➤" if idx == self.selected_index else " "
            lines.append(f"{pointer} {item.name}")
        results_widget.update("\n".join(lines))


def main() -> None:
    """Run the Textual application."""
    ReceiptOrderApp().run()


if __name__ == "__main__":
    main()
