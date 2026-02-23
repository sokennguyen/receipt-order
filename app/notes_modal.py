"""Notes modal screen."""

from __future__ import annotations

from typing import Callable

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Static

from app.data import NOTE_CATALOG
from app.models import OrderEntry
from app.rendering import available_notes_for_order, format_order_label


class NotesModal(ModalScreen[None]):
    """Centered modal to inspect and toggle available notes for one order."""

    BINDINGS = [
        ("escape", "close", "Close"),
        ("q", "close", "Close"),
        ("ctrl+c", "close", "Close"),
        ("j", "move_cursor(1)", "Next"),
        ("k", "move_cursor(-1)", "Previous"),
        ("up", "move_cursor(-1)", "Previous"),
        ("down", "move_cursor(1)", "Next"),
        ("enter", "toggle_current", "Toggle"),
    ]

    CSS = """
    NotesModal {
        align: center middle;
        background: $background 60%;
    }

    #notes-dialog {
        width: 64;
        height: auto;
        border: round $secondary;
        background: $panel;
        padding: 1 2;
    }

    #notes-title {
        text-style: bold;
        margin-bottom: 1;
        color: white;
    }

    #notes-body {
        margin-bottom: 1;
        color: white;
    }

    #notes-help {
        margin-top: 1;
        color: #dddddd;
    }
    """

    cursor_index = reactive(0)

    def __init__(self, order: OrderEntry, on_change: Callable[[], None]) -> None:
        super().__init__()
        self.order = order
        self.on_change = on_change
        self.available_note_ids = available_notes_for_order(order)

    def compose(self) -> ComposeResult:
        with Container(id="notes-dialog"):
            yield Static("Notes", id="notes-title")
            yield Static(id="notes-body")
            yield Static(id="notes-help")

    def on_mount(self) -> None:
        self._refresh_content()

    def action_close(self) -> None:
        self.dismiss()
        self.on_change()

    def action_move_cursor(self, delta: int) -> None:
        if not self.available_note_ids:
            return
        self.cursor_index = (self.cursor_index + delta) % len(self.available_note_ids)
        self._refresh_content()

    def action_toggle_current(self) -> None:
        if not self.available_note_ids:
            return
        note_id = self.available_note_ids[self.cursor_index]
        if note_id in self.order.selected_notes:
            self.order.selected_notes.remove(note_id)
        else:
            self.order.selected_notes.add(note_id)
        self._refresh_content()

    def _refresh_content(self) -> None:
        body = self.query_one("#notes-body", Static)
        help_text = self.query_one("#notes-help", Static)

        content = Text(style="white")
        content.append_text(format_order_label(self.order))

        if not self.available_note_ids:
            content.append("\n\nNo note options for this dish.", style="dim")
            help_text.update("Esc / q / Ctrl+C to close")
            body.update(content)
            return

        content.append("\n\n")
        for idx, note_id in enumerate(self.available_note_ids):
            if idx > 0:
                content.append("\n")
            pointer = "➤ " if idx == self.cursor_index else "  "
            is_checked = note_id in self.order.selected_notes
            checked = "[x]" if is_checked else "[ ]"
            note_style = "bold white" if is_checked else "white"
            content.append(f"{pointer}{checked} {NOTE_CATALOG[note_id]}", style=note_style)

        help_text.update("J/K/↑/↓ move, Enter toggle, Esc/q/Ctrl+C close")
        body.update(content)
