"""Sidewinder Configuration Management.

Handles loading, saving, and querying user configuration.
Configuration is stored in ~/.sidewinder/config.json
"""
import json
import logging
import os
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)


@dataclass
class SidewinderConfig:
    """Application configuration."""
    
    # Paths
    capture_dir: str = "~/.sidewinder/captures"
    wordlist_dir: str = "~/.sidewinder/wordlists"
    results_dir: str = "~/.sidewinder/results"
    
    # Defaults
    default_wordlist: str = "/usr/share/wordlists/rockyou.txt"
    default_channel: int = 1
    default_deauth_count: int = 10
    
    # Timeouts
    capture_timeout_seconds: float = 300.0
    deauth_cooldown_seconds: float = 10.0
    
    # Hardware/Network
    regulatory_domain: str = "00"  # "00" means global/world. Set to "US", "GB", etc.
    mac_randomization: bool = False

    def save(self, path: str = "~/.sidewinder/config.json") -> None:
        """Save configuration to disk."""
        expanded_path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(expanded_path), exist_ok=True)
        try:
            with open(expanded_path, "w") as f:
                json.dump(asdict(self), f, indent=4)
        except Exception as e:
            logger.error("Failed to save config: %s", e)

    @classmethod
    def load(cls, path: str = "~/.sidewinder/config.json") -> "SidewinderConfig":
        """Load configuration from disk, creating defaults if missing."""
        expanded_path = os.path.expanduser(path)
        if not os.path.exists(expanded_path):
            config = cls()
            config.save(path)
            return config

        try:
            with open(expanded_path, "r") as f:
                data = json.load(f)
            # Filter unknown kwargs to be forward-compatible
            import dataclasses
            valid_keys = {f.name for f in dataclasses.fields(cls)}
            filtered_data = {k: v for k, v in data.items() if k in valid_keys}
            return cls(**filtered_data)
        except Exception as e:
            logger.error("Failed to load config (using defaults): %s", e)
            return cls()

    def get_capture_path(self, bssid: str) -> str:
        """Generate a capture file path for a given BSSID."""
        expanded_dir = os.path.expanduser(self.capture_dir)
        os.makedirs(expanded_dir, exist_ok=True)
        import re
        sanitized = re.sub(r'[^a-zA-Z0-9]', '', bssid)
        return os.path.join(expanded_dir, f"capture_{sanitized}")
