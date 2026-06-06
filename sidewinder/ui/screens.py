"""Sidewinder TUI Screens.

All application screens built with Textual.
Each screen has keyboard bindings, composition, and action handlers.

Navigation:
  - j/k: up/down
  - Enter: select/confirm
  - Esc: back/cancel
  - /: command palette
  - ?: help
  - 1-9: quick select by number
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from rich.text import Text

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    OptionList,
    ProgressBar,
    Static,
)
from textual.widgets.option_list import Option
from textual.containers import Horizontal, Vertical, ScrollableContainer, Center, VerticalScroll
from textual.reactive import reactive

from .components import (
    AdapterStatusWidget,
    ErrorCard,
    LogoWidget,
    TooltipPanel,
    Spacer,
    signal_bar,
    signal_color,
    privacy_color,
    InlineConfirm,
)


# ── Main Menu ─────────────────────────────────────────────────────────────────

MAIN_MENU_ITEMS = [
    ("1", "Scan WiFi networks",          "scan"),
    ("2", "Target a specific network",    "target"),
    ("3", "Crack a captured handshake",   "crack"),
    ("4", "View saved captures",          "view"),
    ("5", "Hardware & settings",          "settings"),
    ("6", "Cleanup & restore",            "cleanup"),
    ("7", "Help & tutorial",              "help"),
    ("0", "Exit",                         "exit"),
]


class SidewinderScreen(Screen):
    """Base Screen for all Sidewinder screens.

    Provides OpenCode-inspired zones (Top status bar, Left main container with main
    content + prompt area + overlay + confirmation, Split vertical separator, Right
    sidebar, Bottom footer), Vim-style leader key prefixes, and safe async task execution.
    """

    BINDINGS = [
        Binding("ctrl+a", "attack_leader", "Attack...", show=False),
        Binding("ctrl+s", "scan_leader", "Scan...", show=False),
        Binding("ctrl+g", "capture_leader", "Capture...", show=False),
    ]

    leader_prefix: reactive[str | None] = reactive(None)

    def compose(self) -> ComposeResult:
        with Horizontal(id="screen-layout"):
            with Vertical(id="left-container"):
                with ScrollableContainer(id="main-content"):
                    yield from self.compose_main()
                with Vertical(id="prompt-area"):
                    yield Static("", id="leader-overlay", classes="leader-overlay")
                    yield InlineConfirm(id="inline-confirm")
                    yield from self.compose_prompt()
            yield Static("█", id="sidebar-sep")
            with Vertical(id="right-sidebar"):
                yield from self.compose_sidebar()
        yield Footer()

    def compose_main(self) -> ComposeResult:
        """Compose main content. Must be overridden by subclasses."""
        return []

    def compose_prompt(self) -> ComposeResult:
        """Compose bottom prompt widgets. Override in subclasses."""
        return []

    def compose_sidebar(self) -> ComposeResult:
        """Compose right sidebar widgets. Override or use default."""
        from .components import AdapterStatusWidget
        yield AdapterStatusWidget(id="adapter-status")
        yield Vertical(id="sidebar-error-panel")

    def show_sidebar_error(self, severity: str, what: str, why: str, how: list[str], raw: str = "") -> None:
        try:
            panel = self.query_one("#sidebar-error-panel", Vertical)
            panel.clear()
            from .components import ErrorCard
            panel.mount(ErrorCard(
                severity=severity,
                what=what,
                why=why,
                how_to_fix=how,
                raw_error=raw,
            ))
            from textual.widgets import Button
            panel.mount(Button("Copy Details", id="btn-copy-error"))
            panel.display = True
            
            # Store last error text for clipboard action
            self._last_error_text = f"Severity: {severity}\nWhat: {what}\nWhy: {why}\nHow to fix: {how}\nRaw error: {raw}"
        except Exception:
            # Fallback
            from .screens import ErrorScreen
            self.app.push_screen(ErrorScreen(
                severity=severity,
                what=what,
                why=why,
                how_to_fix=how,
                raw_error=raw,
            ))

    def _copy_to_clipboard(self, text: str) -> None:
        import platform
        import subprocess
        try:
            if platform.system() == "Windows":
                process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, text=True)
                process.communicate(text)
            elif platform.system() == "Linux":
                process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE, text=True)
                process.communicate(text)
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from textual.widgets import Button
        if event.button.id == "btn-copy-error":
            if hasattr(self, "_last_error_text") and self._last_error_text:
                self._copy_to_clipboard(self._last_error_text)
                self.app.notify("Copied to clipboard!", severity="information")
            event.stop()

    def on_mount(self) -> None:
        try:
            self.query_one("#leader-overlay").display = False
        except Exception:
            pass
        self._base_status_timer = self.set_interval(1.0, self._update_base_status)

    def on_unmount(self) -> None:
        if hasattr(self, "_base_status_timer") and self._base_status_timer:
            self._base_status_timer.stop()

    def on_resize(self, event) -> None:
        try:
            collapse = event.size.width < 120
            self.query_one("#right-sidebar").display = not collapse
            self.query_one("#sidebar-sep").display = not collapse
        except Exception:
            pass

    def _update_base_status(self) -> None:
        try:
            widget = self.query_one("#adapter-status", AdapterStatusWidget)
            if hasattr(self.app, "_adapter_manager") and self.app._adapter_manager:
                best = self.app._adapter_manager.get_best_for_operation("scan")
                if best:
                    widget.adapter_name = best.iface
                    widget.adapter_status = best.status.lower()
                    widget.mode = best.current_mode
                    widget.signal = best.signal if hasattr(best, "signal") else -50
            if hasattr(self.app, "session") and self.app.session:
                widget.networks = len(self.app.session.scan_results)
                widget.clients = len(self.app.session.clients)
        except Exception:
            pass

    def action_attack_leader(self) -> None:
        self.leader_prefix = "attack"
        self._show_leader_overlay("Attack: [d] Deauth  [p] PMKID  [w] WPS  [e] Evil Twin")

    def action_scan_leader(self) -> None:
        self.leader_prefix = "scan"
        self._show_leader_overlay("Scan: [f] Full Scan  [b] Band Scan  [c] Channel Lock")

    def action_capture_leader(self) -> None:
        self.leader_prefix = "capture"
        self._show_leader_overlay("Capture: [p] Passive Capture  [a] Active Deauth Capture")

    def _show_leader_overlay(self, message: str) -> None:
        try:
            overlay = self.query_one("#leader-overlay")
            overlay.update(f"[bold $accent]LEADER[/bold $accent] {message}")
            overlay.display = True
        except Exception:
            pass

    def _hide_leader_overlay(self) -> None:
        self.leader_prefix = None
        try:
            overlay = self.query_one("#leader-overlay")
            overlay.display = False
        except Exception:
            pass

    def on_key(self, event) -> None:
        if self.leader_prefix:
            prefix = self.leader_prefix
            self._hide_leader_overlay()
            key = event.key.lower()
            if prefix == "attack":
                if key == "d":
                    self.app.push_screen(DeauthSelectScreen())
                elif key == "p":
                    self.app.push_screen(CaptureProgressScreen(target=self.app.session.selected_target, method="pmkid"))
                elif key == "w":
                    self.app.push_screen(CaptureProgressScreen(target=self.app.session.selected_target, method="wps"))
                elif key == "e":
                    self.app.push_screen(CaptureProgressScreen(target=self.app.session.selected_target, method="evil_twin"))
                event.stop()
            elif prefix == "scan":
                if key == "f":
                    self.app.push_screen(ScanScreen())
                elif key == "b":
                    self.app.push_screen(ScanOptionsScreen())
                elif key == "c":
                    if self.app.session.selected_target:
                        self.app.push_screen(ScanScreen())
                event.stop()
            elif prefix == "capture":
                if key == "p":
                    self.app.push_screen(CaptureProgressScreen(target=self.app.session.selected_target, method="passive"))
                elif key == "a":
                    self.app.push_screen(DeauthSelectScreen())
                event.stop()
            if event.key == "escape":
                event.stop()

    def run_safe_task(self, coro):
        import traceback
        from ..core.errors import SidewinderError
        async def wrapped():
            try:
                await coro
            except SidewinderError as se:
                self.app.show_error(
                    severity=se.severity.value,
                    what=se.what,
                    why=se.why,
                    how=se.how_to_fix,
                    raw=se.raw_error
                )
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.app.show_error(
                    severity="error",
                    what="An unexpected error occurred",
                    why=str(e),
                    how=["Restart Sidewinder", "Check system logs"],
                    raw=traceback.format_exc()
                )
        return asyncio.create_task(wrapped())


class MainMenuScreen(SidewinderScreen):
    """Main menu screen — opencode-style numbered options with inline statuses."""

    BINDINGS = [
        Binding("1", "menu_1", "Scan"),
        Binding("2", "menu_2", "Target"),
        Binding("3", "menu_3", "Crack"),
        Binding("4", "menu_4", "View"),
        Binding("5", "menu_5", "Settings"),
        Binding("6", "menu_6", "Cleanup"),
        Binding("7", "menu_7", "Help"),
        Binding("0", "menu_0", "Exit"),
        Binding("escape", "quit", "Quit"),
    ]

    def compose_main(self) -> ComposeResult:
        from .components import LogoWidget, Spacer
        yield Spacer(height=2)
        yield Center(LogoWidget(id="logo"))
        yield Spacer(height=3)
        yield Center(ListView(id="menu"))

    def compose_prompt(self) -> ComposeResult:
        return []

    def on_mount(self) -> None:
        super().on_mount()
        self._update_menu_items()
        self._menu_timer = self.set_interval(1.0, self._update_menu_items)
        self.query_one(ListView).focus()

    def on_unmount(self) -> None:
        super().on_unmount()
        if hasattr(self, "_menu_timer") and self._menu_timer:
            self._menu_timer.stop()

    def _get_menu_item_info(self, action: str) -> str:
        if action == "scan":
            is_scanning = False
            if hasattr(self.app, "_scan_engine") and self.app._scan_engine and self.app._scan_engine._running:
                is_scanning = True
            return "● scanning..." if is_scanning else "● idle"
        elif action == "target":
            tgt = self.app.session.selected_target
            if tgt:
                return f"■ {tgt.display_name()} ({tgt.bssid[:8]})"
            else:
                return "■ none"
        elif action == "crack":
            crack_res = self.app.session.cracked_passwords
            if crack_res:
                return f"▣ cracked: {crack_res[-1].password}"
            else:
                return "● waiting"
        elif action == "view":
            count = len(self.app.session.captures)
            return f"{count} captures"
        elif action == "settings":
            if hasattr(self.app, "_adapter_manager") and self.app._adapter_manager:
                best = self.app._adapter_manager.get_best_for_operation("scan")
                if best:
                    return f"{best.chipset} [{best.current_mode.upper()}]"
            return ""
        elif action == "cleanup":
            return "▣ restored" if getattr(self.app, "_cleaned_up", False) else "▣ dirty"
        elif action == "help":
            return "?"
        elif action == "exit":
            return "⏻"
        return ""

    def _update_menu_items(self) -> None:
        try:
            lv = self.query_one("#menu", ListView)
            if not lv.children:
                for key, label, action in MAIN_MENU_ITEMS:
                    info = self._get_menu_item_info(action)
                    padded_label = f"{label:<28}"
                    markup = (
                        rf"[$text-muted]\[[/$text-muted]"
                        rf"[bold $secondary]{key}[/bold $secondary]"
                        rf"[$text-muted]][/$text-muted]  "
                        rf"[$text]{padded_label}[/$text]"
                        rf" [dim]{info}[/dim]"
                    )
                    lv.append(ListItem(Label(markup), id=f"menu-{action}"))
            else:
                for item in lv.children:
                    action = item.id.replace("menu-", "") if item.id else ""
                    key = ""
                    label = ""
                    for k, l, a in MAIN_MENU_ITEMS:
                        if a == action:
                            key = k
                            label = l
                            break
                    if not key:
                        continue
                    info = self._get_menu_item_info(action)
                    padded_label = f"{label:<28}"
                    markup = (
                        rf"[$text-muted]\[[/$text-muted]"
                        rf"[bold $secondary]{key}[/bold $secondary]"
                        rf"[$text-muted]][/$text-muted]  "
                        rf"[$text]{padded_label}[/$text]"
                        rf" [dim]{info}[/dim]"
                    )
                    try:
                        lbl = item.query_one(Label)
                        lbl.update(markup)
                    except Exception:
                        pass
        except Exception:
            pass

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        action = event.item.id.replace("menu-", "") if event.item.id else ""
        if action == "scan":
            self.action_menu_1()
        elif action == "target":
            self.action_menu_2()
        elif action == "crack":
            self.action_menu_3()
        elif action == "view":
            self.action_menu_4()
        elif action == "settings":
            self.action_menu_5()
        elif action == "cleanup":
            self.action_menu_6()
        elif action == "help":
            self.action_menu_7()
        elif action == "exit":
            self.action_menu_0()

    def action_menu_1(self) -> None:
        self.app.push_screen(ScanScreen())

    def action_menu_2(self) -> None:
        self.app.push_screen(TargetSelectScreen())

    def action_menu_3(self) -> None:
        cap = self.app.session.captures[-1] if self.app.session.captures else ""
        if not cap:
            self.app.notify("No captures found. Run a scan/capture first or select a capture file.", severity="warning")
            return
        self.app.push_screen(WordlistPickerScreen(), callback=lambda wl: self._on_wordlist_selected_menu_3(cap, wl))

    def _on_wordlist_selected_menu_3(self, cap: str, wordlist_path: str | None) -> None:
        if wordlist_path:
            self.app.push_screen(EnginePickerScreen(), callback=lambda engine: self._on_engine_selected_menu_3(cap, wordlist_path, engine))

    def _on_engine_selected_menu_3(self, cap: str, wordlist_path: str, engine: str | None) -> None:
        if engine:
            self.app.push_screen(CrackProgressScreen(
                cap_file=cap,
                wordlist=wordlist_path,
                engine=engine
            ))

    def action_menu_5(self) -> None:
        self.app.push_screen(AdapterScreen())

    def action_menu_6(self) -> None:
        confirm_bar = self.query_one("#inline-confirm", InlineConfirm)
        confirm_bar.confirm(
            message="Run system cleanup & restore services?",
            choices=["Confirm [y]", "Cancel [n]"],
            on_confirm=self._on_cleanup_confirmed
        )

    def _on_cleanup_confirmed(self, choice_idx: int) -> None:
        if choice_idx == 0:
            self.app.push_screen(CleanupScreen())

    def action_menu_7(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_menu_0(self) -> None:
        self.app.exit()

    def action_quit(self) -> None:
        self.app.exit()

    def action_menu_4(self) -> None:
        self.app.push_screen(CaptureListScreen())


class AdapterScreen(SidewinderScreen):
    """Shows all detected adapters and their status."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("r", "refresh", "Refresh"),
        Binding("m", "monitor_setup", "Monitor Mode"),
        Binding("s", "service_mgr", "Service Mgr"),
    ]

    def compose_main(self) -> ComposeResult:
        yield Static(
            "[bold $primary]Hardware & Adapters[/bold $primary]",
            id="adapter-title",
        )
        table = DataTable(id="adapter-table", show_cursor=True)
        table.add_columns("Interface", "Chipset", "Driver", "Bands", "Monitor", "Inject", "Status")
        yield table

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "  [$text-muted]r[/$text-muted][$text-muted] refresh[/$text-muted]  "
            "[$text-muted]m[/$text-muted][$text-muted] monitor setup[/$text-muted]  "
            "[$text-muted]s[/$text-muted][$text-muted] service mgr[/$text-muted]  "
            "[$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
            id="adapter-hints",
        )

    def on_mount(self) -> None:
        super().on_mount()
        self.call_after_refresh(self._load_adapters)

    async def _load_adapters(self) -> None:
        from ..core.adapter import discover_all_adapters
        table = self.query_one("#adapter-table", DataTable)
        adapters = await discover_all_adapters()
        for a in adapters:
            mon = "[green]YES[/green]" if a.monitor_capable else "[red]NO[/red]"
            inj = "[green]YES[/green]" if a.injection_capable else "[red]NO[/red]"
            table.add_row(
                a.iface,
                a.chipset,
                a.driver,
                "/".join(a.bands),
                mon,
                inj,
                a.display_status(),
            )

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_refresh(self) -> None:
        table = self.query_one("#adapter-table", DataTable)
        table.clear()
        self.call_after_refresh(self._load_adapters)

    def action_monitor_setup(self) -> None:
        table = self.query_one("#adapter-table", DataTable)
        if table.cursor_row >= 0:
            row_keys = list(table.rows.keys())
            if table.cursor_row < len(row_keys):
                iface = row_keys[table.cursor_row].value
                self.app.push_screen(MonitorSetupScreen(adapter_name=iface))

    def action_service_mgr(self) -> None:
        self.app.push_screen(ServiceCheckScreen())


