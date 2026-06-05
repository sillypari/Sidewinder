# Gemini 3.1 Pro — Sidewinder Systematic Completion Prompt

## Your Role

You are a senior Python security engineer completing the **Sidewinder** WiFi audit tool. This is a terminal-native (TUI) tool that bypasses airmon-ng wrappers and natively communicates with Linux via iw/ip/sysfs.

**Your mission:** Systematically complete every missing feature, fix every bug, and ensure zero resource leaks and best-in-class exception handling throughout.

---

## Project Context

**Working directory:** `C:\Users\Parikshit\Desktop\NewGenApps\Sidewinder\sidewinder\`

**Current state (v0.4.0):**
- 24 source files, ~5,500 lines of production code
- 51 tests passing (4 skipped — Linux-only on Windows)
- 31 bugs found (BUG-001 to BUG-031, see `Bug.md`)
- Backend modules exist: adapter detection, monitor mode, scan engine, EAPOL capture, aircrack/hashcat cracking, session management, subprocess management, service kill/restore, cleanup with signal handlers
- UI screens exist: MainMenu, Adapter, Scan, TargetSelect, CaptureMethod, CaptureProgress, DeauthSelect, CrackProgress, Result, Error, Help, Resume, CommandPalette

**Document Authority (single source of truth hierarchy):**
1. `IMPLEMENTATION.md` — canonical for file structure, code snippets, dependency list
2. `Sidewinder.md` — philosophy + research
3. `PLAN.md` — UX design + TUI mockups (16 screens, 60 UX decisions)
4. `Bug.md` — 31 bugs to fix
5. `Track.md` — implementation tracker

**Read these files before writing any code:**
- `Documenation/PLAN.md` (4254 lines) — full spec
- `Documenation/IMPLEMENTATION.md` (2072 lines) — code structure
- `Bug.md` (418 lines) — all 31 bugs with exact line numbers
- `Track.md` — current status

---

## Architecture & Conventions

### Framework
- **TUI:** Textual (handles keyboard input, screen management, async integration)
- **Python:** 3.10+, asyncio-first
- **Dependencies:** textual>=0.40, scapy>=2.5
- **Entry point:** `sidewinder/sidewinder.py` → `main()`

### Code Style
- Type hints on ALL functions and class attributes
- Docstrings on ALL public classes and methods
- `from __future__ import annotations` in every file
- No comments unless asked
- Minimal borders (╭╮╰╯ box-drawing characters)
- Vim-style keybindings (j/k navigate, Enter selects, Esc back, / search, ? help)

### Exception Handling Requirements
- **Never swallow errors** — always notify user via `SidewinderError`
- **Always show What/Why/HowToFix** — structured error messages
- **Always use try/except** around subprocess calls, file I/O, sysfs reads
- **Always use async subprocess** via `SubprocessManager` — never `subprocess.run()` in async context
- **Always close resources** — use `async with` or explicit `.close()` in finally blocks
- **Always handle `CancelledError`** — don't let task cancellation leak resources
- **Always use context managers** for file handles, processes, network connections
- **Always set timeouts** on subprocess calls and network operations
- **Always use process groups** — `os.setsid()` for attack processes so we can kill the tree
- **Always verify process exit** — check returncode, don't assume success

### Resource Leak Prevention Rules
1. Every `open()` must be in a `with` block or have explicit `.close()` in `finally`
2. Every `asyncio.create_task()` must be tracked and cancelled on screen exit
3. Every subprocess must be tracked in `SubprocessManager` for cleanup on signal
4. Every timer (`set_interval`) must be stopped on screen exit
5. Every signal handler must be removable
6. Every file created in `/tmp/` must be listed in `CLEANUP_PATTERNS`
7. No circular imports — use `TYPE_CHECKING` for type hints
8. Every `asyncio.get_event_loop()` call must handle deprecated loop= parameter

---

## Phase 1: Fix All 31 Bugs (BUG-001 to BUG-031)

Fix every bug in `Bug.md`. Here is the complete list:

### CRITICAL (5 bugs) — Fix First

**BUG-001:** `ui/screens.py` — `ScanScreen.action_select_target()` creates `CaptureMethodScreen()` with no args. Pass `target=network` to the screen. The network must be looked up from `self.app.session.scan_results` by BSSID.

**BUG-002:** `ui/screens.py` — `DeauthSelectScreen.action_confirm()` discards checkbox state. Collect selected clients from the DataTable, pass them to `CaptureProgressScreen`. Add `selected_clients` parameter to `CaptureProgressScreen.__init__()`.

**BUG-003:** `ui/screens.py` — `ScanScreen.add_network()` calls `table.update_cell(row_key, "BSSID", ...)` but `update_cell` takes a `CellKey` not a string column name. Fix: use `table.update_cell(row_key, col_key, data)` where `col_key` is from `list(table.columns.keys())[i]`. Also ensure duplicate rows are not added on refresh.

**BUG-004:** `ui/app.py:73` — `_existing_session` is `None` if session has no scan results. Fix: preserve session even if empty — show resume prompt with "Session started at {time}, no scans yet" message.

**BUG-005:** `ui/screens.py` — `ResumeScreen.action_resume()` sets `self.app.session` but doesn't restore state. Fix: populate scan_results, clients, selected_target, captures, handshake, cracked_passwords from the loaded session. The app should use the resumed session for all subsequent operations.

### HIGH (7 bugs)

**BUG-006:** `core/cracker.py:95` — Hashcat speed regex `(k?M?G?)` matches wrong units. Fix: change to `(k|M|G)?`.

**BUG-007:** `core/subprocess_mgr.py:98` — `proc.returncode or 0` masks None. Fix: use `proc.returncode if proc.returncode is not None else -1`.

**BUG-008:** `ui/components.py:175` — `ErrorCard.__init__` takes `how_to_fix: str` but receives `list[str]`. Fix: accept `list[str]` and join with `\n` in render.

**BUG-009 to BUG-012:** `adapters/rtl8821au.py`, `adapters/mt7902.py`, `adapters/rt5370.py` — All call `subprocess.run()` synchronously in async context. Fix: replace with `asyncio.create_subprocess_exec()` or use `SubprocessManager.run()`. Every adapter detection function must be `async def`.

### MEDIUM (18 bugs)

**BUG-013:** `core/scanner.py` — Import inside method body. Move to top-level.

**BUG-014:** `ui/screens.py` — Cleanup menu calls `self.app.action_cleanup()` which doesn't exist. Fix: implement `action_cleanup()` in `SidewinderApp` that runs `CleanupManager.full_cleanup()`.

**BUG-015:** `ui/screens.py` — Multiple `pop_screen()` calls in `ResultScreen.action_main_menu()` can overflow the stack. Fix: use `self.app.switch_screen(MainMenuScreen())` instead of popping.

**BUG-016:** `core/monitor.py`, `core/cleanup.py` — `loop=` parameter deprecated in Python 3.12+. Fix: remove `loop=` from `asyncio.ensure_future()` calls. Use `asyncio.get_running_loop()`.

**BUG-017:** `core/capture.py` — `poll_eapol()` has no type annotation on `on_progress` callback. Add `Callable[[bool, bool, bool, bool, str], None]` type hint.

**BUG-018:** `attacks/deauth.py` — `on_progress` callback untyped. Add proper `Callable` type hint.

**BUG-019:** `core/capture.py` — `poll_eapol()` opens PCAP file every 2 seconds and never closes previous handle. Fix: open once, seek on each poll, close in finally block.

**BUG-020:** `core/capture.py` — `sha256` computation opens file and leaks handle. Fix: use `with` block.

**BUG-021:** `core/services.py` — `ps` output truncated. Fix: use `ps -eo pid,comm` or parse stderr properly.

**BUG-022:** `core/errors.py` — `AdapterError` class is dead code (never used). Remove or use in adapter modules.

**BUG-023:** `core/cracker.py` — Double `.replace()` on hashcat output. Fix: remove redundant replace.

**BUG-024:** `attacks/deauth.py` — Unused import. Remove.

**BUG-025:** 0% test coverage on scanner, cleanup, adapter, subprocess, monitor, services, deauth, screens.

**BUG-026:** `core/adapter.py` — `_check_monitor_via_iw()` is sync and blocks event loop. Make async.

**BUG-027 to BUG-029:** Multiple sync subprocess calls in adapter modules (same as BUG-009 to BUG-012).

**BUG-030:** `ui/screens.py` — ScanScreen never kills airodump-ng on exit. Fix: ensure `stop_and_wait()` is called and process is terminated.

**BUG-031:** `ui/screens.py` — CaptureProgressScreen pushes CrackProgressScreen mid-capture on handshake detection. Fix: complete capture first, then transition.

---

## Phase 2: Missing Core Modules

### 2.1 — `core/rfkill.py` (PLAN Section 16.2)

Create rfkill check/unblock module:

```python
"""Rfkill management — check and unblock wireless kill switches."""
from __future__ import annotations

