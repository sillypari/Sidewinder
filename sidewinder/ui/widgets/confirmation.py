"""Sidewinder Confirmation Modal Dialog."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmationModal(ModalScreen[bool]):
    """Generic confirmation dialog."""

    DEFAULT_CSS = """
    ConfirmationModal {
        align: center middle;
        height: auto;
        & #confirmation-buttons {
            margin-top: 1;
            width: 100%;
            height: 3;
            align: center middle;
            & > Button {
                width: 1fr;
                margin: 0 1;
            }
        }
    }
    """

    BINDINGS = [
        Binding("left,right,up,down,h,j,k,l", "move_focus", "Navigate", show=False),
    ]

    def __init__(
        self,
        message: str,
        confirm_text: str = "Yes [y]",
        confirm_binding: str = "y",
        cancel_text: str = "No [n]",
        cancel_binding: str = "n",
        auto_focus: str = "confirm",
    ) -> None:
        super().__init__()
        self.message = message
        self.confirm_text = confirm_text
        self.cancel_text = cancel_text
        self.auto_focus = auto_focus
        self._confirm_binding = confirm_binding
        self._cancel_binding = cancel_binding

    def on_mount(self) -> None:
        self._bindings.bind(self._confirm_binding, "screen.dismiss(True)")
        self._bindings.bind(self._cancel_binding, "screen.dismiss(False)")
        self._bindings.bind("escape", "screen.dismiss(False)")
        if self.auto_focus:
            try:
                self.query_one(f"#{self.auto_focus}-button").focus()
            except Exception:
                pass

    def compose(self) -> ComposeResult:
        with Vertical(id="confirmation-screen", classes="modal-body") as container:
            container.border_title = "Confirm"
            yield Static(self.message)
            with Horizontal(id="confirmation-buttons"):
                yield Button(self.confirm_text, id="confirm-button")
                yield Button(self.cancel_text, id="cancel-button")
