"""Printer integration based on test.py prototype."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import sleep

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

# Separator tuning values.
# Keep these grouped so thermal-print behavior can be tuned in one place.
_SECTION_SEPARATOR_HEIGHT_PX = 20
_SECTION_SEPARATOR_THICKNESS_PX = 5
_SECTION_SEPARATOR_STRIPE_HEIGHT_PX = 2
_SECTION_SEPARATOR_PAUSE_SECONDS = 0.1


@dataclass
class _GroupedPrintRow:
    item: OrderEntry
    count: int
    note_key: frozenset[str]
    first_seen_index: int
    group_allocations: dict[int, int] = field(default_factory=dict)


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


def _render_compact_line(text: str, font: object) -> object:
    from PIL import Image, ImageDraw

    probe = Image.new("1", (1, 1), color=1)
    probe_draw = ImageDraw.Draw(probe)
    bbox = probe_draw.textbbox((0, 0), text, font=font)
    text_height = bbox[3] - bbox[1]
    canvas_height = max(12, text_height + 6)

    img = Image.new("1", (PRINTER_WIDTH_PX, canvas_height), color=1)
    draw = ImageDraw.Draw(img)
    x = PRINTER_LEFT_INDENT_PX
    y = (canvas_height - text_height) // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=0)
    return img


def _render_spacer(height_px: int) -> object:
    from PIL import Image

    return Image.new("1", (PRINTER_WIDTH_PX, max(1, height_px)), color=1)


def _render_section_separator() -> object:
    from PIL import Image, ImageDraw

    img = Image.new("1", (PRINTER_WIDTH_PX, _SECTION_SEPARATOR_HEIGHT_PX), color=1)
    draw = ImageDraw.Draw(img)
    top = max(0, (_SECTION_SEPARATOR_HEIGHT_PX - _SECTION_SEPARATOR_THICKNESS_PX) // 2)
    bottom = min(_SECTION_SEPARATOR_HEIGHT_PX - 1, top + _SECTION_SEPARATOR_THICKNESS_PX - 1)
    draw.rectangle((0, top, PRINTER_WIDTH_PX - 1, bottom), fill=0)
    return img


def _print_section_separator(printer: object) -> None:
    """
    Print the separator in short stripes with tiny pauses.

    This intentionally reduces instantaneous heat so the line stays crisp
    instead of bleeding into adjacent dots.
    """
    separator = _render_section_separator()
    for top in range(0, separator.height, _SECTION_SEPARATOR_STRIPE_HEIGHT_PX):
        bottom = min(separator.height, top + _SECTION_SEPARATOR_STRIPE_HEIGHT_PX)
        stripe = separator.crop((0, top, PRINTER_WIDTH_PX, bottom))
        printer.image(stripe)
        if bottom < separator.height:
            sleep(_SECTION_SEPARATOR_PAUSE_SECONDS)


def _render_order_number_header(order_number: int, font: object) -> object:
    from PIL import Image, ImageDraw

    text = str(order_number)
    probe = Image.new("1", (1, 1), color=1)
    probe_draw = ImageDraw.Draw(probe)
    text_bbox = probe_draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    top_padding = 4
    bottom_padding = 12
    canvas_height = max(26, text_height + top_padding + bottom_padding)

    img = Image.new("1", (PRINTER_WIDTH_PX, canvas_height), color=1)
    draw = ImageDraw.Draw(img)

    text_x = PRINTER_WIDTH_PX - text_width - text_bbox[0]
    text_y = top_padding - text_bbox[1]
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
        source_group_id = getattr(item, "_group_id", None)
        note_key = frozenset(item.selected_notes)
        key = (item.mode, item.dish_id, note_key)
        row = groups.get(key)
        if row is not None:
            row.count += 1
            if isinstance(source_group_id, int) and source_group_id >= 1:
                row.group_allocations[source_group_id] = row.group_allocations.get(source_group_id, 0) + 1
            continue
        allocations: dict[int, int] = {}
        if isinstance(source_group_id, int) and source_group_id >= 1:
            allocations[source_group_id] = 1
        groups[key] = _GroupedPrintRow(
            item=item,
            count=1,
            note_key=note_key,
            first_seen_index=idx,
            group_allocations=allocations,
        )

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


def _group_allocation_line(group_allocations: dict[int, int]) -> str:
    tokens: list[str] = []
    for group_id in sorted(group_allocations):
        count = group_allocations[group_id]
        if count <= 1:
            tokens.append(str(group_id))
        else:
            tokens.append(f"{group_id}x{count}")
    return " ".join(tokens)


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
    # Group-allocation line should be much smaller than item lines.
    # Set it to half of the current compact size.
    compact_base_size = max(14, PRINTER_FONT_SIZE - 16)
    compact_font_size = max(10, int(round(compact_base_size * (1 / 3))))
    compact_font = ImageFont.truetype(PRINTER_FONT_PATH, compact_font_size)
    header_font = ImageFont.truetype(PRINTER_FONT_PATH, max(20, PRINTER_FONT_SIZE - 20))
    grouped_items = _group_print_items(items)
    printer.image(_render_order_number_header(order_number, header_font))
    printed_s_separator = False

    for row in grouped_items:
        if row.item.mode == "S" and not printed_s_separator:
            _print_section_separator(printer)
            printed_s_separator = True

        line = _grouped_print_label(row.item, row.count)
        img = _render_line(line, font)
        printer.image(img)

        if row.group_allocations:
            allocation = _group_allocation_line(row.group_allocations)
            if allocation:
                printer.image(_render_compact_line(f"    {allocation}", compact_font))

        for note_label in _ordered_note_labels(row.note_key):
            note_line = _render_line(f"    {note_label}", font)
            printer.image(note_line)

    # Give single-line tickets a minimal extra tail for easier tearing.
    if len(grouped_items) == 1:
        printer.image(_render_spacer(PRINTER_SINGLE_ITEM_SPACER_PX))

    printer.cut()