import asyncio

async def rfkill_check() -> dict[str, str]:
    """Check rfkill status for all wireless devices.
    
    Returns:
        Dict mapping device name to block status ('blocked' or 'unblocked').
    """
    # Parse /sys/class/rfkill/rfkill*/soft and /sys/class/rfkill/rfkill*/hard
    # Also run: rfkill list (async)
    
async def rfkill_unblock() -> bool:
    """Unblock all wireless devices.
    
    Returns:
        True if all devices were successfully unblocked.
    """
    # Run: rfkill unblock wifi
    # Verify by re-checking status
```

- Use `asyncio.create_subprocess_exec()` for `rfkill` commands
- Handle FileNotFoundError if rfkill not installed
- Parse sysfs as primary (faster), rfkill command as fallback
- Timeout: 5 seconds on subprocess calls

### 2.2 — `core/config.py` (PLAN Section 7)

Create configuration module:

```python
"""Sidewinder configuration — ~/.sidewinder/config.toml"""
from __future__ import annotations

import os
import tomllib  # Python 3.11+
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Config:
    """Sidewinder configuration with sensible defaults."""
    
    # Adapter
    preferred_adapter: str = ""          # Empty = auto-detect
    reg_domain: str = ""                 # Empty = no regulatory domain set
    
    # Scan
    scan_timeout: int = 30               # seconds
    scan_channels_2g: str = "1-13"       # 2.4GHz channels
    scan_channels_5g: str = "36,40,44,48,52,56,60,64,100,104,108,112,116,120,124,128,132,136,140,149,153,157,161,165"
    
    # Capture
    eapol_timeout: int = 120             # seconds to wait for handshake
    eapol_poll_interval: float = 2.0     # seconds between PCAP polls
    
    # Deauth
    deauth_count: int = 10               # frames per burst
    deauth_bursts: int = 3               # number of bursts
    deauth_cooldown: int = 10            # seconds between bursts
    deauth_rate: int = 10                # frames per second
    
    # Crack
    default_wordlist: str = "/usr/share/wordlists/rockyou.txt"
    aircrack_threads: int = 0            # 0 = auto
    
    # Logging
    log_level: str = "INFO"
    log_dir: str = "~/.sidewinder/logs/"
    
    # Paths
    session_path: str = "~/.sidewinder/session.json"
    capture_dir: str = "~/.sidewinder/captures/"
    
    @classmethod
    def load(cls, path: str = "") -> "Config":
        """Load config from TOML file, falling back to defaults."""
        config_path = os.path.expanduser(path or "~/.sidewinder/config.toml")
        if not os.path.exists(config_path):
            return cls()
        
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        
        # Map TOML keys to dataclass fields
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
    
    def save(self, path: str = "") -> str:
        """Save config to TOML file."""
        # ...tomli_w or manual TOML writing