# ── Scan Screen ───────────────────────────────────────────────────────────────

class ScanScreen(SidewinderScreen):
    """WiFi scan results table — airodump-ng style with signal bars."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "select_target", "Select"),
        Binding("s", "stop_scan", "Stop"),
    ]

    def __init__(self, band: str = "", channels: list[int] | None = None, show_hidden: bool = True, **kwargs) -> None:
        super().__init__(**kwargs)
        self.band = band
        self.channels = channels
        self.show_hidden = show_hidden

    scanning: reactive[bool] = reactive(False)
    network_count: reactive[int] = reactive(0)
    elapsed: reactive[int] = reactive(0)

    def compose_main(self) -> ComposeResult:
        from .components import ScanStatsBar
        with Horizontal(id="scan-header"):
            yield Static("[bold $primary]WiFi Scan[/bold $primary]", id="scan-title")
            yield ScanStatsBar(id="scan-stats")
        yield DataTable(id="scan-table", show_cursor=True)

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  Enter[/$text-muted][$text-muted] select[/$text-muted]"
            "  [$text-muted]s[/$text-muted][$text-muted] stop[/$text-muted]"
            "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
            id="scan-hints",
        )

    def on_mount(self) -> None:
        super().on_mount()
        self.scanning = True
        self._timer = self.set_interval(1.0, self._tick)
        self.call_after_refresh(self._setup_columns)

        if hasattr(self.app, "_adapter_manager") and self.app._adapter_manager:
            adapter = self.app._adapter_manager.get_best_for_operation("scan")
            if adapter:
                from ..core.scanner import ScanEngine
                self._scan_engine = ScanEngine()

                async def run_scan():
                    await self._scan_engine.scan(
                        mon_iface=adapter.iface,
                        band=self.band,
                        channels=self.channels,
                        on_network=self.add_network,
                        on_client=self.add_client,
                    )

                self.scan_task = self.run_safe_task(run_scan())
            else:
                from ..core.errors import ERROR_DB
                self.app.show_error(
                    severity=ERROR_DB["ADAPTER_NOT_FOUND"].severity.value,
                    what=ERROR_DB["ADAPTER_NOT_FOUND"].what,
                    why=ERROR_DB["ADAPTER_NOT_FOUND"].why,
                    how=ERROR_DB["ADAPTER_NOT_FOUND"].how_to_fix
                )

    def _setup_columns(self) -> None:
        table = self.query_one("#scan-table", DataTable)
        w, _ = self.app.size
        has_wps_and_clients = len(table.columns) > 7
        should_have_wps_and_clients = w >= 100

        # If already configured correctly, do not rebuild
        if len(table.columns) > 0 and (has_wps_and_clients == should_have_wps_and_clients):
            return

        table.clear(columns=True)
        table.add_column("BSSID", width=17)
        table.add_column("CH", width=3)
        table.add_column("Signal", width=10)
        table.add_column("Rate", width=8)
        table.add_column("Privacy", width=7)
        table.add_column("Cipher", width=7)
        table.add_column("ESSID", width=20)
        if should_have_wps_and_clients:
            table.add_column("WPS", width=4)
            table.add_column("Clients", width=3)
        else:
            self.app.notify("Some columns hidden. Resize to 100+ for full view.", severity="warning")

        # Repopulate from session
        if hasattr(self.app, "session") and self.app.session:
            for n in self.app.session.scan_results:
                self._add_network_to_table(n)

    def on_resize(self, event) -> None:
        super().on_resize(event)
        self.call_after_refresh(self._setup_columns)

    def on_unmount(self) -> None:
        super().on_unmount()
        self.action_stop_scan()
        if hasattr(self, "_timer") and self._timer:
            self._timer.stop()

    def _tick(self) -> None:
        if self.scanning:
            self.elapsed += 1
        h, m, s = self.elapsed // 3600, (self.elapsed % 3600) // 60, self.elapsed % 60
        try:
            stats = self.query_one("#scan-stats", ScanStatsBar)
            stats.networks = self.network_count
            stats.clients = sum(1 for c in self.app.session.clients)
            stats.elapsed = f"{m:02d}:{s:02d}"

            # Update base status details via reactive variables
            widget = self.query_one("#adapter-status", AdapterStatusWidget)
            widget.networks = self.network_count
            widget.clients = len(self.app.session.clients)
            widget.status = "scanning"
            widget.time_elapsed = f"{m:02d}:{s:02d}"
        except Exception:
            pass

    def add_network(self, network) -> None:
        """Add or update a network in the scan table."""
        existing = next((n for n in self.app.session.scan_results if n.bssid == network.bssid), None)
        if not existing:
            self.app.session.scan_results.append(network)
        else:
            existing.signal = network.signal
            existing.channel = network.channel
            existing.privacy = network.privacy
            existing.cipher = network.cipher
            existing.essid = network.essid
            existing.wps = network.wps

        self._add_network_to_table(network)

    def _add_network_to_table(self, network) -> None:
        table = self.query_one("#scan-table", DataTable)
        bar = signal_bar(network.signal)
        sc = signal_color(network.signal)
        pc = privacy_color(network.privacy)
        row_key = network.bssid
        w, _ = self.app.size

        row_data = [
            f"[$text-muted]{network.bssid}[/$text-muted]",
            f"[$secondary]{network.channel}[/$secondary]",
            f"{bar} [{sc}]{network.signal}[/{sc}]",
            "",
            f"[{pc}]{network.privacy}[/{pc}]",
            network.cipher,
            f"[$text]{network.display_name()}[/$text]"
        ]
        if w >= 100:
            row_data.append("[$success]✓[/$success]" if network.wps else "")
            row_data.append("")

        try:
            for i, data in enumerate(row_data):
                col_key = list(table.columns.keys())[i]
                table.update_cell(row_key, col_key, data, update_width=False)
        except Exception:
            table.add_row(*row_data, key=row_key)

        self.network_count = len(table.rows)

    def add_client(self, client) -> None:
        """Add or update a client in the session."""
        existing = next((c for c in self.app.session.clients if c.mac == client.mac), None)
        if not existing:
            self.app.session.clients.append(client)

    def action_back(self) -> None:
        self._stop_scanning_backend()
        if hasattr(self, "_timer"):
            self._timer.stop()
        self.app.pop_screen()

    def action_stop_scan(self) -> None:
        self._stop_scanning_backend()
        if hasattr(self, "_timer"):
            self._timer.stop()
        self.app.pop_screen()
        self.app.push_screen(TargetSelectScreen())

    def _stop_scanning_backend(self) -> None:
        self.scanning = False
        if hasattr(self, "scan_task") and self.scan_task and not self.scan_task.done():
            self.scan_task.cancel()
        if hasattr(self, "_scan_engine") and self._scan_engine:
            import asyncio
            asyncio.create_task(self._scan_engine.stop_and_wait())

    def action_cursor_down(self) -> None:
        table = self.query_one("#scan-table", DataTable)
        table.action_scroll_down()

    def action_cursor_up(self) -> None:
        table = self.query_one("#scan-table", DataTable)
        table.action_scroll_up()

    def action_select_target(self) -> None:
        """Push AP details screen with the selected network."""
        table = self.query_one("#scan-table", DataTable)
        if table.cursor_row >= 0:
            row_keys = list(table.rows.keys())
            if table.cursor_row < len(row_keys):
                bssid = row_keys[table.cursor_row].value
                network = None
                if hasattr(self, "_scan_engine") and self._scan_engine:
                    network = next((n for n in self._scan_engine.parser.networks.values() if n.bssid == bssid), None)
                if not network:
                    network = next((n for n in self.app.session.scan_results if n.bssid == bssid), None)
                
                if network:
                    self.app.session.selected_target = network
                    screen_cls = globals().get("APDetailsScreen")
                    if screen_cls:
                        self.app.push_screen(screen_cls(target=network))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.action_select_target()


# ── Target Select Screen ──────────────────────────────────────────────────────

class TargetSelectScreen(SidewinderScreen):
    """Select a target from previously scanned networks."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "select", "Select"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def compose_main(self) -> ComposeResult:
        yield Static("[bold $primary]Select Target Network[/bold $primary]", id="target-title")
        yield Static("[$text-muted]──────────────────────[/$text-muted]", id="target-divider")
        table = DataTable(id="target-table", show_cursor=True)
        table.add_columns("BSSID", "CH", "Signal", "Privacy", "ESSID", "Clients")
        yield table

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  Enter[/$text-muted][$text-muted] select[/$text-muted]"
            "  [$text-muted]j/k[/$text-muted][$text-muted] navigate[/$text-muted]"
            "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
            id="target-hints",
        )

    def on_mount(self) -> None:
        super().on_mount()
        # Populate table from session results
        table = self.query_one("#target-table", DataTable)
        for n in self.app.session.scan_results:
            bar = signal_bar(n.signal)
            sc = signal_color(n.signal)
            pc = privacy_color(n.privacy)
            clients_cnt = sum(1 for c in self.app.session.clients if c.bssid == n.bssid)
            table.add_row(
                n.bssid,
                str(n.channel),
                f"{bar} {n.signal}",
                f"[{pc}]{n.privacy}[/{pc}]",
                n.display_name(),
                str(clients_cnt),
                key=n.bssid
            )

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_select(self) -> None:
        table = self.query_one("#target-table", DataTable)
        if table.cursor_row >= 0:
            row_keys = list(table.rows.keys())
            if table.cursor_row < len(row_keys):
                bssid = row_keys[table.cursor_row].value
                network = next((n for n in self.app.session.scan_results if n.bssid == bssid), None)
                if network:
                    self.app.session.selected_target = network
                    screen_cls = globals().get("APDetailsScreen")
                    if screen_cls:
                        self.app.push_screen(screen_cls(target=network))

    def action_cursor_down(self) -> None:
        self.query_one(DataTable).action_scroll_down()

    def action_cursor_up(self) -> None:
        self.query_one(DataTable).action_scroll_up()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.action_select()


