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
    _OTHER_FACTORY_KIND = "other_factory"
    _BUILTIN_KIND = "builtin"
    _CUSTOM_KIND = "custom"

    def __init__(self, order: OrderEntry, on_change: Callable[[], None]) -> None:
        super().__init__()
        self.order = order
        self.on_change = on_change
        self.available_note_ids = available_notes_for_order(order)
        self.typing_other = False
        self.other_input_value = ""

    def compose(self) -> ComposeResult:
        with Container(id="notes-dialog"):
            yield Static("Notes", id="notes-title")
            yield Static(id="notes-body")
            yield Static(id="notes-help")

    def on_mount(self) -> None:
        self._refresh_content()

    def on_key(self, event) -> None:
        if not self.typing_other:
            return

        if event.key == "escape":
            self.typing_other = False
            self.other_input_value = ""
            self._refresh_content()
            event.stop()
            return

        if event.key == "enter":
            self._confirm_other_note()
            event.stop()
            return

        if event.key == "backspace":
            if self.other_input_value:
                self.other_input_value = self.other_input_value[:-1]
            self._refresh_content()
            event.stop()
            return

        if event.is_printable and event.character:
            self.other_input_value += event.character
            self._refresh_content()
            event.stop()
            return

        # Ignore all non-text keys while typing.
        event.stop()

    def action_close(self) -> None:
        if self.typing_other:
            self.typing_other = False
            self.other_input_value = ""
            self._refresh_content()
            return
        self.dismiss()
        self.on_change()

    def action_move_cursor(self, delta: int) -> None:
        if self.typing_other:
            return
        rows = self._rows()
        if not rows:
            return
        self.cursor_index = (self.cursor_index + delta) % len(rows)
        self._refresh_content()

    def action_toggle_current(self) -> None:
        rows = self._rows()
        if not rows:
            return
        row_kind, row_value = rows[self.cursor_index]

        if row_kind == self._OTHER_FACTORY_KIND:
            self.typing_other = True
            self.other_input_value = ""
            self._refresh_content()
            return

        if row_kind == self._BUILTIN_KIND:
            note_id = str(row_value)
            if note_id in self.order.selected_notes:
                self.order.selected_notes.remove(note_id)
            else:
                self.order.selected_notes.add(note_id)
            self._refresh_content()
            return

        if row_kind == self._CUSTOM_KIND:
            note_text = str(row_value)
            self.order.custom_notes = [n for n in self.order.custom_notes if n != note_text]
        self._refresh_content()

    def _rows(self) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        rows.extend((self._BUILTIN_KIND, note_id) for note_id in self.available_note_ids)
        rows.extend((self._CUSTOM_KIND, note_text) for note_text in self.order.custom_notes)
        rows.append((self._OTHER_FACTORY_KIND, "Other note"))
        return rows

    def _factory_row_index(self) -> int:
        return len(self._rows()) - 1

    def _confirm_other_note(self) -> None:
        normalized = self.other_input_value.strip()
        self.typing_other = False
        self.other_input_value = ""
        if not normalized:
            self.cursor_index = self._factory_row_index()
            self._refresh_content()
            return
        if normalized not in self.order.custom_notes:
            self.order.custom_notes.append(normalized)
        self.cursor_index = self._factory_row_index()
        self._refresh_content()

    def _refresh_content(self) -> None:
        body = self.query_one("#notes-body", Static)
        help_text = self.query_one("#notes-help", Static)

        content = Text(style="white")
        content.append_text(format_order_label(self.order))
        rows = self._rows()
        if self.cursor_index >= len(rows):
            self.cursor_index = max(0, len(rows) - 1)

        content.append("\n\n")
        for idx, (row_kind, row_value) in enumerate(rows):
            if idx > 0:
                content.append("\n")
            pointer = "➤ " if idx == self.cursor_index else "  "
            if row_kind == self._BUILTIN_KIND:
                note_id = row_value
                is_checked = note_id in self.order.selected_notes
                checked = "[x]" if is_checked else "[ ]"
                note_style = "bold white" if is_checked else "white"
                content.append(f"{pointer}{checked} {NOTE_CATALOG[note_id]}", style=note_style)
            elif row_kind == self._CUSTOM_KIND:
                note_style = "bold white"
                content.append(f"{pointer}[x] {row_value}", style=note_style)
            else:
                if self.typing_other and idx == self.cursor_index:
                    content.append(f"{pointer}[ ] Other note: {self.other_input_value}|", style="bold white")
                else:
                    content.append(f"{pointer}[ ] Other note", style="white")

        if self.typing_other:
            help_text.update("Type text, Enter confirm, Esc cancel typing")
        else:
            help_text.update("J/K/↑/↓ move, Enter toggle/add, Esc/q/Ctrl+C close")
        body.update(content)
