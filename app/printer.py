"""Printer integration based on test.py prototype."""

from __future__ import annotations

from app.config import (
    PRINTER_FONT_PATH,
    PRINTER_FONT_SIZE,
    PRINTER_LEFT_INDENT_PX,
    PRINTER_SINGLE_ITEM_SPACER_PX,
    PRINTER_USB_PRODUCT_ID,
    PRINTER_USB_VENDOR_ID,
    PRINTER_WIDTH_PX,
)
from app.models import OrderEntry


def to_print_label(item: OrderEntry) -> str:
    """Format printed line as <Mode>-<BaseName> or plain for untagged rows."""
    base_name = item.name
    for suffix in (" Ramyun", " Gimbap"):
        if base_name.endswith(suffix):
            base_name = base_name[: -len(suffix)]
            break

    if item.mode in {"R", "G"}:
        return f"{item.mode}-{base_name}"
    return base_name


def check_printer_dependencies() -> tuple[bool, str]:
    """Check whether printer dependencies are importable."""
    try:
        from escpos.printer import Usb  # noqa: F401
        from PIL import ImageFont  # noqa: F401
    except Exception as exc:
        return (False, f"Printer deps unavailable: {exc}")
    return (True, "Printer ready")


def _render_line(text: str, font: object) -> object:
    from PIL import Image, ImageDraw

    canvas_height = PRINTER_FONT_SIZE + 20
    img = Image.new("1", (PRINTER_WIDTH_PX, canvas_height), color=1)
    draw = ImageDraw.Draw(img)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_height = bbox[3] - bbox[1]

    x = PRINTER_LEFT_INDENT_PX
    y = (canvas_height - text_height) // 2
    draw.text((x, y), text, font=font, fill=0)
    return img


def _render_spacer(height_px: int) -> object:
    from PIL import Image

    return Image.new("1", (PRINTER_WIDTH_PX, max(1, height_px)), color=1)


def print_order_batch(items: list[OrderEntry]) -> None:
    """Print all items in order and cut the ticket at the end."""
    if not items:
        return

    try:
        from escpos.printer import Usb
        from PIL import ImageFont
    except Exception as exc:
        raise RuntimeError(f"Printer dependencies unavailable: {exc}") from exc

    printer = Usb(PRINTER_USB_VENDOR_ID, PRINTER_USB_PRODUCT_ID)
    font = ImageFont.truetype(PRINTER_FONT_PATH, PRINTER_FONT_SIZE)

    for item in items:
        line = to_print_label(item)
        img = _render_line(line, font)
        printer.image(img)

    # Give single-item tickets a minimal extra tail for easier tearing.
    if len(items) == 1:
        printer.image(_render_spacer(PRINTER_SINGLE_ITEM_SPACER_PX))

    printer.cut()
