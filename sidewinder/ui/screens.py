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
from typing import Optional

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
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive

from .components import (
    AdapterStatusWidget,
    EAPOLTracker,
    ErrorCard,
    LogoWidget,
    TooltipPanel,
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
        with Vertical():
            yield LogoWidget(id="logo")
            yield Static(" ", id="spacer")
            yield AdapterStatusWidget(id="adapter-status")
            yield Static(" ", id="spacer2")
            with Vertical(id="menu"):
                for key, label, action in MAIN_MENU_ITEMS:
                    yield Static(
                        f" [[bold magenta]{key}[/bold magenta]] {label}",
                        classes="menu-item",
                        id=f"menu-{action}",
                    )
            yield Static(
                "\n [dim]/ command  ? help  Esc quit[/dim]",
                id="hints",
            )
        yield Footer()

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
        yield Header()
        with Vertical():
            yield Static("[bold cyan]Hardware & Adapters[/bold cyan]\n", id="title")
            table = DataTable(id="adapter-table", show_cursor=True)
            table.add_columns("Interface", "Chipset", "Driver", "Bands", "Monitor", "Inject", "Status")
            yield table
            yield Static(
                "\n [dim]r: refresh  Esc: back[/dim]",
                id="hints",
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
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    scanning: reactive[bool] = reactive(False)
    network_count: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            with Horizontal(id="scan-header"):
                yield Static("[bold cyan]WiFi Scan[/bold cyan]", id="scan-title")
                yield Static("", id="scan-status")
            table = DataTable(id="scan-table", show_cursor=True)
            table.add_columns(
                "BSSID", "CH", "Signal", "Rate", "Privacy", "Cipher", "ESSID", "WPS", "Clients"
            )
            yield table
            yield Static(
                " [dim]Enter: select  s: stop  j/k: navigate  Esc: back[/dim]",
                id="hints",
            )
        yield Footer()

    def on_mount(self) -> None:
        self.scanning = True
        self.call_after_refresh(self._update_status)
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

    def _update_status(self) -> None:
        status = self.query_one("#scan-status", Static)
        if self.scanning:
            status.update(f"[green]SCANNING...[/green] ({self.network_count} networks)")
        else:
            status.update(f"[yellow]STOPPED[/yellow] ({self.network_count} networks)")

    def add_network(self, network) -> None:
        """Add or update a network in the scan table."""
        table = self.query_one("#scan-table", DataTable)
        bar = signal_bar(network.signal)
        sc = signal_color(network.signal)
        pc = privacy_color(network.privacy)
        row_key = network.bssid

        row_data = (
            f"[dim]{network.bssid}[/dim]",
            f"[cyan]{network.channel}[/cyan]",
            f"{bar} [{sc}]{network.signal}[/{sc}]",
            "",
            f"[{pc}]{network.privacy}[/{pc}]",
            network.cipher,
            f"[bold]{network.display_name()}[/bold]",
            "[green]WPS[/green]" if network.wps else "",
            "",
        )
        try:
            for i, data in enumerate(row_data):
                col_key = list(table.columns.keys())[i]
                table.update_cell(row_key, col_key, data, update_width=False)
        except Exception:
            table.add_row(*row_data, key=row_key)

        self.network_count = len(table.rows)
        self._update_status()

    def action_back(self) -> None:
        self.action_stop_scan()
        self.app.pop_screen()

    def action_stop_scan(self) -> None:
        self.scanning = False
        if hasattr(self, "scan_task") and self.scan_task and not self.scan_task.done():
            self.scan_task.cancel()
        if hasattr(self, "_scan_engine") and self._scan_engine:
            import asyncio
            asyncio.create_task(self._scan_engine.stop_and_wait())
        self._update_status()

    def action_cursor_down(self) -> None:
        table = self.query_one("#scan-table", DataTable)
        table.action_scroll_down()

    def action_cursor_up(self) -> None:
        table = self.query_one("#scan-table", DataTable)
        table.action_scroll_up()

    def action_select_target(self) -> None:
        """Push capture method selection with the selected network."""
        table = self.query_one("#scan-table", DataTable)
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
        yield Header()
        with Vertical():
            yield Static("[bold cyan]Select Target Network[/bold cyan]\n")
            table = DataTable(id="target-table", show_cursor=True)
            table.add_columns("BSSID", "CH", "Signal", "Privacy", "ESSID", "Clients")
            yield table
            yield Static(" [dim]Enter: select  j/k: navigate  Esc: back[/dim]")
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
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    selected_idx: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="method-list", classes="panel"):
                yield Static("[bold cyan]Capture Method[/bold cyan]\n")
                for m in CAPTURE_METHODS:
                    risk_c = {"safe": "green", "caution": "yellow", "dangerous": "red"}.get(
                        m["risk_level"], "white"
                    )
                    yield Static(
                        f" [[bold magenta]{m['key']}[/bold magenta]] [bold]{m['name']}[/bold]\n"
                        f"     {m['short']}\n"
                        f"     Risk: [{risk_c}]{m['risk_level'].upper()}[/{risk_c}]\n",
                        classes="menu-item",
                        id=f"method-{m['key']}",
                    )
                yield Static(" [dim]1-5: select  Esc: back[/dim]")
            with Vertical(id="tooltip-area", classes="panel"):
                m = CAPTURE_METHODS[self.selected_idx]
                yield TooltipPanel(
                    name=m["name"],
                    description=m["description"],
                    when_to_use=m["when_to_use"],
                    risk_level=m["risk_level"],
                    risk_detail=m["risk_detail"],
                    requires=", ".join(m["requires"]),
                    id="tooltip",
                )
        yield Footer()

    def action_method_1(self) -> None:
        self.app.push_screen(CaptureProgressScreen(method="passive"))

    def action_method_2(self) -> None:
        self.app.push_screen(DeauthSelectScreen())

    def action_method_3(self) -> None:
        self.app.push_screen(CaptureProgressScreen(method="pmkid"))

    def action_method_4(self) -> None:
        self.app.push_screen(CaptureProgressScreen(method="wps"))

    def action_method_5(self) -> None:
        self.app.push_screen(CaptureProgressScreen(method="evil_twin"))

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_cursor_down(self) -> None:
        self.selected_idx = min(self.selected_idx + 1, len(CAPTURE_METHODS) - 1)

    def action_cursor_up(self) -> None:
        self.selected_idx = max(self.selected_idx - 1, 0)


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
        yield Header()
        with Vertical():
            yield Static(
                f"[bold cyan]Capturing Handshake[/bold cyan] — Method: [yellow]{self.method.title()}[/yellow]\n"
            )
            with Horizontal():
                with Vertical(id="stats-panel", classes="panel"):
                    yield Static(id="capture-stats")
                with Vertical(id="eapol-panel", classes="panel"):
                    yield EAPOLTracker(id="eapol-tracker")
            yield ProgressBar(id="capture-progress", total=100)
            yield Static(
                " [dim]Esc: stop capture  Ctrl+C: stop[/dim]",
                id="hints",
            )
        yield Footer()

    def on_mount(self) -> None:
        self._timer = self.set_interval(1.0, self._tick)

    def _tick(self) -> None:
        self.elapsed += 1
        stats = self.query_one("#capture-stats", Static)
        h, m, s = self.elapsed // 3600, (self.elapsed % 3600) // 60, self.elapsed % 60
        stats.update(
            f"Beacons:  [cyan]{self.beacons}[/cyan]\n"
            f"Data:     [cyan]{self.data_pkts}[/cyan]\n"
            f"Signal:   {signal_bar(self.signal)} {self.signal}dBm\n"
            f"Elapsed:  [cyan]{h:02d}:{m:02d}:{s:02d}[/cyan]\n"
        )

    def update_eapol(
        self, m1: bool, m2: bool, m3: bool, m4: bool, status: str
    ) -> None:
        """Update EAPOL tracker from external event."""
        tracker = self.query_one("#eapol-tracker", EAPOLTracker)
        tracker.m1, tracker.m2, tracker.m3, tracker.m4 = m1, m2, m3, m4
        tracker.status = status

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
    ]

    rate: reactive[int] = reactive(10)

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical():
            yield Static("[bold cyan]Select Deauth Targets[/bold cyan]\n")
            table = DataTable(id="client-table", show_cursor=True)
            table.add_columns("[SEL]", "MAC", "Signal", "Packets")
            yield table
            yield Static(id="rate-display")
            yield Static(
                " [dim]Space: toggle  a: all  Enter: confirm  j/k: navigate  Esc: back[/dim]"
            )
        yield Footer()

    def on_mount(self) -> None:
        self._update_rate_display()

    def _update_rate_display(self) -> None:
        rd = self.query_one("#rate-display", Static)
        rd.update(f"\n Deauth rate: [cyan]{self.rate}[/cyan] frames/burst  [dim](+/- to adjust)[/dim]")

    def add_client(self, mac: str, signal: int, packets: int) -> None:
        table = self.query_one("#client-table", DataTable)
        # Fingerprint the client
        try:
            from ..core.fingerprint import Fingerprinter
            fp = Fingerprinter()
            device = fp.fingerprint_client(mac)
            vendor_label = f" [dim]({device.vendor})[/dim]" if device.vendor != "Unknown" else ""
        except Exception:
            vendor_label = ""
        table.add_row(
            "[green]*[/green]",  # Default: selected
            f"[dim]{mac}[/dim]{vendor_label}",
            f"{signal_bar(signal)} {signal}",
            str(packets),
            key=mac,
        )

    def action_toggle(self) -> None:
        table = self.query_one("#client-table", DataTable)
        if table.cursor_row >= 0:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            current = table.get_cell(row_key, "[SEL]")
            new_val = "[dim] [/dim]" if "*" in str(current) else "[green]*[/green]"
            table.update_cell(row_key, "[SEL]", new_val, update_width=False)

    def action_select_all(self) -> None:
        table = self.query_one("#client-table", DataTable)
        for row_key in table.rows:
            table.update_cell(row_key, "[SEL]", "[green]*[/green]", update_width=False)

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
        yield Header()
        with Vertical():
            yield Static("[bold cyan]Cracking Password[/bold cyan]\n")
            with Vertical(classes="panel"):
                yield Static(id="crack-stats")
                yield ProgressBar(id="crack-progress", total=100)
            yield Static(
                " [dim]Esc: stop cracking[/dim]",
                id="hints",
            )
        yield Footer()

    def on_mount(self) -> None:
        self._update_display()

    def _update_display(self) -> None:
        stats = self.query_one("#crack-stats", Static)
        pct = (self.keys_tested / self.keys_total * 100) if self.keys_total > 0 else 0
        stats.update(
            f"Keys tested: [cyan]{self.keys_tested:,}[/cyan] / {self.keys_total:,}\n"
            f"Speed:       [cyan]{self.speed:,.0f}[/cyan] keys/sec\n"
            f"ETA:         [cyan]{self.eta}[/cyan]\n"
            f"Current:     [dim]{self.current_key or '...'}[/dim]\n"
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
        yield Header()
        with Vertical():
            yield Static(
                f"\n[bold green]* PASSWORD FOUND![/bold green]\n",
                id="result-title",
            )
            yield Static(
                f" ┌─ RESULT ────────────────────────────────────────────────────────┐\n"
                f" │  SSID:     [bold]{self._ssid}[/bold]\n"
                f" │  BSSID:    [dim]{self._bssid}[/dim]\n"
                f" │  Password: [bold green]{self._password}[/bold green]\n"
                f" │  Method:   {self._method}\n"
                f" │  Keys:     {self._keys:,} tested\n"
                f" └────────────────────────────────────────────────────────┘",
                id="result-card",
            )
            yield Static(
                "\n [1] Save to file  [2] Copy to clipboard  [4] Attack another  [6] Main menu"
            )
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
        yield Header()
        with Vertical():
            yield ErrorCard(
                severity=self._sev,
                what=self._what,
                why=self._why,
                how_to_fix=self._how,
                raw_error=self._raw,
            )
            yield Static(" [dim]Enter/Esc: dismiss[/dim]")
        yield Footer()

    def action_back(self) -> None:
        self.app.pop_screen()


# ── Help Screen ───────────────────────────────────────────────────────────────

TUTORIAL = """\
[bold cyan]Welcome to Sidewinder![/bold cyan]

A native Linux WiFi audit tool. Zero bloat, terminal-first.

[bold]Phase 1: Scan[/bold]
  1. Press [bold magenta][1][/bold magenta] from the main menu to scan
  2. Wait for networks to appear (auto-hops all channels)
  3. Press [bold]Enter[/bold] to select your target
  4. Press [bold]s[/bold] to stop scanning

[bold]Phase 2: Capture[/bold]
  1. Choose capture method:
     [bold magenta][1][/bold magenta] Passive — wait for natural handshake (stealthy)
     [bold magenta][2][/bold magenta] Deauth — kick clients to force handshake (fast)
  2. Watch the EAPOL M1-M4 tracker
  3. Capture stops automatically when handshake is detected

[bold]Phase 3: Crack[/bold]
  1. Select wordlist (auto-discovered from system)
  2. Choose tool: aircrack-ng (CPU) or hashcat (GPU)
  3. Watch the progress bar
  4. Password appears in green when found

[bold]Phase 4: Cleanup[/bold]
  1. Press [bold magenta][6][/bold magenta] from main menu
  2. Confirm file deletion
  3. NM/wpa_supplicant restored automatically
  4. Exit safely

[bold]Keyboard Reference:[/bold]
  j/k      Navigate up/down
  Enter    Select/confirm
  Esc      Back/cancel
  /        Command palette
  ?        This help screen
  1-7      Quick menu access
  s        Stop scan
  Space    Toggle checkbox
  a        Select all

[bold]Adapter Priority:[/bold]
  1st: RTL8821AU (morrownr) — full monitor + injection + 5GHz
  2nd: RT5370 — 2.4GHz, reliable, no extra driver needed
  3rd: MT7902 (built-in) — internet only, no injection

[dim]Press Esc to close help[/dim]
"""


class HelpScreen(Screen):
    """Full WiFi audit tutorial — opened with ? key."""

    BINDINGS = [
        Binding("escape", "back", "Close"),
        Binding("q", "back", "Close"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with ScrollableContainer():
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
        yield Header()
        with Vertical(id="resume-container"):
            yield Static("Previous session found", id="resume-title")
            yield Static(" ", id="resume-spacer")

            scan_count = len(self._session.scan_results)
            target = self._session.selected_target
            target_name = target.display_name() if target else "None"
            captures = len(self._session.captures)
            cracked = len(self._session.cracked_passwords)

            summary_lines = [
                f"  Session:  {self._session.id[:8]}...",
                f"  Adapter:  {self._session.adapter or 'Not set'}",
                f"  Scans:    {scan_count} networks found",
                f"  Target:   {target_name}",
                f"  Captures: {captures} files",
                f"  Cracked:  {cracked} passwords",
            ]
            yield Static("\n".join(summary_lines), id="resume-summary")
            yield Static(" ", id="resume-spacer2")
            yield Static(
                "  [bold green]Y[/bold green]  Resume session\n"
                "  [bold red]N[/bold red]  Start fresh",
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
        yield Header()
        with Vertical(id="command-container"):
            yield Static("[bold cyan]Command Palette[/bold cyan]\n")
            yield Input(placeholder="Type a /command...", id="command-input")
            
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
        
        yield Header()
        with Vertical():
            yield Static("Select a wordlist (press Enter)", classes="panel-title")
            path = "/usr/share/wordlists" if os.path.exists("/usr/share/wordlists") else "."
            yield DirectoryTree(path, id="wordlist-tree")
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
        yield Header()
        with Vertical(id="engine-container"):
            yield Static("[bold cyan]Select Cracking Engine[/bold cyan]\n")
            yield Static(
                "  [1] Aircrack-ng (CPU-based, standard)\n"
                "  [2] Hashcat (GPU-based, requires setup)\n"
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
        yield Header()
        with Vertical(id="cleanup-container"):
            yield Static("[bold cyan]System Cleanup[/bold cyan]\n")
            yield Static(
                "The following actions will be performed:\n\n"
                "  [ ] Restore NetworkManager / wpa_supplicant\n"
                "  [ ] Disable Monitor Mode\n"
                "  [ ] Terminate background attack processes\n"
                "  [ ] Clear temporary capture files (/tmp/)\n\n"
                "Press [bold green]Enter[/bold green] to confirm."
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
        yield Header()
        with Vertical(id="service-container"):
            yield Static("[bold cyan]Service Management[/bold cyan]\n")
            yield Static("Checking for conflicting services (NetworkManager, wpa_supplicant)...")
            yield ListView(id="service-list")
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
        yield Header()
        with Vertical():
            yield Static(f"[bold cyan]Monitor Mode Setup for {self.adapter_name}[/bold cyan]\n")
            yield Static(id="monitor-status")

            from ..core.tooltips import get_tooltip
            tip = get_tooltip("monitor_mode")
            if tip:
                yield Static(
                    f"\n[dim cyan]{tip.title}[/dim cyan]: {tip.description}\n"
                    f"[dim]{tip.example}[/dim]",
                    id="tooltip-info",
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
        yield Header()
        with Vertical(id="scan-options-container"):
            yield Static("[bold cyan]Scan Options[/bold cyan]\n")
            yield Checkbox("2.4 GHz Band", value=True, id="band-2g")
            yield Checkbox("5 GHz Band", value=False, id="band-5g")
            yield Checkbox("6 GHz Band", value=False, id="band-6g")
            yield Static("\nSpecific Channels (leave blank for all):")
            yield Input(placeholder="e.g., 1,6,11", id="channels-input")
            yield Checkbox("Show Hidden SSIDs", value=True, id="show-hidden")
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
        yield Header()
        with Vertical():
            yield Static(f"[bold cyan]Access Point Details: {self.target.display_name()}[/bold cyan]\n")
            yield Static(f"BSSID: {self.target.bssid}")
            yield Static(f"Channel: {self.target.channel}")
            yield Static(f"Signal: {self.target.signal} dBm")
            yield Static(f"Encryption: {self.target.privacy} {self.target.cipher} {self.target.auth}")
            yield Static(f"Data Packets: {self.target.data_packets}")
            
            client_count = sum(1 for c in self.app.session.clients if c.bssid == self.target.bssid)
            yield Static(f"\nConnected Clients: {client_count}")

            # Intelligence recommendations
            from ..core.intelligence import IntelligenceEngine
            engine = IntelligenceEngine()
            target_clients = [c for c in self.app.session.clients if c.bssid == self.target.bssid]
            recs = engine.evaluate_target(self.target, target_clients)
            if recs:
                yield Static("\n[bold cyan]Attack Recommendations[/bold cyan]")
                for r in recs:
                    conf_c = "green" if r.confidence >= 70 else ("yellow" if r.confidence >= 40 else "red")
                    yield Static(
                        f"  [{conf_c}]{r.confidence}%[/{conf_c}] [bold]{r.method}[/bold] — {r.reason}"
                    )
                    for w in r.warnings:
                        yield Static(f"    [dim yellow]! {w}[/dim yellow]")
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
        yield Header()
        with Vertical():
            yield Static("[bold cyan]Saved Captures[/bold cyan]", classes="panel-title")
            table = DataTable(id="captures-table", cursor_type="row")
            table.add_columns("Filename", "Size (bytes)", "Modified")
            yield table
            yield Static(
                " [dim]Enter: crack  j/k: navigate  Esc: back[/dim]",
                id="hints",
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
