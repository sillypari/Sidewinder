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
from textual.widgets import Header

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
from .components import StatusBar
from ..core.session import Session
from ..core.config import SidewinderConfig

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
    "/session":  "Manage saved sessions",
    "/theme":    "Switch visual theme (opencode/classic)",
    "/compact":  "Toggle compact visual mode",
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
    theme = "midnight"
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

        self.settings = SidewinderConfig.load()
        from .theme_loader import register_themes
        register_themes(self, self.settings)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield StatusBar(id="global-status-bar")

    def on_mount(self) -> None:
        """Initialize adapters, install signal handlers, and show main menu."""
        try:
            self.theme = self.settings.theme
        except Exception:
            self.theme = "midnight"

        # Force refresh CSS and recompile layout to apply the loaded theme's colors
        self.refresh_css(animate=False)
        self.refresh(layout=True)

        self.push_screen(MainMenuScreen())
        asyncio.create_task(self._initialize())
        # Show resume prompt if previous session exists
        if self._existing_session:
            self.push_screen(ResumeScreen(self._existing_session))
        # Initial check
        self.call_after_refresh(self._check_size)
        # Start global status bar refresh timer
        self._status_timer = self.set_interval(2.0, self._update_global_status)

    def _update_global_status(self) -> None:
        """Refresh the global persistent status bar."""
        try:
            sbar = self.query_one("#global-status-bar", StatusBar)
            if self._adapter_manager:
                best = self._adapter_manager.get_best_for_operation("scan")
                if best:
                    sbar.adapter = best.iface
                    sbar.mode = best.current_mode
                    sbar.channel = "--"
        except Exception:
            pass

    def on_resize(self, event) -> None:
        self._check_size()

    def _check_size(self) -> None:
        w, h = self.size
        if w < 80 or h < 24:
            self.notify(
                f"Terminal too small ({w}x{h}). Minimum 80x24 required.",
                severity="error",
                timeout=10,
            )

    async def _initialize(self) -> None:
        """Discover adapters and initialize subsystems."""
        try:
            from ..adapters import AdapterManager
            from ..core.services import get_service_manager
            from ..core.cleanup import get_cleanup_manager

            self._adapter_manager = AdapterManager()
            await self._adapter_manager.discover()

            if self.dev_mode and not self._adapter_manager.adapters:
                from ..core.adapter import AdapterInfo
                mock_adapter = AdapterInfo(
                    iface="wlan0 (MOCK)",
                    chipset="RTL8812AU",
                    driver="8812au",
                    bands=["2.4G", "5G"],
                    monitor_capable=True,
                    injection_capable=True,
                    is_up=True,
                    current_mode="managed",
                    status="OPTIMIZED"
                )
                self._adapter_manager.adapters[mock_adapter.iface] = mock_adapter

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

    async def action_cleanup(self) -> None:
        """Run full cleanup."""
        if self._cleanup_manager:
            await self._run_cleanup()

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
        """Show error inside active screen's sidebar or fallback to ErrorScreen."""
        if self.screen and hasattr(self.screen, "show_sidebar_error"):
            self.screen.show_sidebar_error(severity, what, why, how, raw)
        else:
            from .screens import ErrorScreen
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

    def action_toggle_compact(self) -> None:
        """Toggle compact mode class on the app."""
        if self.has_class("-compact"):
            self.remove_class("-compact")
            self.notify("Compact mode disabled", severity="information")
        else:
            self.add_class("-compact")
            self.notify("Compact mode enabled", severity="information")

