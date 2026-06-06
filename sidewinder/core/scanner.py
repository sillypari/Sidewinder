"""Sidewinder Scan Engine.

Runs airodump-ng and parses its stdout in real-time.
Extracts networks (APs) and clients using a line-by-line state machine.

Parser state machine:
  IDLE -> detect "CH" line -> HEADER
  HEADER -> detect "BSSID PWR" -> AP_HEADER
  AP_HEADER -> blank line -> AP_DATA
  AP_DATA -> parse each line -> Network discovered
  AP_DATA -> detect "BSSID STATION" -> CLIENT_HEADER
  CLIENT_HEADER -> blank line -> CLIENT_DATA
  CLIENT_DATA -> parse each line -> Client discovered
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from enum import Enum, auto
from typing import Callable, Optional

from ..core.session import Client, Network
from .subprocess_mgr import SubprocessManager, get_manager

logger = logging.getLogger(__name__)


class ParseState(Enum):
    IDLE = auto()
    AP_HEADER = auto()
    AP_DATA = auto()
    CLIENT_HEADER = auto()
    CLIENT_DATA = auto()


class AirodumpParser:
    """Parse airodump-ng stdout line-by-line into Network and Client objects."""

    def __init__(self) -> None:
        self.state = ParseState.IDLE
        self.networks: dict[str, Network] = {}  # bssid -> Network
        self.clients: dict[str, Client] = {}    # mac -> Client

    def feed(self, line: str) -> Optional[Network | Client]:
        """Feed one line of airodump-ng output. Returns parsed object or None."""
        # airodump-ng uses carriage returns to clear screen — strip them
        line = line.replace("\r", "").strip()

        # Detect section headers (case-insensitive to handle both
        # live terminal output and CSV file headers)
        low = line.lower()
        if "bssid" in low and "station" in low:
            self.state = ParseState.CLIENT_HEADER
            return None
        if "bssid" in low and ("pwr" in low or "power" in low) and "essid" in low:
            self.state = ParseState.AP_HEADER
            return None

        # Blank lines transition states
        if not line:
            if self.state == ParseState.AP_HEADER:
                self.state = ParseState.AP_DATA
            elif self.state == ParseState.CLIENT_HEADER:
                self.state = ParseState.CLIENT_DATA
            return None

        # Non-blank data line after a header → transition to DATA state
        if self.state == ParseState.AP_HEADER:
            self.state = ParseState.AP_DATA
        elif self.state == ParseState.CLIENT_HEADER:
            self.state = ParseState.CLIENT_DATA

        # Parse data lines
        if self.state == ParseState.AP_DATA:
            return self._parse_ap_line(line)
        if self.state == ParseState.CLIENT_DATA:
            return self._parse_client_line(line)

        return None

    def _parse_ap_line(self, line: str) -> Optional[Network]:
        """Parse an airodump-ng AP table line.

        Format: BSSID, First time seen, Last time seen, channel, Speed, Privacy, Cipher, Authentication, Power, # beacons, # IV, LAN IP, ID-length, ESSID, Key
        """
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 14:
            return None
        # Basic MAC validation
        if not re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', parts[0]):
            return None
        try:
            bssid = parts[0].upper()
            channel = int(parts[3]) if parts[3].strip().lstrip('-').isdigit() else 0
            signal = int(parts[8]) if parts[8].strip().lstrip('-').isdigit() else -100
            privacy = parts[5].strip() or "OPN"
            cipher = parts[6].strip()
            auth = parts[7].strip()
            beacons = int(parts[9]) if parts[9].strip().isdigit() else 0
            data_packets = int(parts[10]) if parts[10].strip().isdigit() else 0
            essid_raw = parts[13].strip() if len(parts) > 13 else ""
            # Handle hidden SSID
            essid = essid_raw if essid_raw and essid_raw != "\x00" else ""
            first_seen = parts[1].strip()
            last_seen = parts[2].strip()

            network = Network(
                bssid=bssid,
                channel=channel,
                signal=signal,
                privacy=privacy,
                cipher=cipher,
                auth=auth,
                essid=essid,
                beacons=beacons,
                data_packets=data_packets,
                first_seen=first_seen,
                last_seen=last_seen,
            )
            self.networks[bssid] = network
            return network
        except (ValueError, IndexError) as e:
            logger.debug("AP parse error: %s | line: %s", e, line[:80])
            return None

    def _parse_client_line(self, line: str) -> Optional[Client]:
        """Parse an airodump-ng client table line.

        Format: Station MAC, First time seen, Last time seen, Power, # packets, BSSID, Probed ESSIDs
        """
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 6:
            return None
        if not re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', parts[0]):
            return None
        try:
            mac = parts[0].upper()
            signal = int(parts[3]) if parts[3].strip().lstrip('-').isdigit() else 0
            packets = int(parts[4]) if parts[4].strip().isdigit() else 0
            bssid = parts[5].upper() if len(parts) > 5 else ""
            probe = parts[6].strip() if len(parts) > 6 else ""
            first_seen = parts[1].strip()
            last_seen = parts[2].strip()

            client = Client(
                mac=mac,
                bssid=bssid,
                signal=signal,
                packets=packets,
                probe=probe,
                first_seen=first_seen,
                last_seen=last_seen,
            )
            self.clients[mac] = client
            return client
        except (ValueError, IndexError) as e:
            logger.debug("Client parse error: %s | line: %s", e, line[:80])
            return None


class ScanEngine:
    """Run airodump-ng and emit discovered networks and clients in real-time."""

    def __init__(self, mgr: Optional[SubprocessManager] = None) -> None:
        self.mgr = mgr or get_manager()
        self.parser = AirodumpParser()
        self._proc: Optional[asyncio.subprocess.Process] = None
        self._running = False

    async def scan(
        self,
        mon_iface: str,
        capture_prefix: str = "/tmp/sidewinder_scan",
        band: str = "",
        channels: list[int] | None = None,
        on_network: Optional[Callable[[Network], None]] = None,
        on_client: Optional[Callable[[Client], None]] = None,
    ) -> None:
        """Start scanning. Calls on_network/on_client for each discovered entity.

        Parses the airodump-ng CSV output file for real data (not stdout which
        contains screen-refresh escape sequences). CSV is written by airodump-ng
        with --write flag.

        Args:
            mon_iface: Monitor interface
            capture_prefix: Prefix for airodump-ng output files
            band: "a" for 5GHz, "bg" for 2.4GHz, "" for all
            channels: Specific channels to scan (optional)
            on_network: Callback for new/updated network
            on_client: Callback for new/updated client
        """
        cmd = [
            "airodump-ng",
            mon_iface,
            "--write", capture_prefix,
            "--output-format", "csv",
            "-a",     # Only show associated clients
            "--wps",  # Show WPS status
        ]
        if band:
            cmd.extend(["--band", band])
        if channels:
            cmd.extend(["--channel", ",".join(str(c) for c in channels)])

        logger.info("Starting scan on %s", mon_iface)
        self._running = True
        self._proc = await self.mgr.start_background(cmd)

        # Poll the CSV file for updates (airodump-ng stdout is screen refreshes)
        csv_file = f"{capture_prefix}-01.csv"
        while self._running:
            await asyncio.sleep(1.0)
            if os.path.exists(csv_file):
                try:
                    await self._parse_csv(csv_file, on_network, on_client)
                except Exception as e:
                    logger.debug("CSV parse error: %s", e)

    async def _parse_csv(
        self,
        csv_file: str,
        on_network: Optional[Callable[[Network], None]],
        on_client: Optional[Callable[[Client], None]],
    ) -> None:
        """Parse airodump-ng CSV output file."""
        with open(csv_file, errors="replace") as f:
            content = f.read()

        # Reset parser for fresh parse
        parser = AirodumpParser()
        for line in content.splitlines():
            result = parser.feed(line)
            if isinstance(result, Network) and on_network:
                on_network(result)
            elif isinstance(result, Client) and on_client:
                on_client(result)

        # Sync to our state
        self.parser.networks.update(parser.networks)
        self.parser.clients.update(parser.clients)

    def stop(self) -> None:
        """Stop scanning."""
        self._running = False

    async def stop_and_wait(self) -> None:
        """Stop scanning and clean up the background process."""
        self._running = False
        if self._proc:
            await self.mgr.kill_background(self._proc)
            self._proc = None

    def get_networks(self) -> list[Network]:
        """Get all discovered networks, sorted by signal strength."""
        return sorted(
            self.parser.networks.values(),
            key=lambda n: n.signal,
            reverse=True,
        )

    def get_clients(self, bssid: Optional[str] = None) -> list[Client]:
        """Get clients, optionally filtered by AP BSSID."""
        clients = list(self.parser.clients.values())
        if bssid:
            clients = [c for c in clients if c.bssid == bssid.upper()]
        return clients
