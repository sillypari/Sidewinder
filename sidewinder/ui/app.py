"""Sidewinder Main Textual Application.

The top-level App that wires together all screens, manages global state,
and handles slash commands. Uses Textual for full keyboard input handling.

Screens flow:
  MainMenuScreen -> ScanScreen -> TargetSelectScreen -> CaptureMethodScreen
               -> CaptureProgressScreen -> DeauthSelectScreen
               -> CrackProgressScreen -> ResultScreen

Global state lives here (session, adapters, scan engine).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from .screens import (
    AdapterScreen,
    CaptureMethodScreen,
    CrackProgressScreen,
    ErrorScreen,
    HelpScreen,
    MainMenuScreen,
    ResumeScreen,
    ResultScreen,
    ScanScreen,
)
from ..core.session import Session

logger = logging.getLogger(__name__)


SLASH_COMMANDS = {
    "/scan":     "Start WiFi scan",
    "/target":   "Select target network",
    "/capture":  "Start capture",
    "/crack":    "Start crack",
    "/cleanup":  "Cleanup & restore",
    "/help":     "Open help tutorial",
    "/status":   "Show current status",
    "/adapter":  "Switch adapter",
    "/quit":     "Exit Sidewinder",
}


class SidewinderApp(App):
    """Sidewinder WiFi Audit Tool — main application.

    Keyboard bindings (global):
      / — open command palette (slash commands)
      ? — open help screen
    """

    TITLE = "Sidewinder"
    SUB_TITLE = "Native Linux WiFi Audit Tool"
    CSS_PATH = "colors.tcss"
    dark = True

    BINDINGS = [
        Binding("question_mark", "help", "Help", show=True),
        Binding("slash", "command", "Command", show=True),
    ]

    def __init__(self, dev_mode: bool = False, session: Optional[Session] = None) -> None:
        super().__init__()
        self.dev_mode = dev_mode
        self.session: Session = session or Session()
        self._existing_session: Optional[Session] = session if session else None
        self._scan_engine = None
        self._adapter_manager = None
        self._service_manager = None
        self._cleanup_manager = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Footer()

    def on_mount(self) -> None:
        """Initialize adapters, install signal handlers, and show main menu."""
        self.push_screen(MainMenuScreen())
        asyncio.create_task(self._initialize())
        # Show resume prompt if previous session exists
        if self._existing_session:
            self.push_screen(ResumeScreen(self._existing_session))

    async def _initialize(self) -> None:
        """Discover adapters and initialize subsystems."""
        try:
            from ..adapters import AdapterManager
            from ..core.services import get_service_manager
            from ..core.cleanup import get_cleanup_manager

            self._adapter_manager = AdapterManager()
            await self._adapter_manager.discover()

            self._service_manager = get_service_manager()
            self._cleanup_manager = get_cleanup_manager()

            # Install signal handlers for graceful cleanup
            loop = asyncio.get_running_loop()
            self._cleanup_manager.install_signal_handlers(loop)

            logger.info(
                "Initialized with %d adapters",
                len(self._adapter_manager.adapters),
            )
        except Exception as e:
            logger.error("Initialization error: %s", e)

    def action_help(self) -> None:
        """Open help/tutorial screen."""
        self.push_screen(HelpScreen())

    def action_cleanup(self) -> None:
        """Run full cleanup (spawns async work as a task)."""
        if self._cleanup_manager:
            asyncio.ensure_future(self._run_cleanup())

    async def _run_cleanup(self) -> None:
        """Actual async cleanup work."""
        try:
            await self._cleanup_manager.full_cleanup()
            self.notify("Cleanup complete", severity="information")
        except Exception as e:
            self.notify(f"Cleanup failed: {e}", severity="error")

    def action_command(self) -> None:
        """Open command palette for slash commands."""
        from .screens import CommandPaletteScreen
        self.push_screen(CommandPaletteScreen())

    def show_error(self, severity: str, what: str, why: str, how: list[str], raw: str = "") -> None:
        """Push an error screen."""
        self.push_screen(ErrorScreen(
            severity=severity,
            what=what,
            why=why,
            how_to_fix=how,
            raw_error=raw,
        ))

    def notify_error(self, message: str) -> None:
        """Show a brief error notification (non-blocking)."""
        self.notify(message, severity="error")

    def get_status_line(self) -> str:
        """Generate status bar content."""
        parts = []
        if self._adapter_manager:
            best = self._adapter_manager.get_best_for_operation("capture")
            if best:
                parts.append(f"{best.iface}")
                parts.append(f"Ch:{best.current_mode}")
        parts.append("sidewinder v0.1")
        return " │ ".join(parts)