```

### 2.3 — `core/logger.py` (PLAN Section 21.4)

Create JSONL logger with RingBuffer for live logs:

```python
"""JSONL structured logger — ring buffer for live display + file persistence."""
from __future__ import annotations

import json
import os
from collections import deque
from datetime import datetime
from typing import Any, Optional

class RingBuffer:
    """Fixed-size deque for in-memory log display."""
    
    def __init__(self, maxsize: int = 500) -> None:
        self._buffer: deque[dict[str, Any]] = deque(maxlen=maxsize)
    
    def append(self, entry: dict[str, Any]) -> None:
        self._buffer.append(entry)
    
    def get_recent(self, n: int = 50) -> list[dict[str, Any]]:
        return list(self._buffer)[-n:]
    
    def clear(self) -> None:
        self._buffer.clear()

class JSONLLogger:
    """Structured logger that writes JSONL files and maintains a ring buffer."""
    
    def __init__(self, log_dir: str = "~/.sidewinder/logs/") -> None:
        self._log_dir = os.path.expanduser(log_dir)
        self._ring = RingBuffer()
        self._file: Optional[object] = None  # Will be TextIOWrapper
    
    def start(self, session_id: str) -> str:
        """Start logging to a new file. Returns the file path."""
        os.makedirs(self._log_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self._log_dir, f"{ts}_{session_id[:8]}.jsonl")
        self._file = open(path, "a")
        return path
    
    def log(self, event: str, **kwargs: Any) -> None:
        """Log a structured event."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event,
            **kwargs,
        }
        self._ring.append(entry)
        if self._file:
            self._file.write(json.dumps(entry) + "\n")
            self._file.flush()
    
    def get_live_logs(self, n: int = 50) -> list[dict[str, Any]]:
        """Get recent log entries for live display."""
        return self._ring.get_recent(n)
    
    def close(self) -> None:
        """Close the log file."""
        if self._file:
            self._file.close()
            self._file = None
```

### 2.4 — `core/attack.py` (PLAN Section 21)

Create aireplay-ng wrapper (attack logic):

```python
"""Aireplay-ng wrapper — deauth frame injection with rate control."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from .subprocess_mgr import SubprocessManager, ProcessResult
from .errors import SidewinderError, Severity, Category, ERROR_DB

logger = logging.getLogger(__name__)

async def inject_deauth(
    iface: str,
    bssid: str,
    client: str = "FF:FF:FF:FF:FF:FF",  # broadcast
    count: int = 10,
    timeout: float = 30.0,
    subprocess_mgr: Optional[SubprocessManager] = None,
) -> ProcessResult:
    """Inject deauthentication frames via aireplay-ng.
    
    Args:
        iface: Monitor mode interface
        bssid: Target AP BSSID
        client: Target client MAC (default: broadcast)
        count: Number of deauth frames to send
        timeout: Maximum seconds to wait
        subprocess_mgr: Optional pre-configured subprocess manager
    
    Returns:
        ProcessResult with returncode, stdout, stderr
    
    Raises:
        SidewinderError: If aireplay-ng fails or is not found
    """
    mgr = subprocess_mgr or SubprocessManager()
    
    cmd = [
        "aireplay-ng",
        "--deauth", str(count),
        "-a", bssid,
        "-c", client,
        "--ignore-negative-one",
        iface,
    ]
    
    try:
        result = await mgr.run(cmd, timeout=timeout)
        if result.returncode != 0 and "No such BSSID" not in result.stderr:
            raise SidewinderError(
                severity=Severity.ERROR,
                category=Category.PROCESS,
                what="Deauth injection failed",
                why=f"aireplay-ng exited with code {result.returncode}",
                how_to_fix=[
                    "Verify adapter is in monitor mode",
                    "Check target BSSID is on same channel",
                    "Try: aireplay-ng --test <iface> to verify injection",
                ],
                raw_error=result.stderr[:500],
            )
        return result
    except FileNotFoundError:
        raise ERROR_DB["AIREPLAY_FAILED"]
    except asyncio.TimeoutError:
        raise SidewinderError(
            severity=Severity.ERROR,
            category=Category.PROCESS,
            what="Deauth injection timed out",
            why=f"No response after {timeout}s",
            how_to_fix=[
                "Check adapter is on correct channel",
                "Verify target AP is in range",
                "Try increasing timeout",
            ],
        )
