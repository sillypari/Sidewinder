"""Sidewinder Theme Loader.

Handles loading custom user themes and registering all themes with the Textual app.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
import yaml
from textual.app import App, InvalidThemeError
from textual.theme import Theme as TextualTheme

from .theme import Theme
from .themes import BUILTIN_THEMES

logger = logging.getLogger(__name__)


def load_user_themes(theme_dir: Path) -> dict[str, TextualTheme]:
    """Load YAML themes from the user themes directory."""
    themes: dict[str, TextualTheme] = {}
    if not theme_dir.exists():
        return themes

    for path in theme_dir.iterdir():
        if path.suffix in (".yaml", ".yml"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not data or not isinstance(data, dict):
                    continue
                # If name is not in YAML data, use filename
                if "name" not in data:
                    data["name"] = path.stem
                theme = Theme(**data)
                themes[theme.name] = theme.to_textual_theme()
                logger.info("Loaded custom user theme: %s", theme.name)
            except Exception as e:
                logger.warning("Failed to load user theme from %s: %s", path, e)
    return themes


def register_themes(app: App, settings) -> None:
    """Register all themes with the app and set the configured theme."""
    available: dict[str, TextualTheme] = {}

    # Always include midnight as fallback/default
    if "midnight" in BUILTIN_THEMES:
        available["midnight"] = BUILTIN_THEMES["midnight"]

    # Load built-in themes
    load_builtin = getattr(settings, "load_builtin_themes", True)
    if load_builtin:
        available.update(BUILTIN_THEMES)

    # Load user themes
    load_user = getattr(settings, "load_user_themes", True)
    theme_dir_str = getattr(settings, "theme_directory", "~/.sidewinder/themes")
    theme_dir = Path(os.path.expanduser(theme_dir_str) if isinstance(theme_dir_str, str) else theme_dir_str)
    
    if load_user:
        try:
            user_themes = load_user_themes(theme_dir)
            available.update(user_themes)
        except Exception as e:
            logger.warning("Error loading user themes: %s", e)

    # Register all resolved themes with the Textual App
    for theme in available.values():
        app.register_theme(theme)

    # Set configured theme
    configured_theme = getattr(settings, "theme", "midnight")
    try:
        app.theme = configured_theme
    except InvalidThemeError:
        logger.warning("Theme %r not found, falling back to 'midnight'", configured_theme)
        app.theme = "midnight"