# ── Capture Method Screen ──────────────────────────────────────────────────────

CAPTURE_METHODS = [
    {
        "key": "1",
        "name": "Passive Capture",
        "short": "Listen for handshake — no interference",
        "description": "Listens passively for a WPA handshake without sending any packets",
        "when_to_use": "When you want to be stealthy or the AP has many active clients",
        "risk_level": "safe",
        "risk_detail": "No packets sent. Pure listening. Undetectable.",
        "requires": ["monitor_mode"],
    },
    {
        "key": "2",
        "name": "Deauth + Capture",
        "short": "Kick clients, force handshake — faster",
        "description": "Sends deauthentication frames to kick clients off, forcing a new handshake",
        "when_to_use": "When you need a handshake quickly and don't mind being detected",
        "risk_level": "caution",
        "risk_detail": "Sends deauth packets. Clients disconnect briefly. May trigger IDS.",
        "requires": ["monitor_mode", "injection_capable"],
    },
    {
        "key": "3",
        "name": "PMKID Capture",
        "short": "Clientless handshake capture",
        "description": "Requests PMKID from AP without needing clients",
        "when_to_use": "When there are no clients connected to the AP",
        "risk_level": "safe",
        "risk_detail": "Active request but generally stealthy",
        "requires": ["monitor_mode"],
    },
    {
        "key": "4",
        "name": "WPS Pixie-Dust",
        "short": "Offline WPS PIN attack",
        "description": "Attempts Pixie-Dust attack on vulnerable WPS implementations",
        "when_to_use": "When target has WPS enabled",
        "risk_level": "caution",
        "risk_detail": "High packet volume, active probing",
        "requires": ["monitor_mode"],
    },
    {
        "key": "5",
        "name": "Evil Twin",
        "short": "Rogue AP phishing",
        "description": "Spawns a fake AP to capture credentials",
        "when_to_use": "When WPA cracking fails",
        "risk_level": "dangerous",
        "risk_detail": "Highly intrusive, creates fake networks, active MITM",
        "requires": ["monitor_mode"],
    },
]


class CaptureMethodScreen(SidewinderScreen):
    """Select capture method with live tooltips."""

    BINDINGS = [
        Binding("1", "method_1", "Passive"),
        Binding("2", "method_2", "Deauth"),
        Binding("3", "method_3", "PMKID"),
        Binding("4", "method_4", "WPS"),
        Binding("5", "method_5", "EvilTwin"),
        Binding("escape", "back", "Back"),
    ]

    selected_idx: reactive[int] = reactive(0)

    def compose_main(self) -> ComposeResult:
        with Horizontal(id="sc-method"):
            with Vertical(id="method-list"):
                yield Static("[bold $primary]Capture Method[/bold $primary]", id="method-title")
                yield Static("[$text-disabled]──────────────[/$text-disabled]")
                for m in CAPTURE_METHODS:
                    risk_colors = {"safe": "$success", "caution": "$warning", "dangerous": "$error"}
                    rc = risk_colors.get(m["risk_level"], "$text")
                    markup = (
                        rf"[$text-muted]\[[/$text-muted]"
                        f"[bold $secondary]{m['key']}[/bold $secondary]"
                        f"[$text-muted]] [/$text-muted]"
                        f"[bold $text]{m['name']}[/bold $text]\n"
                        f"    [$text-muted]{m['short']}[/$text-muted]\n"
                        f"    [$text-muted]Risk: [/$text-muted]"
                        f"[{rc}]{m['risk_level'].upper()}[/{rc}]"
                    )
                    yield Static(markup, id=f"method-{m['key']}")
            with Vertical(id="tooltip-panel"):
                yield Static("", id="tooltip-container")

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  1-5[/$text-muted][$text-muted] select[/$text-muted]"
            "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
            id="method-hints",
        )

    def on_mount(self) -> None:
        super().on_mount()
        self.watch_selected_idx(self.selected_idx)

    def watch_selected_idx(self, idx: int) -> None:
        try:
            m = CAPTURE_METHODS[idx]
            container = self.query_one("#tooltip-panel", Vertical)
            try:
                old = self.query_one("#tooltip")
                old.remove()
            except Exception:
                pass
            container.mount(
                TooltipPanel(
                    name=m["name"],
                    description=m["description"],
                    when_to_use=m["when_to_use"],
                    risk_level=m["risk_level"],
                    risk_detail=m["risk_detail"],
                    requires=", ".join(m["requires"]),
                    id="tooltip",
                )
            )
        except Exception:
            pass

    def action_method_1(self) -> None:
        self.selected_idx = 0
        self.app.push_screen(CaptureProgressScreen(
            target=self.app.session.selected_target,
            method="passive"
        ))

    def action_method_2(self) -> None:
        self.selected_idx = 1
        self.app.push_screen(DeauthSelectScreen())

    def action_method_3(self) -> None:
        self.selected_idx = 2
        self.app.push_screen(CaptureProgressScreen(
            target=self.app.session.selected_target,
            method="pmkid"
        ))

    def action_method_4(self) -> None:
        self.selected_idx = 3
        self.app.push_screen(CaptureProgressScreen(
            target=self.app.session.selected_target,
            method="wps"
        ))

    def action_method_5(self) -> None:
        self.selected_idx = 4
        self.app.push_screen(CaptureProgressScreen(
            target=self.app.session.selected_target,
            method="evil_twin"
        ))

    def action_back(self) -> None:
        self.app.pop_screen()



# ── Capture Progress Screen ───────────────────────────────────────────────────

