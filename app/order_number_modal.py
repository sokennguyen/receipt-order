"""Order number entry modal screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Static


class OrderNumberModal(ModalScreen[int | None]):
    """Prompt for an order number before submit/print."""

    CSS = """
    OrderNumberModal {
        align: center middle;
        background: $background 60%;
    }

    #order-number-dialog {
        width: 56;
        height: auto;
        border: round $secondary;
        background: $panel;
        padding: 1 2;
    }

    #order-number-title {
        text-style: bold;
        margin-bottom: 1;
        color: white;
    }

    #order-number-prompt {
        color: white;
        margin-bottom: 1;
    }

    #order-number-value {
        border: heavy $secondary;
        padding: 0 1;
        color: white;
        margin-bottom: 1;
    }

    #order-number-error {
        color: #ffb3b3;
        margin-bottom: 1;
    }

    #order-number-help {
        color: #dddddd;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.value = ""
        self.error = ""

    def compose(self) -> ComposeResult:
        with Container(id="order-number-dialog"):
            yield Static("Order Number", id="order-number-title")
            yield Static("Enter a number from 1 to 1000", id="order-number-prompt")
            yield Static(id="order-number-value")
            yield Static(id="order-number-error")
            yield Static("Digits only. Enter confirm. Backspace delete. Esc/q/Ctrl+C cancel.", id="order-number-help")

    def on_mount(self) -> None:
        self._refresh_content()

    def on_key(self, event: Key) -> None:
        if event.key in {"escape", "q", "ctrl+c"}:
            self.dismiss(None)
            event.stop()
            return

        if event.key == "enter":
            self._confirm()
            event.stop()
            return

        if event.key == "backspace":
            if self.value:
                self.value = self.value[:-1]
                self.error = ""
                self._refresh_content()
            event.stop()
            return

        if event.is_printable and event.character and event.character.isdigit():
            if len(self.value) < 4:
                self.value += event.character
            self.error = ""
            self._refresh_content()
            event.stop()

    def _confirm(self) -> None:
        if not self.value:
            self.error = "Order number is required."
            self._refresh_content()
            return

        parsed = int(self.value)
        if not (1 <= parsed <= 1000):
            self.error = "Order number must be between 1 and 1000."
            self._refresh_content()
            return

        self.dismiss(parsed)

    def _refresh_content(self) -> None:
        value_widget = self.query_one("#order-number-value", Static)
        error_widget = self.query_one("#order-number-error", Static)
        value_widget.update(self.value or "")
        error_widget.update(self.error or "")
