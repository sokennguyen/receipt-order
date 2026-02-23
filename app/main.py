"""Entry point for the receipt-order Textual app."""

from __future__ import annotations

from app.receipt_app import ReceiptOrderApp


def main() -> None:
    """Run the Textual application."""
    ReceiptOrderApp().run()


if __name__ == "__main__":
    main()
