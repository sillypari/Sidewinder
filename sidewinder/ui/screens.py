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


class MainMenuScreen(Screen):
    """Main menu screen — opencode-style numbered options."""

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

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="main-container"):
            yield Spacer(flex=1)
            with Center():
                yield LogoWidget(id="logo")
            yield Spacer(height=1)
            with Center():
                yield AdapterStatusWidget(id="adapter-status")
            yield Spacer(height=1)
            with Center():
                list_items = []
                for key, label, action in MAIN_MENU_ITEMS:
                    markup = rf"[$text-muted]\[[/$text-muted][bold $secondary]{key}[/bold $secondary][$text-muted]][/$text-muted]  [$text]{label}[/$text]"
                    list_items.append(ListItem(Label(markup), id=f"menu-{action}"))
                yield ListView(*list_items, id="menu")
            yield Spacer(height=1)
            with Center():
                yield Static(
                    "[$text-muted]  /[/$text-muted][$text-muted] command[/$text-muted]"
                    "  [$text-muted]?[/$text-muted][$text-muted] help[/$text-muted]"
                    "  [$text-muted]Esc[/$text-muted][$text-muted] quit[/$text-muted]",
                    id="hints",
                )
            yield Spacer(flex=1)
        yield Footer()

    def on_mount(self) -> None:
        self.update_timer = self.set_interval(1.0, self.update_adapter_status)
        # Give ListView focus so arrow keys work immediately
        self.query_one(ListView).focus()

    def on_unmount(self) -> None:
        if hasattr(self, "update_timer") and self.update_timer:
            self.update_timer.stop()


    def update_adapter_status(self) -> None:
        if hasattr(self.app, "_adapter_manager") and self.app._adapter_manager:
            best = self.app._adapter_manager.get_best_for_operation("scan")
            if best:
                try:
                    widget = self.query_one("#adapter-status", AdapterStatusWidget)
                    widget.adapter_name = best.iface
                    widget.adapter_status = best.status
                    widget.channel = "--"
                    widget.mode = best.current_mode
                except Exception:
                    pass
        self._refresh_menu_states()

    def _refresh_menu_states(self) -> None:
        """Update each menu item label with live state (§14.3 dense information)."""
        try:
            session = self.app.session
            lv = self.query_one("#menu", ListView)

            # Scan item — show network count if results exist
            scan_state = ""
            if session.scan_results:
                scan_state = f"  [$text-muted]● {len(session.scan_results)} nets[/$text-muted]"

            # Target item — show selected target name
            target_state = ""
            if session.selected_target:
                t = session.selected_target
                target_state = f"  [$text-muted]■ {t.display_name()[:12]}[/$text-muted]"

            # Crack item — show cracked count
            crack_state = ""
            if session.cracked_passwords:
                crack_state = f"  [$success]▣ {len(session.cracked_passwords)} found[/$success]"

            # View item — show capture file count
            view_state = ""
            if session.captures:
                view_state = f"  [$text-muted]{len(session.captures)} files[/$text-muted]"

            # Settings — show adapter mode
            settings_state = ""
            if hasattr(self.app, "_adapter_manager") and self.app._adapter_manager:
                best = self.app._adapter_manager.get_best_for_operation("scan")
                if best:
                    mode_col = "$secondary" if best.current_mode == "monitor" else "$text-muted"
                    settings_state = f"  [{mode_col}]{best.iface}[/{mode_col}]"

            states = [
                scan_state, target_state, crack_state, view_state,
                settings_state, "", "", "",
            ]
            menu_items = list(MAIN_MENU_ITEMS)

            for (key, label, action), state in zip(menu_items, states):
                markup = (
                    rf"[$text-muted]\[[/$text-muted][bold $secondary]{key}[/bold $secondary]"
                    rf"[$text-muted]][/$text-muted]  [$text]{label}[/$text]{state}"
                )
                try:
                    item = lv.get_child_by_id(f"menu-{action}")
                    if item:
                        label_widget = item.query_one(Label)
                        label_widget.update(markup)
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
        self.app.push_screen(CrackProgressScreen())

    def action_menu_4(self) -> None:
        self.app.push_screen(CaptureListScreen())

    def action_menu_5(self) -> None:
        self.app.push_screen(AdapterScreen())

    def action_menu_6(self) -> None:
        self.app.push_screen(CleanupScreen())

    def action_menu_7(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_menu_0(self) -> None:
        self.app.exit()

    def action_quit(self) -> None:
        self.app.exit()


# ── Adapter Screen ────────────────────────────────────────────────────────────

class AdapterScreen(Screen):
    """Shows all detected adapters and their status."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="adapter-screen-container"):
            yield Static(
                "[bold $primary]Hardware & Adapters[/bold $primary]",
                id="adapter-title",
            )
            table = DataTable(id="adapter-table", show_cursor=True)
            table.add_columns("Interface", "Chipset", "Driver", "Bands", "Monitor", "Inject", "Status")
            yield table
            yield Static(
                "  [$text-muted]r[/$text-muted][$text-muted] refresh[/$text-muted]  "
                "[$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
                id="adapter-hints",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.call_after_refresh(self._load_adapters)

    async def _load_adapters(self) -> None:
        from ..core.adapter import discover_all_adapters
        table = self.query_one("#adapter-table", DataTable)
        adapters = await discover_all_adapters()
        for a in adapters:
            mon = "[$success]YES[/$success]" if a.monitor_capable else "[$error]NO[/$error]"
            inj = "[$success]YES[/$success]" if a.injection_capable else "[$error]NO[/$error]"
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


# ── Scan Screen ───────────────────────────────────────────────────────────────

class ScanScreen(Screen):
    """WiFi scan results table — airodump-ng style with signal bars."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "select_target", "Select"),
        Binding("s", "stop_scan", "Stop"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    scanning: reactive[bool] = reactive(False)
    network_count: reactive[int] = reactive(0)
    elapsed: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        from .components import ScanStatsBar, StatusBar
        yield Header(show_clock=True)
        with Vertical(id="sc-scan"):
            with Horizontal(id="scan-header"):
                yield Static("[bold $primary]WiFi Scan[/bold $primary]", id="scan-title")
                yield ScanStatsBar(id="scan-stats")
            table = DataTable(id="scan-table", show_cursor=True)
            yield table
            yield Static(
                "[$text-muted]  Enter[/$text-muted][$text-muted] select[/$text-muted]"
                "  [$text-muted]s[/$text-muted][$text-muted] stop[/$text-muted]"
                "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
                id="scan-hints",
            )
        yield StatusBar(id="scan-status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.scanning = True
        self._timer = self.set_interval(1.0, self._tick)
        self.call_after_refresh(self._setup_columns)

        if hasattr(self.app, "_adapter_manager") and self.app._adapter_manager:
            adapter = self.app._adapter_manager.get_best_for_operation("scan")
            if adapter:
                from ..core.scanner import ScanEngine
                self._scan_engine = ScanEngine()

                async def run_scan():
                    try:
                        await self._scan_engine.scan(
                            mon_iface=adapter.iface,
                            on_network=lambda n: self.call_from_thread(self.add_network, n),
                            on_client=lambda c: self.call_from_thread(self.add_client, c),
                        )
                    except Exception as e:
                        self.app.notify(f"Scan failed: {e}", severity="error")

                import asyncio
                self.scan_task = asyncio.create_task(run_scan())

    def _setup_columns(self) -> None:
        table = self.query_one("#scan-table", DataTable)
        w, _ = self.app.size
        table.clear(columns=True)
        table.add_column("BSSID", width=17)
        table.add_column("CH", width=3)
        table.add_column("Signal", width=10)
        table.add_column("Rate", width=8)
        table.add_column("Privacy", width=7)
        table.add_column("Cipher", width=7)
        table.add_column("ESSID", width=20)
        if w >= 100:
            table.add_column("WPS", width=4)
            table.add_column("Clients", width=3)
        else:
            self.app.notify("Some columns hidden. Resize to 100+ for full view.", severity="warning")

    def on_resize(self, event) -> None:
        self.call_after_refresh(self._setup_columns)

    def on_unmount(self) -> None:
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

            sbar = self.query_one("#scan-status-bar", StatusBar)
            sbar.elapsed = f"{h:02d}:{m:02d}:{s:02d}"
            if hasattr(self.app, "_adapter_manager") and self.app._adapter_manager:
                best = self.app._adapter_manager.get_best_for_operation("scan")
                if best:
                    sbar.adapter = best.iface
                    sbar.mode = best.current_mode
                    sbar.channel = "--"
        except Exception:
            pass

    def add_network(self, network) -> None:
        """Add or update a network in the scan table."""
        # Persist to session
        existing = next((n for n in self.app.session.scan_results if n.bssid == network.bssid), None)
        if not existing:
            self.app.session.scan_results.append(network)

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
        self.action_stop_scan()
        if hasattr(self, "_timer"):
            self._timer.stop()
        self.app.pop_screen()

    def action_stop_scan(self) -> None:
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
                # Match from the active scan engine or current session scan results
                network = None
                if hasattr(self, "_scan_engine") and self._scan_engine:
                    network = next((n for n in self._scan_engine.networks if n.bssid == bssid), None)
                if not network:
                    network = next((n for n in self.app.session.scan_results if n.bssid == bssid), None)
                
                if network:
                    self.app.session.selected_target = network
                    screen_cls = globals().get("APDetailsScreen")
                    if screen_cls:
                        self.app.push_screen(screen_cls(target=network))


# ── Target Select Screen ──────────────────────────────────────────────────────

class TargetSelectScreen(Screen):
    """Select a target from previously scanned networks."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "select", "Select"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="sc-target"):
            yield Static("[bold $primary]Select Target Network[/bold $primary]", id="target-title")
            yield Static("[$text-muted]──────────────────────[/$text-muted]", id="target-divider")
            table = DataTable(id="target-table", show_cursor=True)
            table.add_columns("BSSID", "CH", "Signal", "Privacy", "ESSID", "Clients")
            yield table
            yield Static(
                "[$text-muted]  Enter[/$text-muted][$text-muted] select[/$text-muted]"
                "  [$text-muted]j/k[/$text-muted][$text-muted] navigate[/$text-muted]"
                "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
                id="target-hints",
            )
        yield Footer()

    def on_mount(self) -> None:
        """Populate table from session scan results."""
        self.call_after_refresh(self._load_scan_results)

    def _load_scan_results(self) -> None:
        table = self.query_one("#target-table", DataTable)
        networks = self.app.session.scan_results
        if not networks:
            self.notify("No scan results yet. Run a scan first.", severity="warning")
            return
        for network in networks:
            bar = signal_bar(network.signal)
            sc = signal_color(network.signal)
            pc = privacy_color(network.privacy)
            client_count = sum(
                1 for c in self.app.session.clients if c.bssid == network.bssid
            )
            table.add_row(
                f"[$text-muted]{network.bssid}[/$text-muted]",
                f"[$secondary]{network.channel}[/$secondary]",
                f"{bar} [{sc}]{network.signal}[/{sc}]",
                f"[{pc}]{network.privacy}[/{pc}]",
                f"[$text]{network.display_name()}[/$text]",
                str(client_count),
                key=network.bssid,
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


class CaptureMethodScreen(Screen):
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

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
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
                yield Static(
                    "[$text-muted]  1-5[/$text-muted][$text-muted] select[/$text-muted]"
                    "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
                    id="method-hints",
                )
            with Vertical(id="tooltip-panel"):
                # Initial render container
                yield Static("", id="tooltip-container")
        yield Footer()

    def on_mount(self) -> None:
        self.watch_selected_idx(self.selected_idx)

    def watch_selected_idx(self, idx: int) -> None:
        try:
            m = CAPTURE_METHODS[idx]
            container = self.query_one("#tooltip-panel", Vertical)
            # Remove old tooltip if exists
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

class CaptureProgressScreen(Screen):
    """Live capture progress with EAPOL M1-M4 tracker."""

    BINDINGS = [
        Binding("escape", "stop", "Stop"),
        Binding("ctrl+c", "stop", "Stop"),
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

    def compose(self) -> ComposeResult:
        from .components import AttackProgressPanel
        yield Header(show_clock=True)
        with Vertical(id="sc-capture"):
            yield Static(
                f"[bold $primary]Capturing Handshake[/bold $primary]",
                id="capture-title",
            )
            yield Static("[$text-disabled]──────────────────────────────────────────────────[/$text-disabled]")
            yield AttackProgressPanel(method=self.method, id="attack-panel")
            yield ProgressBar(id="capture-progress", total=100)
            yield Static(
                "[$text-muted]  Esc[/$text-muted][$text-muted] stop capture[/$text-muted]",
                id="capture-hints",
            )
        yield Footer()

    def on_mount(self) -> None:
        self._timer = self.set_interval(1.0, self._tick)

    def on_unmount(self) -> None:
        if hasattr(self, "_timer") and self._timer:
            self._timer.stop()

    def _tick(self) -> None:
        self.elapsed += 1
        try:
            panel = self.query_one("#attack-panel", AttackProgressPanel)
            panel.beacons = self.beacons
            panel.data_pkts = self.data_pkts
            panel.signal = self.signal
            panel.refresh()
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

class DeauthSelectScreen(Screen):
    """Select which clients to deauth with checkbox list."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "confirm", "Confirm"),
        Binding("space", "toggle", "Toggle"),
        Binding("a", "select_all", "Select All"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("plus", "rate_up", "Rate +"),
        Binding("minus", "rate_down", "Rate -"),
    ]

    rate: reactive[int] = reactive(10)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="sc-deauth"):
            yield Static("[bold $primary]Select Deauth Targets[/bold $primary]", id="deauth-title")
            yield Static("[$text-disabled]────────────────────[/$text-disabled]")
            table = DataTable(id="client-table", show_cursor=True)
            yield table
            yield Static(id="rate-display")
            yield Static(
                "[$text-muted]  Space[/$text-muted][$text-muted] toggle[/$text-muted]"
                "  [$text-muted]a[/$text-muted][$text-muted] select all[/$text-muted]"
                "  [$text-muted]+/-[/$text-muted][$text-muted] rate[/$text-muted]"
                "  [$text-muted]Enter[/$text-muted][$text-muted] confirm[/$text-muted]"
                "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
                id="deauth-hints",
            )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#client-table", DataTable)
        table.add_column("SEL", width=4)
        table.add_column("MAC", width=17)
        table.add_column("Vendor", width=15)
        table.add_column("Signal", width=10)
        table.add_column("Packets", width=6)
        self._update_rate_display()

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
            "[$success]*[/$success]",  # Default: selected
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

    def action_cursor_down(self) -> None:
        self.query_one(DataTable).action_scroll_down()

    def action_cursor_up(self) -> None:
        self.query_one(DataTable).action_scroll_up()


# ── Crack Progress Screen ─────────────────────────────────────────────────────

class CrackProgressScreen(Screen):
    """Real-time cracking progress with keys/sec, ETA, current key."""

    BINDINGS = [
        Binding("escape", "stop", "Stop"),
    ]

    keys_tested: reactive[int] = reactive(0)
    keys_total: reactive[int] = reactive(0)
    speed: reactive[float] = reactive(0.0)
    current_key: reactive[str] = reactive("")
    eta: reactive[str] = reactive("unknown")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="sc-crack"):
            yield Static("[bold $primary]Cracking Password[/bold $primary]", id="crack-title")
            yield Static("[$text-disabled]────────────────[/$text-disabled]")
            with Vertical(id="crack-stats-panel"):
                yield Static(id="crack-stats")
                yield ProgressBar(id="crack-progress", total=100)
            yield Static(
                "[$text-muted]  Esc[/$text-muted][$text-muted] stop cracking[/$text-muted]",
                id="crack-hints",
            )
        yield Footer()

    def on_mount(self) -> None:
        self._update_display()

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
        """Stop cracking and return to previous screen."""
        self.app.pop_screen()


# ── Result Screen ─────────────────────────────────────────────────────────────

class ResultScreen(Screen):
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

    def compose(self) -> ComposeResult:
        from .components import PasswordCard
        yield Header(show_clock=True)
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
            yield Spacer(height=1)
            with Center():
                yield Static(
                    "[$text-muted]  1[/$text-muted][$text-muted] save to file[/$text-muted]"
                    "  [$text-muted]2[/$text-muted][$text-muted] copy to clipboard[/$text-muted]"
                    "  [$text-muted]4[/$text-muted][$text-muted] attack another[/$text-muted]"
                    "  [$text-muted]6[/$text-muted][$text-muted] main menu[/$text-muted]",
                    id="result-hints",
                )
            yield Spacer(flex=1)
        yield Footer()

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

class ErrorScreen(Screen):
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

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="sc-error"):
            yield ErrorCard(
                severity=self._sev,
                what=self._what,
                why=self._why,
                how_to_fix=self._how,
                raw_error=self._raw,
            )
            yield Static(
                "[$text-muted]  Enter[/$text-muted][$text-muted] dismiss[/$text-muted]"
                "  [$text-muted]Esc[/$text-muted][$text-muted] dismiss[/$text-muted]",
                id="error-hints",
            )
        yield Footer()

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