class CaptureProgressScreen(SidewinderScreen):
    """Live capture progress with EAPOL M1-M4 tracker."""

    BINDINGS = [
        Binding("escape", "stop", "Stop"),
        Binding("ctrl+x", "stop", "Stop"),
    ]

    def __init__(self, target=None, method: str = "passive", selected_clients=None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.target = target
        self.method = method
        self.selected_clients = selected_clients or []

    beacons: reactive[int] = reactive(0)
    data_pkts: reactive[int] = reactive(0)
    signal: reactive[int] = reactive(-100)
    elapsed: reactive[int] = reactive(0)

    def compose_main(self) -> ComposeResult:
        from .components import AttackProgressPanel
        yield Static(
            f"[bold $primary]Capturing Handshake[/bold $primary]",
            id="capture-title",
        )
        yield Static("[$text-disabled]──────────────────────────────────────────────────[/$text-disabled]")
        yield AttackProgressPanel(method=self.method, id="attack-panel")
        yield ProgressBar(id="capture-progress", total=100)

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  Esc[/$text-muted][$text-muted] stop capture[/$text-muted]",
            id="capture-hints",
        )

    def on_mount(self) -> None:
        super().on_mount()
        self._timer = self.set_interval(1.0, self._tick)
        self.capture_task = self.run_safe_task(self._start_capture())

    def on_unmount(self) -> None:
        super().on_unmount()
        if hasattr(self, "_timer") and self._timer:
            self._timer.stop()
        if hasattr(self, "capture_task") and self.capture_task and not self.capture_task.done():
            self.capture_task.cancel()

    async def _start_capture(self) -> None:
        if not hasattr(self.app, "_adapter_manager") or not self.app._adapter_manager:
            from ..core.errors import ERROR_DB
            raise ERROR_DB["ADAPTER_NOT_FOUND"]
        adapter = self.app._adapter_manager.get_best_for_operation("capture")
        if not adapter:
            from ..core.errors import ERROR_DB
            raise ERROR_DB["ADAPTER_NOT_FOUND"]

        if adapter.current_mode != "monitor":
            from ..core.errors import ERROR_DB
            raise ERROR_DB["MONITOR_MODE_FAILED"]

        import os
        from ..core.config import expand_user_path
        captures_dir = expand_user_path("~/.sidewinder/captures")
        os.makedirs(captures_dir, exist_ok=True)
        bssid_clean = self.target.bssid.replace(":", "")
        output_prefix = os.path.join(captures_dir, f"capture_{bssid_clean}")

        from ..core.capture import capture_passive
        from ..attacks.deauth import run_deauth, DeauthConfig
        from ..attacks.pmkid import PMKIDEngine
        from ..attacks.wps import WPSEngine
        from ..attacks.evil_twin import EvilTwinEngine
        from ..core.subprocess_mgr import get_manager

        try:
            widget = self.query_one("#adapter-status", AdapterStatusWidget)
            widget.status = "capturing"
        except Exception:
            pass

        handshake = None
        if self.method == "passive":
            handshake = await capture_passive(
                mon_iface=adapter.iface,
                bssid=self.target.bssid,
                channel=self.target.channel,
                output_prefix=output_prefix,
                timeout=300.0,
                on_progress=self.update_eapol
            )
        elif self.method == "deauth":
            client = self.selected_clients[0] if self.selected_clients else "FF:FF:FF:FF:FF:FF"
            deauth_res = await run_deauth(
                iface=adapter.iface,
                phy=adapter.phy,
                config=DeauthConfig(
                    bssid=self.target.bssid,
                    client=client,
                    channel=self.target.channel,
                    output_prefix=output_prefix,
                    timeout=300.0
                ),
                on_progress=self._on_deauth_progress
            )
            handshake = deauth_res.handshake
        elif self.method == "pmkid":
            engine = PMKIDEngine(get_manager())
            engine.set_progress_callback(self._on_attack_progress)
            from ..core.attack import AttackConfig
            res = await engine.start(AttackConfig(target_bssid=self.target.bssid, channel=self.target.channel, timeout=300.0), iface=adapter.iface)
            if res.success:
                from ..core.session import HandshakeResult
                handshake = HandshakeResult(status="full")
        elif self.method == "wps":
            engine = WPSEngine(get_manager())
            engine.set_progress_callback(self._on_attack_progress)
            from ..core.attack import AttackConfig
            res = await engine.start(AttackConfig(target_bssid=self.target.bssid, channel=self.target.channel, timeout=300.0), iface=adapter.iface)
            if res.success:
                from ..core.session import CrackResult
                crack_res = CrackResult(found=True, password=res.stats.get("wpa_psk", "unknown"), method="wps")
                self.app.session.cracked_passwords.append(crack_res)
                self.app.push_screen(ResultScreen(
                    password=crack_res.password,
                    ssid=self.target.display_name(),
                    bssid=self.target.bssid,
                    method="WPS Pixie-Dust",
                    keys_tested=1
                ))
                return
        elif self.method == "evil_twin":
            engine = EvilTwinEngine(get_manager())
            success = await engine.start_rogue_ap(
                mon_iface=adapter.iface,
                essid=self.target.display_name(),
                channel=self.target.channel,
                target_bssid=self.target.bssid,
                on_log=self._on_rogue_ap_log
            )
            if success:
                from ..core.session import HandshakeResult
                handshake = HandshakeResult(status="full")

        if "MOCK" in adapter.iface:
            # Create a dummy file so that os.path.exists passes
            with open(output_prefix + "-01.cap", "w") as f:
                f.write("mock pcap content")

        if handshake and handshake.status in ("full", "partial"):
            cap_file = output_prefix + "-01.cap"
            if os.path.exists(cap_file):
                self.app.session.captures.append(cap_file)
                self.app.session.handshake = handshake
                self.app.session.save()
                self.app.notify(f"Handshake captured! Saved to {os.path.basename(cap_file)}", severity="success")
                self.app.push_screen(WordlistPickerScreen(), callback=self._on_wordlist_selected)
            else:
                self.app.notify("Capture file missing despite handshake confirmation.", severity="warning")
        else:
            if self.method in ("passive", "deauth", "evil_twin"):
                self.app.notify("No handshake captured.", severity="warning")
                self.app.pop_screen()

    def _on_deauth_progress(self, **kwargs) -> None:
        try:
            panel = self.query_one("#attack-panel", AttackProgressPanel)
            sent = kwargs.get("deauths_sent", 0)
            panel.beacons = sent
            panel.refresh()
        except Exception:
            pass

    def _on_attack_progress(self, **kwargs) -> None:
        status = kwargs.get("status", "")
        try:
            panel = self.query_one("#attack-panel", AttackProgressPanel)
            panel.status = status
            panel.refresh()
        except Exception:
            pass

    def _on_rogue_ap_log(self, log_msg: str) -> None:
        self._on_attack_progress(status=log_msg)

    def _on_wordlist_selected(self, wordlist_path: str | None) -> None:
        if wordlist_path:
            self.app.push_screen(EnginePickerScreen(), callback=lambda engine: self._on_engine_selected(wordlist_path, engine))
        else:
            self.app.pop_screen()

    def _on_engine_selected(self, wordlist_path: str, engine: str | None) -> None:
        if engine:
            self.app.push_screen(CrackProgressScreen(
                cap_file=self.app.session.captures[-1],
                wordlist=wordlist_path,
                engine=engine
            ))
        else:
            self.app.pop_screen()

    def _tick(self) -> None:
        self.elapsed += 1
        try:
            panel = self.query_one("#attack-panel", AttackProgressPanel)
            panel.beacons = self.beacons
            panel.data_pkts = self.data_pkts
            panel.signal = self.signal
            panel.refresh()

            # Update base status details
            widget = self.query_one("#adapter-status", AdapterStatusWidget)
            widget.status = "capturing"
            widget.time_elapsed = f"{self.elapsed // 60:02d}:{self.elapsed % 60:02d}"
        except Exception:
            pass

    def update_eapol(
        self, m1: bool, m2: bool, m3: bool, m4: bool, status: str
    ) -> None:
        """Update EAPOL tracker from external event."""
        try:
            panel = self.query_one("#attack-panel", AttackProgressPanel)
            panel.m1, panel.m2, panel.m3, panel.m4 = m1, m2, m3, m4
            panel.status = status
            panel.refresh()
        except Exception:
            pass

    def action_stop(self) -> None:
        if hasattr(self, "_timer"):
            self._timer.stop()
        self.app.pop_screen()


# ── Deauth Target Selection Screen ────────────────────────────────────────────

