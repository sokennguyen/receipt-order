"""Printer integration based on test.py prototype."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import (
    PRINTER_FONT_PATH,
    PRINTER_FONT_SIZE,
    PRINTER_LEFT_INDENT_PX,
    PRINTER_SINGLE_ITEM_SPACER_PX,
    PRINTER_USB_PRODUCT_ID,
    PRINTER_USB_VENDOR_ID,
    PRINTER_WIDTH_PX,
)
from app.data import NOTE_CATALOG, print_label_override_for_dish, print_note_alias_for_id
from app.models import OrderEntry


@dataclass
class _GroupedPrintRow:
    item: OrderEntry
    count: int
    note_key: frozenset[str]
    first_seen_index: int


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


def _render_section_separator() -> object:
    from PIL import Image, ImageDraw

    height = 10
    img = Image.new("1", (PRINTER_WIDTH_PX, height), color=1)
    draw = ImageDraw.Draw(img)
    y = height // 2
    draw.line((0, y, PRINTER_WIDTH_PX - 1, y), fill=0, width=1)
    return img


def _render_order_number_header(order_number: int, font: object) -> object:
    from PIL import Image, ImageDraw

    text = str(order_number)
    canvas_height = max(26, PRINTER_FONT_SIZE - 24)
    img = Image.new("1", (PRINTER_WIDTH_PX, canvas_height), color=1)
    draw = ImageDraw.Draw(img)

    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    text_x = max(0, PRINTER_WIDTH_PX - text_width)
    text_y = max(0, (canvas_height - text_height) // 2)
    draw.text((text_x, text_y), text, font=font, fill=0)
    return img


def _category_rank(mode: str | None) -> int:
    if mode == "G":
        return 0
    if mode == "R":
        return 1
    if mode == "S":
        return 3
    return 2


def _group_print_items(items: list[OrderEntry]) -> list[_GroupedPrintRow]:
    """Group by mode+dish+exact note set and then sort for print."""
    groups: dict[tuple[str | None, str, frozenset[str]], _GroupedPrintRow] = {}

    for idx, item in enumerate(items):
        note_key = frozenset(item.selected_notes)
        key = (item.mode, item.dish_id, note_key)
        row = groups.get(key)
        if row is not None:
            row.count += 1
            continue
        groups[key] = _GroupedPrintRow(item=item, count=1, note_key=note_key, first_seen_index=idx)

    rows = list(groups.values())
    rows.sort(key=lambda row: (_category_rank(row.item.mode), -row.count, row.first_seen_index))
    return rows


def _ordered_note_labels(note_key: frozenset[str]) -> list[str]:
    return [print_note_alias_for_id(note_id) for note_id in NOTE_CATALOG if note_id in note_key]


def _grouped_print_label(item: OrderEntry, count: int) -> str:
    base = to_print_label(item)
    if count <= 1:
        return base
    return f"{base} │{count}"


def print_order_batch(items: list[OrderEntry], order_number: int) -> None:
    """Print all items in order and cut the ticket at the end."""
    if not items:
        return
    if not (1 <= order_number <= 1000):
        raise ValueError("order_number must be between 1 and 1000")

    try:
        from escpos.printer import Usb
        from PIL import ImageFont
    except Exception as exc:
        raise RuntimeError(f"Printer dependencies unavailable: {exc}") from exc

    printer = Usb(PRINTER_USB_VENDOR_ID, PRINTER_USB_PRODUCT_ID)
    font = ImageFont.truetype(PRINTER_FONT_PATH, PRINTER_FONT_SIZE)
    header_font = ImageFont.truetype(PRINTER_FONT_PATH, max(20, PRINTER_FONT_SIZE - 20))
    grouped_items = _group_print_items(items)
    printer.image(_render_order_number_header(order_number, header_font))
    printed_s_separator = False

    for row in grouped_items:
        if row.item.mode == "S" and not printed_s_separator:
            printer.image(_render_section_separator())
            printed_s_separator = True

        line = _grouped_print_label(row.item, row.count)
        img = _render_line(line, font)
        printer.image(img)

        for note_label in _ordered_note_labels(row.note_key):
            note_line = _render_line(f"    {note_label}", font)
            printer.image(note_line)

    # Give single-line tickets a minimal extra tail for easier tearing.
    if len(grouped_items) == 1:
        printer.image(_render_spacer(PRINTER_SINGLE_ITEM_SPACER_PX))

    printer.cut()
