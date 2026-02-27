"""Printer integration based on test.py prototype."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
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
from app.data import NOTE_CATALOG, print_label_override_for_dish, print_note_alias_for_id, print_note_alias_for_text
from app.models import OrderEntry

# Separator tuning values.
# Keep these grouped so thermal-print behavior can be tuned in one place.
_SECTION_SEPARATOR_HEIGHT_PX = 20
_SECTION_SEPARATOR_THICKNESS_PX = 5
_SECTION_SEPARATOR_STRIPE_HEIGHT_PX = 2
_SECTION_SEPARATOR_PAUSE_SECONDS = 0.1
_BAG_INLINE_SEPARATOR_TOKEN = "__BAG_SEP__"
_BAG_OUTLINE_STROKE_PX = 2
_BAG_EAR_STROKE_PX = 2
_MAIN_TO_BAG_GAP_PX = 18
_BAG_TO_BAG_GAP_PX = 12
_HEADER_RIGHT_GUTTER_PX = 8
# Extra vertical headroom for full-size lines to avoid descender clipping on thermal output.
_MAIN_LINE_EXTRA_PX = 30
_FONT_OVERRIDE_ENV = "RECEIPT_PRINTER_FONT_PATH"
_LINUX_FONT_FALLBACKS = (
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
)


@dataclass
class _GroupedPrintRow:
    item: OrderEntry
    count: int
    note_key: frozenset[str]
    custom_note_key: frozenset[str]
    custom_notes_sorted: tuple[str, ...]
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


def resolve_printer_font_path() -> str:
    """
    Resolve a printer font path with macOS default behavior preserved.

    Resolution order:
    1. RECEIPT_PRINTER_FONT_PATH (if set)
    2. PRINTER_FONT_PATH
    3. Known Linux fallbacks
    """
    env_override = os.environ.get(_FONT_OVERRIDE_ENV, "").strip()
    candidates: list[str] = []
    if env_override:
        candidates.append(env_override)
    candidates.append(PRINTER_FONT_PATH)
    candidates.extend(_LINUX_FONT_FALLBACKS)

    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if Path(candidate).is_file():
            return candidate

    raise RuntimeError(
        f"No usable printer font found. Set {_FONT_OVERRIDE_ENV} to a valid .ttf/.otf file. "
        f"Tried: {', '.join(seen)}"
    )


def check_printer_dependencies() -> tuple[bool, str]:
    """Check whether printer dependencies are importable."""
    try:
        from escpos.printer import Usb  # noqa: F401
        from PIL import ImageFont
        font_path = resolve_printer_font_path()
        ImageFont.truetype(font_path, max(10, PRINTER_FONT_SIZE // 2))
    except Exception as exc:
        return (False, f"Printer deps unavailable: {exc}")
    return (True, "Printer ready")


def _render_line(text: str, font: object) -> object:
    from PIL import Image, ImageDraw

    canvas_height = PRINTER_FONT_SIZE + _MAIN_LINE_EXTRA_PX
    img = Image.new("1", (PRINTER_WIDTH_PX, canvas_height), color=1)
    draw = ImageDraw.Draw(img)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_height = bbox[3] - bbox[1]

    x = PRINTER_LEFT_INDENT_PX
    # Offset by bbox top so descenders (g, y, p, etc.) are not clipped.
    y = (canvas_height - text_height) // 2 - bbox[1]
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


def _fit_text_to_px(text: str, font: object, max_width_px: int) -> str:
    from PIL import Image, ImageDraw

    probe = Image.new("1", (1, 1), color=1)
    draw = ImageDraw.Draw(probe)
    if draw.textbbox((0, 0), text, font=font)[2] <= max_width_px:
        return text
    ellipsis = "..."
    trimmed = text
    while trimmed:
        candidate = f"{trimmed}{ellipsis}"
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width_px:
            return candidate
        trimmed = trimmed[:-1]
    return ellipsis


def _draw_bag_ear(draw: object, center_x: int, baseline_y: int, stroke_width: int = 1) -> int:
    """Draw a two-loop bag handle ear and return its height in pixels."""
    loop_width = 24
    loop_height = 12
    inner_gap = 4
    outer_stem_height = 4
    total_width = (loop_width * 2) + inner_gap
    left_outer = center_x - (total_width // 2)
    right_outer = left_outer + total_width
    left_loop = (left_outer, baseline_y - loop_height, left_outer + loop_width, baseline_y)
    right_loop = (right_outer - loop_width, baseline_y - loop_height, right_outer, baseline_y)

    # Outer stems anchor the ear to the top box border.
    draw.line(
        (left_outer, baseline_y, left_outer, baseline_y - outer_stem_height),
        fill=0,
        width=stroke_width,
    )
    draw.line(
        (right_outer, baseline_y, right_outer, baseline_y - outer_stem_height),
        fill=0,
        width=stroke_width,
    )
    # Two-loop handle using arcs.
    draw.arc(left_loop, 180, 0, fill=0, width=stroke_width)
    draw.arc(right_loop, 180, 0, fill=0, width=stroke_width)
    return loop_height


def _render_taw_bag_box(lines: list[str], font: object) -> object:
    from PIL import Image, ImageDraw

    if not lines:
        lines = [""]

    line_slot_px = PRINTER_FONT_SIZE + 20
    pad_x = 10
    pad_y = 8
    max_inner_width = max(120, PRINTER_WIDTH_PX - (PRINTER_LEFT_INDENT_PX * 2) - (pad_x * 2))

    safe_lines = []
    for line in lines:
        if line == _BAG_INLINE_SEPARATOR_TOKEN:
            safe_lines.append(line)
            continue
        safe_lines.append(_fit_text_to_px(line, font, max_inner_width))

    probe = Image.new("1", (1, 1), color=1)
    probe_draw = ImageDraw.Draw(probe)
    line_sizes = []
    for line in safe_lines:
        if line == _BAG_INLINE_SEPARATOR_TOKEN:
            line_sizes.append((max_inner_width, line_slot_px, 0))
            continue
        bbox = probe_draw.textbbox((0, 0), line, font=font)
        line_sizes.append((bbox[2] - bbox[0], bbox[3] - bbox[1], bbox[1], line_slot_px))

    content_width = max(width for width, *_ in line_sizes)
    content_height = line_slot_px * len(line_sizes)
    box_width = min(PRINTER_WIDTH_PX - (PRINTER_LEFT_INDENT_PX * 2), content_width + (pad_x * 2))
    x0 = PRINTER_LEFT_INDENT_PX
    x1 = x0 + box_width - 1

    ear_h = 12
    ear_margin = 2
    top_gap = ear_h + ear_margin

    y0 = top_gap
    y1 = y0 + (pad_y * 2) + content_height
    img_h = y1 + 4

    img = Image.new("1", (PRINTER_WIDTH_PX, img_h), color=1)
    draw = ImageDraw.Draw(img)

    draw.rectangle((x0, y0, x1, y1), outline=0, width=_BAG_OUTLINE_STROKE_PX)
    ear_center_x = x0 + (box_width // 2)
    _draw_bag_ear(draw, ear_center_x, y0, stroke_width=_BAG_EAR_STROKE_PX)

    y = y0 + pad_y
    text_x = x0 + pad_x
    for line, size in zip(safe_lines, line_sizes):
        if line == _BAG_INLINE_SEPARATOR_TOKEN:
            sep_h = 2
            sep_y = y + (line_slot_px - sep_h) // 2
            draw.rectangle((text_x, sep_y, x1 - pad_x, sep_y + sep_h - 1), fill=0)
        else:
            _, h, top, slot_h = size
            text_y = y + (slot_h - h) // 2
            # `top` adjusts for font ascent/descent baseline.
            draw.text((text_x, text_y - top), line, font=font, fill=0)
        y += line_slot_px

    return img


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


def _render_order_number_header(order_number: int, font: object, not_paid: bool = False) -> object:
    from PIL import Image, ImageDraw

    probe = Image.new("1", (1, 1), color=1)
    probe_draw = ImageDraw.Draw(probe)
    has_number = order_number > 0
    text = str(order_number) if has_number else ""
    text_bbox = probe_draw.textbbox((0, 0), text, font=font) if has_number else (0, 0, 0, 0)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    top_padding = 4
    bottom_padding = 12

    badge_font = None
    badge_text = "NOT PAID"
    badge_bbox = (0, 0, 0, 0)
    badge_height = 0
    if not_paid:
        try:
            badge_font = font.font_variant(size=max(10, int(font.size * 0.45)))
        except Exception:
            badge_font = font
        badge_bbox = probe_draw.textbbox((0, 0), badge_text, font=badge_font)
        badge_height = badge_bbox[3] - badge_bbox[1]

    content_height = max(text_height if has_number else 0, badge_height if not_paid else 0)
    canvas_height = max(26, content_height + top_padding + bottom_padding)

    img = Image.new("1", (PRINTER_WIDTH_PX, canvas_height), color=1)
    draw = ImageDraw.Draw(img)

    if has_number:
        text_x = PRINTER_WIDTH_PX - _HEADER_RIGHT_GUTTER_PX - text_width - text_bbox[0]
        text_y = top_padding - text_bbox[1]
        draw.text((text_x, text_y), text, font=font, fill=0)
    if not_paid:
        badge_x = PRINTER_LEFT_INDENT_PX
        badge_y = max(0, top_padding - badge_bbox[1])
        assert badge_font is not None
        draw.text((badge_x, badge_y), badge_text, font=badge_font, fill=0)
    return img


def _print_order_header_phase(printer: object, order_number: int, header_font: object, not_paid: bool) -> None:
    """Print the order header as an isolated first phase."""
    printer.image(_render_order_number_header(order_number, header_font, not_paid=not_paid))


def _category_rank(mode: str | None) -> int:
    if mode == "G":
        return 0
    if mode == "R":
        return 1
    if mode == "S":
        return 3
    return 2


def _group_print_items(items: list[OrderEntry]) -> list[_GroupedPrintRow]:
    """Group by mode+dish+exact built-in/custom note sets and then sort for print."""
    groups: dict[tuple[str | None, str, frozenset[str], frozenset[str], int | None], _GroupedPrintRow] = {}

    for idx, item in enumerate(items):
        source_group_id = getattr(item, "_group_id", None)
        note_key = frozenset(item.selected_notes)
        custom_note_key = frozenset(item.custom_notes)
        # `other_side` intentionally does not merge; each row prints individually.
        uniqueness = idx if item.dish_id == "other_side" else None
        key = (item.mode, item.dish_id, note_key, custom_note_key, uniqueness)
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
            custom_note_key=custom_note_key,
            custom_notes_sorted=tuple(sorted(custom_note_key)),
            first_seen_index=idx,
            group_allocations=allocations,
        )

    rows = list(groups.values())
    rows.sort(key=lambda row: (_category_rank(row.item.mode), -row.count, row.first_seen_index))
    return rows


def _ordered_note_labels(note_key: frozenset[str], custom_notes_sorted: tuple[str, ...]) -> list[str]:
    labels = [print_note_alias_for_id(note_id) for note_id in NOTE_CATALOG if note_id in note_key]
    labels.extend(
        aliased for aliased in (print_note_alias_for_text(note_text) for note_text in custom_notes_sorted) if aliased
    )
    return labels


def _grouped_print_label(item: OrderEntry, count: int) -> str:
    base = to_print_label(item)
    if count <= 1:
        return base
    return f"{base} {count}"


def _group_allocation_line(group_allocations: dict[int, int]) -> str:
    tokens: list[str] = []
    for group_id in sorted(group_allocations):
        count = group_allocations[group_id]
        if count <= 1:
            tokens.append(str(group_id))
        else:
            tokens.append(f"{group_id}x{count}")
    return " ".join(tokens)


def _takeaway_buckets(items: list[OrderEntry]) -> list[tuple[int | None, list[OrderEntry]]]:
    buckets: dict[int | None, list[OrderEntry]] = {}
    for item in items:
        if not item.is_takeaway:
            continue
        group_id = getattr(item, "_group_id", None)
        key = group_id if isinstance(group_id, int) and group_id >= 1 else None
        buckets.setdefault(key, []).append(item)
    grouped_keys = sorted(key for key in buckets if key is not None)
    ordered_keys = grouped_keys + ([None] if None in buckets else [])
    return [(key, buckets[key]) for key in ordered_keys]


def print_order_batch(items: list[OrderEntry], order_number: int, not_paid: bool = False) -> None:
    """Print all items in order and cut the ticket at the end."""
    if not items:
        return
    if not (0 <= order_number <= 1000):
        raise ValueError("order_number must be between 0 and 1000")

    try:
        from escpos.printer import Usb
        from PIL import ImageFont
    except Exception as exc:
        raise RuntimeError(f"Printer dependencies unavailable: {exc}") from exc

    printer = Usb(PRINTER_USB_VENDOR_ID, PRINTER_USB_PRODUCT_ID)
    font_path = resolve_printer_font_path()
    font = ImageFont.truetype(font_path, PRINTER_FONT_SIZE)
    # Group-allocation line should be much smaller than item lines.
    # Set it to half of the current compact size.
    compact_base_size = max(14, PRINTER_FONT_SIZE - 16)
    compact_font_size = max(10, int(round(compact_base_size * (1 / 3))))
    compact_font = ImageFont.truetype(font_path, compact_font_size)
    header_font = ImageFont.truetype(font_path, max(20, PRINTER_FONT_SIZE - 20))
    main_items = [item for item in items if not item.is_takeaway]
    takeaway_items = [item for item in items if item.is_takeaway]
    grouped_main_rows = _group_print_items(main_items)
    takeaway_buckets = _takeaway_buckets(takeaway_items)
    header_needed = (order_number > 0) or bool(not_paid)
    if header_needed:
        _print_order_header_phase(printer, order_number, header_font, not_paid)
    printed_main_s_separator = False

    for row in grouped_main_rows:
        if row.item.mode == "S" and not printed_main_s_separator:
            _print_section_separator(printer)
            printed_main_s_separator = True

        line = _grouped_print_label(row.item, row.count)
        img = _render_line(line, font)
        printer.image(img)

        if row.group_allocations:
            allocation = _group_allocation_line(row.group_allocations)
            if allocation:
                printer.image(_render_compact_line(f"    {allocation}", compact_font))

        for note_label in _ordered_note_labels(row.note_key, row.custom_notes_sorted):
            note_line = _render_line(f"    {note_label}", font)
            printer.image(note_line)

    for bag_idx, (group_id, bucket_items) in enumerate(takeaway_buckets):
        if bag_idx == 0 and grouped_main_rows:
            printer.image(_render_spacer(_MAIN_TO_BAG_GAP_PX))
        elif bag_idx > 0:
            printer.image(_render_spacer(_BAG_TO_BAG_GAP_PX))

        bag_rows = _group_print_items(bucket_items)
        bag_lines: list[str] = []
        printed_bag_s_separator = False
        for row in bag_rows:
            if row.item.mode == "S" and not printed_bag_s_separator:
                bag_lines.append(_BAG_INLINE_SEPARATOR_TOKEN)
                printed_bag_s_separator = True
            bag_lines.append(_grouped_print_label(row.item, row.count))
            for note_label in _ordered_note_labels(row.note_key, row.custom_notes_sorted):
                bag_lines.append(f"    {note_label}")
        printer.image(_render_taw_bag_box(bag_lines, font))
        if group_id is not None:
            printer.image(_render_compact_line(str(group_id), compact_font))

    # Give single-line tickets a minimal extra tail for easier tearing.
    bag_grouped_count_total = sum(len(_group_print_items(bucket_items)) for _, bucket_items in takeaway_buckets)
    if len(grouped_main_rows) == 1 or (len(grouped_main_rows) == 0 and bag_grouped_count_total == 1):
        printer.image(_render_spacer(PRINTER_SINGLE_ITEM_SPACER_PX))

    printer.cut()