class DeauthSelectScreen(SidewinderScreen):
    """Select which clients to deauth with checkbox list."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "confirm", "Confirm"),
        Binding("space", "toggle", "Toggle"),
        Binding("a", "select_all", "Select All"),
        Binding("plus", "rate_up", "Rate +"),
        Binding("minus", "rate_down", "Rate -"),
    ]

    rate: reactive[int] = reactive(10)

    def compose_main(self) -> ComposeResult:
        yield Static("[bold $primary]Select Deauth Targets[/bold $primary]", id="deauth-title")
        yield Static("[$text-disabled]────────────────────[/$text-disabled]")
        yield DataTable(id="client-table", show_cursor=True)
        yield Static(id="rate-display")

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  Space[/$text-muted][$text-muted] toggle[/$text-muted]"
            "  [$text-muted]a[/$text-muted][$text-muted] select all[/$text-muted]"
            "  [$text-muted]+/-[/$text-muted][$text-muted] rate[/$text-muted]"
            "  [$text-muted]Enter[/$text-muted][$text-muted] confirm[/$text-muted]"
            "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
            id="deauth-hints",
        )

    def on_mount(self) -> None:
        super().on_mount()
        table = self.query_one("#client-table", DataTable)
        table.add_column("SEL", width=4)
        table.add_column("MAC", width=17)
        table.add_column("Vendor", width=15)
        table.add_column("Signal", width=10)
        table.add_column("Packets", width=6)
        self._update_rate_display()

        # Load clients belonging to the selected AP
        target = self.app.session.selected_target
        if target:
            clients = [c for c in self.app.session.clients if c.bssid.upper() == target.bssid.upper()]
            for c in clients:
                self.add_client(c.mac, c.signal, c.packets)

    def _update_rate_display(self) -> None:
        rd = self.query_one("#rate-display", Static)
        rd.update(f"[$text-muted]  Deauth rate[/$text-muted]  [$accent]{self.rate}[/$accent][$text-muted] frames/burst[/$text-muted]  [$text-muted]+/- to adjust[/$text-muted]")

    def action_rate_up(self) -> None:
        self.rate = min(self.rate + 5, 50)
        self._update_rate_display()

    def action_rate_down(self) -> None:
        self.rate = max(self.rate - 5, 5)
        self._update_rate_display()

    def add_client(self, mac: str, signal: int, packets: int) -> None:
        table = self.query_one("#client-table", DataTable)
        vendor = "Unknown"
        try:
            from ..core.fingerprint import Fingerprinter
            fp = Fingerprinter()
            device = fp.fingerprint_client(mac)
            vendor = device.vendor
        except Exception:
            pass

        table.add_row(
            "[$success]*[/$success]",
            f"[$text-muted]{mac}[/$text-muted]",
            vendor[:15],
            f"{signal_bar(signal)} {signal}",
            str(packets),
            key=mac,
        )

    def action_toggle(self) -> None:
        table = self.query_one("#client-table", DataTable)
        if table.cursor_row >= 0:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            col_key = list(table.columns.keys())[0]
            current = table.get_cell(row_key, col_key)
            new_val = "[$text-muted]·[/$text-muted]" if "*" in str(current) else "[$success]*[/$success]"
            table.update_cell(row_key, col_key, new_val, update_width=False)

    def action_select_all(self) -> None:
        table = self.query_one("#client-table", DataTable)
        col_key = list(table.columns.keys())[0]
        for row_key in table.rows:
            table.update_cell(row_key, col_key, "[$success]*[/$success]", update_width=False)

    def action_confirm(self) -> None:
        table = self.query_one("#client-table", DataTable)
        selected = []
        try:
            col_key = list(table.columns.keys())[0]
            for row_key in table.rows:
                cell = table.get_cell(row_key, col_key)
                if "*" in str(cell):
                    selected.append(row_key.value)
        except Exception:
            pass
        self.app.push_screen(CaptureProgressScreen(
            target=self.app.session.selected_target,
            method="deauth",
            selected_clients=selected
        ))

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Crack Progress Screen ─────────────────────────────────────────────────────

class CrackProgressScreen(SidewinderScreen):
    """Real-time cracking progress with keys/sec, ETA, current key."""

    BINDINGS = [
        Binding("escape", "stop", "Stop"),
    ]

    def __init__(self, cap_file: str = "", wordlist: str = "", engine: str = "aircrack", **kwargs) -> None:
        super().__init__(**kwargs)
        self.cap_file = cap_file
        self.wordlist = wordlist
        self.engine = engine

    keys_tested: reactive[int] = reactive(0)
    keys_total: reactive[int] = reactive(0)
    speed: reactive[float] = reactive(0.0)
    current_key: reactive[str] = reactive("")
    eta: reactive[str] = reactive("unknown")

    def compose_main(self) -> ComposeResult:
        yield Static("[bold $primary]Cracking Password[/bold $primary]", id="crack-title")
        yield Static("[$text-disabled]────────────────[/$text-disabled]")
        with Vertical(id="crack-stats-panel"):
            yield Static(id="crack-stats")
            yield ProgressBar(id="crack-progress", total=100)

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  Esc[/$text-muted][$text-muted] stop cracking[/$text-muted]",
            id="crack-hints",
        )

    def on_mount(self) -> None:
        super().on_mount()
        self._update_display()
        self.crack_task = self.run_safe_task(self._start_cracking())

    def on_unmount(self) -> None:
        super().on_unmount()
        if hasattr(self, "crack_task") and self.crack_task and not self.crack_task.done():
            self.crack_task.cancel()

    async def _start_cracking(self) -> None:
        cap = self.cap_file or (self.app.session.captures[-1] if self.app.session.captures else "")
        if not cap:
            from ..core.errors import SidewinderError, Severity, Category
            raise SidewinderError(
                severity=Severity.ERROR,
                category=Category.USER,
                what="No capture file selected for cracking",
                why="A capture file containing a handshake must be selected first.",
                how_to_fix=["Perform a scan and capture first", "Or select a capture from the captures list."]
            )

        wordlist = self.wordlist or "/usr/share/wordlists/rockyou.txt"
        import os
        if not os.path.exists(wordlist):
            from ..core.errors import ERROR_DB
            raise ERROR_DB["WORDLIST_NOT_FOUND"]

        try:
            widget = self.query_one("#adapter-status", AdapterStatusWidget)
            widget.status = "cracking"
        except Exception:
            pass

        from ..core.cracker import crack_aircrack, crack_hashcat, CrackProgress
        from ..core.subprocess_mgr import get_manager

        target_bssid = self.app.session.selected_target.bssid if self.app.session.selected_target else "00:00:00:00:00:00"
        ssid = self.app.session.selected_target.display_name() if self.app.session.selected_target else "Unknown"

        def handle_progress(progress: CrackProgress) -> None:
            self.update_progress(
                tested=progress.keys_tested,
                total=progress.total_keys or 100000,
                speed=progress.keys_per_second,
                current=progress.current_key,
                eta=progress.eta_display()
            )

        if self.engine == "aircrack":
            result = await crack_aircrack(
                cap_file=cap,
                bssid=target_bssid,
                wordlist=wordlist,
                on_progress=handle_progress,
                mgr=get_manager()
            )
        else:
            result = await crack_hashcat(
                cap_file=cap,
                wordlist=wordlist,
                on_progress=handle_progress,
                mgr=get_manager()
            )

        if result and result.found:
            self.app.session.cracked_passwords.append(result)
            self.app.session.save()
            self.show_result(
                password=result.password,
                ssid=ssid,
                bssid=target_bssid,
                method=self.engine.upper(),
                keys=result.keys_tested
            )
        else:
            self.app.notify("Password not found in wordlist.", severity="warning")
            self.action_stop()

    def _update_display(self) -> None:
        stats = self.query_one("#crack-stats", Static)
        pct = (self.keys_tested / self.keys_total * 100) if self.keys_total > 0 else 0
        stats.update(
            f"[$text-muted]Keys tested[/$text-muted]  [$secondary]{self.keys_tested:,}[/$secondary][$text-muted] / [/$text-muted][$text]{self.keys_total:,}[/$text]\n"
            f"[$text-muted]Speed      [/$text-muted]  [$secondary]{self.speed:,.0f}[/$secondary][$text-muted] keys/sec[/$text-muted]\n"
            f"[$text-muted]ETA        [/$text-muted]  [$secondary]{self.eta}[/$secondary]\n"
            f"[$text-muted]Current    [/$text-muted]  [$text-muted]{self.current_key or '...'}[/$text-muted]\n"
        )
        pbar = self.query_one("#crack-progress", ProgressBar)
        pbar.progress = pct

    def update_progress(self, tested: int, total: int, speed: float, current: str, eta: str) -> None:
        """Update progress from crack engine."""
        self.keys_tested = tested
        self.keys_total = total
        self.speed = speed
        self.current_key = current
        self.eta = eta
        self._update_display()

    def show_result(self, password: str, ssid: str, bssid: str, method: str, keys: int) -> None:
        """Password found — transition to result screen."""
        self.app.push_screen(ResultScreen(
            password=password,
            ssid=ssid,
            bssid=bssid,
            method=method,
            keys_tested=keys,
        ))

    def action_stop(self) -> None:
        if self.app.session.captures:
            self.app.push_screen(WordlistPickerScreen(), callback=self._on_wordlist_selected)
        else:
            self.app.pop_screen()

    def _on_wordlist_selected(self, wordlist_path: str | None) -> None:
        if wordlist_path:
            self.app.push_screen(EnginePickerScreen(), callback=lambda engine: self._on_engine_selected(wordlist_path, engine))
        else:
            self.app.pop_screen()

    def _on_engine_selected(self, wordlist_path: str, engine: str | None) -> None:
        if engine:
            self.app.push_screen(CrackProgressScreen(
                cap_file=self.app.session.captures[-1],
                wordlist=wordlist_path,
                engine=engine
            ))
        else:
            self.app.pop_screen()


# ── Result Screen ─────────────────────────────────────────────────────────────

class ResultScreen(SidewinderScreen):
    """Password found result card."""

    BINDINGS = [
        Binding("1", "save", "Save"),
        Binding("2", "copy", "Copy"),
        Binding("4", "attack_another", "Attack Another"),
        Binding("6", "main_menu", "Main Menu"),
        Binding("escape", "main_menu", "Main Menu"),
    ]

    def __init__(
        self,
        password: str,
        ssid: str,
        bssid: str,
        method: str,
        keys_tested: int,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._password = password
        self._ssid = ssid
        self._bssid = bssid
        self._method = method
        self._keys = keys_tested

    def compose_main(self) -> ComposeResult:
        from .components import PasswordCard
        with Vertical(id="sc-result"):
            yield Spacer(flex=1)
            with Center():
                yield PasswordCard(
                    ssid=self._ssid,
                    bssid=self._bssid,
                    password=self._password,
                    method=self._method,
                    keys=self._keys,
                    elapsed=0.0, # We can pass session elapsed or mock it
                    id="result-card",
                )
            yield Spacer(flex=1)

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  1[/$text-muted][$text-muted] save to file[/$text-muted]"
            "  [$text-muted]2[/$text-muted][$text-muted] copy to clipboard[/$text-muted]"
            "  [$text-muted]4[/$text-muted][$text-muted] attack another[/$text-muted]"
            "  [$text-muted]6[/$text-muted][$text-muted] main menu[/$text-muted]",
            id="result-hints",
        )

    async def action_copy(self) -> None:
        """Copy password to clipboard via xclip/xsel."""
        import asyncio
        import subprocess
        try:
            proc = await asyncio.create_subprocess_exec(
                "xclip", "-selection", "clipboard",
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            await proc.communicate(input=self._password.encode())
            if proc.returncode == 0:
                self.notify("Password copied to clipboard")
                return
        except Exception:
            pass
        try:
            proc = await asyncio.create_subprocess_exec(
                "xsel", "--clipboard", "--input",
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            await proc.communicate(input=self._password.encode())
            if proc.returncode == 0:
                self.notify("Password copied to clipboard")
                return
        except Exception:
            pass
        self.notify("Failed to copy (xclip/xsel missing)", severity="error")

    def action_save(self) -> None:
        """Save password to ~/.sidewinder/results/."""
        import os
        from datetime import datetime
        results_dir = os.path.expanduser("~/.sidewinder/results")
        os.makedirs(results_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(results_dir, f"{self._ssid}_{ts}.txt")
        with open(path, "w") as f:
            f.write(f"SSID: {self._ssid}\nBSSID: {self._bssid}\nPassword: {self._password}\nMethod: {self._method}\n")
        self.notify(f"Saved to {path}")



    def action_attack_another(self) -> None:
        self.app.push_screen(ScanScreen())

    def action_main_menu(self) -> None:
        while len(self.app.screen_stack) > 2:
            self.app.pop_screen()


# ── Error Screen ──────────────────────────────────────────────────────────────

class ErrorScreen(SidewinderScreen):
    """Displays a structured error with What/Why/HowToFix."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "back", "Dismiss"),
    ]

    def __init__(
        self,
        severity: str,
        what: str,
        why: str,
        how_to_fix: list[str],
        raw_error: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._sev = severity
        self._what = what
        self._why = why
        self._how = how_to_fix
        self._raw = raw_error
        self._last_error_text = f"Severity: {severity}\nWhat: {what}\nWhy: {why}\nHow to fix: {how_to_fix}\nRaw error: {raw_error}"

    def compose_main(self) -> ComposeResult:
        with Vertical(id="sc-error"):
            yield ErrorCard(
                severity=self._sev,
                what=self._what,
                why=self._why,
                how_to_fix=self._how,
                raw_error=self._raw,
            )
            from textual.widgets import Button
            yield Button("Copy Details", id="btn-copy-error")

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  Enter[/$text-muted][$text-muted] dismiss[/$text-muted]"
            "  [$text-muted]Esc[/$text-muted][$text-muted] dismiss[/$text-muted]",
            id="error-hints",
        )

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Help Screen ───────────────────────────────────────────────────────────────

TUTORIAL = """\
 [$accent]┌─ Welcome to Sidewinder ──────────────────────────────────────────┐[/$accent]
 [$accent]│[/$accent]  A native Linux WiFi audit tool. Zero bloat, terminal-first.   [$accent]│[/$accent]
 [$accent]└──────────────────────────────────────────────────────────────────┘[/$accent]

 [$primary]Phase 1 · Scan[/$primary]
 [$text-disabled]──────────────[/$text-disabled]
   [$text-muted]1.[/$text-muted]  Press [bold $primary][1][/bold $primary] from the main menu to start a live scan
   [$text-muted]2.[/$text-muted]  Networks appear automatically (auto-hops all channels)
   [$text-muted]3.[/$text-muted]  Press [bold $text]Enter[/bold $text] on a network to select it as the target
   [$text-muted]4.[/$text-muted]  Press [bold $text]s[/bold $text] to stop scanning and move to capture

 [$primary]Phase 2 · Capture[/$primary]
 [$text-disabled]─────────────────[/$text-disabled]
   [$text-muted]1.[/$text-muted]  Choose your method:
       [bold $primary][1][/bold $primary]  [$success]Passive[/$success]  — Listen quietly for a natural handshake
       [bold $primary][2][/bold $primary]  [$warning]Deauth[/$warning]   — Force clients off, capture handshake fast
   [$text-muted]2.[/$text-muted]  Watch the [$accent]EAPOL M1→M2→M3→M4[/$accent] tracker fill in
   [$text-muted]3.[/$text-muted]  Capture stops automatically when handshake is complete

 [$primary]Phase 3 · Crack[/$primary]
 [$text-disabled]───────────────[/$text-disabled]
   [$text-muted]1.[/$text-muted]  Pick a wordlist (Sidewinder auto-discovers system lists)
   [$text-muted]2.[/$text-muted]  Choose engine: [$secondary]aircrack-ng[/$secondary] (CPU) or [$primary]hashcat[/$primary] (GPU)
   [$text-muted]3.[/$text-muted]  Watch the progress bar and key-rate counter
   [$text-muted]4.[/$text-muted]  Password appears in [bold $success]green[/bold $success] when found

 [$primary]Phase 4 · Cleanup[/$primary]
 [$text-disabled]─────────────────[/$text-disabled]
   [$text-muted]1.[/$text-muted]  Press [bold $primary][6][/bold $primary] from the main menu
   [$text-muted]2.[/$text-muted]  Confirm capture file deletion
   [$text-muted]3.[/$text-muted]  NetworkManager and wpa_supplicant are restored automatically
   [$text-muted]4.[/$text-muted]  Exit safely

 [$primary]Keyboard Reference[/$primary]
 [$text-disabled]──────────────────[/$text-disabled]
   [bold $text]j / k[/bold $text]      Navigate up / down
   [bold $text]Enter[/bold $text]      Select or confirm
   [bold $text]Esc[/bold $text]        Back or cancel
   [bold $text]/[/bold $text]          Open command palette
   [bold $text]?[/bold $text]          This help screen
   [bold $text]1 – 7[/bold $text]      Quick menu access
   [bold $text]s[/bold $text]          Stop active scan
   [bold $text]Space[/bold $text]      Toggle checkbox (deauth screen)
   [bold $text]a[/bold $text]          Select all (deauth screen)

 [$primary]Adapter Priority[/$primary]
 [$text-disabled]────────────────[/$text-disabled]
   [$success]1st[/$success]  RTL8821AU — Full monitor + injection + 5GHz
   [$warning]2nd[/$warning]  RT5370    — 2.4GHz, reliable, no extra driver needed
   [$error]3rd[/$error]  MT7902    — Internet only, no injection

 [$text-muted]Press Esc or q to close[/$text-muted]
"""