```

### 2.5 — `core/vm.py` (PLAN Section 16.2)

Create VM detection module:

```python
"""VM detection — check if running in a virtual machine."""
from __future__ import annotations

import asyncio
import os

async def detect_vm() -> dict[str, str]:
    """Detect if running in a VM.
    
    Returns:
        Dict with keys: 'is_vm', 'vm_type', 'confidence'
    """
    checks = {}
    
    # Check /sys/class/dmi/id/product_name
    try:
        with open("/sys/class/dmi/id/product_name") as f:
            product = f.read().strip().lower()
            if any(vm in product for vm in ["virtualbox", "vmware", "kvm", "qemu", "xen", "hyper-v"]):
                checks["dmi_product"] = product
    except (FileNotFoundError, PermissionError):
        pass
    
    # Check /proc/cpuinfo for hypervisor flag
    try:
        with open("/proc/cpuinfo") as f:
            content = f.read()
            if "hypervisor" in content:
                checks["hypervisor_flag"] = True
    except (FileNotFoundError, PermissionError):
        pass
    
    # Check systemd-detect-virt (async)
    try:
        proc = await asyncio.create_subprocess_exec(
            "systemd-detect-virt",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
        virt = stdout.decode().strip()
        if virt and virt != "none":
            checks["systemd_detect_virt"] = virt
    except (FileNotFoundError, asyncio.TimeoutError):
        pass
    
    is_vm = bool(checks)
    vm_type = checks.get("systemd_detect_virt") or checks.get("dmi_product", "unknown")
    
    return {
        "is_vm": str(is_vm).lower(),
        "vm_type": vm_type,
        "confidence": "high" if len(checks) >= 2 else "low" if checks else "none",
    }
```

### 2.6 — `__main__.py` (PLAN Section 7)

Create `python -m sidewinder` entry point:

```python
"""Allow running as: python -m sidewinder"""
from sidewinder.sidewinder import main

if __name__ == "__main__":
    main()
```

### 2.7 — `cli.py` (PLAN Section 7)

Create top-level CLI parser:

```python
"""Sidewinder CLI — top-level argument parser."""
from __future__ import annotations

import argparse
import sys

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sidewinder",
        description="Sidewinder — Native Linux WiFi Audit Tool",
    )
    parser.add_argument("--version", action="version", version="sidewinder 0.4.0")
    parser.add_argument("--dev", action="store_true", help="Enable dev mode")
    parser.add_argument("--reg-domain", type=str, default="", help="Regulatory domain (e.g., US, GB)")
    parser.add_argument("--adapter", type=str, default="", help="Force specific adapter")
    parser.add_argument("--config", type=str, default="", help="Path to config file")
    
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("scan", help="Scan WiFi networks")
    sub.add_parser("target", help="Select target")
    sub.add_parser("capture", help="Capture handshake")
    sub.add_parser("crack", help="Crack password")
    sub.add_parser("cleanup", help="Cleanup & restore")
    sub.add_parser("doctor", help="Check dependencies")
    sub.add_parser("help", help="Show help")
    
    return parser

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return create_parser().parse_args(argv)
```

---

## Phase 3: Missing Screens (PLAN Section 10)

### 3.1 — Wordlist Picker Screen

Create `WordlistPickerScreen`:
- Auto-discover `/usr/share/wordlists/` and `~/wordlists/`
- Show wordlists in DataTable with name, size, line count
- Manual path input option
- Tooltip: what wordlists are, when to use which
- Pass selected wordlist path to CrackProgressScreen

### 3.2 — Engine Picker Screen

Create `EnginePickerScreen`:
- Two options: aircrack-ng (CPU) vs hashcat (GPU)
- Auto-detect if hashcat is available
- Show estimated speed for each
- Tooltip: CPU vs GPU tradeoffs
- Pass selected engine to CrackProgressScreen

### 3.3 — Cleanup Screen

Create `CleanupScreen`:
- Show list of files to be deleted (from `/tmp/sidewinder_*`)
- Show services that were killed
- Checkbox per file/service
- Confirm button
- Execute full cleanup

### 3.4 — Service Check Screen

Create `ServiceCheckScreen`:
- Show detected services (NM, wpa_supplicant, dhclient)
- Show which are running/stopped
- Kill/restore buttons per service
- Status indicators

### 3.5 — Monitor Setup Screen

Create `MonitorSetupScreen`:
- Show adapter status before/after monitor mode
- Channel selection
- Power save toggle
- Verification status
- Rollback option

### 3.6 — Scan Options Screen

Create `ScanOptionsScreen`:
- Band selection (2.4GHz / 5GHz / Both)
- Channel list (or auto)
- Duration / timeout
- Hidden SSID inclusion

### 3.7 — AP Details Screen

Create `APDetailsScreen`:
- Full details for selected AP
- All beacons, data packets, vendor info
- WPS status, client list
- Signal history if available

---

## Phase 4: Wire Everything Together

### 4.1 — Wire Slash Commands

In `ui/app.py`, implement `action_command()` to actually route commands:

```python
async def action_command(self, cmd: str) -> None:
    """Route slash command to appropriate action."""
    if cmd == "/scan":
        self.push_screen(ScanScreen())
    elif cmd == "/target":
        self.push_screen(TargetSelectScreen())
    elif cmd == "/capture":
        # Need target first
        if self.session.selected_target:
            self.push_screen(CaptureMethodScreen(target=self.session.selected_target))
        else:
            self.push_screen(ScanScreen())
    elif cmd == "/crack":
        if self.session.handshake:
            self.push_screen(WordlistPickerScreen())
        else:
            self.notify("No handshake captured yet", severity="warning")
    elif cmd == "/cleanup":
        await self._do_cleanup()
    elif cmd == "/help":
        self.push_screen(HelpScreen())
    elif cmd == "/status":
        self._show_status()
    elif cmd == "/adapter":
        self.push_screen(AdapterScreen())
    elif cmd == "/quit":
        # Confirm then exit
        self.push_screen(ConfirmScreen("Exit Sidewinder?", self.exit))
