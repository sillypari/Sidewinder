"""HelpScreen modal showing keybindings for widgets."""
from __future__ import annotations

from dataclasses import dataclass
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import DataTable, Label, Static


@dataclass
class HelpData:
    title: str
    description: str


class Helpable:
    help: HelpData


class HelpScreen(ModalScreen[None]):
    """Modal help screen showing widget-specific keybindings."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
        & > VerticalScroll {
            background: $background;
            padding: 1 2;
            width: 65%;
            height: 80%;
            border: tall $surface;
            border-title-color: $secondary;
            border-title-background: $background;
            border-title-style: bold;
        }
        & DataTable#bindings-table {
            width: 1fr;
            height: 1fr;
            margin-top: 1;
        }
        #footer-area {
            dock: bottom;
            height: auto;
            margin-top: 1;
            content-align: center middle;
            color: $foreground;
        }
    }
    """

    BINDINGS = [Binding("escape", "dismiss(None)", "Close Help")]

    def __init__(self, widget: Helpable) -> None:
        super().__init__()
        self.helpable = widget

    def compose(self) -> ComposeResult:
        with VerticalScroll() as vs:
            vs.border_title = getattr(self.helpable.help, "title", "Help")
            yield Static(getattr(self.helpable.help, "description", ""))

            table = DataTable(id="bindings-table", cursor_type="row", zebra_stripes=True)
            table.add_columns("Key", "Description")
            yield table
            yield Label("Press ESC to dismiss.", id="footer-area")

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        # Populate bindings table from self.helpable
        if hasattr(self.helpable, "BINDINGS"):
            for binding in self.helpable.BINDINGS:
                table.add_row(binding.key, binding.description)
        elif hasattr(self.helpable, "_bindings") and self.helpable._bindings:
            for binding in self.helpable._bindings.keys.values():
                table.add_row(binding.key, binding.description)