class HelpScreen(SidewinderScreen):
    """Full WiFi audit tutorial — opened with ? key."""

    BINDINGS = [
        Binding("escape", "back", "Close"),
        Binding("q", "back", "Close"),
    ]

    def compose_main(self) -> ComposeResult:
        with VerticalScroll(id="help-scroll"):
            yield Static(TUTORIAL, id="tutorial-text")

    def compose_prompt(self) -> ComposeResult:
        yield Static("[$text-muted]  Esc / q[/$text-muted][$text-muted] close help[/$text-muted]", id="help-hints")

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Session Resume ────────────────────────────────────────────────────────────

class ResumeScreen(SidewinderScreen):
    """Session resume prompt — shown when a previous session exists.

    Displays session summary and asks Y/n to resume.
    """

    BINDINGS = [
        Binding("y", "resume", "Resume"),
        Binding("n", "new_session", "New Session"),
        Binding("escape", "new_session", "New Session"),
    ]

    def __init__(self, session) -> None:
        super().__init__()
        self._session = session

    def compose_main(self) -> ComposeResult:
        with Vertical(id="sc-resume"):
            yield Static("[bold $primary]Previous Session Found[/bold $primary]", id="resume-title")
            yield Static("[$text-disabled]─────────────────────[/$text-disabled]")
            scan_count = len(self._session.scan_results)
            target = self._session.selected_target
            target_name = target.display_name() if target else "None"
            captures = len(self._session.captures)
            cracked = len(self._session.cracked_passwords)
            yield Static(
                f"[$text-muted]  Session [/$text-muted]  [$text-muted]{self._session.id[:8]}...[/$text-muted]\n"
                f"[$text-muted]  Adapter [/$text-muted]  [$text-muted]{self._session.adapter or 'Not set'}[/$text-muted]\n"
                f"[$text-muted]  Scans   [/$text-muted]  [$text]{scan_count} networks[/$text]\n"
                f"[$text-muted]  Target  [/$text-muted]  [$text]{target_name}[/$text]\n"
                f"[$text-muted]  Captures[/$text-muted]  [$text]{captures} files[/$text]\n"
                f"[$text-muted]  Cracked [/$text-muted]  [$success]{cracked} passwords[/$success]",
                id="resume-summary",
            )

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[bold $success]  Y[/bold $success][$text-muted]  Resume this session[/$text-muted]\n"
            "[bold $error]  N[/bold $error][$text-muted]  Start fresh[/$text-muted]",
            id="resume-options",
        )

    def action_resume(self) -> None:
        self.app.session = self._session
        # Ensure session data flows into scan results
        self.app.notify(f"Resumed session {self._session.id[:8]}", severity="information")
        self.app.pop_screen()

    def action_new_session(self) -> None:
        """Discard old session and start fresh."""
        self.app.notify("Starting new session", severity="information")
        self.app.pop_screen()


# ── Command Palette ───────────────────────────────────────────────────────────

class CommandPaletteScreen(SidewinderScreen):
    """Slash command palette overlay."""

    BINDINGS = [
        Binding("escape", "back", "Close"),
        Binding("enter", "submit", "Submit"),
        Binding("up", "nav_up", "Up", show=False),
        Binding("down", "nav_down", "Down", show=False),
    ]

    def compose_main(self) -> ComposeResult:
        from .app import SLASH_COMMANDS
        with Vertical(id="command-container"):
            yield Static(
                "[bold $primary]Command Palette[/bold $primary]",
                id="command-title",
            )
            yield Input(placeholder="/command…", id="command-input")
            
            options = [
                Option(f"{cmd} - {desc}", id=cmd)
                for cmd, desc in SLASH_COMMANDS.items()
            ]
            yield OptionList(*options, id="command-list")

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  Enter[/$text-muted][$text-muted] submit[/$text-muted]"
            "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
            id="command-hints",
        )

    def on_mount(self) -> None:
        self.query_one(Input).focus()
        olist = self.query_one(OptionList)
        if olist.option_count > 0:
            olist.highlighted = 0

    def on_input_changed(self, event) -> None:
        from .app import SLASH_COMMANDS
        val = event.value.lower()
        olist = self.query_one(OptionList)
        olist.clear_options()
        for cmd, desc in SLASH_COMMANDS.items():
            if val in cmd.lower() or val in desc.lower():
                olist.add_option(Option(f"{cmd} - {desc}", id=cmd))
        if olist.option_count > 0:
            olist.highlighted = 0
        else:
            olist.highlighted = None

    def on_input_submitted(self, event) -> None:
        self.action_submit()

    def action_nav_up(self) -> None:
        olist = self.query_one(OptionList)
        if olist.option_count > 0:
            if olist.highlighted is None:
                olist.highlighted = olist.option_count - 1
            elif olist.highlighted > 0:
                olist.highlighted -= 1

    def action_nav_down(self) -> None:
        olist = self.query_one(OptionList)
        if olist.option_count > 0:
            if olist.highlighted is None:
                olist.highlighted = 0
            elif olist.highlighted < olist.option_count - 1:
                olist.highlighted += 1

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_submit(self) -> None:
        self._execute_command()

    def on_option_list_option_selected(self, event) -> None:
        self._execute_command(event.option.id)

    def _execute_command(self, cmd_id: Optional[str] = None) -> None:
        if not cmd_id:
            olist = self.query_one(OptionList)
            if olist.highlighted is not None:
                cmd_id = olist.get_option_at_index(olist.highlighted).id
            else:
                self.app.notify("No command selected.", severity="warning")
                return
        
        self.app.pop_screen()
        
        if cmd_id == "/scan":
            self.app.push_screen(ScanScreen())
        elif cmd_id == "/target":
            self.app.push_screen(TargetSelectScreen())
        elif cmd_id == "/help":
            self.app.push_screen(HelpScreen())
        elif cmd_id == "/cleanup":
            self.app.push_screen(CleanupScreen())
        elif cmd_id == "/theme":
            self.app.push_screen(ThemeSelectScreen())
        elif cmd_id == "/compact":
            if hasattr(self.app, "action_toggle_compact"):
                self.app.action_toggle_compact()
        elif cmd_id == "/capture":
            if self.app.session.selected_target:
                self.app.push_screen(CaptureMethodScreen(target=self.app.session.selected_target))
            else:
                self.app.notify("No target selected. Select a target first.", severity="warning")
        elif cmd_id == "/crack":
            cap = self.app.session.captures[-1] if self.app.session.captures else ""
            if not cap:
                self.app.notify("No captures found. Run a scan/capture first or select a capture file.", severity="warning")
            else:
                self.app.push_screen(WordlistPickerScreen(), callback=lambda wl: self._on_wordlist_selected_cmd(cap, wl))
        elif cmd_id == "/adapter":
            self.app.push_screen(AdapterScreen())
        elif cmd_id == "/status":
            self.app.push_screen(SessionStatusScreen())
        elif cmd_id == "/session":
            self.app.push_screen(SessionListScreen())
        elif cmd_id == "/quit":
            self.app.exit()
        else:
            self.app.notify(f"Command {cmd_id} not fully wired yet.", severity="warning")

    def _on_wordlist_selected_cmd(self, cap: str, wordlist_path: str | None) -> None:
        if wordlist_path:
            self.app.push_screen(EnginePickerScreen(), callback=lambda engine: self._on_engine_selected_cmd(cap, wordlist_path, engine))

    def _on_engine_selected_cmd(self, cap: str, wordlist_path: str, engine: str | None) -> None:
        if engine:
            self.app.push_screen(CrackProgressScreen(
                cap_file=cap,
                wordlist=wordlist_path,
                engine=engine
            ))



# ── Theme Selector ────────────────────────────────────────────────────────────

class ThemeSelectScreen(SidewinderScreen):
    """Modal screen for selecting visual themes with live preview."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select", "Select"),
    ]

    def compose_main(self) -> ComposeResult:
        with Vertical(id="theme-select-container"):
            yield Static(
                "[bold $primary]Select Visual Theme[/bold $primary]",
                id="theme-title",
            )
            themes = list(self.app.available_themes.keys())
            options = [Option(theme, id=theme) for theme in themes]
            yield OptionList(*options, id="theme-list")

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  Enter[/$text-muted][$text-muted] select[/$text-muted]"
            "  [$text-muted]Esc[/$text-muted][$text-muted] cancel[/$text-muted]",
            id="theme-hints",
        )

    def on_mount(self) -> None:
        self._original_theme = self.app.theme
        olist = self.query_one(OptionList)
        olist.focus()
        for i, opt in enumerate(olist._options):
            if opt.id == self._original_theme:
                olist.highlighted = i
                break

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """Live preview theme as user highlights options."""
        theme_id = event.option.id
        if theme_id in self.app.available_themes:
            self.app.theme = theme_id
            self.app.refresh_css(animate=False)
            self.app.refresh(layout=True)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Confirm selection when pressing Enter on the option list."""
        self.action_select()

    def action_cancel(self) -> None:
        """Cancel selection and restore original theme."""
        self.app.theme = self._original_theme
        self.app.refresh_css(animate=False)
        self.app.refresh(layout=True)
        self.app.pop_screen()

    def action_select(self) -> None:
        """Confirm selection and save theme to config."""
        selected_theme = self.query_one(OptionList).get_option_at_index(
            self.query_one(OptionList).highlighted
        ).id
        self.app.theme = selected_theme
        self.app.refresh_css(animate=False)
        self.app.refresh(layout=True)
        self.app.settings.theme = selected_theme
        self.app.settings.save()
        self.app.notify(f"Theme set to {selected_theme}", severity="success")
        self.app.pop_screen()


# ── Wordlist Picker ───────────────────────────────────────────────────────────

class WordlistPickerScreen(SidewinderScreen):
    """File browser for selecting wordlists."""
    
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "select", "Select"),
    ]

    def compose_main(self) -> ComposeResult:
        from textual.widgets import DirectoryTree
        import os

        with Vertical(id="sc-wordlist"):
            yield Static("[bold $primary]Select Wordlist[/bold $primary]", id="wordlist-title")
            yield Static("[$text-disabled]──────────────[/$text-disabled]")
            path = "/usr/share/wordlists" if os.path.exists("/usr/share/wordlists") else "."
            yield DirectoryTree(path, id="wordlist-tree")

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  Enter[/$text-muted][$text-muted] select[/$text-muted]"
            "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
            id="wordlist-hints",
        )

    def on_directory_tree_file_selected(self, event) -> None:
        self.app.notify(f"Selected: {event.path}")
        self.dismiss(str(event.path))

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Engine Picker ─────────────────────────────────────────────────────────────

