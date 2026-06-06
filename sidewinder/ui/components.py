"""Sidewinder UI reusable widget components."""

from __future__ import annotations

from rich.panel import Panel
from rich.text import Text
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static


class Spacer(Static):
    """A spacer widget for flexible TUI layouts."""
    def __init__(self, flex: int | None = None, height: int | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        if flex is not None:
            self.styles.height = f"{flex}fr"
        elif height is not None:
            self.styles.height = height



# ── ASCII art logo ──────────────────────────────────────────────────────────

# Two-tone logo: "SIDE" in bright text, "WINDER" in dim — compact version
LOGO: str = """\
[$primary]                        [/$primary][$text-muted]                                              [/$text-muted]
[$primary]  ████  ████  ████    ██████  [/$primary][$text-muted]██        ██  ████  ██    ██  ████    ██████  ████  [/$text-muted]
[$primary]██      ██    ██    ██        [/$primary][$text-muted]██        ██    ██  ████  ██    ██  ██      ██    [/$text-muted]
[$primary]  ████  ██    ██    ██████  [/$primary][$text-muted]██  ██    ██    ██  ██  ██    ██  ██████  ████  [/$text-muted]
[$primary]      ██  ██    ██    ██      [/$text-muted]  ██  ██      ██    ████  ██    ██  ██      ██    [/$text-muted]
[$primary]██████    ████  ████    ██████  [/$primary][$text-muted]    ████      ████  ██    ██  ████    ██████  ████  [/$text-muted]"""


# ── Pure helper functions ────────────────────────────────────────────────────

def signal_bar(signal: int) -> str:
    """Return a 10-character Unicode bar representing WiFi signal strength.

    Args:
        signal: RSSI value in dBm (e.g. -45).

    Returns:
        A Rich markup string with coloured block characters.
    """
    if signal >= -50:
        filled, color = 10, "$success"
    elif signal >= -60:
        filled, color = 8,  "$success"
    elif signal >= -70:
        filled, color = 6,  "$warning"
    elif signal >= -80:
        filled, color = 4,  "$warning"
    elif signal >= -90:
        filled, color = 2,  "$error"
    else:
        filled, color = 1,  "$error"

    bar = "█" * filled + "░" * (10 - filled)
    return f"[{color}]{bar}[/{color}]"


def signal_color(signal: int) -> str:
    """Return a Rich colour name for the given RSSI value.

    Args:
        signal: RSSI value in dBm.

    Returns:
        Rich colour name string.
    """
    if signal > -50:
        return "$success"
    elif signal > -70:
        return "$warning"
    else:
        return "$error"


def privacy_color(privacy: str) -> str:
    """Return a Rich colour name for the given WiFi privacy/encryption type.

    Args:
        privacy: Encryption label such as 'OPN', 'WEP', 'WPA2', 'WPA3', 'WPA'.

    Returns:
        Rich colour name string.
    """
    mapping: dict[str, str] = {
        "OPN":  "$error",
        "WEP":  "$warning",
        "WPA2": "$success",
        "WPA3": "$secondary",
        "WPA":  "$success",
    }
    return mapping.get(privacy.upper(), "$text")


def eapol_status_display(m1: bool, m2: bool, m3: bool, m4: bool) -> str:
    """Return a Rich markup string showing the 4-way EAPOL handshake progress.

    Each message label is coloured green when captured or dim/grey when pending.

    Args:
        m1: Whether EAPOL message 1 has been captured.
        m2: Whether EAPOL message 2 has been captured.
        m3: Whether EAPOL message 3 has been captured.
        m4: Whether EAPOL message 4 has been captured.

    Returns:
        Rich markup string like "[green]M1[/] [green]M2[/] [dim]M3[/] [dim]M4[/]".
    """
    def label(name: str, captured: bool) -> str:
        """Render a single EAPOL label."""
        return f"[bold green]{name}[/bold green]" if captured else f"[dim]{name}[/dim]"

    return f"{label('M1', m1)}  {label('M2', m2)}  {label('M3', m3)}  {label('M4', m4)}"


# ── Widgets ──────────────────────────────────────────────────────────────────

class LogoWidget(Static):
    """Renders the opencode-style ASCII-art logo in two-tone white/dim."""

    def render(self) -> str:  # type: ignore[override]
        """Render the logo as Rich markup."""
        return LOGO


class AdapterStatusWidget(Static):
    """Displays current WiFi adapter state in a Rich panel.

    Reactive attributes are updated externally as the adapter state changes.
    """

    adapter_name: reactive[str] = reactive("N/A")
    adapter_status: reactive[str] = reactive("unknown")
    channel: reactive[str | int] = reactive("--")
    mode: reactive[str] = reactive("managed")

    def render(self) -> str:  # type: ignore[override]
        """Render the adapter status using theme variables."""
        status_color = {
            "ready":      "$success",
            "optimized":  "$success",
            "monitor":    "$secondary",
            "error":      "$error",
            "unknown":    "$text-muted",
        }.get(self.adapter_status.lower(), "$text")

        mode_color = "$secondary" if self.mode == "monitor" else "$accent"

        return (
            f"[$text-muted]Interface :[/$text-muted] [$text]{self.adapter_name}[/$text]\n"
            f"[$text-muted]Status    :[/$text-muted] [{status_color}]{self.adapter_status}[/{status_color}]\n"
            f"[$text-muted]Channel   :[/$text-muted] [$warning]{self.channel}[/$warning]\n"
            f"[$text-muted]Mode      :[/$text-muted] [{mode_color}]{self.mode}[/{mode_color}]"
        )


class ErrorCard(Static):
    """Renders a structured error panel with severity, cause, and remediation.

    Args:
        severity: One of 'info', 'warning', 'error', 'critical'.
        what: Short description of what went wrong.
        why: Explanation of the root cause.
        how_to_fix: Step-by-step remediation advice.
        raw_error: Optional raw exception / traceback text.
    """

    def __init__(
        self,
        severity: str,
        what: str,
        why: str,
        how_to_fix: str | list[str],
        raw_error: str = "",
        **kwargs,
    ) -> None:
        """Initialise the ErrorCard with all context fields."""
        super().__init__(**kwargs)
        self._severity = severity
        self._what = what
        self._why = why
        self._how_to_fix = how_to_fix if isinstance(how_to_fix, str) else "\n  ".join(how_to_fix)
        self._raw_error = raw_error

    def render(self) -> Panel:  # type: ignore[override]
        """Render the error card panel."""
        severity_color = {
            "info":     "blue",
            "warning":  "yellow",
            "error":    "red",
            "critical": "bright_red",
        }.get(self._severity.lower(), "red")

        body = Text()

        body.append("● WHAT\n", style="bold yellow")
        body.append(f"  {self._what}\n\n")

        body.append("● WHY\n", style="bold yellow")
        body.append(f"  {self._why}\n\n")

        body.append("● HOW TO FIX\n", style="bold yellow")
        if isinstance(self._how_to_fix, list):
            for step in self._how_to_fix:
                body.append(f"  • {step}\n")
        else:
            body.append(f"  {self._how_to_fix}\n")

        if self._raw_error:
            body.append("\n● RAW ERROR\n", style="bold dim")
            body.append(f"  {self._raw_error}\n", style="dim")

        title = Text()
        title.append(f"[{self._severity.upper()}]", style=f"bold {severity_color}")
        return Panel(body, title=title, border_style=severity_color)


class TooltipPanel(Static):
    """Renders an informational panel describing a capture method or feature.

    Args:
        name: Feature / method name.
        description: Human-readable description.
        when_to_use: Guidance on when this method is appropriate.
        risk_level: One of 'safe', 'caution', 'dangerous'.
        risk_detail: Additional risk context.
        requires: Comma-separated list of requirements (e.g. 'monitor mode').
    """

    def __init__(
        self,
        name: str,
        description: str,
        when_to_use: str,
        risk_level: str,
        risk_detail: str,
        requires: str,
        **kwargs,
    ) -> None:
        """Initialise TooltipPanel with method metadata."""
        super().__init__(**kwargs)
        self._name = name
        self._description = description
        self._when_to_use = when_to_use
        self._risk_level = risk_level
        self._risk_detail = risk_detail
        self._requires = requires

    def render(self) -> Panel:  # type: ignore[override]
        """Render the tooltip / info panel."""
        risk_color = {
            "safe":      "green",
            "caution":   "yellow",
            "dangerous": "red",
        }.get(self._risk_level.lower(), "white")

        body = Text()
        body.append(f"{self._description}\n\n")

        body.append("When to use\n", style="bold cyan")
        body.append(f"  {self._when_to_use}\n\n")

        body.append("Risk level  ", style="bold")
        body.append(
            f"{self._risk_level.upper()}\n", style=f"bold {risk_color}"
        )
        body.append(f"  {self._risk_detail}\n\n")

        body.append("Requires\n", style="bold")
        for req in self._requires.split(","):
            body.append(f"  • {req.strip()}\n")

        return Panel(
            body,
            title=f"[bold cyan]{self._name}[/bold cyan]",
            border_style="cyan",
        )


class EAPOLTracker(Static):
    """Displays live progress of the WPA 4-way EAPOL handshake capture.

    Reactive attributes are updated externally as frames are sniffed.
    """

    m1: reactive[bool] = reactive(False)
    m2: reactive[bool] = reactive(False)
    m3: reactive[bool] = reactive(False)
    m4: reactive[bool] = reactive(False)
    status: reactive[str] = reactive("waiting")

    def render(self) -> str:  # type: ignore[override]
        """Render the EAPOL handshake tracker using theme variables."""
        handshake = eapol_status_display(self.m1, self.m2, self.m3, self.m4)

        status_color = {
            "waiting":  "$text-muted",
            "partial":  "$warning",
            "complete": "$success",
            "failed":   "$error",
        }.get(self.status.lower(), "$text")

        return (
            f"[bold]EAPOL Capture[/bold]\n\n"
            f"[$text-muted]4-Way Handshake:[/$text-muted] {handshake}\n"
            f"[$text-muted]Status        :[/$text-muted] [{status_color}]{self.status.upper()}[/{status_color}]"
        )


class StatusBar(Static):
    """Bottom status bar summarizing connection state and execution time."""
    adapter: reactive[str] = reactive("--")
    channel: reactive[str] = reactive("--")
    mode: reactive[str] = reactive("managed")
    signal: reactive[int] = reactive(-100)
    elapsed: reactive[str] = reactive("00:00:00")

    def render(self) -> str:
        bar = signal_bar(self.signal)
        sc = signal_color(self.signal)
        return (
            f" [$text-muted]{self.adapter}[/$text-muted] "
            f"[$text-disabled]│[/$text-disabled] [$secondary]Ch:{self.channel}[/$secondary] "
            f"[$text-disabled]│[/$text-disabled] [$primary]{self.mode}[/$primary] "
            f"[$text-disabled]│[/$text-disabled] {bar} [{sc}]{self.signal} dBm[/{sc}] "
            f"[$text-disabled]│[/$text-disabled] [$text-muted]{self.elapsed}[/$text-muted]"
        )


class ScanStatsBar(Static):
    """Displays real-time network and client counts in top panel of ScanScreen."""
    networks: reactive[int] = reactive(0)
    clients: reactive[int] = reactive(0)
    elapsed: reactive[str] = reactive("00:00")

    def render(self) -> str:
        return (
            f" [$primary]Networks[/$primary] [$text]{self.networks}[/$text]  "
            f"[$primary]Clients[/$primary] [$text]{self.clients}[/$text]  "
            f"[$text-muted]elapsed[/$text-muted] [$text-muted]{self.elapsed}[/$text-muted]"
        )


class TargetCard(Static):
    """Visual panel representing the selected Target Access Point."""
    def __init__(self, target, **kwargs) -> None:
        super().__init__(**kwargs)
        self.target = target

    def render(self) -> str:
        pc = privacy_color(self.target.privacy)
        bar = signal_bar(self.target.signal)
        wps_status = "[$success]YES[/$success]" if self.target.wps else "[$error]NO[/$error]"
        return (
            f"[$primary]Target: {self.target.display_name()}[/$primary]\n"
            f"[$text-muted]BSSID[/$text-muted]     {self.target.bssid}\n"
            f"[$text-muted]Channel[/$text-muted]   [$secondary]{self.target.channel}[/$secondary]\n"
            f"[$text-muted]Signal[/$text-muted]    {bar} [$text]{self.target.signal} dBm[/$text]\n"
            f"[$text-muted]Security[/$text-muted]  [{pc}]{self.target.privacy}[/{pc}] [$text-muted]({self.target.cipher}/{self.target.auth})[/$text-muted]\n"
            f"[$text-muted]WPS[/$text-muted]       {wps_status}"
        )


class ClientRow(Static):
    """Client row showing selection checkmark, MAC, Vendor, Signal, and Packets count."""
    def __init__(self, mac: str, vendor: str, signal: int, packets: int, selected: bool = True, **kwargs) -> None:
        super().__init__(**kwargs)
        self.mac = mac
        self.vendor = vendor
        self.signal = signal
        self.packets = packets
        self.selected = selected

    def render(self) -> str:
        sel = "[$success]✓[/$success]" if self.selected else "[$text-muted]·[/$text-muted]"
        bar = signal_bar(self.signal)
        vendor_lbl = f" [$text-muted]({self.vendor})[/$text-muted]" if self.vendor != "Unknown" else ""
        return (
            f" {sel}  [$text]{self.mac}[/$text]{vendor_lbl}  "
            f"{bar} [$text-muted]{self.signal}[/$text-muted]  "
            f"[$secondary]{self.packets}[/$secondary] pkts"
        )


class AttackProgressPanel(Static):
    """Comprehensive panel tracking background packets and handshake capture status."""
    def __init__(self, method: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.method = method
        self.beacons = 0
        self.data_pkts = 0
        self.signal = -100
        self.m1 = self.m2 = self.m3 = self.m4 = False
        self.status = "waiting"

    def render(self) -> str:
        h = eapol_status_display(self.m1, self.m2, self.m3, self.m4)
        bar = signal_bar(self.signal)
        return (
            f"[$primary]Attack Engine: {self.method.upper()}[/$primary]\n\n"
            f"[$text-muted]Beacons [/$text-muted] [$secondary]{self.beacons:,}[/$secondary]\n"
            f"[$text-muted]Data    [/$text-muted] [$secondary]{self.data_pkts:,}[/$secondary]\n"
            f"[$text-muted]Signal  [/$text-muted] {bar} [$text]{self.signal} dBm[/$text]\n\n"
            f"[$text-muted]Handshake[/$text-muted] {h}  [$text-muted]({self.status.upper()})[/$text-muted]"
        )


class PasswordCard(Static):
    """Visual panel for ResultScreen exhibiting cracked credentials."""
    def __init__(self, ssid: str, bssid: str, password: str, method: str, keys: int, elapsed: float, **kwargs) -> None:
        super().__init__(**kwargs)
        self.ssid = ssid
        self.bssid = bssid
        self.password = password
        self.method = method
        self.keys = keys
        self.elapsed = elapsed

    def render(self) -> str:
        time_str = f"{int(self.elapsed // 60):02d}:{int(self.elapsed % 60):02d}"
        return (
            f"[$success bold]  ✓  PASSWORD CRACKED SUCCESSFULLY[/$success bold]\n"
            f"[$text-disabled]  {'─'*44}[/$text-disabled]\n"
            f"  [$text-muted]SSID    [/$text-muted]  [$text]{self.ssid}[/$text]\n"
            f"  [$text-muted]BSSID   [/$text-muted]  [$text-muted]{self.bssid}[/$text-muted]\n"
            f"  [$text-muted]Password[/$text-muted]  [bold $success]{self.password}[/bold $success]\n"
            f"  [$text-muted]Method  [/$text-muted]  [$secondary]{self.method}[/$secondary]\n"
            f"  [$text-muted]Keys    [/$text-muted]  [$text-muted]{self.keys:,} tested[/$text-muted]\n"
            f"  [$text-muted]Time    [/$text-muted]  [$text-muted]{time_str}[/$text-muted]"
        )

