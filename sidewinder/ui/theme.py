"""Sidewinder Theme System.

Implements a dynamic theme system mapped to TCSS variables.
"""
from dataclasses import dataclass
from typing import Dict


@dataclass
class SidewinderTheme:
    """Semantic color slots for the TUI, inspired by opencode."""

    # Core
    primary: str = "#89b4fd"        # Blue — success, active, selected
    secondary: str = "#cba6f7"      # Mauve — info, headers, highlights
    accent: str = "#fab387"         # Peach — special actions
    error: str = "#f38ba8"          # Red — errors, danger
    warning: str = "#f9e2af"        # Yellow — warnings, caution
    success: str = "#a6e3a1"        # Green — passwords found
    info: str = "#89b4fa"           # Blue — informational

    # Text
    text: str = "#cdd6f4"           # Primary text (catppuccin text)
    text_muted: str = "#a6adc8"     # Secondary text (catppuccin subtext)
    text_dim: str = "#585b70"       # Dimmed text (surface2)

    # Background
    bg: str = "#1e1e2e"             # Base screen background
    bg_panel: str = "#181825"       # Mantle (panel/card background)
    bg_element: str = "#313244"     # Surface0 (input, button background)
    bg_hover: str = "#45475a"       # Surface1 (hover state)

    # Border
    border: str = "#45475a"         # Default subtle border (surface1)
    border_active: str = "#89b4fa"  # Focused/active border
    border_subtle: str = "#313244"  # Very subtle separation

    # WiFi-specific
    signal_strong: str = "#a6e3a1"
    signal_medium: str = "#f9e2af"
    signal_weak: str = "#f38ba8"
    enc_wpa3: str = "#cba6f7"
    enc_wpa2: str = "#a6e3a1"
    enc_wpa: str = "#89b4fa"
    enc_wep: str = "#f9e2af"
    enc_open: str = "#f38ba8"


# The exact opencode aesthetic is highly inspired by Catppuccin Mocha.
OPENCODE_THEME = SidewinderTheme()

# Fallback/Legacy theme (classic Sidewinder green)
CLASSIC_THEME = SidewinderTheme(
    primary="#4CAF50",
    secondary="#00BCD4",
    text="#E6EDF3",
    text_muted="#8B949E",
    bg="#0A0A0A",
    bg_panel="#161B22",
    bg_element="#21262D",
    bg_hover="#18181B",
    border="#30363D",
    border_active="#4CAF50"
)

THEMES: Dict[str, SidewinderTheme] = {
    "opencode": OPENCODE_THEME,
    "classic": CLASSIC_THEME,
}


from textual.theme import Theme

def get_textual_themes() -> dict[str, Theme]:
    """Convert SidewinderThemes to Textual Themes."""
    textual_themes = {}
    for name, t in THEMES.items():
        textual_themes[name] = Theme(
            name=name,
            primary=t.primary,
            secondary=t.secondary,
            accent=t.accent,
            warning=t.warning,
            error=t.error,
            success=t.success,
            foreground=t.text,
            background=t.bg,
            surface=t.bg_element,
            panel=t.bg_panel,
            dark=True,
            variables={
                "text-muted": t.text_muted,
                "text-dim": t.text_dim,
                "bg-hover": t.bg_hover,
                "border": t.border,
                "border-active": t.border_active,
                "border-subtle": t.border_subtle,
                "signal-strong": t.signal_strong,
                "signal-medium": t.signal_medium,
                "signal-weak": t.signal_weak,
                "enc-wpa3": t.enc_wpa3,
                "enc-wpa2": t.enc_wpa2,
                "enc-wpa": t.enc_wpa,
                "enc-wep": t.enc_wep,
                "enc-open": t.enc_open,
            }
        )
    return textual_themes