```

### 4.2 — Wire UI → Backend (Fix CRITICAL Bugs)

The entire capture flow must work end-to-end:

1. **ScanScreen** → discovers adapters, runs `ScanEngine.scan()`, populates table
2. **TargetSelectScreen** → reads from `self.app.session.scan_results`
3. **CaptureMethodScreen** → receives `target=Network`, shows options
4. **CaptureProgressScreen** → receives `target`, `method`, `clients`; runs `capture_passive()` or `capture_deauth()`
5. **CrackProgressScreen** → receives `handshake_path`; runs `crack_aircrack()` or `crack_hashcat()`
6. **ResultScreen** → receives `password`, `ssid`, `bssid`, `method`, `keys_tested`

### 4.3 — Wire Scan to Backend

In `ScanScreen.on_mount()`:
```python
async def _run_scan(self) -> None:
    adapter = self.app._adapter_manager.get_best_for_operation("scan")
    if not adapter:
        self.app.show_error(**ERROR_DB["ADAPTER_NOT_FOUND"].to_dict())
        return
    
    engine = ScanEngine(adapter.iface)
    self._scan_engine = engine
    
    try:
        async for network in engine.scan():
            self.app.session.scan_results.append(network)
            self.add_network(network)
    except asyncio.CancelledError:
        pass  # Normal stop
    except SidewinderError as e:
        self.app.show_error(**e.to_dict())
    finally:
        await engine.stop_and_wait()
```

### 4.4 — Wire Capture to Backend

In `CaptureProgressScreen.on_mount()`:
```python
async def _run_capture(self) -> None:
    target = self._target  # Set in __init__
    method = self._method
    
    # Set channel
    await set_channel(self._monitor_iface, target.channel)
    
    output_prefix = f"/tmp/sidewinder_{target.bssid.replace(':', '')}"
    
    try:
        if method == "passive":
            result = await capture_passive(
                self._monitor_iface,
                target.bssid,
                target.channel,
                timeout=self.app.config.eapol_timeout,
                output_prefix=output_prefix,
                on_progress=self._on_eapol_progress,
            )
        elif method == "deauth":
            selected = self._selected_clients  # From __init__
            result = await capture_deauth(
                self._monitor_iface,
                self._managed_iface,
                target.bssid,
                target.channel,
                clients=selected,
                count=self.app.config.deauth_count,
                bursts=self.app.config.deauth_bursts,
                cooldown=self.app.config.deauth_cooldown,
                timeout=self.app.config.eapol_timeout,
                output_prefix=output_prefix,
                on_progress=self._on_eapol_progress,
            )
        
        self.app.session.handshake = result
        self.app.session.captures.append(f"{output_prefix}.cap")
        
        if result.status in ("full", "partial"):
            self.app.push_screen(CrackProgressScreen(handshake_path=f"{output_prefix}.cap"))
        else:
            self.app.show_error(**ERROR_DB["NO_HANDSHAKE"].to_dict())
    
    except asyncio.CancelledError:
        pass
    except SidewinderError as e:
        self.app.show_error(**e.to_dict())
```

### 4.5 — Wire Crack to Backend

In `CrackProgressScreen.on_mount()`:
```python
async def _run_crack(self) -> None:
    try:
        if self._engine == "aircrack":
            async for progress in crack_aircrack(
                self._handshake_path,
                self._wordlist,
                threads=self.app.config.aircrack_threads,
            ):
                self.update_progress(
                    tested=progress.keys_tested,
                    total=progress.keys_total,
                    speed=progress.speed,
                    current=progress.current_key,
                    eta=progress.eta,
                )
                if progress.found:
                    self.app.session.cracked_passwords.append(CrackResult(
                        found=True,
                        password=progress.password,
                        method="aircrack",
                        wordlist=self._wordlist,
                        keys_tested=progress.keys_tested,
                    ))
                    self.app.push_screen(ResultScreen(
                        password=progress.password,
                        ssid=self.app.session.selected_target.essid,
                        bssid=self.app.session.selected_target.bssid,
                        method="aircrack",
                        keys_tested=progress.keys_tested,
                    ))
                    return
        
        elif self._engine == "hashcat":
            # Similar flow with crack_hashcat()
            pass
        
        # No result
        self.app.show_error(**ERROR_DB["CRACK_NO_RESULT"].to_dict())
    
    except asyncio.CancelledError:
        pass
    except SidewinderError as e:
        self.app.show_error(**e.to_dict())
