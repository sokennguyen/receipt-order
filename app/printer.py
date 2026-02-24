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
from app.data import print_label_override_for_dish
from app.models import OrderEntry


def to_print_label(item: OrderEntry) -> str:
    """Format printed line as <Mode>-<BaseName> or plain for untagged rows."""
    override = print_label_override_for_dish(item.dish_id)
    if override is not None:
        return override

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


def _group_print_items(items: list[OrderEntry]) -> list[tuple[OrderEntry, int]]:
    """Group by mode+dish while preserving first-seen order."""
    groups: dict[tuple[str | None, str], tuple[OrderEntry, int]] = {}
    ordered_keys: list[tuple[str | None, str]] = []

    for item in items:
        key = (item.mode, item.dish_id)
        if key in groups:
            representative, count = groups[key]
            groups[key] = (representative, count + 1)
            continue
        groups[key] = (item, 1)
        ordered_keys.append(key)

    return [groups[key] for key in ordered_keys]


def _grouped_print_label(item: OrderEntry, count: int) -> str:
    base = to_print_label(item)
    if count <= 1:
        return base
    return f"{base} {count}"


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
    grouped_items = _group_print_items(items)

    for item, count in grouped_items:
        line = _grouped_print_label(item, count)
        img = _render_line(line, font)
        printer.image(img)

    # Give single-line tickets a minimal extra tail for easier tearing.
    if len(grouped_items) == 1:
        printer.image(_render_spacer(PRINTER_SINGLE_ITEM_SPACER_PX))

    printer.cut()
