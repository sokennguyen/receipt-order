"""Entry point for the receipt-order Textual app."""

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static


class ReceiptOrderApp(App):
    """A minimal Textual application scaffold."""

    TITLE = "Receipt Order"
    SUB_TITLE = "Textual starter"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Welcome to your Textual app!", id="welcome")
        yield Footer()


def main() -> None:
    """Run the Textual application."""
    ReceiptOrderApp().run()


if __name__ == "__main__":
    main()
