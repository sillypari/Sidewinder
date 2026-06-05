"""Sidewinder Monitor Mode Manager.

Enter/exit monitor mode using direct iw/ip calls — bypasses airmon-ng entirely.

Implements these airmon-ng functions natively:
  setLink(), startMac80211Iface(), stopMac80211Iface(), setChannelMac80211()

Two paths:
  - Standard mac80211: creates monitor VIF (iw phy <phy> interface add <name> type monitor)
  - Bad driver fallback: direct mode change (iw dev <iface> set type monitor)
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from .subprocess_mgr import run

logger = logging.getLogger(__name__)

# ARPHRD_IEEE80211_RADIOTAP - what sysfs type field shows for monitor mode
ARPHRD_IEEE80211_RADIOTAP = "803"
# ARPHRD_ETHER - normal managed mode
ARPHRD_ETHER = "1"


async def set_link(iface: str, state: str) -> None:
    """Bring interface up or down.

    Equivalent to airmon-ng setLink().

    Args:
        iface: Interface name (e.g., "wlan0")
        state: "up" or "down"
    """
    await run(["ip", "link", "set", iface, state])
    logger.debug("Interface %s -> %s", iface, state)


async def enter_monitor_mode(
    iface: str,
    phy: str,
    channel: int = 6,
) -> str:
    """Enter monitor mode via VIF creation (standard mac80211 path).

    Equivalent to airmon-ng startMac80211Iface().
    Creates a new monitor VIF named '<iface>mon'.

    Args:
        iface: Base interface name (e.g., "wlan0")
        phy: PHY name (e.g., "phy0")
        channel: Initial channel (default 6)

    Returns:
        Monitor interface name (e.g., "wlan0mon")
    """
    mon_iface = f"{iface}mon"
    logger.info("Entering monitor mode: %s -> %s", iface, mon_iface)

    # 1. Bring base interface down
    await set_link(iface, "down")

    # 2. Create monitor VIF
    await run(["iw", "phy", phy, "interface", "add", mon_iface, "type", "monitor"])

    # 3. Bring monitor interface up
    await set_link(mon_iface, "up")

    # 4. Set initial channel
    await set_channel(mon_iface, channel)

    # 5. Set TX power (3000 = 30 dBm in mBm)
    try:
        await run(["iw", "dev", mon_iface, "set", "txpower", "fixed", "3000"], check=False)
    except Exception:
        pass  # TX power setting may fail on some drivers, non-fatal

    # 6. Verify monitor mode is active
    mode = get_interface_mode_sync(mon_iface)
    if mode != "monitor":
        raise RuntimeError(
            f"Monitor mode verification failed: expected 'monitor', got '{mode}' on {mon_iface}"
        )

    logger.info("Monitor mode active: %s (ch %d)", mon_iface, channel)
    return mon_iface


async def enter_monitor_mode_bad_driver(iface: str) -> str:
    """Enter monitor mode via direct type change (RTL8821AU morrownr / bad driver fallback).

    Equivalent to airmon-ng changeMac80211IfaceTypeMonitor().
    Does NOT create a new VIF — changes existing interface type in-place.

    Args:
        iface: Interface name to modify

    Returns:
        Same iface name (modified in-place)
    """
    logger.info("Entering monitor mode (bad driver path): %s", iface)

    await set_link(iface, "down")
    await run(["iw", "dev", iface, "set", "type", "monitor"])
    await run(["iw", "dev", iface, "set", "monitor", "otherbss"], check=False)
    await set_link(iface, "up")

    mode = get_interface_mode_sync(iface)
    if mode != "monitor":
        raise RuntimeError(
            f"Direct monitor mode failed: expected 'monitor', got '{mode}' on {iface}"
        )

    logger.info("Monitor mode active (bad driver): %s", iface)
    return iface


async def exit_monitor_mode(
    mon_iface: str,
    iface: str,
    phy: str,
) -> None:
    """Exit monitor mode, restore managed mode.

    Equivalent to airmon-ng stopMac80211Iface().
    Deletes the monitor VIF and recreates the station VIF.

    Args:
        mon_iface: Monitor interface name to delete (e.g., "wlan0mon")
        iface: Managed interface to recreate (e.g., "wlan0")
        phy: PHY name for VIF recreation (e.g., "phy0")
    """
    logger.info("Exiting monitor mode: %s -> %s", mon_iface, iface)

    # 1. Delete monitor VIF
    await run(["iw", "dev", mon_iface, "del"], check=False)

    # 2. Recreate managed VIF (may already exist if using bad driver path)
    try:
        await run(["iw", "phy", phy, "interface", "add", iface, "type", "station"])
    except RuntimeError:
        # Interface already exists (bad driver path)
        pass

    # 3. Bring up
    await set_link(iface, "up")

    logger.info("Managed mode restored: %s", iface)


async def set_channel(
    iface: str,
    channel: int,
    bandwidth: str = "",
) -> None:
    """Set channel on monitor interface.

    Equivalent to airmon-ng setChannelMac80211().

    Args:
        iface: Monitor interface name
        channel: Channel number (1-14 for 2.4GHz, 36-165 for 5GHz)
        bandwidth: Optional bandwidth ("HT20", "HT40+", "HT40-", "80MHz")
    """
    cmd = ["iw", "dev", iface, "set", "channel", str(channel)]
    if bandwidth:
        cmd.append(bandwidth)
    await run(cmd)
    logger.debug("Channel set: %s -> ch%d %s", iface, channel, bandwidth)


async def lock_channel(mon_iface: str, channel: int) -> bool:
    """Lock to specific channel and verify the lock succeeded.

    Args:
        mon_iface: Monitor interface name
        channel: Channel number to lock to

    Returns:
        True if channel was set and verified correctly.
    """
    await set_channel(mon_iface, channel)
    # Verify via iw dev info
    result = await run(["iw", "dev", mon_iface, "info"], check=False)
    return f"channel {channel}" in result.stdout.lower()


async def set_power_save(iface: str, enable: bool) -> None:
    """Enable or disable power save mode.

    Args:
        iface: Interface name
        enable: True to enable power save, False to disable
    """
    state = "on" if enable else "off"
    await run(["iw", "dev", iface, "set", "power_save", state], check=False)


def get_interface_mode_sync(iface: str) -> str:
    """Read current interface mode synchronously from sysfs type field.

    type=1   = ARPHRD_ETHER = managed/station
    type=803 = ARPHRD_IEEE80211_RADIOTAP = monitor

    Args:
        iface: Interface name to inspect

    Returns:
        "monitor", "managed", or "unknown(<type>)"
    """
    type_path = Path(f"/sys/class/net/{iface}/type")
    if not type_path.exists():
        return "unknown"
    iface_type = type_path.read_text().strip()
    if iface_type == ARPHRD_IEEE80211_RADIOTAP:
        return "monitor"
    if iface_type == ARPHRD_ETHER:
        return "managed"
    return f"unknown({iface_type})"


class MonitorWatcher:
    """Watch monitor mode status and report if lost.

    Runs as a background async task.
    Reports events but NEVER auto-fixes — recommendation only.
    """

    def __init__(self, iface: str, poll_interval: float = 2.0) -> None:
        """Initialise the watcher.

        Args:
            iface: Monitor interface name to watch
            poll_interval: Seconds between sysfs polls (default 2.0)
        """
        self.iface = iface
        self.poll_interval = poll_interval
        self._running = False

    async def watch(self):
        """Watch monitor mode. Yields events when mode is lost.

        Yields:
            dict with keys: type, iface, current_mode, message, recommendation
        """
        self._running = True
        while self._running:
            await asyncio.sleep(self.poll_interval)
            mode = get_interface_mode_sync(self.iface)
            if mode != "monitor":
                yield {
                    "type": "MODE_LOST",
                    "iface": self.iface,
                    "current_mode": mode,
                    "message": f"Monitor mode lost on {self.iface} (now: {mode})",
                    "recommendation": "Press [R] to re-enable monitor mode",
                }

    def stop(self) -> None:
        """Stop the watcher."""
        self._running = False
