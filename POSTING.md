# Posting UI → Sidewinder Design Reference

> Copy-paste ready code from Posting's TUI for Sidewinder.
> Every pattern, every theme, every SCSS rule — adapted for our WiFi audit tool.

---

## Table of Contents

1. [Theme System (Copy This)](#1-theme-system)
2. [Built-in Themes (All 13)](#2-built-in-themes)
3. [Theme Selector (Copy This)](#3-theme-selector)
4. [SCSS Rules (Copy This)](#4-scss-rules)
5. [Layout Architecture](#5-layout-architecture)
6. [Widget Patterns](#6-widget-patterns)
7. [Visual Rules](#7-visual-rules)
8. [Sidewinder Theme File](#8-sidewinder-theme-file)

---

## 1. Theme System

### Posting's Theme Model ( Exact Copy )

```python
# sidewinder/ui/theme.py
from pydantic import BaseModel, Field
from textual.app import App
from textual.color import Color
from textual.theme import Theme as TextualTheme
from textual.theme import BUILTIN_THEMES as TEXTUAL_THEMES
from pathlib import Path
import yaml


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
```

### Theme Loading ( Exact Copy from Posting )

```python
# sidewinder/ui/theme_loader.py
from pathlib import Path
from pydantic import BaseModel
import yaml
from textual.app import InvalidThemeError
from textual.theme import Theme as TextualTheme

from posting.themes import Theme as PostingTheme


BUILTIN_THEMES: dict[str, TextualTheme] = {}  # Populated in section 2


def load_user_themes(theme_dir: Path) -> dict[str, TextualTheme]:
    """Load YAML themes from user directory."""
    themes = {}
    if not theme_dir.exists():
        return themes
    for path in theme_dir.iterdir():
        if path.suffix in (".yaml", ".yml"):
            try:
                with open(path) as f:
                    data = yaml.safe_load(f) or {}
                theme = Theme(**data)
                themes[theme.name] = theme.to_textual_theme()
            except Exception:
                pass
    return themes


def register_themes(app: App, settings) -> None:
    """Register all themes with the app."""
    available = {}

    # Always include default
    available["midnight"] = BUILTIN_THEMES["midnight"]

    # Load built-in themes
    if settings.load_builtin_themes:
        available |= BUILTIN_THEMES

    # Load user themes
    if settings.load_user_themes:
        user_themes = load_user_themes(settings.theme_directory)
        available |= user_themes

    # Register with Textual
    for theme in available.values():
        app.register_theme(theme)

    # Set default
    try:
        app.theme = settings.theme
    except InvalidThemeError:
        app.theme = "midnight"
```

---

## 2. Built-in Themes (All 13)

### Copy-Paste Theme Definitions

```python
# sidewinder/ui/themes.py
from textual.theme import Theme as TextualTheme

BUILTIN_THEMES: dict[str, TextualTheme] = {
    # ── DEFAULT ──────────────────────────────────────────────
    "midnight": TextualTheme(
        name="midnight",
        primary="#4CAF50",           # Green — our signature
        secondary="#00BCD4",         # Cyan — info
        background="#0A0A0A",        # Near-black
        surface="#161B22",           # Dark panel
        panel="#21262D",             # Lighter panel
        warning="#FF9800",           # Orange
        error="#F44336",             # Red
        success="#00E676",           # Bright green
        accent="#9C27B0",            # Purple — accent
        dark=True,
        variables={
            "input-cursor-background": "#4CAF50",
            "footer-background": "transparent",
            "method-scan": "#0ea5e9",
            "method-deauth": "#ef4444",
            "method-passive": "#22c55e",
            "method-pmkid": "#f59e0b",
            "method-wps": "#8b5cf6",
            "method-evil-twin": "#f97316",
            "method-crack": "#14b8a6",
            "signal-strong": "#22c55e",
            "signal-medium": "#f59e0b",
            "signal-weak": "#ef4444",
            "enc-wpa3": "#00BCD4",
            "enc-wpa2": "#22c55e",
            "enc-wpa": "#4CAF50",
            "enc-wep": "#f59e0b",
            "enc-open": "#ef4444",
            "sidebar-active": "#22c55e",
            "sidebar-inactive": "#6b7280",
            "sidebar-monitor": "#0ea5e9",
        },
    ),

    # ── CYBERPUNK ────────────────────────────────────────────
    "cyberpunk": TextualTheme(
        name="cyberpunk",
        primary="#FF00FF",           # Magenta
        secondary="#00FFFF",         # Cyan
        background="#0D0221",        # Deep purple-black
        surface="#1A0533",           # Dark purple
        panel="#2D1B69",             # Purple panel
        warning="#FFD700",           # Gold
        error="#FF3366",             # Hot pink
        success="#39FF14",           # Neon green
        accent="#FF6600",            # Neon orange
        dark=True,
        variables={
            "input-cursor-background": "#FF00FF",
            "footer-background": "transparent",
            "method-scan": "#00FFFF",
            "method-deauth": "#FF3366",
            "method-passive": "#39FF14",
            "method-pmkid": "#FFD700",
            "method-wps": "#FF00FF",
            "method-evil-twin": "#FF6600",
            "method-crack": "#00FFFF",
            "signal-strong": "#39FF14",
            "signal-medium": "#FFD700",
            "signal-weak": "#FF3366",
            "enc-wpa3": "#00FFFF",
            "enc-wpa2": "#39FF14",
            "enc-wpa": "#FF00FF",
            "enc-wep": "#FFD700",
            "enc-open": "#FF3366",
            "sidebar-active": "#39FF14",
            "sidebar-inactive": "#6b7280",
            "sidebar-monitor": "#00FFFF",
        },
    ),

    # ── HACKER (Green on Black) ──────────────────────────────
    "hacker": TextualTheme(
        name="hacker",
        primary="#00FF00",
        secondary="#3A9F3A",
        background="#000000",
        surface="#0A0A0A",
        panel="#111111",
        warning="#00FF66",
        error="#FF0000",
        success="#00DD00",
        accent="#00FF33",
        dark=True,
        variables={
            "input-cursor-background": "#00FF00",
            "footer-background": "transparent",
            "method-scan": "#00FF00",
            "method-deauth": "#FF0000",
            "method-passive": "#00DD00",
            "method-pmkid": "#00FF66",
            "method-wps": "#00FF33",
            "method-evil-twin": "#3A9F3A",
            "method-crack": "#00FF00",
            "signal-strong": "#00FF00",
            "signal-medium": "#00FF66",
            "signal-weak": "#FF0000",
            "enc-wpa3": "#00FF00",
            "enc-wpa2": "#00DD00",
            "enc-wpa": "#00FF33",
            "enc-wep": "#00FF66",
            "enc-open": "#FF0000",
            "sidebar-active": "#00FF00",
            "sidebar-inactive": "#3A9F3A",
            "sidebar-monitor": "#00FF00",
        },
    ),

    # ── GALAXY ───────────────────────────────────────────────
    "galaxy": TextualTheme(
        name="galaxy",
        primary="#C45AFF",
        secondary="#a684e8",
        background="#0F0F1F",
        surface="#1E1E3F",
        panel="#2D2B55",
        warning="#FFD700",
        error="#FF4500",
        success="#00FA9A",
        accent="#FF69B4",
        dark=True,
        variables={
            "input-cursor-background": "#C45AFF",
            "footer-background": "transparent",
            "method-scan": "#a684e8",
            "method-deauth": "#FF4500",
            "method-passive": "#00FA9A",
            "method-pmkid": "#FFD700",
            "method-wps": "#C45AFF",
            "method-evil-twin": "#FF69B4",
            "method-crack": "#a684e8",
            "signal-strong": "#00FA9A",
            "signal-medium": "#FFD700",
            "signal-weak": "#FF4500",
            "enc-wpa3": "#a684e8",
            "enc-wpa2": "#00FA9A",
            "enc-wpa": "#C45AFF",
            "enc-wep": "#FFD700",
            "enc-open": "#FF4500",
            "sidebar-active": "#00FA9A",
            "sidebar-inactive": "#6b7280",
            "sidebar-monitor": "#a684e8",
        },
    ),

    # ── SUNSET ───────────────────────────────────────────────
    "sunset": TextualTheme(
        name="sunset",
        primary="#FF7E5F",
        secondary="#FEB47B",
        background="#2B2139",
        surface="#362C47",
        panel="#413555",
        warning="#FFD93D",
        error="#FF5757",
        success="#98D8AA",
        accent="#B983FF",
        dark=True,
        variables={
            "input-cursor-background": "#FF7E5F",
            "footer-background": "transparent",
            "method-scan": "#FEB47B",
            "method-deauth": "#FF5757",
            "method-passive": "#98D8AA",
            "method-pmkid": "#FFD93D",
            "method-wps": "#B983FF",
            "method-evil-twin": "#FF7E5F",
            "method-crack": "#FEB47B",
            "signal-strong": "#98D8AA",
            "signal-medium": "#FFD93D",
            "signal-weak": "#FF5757",
            "enc-wpa3": "#FEB47B",
            "enc-wpa2": "#98D8AA",
            "enc-wpa": "#FF7E5F",
            "enc-wep": "#FFD93D",
            "enc-open": "#FF5757",
            "sidebar-active": "#98D8AA",
            "sidebar-inactive": "#6b7280",
            "sidebar-monitor": "#FEB47B",
        },
    ),

    # ── AURORA ───────────────────────────────────────────────
    "aurora": TextualTheme(
        name="aurora",
        primary="#45FFB3",
        secondary="#A1FCDF",
        background="#0A1A2F",
        surface="#142942",
        panel="#1E3655",
        warning="#FFE156",
        error="#FF6B6B",
        success="#64FFDA",
        accent="#DF7BFF",
        dark=True,
        variables={
            "input-cursor-background": "#45FFB3",
            "footer-background": "transparent",
            "method-scan": "#A1FCDF",
            "method-deauth": "#FF6B6B",
            "method-passive": "#64FFDA",
            "method-pmkid": "#FFE156",
            "method-wps": "#DF7BFF",
            "method-evil-twin": "#45FFB3",
            "method-crack": "#A1FCDF",
            "signal-strong": "#64FFDA",
            "signal-medium": "#FFE156",
            "signal-weak": "#FF6B6B",
            "enc-wpa3": "#A1FCDF",
            "enc-wpa2": "#64FFDA",
            "enc-wpa": "#45FFB3",
            "enc-wep": "#FFE156",
            "enc-open": "#FF6B6B",
            "sidebar-active": "#64FFDA",
            "sidebar-inactive": "#6b7280",
            "sidebar-monitor": "#A1FCDF",
        },
    ),

    # ── NAUTILUS ─────────────────────────────────────────────
    "nautilus": TextualTheme(
        name="nautilus",
        primary="#0077BE",
        secondary="#20B2AA",
        background="#001F3F",
        surface="#003366",
        panel="#005A8C",
        warning="#FFD700",
        error="#FF6347",
        success="#32CD32",
        accent="#FF8C00",
        dark=True,
        variables={
            "input-cursor-background": "#0077BE",
            "footer-background": "transparent",
        },
    ),

    # ── COBALT ───────────────────────────────────────────────
    "cobalt": TextualTheme(
        name="cobalt",
        primary="#334D5C",
        secondary="#66B2FF",
        background="#1F262A",
        surface="#27343B",
        panel="#2D3E46",
        warning="#FFAA22",
        error="#E63946",
        success="#4CAF50",
        accent="#D94E64",
        dark=True,
        variables={
            "input-cursor-background": "#66B2FF",
            "footer-background": "transparent",
        },
    ),

    # ── TWILIGHT ─────────────────────────────────────────────
    "twilight": TextualTheme(
        name="twilight",
        primary="#367588",
        secondary="#5F9EA0",
        background="#191970",
        surface="#3B3B6D",
        panel="#4C516D",
        warning="#FFD700",
        error="#FF6347",
        success="#00FA9A",
        accent="#FF7F50",
        dark=True,
        variables={
            "input-cursor-background": "#367588",
            "footer-background": "transparent",
        },
    ),

    # ── SYNTHWAVE ────────────────────────────────────────────
    "synthwave": TextualTheme(
        name="synthwave",
        primary="#FF006E",
        secondary="#8338EC",
        background="#0F0A19",
        surface="#1A0F26",
        panel="#251833",
        warning="#FFBE0B",
        error="#FB5607",
        success="#06FFA5",
        accent="#3A86FF",
        dark=True,
        variables={
            "input-cursor-background": "#FF006E",
            "footer-background": "transparent",
            "method-scan": "#3A86FF",
            "method-deauth": "#FB5607",
            "method-passive": "#06FFA5",
            "method-pmkid": "#FFBE0B",
            "method-wps": "#8338EC",
            "method-evil-twin": "#FF006E",
            "method-crack": "#3A86FF",
            "signal-strong": "#06FFA5",
            "signal-medium": "#FFBE0B",
            "signal-weak": "#FB5607",
            "enc-wpa3": "#3A86FF",
            "enc-wpa2": "#06FFA5",
            "enc-wpa": "#FF006E",
            "enc-wep": "#FFBE0B",
            "enc-open": "#FB5607",
            "sidebar-active": "#06FFA5",
            "sidebar-inactive": "#6b7280",
            "sidebar-monitor": "#3A86FF",
        },
    ),

    # ── HYPERNOVA ────────────────────────────────────────────
    "hypernova": TextualTheme(
        name="hypernova",
        primary="#00F5D4",
        secondary="#7B2FF7",
        background="#0B0B12",
        surface="#121225",
        panel="#1A1A32",
        warning="#FEE440",
        error="#F72585",
        success="#80FF72",
        accent="#4CC9F0",
        dark=True,
        variables={
            "input-cursor-background": "#4CC9F0",
            "footer-background": "transparent",
            "method-scan": "#00F5D4",
            "method-deauth": "#F72585",
            "method-passive": "#80FF72",
            "method-pmkid": "#FEE440",
            "method-wps": "#7B2FF7",
            "method-evil-twin": "#4CC9F0",
            "method-crack": "#00F5D4",
            "signal-strong": "#80FF72",
            "signal-medium": "#FEE440",
            "signal-weak": "#F72585",
            "enc-wpa3": "#00F5D4",
            "enc-wpa2": "#80FF72",
            "enc-wpa": "#00F5D4",
            "enc-wep": "#FEE440",
            "enc-open": "#F72585",
            "sidebar-active": "#80FF72",
            "sidebar-inactive": "#6b7280",
            "sidebar-monitor": "#00F5D4",
        },
    ),

    # ── MANUSCRIPT (Light Theme) ─────────────────────────────
    "manuscript": TextualTheme(
        name="manuscript",
        primary="#2C4251",
        secondary="#6B4423",
        background="#F5F1E9",
        surface="#EBE6D9",
        panel="#E0DAC8",
        warning="#B4846C",
        error="#A94442",
        success="#2D5A27",
        accent="#8B4513",
        dark=False,
        variables={
            "input-cursor-background": "#2C4251",
            "input-selection-background": "#2C4251 25%",
            "footer-background": "#2C4251",
            "footer-key-foreground": "#F5F1E9",
            "footer-description-foreground": "#F5F1E9",
        },
    ),

    # ── MATTERMOST ───────────────────────────────────────────
    "mattermost": TextualTheme(
        name="mattermost",
        primary="#1C58D9",
        secondary="#26A186",
        background="#1E325C",
        surface="#253D6B",
        panel="#2E4A7A",
        warning="#F5A623",
        error="#D24B4E",
        success="#3DB887",
        accent="#8551FA",
        dark=True,
        variables={
            "input-cursor-background": "#1C58D9",
            "footer-background": "transparent",
        },
    ),
}

# Legacy aliases for backward compatibility
THEMES = BUILTIN_THEMES
```

---

## 3. Theme Selector (Copy This)

### Posting's Exact Implementation

Posting uses Textual's **built-in command palette** for theme switching. It hooks into `CommandPalette` events to provide live preview. Here's the exact code adapted for Sidewinder:

```python
# sidewinder/ui/app.py — ADD THESE METHODS TO SidewinderApp

from textual.command import CommandPalette
from textual.content import Content

# Add to SidewinderApp class:

_original_theme: str = "midnight"

@on(CommandPalette.Opened)
def palette_opened(self) -> None:
    """Store current theme before palette opens."""
    if not self.settings.command_palette.theme_preview:
        return
    self._original_theme = self.theme

@on(CommandPalette.OptionHighlighted)
def palette_option_highlighted(self, event: CommandPalette.OptionHighlighted) -> None:
    """Live preview theme as user navigates palette."""
    if not self.settings.command_palette.theme_preview:
        return
    prompt = event.highlighted_event.option.prompt
    themes = self.available_themes.keys()
    if isinstance(prompt, Content):
        candidate = prompt.plain
        if candidate in themes:
            self.theme = candidate
        else:
            self.theme = self._original_theme
        self.call_next(self.screen._update_styles)

@on(CommandPalette.Closed)
def palette_closed(self, event: CommandPalette.Closed) -> None:
    """Restore original theme if nothing selected."""
    if not self.settings.command_palette.theme_preview:
        return
    if not event.option_selected:
        self.theme = self._original_theme
```

### How to Register Theme Commands

```python
# sidewinder/commands.py
from textual.command import SimpleCommand, SimpleProvider

class SidewinderProvider(SimpleProvider):
    async def search(self, query: str) -> CommandPalette_hits:
        commands = []

        # Theme switching
        if not self.app.ansi_color:
            commands.append(
                SimpleCommand(
                    name="theme: Switch theme",
                    callback=self.app.action_change_theme,
                    help_text="Preview and select a theme",
                )
            )

        # ... other commands
        return commands
```

### Config for Theme Preview

```python
# sidewinder/config.py — add to Settings class

class CommandPaletteSettings(BaseModel):
    theme_preview: bool = True  # Enable live theme preview
    # ...

class Settings(BaseSettings):
    # ... existing fields
    theme: str = "midnight"
    theme_directory: Path = Path("~/.sidewinder/themes").expanduser()
    load_user_themes: bool = True
    load_builtin_themes: bool = True
    command_palette: CommandPaletteSettings = CommandPaletteSettings()
```

---

## 4. SCSS Rules (Copy This)

### Posting's Full SCSS — Adapted for Sidewinder

```scss
// sidewinder/ui/sidewinder.scss

// ── GLOBAL SCROLLBAR ────────────────────────────────────────
* {
  scrollbar-color: $primary 10%;
  scrollbar-color-hover: $primary 80%;
  scrollbar-color-active: $primary;
  scrollbar-background: $surface-darken-1;
  scrollbar-background-hover: $surface-darken-1;
  scrollbar-background-active: $surface-darken-1;
  scrollbar-size-vertical: 1;

  &:focus {
    scrollbar-color: $primary 50%;
  }
}

// ── SCREEN ──────────────────────────────────────────────────
Screen {
  background: $background;
}

ModalScreen {
  background: black 30%;
}

// ── SECTION PATTERN (From Posting) ─────────────────────────
// Apply to any bordered panel. Brightens on focus.
.section {
  border: round $accent 40%;
  border-title-color: $text-accent 50%;
  border-title-align: right;

  &:focus-within {
    border: round $accent 100%;
    border-title-color: $foreground;
    border-title-style: b;
  }
}

// ── HIDDEN / UTILITY ────────────────────────────────────────
.hidden {
  display: none;
}

// ── HEADER ──────────────────────────────────────────────────
AppHeader {
  color: $text-primary;
  padding: 1 3;
  height: auto;

  & > #app-title {
    text-style: bold;
  }

  & > #app-user-host {
    dock: right;
    color: $text-muted;
  }
}

// ── URL BAR (Adapted for SIDEBAR/ADAPTER BAR) ──────────────
AdapterBar {
  height: auto;
  padding: 0 3 0 3;

  & #main-row {
    height: 1;
  }

  & #adapter-selector {
    width: 20;
    height: 1;
    &:blur SelectCurrent {
      background: $primary-muted;
      #label {
        color: $text-primary;
      }
    }
  }

  & #mode-indicator {
    width: 10;
    height: 1;
    padding: 0 1;
    display: none;
    &.-monitor {
      color: $text-success;
      background: $success-muted;
    }
    &.-managed {
      color: $text-warning;
      background: $warning-muted;
    }
  }

  & #channel-display {
    width: 8;
    height: 1;
    padding: 0 1;
  }
}

// ── SEND BUTTON (Adapted for ACTION BUTTON) ─────────────────
SendButton {
  min-width: 8;
  background: $accent-muted;
  color: $text-accent;
  text-style: b;
  &:hover {
    background-tint: $text-accent 10%;
  }
}

// ── DATA TABLE ──────────────────────────────────────────────
DataTable {
  height: auto;
  width: 1fr;
  padding: 0 1;
  &:focus {
    width: 1fr;
    padding: 0;
    border-left: inner $accent;
  }
}

.SidewinderDataTable {
  & > .datatable--header {
    color: $text-success;
    background: $surface;
  }
  & > .datatable--header-cursor {
    color: $text;
    background: $block-cursor-background;
  }
  &:blur {
    & > .datatable--cursor {
      background: transparent;
    }
    & > .datatable--header-cursor {
      color: $text-success;
      background: $surface;
    }
  }
}

// ── INPUT ───────────────────────────────────────────────────
Input {
  border: none;
  width: 1fr;
  padding: 0 1;
  height: 1;
  &:focus {
    border: none;
    padding: 0 1;
  }
  &.error {
    border-left: thick $error;
  }
  &.-invalid {
    padding-left: 0;
    border-left: outer $error;
  }
}

// ── BUTTON ──────────────────────────────────────────────────
Button {
  padding: 0 1;
  height: 1;
  border: none;
  &:disabled {
    opacity: 40%;
  }
}

// ── SELECT ──────────────────────────────────────────────────
Select {
  height: 1;
  border: none;
  padding: 0;
  &:focus {
    #label {
      color: $block-cursor-foreground;
    }
    SelectCurrent {
      background: $block-cursor-background;
      .arrow {
        color: $block-cursor-foreground;
      }
    }
  }

  SelectCurrent {
    height: 1;
    border: none;
    padding: 0 1;
    background: $surface;
    .arrow {
      color: $text-disabled;
    }
  }

  & > SelectOverlay {
    padding: 0;
    border: none;
  }
}

// ── TABS (Posting's Compact Tab Style) ──────────────────────
Tabs {
  height: auto;
  & Underline {
    height: 1;
  }
}

// ── TABBED CONTENT ──────────────────────────────────────────
TabbedContent {
  height: 1fr;
}

// ── FOOTER ──────────────────────────────────────────────────
Footer {
  padding-left: 2;
}

// ── MODAL BODY (Help, Confirm, etc.) ────────────────────────
.modal-body {
  background: $background;
  padding: 1 2;
  width: 50%;
  height: auto;
  max-height: 70%;
  border: wide $background-lighten-2;
  border-title-color: $text;
  border-title-background: $background;
  border-title-style: bold;
}

// ── COMMAND PALETTE ─────────────────────────────────────────
CommandPalette {
  background: black 33%;

  & > Vertical {
    margin-top: 2;
    width: 65vw;
    max-height: 65vh;
  }

  & #--input {
    border: none;
    border-left: wide $accent;

    & CommandInput {
      height: 3;
      border: none;
      padding: 1 2;
    }

    & SearchIcon {
      display: none;
    }
  }

  & CommandList {
    border: none;
    border-left: wide $accent;
    padding-bottom: 1;
  }
}

// ── AUTO COMPLETE ───────────────────────────────────────────
AutoComplete {
  border-left: wide $accent;
  background: $surface;

  & AutoCompleteList {
    color: $text-muted;
    background: transparent;
  }

  & .autocomplete--highlight-match {
    color: $text-accent;
    background: $accent-muted;
  }
}

// ── JUMP MODE LABELS ────────────────────────────────────────
.textual-jump-label {
  dock: top;
  color: $text-accent;
  background: $accent-muted;
  text-style: bold;
  padding: 0 1;
  margin-right: 1;
  offset-y: -1;
  height: 1;
  width: auto;
}

#textual-jump-info {
  margin-bottom: 1;
  dock: bottom;
  height: 1;
  width: 1fr;
  background: $accent-muted;
  color: $text-accent;
  hatch: right $accent 30%;

  & Label {
    width: auto;
    padding: 0 1;
  }
}

#textual-jump-dismiss {
  dock: bottom;
  height: 1;
  background: transparent;
  color: $foreground-muted;
}

// ── RESPONSE AREA ───────────────────────────────────────────
ResponseArea {
  border-subtitle-color: $text-muted;

  &.success .border-title-status {
    color: $text-success;
    background: $success-muted;
  }
  &.warning .border-title-status {
    color: $text-warning;
    background: $warning-muted;
  }
  &.error .border-title-status {
    color: $text-error;
    background: $error-muted;
  }
}

// ── KEY-VALUE EDITOR ────────────────────────────────────────
KeyValueEditor {
  KeyValueInput {
    dock: bottom;
    height: auto;
    width: 1fr;

    #editing-row-label {
      display: none;
      padding: 0 1;
      height: 1;
      color: $text-accent;
    }

    #key-value-inputs {
      height: 1;
    }

    #row-writer-footer {
      height: auto;
    }

    &.edit-mode {
      background: $accent-muted;
      #editing-row-label {
        display: block;
      }
      #add-button {
        color: $text;
        background: $accent;
      }
      Input {
        color: $text;
        background: $accent 10%;
      }
    }

    & Input {
      border: none;
      width: 1fr;
      margin: 0 1;
      padding: 0 1;
      &:focus {
        border: none;
        padding: 0 1;
      }
    }

    & Button {
      background: $primary;
      color: $text;
      text-style: none;
      min-width: 0;
      width: auto;
      margin: 0 1;
      &:hover {
        text-style: b;
        border: none;
        background: $primary-darken-1;
      }
    }
  }

  & PostingDataTable {
    display: block;
  }

  & #empty-message {
    display: none;
  }

  &.empty {
    & PostingDataTable {
      display: none;
    }
    & #empty-message {
      color: $text-muted;
      hatch: right $surface-lighten-1 70%;
      display: block;
    }
  }
}

// ── COLLECTION BROWSER (Sidebar) ────────────────────────────
CollectionBrowser {
  height: 1fr;
  dock: left;
  width: auto;
  max-width: 33%;

  & Tree {
    color: $foreground 80%;
    background: transparent;
    width: 1fr;
    &:focus {
      color: $foreground;
    }
  }

  #empty-collection-label {
    color: $text-muted;
    padding: 1 2;
    width: 24;
  }

  &.section {
    border-subtitle-align: left;
  }

  & RequestPreview {
    color: $text-muted;
    dock: bottom;
    height: auto;
    max-height: 50%;
    width: 100%;
    padding: 0 1;
    border-top: solid $accent 40%;
    &.hidden {
      display: none;
    }
  }
}

// ── TEXT AREA ───────────────────────────────────────────────
TextArea {
  border: none;
  &:focus {
    border: none;
  }

  &.empty {
    & .text-area--cursor-line {
      background: transparent;
    }
    & .text-area--cursor-gutter {
      background: transparent;
    }
  }
}

// ── TEXT AREA FOOTER ────────────────────────────────────────
TextAreaFooter {
  dock: bottom;
  height: 1;
  width: 1fr;

  &:focus-within {
    background: $primary-muted;
  }

  &:disabled {
    background: transparent;
  }

  & Select {
    width: 8;
    margin-left: 1;
    & SelectCurrent {
      width: 8;
      background: $surface;
    }
    & SelectOverlay {
      width: 16;
    }
  }

  & Checkbox {
    margin: 0 1;
    height: 1;
    padding: 0 1;
    border: none;
    & .toggle--button {
      background: transparent;
    }
    &:focus {
      background: $block-cursor-background;
      & .toggle--button {
        background: $block-cursor-background;
      }
    }
  }

  #location-label {
    width: auto;
    color: $text 50%;
    margin-left: 1;
  }

  #mode-label {
    dock: left;
    padding: 0 1;
    display: none;
    margin-left: 1;
    &.visual-mode {
      color: $text-accent;
      background: $accent-muted;
      display: block;
    }
  }

  #rw-label {
    margin-left: 1;
    color: $text-warning;
    background: $warning-muted;
    padding: 0 1;
    display: none;
    &:disabled {
      opacity: 30%;
    }
    &.read-only {
      display: block;
    }
  }
}

// ── RICH LOG ────────────────────────────────────────────────
PostingRichLog {
  background: $surface 75%;
  padding-left: 1;
  &:focus {
    border-left: wide $accent;
    padding-left: 0;
  }
}

// ── SCRIPT OUTPUT ───────────────────────────────────────────
ScriptOutput {
  padding: 0 2;

  & #status-bar {
    height: 3;
    text-style: bold;
  }

  & Label {
    width: auto;
    &.-success {
      color: $text-success;
      text-style: not b;
    }
    &.-error {
      color: $text-error;
      text-style: not b;
    }
    &.-no-script {
      color: $text-muted;
      text-style: not b;
    }
  }

  & #script-output-title {
    text-style: b;
  }
}

// ── COMPACT MODE (Toggle via command palette) ───────────────
.SidewinderApp.-compact {
  & AppHeader {
    padding: 0 1;
  }

  & AppBody {
    padding: 0;
  }

  & Footer {
    FooterKey {
      margin-left: 1;
    }
    padding-left: 0;
  }

  & .section {
    border: none;
  }

  & Tabs {
    height: 1;
    & Underline {
      display: none;
      height: 0;
    }
  }

  & TabbedContent:focus-within Tabs {
    &:focus {
      & .-active {
        text-style: $block-cursor-text-style;
        color: $block-cursor-foreground;
        background: $block-cursor-background;
      }
    }
    &:blur Tab:enabled {
      &.-active {
        background: $panel;
      }
    }
  }

  & CollectionBrowser {
    background: $surface 50%;
    &:focus {
      outline: vkey $accent;
    }
    & RequestPreview {
      border-top: none;
      background: $surface 100%;
      padding: 0 1;
    }
  }

  & RequestEditor {
    background: $surface 25%;
  }

  & ResponseArea {
    background: $surface 10%;
  }

  & CommandPalette {
    align-horizontal: left;

    & > Vertical {
      margin-left: 11;
      margin-top: 1;
      max-width: 1fr;
      width: auto;
    }

    & #--input {
      border: none;
      border-left: wide $accent;

      & CommandInput {
        height: 1;
        border: none;
        padding: 0;
        width: 1fr;
      }
    }

    & CommandList {
      width: auto;
      border: none;
      max-height: 67vh;
      border-left: wide $accent;
      padding: 0;
      & > .option-list--option {
        padding: 0;
      }
    }
  }
}

// ── LAYOUT SWITCHING ────────────────────────────────────────
AppBody {
  padding: 0 2;

  &.layout-horizontal {
    layout: horizontal;

    & KeyValueInput {
      dock: top;
      & #key-value-inputs {
        layout: vertical;
        height: 3;
        & Button {
          width: 100%;
        }
      }
    }
  }

  &.layout-vertical {
    layout: vertical;

    & KeyValueInput #key-value-inputs {
      layout: horizontal;
    }
  }
}

// ── EMPTY STATE HATCH PATTERN ───────────────────────────────
$empty-hatch: right $surface-lighten-1 70%;

// ── CENTER MIDDLE UTILITY ───────────────────────────────────
CenterMiddle {
  align: center middle;
  width: 1fr;
  height: 1fr;
}
```

---

## 5. Layout Architecture

### Posting's Layout → Sidewinder Mapping

```
Posting                          Sidewinder
──────                           ──────────
AppHeader (version + host)   →   AppHeader (version + adapter)
UrlBar (method + URL + send) →   AdapterBar (adapter + channel + mode + status)
AppBody                       →   AppBody
  ├─ CollectionBrowser        →   AdapterList (docked left)
  ├─ RequestEditor            →   ScanEditor (tabbed: scan, target, capture)
  └─ ResponseArea             →   ResponseArea (tabbed: results, handshake, logs)
Footer                        →   Footer
```

### AppBody Structure

```python
# Sidewinder's AppBody — mirrors Posting's pattern
class AppBody(Vertical):
    """The body of the app."""

    def compose(self) -> ComposeResult:
        # Left sidebar (adapter list) — toggleable with ctrl+h
        adapter_list = AdapterList()
        adapter_list.display = self.settings.adapter_list.show_on_startup
        yield adapter_list

        # Main content area
        yield ScanEditor()      # Request editing equivalent
        yield ResponseArea()    # Response viewing equivalent
```

### TabbedContent Pattern

Posting uses `PostingTabbedContent` — a custom `TabbedContent` with vim bindings:

```python
# sidewinder/widgets/tabeted_content.py
from textual.binding import Binding
from textual.widgets import TabbedContent, Tabs


class SidewinderTabbedContent(TabbedContent):
    """TabbedContent with vim-style navigation."""

    BINDINGS = [
        Binding("l", "next_tab", "Next tab", show=False),
        Binding("h", "previous_tab", "Previous tab", show=False),
        Binding("down,j", "app.focus_next", "Focus next", show=False),
        Binding("up,k", "app.focus_previous", "Focus previous", show=False),
    ]

    def action_next_tab(self) -> None:
        tabs = self.query_one(Tabs)
        if tabs.has_focus:
            tabs.action_next_tab()

    def action_previous_tab(self) -> None:
        tabs = self.query_one(Tabs)
        if tabs.has_focus:
            tabs.action_previous_tab()
```

---

## 6. Widget Patterns

### CenterMiddle Utility

```python
# sidewinder/widgets/center_middle.py
from textual.widget import Widget


class CenterMiddle(Widget, inherit_bindings=False):
    """A container which aligns children on both axes."""
    DEFAULT_CSS = """
    CenterMiddle {
        align: center middle;
        width: 1fr;
        height: 1fr;
    }
    """
```

### Confirmation Dialog

```python
# sidewinder/widgets/confirmation.py
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmationModal(ModalScreen[bool]):
    """Generic confirmation dialog."""

    DEFAULT_CSS = """
    ConfirmationModal {
        align: center middle;
        height: auto;
        & #confirmation-buttons {
            margin-top: 1;
            width: 100%;
            height: 1;
            align: center middle;
            & > Button {
                width: 1fr;
            }
        }
    }
    """

    BINDINGS = [
        Binding("left,right,up,down,h,j,k,l", "move_focus", "Navigate", show=False),
    ]

    def __init__(
        self,
        message: str,
        confirm_text: str = "Yes [y]",
        confirm_binding: str = "y",
        cancel_text: str = "No [n]",
        cancel_binding: str = "n",
        auto_focus: str = "confirm",
    ) -> None:
        super().__init__()
        self.message = message
        self.confirm_text = confirm_text
        self.cancel_text = cancel_text
        self.auto_focus = auto_focus
        self._confirm_binding = confirm_binding
        self._cancel_binding = cancel_binding

    def on_mount(self) -> None:
        self._bindings.bind(self._confirm_binding, "screen.dismiss(True)")
        self._bindings.bind(self._cancel_binding, "screen.dismiss(False)")
        self._bindings.bind("escape", "screen.dismiss(False)")
        if self.auto_focus:
            self.query_one(f"#{self.auto_focus}-button").focus()

    def compose(self) -> ComposeResult:
        with Vertical(id="confirmation-screen", classes="modal-body") as container:
            container.border_title = "Confirm"
            yield Static(self.message)
            with Horizontal(id="confirmation-buttons"):
                yield Button(self.confirm_text, id="confirm-button")
                yield Button(self.cancel_text, id="cancel-button")
```

### Help Screen

```python
# sidewinder/widgets/help_screen.py
from dataclasses import dataclass
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import DataTable, Label, Static
from posting.widgets.datatable import PostingDataTable


@dataclass
class HelpData:
    title: str
    description: str


class Helpable:
    help: HelpData


class HelpScreen(ModalScreen[None]):
    """Modal help screen showing widget-specific keybindings."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
        & > VerticalScroll {
            background: $background;
            padding: 1 2;
            width: 65%;
            height: 80%;
            border: wide $background-lighten-2;
            border-title-color: $text;
            border-title-background: $background;
            border-title-style: bold;
        }
        & DataTable#bindings-table {
            width: 1fr;
            height: 1fr;
        }
        & HelpModalHeader {
            dock: top;
            width: 1fr;
            content-align: center middle;
            background: $background-lighten-1;
            color: $text-muted;
        }
        #footer-area {
            dock: bottom;
            height: auto;
            margin-top: 1;
            content-align: center middle;
            background: $background-lighten-1;
            color: $text-muted;
        }
    }
    """

    BINDINGS = [Binding("escape", "dismiss('')", "Close Help")]

    def __init__(self, widget: Helpable) -> None:
        super().__init__()
        self.helpable = widget

    def compose(self) -> ComposeResult:
        with VerticalScroll() as vs:
            vs.border_title = self.helpable.help.title
            yield Static(self.helpable.help.description)

            table = PostingDataTable(id="bindings-table", cursor_type="row", zebra_stripes=True)
            table.add_columns("Key", "Description")
            # Add keybindings from the widget
            yield table
            yield Label("Press ESC to dismiss.", id="footer-area")
```

### Adapter Selector (MethodSelector Equivalent)

```python
# sidewinder/widgets/adapter_selector.py
from dataclasses import dataclass
from textual import on
from textual.binding import Binding
from textual.message import Message
from textual.widgets import Select


class AdapterSelector(Select[str]):
    """Select a WiFi adapter."""

    BINDINGS = [
        Binding("1", "select_adapter('adapter1')", "Adapter 1", show=False),
        Binding("2", "select_adapter('adapter2')", "Adapter 2", show=False),
        Binding("3", "select_adapter('adapter3')", "Adapter 3", show=False),
    ]

    def __init__(self, adapters: list[tuple[str, str]], **kwargs):
        super().__init__(
            adapters,
            prompt="Adapter",
            allow_blank=False,
            type_to_search=False,
            **kwargs,
        )

    @dataclass
    class AdapterChanged(Message):
        value: str
        select: "AdapterSelector"

        @property
        def control(self):
            return self.select

    @on(Select.Changed)
    def adapter_selected(self, event: Select.Changed) -> None:
        event.stop()
        if event.value is not Select.BLANK:
            self.post_message(self.AdapterChanged(value=event.value, select=self))

    def action_select_adapter(self, adapter: str) -> None:
        self.select_or_highlight(adapter)
```

---

## 7. Visual Rules

### Color Application (From Posting's SCSS)

| Element | Color Variable | Usage |
|---------|---------------|-------|
| Active cursor | `$primary` | DataTable cursor, focused input |
| Section border (idle) | `$accent 40%` | Dim rounded border |
| Section border (focus) | `$accent 100%` | Bright rounded border |
| Input focus | `$surface-lighten-1` | Left border on focus |
| Input error | `$error` | Left thick border |
| Button hover | `$primary-darken-1` | Slightly darker |
| Button disabled | `opacity: 40%` | Faded |
| Tab active | `$block-cursor-background` | Background highlight |
| Tab inactive | `$panel` | Subtle background |
| Scrollbar | `$primary` | Matches theme primary |
| Modal overlay | `black 33%` | Semi-transparent |
| Empty state | `$surface-lighten-1` hatch | Diagonal lines pattern |
| Jump labels | `$text-accent` on `$accent-muted` | Bold, offset |
| Status success | `$text-success` on `$success-muted` | Green |
| Status warning | `$text-warning` on `$warning-muted` | Yellow |
| Status error | `$text-error` on `$error-muted` | Red |

### Border Patterns

```
Standard panel:   border: round $accent 40%
Focused panel:    border: round $accent 100%
Modal:            border: wide $background-lighten-2
Input focus:      border-left: outer $surface-lighten-1
Input error:      border-left: thick $error
DataTable focus:  border-left: inner $accent
AutoComplete:     border-left: wide $accent
Command palette:  border-left: wide $accent
```

### Padding Rules

```
AppHeader:        padding: 1 3
AppBody:          padding: 0 2
UrlBar:           padding: 0 3 0 3
Footer:           padding-left: 2
DataTable:        padding: 0 1
Input:            padding: 0 1
Modal body:       padding: 1 2
KeyValueInput:    margin: 0 1
Button:           padding: 0 1
```

### Height Rules

```
Header:           height: auto (1 row)
UrlBar main row:  height: 1
Footer:           height: auto (1 row)
Select:           height: 1
Button:           height: 1
Input:            height: 1
Tabs:             height: auto
Tab underline:    height: 1
TextAreaFooter:   dock: bottom, height: 1
Content area:     height: 1fr (fills remaining)
```

---

## 8. Sidewinder Theme File

### TCSS Variables (Matching Posting's Pattern)

```css
/* sidewinder/ui/sidewinder.tcss — CSS Variables */

/* These map to the theme variables set in themes.py */
/* Textual auto-generates these from the theme's variables dict */

/*
  $primary           → theme.primary
  $secondary         → theme.secondary
  $background        → theme.background
  $surface           → theme.surface
  $panel             → theme.panel
  $warning           → theme.warning
  $error             → theme.error
  $success           → theme.success
  $accent            → theme.accent

  Custom variables (from theme.variables):
  $method-scan       → method scan color
  $method-deauth     → method deauth color
  $method-passive    → method passive color
  $signal-strong     → strong signal color
  $signal-medium     → medium signal color
  $signal-weak       → weak signal color
  $enc-wpa3          → WPA3 color
  $enc-wpa2          → WPA2 color
  $enc-open          → open network color
  $sidebar-active    → active adapter color
  $sidebar-inactive  → inactive adapter color
  $sidebar-monitor   → monitor mode color
*/
```

### How Variables Flow

```
themes.py (Python dict)
    ↓ to_textual_theme()
TextualTheme (variables dict)
    ↓ register_theme()
Textual App (auto-generates CSS vars)
    ↓
SCSS files ($primary, $method-scan, etc.)
    ↓
Widget styles (border: round $accent 40%)
```

### Complete Theme Loading in App

```python
# sidewinder/app.py — in Posting.__init__()

def __init__(self, settings, ...):
    super().__init__()

    # Register all themes
    available_themes = {}
    if settings.load_builtin_themes:
        available_themes |= BUILTIN_THEMES
    if settings.load_user_themes:
        user_themes = load_user_themes(settings.theme_directory)
        available_themes |= user_themes

    for theme in available_themes.values():
        self.register_theme(theme)

    # Set default theme
    try:
        self.theme = settings.theme
    except InvalidThemeError:
        self.theme = "midnight"

    # Enable theme preview in command palette
    self.animation_level = settings.animation
```

---

## Quick Reference: What to Copy

| What | Where | Status |
|------|-------|--------|
| Theme model | `themes.py` Theme class | Copy `Theme` + `MethodStyles` + `SignalStyles` + `EncryptionStyles` + `SidebarStyles` |
| 13 built-in themes | `themes.py` BUILTIN_THEMES dict | Copy all, rename "galaxy" → "midnight" as default |
| Theme loader | `theme_loader.py` | Copy `load_user_themes()` + `register_themes()` |
| Theme selector | `app.py` command palette hooks | Copy `palette_opened` + `palette_option_highlighted` + `palette_closed` |
| SCSS rules | `sidewinder.scss` | Copy entire file, rename widget classes |
| Section pattern | `.section` CSS class | Copy exactly — this is the key visual pattern |
| Compact mode | `.SidewinderApp.-compact` | Copy entire block |
| Tabbed content | `SidewinderTabbedContent` | Copy, add vim h/l bindings |
| Center middle | `CenterMiddle` widget | Copy exactly |
| Confirmation modal | `ConfirmationModal` | Copy exactly |
| Help screen | `HelpScreen` + `HelpData` | Copy exactly |
| Empty state | `CenterMiddle` + hatch pattern | Copy CSS pattern |
| Modal overlay | `black 33%` background | Copy pattern |
| Input styling | Borderless + left border on focus/error | Copy SCSS |
| DataTable focus | `border-left: inner $accent` | Copy SCSS |
| Jump mode | `JumpOverlay` + `Jumper` | Copy from Posting's source |
```
