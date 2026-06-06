"""Sidewinder Theme System.

Implements a dynamic theme system mapped to TCSS variables.
"""
from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, Field
from textual.theme import Theme as TextualTheme


class MethodStyles(BaseModel):
    """HTTP method colors — WiFi equivalents for attack types."""
    scan: str = "#0ea5e9"         # cyan — scan
    deauth: str = "#ef4444"       # red — deauth (aggressive)
    passive: str = "#22c55e"      # green — passive (safe)
    pmkid: str = "#f59e0b"        # amber — PMKID
    wps: str = "#8b5cf6"          # purple — WPS
    evil_twin: str = "#f97316"    # orange — evil twin
    crack: str = "#14b8a6"        # teal — cracking


class SignalStyles(BaseModel):
    """WiFi signal color thresholds."""
    strong: str = "#22c55e"       # -30 to -50 dBm
    medium: str = "#f59e0b"       # -51 to -70 dBm
    weak: str = "#ef4444"         # -71 to -90 dBm


class EncryptionStyles(BaseModel):
    """Encryption type colors."""
    wpa3: str = "#00BCD4"
    wpa2: str = "#22c55e"
    wpa: str = "#4CAF50"
    wep: str = "#f59e0b"
    open: str = "#ef4444"


class SidebarStyles(BaseModel):
    """Sidebar (adapter list) colors."""
    active_adapter: str = "#22c55e"
    inactive_adapter: str = "#6b7280"
    monitor_mode: str = "#0ea5e9"


class Theme(BaseModel):
    """Full theme definition for Sidewinder."""
    name: str = Field(exclude=True)

    # Core Textual colors
    primary: str
    secondary: str | None = None
    background: str | None = None
    surface: str | None = None
    panel: str | None = None
    warning: str | None = None
    error: str | None = None
    success: str | None = None
    accent: str | None = None
    dark: bool = True

    # WiFi-specific styles
    method: MethodStyles = Field(default_factory=MethodStyles)
    signal: SignalStyles = Field(default_factory=SignalStyles)
    encryption: EncryptionStyles = Field(default_factory=EncryptionStyles)
    sidebar: SidebarStyles = Field(default_factory=SidebarStyles)

    # Metadata
    author: str | None = Field(default=None, exclude=True)
    description: str | None = Field(default=None, exclude=True)

    def to_textual_theme(self) -> TextualTheme:
        """Convert to Textual Theme with variables."""
        colors = {
            "primary": self.primary,
            "secondary": self.secondary,
            "background": self.background,
            "surface": self.surface,
            "panel": self.panel,
            "warning": self.warning,
            "error": self.error,
            "success": self.success,
            "accent": self.accent,
        }
        colors = {k: v for k, v in colors.items() if v is not None}

        variables = {
            # Method colors
            "method-scan": self.method.scan,
            "method-deauth": self.method.deauth,
            "method-passive": self.method.passive,
            "method-pmkid": self.method.pmkid,
            "method-wps": self.method.wps,
            "method-evil-twin": self.method.evil_twin,
            "method-crack": self.method.crack,
            # Signal colors
            "signal-strong": self.signal.strong,
            "signal-medium": self.signal.medium,
            "signal-weak": self.signal.weak,
            # Encryption colors
            "enc-wpa3": self.encryption.wpa3,
            "enc-wpa2": self.encryption.wpa2,
            "enc-wpa": self.encryption.wpa,
            "enc-wep": self.encryption.wep,
            "enc-open": self.encryption.open,
            # Sidebar colors
            "sidebar-active": self.sidebar.active_adapter,
            "sidebar-inactive": self.sidebar.inactive_adapter,
            "sidebar-monitor": self.sidebar.monitor_mode,
            # UI variables (matching Posting's pattern)
            "input-cursor-background": self.primary,
            "footer-background": "transparent",
        }

        return TextualTheme(
            name=self.name,
            dark=self.dark,
            **colors,
            variables=variables,
        )
