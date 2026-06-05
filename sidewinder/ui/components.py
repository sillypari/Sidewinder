"""Sidewinder UI reusable widget components."""

from __future__ import annotations

from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static


# ── ASCII art logo ──────────────────────────────────────────────────────────

LOGO: str = """\
  ██████╗██╗██████╗ ███████╗██╗    ██╗██╗███╗   ██╗██████╗ ███████╗██████╗
  ██╔════╝██║██╔══██╗██╔════╝██║    ██║██║████╗  ██║██╔══██╗██╔════╝██╔══██╗
  ╚█████╗ ██║██║  ██║█████╗  ██║ █╗ ██║██║██╔██╗ ██║██║  ██║█████╗  ██████╔╝"""


# ── Pure helper functions ────────────────────────────────────────────────────

def signal_bar(signal: int) -> str:
    """Return a 10-character Unicode bar representing WiFi signal strength.

    Args:
        signal: RSSI value in dBm (e.g. -45).

    Returns:
        A Rich markup string with coloured block characters.
    """
    # Normalise to 0-10 filled blocks
    if signal >= -50:
        filled = 10
        color = "green"
    elif signal >= -60:
        filled = 8
        color = "green"
    elif signal >= -70:
        filled = 6
        color = "yellow"
    elif signal >= -80:
        filled = 4
        color = "yellow"
    elif signal >= -90:
        filled = 2
        color = "red"
    else:
        filled = 1
        color = "red"

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
        return "green"
    elif signal > -70:
        return "yellow"
    else:
        return "red"


def privacy_color(privacy: str) -> str:
    """Return a Rich colour name for the given WiFi privacy/encryption type.

    Args:
        privacy: Encryption label such as 'OPN', 'WEP', 'WPA2', 'WPA3', 'WPA'.

    Returns:
        Rich colour name string.
    """
    mapping: dict[str, str] = {
        "OPN":  "red",
        "WEP":  "yellow",
        "WPA2": "green",
        "WPA3": "cyan",
        "WPA":  "bright_green",
    }
    return mapping.get(privacy.upper(), "white")


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
        return f"[green bold]{name}[/]" if captured else f"[dim]{name}[/]"

    return f"{label('M1', m1)}  {label('M2', m2)}  {label('M3', m3)}  {label('M4', m4)}"


# ── Widgets ──────────────────────────────────────────────────────────────────

class LogoWidget(Static):
    """Renders the Sidewinder ASCII-art logo in bold green."""

    def render(self) -> str:  # type: ignore[override]
        """Render the logo as Rich markup."""
        return f"[bold green]{LOGO}[/bold green]"


class AdapterStatusWidget(Static):
    """Displays current WiFi adapter state in a Rich panel.

    Reactive attributes are updated externally as the adapter state changes.
    """

    adapter_name: reactive[str] = reactive("N/A")
    adapter_status: reactive[str] = reactive("unknown")
    channel: reactive[str | int] = reactive("--")
    mode: reactive[str] = reactive("managed")

    def render(self) -> Panel:  # type: ignore[override]
        """Render the adapter status panel."""
        status_color = {
            "ready":    "green",
            "monitor":  "cyan",
            "error":    "red",
            "unknown":  "dim",
        }.get(self.adapter_status.lower(), "white")

        lines = Text()
        lines.append("Interface : ", style="bold")
        lines.append(str(self.adapter_name), style="cyan")
        lines.append("\n")
        lines.append("Status    : ", style="bold")
        lines.append(str(self.adapter_status).upper(), style=status_color)
        lines.append("\n")
        lines.append("Channel   : ", style="bold")
        lines.append(str(self.channel), style="yellow")
        lines.append("\n")
        lines.append("Mode      : ", style="bold")
        lines.append(str(self.mode).capitalize(), style="bright_blue")

        return Panel(lines, title="[bold]Adapter Status[/bold]", border_style="dim white")


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

    def render(self) -> Panel:  # type: ignore[override]
        """Render the EAPOL handshake tracker panel."""
        handshake = eapol_status_display(self.m1, self.m2, self.m3, self.m4)

        status_color = {
            "waiting":  "dim",
            "partial":  "yellow",
            "complete": "green",
            "failed":   "red",
        }.get(self.status.lower(), "white")

        body = Text()
        body.append("4-Way Handshake  ", style="bold")
        body.append_text(Text.from_markup(handshake))
        body.append("\n\n")
        body.append("Status  ", style="bold")
        body.append(self.status.upper(), style=f"bold {status_color}")

        return Panel(
            body,
            title="[bold]EAPOL Capture[/bold]",
            border_style="green" if self.status == "complete" else "dim white",
        )
