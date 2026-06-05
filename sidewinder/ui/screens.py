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
    EAPOLTracker,
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
            yield Spacer(height=4)
            with Center():
                yield LogoWidget(id="logo")
            yield Spacer(height=1)
            with Center():
                yield AdapterStatusWidget(id="adapter-status")
            yield Spacer(height=1)
            with Center():
                list_items = []
                for key, label, action in MAIN_MENU_ITEMS:
                    t = Text()
                    t.append(" [", style="#585b70")
                    t.append(key, style="bold #cba6f7")   # mauve — key highlight
                    t.append("]", style="#585b70")
                    t.append(f"  {label}", style="#a6adc8")
                    list_items.append(ListItem(Label(t), id=f"menu-{action}"))
                yield ListView(*list_items, id="menu")
            yield Spacer(height=1)
            with Center():
                yield Static(
                    "[#585b70]  /[/#585b70][#a6adc8] command[/#a6adc8]"
                    "  [#585b70]?[/#585b70][#a6adc8] help[/#a6adc8]"
                    "  [#585b70]Esc[/#585b70][#a6adc8] quit[/#a6adc8]",
                    id="hints",
                )
            yield Spacer(flex=1)
        yield Footer()

    def on_mount(self) -> None:
        self.update_timer = self.set_interval(1.0, self.update_adapter_status)
        # Give ListView focus so arrow keys work immediately
        self.query_one(ListView).focus()

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
            if hasattr(self.app, "action_cleanup"):
                self.app.action_cleanup()
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

    def action_menu_5(self) -> None:
        self.app.push_screen(AdapterScreen())

    async def action_menu_6(self) -> None:
        if hasattr(self.app, "action_cleanup"):
            await self.app.action_cleanup()

    def action_menu_7(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_menu_0(self) -> None:
        self.app.exit()

    def action_quit(self) -> None:
        self.app.exit()

    # Also handle menu_4 for view
    def action_menu_4(self) -> None:
        self.app.push_screen(CaptureListScreen())


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
                "[bold #cba6f7]Hardware & Adapters[/bold #cba6f7]",
                id="adapter-title",
            )
            table = DataTable(id="adapter-table", show_cursor=True)
            table.add_columns("Interface", "Chipset", "Driver", "Bands", "Monitor", "Inject", "Status")
            yield table
            yield Static(
                "  [#585b70]r[/#585b70][#a6adc8] refresh[/#a6adc8]  "
                "[#585b70]Esc[/#585b70][#a6adc8] back[/#a6adc8]",
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


# ── Scan Screen ───────────────────────────────────────────────────────────────

class ScanScreen(Screen):
    """WiFi scan results table — airodump-ng style with signal bars."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "select_target", "Select"),
        Binding("s", "stop_scan", "Stop"),
    ]

    scanning: reactive[bool] = reactive(False)
    network_count: reactive[int] = reactive(0)
    elapsed: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        from .components import ScanStatsBar, StatusBar
        yield Header(show_clock=True)
        with Vertical(id="sc-scan"):
            with Horizontal(id="scan-header"):
                yield Static("[bold #cba6f7]WiFi Scan[/bold #cba6f7]", id="scan-title")
                yield ScanStatsBar(id="scan-stats")
            table = DataTable(id="scan-table", show_cursor=True)
            yield table
            yield Static(
                "[#585b70]  Enter[/#585b70][#a6adc8] select[/#a6adc8]"
                "  [#585b70]s[/#585b70][#a6adc8] stop[/#a6adc8]"
                "  [#585b70]Esc[/#585b70][#a6adc8] back[/#a6adc8]",
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
                        await self._scan_engine.scan(mon_iface=adapter.iface, on_network=lambda n: self.call_from_thread(self.add_network, n))
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

    def _tick(self) -> None:
        if self.scanning:
            self.elapsed += 1
        h, m, s = self.elapsed // 3600, (self.elapsed % 3600) // 60, self.elapsed % 60
        stats = self.query_one("#scan-stats", ScanStatsBar)
        stats.networks = self.network_count
        stats.clients = sum(1 for c in self.app.session.clients)
        stats.elapsed = f"{m:02d}:{s:02d}"

        # Update status bar
        sbar = self.query_one("#scan-status-bar", StatusBar)
        sbar.elapsed = f"{h:02d}:{m:02d}:{s:02d}"
        if hasattr(self.app, "_adapter_manager") and self.app._adapter_manager:
            best = self.app._adapter_manager.get_best_for_operation("scan")
            if best:
                sbar.adapter = best.iface
                sbar.mode = best.current_mode
                sbar.channel = str(best.current_mode) # or whatever the adapter channel is

    def _update_status(self) -> None:
        pass

    def add_network(self, network) -> None:
        """Add or update a network in the scan table."""
        table = self.query_one("#scan-table", DataTable)
        bar = signal_bar(network.signal)
        sc = signal_color(network.signal)
        pc = privacy_color(network.privacy)
        row_key = network.bssid
        w, _ = self.app.size

        row_data = [
            f"[#585b70]{network.bssid}[/#585b70]",
            f"[#89dceb]{network.channel}[/#89dceb]",
            f"{bar} [{sc}]{network.signal}[/{sc}]",
            "",
            f"[{pc}]{network.privacy}[/{pc}]",
            network.cipher,
            f"[#cdd6f4]{network.display_name()}[/#cdd6f4]"
        ]
        if w >= 100:
            row_data.append("[#a6e3a1]✓[/#a6e3a1]" if network.wps else "")
            row_data.append("")

        try:
            for i, data in enumerate(row_data):
                col_key = list(table.columns.keys())[i]
                table.update_cell(row_key, col_key, data, update_width=False)
        except Exception:
            table.add_row(*row_data, key=row_key)

        self.network_count = len(table.rows)

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
            yield Static("[bold #cba6f7]Select Target Network[/bold #cba6f7]", id="target-title")
            yield Static("[#585b70]──────────────────────[/#585b70]", id="target-divider")
            table = DataTable(id="target-table", show_cursor=True)
            table.add_columns("BSSID", "CH", "Signal", "Privacy", "ESSID", "Clients")
            yield table
            yield Static(
                "[#585b70]  Enter[/#585b70][#a6adc8] select[/#a6adc8]"
                "  [#585b70]j/k[/#585b70][#a6adc8] navigate[/#a6adc8]"
                "  [#585b70]Esc[/#585b70][#a6adc8] back[/#a6adc8]",
                id="target-hints",
            )
        yield Footer()

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
                yield Static("[bold #cba6f7]Capture Method[/bold #cba6f7]", id="method-title")
                yield Static("[#45475a]──────────────[/#45475a]")
                for m in CAPTURE_METHODS:
                    risk_colors = {"safe": "#a6e3a1", "caution": "#f9e2af", "dangerous": "#f38ba8"}
                    rc = risk_colors.get(m["risk_level"], "#cdd6f4")
                    t = Text()
                    t.append(" [", style="#585b70")
                    t.append(m["key"], style="bold #cba6f7")
                    t.append("] ", style="#585b70")
                    t.append(m["name"], style="bold #cdd6f4")
                    t.append(f"\n    {m['short']}", style="#a6adc8")
                    t.append(f"\n    Risk: ", style="#585b70")
                    t.append(m['risk_level'].upper(), style=rc)
                    yield Static(t, id=f"method-{m['key']}")
                yield Static(
                    "[#585b70]  1-5[/#585b70][#a6adc8] select[/#a6adc8]"
                    "  [#585b70]Esc[/#585b70][#a6adc8] back[/#a6adc8]",
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
                f"[bold #cba6f7]Capturing Handshake[/bold #cba6f7]",
                id="capture-title",
            )
            yield Static("[#45475a]──────────────────────────────────────────────────[/#45475a]")
            yield AttackProgressPanel(method=self.method, id="attack-panel")
            yield ProgressBar(id="capture-progress", total=100)
            yield Static(
                "[#585b70]  Esc[/#585b70][#a6adc8] stop capture[/#a6adc8]",
                id="capture-hints",
            )
        yield Footer()

    def on_mount(self) -> None:
        self._timer = self.set_interval(1.0, self._tick)

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
        Binding("plus", "rate_up", "Rate +"),
        Binding("minus", "rate_down", "Rate -"),
    ]

    rate: reactive[int] = reactive(10)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="sc-deauth"):
            yield Static("[bold #cba6f7]Select Deauth Targets[/bold #cba6f7]", id="deauth-title")
            yield Static("[#45475a]────────────────────[/#45475a]")
            table = DataTable(id="client-table", show_cursor=True)
            yield table
            yield Static(id="rate-display")
            yield Static(
                "[#585b70]  Space[/#585b70][#a6adc8] toggle[/#a6adc8]"
                "  [#585b70]a[/#585b70][#a6adc8] select all[/#a6adc8]"
                "  [#585b70]+/-[/#585b70][#a6adc8] rate[/#a6adc8]"
                "  [#585b70]Enter[/#585b70][#a6adc8] confirm[/#a6adc8]"
                "  [#585b70]Esc[/#585b70][#a6adc8] back[/#a6adc8]",
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
        rd.update(f"[#585b70]  Deauth rate[/#585b70]  [#89b4fa]{self.rate}[/#89b4fa][#a6adc8] frames/burst[/#a6adc8]  [#585b70]+/- to adjust[/#585b70]")

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
            "[#a6e3a1]*[/#a6e3a1]",  # Default: selected
            f"[#585b70]{mac}[/#585b70]",
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
            new_val = "[#585b70]·[/#585b70]" if "*" in str(current) else "[#a6e3a1]*[/#a6e3a1]"
            table.update_cell(row_key, col_key, new_val, update_width=False)

    def action_select_all(self) -> None:
        table = self.query_one("#client-table", DataTable)
        col_key = list(table.columns.keys())[0]
        for row_key in table.rows:
            table.update_cell(row_key, col_key, "[#a6e3a1]*[/#a6e3a1]", update_width=False)

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
            yield Static("[bold #cba6f7]Cracking Password[/bold #cba6f7]", id="crack-title")
            yield Static("[#45475a]────────────────[/#45475a]")
            with Vertical(id="crack-stats-panel"):
                yield Static(id="crack-stats")
                yield ProgressBar(id="crack-progress", total=100)
            yield Static(
                "[#585b70]  Esc[/#585b70][#a6adc8] stop cracking[/#a6adc8]",
                id="crack-hints",
            )
        yield Footer()

    def on_mount(self) -> None:
        self._update_display()

    def _update_display(self) -> None:
        stats = self.query_one("#crack-stats", Static)
        pct = (self.keys_tested / self.keys_total * 100) if self.keys_total > 0 else 0
        stats.update(
            f"[#585b70]Keys tested[/#585b70]  [#89dceb]{self.keys_tested:,}[/#89dceb][#585b70] / [/#585b70][#cdd6f4]{self.keys_total:,}[/#cdd6f4]\n"
            f"[#585b70]Speed      [/#585b70]  [#89dceb]{self.speed:,.0f}[/#89dceb][#a6adc8] keys/sec[/#a6adc8]\n"
            f"[#585b70]ETA        [/#585b70]  [#89dceb]{self.eta}[/#89dceb]\n"
            f"[#585b70]Current    [/#585b70]  [#585b70]{self.current_key or '...'}[/#585b70]\n"
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
        # Move to Wordlist Picker to start cracking if we captured something
        if self.app.session.captures:
            self.app.push_screen(WordlistPickerScreen())
        else:
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
                    "[#585b70]  1[/#585b70][#a6adc8] save to file[/#a6adc8]"
                    "  [#585b70]2[/#585b70][#a6adc8] copy to clipboard[/#a6adc8]"
                    "  [#585b70]4[/#585b70][#a6adc8] attack another[/#a6adc8]"
                    "  [#585b70]6[/#585b70][#a6adc8] main menu[/#a6adc8]",
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
                "[#585b70]  Enter[/#585b70][#a6adc8] dismiss[/#a6adc8]"
                "  [#585b70]Esc[/#585b70][#a6adc8] dismiss[/#a6adc8]",
                id="error-hints",
            )
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Help Screen ───────────────────────────────────────────────────────────────

TUTORIAL = """\
 [#89b4fa]┌─ Welcome to Sidewinder ──────────────────────────────────────────┐[/#89b4fa]
 [#89b4fa]│[/#89b4fa]  A native Linux WiFi audit tool. Zero bloat, terminal-first.   [#89b4fa]│[/#89b4fa]
 [#89b4fa]└──────────────────────────────────────────────────────────────────┘[/#89b4fa]

 [#cba6f7]Phase 1 · Scan[/#cba6f7]
 [#45475a]──────────────[/#45475a]
   [#585b70]1.[/#585b70]  Press [bold #cba6f7][1][/bold #cba6f7] from the main menu to start a live scan
   [#585b70]2.[/#585b70]  Networks appear automatically (auto-hops all channels)
   [#585b70]3.[/#585b70]  Press [bold #cdd6f4]Enter[/bold #cdd6f4] on a network to select it as the target
   [#585b70]4.[/#585b70]  Press [bold #cdd6f4]s[/bold #cdd6f4] to stop scanning and move to capture

 [#cba6f7]Phase 2 · Capture[/#cba6f7]
 [#45475a]─────────────────[/#45475a]
   [#585b70]1.[/#585b70]  Choose your method:
       [bold #cba6f7][1][/bold #cba6f7]  [#a6e3a1]Passive[/#a6e3a1]  — Listen quietly for a natural handshake
       [bold #cba6f7][2][/bold #cba6f7]  [#f9e2af]Deauth[/#f9e2af]   — Force clients off, capture handshake fast
   [#585b70]2.[/#585b70]  Watch the [#89b4fa]EAPOL M1→M2→M3→M4[/#89b4fa] tracker fill in
   [#585b70]3.[/#585b70]  Capture stops automatically when handshake is complete

 [#cba6f7]Phase 3 · Crack[/#cba6f7]
 [#45475a]───────────────[/#45475a]
   [#585b70]1.[/#585b70]  Pick a wordlist (Sidewinder auto-discovers system lists)
   [#585b70]2.[/#585b70]  Choose engine: [#89dceb]aircrack-ng[/#89dceb] (CPU) or [#cba6f7]hashcat[/#cba6f7] (GPU)
   [#585b70]3.[/#585b70]  Watch the progress bar and key-rate counter
   [#585b70]4.[/#585b70]  Password appears in [bold #a6e3a1]green[/bold #a6e3a1] when found

 [#cba6f7]Phase 4 · Cleanup[/#cba6f7]
 [#45475a]─────────────────[/#45475a]
   [#585b70]1.[/#585b70]  Press [bold #cba6f7][6][/bold #cba6f7] from the main menu
   [#585b70]2.[/#585b70]  Confirm capture file deletion
   [#585b70]3.[/#585b70]  NetworkManager and wpa_supplicant are restored automatically
   [#585b70]4.[/#585b70]  Exit safely

 [#cba6f7]Keyboard Reference[/#cba6f7]
 [#45475a]──────────────────[/#45475a]
   [bold #cdd6f4]j / k[/bold #cdd6f4]      Navigate up / down
   [bold #cdd6f4]Enter[/bold #cdd6f4]      Select or confirm
   [bold #cdd6f4]Esc[/bold #cdd6f4]        Back or cancel
   [bold #cdd6f4]/[/bold #cdd6f4]          Open command palette
   [bold #cdd6f4]?[/bold #cdd6f4]          This help screen
   [bold #cdd6f4]1 – 7[/bold #cdd6f4]      Quick menu access
   [bold #cdd6f4]s[/bold #cdd6f4]          Stop active scan
   [bold #cdd6f4]Space[/bold #cdd6f4]      Toggle checkbox (deauth screen)
   [bold #cdd6f4]a[/bold #cdd6f4]          Select all (deauth screen)

 [#cba6f7]Adapter Priority[/#cba6f7]
 [#45475a]────────────────[/#45475a]
   [#a6e3a1]1st[/#a6e3a1]  RTL8821AU — Full monitor + injection + 5GHz
   [#f9e2af]2nd[/#f9e2af]  RT5370    — 2.4GHz, reliable, no extra driver needed
   [#f38ba8]3rd[/#f38ba8]  MT7902    — Internet only, no injection

 [#585b70]Press Esc or q to close[/#585b70]
"""


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
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Session Resume ────────────────────────────────────────────────────────────

class ResumeScreen(Screen):
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

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="sc-resume"):
            yield Static("[bold #cba6f7]Previous Session Found[/bold #cba6f7]", id="resume-title")
            yield Static("[#45475a]─────────────────────[/#45475a]")
            scan_count = len(self._session.scan_results)
            target = self._session.selected_target
            target_name = target.display_name() if target else "None"
            captures = len(self._session.captures)
            cracked = len(self._session.cracked_passwords)
            yield Static(
                f"[#585b70]  Session [/#585b70]  [#a6adc8]{self._session.id[:8]}...[/#a6adc8]\n"
                f"[#585b70]  Adapter [/#585b70]  [#a6adc8]{self._session.adapter or 'Not set'}[/#a6adc8]\n"
                f"[#585b70]  Scans   [/#585b70]  [#cdd6f4]{scan_count} networks[/#cdd6f4]\n"
                f"[#585b70]  Target  [/#585b70]  [#cdd6f4]{target_name}[/#cdd6f4]\n"
                f"[#585b70]  Captures[/#585b70]  [#cdd6f4]{captures} files[/#cdd6f4]\n"
                f"[#585b70]  Cracked [/#585b70]  [#a6e3a1]{cracked} passwords[/#a6e3a1]",
                id="resume-summary",
            )
            yield Static(
                "[bold #a6e3a1]  Y[/bold #a6e3a1][#a6adc8]  Resume this session[/#a6adc8]\n"
                "[bold #f38ba8]  N[/bold #f38ba8][#a6adc8]  Start fresh[/#a6adc8]",
                id="resume-options",
            )
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
                "[bold #cba6f7]Command Palette[/bold #cba6f7]",
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
        elif cmd_id == "/help":
            self.app.push_screen(HelpScreen())
        elif cmd_id == "/cleanup":
            if hasattr(self.app, "action_cleanup"):
                self.app.action_cleanup()
        elif cmd_id == "/theme":
            current_theme = self.app.theme
            next_theme = "classic" if current_theme == "opencode" else "opencode"
            self.app.theme = next_theme
            self.app.notify(f"Theme changed to {next_theme}", severity="information")
        elif cmd_id == "/quit":
            self.app.exit()
        else:
            self.app.notify(f"Command {cmd_id} not fully wired yet.", severity="warning")


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
            yield Static("[bold #cba6f7]Select Wordlist[/bold #cba6f7]", id="wordlist-title")
            yield Static("[#45475a]──────────────[/#45475a]")
            path = "/usr/share/wordlists" if os.path.exists("/usr/share/wordlists") else "."
            yield DirectoryTree(path, id="wordlist-tree")
            yield Static(
                "[#585b70]  Enter[/#585b70][#a6adc8] select[/#a6adc8]"
                "  [#585b70]Esc[/#585b70][#a6adc8] back[/#a6adc8]",
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
            yield Static("[bold #cba6f7]Select Cracking Engine[/bold #cba6f7]", id="engine-title")
            yield Static("[#45475a]──────────────────────[/#45475a]")
            yield Static(
                " [#585b70][[/#585b70][bold #cba6f7]1[/bold #cba6f7][#585b70]][/#585b70]  "
                "[#cdd6f4]Aircrack-ng[/#cdd6f4][#a6adc8]  CPU-based, standard[/#a6adc8]\n"
                " [#585b70][[/#585b70][bold #cba6f7]2[/bold #cba6f7][#585b70]][/#585b70]  "
                "[#cdd6f4]Hashcat[/#cdd6f4][#a6adc8]     GPU-based, requires CUDA/ROCm[/#a6adc8]\n",
                id="engine-options",
            )
            yield Static(
                "[#585b70]  1/2[/#585b70][#a6adc8] select engine[/#a6adc8]"
                "  [#585b70]Esc[/#585b70][#a6adc8] back[/#a6adc8]",
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
            yield Static("[bold #cba6f7]System Cleanup[/bold #cba6f7]", id="cleanup-title")
            yield Static("[#45475a]──────────────[/#45475a]")
            yield Static(
                "[#a6adc8]The following actions will be performed:[/#a6adc8]\n\n"
                "  [#585b70][ ][/#585b70]  Restore NetworkManager / wpa_supplicant\n"
                "  [#585b70][ ][/#585b70]  Disable Monitor Mode\n"
                "  [#585b70][ ][/#585b70]  Terminate background attack processes\n"
                "  [#585b70][ ][/#585b70]  Clear temporary capture files (/tmp/)\n",
                id="cleanup-body",
            )
            yield Static(
                "[#585b70]  Enter[/#585b70][#a6e3a1] confirm cleanup[/#a6e3a1]"
                "  [#585b70]Esc[/#585b70][#a6adc8] back[/#a6adc8]",
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
        Binding("k", "kill_services", "Kill Conflicting"),
        Binding("r", "restore_services", "Restore Services"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="sc-services"):
            yield Static("[bold #cba6f7]Service Management[/bold #cba6f7]", id="services-title")
            yield Static("[#45475a]──────────────────[/#45475a]")
            yield Static(
                "[#a6adc8]Checking for conflicting services...[/#a6adc8]",
                id="services-status",
            )
            yield ListView(id="service-list")
            yield Static(
                "[#585b70]  k[/#585b70][#f38ba8] kill conflicting[/#f38ba8]"
                "  [#585b70]r[/#585b70][#a6e3a1] restore[/#a6e3a1]"
                "  [#585b70]Esc[/#585b70][#a6adc8] back[/#a6adc8]",
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
            await self.app._service_manager.restore_services()
            self.app.notify("Services restored.")
            await self._load_services()

    def action_back(self) -> None:
        self.app.pop_screen()


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
                f"[bold #cba6f7]Monitor Mode[/bold #cba6f7]  "
                f"[#585b70]adapter[/#585b70] [#89dceb]{self.adapter_name}[/#89dceb]",
                id="monitor-title",
            )
            yield Static("[#45475a]──────────────────────────────[/#45475a]")
            yield Static(id="monitor-status")
            from ..core.tooltips import get_tooltip
            tip = get_tooltip("monitor_mode")
            if tip:
                yield Static(
                    f"[#cba6f7]{tip.title}[/#cba6f7]\n"
                    f"[#a6adc8]{tip.description}[/#a6adc8]\n"
                    f"[#585b70]{tip.example}[/#585b70]",
                    id="tooltip-info",
                )
            yield Static(
                "[#585b70]  e[/#585b70][#a6e3a1] enable monitor[/#a6e3a1]"
                "  [#585b70]d[/#585b70][#f38ba8] disable monitor[/#f38ba8]"
                "  [#585b70]Esc[/#585b70][#a6adc8] back[/#a6adc8]",
                id="monitor-hints",
            )
        yield Footer()

    async def on_mount(self) -> None:
        self.call_after_refresh(self._check_status)

    async def _check_status(self) -> None:
        from ..core.monitor import get_interface_mode
        mode = await get_interface_mode(self.adapter_name)
        status = self.query_one("#monitor-status", Static)
        status.update(f"Current mode: [bold]{mode}[/bold]")

    async def action_enable_monitor(self) -> None:
        from ..core.monitor import enter_monitor_mode
        try:
            new_iface = await enter_monitor_mode(self.adapter_name)
            self.app.notify(f"Monitor mode enabled on {new_iface}")
            self.adapter_name = new_iface
            await self._check_status()
        except Exception as e:
            self.app.notify(f"Failed: {e}", severity="error")

    async def action_disable_monitor(self) -> None:
        from ..core.monitor import exit_monitor_mode
        try:
            # Assumes original iface is name without 'mon'
            orig = self.adapter_name.replace("mon", "")
            await exit_monitor_mode(self.adapter_name, orig)
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
            yield Static("[bold #cba6f7]Scan Options[/bold #cba6f7]", id="scanopts-title")
            yield Static("[#45475a]────────────[/#45475a]")
            yield Checkbox("2.4 GHz Band", value=True, id="band-2g")
            yield Checkbox("5 GHz Band", value=False, id="band-5g")
            yield Checkbox("6 GHz Band", value=False, id="band-6g")
            yield Static(
                "[#a6adc8]Specific channels[/#a6adc8] [#585b70](leave blank for all)[/#585b70]",
                id="channels-label",
            )
            yield Input(placeholder="e.g. 1,6,11", id="channels-input")
            yield Checkbox("Show Hidden SSIDs", value=True, id="show-hidden")
            yield Static(
                "[#585b70]  Enter[/#585b70][#a6adc8] start scan[/#a6adc8]"
                "  [#585b70]Esc[/#585b70][#a6adc8] back[/#a6adc8]",
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
                f"[bold #cba6f7]Access Point Details[/bold #cba6f7]  "
                f"[#cdd6f4]{self.target.display_name()}[/#cdd6f4]",
                id="apdetails-title",
            )
            yield Static("[#45475a]──────────────────────────────[/#45475a]")
            pc = privacy_color(self.target.privacy)
            yield Static(
                f"[#585b70]BSSID     [/#585b70]  [#585b70]{self.target.bssid}[/#585b70]\n"
                f"[#585b70]Channel   [/#585b70]  [#89dceb]{self.target.channel}[/#89dceb]\n"
                f"[#585b70]Signal    [/#585b70]  {signal_bar(self.target.signal)} [#cdd6f4]{self.target.signal} dBm[/#cdd6f4]\n"
                f"[#585b70]Encryption[/#585b70]  [{pc}]{self.target.privacy}[/{pc}] [#a6adc8]{self.target.cipher} {self.target.auth}[/#a6adc8]\n"
                f"[#585b70]Data Pkts [/#585b70]  [#a6adc8]{self.target.data_packets}[/#a6adc8]\n",
                id="apdetails-info",
            )
            client_count = sum(1 for c in self.app.session.clients if c.bssid == self.target.bssid)
            yield Static(
                f"[#cba6f7]Connected Clients[/#cba6f7]  [#cdd6f4]{client_count}[/#cdd6f4]",
                id="apdetails-clients",
            )
            from ..core.intelligence import IntelligenceEngine
            engine = IntelligenceEngine()
            target_clients = [c for c in self.app.session.clients if c.bssid == self.target.bssid]
            recs = engine.evaluate_target(self.target, target_clients)
            if recs:
                yield Static(
                    "[bold #cba6f7]Attack Recommendations[/bold #cba6f7]",
                    id="apdetails-recs-title",
                )
                for r in recs:
                    conf_c = "#a6e3a1" if r.confidence >= 70 else ("#f9e2af" if r.confidence >= 40 else "#f38ba8")
                    yield Static(
                        f"  [{conf_c}]{r.confidence}%[/{conf_c}]  "
                        f"[#cdd6f4]{r.method}[/#cdd6f4]  [#a6adc8]{r.reason}[/#a6adc8]"
                    )
                    for w in r.warnings:
                        yield Static(f"    [#f9e2af]! {w}[/#f9e2af]")
            yield Static(
                "[#585b70]  a[/#585b70][#a6adc8] attack this AP[/#a6adc8]"
                "  [#585b70]Esc[/#585b70][#a6adc8] back[/#a6adc8]",
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
            yield Static("[bold #cba6f7]Saved Captures[/bold #cba6f7]", id="captures-title")
            yield Static("[#45475a]──────────────[/#45475a]")
            table = DataTable(id="captures-table", cursor_type="row")
            table.add_columns("Filename", "Size", "Modified")
            yield table
            yield Static(
                "[#585b70]  Enter[/#585b70][#a6adc8] crack selected[/#a6adc8]"
                "  [#585b70]j/k[/#585b70][#a6adc8] navigate[/#a6adc8]"
                "  [#585b70]Esc[/#585b70][#a6adc8] back[/#a6adc8]",
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
