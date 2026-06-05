"""Sidewinder Tooltip Database.

Provides structured, contextual help and warnings for actions across the TUI.
"""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class Tooltip:
    """A contextual tooltip."""
    title: str
    description: str
    risk_level: str  # "Low", "Medium", "High"
    example: str = ""


# Centralized dictionary of tooltips mapping to UI components/actions
TOOLTIPS: Dict[str, Tooltip] = {
    "monitor_mode": Tooltip(
        title="Monitor Mode",
        description="Puts your WiFi adapter into a passive listening state, capturing all traffic in the air instead of just traffic meant for your machine.",
        risk_level="Low",
        example="Requires killing NetworkManager to prevent interference."
    ),
    "deauth_active": Tooltip(
        title="Targeted Deauthentication",
        description="Injects spoofed 'disconnect' frames to a specific connected client, forcing them to reconnect and transmit the 4-way EAPOL handshake.",
        risk_level="High",
        example="Highly visible to wireless intrusion detection systems (WIDS)."
    ),
    "deauth_broadcast": Tooltip(
        title="Broadcast Deauthentication",
        description="Sends disconnect frames to the broadcast address (FF:FF:FF:FF:FF:FF), disconnecting ALL clients on the target AP simultaneously.",
        risk_level="High",
        example="Extremely noisy and disruptive. May trigger alarms."
    ),
    "pmkid_attack": Tooltip(
        title="PMKID Capture",
        description="Requests the Pairwise Master Key Identifier directly from the AP. Does not require connected clients.",
        risk_level="Medium",
        example="Only works on routers with roaming/802.11r capabilities enabled."
    ),
    "evil_twin": Tooltip(
        title="Evil Twin Attack",
        description="Spawns a rogue Access Point mimicking the target SSID to trick clients into connecting to you instead of the real AP.",
        risk_level="High",
        example="Requires a secondary adapter for internet passthrough or captive portal."
    ),
}


def get_tooltip(key: str) -> Optional[Tooltip]:
    """Retrieve a tooltip by key."""
    return TOOLTIPS.get(key)