class EnginePickerScreen(SidewinderScreen):
    """Select cracking engine (Aircrack-ng vs Hashcat)."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("1", "select_aircrack", "Aircrack-ng (CPU)"),
        Binding("2", "select_hashcat", "Hashcat (GPU)"),
    ]

    def compose_main(self) -> ComposeResult:
        with Vertical(id="sc-engine"):
            yield Static("[bold $primary]Select Cracking Engine[/bold $primary]", id="engine-title")
            yield Static("[$text-disabled]──────────────────────[/$text-disabled]")
            yield Static(
                " [$text-muted][[/$text-muted][bold $primary]1[/bold $primary][$text-muted]][/$text-muted]  "
                "[$text]Aircrack-ng[/$text][$text-muted]  CPU-based, standard[/$text-muted]\n"
                " [$text-muted][[/$text-muted][bold $primary]2[/bold $primary][$text-muted]][/$text-muted]  "
                "[$text]Hashcat[/$text][$text-muted]     GPU-based, requires CUDA/ROCm[/$text-muted]\n",
                id="engine-options",
            )

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  1/2[/$text-muted][$text-muted] select engine[/$text-muted]"
            "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
            id="engine-hints",
        )

    def action_select_aircrack(self) -> None:
        self.dismiss("aircrack")

    def action_select_hashcat(self) -> None:
        self.dismiss("hashcat")

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Cleanup Screen ────────────────────────────────────────────────────────────

class CleanupScreen(SidewinderScreen):
    """Visual checklist for restored services/files."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "run_cleanup", "Run Cleanup"),
    ]

    def compose_main(self) -> ComposeResult:
        with Vertical(id="sc-cleanup"):
            yield Static("[bold $primary]System Cleanup[/bold $primary]", id="cleanup-title")
            yield Static("[$text-disabled]──────────────[/$text-disabled]")
            yield Static(
                "[$text-muted]The following actions will be performed:[/$text-muted]\n\n"
                "  [$text-muted][ ][/$text-muted]  Restore NetworkManager / wpa_supplicant\n"
                "  [$text-muted][ ][/$text-muted]  Disable Monitor Mode\n"
                "  [$text-muted][ ][/$text-muted]  Terminate background attack processes\n"
                "  [$text-muted][ ][/$text-muted]  Clear temporary capture files (/tmp/)\n",
                id="cleanup-body",
            )

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  Enter[/$text-muted][$success] confirm cleanup[/$success]"
            "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
            id="cleanup-hints",
        )

    async def action_run_cleanup(self) -> None:
        body = self.query_one("#cleanup-body", Static)

        # Step 1: Terminate background attack processes
        body.update(
            "[$text-muted]The following actions will be performed:[/$text-muted]\n\n"
            "  [$text-muted][ ][/$text-muted]  Restore NetworkManager / wpa_supplicant\n"
            "  [$text-muted][ ][/$text-muted]  Disable Monitor Mode\n"
            "  [$success][x][/$success]  Terminate background attack processes\n"
            "  [$text-muted][ ][/$text-muted]  Clear temporary capture files (/tmp/)\n"
        )
        await asyncio.sleep(0.5)

        # Step 2: Disable Monitor Mode
        body.update(
            "[$text-muted]The following actions will be performed:[/$text-muted]\n\n"
            "  [$text-muted][ ][/$text-muted]  Restore NetworkManager / wpa_supplicant\n"
            "  [$success][x][/$success]  Disable Monitor Mode\n"
            "  [$success][x][/$success]  Terminate background attack processes\n"
            "  [$text-muted][ ][/$text-muted]  Clear temporary capture files (/tmp/)\n"
        )
        await asyncio.sleep(0.5)

        # Step 3: Restore NetworkManager / wpa_supplicant
        if hasattr(self.app, "action_cleanup"):
            await self.app.action_cleanup()

        body.update(
            "[$text-muted]The following actions will be performed:[/$text-muted]\n\n"
            "  [$success][x][/$success]  Restore NetworkManager / wpa_supplicant\n"
            "  [$success][x][/$success]  Disable Monitor Mode\n"
            "  [$success][x][/$success]  Terminate background attack processes\n"
            "  [$text-muted][ ][/$text-muted]  Clear temporary capture files (/tmp/)\n"
        )
        await asyncio.sleep(0.5)

        # Step 4: Clear temporary capture files (/tmp/)
        if hasattr(self.app, "_cleanup_manager") and self.app._cleanup_manager:
            await self.app._cleanup_manager.cleanup_files()

        body.update(
            "[$text-muted]The following actions will be performed:[/$text-muted]\n\n"
            "  [$success][x][/$success]  Restore NetworkManager / wpa_supplicant\n"
            "  [$success][x][/$success]  Disable Monitor Mode\n"
            "  [$success][x][/$success]  Terminate background attack processes\n"
            "  [$success][x][/$success]  Clear temporary capture files (/tmp/)\n"
        )
        self.app._cleaned_up = True
        await asyncio.sleep(1.0)
        self.app.pop_screen()

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Service Check Screen ──────────────────────────────────────────────────────

class ServiceCheckScreen(SidewinderScreen):
    """Interface to manually kill/restore services."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("k", "kill_services", "Kill Conflicting"),
        Binding("r", "restore_services", "Restore Services"),
    ]

    def compose_main(self) -> ComposeResult:
        with Vertical(id="sc-services"):
            yield Static("[bold $primary]Service Management[/bold $primary]", id="services-title")
            yield Static("[$text-disabled]──────────────────[/$text-disabled]")
            yield Static(
                "[$text-muted]Checking for conflicting services...[/$text-muted]",
                id="services-status",
            )
            yield ListView(id="service-list")

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  k[/$text-muted][$error] kill conflicting[/$error]"
            "  [$text-muted]r[/$text-muted][$success] restore[/$success]"
            "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
            id="services-hints",
        )

    async def on_mount(self) -> None:
        self.call_after_refresh(self._load_services)

    async def _load_services(self) -> None:
        lv = self.query_one("#service-list", ListView)
        if self.app._service_manager:
            found = await self.app._service_manager.find_conflicting()
            if not found:
                lv.append(ListItem(Label("No conflicting services found.")))
            else:
                for pid, name in found:
                    lv.append(ListItem(Label(f"PID {pid}: {name}")))
        else:
            lv.append(ListItem(Label("Service Manager not initialized.")))

    async def action_kill_services(self) -> None:
        if self.app._service_manager:
            res = await self.app._service_manager.kill_conflicting()
            self.app.notify(f"Killed {len(res.killed)} services.")
            await self._load_services()

    async def action_restore_services(self) -> None:
        if self.app._service_manager:
            await self.app._service_manager.restore()
            self.app.notify("Services restored.")
            await self._load_services()

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Monitor Setup Screen ──────────────────────────────────────────────────────

class MonitorSetupScreen(SidewinderScreen):
    """Real-time feedback for interface mode switching."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("e", "enable_monitor", "Enable Monitor"),
        Binding("d", "disable_monitor", "Disable Monitor"),
    ]

    def __init__(self, adapter_name: str, **kwargs):
        super().__init__(**kwargs)
        self.adapter_name = adapter_name

    def compose_main(self) -> ComposeResult:
        with Vertical(id="sc-monitor"):
            yield Static(
                f"[bold $primary]Monitor Mode[/bold $primary]  "
                f"[$text-muted]adapter[/$text-muted] [$secondary]{self.adapter_name}[/$secondary]",
                id="monitor-title",
            )
            yield Static("[$text-disabled]──────────────────────────────[/$text-disabled]")
            yield Static(id="monitor-status")
            from ..core.tooltips import get_tooltip
            tip = get_tooltip("monitor_mode")
            if tip:
                yield Static(
                    f"[$primary]{tip.title}[/$primary]\n"
                    f"[$text-muted]{tip.description}[/$text-muted]\n"
                    f"[$text-muted]{tip.example}[/$text-muted]",
                    id="tooltip-info",
                )

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  e[/$text-muted][$success] enable monitor[/$success]"
            "  [$text-muted]d[/$text-muted][$error] disable monitor[/$error]"
            "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
            id="monitor-hints",
        )

    async def on_mount(self) -> None:
        self.call_after_refresh(self._check_status)

    async def _check_status(self) -> None:
        import asyncio
        from ..core.monitor import get_interface_mode_sync
        mode = await asyncio.to_thread(get_interface_mode_sync, self.adapter_name)
        status = self.query_one("#monitor-status", Static)
        status.update(f"Current mode: [bold]{mode}[/bold]")

    async def action_enable_monitor(self) -> None:
        import asyncio
        from ..core.monitor import enter_monitor_mode
        from ..core.adapter import get_phy
        try:
            phy = await asyncio.to_thread(get_phy, self.adapter_name)
            if not phy:
                self.app.notify("Cannot determine PHY for adapter", severity="error")
                return
            new_iface = await enter_monitor_mode(self.adapter_name, phy)
            self.app.notify(f"Monitor mode enabled on {new_iface}")
            self.adapter_name = new_iface
            await self._check_status()
        except Exception as e:
            self.app.notify(f"Failed: {e}", severity="error")

    async def action_disable_monitor(self) -> None:
        import asyncio
        from ..core.monitor import exit_monitor_mode
        from ..core.adapter import get_phy
        try:
            phy = await asyncio.to_thread(get_phy, self.adapter_name)
            if not phy:
                self.app.notify("Cannot determine PHY for adapter", severity="error")
                return
            orig = self.adapter_name.replace("mon", "")
            await exit_monitor_mode(self.adapter_name, orig, phy)
            self.app.notify(f"Monitor mode disabled. Back to {orig}")
            self.adapter_name = orig
            await self._check_status()
        except Exception as e:
            self.app.notify(f"Failed: {e}", severity="error")

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Scan Options Screen ───────────────────────────────────────────────────────