```

---

## Phase 5: Recommendation Engine (PLAN Section 19)

### 5.1 — Recommendation Dataclass

```python
@dataclass
class Recommendation:
    """A suggestion from Sidewinder. User always decides."""
    
    title: str                    # "Easiest target: HomeNetwork"
    message: str                  # "Signal: -47dBm, 3 active clients"
    reason: str                   # "Strong signal, WPA2, has clients"
    confidence: float             # 0.0 - 1.0
    alternatives: list[str]       # Other options
    auto_execute: bool = False    # ALWAYS False
    require_acknowledgment: bool = False
    options: list[str] | None = None
    details: dict | None = None

@dataclass
class MethodRecommendation:
    """Suggested capture method."""
    recommended: str              # "passive", "deauth", "pmkid"
    confidence: float
    reason: str
    alternatives: list[str]
    auto_execute: bool = False

@dataclass
class AnalysisReport:
    """Scan analysis with ranked targets."""
    total_aps: int
    recommendations: list[Recommendation]
    warnings: list[Warning]
```

### 5.2 — IntelligenceEngine

```python
class IntelligenceEngine:
    """Analyzes scan results and recommends targets/methods. NEVER auto-executes."""
    
    def rank_targets(self, networks: list[Network]) -> list[tuple[Network, float]]:
        """Rank targets by attackability score.
        
        Score factors: signal strength, client count, encryption type, WPS status.
        Returns list of (network, score) sorted by score descending.
        """
        scored = []
        for net in networks:
            score = 0.0
            # Signal: -30 = 1.0, -90 = 0.0
            score += max(0, min(1, (net.signal + 90) / 60)) * 0.3
            # Clients: more = easier
            score += min(1, net.clients / 5) * 0.3
            # Encryption: WPA2-CCMP = easiest
            if "WPA2" in net.privacy:
                score += 0.2
            elif "WPA" in net.privacy:
                score += 0.15
            # WPS: bonus
            if net.wps:
                score += 0.1
            # Channel: 2.4GHz = more compatible
            if net.channel <= 14:
                score += 0.1
            scored.append((net, score))
        
        return sorted(scored, key=lambda x: x[1], reverse=True)
    
    def suggest_method(self, target: Network, clients: list[Client]) -> MethodRecommendation:
        """Suggest best capture method. User decides."""
        target_clients = [c for c in clients if c.bssid == target.bssid]
        
        if target_clients and target.signal > -60:
            return MethodRecommendation(
                recommended="deauth",
                confidence=0.85,
                reason=f"Active clients ({len(target_clients)}), strong signal ({target.signal}dBm)",
                alternatives=["passive"],
            )
        elif not target_clients:
            return MethodRecommendation(
                recommended="passive",
                confidence=0.5,
                reason="No clients — passive capture only (PMKID deferred to Phase 2)",
                alternatives=[],
            )
        else:
            return MethodRecommendation(
                recommended="passive",
                confidence=0.3,
                reason=f"Weak signal ({target.signal}dBm) — passive most reliable",
                alternatives=["deauth"],
            )
    
    def estimate_success(self, target: Network, method: str, clients: list[Client]) -> float:
        """Estimate success probability. Informational only."""
        factors = []
        # Signal factor
        factors.append(max(0, min(1, (target.signal + 90) / 60)))
        # Client factor
        target_clients = [c for c in clients if c.bssid == target.bssid]
        factors.append(min(1, len(target_clients) / 3))
        # Method fit
        if method == "deauth" and target_clients:
            factors.append(0.9)
        elif method == "passive":
            factors.append(0.5)
        else:
            factors.append(0.3)
        return sum(factors) / len(factors)
