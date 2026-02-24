"""Runtime configuration defaults for persistence and printing."""

from __future__ import annotations

DB_PATH = "data/receipt.db"

# Values copied from test.py prototype.
PRINTER_USB_VENDOR_ID = 0x28E9
PRINTER_USB_PRODUCT_ID = 0x0289
PRINTER_WIDTH_PX = 384
PRINTER_FONT_SIZE = 68
PRINTER_FONT_PATH = "/System/Library/Fonts/SFNS.ttf"
PRINTER_LEFT_INDENT_PX = 16
PRINTER_SINGLE_ITEM_SPACER_PX = 70