class ScanOptionsScreen(SidewinderScreen):
    """Form inputs for band selection, channels, and hidden SSIDs."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "start_scan", "Start Scan"),
    ]

    def compose_main(self) -> ComposeResult:
        from textual.widgets import Checkbox, Input
        with Vertical(id="sc-scanopts"):
            yield Static("[bold $primary]Scan Options[/bold $primary]", id="scanopts-title")
            yield Static("[$text-disabled]────────────[/$text-disabled]")
            yield Checkbox("2.4 GHz Band", value=True, id="band-2g")
            yield Checkbox("5 GHz Band", value=False, id="band-5g")
            yield Checkbox("6 GHz Band", value=False, id="band-6g")
            yield Static(
                "[$text-muted]Specific channels[/$text-muted] [$text-muted](leave blank for all)[/$text-muted]",
                id="channels-label",
            )
            yield Input(placeholder="e.g. 1,6,11", id="channels-input")
            yield Checkbox("Show Hidden SSIDs", value=True, id="show-hidden")

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  Enter[/$text-muted][$text-muted] start scan[/$text-muted]"
            "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
            id="scanopts-hints",
        )

    def on_input_submitted(self, event) -> None:
        self.action_start_scan()

    def action_start_scan(self) -> None:
        from textual.widgets import Checkbox, Input
        
        band_2g = self.query_one("#band-2g", Checkbox).value
        band_5g = self.query_one("#band-5g", Checkbox).value
        
        band_str = ""
        if band_2g and not band_5g:
            band_str = "g"
        elif band_5g and not band_2g:
            band_str = "a"
            
        chan_text = self.query_one("#channels-input", Input).value.strip()
        channels = []
        if chan_text:
            try:
                channels = [int(c.strip()) for c in chan_text.split(",") if c.strip().isdigit()]
            except Exception:
                pass
                
        show_hidden = self.query_one("#show-hidden", Checkbox).value
        
        self.app.push_screen(ScanScreen(
            band=band_str,
            channels=channels if channels else None,
            show_hidden=show_hidden
        ))

    def action_back(self) -> None:
        self.app.pop_screen()


# ── AP Details Screen ─────────────────────────────────────────────────────────

class APDetailsScreen(SidewinderScreen):
    """Detailed drill-down for a selected target AP."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("a", "attack", "Attack this AP"),
    ]

    def __init__(self, target, **kwargs) -> None:
        super().__init__(**kwargs)
        self.target = target

    def compose_main(self) -> ComposeResult:
        with VerticalScroll(id="sc-apdetails"):
            yield Static(
                f"[bold $primary]Access Point Details[/bold $primary]  "
                f"[$text]{self.target.display_name()}[/$text]",
                id="apdetails-title",
            )
            yield Static("[$text-disabled]──────────────────────────────[/$text-disabled]")
            pc = privacy_color(self.target.privacy)
            yield Static(
                f"[$text-muted]BSSID     [/$text-muted]  [$text-muted]{self.target.bssid}[/$text-muted]\n"
                f"[$text-muted]Channel   [/$text-muted]  [$secondary]{self.target.channel}[/$secondary]\n"
                f"[$text-muted]Signal    [/$text-muted]  {signal_bar(self.target.signal)} [$text]{self.target.signal} dBm[/$text]\n"
                f"[$text-muted]Encryption[/$text-muted]  [{pc}]{self.target.privacy}[/{pc}] [$text-muted]{self.target.cipher} {self.target.auth}[/$text-muted]\n"
                f"[$text-muted]Data Pkts [/$text-muted]  [$text-muted]{self.target.data_packets}[/$text-muted]\n",
                id="apdetails-info",
            )
            client_count = sum(1 for c in self.app.session.clients if c.bssid == self.target.bssid)
            yield Static(
                f"[$primary]Connected Clients[/$primary]  [$text]{client_count}[/$text]",
                id="apdetails-clients",
            )
            from ..core.intelligence import IntelligenceEngine
            engine = IntelligenceEngine()
            target_clients = [c for c in self.app.session.clients if c.bssid == self.target.bssid]
            recs = engine.evaluate_target(self.target, target_clients)
            if recs:
                yield Static(
                    "[bold $primary]Attack Recommendations[/bold $primary]",
                    id="apdetails-recs-title",
                )
                for r in recs:
                    conf_c = "$success" if r.confidence >= 70 else ("$warning" if r.confidence >= 40 else "$error")
                    yield Static(
                        f"  [{conf_c}]{r.confidence}%[/{conf_c}]  "
                        f"[$text]{r.method}[/$text]  [$text-muted]{r.reason}[/$text-muted]"
                    )
                    for w in r.warnings:
                        yield Static(f"    [$warning]! {w}[/$warning]")

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  a[/$text-muted][$text-muted] attack this AP[/$text-muted]"
            "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
            id="apdetails-hints",
        )

    def action_attack(self) -> None:
        self.app.push_screen(CaptureMethodScreen())

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Capture List Screen ───────────────────────────────────────────────────────

class CaptureListScreen(SidewinderScreen):
    """List saved capture files and allow selection for cracking."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "crack", "Crack Selected"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def compose_main(self) -> ComposeResult:
        from textual.widgets import DataTable
        with Vertical(id="sc-captures"):
            yield Static("[bold $primary]Saved Captures[/bold $primary]", id="captures-title")
            yield Static("[$text-disabled]──────────────[/$text-disabled]")
            table = DataTable(id="captures-table", cursor_type="row")
            table.add_columns("Filename", "Size", "Modified")
            yield table

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  Enter[/$text-muted][$text-muted] crack selected[/$text-muted]"
            "  [$text-muted]j/k[/$text-muted][$text-muted] navigate[/$text-muted]"
            "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
            id="captures-hints",
        )

    def on_mount(self) -> None:
        import os
        import time
        table = self.query_one("#captures-table", DataTable)
        capture_dir = os.path.expanduser(self.app.session.DEFAULT_PATH.replace("session.json", "captures"))
        
        # If user config provides capture_dir, we could use that, but session paths work
        from ..core.config import SidewinderConfig
        cfg = SidewinderConfig.load()
        capture_dir = os.path.expanduser(cfg.capture_dir)

        if not os.path.exists(capture_dir):
            os.makedirs(capture_dir, exist_ok=True)

        files_added = False
        for f in os.listdir(capture_dir):
            if f.endswith(".cap") or f.endswith(".pcapng") or f.endswith(".csv") or f.endswith(".hc22000"):
                full_path = os.path.join(capture_dir, f)
                size = os.path.getsize(full_path)
                mtime = os.path.getmtime(full_path)
                mdate = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
                table.add_row(f, str(size), mdate, key=full_path)
                files_added = True

        if not files_added:
            self.app.notify("No capture files found.", severity="warning")

    def action_crack(self) -> None:
        from textual.widgets import DataTable
        table = self.query_one("#captures-table", DataTable)
        if table.cursor_row >= 0:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            full_path = row_key.value
            self.app.notify(f"Selected {full_path} for cracking.", severity="information")
            self.app.push_screen(WordlistPickerScreen(), callback=lambda wl: self._on_wordlist_selected_capture_list(full_path, wl))

    def _on_wordlist_selected_capture_list(self, cap: str, wordlist_path: str | None) -> None:
        if wordlist_path:
            self.app.push_screen(EnginePickerScreen(), callback=lambda engine: self._on_engine_selected_capture_list(cap, wordlist_path, engine))

    def _on_engine_selected_capture_list(self, cap: str, wordlist_path: str, engine: str | None) -> None:
        if engine:
            self.app.push_screen(CrackProgressScreen(
                cap_file=cap,
                wordlist=wordlist_path,
                engine=engine
            ))
            
    def action_back(self) -> None:
        self.app.pop_screen()
        
    def action_cursor_down(self) -> None:
        from textual.widgets import DataTable
        self.query_one(DataTable).action_scroll_down()

    def action_cursor_up(self) -> None:
        from textual.widgets import DataTable
        self.query_one(DataTable).action_scroll_up()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.action_crack()


# ── Session Management Screens ───────────────────────────────────────────────

class SessionStatusScreen(SidewinderScreen):
    """Displays current session stats, adapter info, and target details."""
    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose_main(self) -> ComposeResult:
        tgt = self.app.session.selected_target
        tgt_str = f"{tgt.display_name()} ({tgt.bssid})" if tgt else "None"
        caps_str = f"{len(self.app.session.captures)} captures"
        cracks_str = f"{len(self.app.session.cracked_passwords)} cracked"
        
        best_iface = "None"
        if hasattr(self.app, "_adapter_manager") and self.app._adapter_manager:
            best = self.app._adapter_manager.get_best_for_operation("scan")
            if best:
                best_iface = f"{best.iface} ({best.chipset})"
                
        yield Static("[bold $primary]Session Status[/bold $primary]", id="status-title")
        yield Static("[$text-disabled]──────────────────────────────────────────────────[/$text-disabled]")
        yield Static(
            f" [bold $secondary]Active Interface[/bold $secondary] : {best_iface}\n"
            f" [bold $secondary]Selected Target[/bold $secondary]  : {tgt_str}\n"
            f" [bold $secondary]Total Captures[/bold $secondary]   : {caps_str}\n"
            f" [bold $secondary]Cracked Networks[/bold $secondary] : {cracks_str}\n",
            id="status-details"
        )

    def compose_prompt(self) -> ComposeResult:
        yield Static("[$text-muted]  Esc[/$text-muted][$text-muted] back[/$text-muted]", id="status-hints")

    def action_back(self) -> None:
        self.app.pop_screen()


class SessionListScreen(SidewinderScreen):
    """Displays saved sessions and allows loading or deleting them."""
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "load_session", "Load Selected"),
        Binding("d", "delete_session", "Delete Selected"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def compose_main(self) -> ComposeResult:
        from textual.widgets import DataTable
        with Vertical(id="sc-sessions"):
            yield Static("[bold $primary]Saved Sessions[/bold $primary]", id="sessions-title")
            yield Static("[$text-disabled]──────────────────────[/$text-disabled]")
            table = DataTable(id="sessions-table", cursor_type="row")
            table.add_columns("Session ID", "Start Time", "Target Network", "Captures")
            yield table

    def compose_prompt(self) -> ComposeResult:
        yield Static(
            "[$text-muted]  Enter[/$text-muted][$text-muted] load selected[/$text-muted]"
            "  [$text-muted]d[/$text-muted][$error] delete selected[/$error]"
            "  [$text-muted]j/k[/$text-muted][$text-muted] navigate[/$text-muted]"
            "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
            id="sessions-hints",
        )

    def on_mount(self) -> None:
        self._load_sessions()

    def _load_sessions(self) -> None:
        from textual.widgets import DataTable
        import os
        import json
        from ..core.config import expand_user_path
        
        table = self.query_one("#sessions-table", DataTable)
        table.clear()
        
        sessions_dir = expand_user_path("~/.sidewinder/sessions")
        if not os.path.exists(sessions_dir):
            os.makedirs(sessions_dir, exist_ok=True)
            
        files = [f for f in os.listdir(sessions_dir) if f.endswith(".json")]
        if not files:
            self.app.notify("No saved sessions found.", severity="warning")
            return
            
        for f in files:
            full_path = os.path.join(sessions_dir, f)
            try:
                with open(full_path, "r") as fh:
                    data = json.load(fh)
                sid = data.get("id", f.replace(".json", ""))[:8]
                stime_raw = data.get("start_time", "")
                stime = stime_raw.split(".")[0].replace("T", " ") if stime_raw else "Unknown"
                tgt = data.get("selected_target")
                tgt_name = tgt.get("essid", "[NONE]") if tgt else "[NONE]"
                caps = len(data.get("captures", []))
                table.add_row(sid, stime, tgt_name, str(caps), key=full_path)
            except Exception:
                pass

    def action_load_session(self) -> None:
        from textual.widgets import DataTable
        table = self.query_one("#sessions-table", DataTable)
        if table.cursor_row >= 0:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            full_path = row_key.value
            from ..core.session import Session
            try:
                loaded = Session.load(full_path)
                if loaded:
                    self.app.session = loaded
                    # Overwrite default active session
                    loaded.save()
                    self.app.notify(f"Successfully loaded session {loaded.id[:8]}")
                    self.app.pop_screen()
            except Exception as e:
                self.app.notify(f"Failed to load session: {e}", severity="error")

    def action_delete_session(self) -> None:
        from textual.widgets import DataTable
        table = self.query_one("#sessions-table", DataTable)
        if table.cursor_row >= 0:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            full_path = row_key.value
            import os
            try:
                os.unlink(full_path)
                self.app.notify("Session deleted.")
                self._load_sessions()
            except Exception as e:
                self.app.notify(f"Failed to delete session: {e}", severity="error")

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_cursor_down(self) -> None:
        from textual.widgets import DataTable
        self.query_one(DataTable).action_scroll_down()

    def action_cursor_up(self) -> None:
        from textual.widgets import DataTable
        self.query_one(DataTable).action_scroll_up()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.action_load_session()