```

---

## Phase 6: Tooltip Database (PLAN Section 14.3)

Create `core/tooltips.py`:

```python
"""Tooltip database — structured help for every option and flag."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Tooltip:
    """Structured tooltip with full context."""
    
    name: str
    description: str
    when_to_use: str
    risk_level: str              # "safe", "caution", "dangerous"
    risk_detail: str
    example: str = ""
    requires: list[str] = field(default_factory=list)
    compatible_with: list[str] = field(default_factory=list)
    flags: dict[str, str] = field(default_factory=dict)

TOOLTIPS: dict[str, Tooltip] = {
    "capture_passive": Tooltip(
        name="Passive Capture",
        description="Listen for handshake without sending any packets",
        when_to_use="When you want to be stealthy or the AP has many active clients",
        risk_level="safe",
        risk_detail="No packets sent. Pure listening. Undetectable.",
        example="Listens on target channel. Captures EAPOL frames when clients naturally reconnect.",
        requires=["monitor_mode"],
        compatible_with=["wpa", "wpa2", "wpa3"],
    ),
    "capture_deauth": Tooltip(
        name="Deauth + Capture",
        description="Send deauth frames to kick clients, forcing a new handshake",
        when_to_use="When you need a handshake quickly and don't mind being detected",
        risk_level="caution",
        risk_detail="Sends deauth packets. Clients disconnect briefly. May trigger IDS.",
        example="Sends 10 deauth frames × 3 bursts. Clients reconnect within 5-10 seconds.",
        requires=["monitor_mode", "injection_capable"],
        compatible_with=["wpa", "wpa2"],
        flags={
            "--deauth-count": "Number of frames per burst (default: 10)",
            "--deauth-bursts": "Number of bursts (default: 3)",
            "--deauth-cooldown": "Seconds between bursts (default: 10)",
        },
    ),
    "scan_band": Tooltip(
        name="Scan Band",
        description="Which frequency band to scan",
        when_to_use="2.4GHz = longer range, slower speed. 5GHz = shorter range, faster speed.",
        risk_level="safe",
        risk_detail="No risk. Just determines which frequencies to listen on.",
        example="2.4GHz = channels 1-13. 5GHz = channels 36-165.",
        requires=["monitor_mode"],
    ),
    "crack_aircrack": Tooltip(
        name="aircrack-ng (CPU)",
        description="CPU-based WPA key cracking. Slower but works everywhere.",
        when_to_use="When you don't have a GPU or hashcat isn't installed.",
        risk_level="safe",
        risk_detail="No risk. Just uses CPU cycles.",
        example="Tests ~10,000 keys/sec on modern CPU. 14M keys = ~23 minutes.",
        compatible_with=["wpa", "wpa2"],
        flags={"--threads": "Number of CPU threads (default: auto)"},
    ),
    "crack_hashcat": Tooltip(
        name="hashcat (GPU)",
        description="GPU-based WPA key cracking. Much faster but requires GPU.",
        when_to_use="When you have a compatible GPU (NVIDIA/AMD).",
        risk_level="safe",
        risk_detail="No risk. Uses GPU compute units.",
        example="Tests ~100,000 keys/sec on GTX 1080. 14M keys = ~2 minutes.",
        requires=["hashcat", "compatible_gpu"],
        compatible_with=["wpa", "wpa2"],
        flags={
            "--gpu-platform": "GPU platform ID (default: auto-detect)",
            "--gpu-device": "GPU device ID (default: 0)",
        },
    ),
    "wordlist": Tooltip(
        name="Wordlist",
        description="File containing potential passwords to test",
        when_to_use="Use rockyou.txt for general testing. Use targeted lists for specific APs.",
        risk_level="safe",
        risk_detail="No risk. Just reads a file.",
        example="rockyou.txt = 14M common passwords. Custom = your target's likely passwords.",
        flags={
            "--wordlist": "Path to wordlist file",
            "--rules": "Apply hashcat rules (e.g., best64.rule)",
        },
    ),
    "deauth_count": Tooltip(
        name="Deauth Frame Count",
        description="Number of deauthentication frames to send per burst",
        when_to_use="Higher count = more reliable but more detectable",
        risk_level="caution",
        risk_detail="More frames = more chance of success, but more noise on the air",
        example="10 frames is usually enough. Use 5 for stealth, 20 for reliability.",
        requires=["monitor_mode", "injection_capable"],
        flags={"--deauth-count": "Number of frames (default: 10, range: 1-100)"},
    ),
    "deauth_rate": Tooltip(
        name="Deauth Rate",
        description="Frames per second during deauth burst",
        when_to_use="Higher rate = faster but may overwhelm adapter",
        risk_level="caution",
        risk_detail="RT5370 limited to ~300-400/sec. RTL8821AU can do ~1000/sec.",
        example="10 fps is safe. 50 fps is aggressive. 100 fps may drop packets.",
        requires=["monitor_mode", "injection_capable"],
        flags={"--deauth-rate": "Frames per second (default: 10)"},
    ),
}
```

---

## Phase 7: Error Code Database Completion (PLAN Section 13)

Expand `core/errors.py` to include all error codes from PLAN.md:

| Code | Title | Severity | Category |
|------|-------|----------|----------|
| E001 | Adapter Disconnected | CRITICAL | HARDWARE |
| E002 | Monitor Mode Failed | ERROR | HARDWARE |
| E003 | Weak Signal | WARNING | HARDWARE |
| E004 | Wrong Driver | ERROR | HARDWARE |
| E005 | MT7902 No Injection | ERROR | HARDWARE |
| E006 | Rfkill Blocked | ERROR | HARDWARE |
| E010 | airodump-ng Failed | ERROR | PROCESS |
| E011 | aireplay-ng Failed | ERROR | PROCESS |
| E012 | airodump-ng Stuck | ERROR | PROCESS |
| E013 | Subprocess Timeout | ERROR | PROCESS |
| E014 | Process Killed | WARNING | PROCESS |
| E020 | No Handshake Captured | WARNING | NETWORK |
| E021 | MAC Randomization | WARNING | NETWORK |
| E022 | Weak Encryption | WARNING | NETWORK |
| E023 | Hidden SSID | INFO | NETWORK |
| E030 | Root Required | CRITICAL | PERMISSION |
| E031 | Insufficient Permissions | ERROR | PERMISSION |
| E040 | Disk Full | ERROR | RESOURCE |
| E041 | Out of Memory | ERROR | RESOURCE |
| E042 | CPU Overload | WARNING | RESOURCE |
| E050 | Invalid Wordlist | ERROR | USER |
| E051 | Password Not Found | WARNING | USER |
| E052 | User Cancelled | INFO | USER |
| E053 | Session Corrupted | ERROR | USER |

Add these to `ERROR_DB` with proper `code` field matching PLAN.md format.

---

## Phase 8: Test Coverage (BUG-025)

Write unit tests for all untested modules:

### `tests/test_scanner.py`
- Test `AirodumpParser` state machine with sample CSV data
- Test `ScanEngine` initialization
- Test network/client parsing

### `tests/test_cleanup.py`
- Test `CleanupManager` initialization
- Test file pattern matching
- Test signal handler installation (mock)

### `tests/test_adapter_all.py`
- Test `RT5370Adapter` initialization (mock subprocess)
- Test `RTL8821AUAdapter` initialization (mock subprocess)
- Test `MT7902Adapter` initialization (mock subprocess)
- Test `AdapterManager.discover()`
- Test `FailoverManager.execute_with_failover()`

### `tests/test_monitor.py`
- Test `enter_monitor_mode()` with mocked subprocess
- Test `exit_monitor_mode()` with mocked subprocess
- Test `MonitorWatcher` mode detection

### `tests/test_services.py`
- Test `ServiceManager.kill_conflicting()` with mocked systemctl
- Test `ServiceManager.restore()` with mocked systemctl

### `tests/test_deauth.py`
- Test `run_deauth()` with mocked aireplay-ng
- Test rate limiting logic
- Test burst/cooldown timing

### `tests/test_config.py`
- Test `Config.load()` with sample TOML
- Test default values
- Test save/load roundtrip

### `tests/test_tooltips.py`
- Test all tooltips have required fields
- Test `TOOLTIPS` dict completeness

### `tests/test_intelligence.py`
- Test `IntelligenceEngine.rank_targets()`
- Test `suggest_method()` for various scenarios
- Test `estimate_success()` returns valid range

All tests should:
- Use `pytest` and `pytest-asyncio`
- Mock subprocess calls with `unittest.mock.patch` or `pytest-mock`
- Mark Linux-only tests with `@pytest.mark.skipif(sys.platform != "linux")`
- Have clear docstrings explaining what each test verifies
- Achieve >80% coverage on each module

---

## Implementation Order

Execute in this exact order:

1. **Fix all 31 bugs** (Phase 1) — this is the foundation
2. **Create `core/rfkill.py`** (Phase 2.1) — needed by adapter detection
3. **Create `core/config.py`** (Phase 2.2) — needed by all modules
4. **Create `core/logger.py`** (Phase 2.3) — needed by session management
5. **Create `core/attack.py`** (Phase 2.4) — needed by deauth flow
6. **Create `core/vm.py`** (Phase 2.5) — informational, low priority
7. **Create `__main__.py`** (Phase 2.6) — 1 file, do it
8. **Create `cli.py`** (Phase 2.7) — needed for entry point
9. **Create missing screens** (Phase 3) — one at a time
10. **Wire everything together** (Phase 4) — the critical integration
11. **Build recommendation engine** (Phase 5) — intelligence layer
12. **Create tooltip database** (Phase 6) — structured help
13. **Complete error codes** (Phase 7) — expand ERROR_DB
14. **Write tests** (Phase 8) — coverage for all modules

---

## Verification Checklist

After completing all phases, verify:

- [ ] `python -m sidewinder` works
- [ ] `sidewinder --version` works
- [ ] All 31 bugs fixed (re-check Bug.md)
- [ ] All screens navigable (16 screens)
- [ ] All slash commands functional
- [ ] Scan → Select → Capture → Crack → Result flow works end-to-end
- [ ] Cleanup restores all services
- [ ] Session save/resume works
- [ ] All error codes have proper What/Why/HowToFix
- [ ] All tooltips have required fields
- [ ] No resource leaks (check file handles, subprocesses, timers)
- [ ] No sync subprocess calls in async context
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Coverage >80% on core modules: `pytest --cov=sidewinder`
- [ ] No type errors: `pyright sidewinder/`
- [ ] No lint errors: `ruff check sidewinder/`

---

## Critical Reminders

1. **NEVER AUTO-EXECUTE** — All intelligence is RECOMMENDATION ONLY. User always decides.
2. **NEVER SWALLOW ERRORS** — Always notify user via SidewinderError with What/Why/HowToFix.
3. **NEVER BLOCK THE EVENT LOOP** — All subprocess calls must be async via SubprocessManager.
4. **ALWAYS CLOSE RESOURCES** — Use `with` blocks, `finally` clauses, context managers.
5. **ALWAYS CANCEL TASKS ON EXIT** — Track every `create_task()`, cancel in `on_unmount()`.
6. **ALWAYS SET TIMEOUTS** — Every subprocess, every network call, every poll loop.
7. **ALWAYS USE PROCESS GROUPS** — `os.setsid()` for attack processes so we can kill the tree.
8. **PREFER EXISTING CODE** — Reuse SubprocessManager, SidewinderError, Session patterns.
9. **FOLLOW EXISTING STYLE** — Match the code style of adjacent files.
10. **TEST ON LINUX** — All sysfs/iw/ip calls are Linux-only. Mock in tests.