TUTORIAL = TUTORIAL.replace(" [$text-muted]Press Esc or q to close[/$text-muted]\n", "")



class HelpScreen(Screen):
    """Full WiFi audit tutorial — opened with ? key."""

    BINDINGS = [
        Binding("escape", "back", "Close"),
        Binding("q", "back", "Close"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll(id="help-scroll"):
            yield Static(TUTORIAL, id="tutorial-text")
        yield Static(
            "[$text-muted]  Esc[/$text-muted][$text-muted] close[/$text-muted]"
            "  [$text-muted]q[/$text-muted][$text-muted] close[/$text-muted]",
            id="help-hints",
        )
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Session Resume ────────────────────────────────────────────────────────────

class ResumeScreen(Screen):
    """Session resume prompt — shown when a previous session exists.

    Displays logo, session summary and asks Y/n to resume.
    """

    BINDINGS = [
        Binding("y", "resume", "Resume"),
        Binding("n", "new_session", "New Session"),
        Binding("escape", "new_session", "New Session"),
    ]

    def __init__(self, session) -> None:
        super().__init__()
        self._session = session

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="sc-resume"):
            yield Spacer(flex=1)
            with Center():
                yield LogoWidget(id="logo")
            yield Spacer(height=2)
            with Center():
                yield Static("[bold $primary]Previous Session Found[/bold $primary]", id="resume-title")
            with Center():
                yield Static("[$text-disabled]─────────────────────[/$text-disabled]")
            scan_count = len(self._session.scan_results)
            target = self._session.selected_target
            target_name = target.display_name() if target else "None"
            captures = len(self._session.captures)
            cracked = len(self._session.cracked_passwords)
            with Center():
                yield Static(
                    f"[$text-muted]Session[/$text-muted]  [$text-muted]{self._session.id[:8]}...[/$text-muted]\n"
                    f"[$text-muted]Adapter[/$text-muted]  [$text-muted]{self._session.adapter or 'Not set'}[/$text-muted]\n"
                    f"[$text-muted]Scans  [/$text-muted]  [$text]{scan_count} networks[/$text]\n"
                    f"[$text-muted]Target [/$text-muted]  [$text]{target_name}[/$text]\n"
                    f"[$text-muted]Captures[/$text-muted]  [$text]{captures} files[/$text]\n"
                    f"[$text-muted]Cracked[/$text-muted]  [$success]{cracked} passwords[/$success]",
                    id="resume-summary",
                )
            yield Spacer(height=1)
            with Center():
                yield Static(
                    "[bold $success]Y[/bold $success]  [$text-muted]Resume this session[/$text-muted]\n"
                    "[bold $error]N[/bold $error]  [$text-muted]Start fresh[/$text-muted]",
                    id="resume-options",
                )
            yield Spacer(flex=1)
        yield Footer()

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

class CommandPaletteScreen(Screen):
    """Slash command palette overlay."""

    BINDINGS = [
        Binding("escape", "back", "Close"),
        Binding("enter", "submit", "Submit"),
    ]

    def compose(self) -> ComposeResult:
        from .app import SLASH_COMMANDS
        yield Header(show_clock=True)
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
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_changed(self, event) -> None:
        from .app import SLASH_COMMANDS
        val = event.value.lower()
        olist = self.query_one(OptionList)
        olist.clear_options()
        for cmd, desc in SLASH_COMMANDS.items():
            if val in cmd.lower() or val in desc.lower():
                olist.add_option(Option(f"{cmd} - {desc}", id=cmd))

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
        elif cmd_id == "/capture":
            self.app.push_screen(CaptureMethodScreen())
        elif cmd_id == "/crack":
            self.app.push_screen(CrackProgressScreen())
        elif cmd_id == "/adapter":
            self.app.push_screen(AdapterScreen())
        elif cmd_id == "/help":
            self.app.push_screen(HelpScreen())
        elif cmd_id == "/cleanup":
            self.app.push_screen(CleanupScreen())
        elif cmd_id == "/status":
            # Show current adapter status as a notification
            try:
                if hasattr(self.app, "_adapter_manager") and self.app._adapter_manager:
                    best = self.app._adapter_manager.get_best_for_operation("scan")
                    if best:
                        self.app.notify(
                            f"Adapter: {best.iface} | Mode: {best.current_mode} | Status: {best.status}",
                            severity="information",
                        )
                    else:
                        self.app.notify("No adapter available", severity="warning")
                else:
                    self.app.notify("Adapter manager not initialised", severity="warning")
            except Exception as e:
                self.app.notify(f"Status error: {e}", severity="error")
        elif cmd_id == "/theme":
            self.app.push_screen(ThemeSelectScreen())
        elif cmd_id == "/compact":
            if hasattr(self.app, "action_toggle_compact"):
                self.app.action_toggle_compact()
        elif cmd_id == "/quit":
            self.app.exit()
        elif cmd_id == "/session":
            self.app.notify("Session management not yet implemented.", severity="warning")
        else:
            self.app.notify(f"Command {cmd_id} not wired.", severity="warning")



# ── Theme Selector ────────────────────────────────────────────────────────────

class ThemeSelectScreen(Screen):
    """Modal screen for selecting visual themes with live preview."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "select", "Select"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="theme-select-container"):
            yield Static(
                "[bold $primary]Select Visual Theme[/bold $primary]",
                id="theme-title",
            )
            themes = list(self.app.available_themes.keys())
            options = [Option(theme, id=theme) for theme in themes]
            yield OptionList(*options, id="theme-list")
        yield Footer()

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

    def action_cancel(self) -> None:
        """Cancel selection and restore original theme."""
        self.app.theme = self._original_theme
        self.app.pop_screen()

    def action_select(self) -> None:
        """Confirm selection and save theme to config."""
        selected_theme = self.query_one(OptionList).get_option_at_index(
            self.query_one(OptionList).highlighted
        ).id
        self.app.theme = selected_theme
        self.app.settings.theme = selected_theme
        self.app.settings.save()
        self.app.notify(f"Theme set to {selected_theme}", severity="success")
        self.app.pop_screen()


# ── Wordlist Picker ───────────────────────────────────────────────────────────

class WordlistPickerScreen(Screen):
    """File browser for selecting wordlists."""
    
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "select", "Select"),
    ]

    def compose(self) -> ComposeResult:
        from textual.widgets import DirectoryTree
        import os

        yield Header(show_clock=True)
        with Vertical(id="sc-wordlist"):
            yield Static("[bold $primary]Select Wordlist[/bold $primary]", id="wordlist-title")
            yield Static("[$text-disabled]──────────────[/$text-disabled]")
            path = "/usr/share/wordlists" if os.path.exists("/usr/share/wordlists") else "."
            yield DirectoryTree(path, id="wordlist-tree")
            yield Static(
                "[$text-muted]  Enter[/$text-muted][$text-muted] select[/$text-muted]"
                "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
                id="wordlist-hints",
            )
        yield Footer()

    def on_directory_tree_file_selected(self, event) -> None:
        self.app.notify(f"Selected: {event.path}")
        self.dismiss(str(event.path))

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Engine Picker ─────────────────────────────────────────────────────────────

class EnginePickerScreen(Screen):
    """Select cracking engine (Aircrack-ng vs Hashcat)."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("1", "select_aircrack", "Aircrack-ng (CPU)"),
        Binding("2", "select_hashcat", "Hashcat (GPU)"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
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
            yield Static(
                "[$text-muted]  1/2[/$text-muted][$text-muted] select engine[/$text-muted]"
                "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
                id="engine-hints",
            )
        yield Footer()

    def action_select_aircrack(self) -> None:
        self.dismiss("aircrack")

    def action_select_hashcat(self) -> None:
        self.dismiss("hashcat")

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Cleanup Screen ────────────────────────────────────────────────────────────

class CleanupScreen(Screen):
    """Visual checklist for restored services/files."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "run_cleanup", "Run Cleanup"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
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
            yield Static(
                "[$text-muted]  Enter[/$text-muted][$success] confirm cleanup[/$success]"
                "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
                id="cleanup-hints",
            )
        yield Footer()

    async def action_run_cleanup(self) -> None:
        if hasattr(self.app, "action_cleanup"):
            await self.app.action_cleanup()
        self.app.pop_screen()

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Service Check Screen ──────────────────────────────────────────────────────

class ServiceCheckScreen(Screen):
    """Interface to manually kill/restore services."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("K", "kill_services", "Kill Conflicting"),
        Binding("r", "restore_services", "Restore Services"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="sc-services"):
            yield Static("[bold $primary]Service Management[/bold $primary]", id="services-title")
            yield Static("[$text-disabled]──────────────────[/$text-disabled]")
            yield Static(
                "[$text-muted]Checking for conflicting services...[/$text-muted]",
                id="services-status",
            )
            yield ListView(id="service-list")
            yield Static(
                "[$text-muted]  K[/$text-muted][$error] kill conflicting[/$error]"
                "  [$text-muted]r[/$text-muted][$success] restore[/$success]"
                "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
                id="services-hints",
            )
        yield Footer()

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

    def action_cursor_down(self) -> None:
        try:
            self.query_one(ListView).scroll_down()
        except Exception:
            pass


# ── Monitor Setup Screen ──────────────────────────────────────────────────────

class MonitorSetupScreen(Screen):
    """Real-time feedback for interface mode switching."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("e", "enable_monitor", "Enable Monitor"),
        Binding("d", "disable_monitor", "Disable Monitor"),
    ]

    def __init__(self, adapter_name: str):
        super().__init__()
        self.adapter_name = adapter_name

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
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
            yield Static(
                "[$text-muted]  e[/$text-muted][$success] enable monitor[/$success]"
                "  [$text-muted]d[/$text-muted][$error] disable monitor[/$error]"
                "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
                id="monitor-hints",
            )
        yield Footer()

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

class ScanOptionsScreen(Screen):
    """Form inputs for band selection, channels, and hidden SSIDs."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "start_scan", "Start Scan"),
    ]

    def compose(self) -> ComposeResult:
        from textual.widgets import Checkbox, Input
        yield Header(show_clock=True)
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
            yield Static(
                "[$text-muted]  Enter[/$text-muted][$text-muted] start scan[/$text-muted]"
                "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
                id="scanopts-hints",
            )
        yield Footer()

    def action_start_scan(self) -> None:
        # In a real app, we'd pass these options to the scan engine.
        self.app.push_screen(ScanScreen())

    def action_back(self) -> None:
        self.app.pop_screen()


# ── AP Details Screen ─────────────────────────────────────────────────────────

class APDetailsScreen(Screen):
    """Detailed drill-down for a selected target AP."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("a", "attack", "Attack this AP"),
    ]

    def __init__(self, target) -> None:
        super().__init__()
        self.target = target

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
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
            yield Static(
                "[$text-muted]  a[/$text-muted][$text-muted] attack this AP[/$text-muted]"
                "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
                id="apdetails-hints",
            )
        yield Footer()

    def action_attack(self) -> None:
        self.app.push_screen(CaptureMethodScreen())

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Capture List Screen ───────────────────────────────────────────────────────

class CaptureListScreen(Screen):
    """List saved capture files and allow selection for cracking."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "crack", "Crack Selected"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def compose(self) -> ComposeResult:
        from textual.widgets import DataTable
        yield Header(show_clock=True)
        with Vertical(id="sc-captures"):
            yield Static("[bold $primary]Saved Captures[/bold $primary]", id="captures-title")
            yield Static("[$text-disabled]──────────────[/$text-disabled]")
            table = DataTable(id="captures-table", cursor_type="row")
            table.add_columns("Filename", "Size", "Modified")
            yield table
            yield Static(
                "[$text-muted]  Enter[/$text-muted][$text-muted] crack selected[/$text-muted]"
                "  [$text-muted]j/k[/$text-muted][$text-muted] navigate[/$text-muted]"
                "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
                id="captures-hints",
            )
        yield Footer()

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
            # We assume it's a valid capture. Push to engine picker or crack screen.
            # In a full flow we would set session target or pass filename.
            self.app.notify(f"Selected {full_path} for cracking.", severity="information")
            self.app.push_screen(CrackProgressScreen())
            
    def action_back(self) -> None:
        self.app.pop_screen()
        
    def action_cursor_down(self) -> None:
        from textual.widgets import DataTable
        self.query_one(DataTable).action_scroll_down()

    def action_cursor_up(self) -> None:
        from textual.widgets import DataTable
        self.query_one(DataTable).action_scroll_up()


# ── Session Status Screen ───────────────────────────────────────────────────────

class SessionStatusScreen(Screen):
    """Displays current session stats, adapter info, and target details."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        tgt = self.app.session.selected_target
        tgt_str = f"{tgt.display_name()} ({tgt.bssid})" if tgt else "None"
        caps_str = f"{len(self.app.session.captures)} captures"
        cracks_str = f"{len(self.app.session.cracked_passwords)} cracked"

        best_iface = "None"
        if hasattr(self.app, "_adapter_manager") and self.app._adapter_manager:
            best = self.app._adapter_manager.get_best_for_operation("scan")
            if best:
                best_iface = f"{best.iface} ({best.chipset})"

        with Vertical(id="sc-status"):
            yield Static("[bold $primary]Session Status[/bold $primary]", id="status-title")
            yield Static("[$text-disabled]──────────────────────────────[/$text-disabled]")
            yield Static(
                f" [bold $secondary]Active Interface[/bold $secondary] : {best_iface}\n"
                f" [bold $secondary]Selected Target[/bold $secondary]  : {tgt_str}\n"
                f" [bold $secondary]Total Captures[/bold $secondary]   : {caps_str}\n"
                f" [bold $secondary]Cracked Networks[/bold $secondary] : {cracks_str}\n",
                id="status-details"
            )
            yield Static("[$text-muted]  Esc[/$text-muted][$text-muted] back[/$text-muted]", id="status-hints")
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Session List Screen ─────────────────────────────────────────────────────────

class SessionListScreen(Screen):
    """Displays saved sessions and allows loading or deleting them."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "load_session", "Load Selected"),
        Binding("d", "delete_session", "Delete Selected"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def compose(self) -> ComposeResult:
        from textual.widgets import DataTable
        yield Header(show_clock=True)
        with Vertical(id="sc-sessions"):
            yield Static("[bold $primary]Saved Sessions[/bold $primary]", id="sessions-title")
            yield Static("[$text-disabled]──────────────────────[/$text-disabled]")
            table = DataTable(id="sessions-table", cursor_type="row")
            table.add_columns("Session ID", "Start Time", "Target Network", "Captures")
            yield table
            yield Static(
                "[$text-muted]  Enter[/$text-muted][$text-muted] load selected[/$text-muted]"
                "  [$text-muted]d[/$text-muted][$error] delete selected[/$error]"
                "  [$text-muted]j/k[/$text-muted][$text-muted] navigate[/$text-muted]"
                "  [$text-muted]Esc[/$text-muted][$text-muted] back[/$text-muted]",
                id="sessions-hints",
            )
        yield Footer()

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
            try:
                import os
                os.remove(full_path)
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
