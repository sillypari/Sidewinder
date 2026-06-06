# Sidewinder — Native Linux WiFi Audit Tool

**Terminal-native, opencode-style interactive CLI for 802.11 penetration testing**

---

## 1. Why Sidewinder Exists (The Wcrack Post-Mortem)

### 1.1 Wcrack's Architectural Mistakes

Wcrack was built as a **full-stack web platform** (FastAPI + React + WebSocket) with 14 DB tables, 9 API routers, EventBus, RadioLeaseManager, ManagedProcess, AdapterWatchdog, captive portal server, and 10 frontend pages — all for a single-operator local tool.

**What went wrong:**

| Layer | Problem | Impact |
|-------|---------|--------|
| **Frontend** | React 19 + Vite + Tailwind + shadcn/ui + Zustand | 4,000+ LOC, hydration bugs, WebSocket reconnection storms, "F5 Problem" (state loss on refresh) |
| **Backend** | FastAPI + async SQLAlchemy + Alembic + 14 models | Over-engineered for single-user; migrations, sessions, connection pooling add zero RF value |
| **IPC** | HTTP REST + WebSocket + EventBus (ring buffer) | 3 serialization hops for one airodump line: subprocess → stdout → EventBus → WS → React store → render |
| **Process Mgmt** | ManagedProcess with TaskGroup, drain tasks, killpg | 160 lines just to not leak zombies; still had pipe deadlocks |
| **Hardware** | AdapterWatchdog polls `iw dev` every 2s + pyudev + airmon-ng cache | Duplicates kernel state; race conditions on mode switches |
| **Deployment** | systemd + sudoers + udev + regulatory service | 4 config files, requires root, breaks on Ubuntu version drift |

**Root cause:** Wcrack treated a **CLI problem** as a **web app problem**. The browser added zero value for a single operator on localhost.

### 1.2 The airmon-ng Revelation

`airmon-ng` is a **1,439-line bash wrapper** that does nothing magic:

```
┌─────────────────────────────────────────────────────────────┐
│  airmon-ng start wlan0                                      │
├─────────────────────────────────────────────────────────────┤
│  1. Read PHY from /sys/class/net/wlan0/phy80211/name       │
│  2. iw phy phy0 interface add wlan0mon type monitor         │
│  3. ip link set wlan0mon up                                 │
│  4. iw dev wlan0mon set channel <N>                         │
│  5. iw dev wlan0mon set txpower fixed 3000                  │
│  6. iw wlan0 del (if not ELITE mode)                        │
│  7. pkill NetworkManager, wpa_supplicant, dhclient, avahi  │
└─────────────────────────────────────────────────────────────┘
```

**Every single call is a netlink/ioctl syscall.** Python can do this natively via:
- `pyroute2` / `nl80211` (kernel netlink)
- `asyncio.subprocess` + `iw` / `ip` (userspace, zero parsing overhead)
- Direct `/sys` reads (driver, chipset, rx/tx stats, mode, channel)

**No wrapper needed. No bash. No airmon-ng.**

### 1.3 Sidewinder's Design Philosophy

> **"Native Linux, terminal-first, zero bloat."**

| Principle | Wcrack | Sidewinder |
|-----------|--------|------------|
| Interface | Web GUI (React) | Terminal TUI (Textual/rich) |
| Architecture | Client-server (HTTP/WS) | Single process, direct syscalls |
| State | SQLite + EventBus + Zustand | In-memory + optional SQLite log |
| Process mgmt | ManagedProcess (160 lines) | asyncio + os.killpg (20 lines) |
| Hardware | AdapterWatchdog (polling) | Direct `iw`/`ip` + nl80211 |
| Deployment | systemd + sudoers + udev | Single binary/script, `sudo ./sidewinder` |
| Config | 14 DB tables, env vars, TOML | CLI flags + `~/.config/sidewinder/` |

---

## 2. airmon-ng Line-by-Line Deep Dive

### 2.1 What airmon-ng Actually Is

Source: `aircrack-ng/scripts/airmon-ng` — 1,439 lines, POSIX `/bin/sh` script.
It is **NOT** a "tool." It is a **bash orchestration layer** over `iw`, `ip`, `ethtool`, `rfkill`, `lsusb`, `lspci`, `modinfo`, and `kill`.

### 2.2 Initialization Block (Lines 1–100)

```bash
DEBUG="0"; VERBOSE="0"; ELITE="0"; USERID=""; IFACE=""
MAC80211=0
```

**Flags:**
- `--elite` → keeps the original managed-mode interface alive alongside monitor (don't `iw <iface> del`)
- `--verbose` → shows driver source (K/C/V/S), firmware version, chipset extended info
- `--debug` → prints every decision path

**Channel default:** `CH=10` if not specified.

**Root check:** Runs `id -u`. Exits if not 0.

### 2.3 Dependency Check Block (Lines 100–180)

Checks existence of: `uname`, `ip`/`ifconfig`, `iw`, `ethtool`, `lsusb`, `lspci`, `modprobe`, `modinfo`, `rfkill`, `awk`, `grep`.

**Why each matters:**

| Binary | Purpose in airmon-ng |
|--------|---------------------|
| `iw` | Core — creates/deletes VIFs, sets channel, reads PHY info |
| `ip` | Brings interfaces up/down (`ip link set dev <iface> up/down`) |
| `ethtool` | Reads driver name, bus info, firmware version from NIC |
| `lsusb` | USB chipset detection (`lsusb -d <VID:PID>`) |
| `lspci` | PCI chipset detection |
| `rfkill` | Checks soft/hard radio kill blocks |
| `modinfo` | Reads driver module path to determine source (kernel/vendor/staging) |
| `modprobe` | Loads compat module for driver source detection |

### 2.4 `getPhy()` — PHY Discovery (Lines ~400–420)

```bash
getPhy() {
    if [ -r /sys/class/net/$1/phy80211/name ]; then
        PHYDEV="$(cat /sys/class/net/$1/phy80211/name)"
    fi
}
```

**Reads:** `/sys/class/net/<iface>/phy80211/name` → returns `phy0`, `phy1`, etc.

**This is the single most important file.** It maps interface → physical radio. Without it, `iw phy <PHY> interface add` cannot create a VIF.

### 2.5 `getDriver()` — Driver Detection (Lines ~430–500)

```bash
getDriver() {
    if [ -f /sys/class/net/$1/device/uevent ]; then
        DRIVER="$(awk -F'=' '$1 == "DRIVER" {print $2}' /sys/class/net/$1/device/uevent)"
    fi
```

**Primary path:** `/sys/class/net/<iface>/device/uevent` → `DRIVER=` line.

**USB fallback:** If `DRIVER=usb`, digs into `/sys/class/net/<iface>/device/<BUS_ADDR>/uevent` for the real driver (rt2870, rt3070, etc.).

**Normalization:** Renames `rtl8187L` → `r8187l`, `rt2870` → `rt2870sta`, etc.

### 2.6 `getChipset()` — Chipset Detection (Lines ~550–650)

**USB:** `lsusb -d <VID:PID>` → strips "Network Connection"/"Wireless Adapter" → chipset name.

**PCI:** `lspci -d <VID:PID>` → strips "Wireless LAN Controller" → chipset name.

**SDIO:** Hardcoded VID:PID map for Broadcom chips (4330, 4334, 43455, etc.).

**Fallback:** `/sys/class/net/<iface>/device/product` or `"non-mac80211 device? (report this!)"`.

### 2.7 `getStack()` — Wireless Stack Detection (Lines ~500–520)

```bash
getStack() {
    if [ -d /sys/class/net/$1/phy80211/ ]; then
        MAC80211="1"; STACK="mac80211"
    else
        MAC80211="0"; STACK="ieee80211"
    fi
    if [ -e /proc/sys/dev/$1/fftxqmin ]; then
        MAC80211="0"; STACK="net80211"
    fi
}
```

**Three stacks:**
- `mac80211` — modern kernel softMAC (99% of adapters)
- `ieee80211` — old hardMAC drivers
- `net80211` — FreeBSD-style

**Only mac80211 gets monitor mode via `iw`.** Others are legacy or unsupported.

### 2.8 `scanProcesses()` — Conflicting Process Killer (Lines ~650–750)

```bash
PROCESSES="wpa_action\|wpa_supplicant\|wpa_cli\|dhclient\|ifplugd\|dhcdbd\|dhcpcd\|udhcpc\|NetworkManager\|knetworkmanager\|avahi-autoipd\|avahi-daemon\|wlassistant\|wifibox"
```

**On `check`:** Lists matching PIDs.

**On `check kill`:**
1. `service network-manager stop` (via systemctl/service)
2. `service NetworkManager stop`
3. `service avahi-daemon stop`
4. Then `kill -9` on every matching PID

**Why kill:** These processes fight over the interface — NM tries to manage it, wpa_supplicant tries to associate, dhclient tries to DHCP. They all break monitor mode.

### 2.9 `startMac80211Iface()` — The Core (Lines ~220–330)

This is the **heart of airmon-ng**. Step by step:

**Step 1 — rfkill check:**
```bash
rfkill_check ${PHYDEV}
```
Reads `/sys/class/rfkill/rfkillN/soft` and `/hard`. If blocked, offers `rfkill unblock`.

**Step 2 — Check for existing monitor VIF:**
```bash
for i in $(ls /sys/class/ieee80211/${PHYDEV}/device/net/); do
    if [ "$(cat .../type)" = "803" ]; then  # 803 = monitor mode
        # Already in monitor mode, just set channel
        setChannelMac80211 ${i}
        exit
    fi
done
```

**Step 3 — Create monitor VIF:**
```bash
setLink ${1} down                               # ip link set wlan0 down
iw phy ${PHYDEV} interface add ${1}mon type monitor  # create wlan0mon
sleep 1                                          # wait for udev
```

**Step 4 — Verify:**
```bash
if [ "$(cat .../type)" = "803" ]; then  # 803 = ARPHRD_IEEE80211_RADIOTAP
    setChannelMac80211 ${1}mon
fi
```

**Step 5 — Delete original (non-ELITE):**
```bash
if [ "${ELITE}" = "0" ]; then
    iw ${1} del  # remove wlan0, keep wlan0mon only
fi
```

### 2.10 `setChannelMac80211()` — Channel Setting (Lines ~330–380)

```bash
if [ ${CH} -lt 1000 ]; then
    # Validate against hardware-supported channels
    channel_list="$(iw phy ${PHYDEV} info | grep -oP '\[\K[^\]]+')"
    IW_ERROR="$(iw dev ${1} set channel ${CH})"
else
    # Frequency mode (for >1000 values like 2422 MHz)
    IW_ERROR="$(iw dev ${1} set freq "${CH}")"
fi
```

**Channel validation:** Reads supported channel list from `iw phy <PHY> info`, checks if requested channel exists.

**Error handling:**
- Error `-16` (EBUSY) → interface was reset to station mode by NM → abort
- Error `-22` (EINVAL) → channel outside regulatory domain

### 2.11 `stopMac80211Iface()` — Monitor Mode Teardown (Lines ~380–450)

```bash
# 1. Verify interface is actually monitor (type 803)
# 2. Recreate station VIF if needed
iw phy ${PHYDEV} interface add ${1%mon} type station
# 3. Delete monitor VIF
setLink ${1} down
iw dev "${1}" del
```

**Key safety check:** Refuses to stop a non-monitor interface (prevents destroying your managed-mode NIC by accident).

### 2.12 `findFreeInterface()` — Name Collision Avoidance (Lines ~150–200)

```bash
for i in $(seq 0 100); do
    if [ ! -e /sys/class/net/wlan${i} ]; then
        if [ ! -e /sys/class/net/wlan${i}mon ]; then
            iw phy ${PHYDEV} interface add wlan${i}${target_suffix} type ${target_mode}
            break
        fi
    fi
done
```

Loops `wlan0` → `wlan99` to find a free name. Handles udev renaming.

### 2.13 `handleLostPhys()` — PHY Recovery (Lines ~130–150)

Scans `/sys/class/ieee80211/` for PHYs with no interfaces. Offers to create one.

### 2.14 `rfkill_check()` / `rfkill_unblock()` — Radio Kill Switch (Lines ~200–230)

```bash
rfkill_check() {
    index="$(rfkill list | grep ${1} | awk -F: '{print $1}')"
    soft=$(printf "${rfkill_status}" | grep -i soft | awk '{print $3}')
    hard=$(printf "${rfkill_status}" | grep -i hard | awk '{print $3}')
}
```

Returns: `0`=unblocked, `1`=soft blocked, `2`=hard blocked, `3`=both.

---

## 3. What Sidewinder Replaces (Native Equivalents)

| airmon-ng Function | Lines | Native Equivalent |
|-------------------|-------|-------------------|
| Read PHY name | `getPhy()` | `cat /sys/class/net/<iface>/phy80211/name` |
| Detect driver | `getDriver()` | `cat /sys/class/net/<iface>/device/uevent` |
| Detect chipset | `getChipset()` | `lsusb -d` / `lspci -d` / sysfs modalias |
| Detect stack | `getStack()` | `ls /sys/class/net/<iface>/phy80211/` |
| Check rfkill | `rfkill_check()` | `cat /sys/class/rfkill/rfkill*/{soft,hard}` |
| Unblock rfkill | `rfkill_unblock()` | `rfkill unblock <N>` or write sysfs |
| Create monitor VIF | `startMac80211Iface()` | `iw phy <phy> interface add <name> type monitor` |
| Delete monitor VIF | `stopMac80211Iface()` | `iw dev <name> del` |
| Bring interface up | `setLink()` | `ip link set dev <iface> up` |
| Set channel | `setChannelMac80211()` | `iw dev <iface> set channel <N>` |
| Set frequency | `setChannelMac80211()` | `iw dev <iface> set freq <MHz>` |
| Kill conflicting procs | `scanProcesses()` | `pkill -f "NetworkManager\|wpa_supplicant\|dhclient"` |
| Stop services | `scanProcesses()` | `systemctl stop NetworkManager wpa_supplicant` |
| Find free interface | `findFreeInterface()` | Loop `wlan0`..`wlan99` + check sysfs |
| Lost phys recovery | `handleLostPhys()` | Iterate `/sys/class/ieee80211/` |
| VM detection | `checkvm()` | `dmidecode` / `lsmod` / `dmesg` |

---

## 4. Sidewinder's Complete Pipeline (Highly Detailed)

### 4.1 Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    SIDEWINDER ATTACK PIPELINE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PHASE 0: HARDWARE DISCOVERY                                   │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  iw dev → list interfaces                            │      │
│  │  sysfs → PHY, driver, chipset, mode, MAC, channel    │      │
│  │  rfkill → soft/hard block status                      │      │
│  │  lsusb/lspci → USB/PCI bus detection                 │      │
│  └───────────────────────────────────────────────────────┘      │
│                         │                                       │
│                         ▼                                       │
│  PHASE 1: SERVICE MANAGEMENT                                   │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  scanProcesses() → find NM, wpa_supplicant, dhclient │      │
│  │  kill -9 → terminate conflicting processes            │      │
│  │  systemctl stop → NM, wpa_supplicant, avahi          │      │
│  └───────────────────────────────────────────────────────┘      │
│                         │                                       │
│                         ▼                                       │
│  PHASE 2: MONITOR MODE                                        │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  ip link set <iface> down                             │      │
│  │  iw phy <phy> interface add <mon> type monitor        │      │
│  │  ip link set <mon> up                                 │      │
│  │  iw dev <mon> set channel <N>                         │      │
│  │  iw dev <mon> set txpower fixed 3000                  │      │
│  └───────────────────────────────────────────────────────┘      │
│                         │                                       │
│                         ▼                                       │
│  PHASE 3: RECONNAISSANCE                                      │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  airodump-ng <mon> --write scan --output-format csv   │      │
│  │  Parse stdout in real-time (no CSV polling)           │      │
│  │  Publish: network.discovered, client.discovered       │      │
│  │  Filter: BSSID, SSID, channel, encryption, power      │      │
│  └───────────────────────────────────────────────────────┘      │
│                         │                                       │
│                         ▼                                       │
│  PHASE 4: TARGET SELECTION                                     │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  User selects target network from scan results        │      │
│  │  Lock channel to target's channel                     │      │
│  │  Validate: encryption type, signal strength, clients  │      │
│  └───────────────────────────────────────────────────────┘      │
│                         │                                       │
│                         ▼                                       │
│  PHASE 5: HANDSHAKE CAPTURE                                    │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  Option A: Passive capture                            │      │
│  │    airodump-ng <mon> --bssid <BSSID> --channel <CH>   │      │
│  │    Wait for 4-way EAPOL handshake (M1-M4)            │      │
│  │                                                       │      │
│  │  Option B: Active deauth + capture                    │      │
│  │    aireplay-ng --deauth 10 -a <BSSID> -c <client> <m>│      │
│  │    airodump-ng simultaneously capturing               │      │
│  │                                                       │      │
│  │  Option C: PMKID capture (clientless)                 │      │
│  │    hcxdumptool -i <mon> --filterlist=<BSSID>          │      │
│  │    hcxpcapngtool -o hash.22000 <capture>              │      │
│  │                                                       │      │
│  │  Validate: verify_handshake() checks EAPOL M1-M4     │      │
│  │  Save: SHA-256, path, EAPOL status, size             │      │
│  └───────────────────────────────────────────────────────┘      │
│                         │                                       │
│                         ▼                                       │
│  PHASE 6: CRACKING                                             │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  aircrack-ng -w <wordlist> -b <BSSID> <capture>      │      │
│  │  OR                                                   │      │
│  │  hashcat -m 22000 <hash.22000> -a 0 <wordlist>       │      │
│  │                                                       │      │
│  │  Track: progress %, keys/s, ETA, current passphrase  │      │
│  │  Save: potfile, cracked keys                          │      │
│  └───────────────────────────────────────────────────────┘      │
│                         │                                       │
│                         ▼                                       │
│  PHASE 7: CLEANUP                                              │
│  ┌───────────────────────────────────────────────────────┐      │
│  │  iw dev <mon> del                                     │      │
│  │  iw phy <phy> interface add <iface> type station      │      │
│  │  ip link set <iface> up                               │      │
│  │  systemctl start NetworkManager wpa_supplicant        │      │
│  └───────────────────────────────────────────────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Phase 0: Hardware Discovery (Detailed)

**Input:** System boots, USB adapters plugged in.

**Operations:**
```
1. Parse iw dev output
   → Extract: phy#, interface, ifindex, wdev, addr, type, channel

2. For each interface, read sysfs:
   /sys/class/net/<iface>/phy80211/name          → PHY name (phy0)
   /sys/class/net/<iface>/device/driver          → driver symlink (rt2800usb)
   /sys/class/net/<iface>/device/uevent          → DRIVER= line
   /sys/class/net/<iface>/device/modalias        → bus type (usb/pci/sdio)
   /sys/class/net/<iface>/device/idVendor        → USB VID (for chipset)
   /sys/class/net/<iface>/device/idProduct       → USB PID (for chipset)
   /sys/class/net/<iface>/statistics/rx_packets  → RX count
   /sys/class/net/<iface>/statistics/tx_packets  → TX count
   /sys/class/net/<iface>/operstate              → up/down
   /sys/class/net/<iface>/address                → MAC address

3. Read rfkill state:
   /sys/class/rfkill/rfkillN/soft                → software block (0/1)
   /sys/class/rfkill/rfkillN/hard                → hardware block (0/1)

4. Detect chipset name:
   USB: lsusb -d <VID>:<PID>
   PCI: lspci -d <VID>:<PID>
   Fallback: /sys/class/net/<iface>/device/product
```

**Output:** List of adapters with: `name, phy, mac, driver, chipset, mode, channel, rfkill, rx, tx`

**What Wcrack did wrong:** Polled `iw dev` every 2s in a loop + used airmon-ng cache (30s TTL) for chipset. Sidewinder reads sysfs directly on demand (zero polling).

### 4.3 Phase 1: Service Management (Detailed)

**Input:** User wants to start monitor mode.

**Problem:** NetworkManager, wpa_supplicant, dhclient, avahi-daemon all fight over the wireless interface. NM periodically scans. wpa_supplicant tries to associate. dhclient requests leases.

**Operations:**
```
1. scanProcesses()
   → ps -A -o comm= | grep -E "NetworkManager|wpa_supplicant|dhclient|avahi-daemon"

2. For each found process:
   if (process == "NetworkManager"):
       systemctl stop NetworkManager    # graceful stop
   elif (process == "wpa_supplicant"):
       kill -9 <PID>                    # force kill (NM may respawn it)
   elif (process == "dhclient"):
       kill -9 <PID>
   elif (process == "avahi-daemon"):
       systemctl stop avahi-daemon
```

**Why `kill -9` not `kill -15`:** NetworkManager respawns wpa_supplicant within milliseconds. SIGTERM gives it time to restart before you can act.

**Sidewinder enhancement:** Track which processes were killed → offer `restore` command to restart them.

### 4.4 Phase 2: Monitor Mode (Detailed)

**Input:** Clean interface, no conflicting processes.

**Step-by-step native implementation:**
```
1. ip link set dev wlan0 down
   → Sets IFF_UP=0 on the interface

2. iw phy phy0 interface add wlan0mon type monitor
   → Creates a new Virtual Interface (VIF) of type monitor
   → Kernel creates /sys/class/net/wlan0mon
   → udev may rename it (handle via sysfs scan)

3. ip link set dev wlan0mon up
   → Sets IFF_UP=0x1 on the monitor VIF

4. iw dev wlan0mon set channel 6
   → Sets the radio to listen on channel 6
   → Equivalent: iw dev wlan0mon set freq 2437

5. iw dev wlan0mon set txpower fixed 3000
   → Sets TX power to 30 dBm (1000 * dBm = milliwatts)
```

**Verification:**
```
iw dev wlan0mon info
→ Should show: type monitor, channel 6

cat /sys/class/net/wlan0mon/type
→ Should return: 803 (ARPHRD_IEEE80211_RADIOTAP)
```

**Bad driver fallback (rtl8821au etc.):**
```
ip link set dev wlan0 down
iw dev wlan0 set type monitor    # direct mode change, no VIF
ip link set dev wlan0 up
iw dev wlan0 set monitor otherbss
```

### 4.5 Phase 3: Reconnaissance (Detailed)

**Input:** Monitor mode interface active.

**Command:**
```
airodump-ng wlan0mon --write scan --output-format csv,pcap -a --wps
```

**Real-time stdout parsing:**
```
airodump-ng refreshes every ~1s with a screen redraw.
Format:
  CH  6 ][ Elapsed: 5 s ][ 2026-06-05 23:04:24
  BSSID              PWR  Beacons  #Data  Rate  MB  ENC  CIPHER  AUTH  ESSID
  AA:BB:CC:DD:EE:FF  -47  1234     567    54e   -   WPA2 CCMP   PSK  NASA
  ...
  BSSID              STATION            PWR    Rate   Lost  Frames  Probes
  AA:BB:CC:DD:EE:FF  11:22:33:44:55:66  -65    54e    0     123     NASA
```

**Parser state machine:**
```
IDLE → detect "CH" line → HEADER
HEADER → detect "BSSID PWR" → AP_HEADER
AP_HEADER → blank line → AP_DATA
AP_DATA → parse each line → network.discovered event
AP_DATA → detect "BSSID STATION" → CLIENT_HEADER
CLIENT_HEADER → blank line → CLIENT_DATA
CLIENT_DATA → parse each line → client.discovered event
```

**Filtering (built-in):**
- `--bssid <MAC>` → single target
- `--channel <N>` → single channel (locks radio)
- `--band a/b/g` → band filter
- `-a` → only show associated clients (no probe requests)
- `--wps` → show WPS status

### 4.6 Phase 4: Target Selection (Detailed)

**Input:** Scan results in memory.

**User flow:**
```
1. Display table of discovered networks:
   [#] BSSID              CH  ENC     PWR  CLIENTS  ESSID
   [1] AA:BB:CC:DD:EE:FF  6   WPA2    -47  3        NASA
   [2] 11:22:33:44:55:66  11  WPA2    -62  1        NASA+
   [3] 77:88:99:AA:BB:CC  1   OPEN    -71  0        Guest

2. User types: select 1

3. Lock channel:
   iw dev wlan0mon set channel 6

4. Display target details:
   BSSID: AA:BB:CC:DD:EE:FF
   SSID: NASA
   Channel: 6
   Encryption: WPA2 (CCMP/PSK)
   Signal: -47 dBm (Excellent)
   Clients: 3
   WPS: Disabled
```

**What Wcrack missed:** No channel lock confirmation. Scanner kept hopping during capture. Sidewinder explicitly locks and verifies.

### 4.7 Phase 5: Handshake Capture (Detailed)

**Three capture methods:**

**Method A — Passive Capture:**
```
airodump-ng wlan0mon --bssid AA:BB:CC:DD:EE:FF --channel 6 \
    --write /tmp/cap --output-format pcap

# Parser watches for EAPOL frames in airodump-ng output
# When 4-way handshake detected (M1-M4):
#   → Stop airodump-ng
#   → Save .cap file
#   → verify_handshake() checks EAPOL completeness
#   → SHA-256 hash computed
#   → Saved to captures/ directory
```

**Method B — Active Deauth + Capture:**
```
# Terminal 1: Capture
airodump-ng wlan0mon --bssid <BSSID> --channel 6 --write /tmp/cap

# Terminal 2: Deauth (triggers handshake)
aireplay-ng --deauth 10 -a <BSSID> -c <CLIENT> wlan0mon

# EAPOL frames appear in capture within seconds
```

**Method C — PMKID (Clientless):**
```
# No client needed — captures PMKID from AP directly
hcxdumptool -i wlan0mon \
    --filterlist=<BSSID> --filtermode=2 \
    --enable_status=1 \
    -o /tmp/pmkid.pcapng

# Convert to hashcat format
hcxpcapngtool -o /tmp/hash.22000 /tmp/pmkid.pcapng
```

**EAPOL Validation:**
```
verify_handshake(cap_file):
    1. Open PCAP with tshark/scapy
    2. Filter for EAPOL frames (ethertype 0x888e)
    3. Check M1, M2, M3, M4 presence
    4. Minimum: M1 + M2 = "Partial"
    5. Full: M1 + M2 + M3 + M4 = "Valid"
    6. Extract: ANonce, SNonce, MIC, GTK
```

### 4.8 Phase 6: Cracking (Detailed)

**aircrack-ng (CPU):**
```
aircrack-ng -w /usr/share/wordlists/rockyou.txt \
    -b AA:BB:CC:DD:EE:FF \
    /tmp/cap-01.cap

# Output shows:
# [00:03:45] 1234567 keys/s | ETA 00:15:30 | Current passphrase: password123
```

**hashcat (GPU):**
```
hashcat -m 22000 /tmp/hash.22000 -a 0 /usr/share/wordlists/rockyou.txt -d 1

# -m 22000 = WPA-PBKDF2-PMKID+EAPOL
# -a 0 = straight dictionary attack
# -d 1 = GPU device 1
```

**Progress tracking:**
```
Parse aircrack-ng stdout:
  keys/s: "1234567 keys/s"
  ETA: "00:15:30"
  progress: "2.3%" (if determinable)

Parse hashcat stdout:
  "Progress.....: 123456/1000000 (12.35%)"
  "Speed.#1.....: 123456 keys/s"
  "Time.Left....: 15 mins, 30 secs"
```

### 4.9 Phase 7: Cleanup (Detailed)

**Reverse of setup:**
```
1. Kill airodump-ng/aireplay-ng/hcxdumptool
   → os.killpg(pgid, SIGTERM) → wait → SIGKILL

2. Delete monitor VIF
   → iw dev wlan0mon del

3. Recreate managed VIF
   → iw phy phy0 interface add wlan0 type station
   → ip link set wlan0 up

4. Restart services
   → systemctl start NetworkManager
   → systemctl start wpa_supplicant

5. Verify connectivity
   → ip addr show wlan0
   → ping -c 3 8.8.8.8
```

**What Wcrack missed:** No automatic cleanup on Ctrl+C. Zombie processes left behind. Sidewinder registers signal handlers for graceful shutdown.

---

## 5. What's Missing From Your Basic Pipeline

You listed: `check cards → monitor/manage → check kill/restore → airodump → capture → crack`

**Missing pieces from Wcrack's hard-won lessons:**

| # | Missing | Why Critical |
|---|---------|-------------|
| 1 | **Channel lock verification** | Scanner hops channels during capture → you miss handshakes. Must lock and verify. |
| 2 | **EAPOL state machine** | Need to track M1-M4. Partial handshake (M1+M2) is usable for offline crack, M3+M4 adds nothing new. |
| 3 | **PCAP validation** | `verify_handshake()` — many captures are empty or have no EAPOL. Must verify before cracking. |
| 4 | **PMKID capture** | Clientless alternative. hcxdumptool captures PMKID from AP beacon. No deauth needed. |
| 5 | **Wordlist management** | Download, filter, deduplicate. RockYou is 14M lines. Custom wordlists matter. |
| 6 | **Crack progress tracking** | aircrack-ng and hashcat have different stdout formats. Parse both. |
| 7 | **SHA-256 integrity** | Compute hash at capture time, re-verify at crack time. Detect tampering. |
| 8 | **wpaclean stripping** | Clean captures of junk data. Reduces crack time by 50%+. |
| 9 | **Signal strength filtering** | -90 dBm captures are garbage. Filter by signal quality. |
| 10 | **Regulatory domain** | `iw reg set BO` unlocks all channels. Some adapters are country-locked. |
| 11 | **USB hotplug handling** | Adapter removed mid-attack → crash. Must handle gracefully. |
| 12 | **Ctrl+C cleanup** | Signal handlers for SIGINT/SIGTERM → reverse teardown → no zombies. |
| 13 | **TX power setting** | `iw dev <mon> set txpower fixed 3000` — increases range for capture. |
| 14 | **hcxpcapngtool conversion** | PMKID from hcxdumptool needs conversion to hashcat -m 22000 format. |

---

## 6. Sidewinder's Current Goal (MVP Scope)

### 6.1 MVP Definition

> **"Open terminal, run `sudo ./sidewinder`, get a scan, pick a target, capture handshake, crack it."**

No web UI. No database. No React. Just a terminal that does the job.

### 6.2 MVP Features (Ordered by Priority)

| # | Feature | Priority | Decision |
|---|---------|----------|----------|
| 1 | Hardware discovery (`iw dev` + sysfs) | P0 | INCLUDE |
| 2 | Monitor mode (native `iw`/`ip`) | P0 | INCLUDE |
| 3 | Kill/restore services | P0 | INCLUDE |
| 4 | Airodump-ng scan + real-time parsing | P0 | INCLUDE |
| 5 | Target selection (interactive) | P0 | INCLUDE |
| 6 | Handshake capture (passive + deauth) | P0 | INCLUDE |
| 7 | EAPOL validation | P1 | INCLUDE |
| 8 | Crack with aircrack-ng | P0 | INCLUDE |
| 9 | Crack progress tracking | P1 | INCLUDE |
| 10 | Cleanup (restore managed mode) | P0 | INCLUDE |
| 11 | Multi-adapter support | P1 | INCLUDE |
| 12 | Session state save/resume | P1 | INCLUDE |
| 13 | JSONL logging | P1 | INCLUDE |
| 14 | PMKID capture | P2 | DEFER |
| 15 | Evil Twin | P2 | DEFER |
| 16 | Wordlist management | P1 | INCLUDE (interactive prompt) |

### 6.3 MVP Tech Stack

```
Language:    Python 3.11+
TUI:         rich (tables, live output, progress bars, prompts)
Async:       asyncio (subprocess management)
Subprocess:  asyncio.create_subprocess_exec + os.killpg
Config:      CLI flags (--iface, --channel, --wordlist)
Storage:     In-memory + session.json + JSONL log
Root:        sudo ./sidewinder (single command)
Regulatory:  Auto-set iw reg set BO on startup
```

### 6.4 MVP User Flow

```
$ sudo ./sidewinder

╔══════════════════════════════════════════════════════════════╗
║  SIDEWINDER v0.1 — Native WiFi Audit Tool                   ║
╚══════════════════════════════════════════════════════════════╝

[Phase 0] Hardware Discovery
  Found 3 adapters:
  [1] wlan0  | phy0 | MT7902  | managed | ch:1  | RT
  [2] wlan1  | phy1 | RT3070  | managed | ch:6  | USB
  [3] wlan2  | phy2 | RTL8821 | managed | ch:1  | USB

  Select adapter for attack: 2

[Phase 1] Service Management
  Found conflicting processes:
    PID 1234  NetworkManager
    PID 1235  wpa_supplicant
    PID 1236  dhclient
  Kill? [Y/n]: Y
  Killed 3 processes.

[Phase 2] Monitor Mode
  Creating monitor VIF on wlan1...
  phy1 → wlan1mon (monitor)
  Channel: 6 | TX Power: 30 dBm
  Verification: type=803 [*]

[Phase 3] Scanning...
  [1] AA:BB:CC:DD:EE:FF  | Ch:6  | WPA2 | -47dBm | 3 clients | NASA
  [2] 11:22:33:44:55:66  | Ch:11 | WPA2 | -62dBm | 1 client  | NASA+
  [3] 77:88:99:AA:BB:CC  | Ch:1  | OPEN | -71dBm | 0 clients | Guest

  Press Enter to stop scanning...

[Phase 4] Target: NASA (AA:BB:CC:DD:EE:FF)
  Channel locked: 6
  Clients:
    [1] 11:22:33:44:55:66 | -65dBm | Last seen: 2s ago
    [2] 55:66:77:88:99:AA | -72dBm | Last seen: 15s ago

[Phase 5] Capture Method:
  [1] Passive (wait for handshake)
  [2] Active deauth (force handshake)
  [3] PMKID (clientless)

  > 2

  Deauth target: 1 (11:22:33:44:55:66)
  Sending 10 deauth frames...
  Capturing on wlan1mon...
  [*] EAPOL M1+M2 detected! (Partial handshake)
  [*] EAPOL M3+M4 detected! (Full handshake)
  Saved: captures/NASA_AA-BB-CC-DD-EE-FF_20260605_2304.pcap
  SHA-256: a1b2c3d4...

[Phase 6] Crack
  Wordlist: /usr/share/wordlists/rockyou.txt (14,344,392 lines)
  Starting aircrack-ng...
  [00:03:45] 1,234,567 keys/s | ETA: 00:15:30 | password123
  ...
  [*] KEY FOUND! password123
  Saved: results/NASA_cracked.txt

[Phase 7] Cleanup
  Stopping capture...
  Deleting wlan1mon...
  Restoring wlan1 (managed)...
  Restarting NetworkManager...
  [*] Done.
```

---

## 7. Sidewinder vs Wcrack vs Airgeddon vs Wifite

| Feature | Sidewinder | Wcrack | Airgeddon | Wifite |
|---------|-----------|--------|-----------|--------|
| Interface | Terminal TUI | Web GUI | Bash menu | CLI |
| Language | Python | Python+React | Bash | Python |
| airmon-ng | Bypassed (native) | Used as wrapper | Used as wrapper | Used as wrapper |
| Lines of code | ~2000 (est) | ~10,000+ | ~20,000 | ~8,000 |
| Dependencies | Python only | Node, npm, FastAPI, SQLAlchemy | Bash, xterm, many | Python, aircrack-ng |
| Root required | Yes | Yes | Yes | Yes |
| Deploy | `sudo ./sidewinder` | `sudo ./start.sh` | `bash airgeddon.sh` | `sudo wifite` |
| Real-time scan | Yes (stdout parse) | Yes (stdout parse) | Yes (curses) | Yes (curses) |
| EAPOL validation | Yes | Yes | Yes | Yes |
| PMKID | Yes | Yes | Yes | Yes |
| Evil Twin | P2 (later) | Yes (6 templates) | Yes (many) | No |
| Crack | Yes | Yes | Yes | Yes |
| Scope control | P1 (later) | Yes | No | No |

---

## 8. Key Design Decisions

### D1: No Database for MVP
Wcrack had 14 SQLite tables. Most were never queried twice. Sidewinder stores everything in memory. Optional JSONL log for post-session review.

### D2: No EventBus for MVP
Wcrack's EventBus had 100K ring buffer, 30+ topics, dead letter queue. Sidewinder uses direct function calls. If you need async decoupling, use `asyncio.Queue`.

### D3: No ManagedProcess for MVP
Wcrack's 160-line ManagedProcess solved pipe deadlocks and zombie processes. Sidewinder uses `asyncio.create_subprocess_exec` + `os.killpg` (20 lines). The key insight: `start_new_session=True` in `create_subprocess_exec` gives you process group isolation for free.

### D4: No WebSocket for MVP
Wcrack's WS had exponential backoff, history replay, sequence IDs. Sidewinder's TUI renders directly from memory. Zero network overhead.

### D5: airmon-ng Bypass
Every WiFi tool (airgeddon, wifite, Wcrack) wraps airmon-ng. Sidewinder calls `iw`, `ip`, sysfs directly. This eliminates:
- Bash parsing overhead
- airmon-ng version compatibility issues
- Dependency on the aircrack-ng package (only need `iw`, `ip`, `airodump-ng`, `aireplay-ng`)

### D6: Single Process, No Fork
Wcrack: FastAPI (port 8000) + Vite (port 3000) + WebSocket hub + EventBus + Worker. Sidewinder: one process, one terminal, one user.

---

## 9. Final Decisions

| # | Question | Decision |
|---|----------|----------|
| Q1 | TUI framework | **rich** — simple tables, live output, progress bars |
| Q2 | Evil Twin | **Defer to P2** — focus on scan→capture→crack first |
| Q3 | Scope control | **Trust the operator** — no BSSID allowlist |
| Q4 | PMKID | **Defer to P2** — handshake only for MVP |
| Q5 | Wordlist | **Interactive prompt** — user provides path at crack time |
| Q6 | Logging | **JSONL file** — `~/.sidewinder/logs/YYYYMMDD_HHMMSS.jsonl` |
| Q7 | Session state | **Save session** — `~/.sidewinder/session.json` (scan, target, captures) |
| Q8 | Multi-adapter | **Multi-adapter support** — scan on one, capture on another |
| Q9 | Regulatory domain | **Auto-set BO** — `iw reg set BO` on startup |
| Q10 | Progress display | **Rich progress bars** — for scan, capture, crack operations |

---

## 10. UX Decisions (Locked — 60 Questions)

### 10.1 Core Architecture (Q1–Q10)

| # | Question | Decision |
|---|----------|----------|
| Q1 | TUI framework | **rich** — simple tables, live output, progress bars |
| Q2 | Evil Twin | **Defer to P2** — focus on scan→capture→crack first |
| Q3 | Scope control | **Trust the operator** — no BSSID allowlist |
| Q4 | PMKID | **Defer to P2** — handshake only for MVP |
| Q5 | Wordlist | **Interactive prompt** — user provides path at crack time |
| Q6 | Logging | **JSONL file** — `~/.sidewinder/logs/YYYYMMDD_HHMMSS.jsonl` |
| Q7 | Session state | **Save session** — `~/.sidewinder/session.json` (scan, target, captures) |
| Q8 | Multi-adapter | **Multi-adapter support** — scan on one, capture on another |
| Q9 | Regulatory domain | **Auto-set BO** — `iw reg set BO` on startup |
| Q10 | Progress display | **Rich progress bars** — for scan, capture, crack operations |

### 10.2 UX Flow (Q11–Q20)

| # | Question | Decision |
|---|----------|----------|
| Q11 | Help system | **Full tutorial mode** — press `?` for complete WiFi audit tutorial |
| Q12 | Progress bar detail | **Current key** — show which key is being tested during crack |
| Q13 | Regulatory domain UX | **Ask once + remember** — first run asks, saves choice |
| Q14 | Screen transitions | **Fade effect** — brief fade animation between screens |
| Q15 | Hint system | **Bottom hint bar** — always show 2-3 relevant key hints |
| Q16 | Unicode support | **Graceful fallback** — try Unicode first, ASCII if not supported |
| Q17 | Accessibility | **Colors only** — no special color blindness mode |
| Q18 | Startup check | **Full check** — root, iw, aircrack-ng, hashcat, adapter present |
| Q19 | Ctrl+C behavior | **Always confirm** — no force quit, user must answer prompt |
| Q20 | Log naming | **Timestamp + target** — `YYYYMMDD_HHMMSS_BSSID.jsonl` |

### 10.3 opencode Style (Q21–Q24)

| # | Question | Decision |
|---|----------|----------|
| Q21 | Color scheme | **Match vibe, not colors** — WiFi-themed (green signals, cyan RF), not opencode's orange |
| Q22 | Keybindings | **Vim-style** — j/k navigate, Enter selects, Esc back, / searches, ? helps |
| Q23 | Slash commands | **WiFi-specific** — /scan, /target, /capture, /crack, /cleanup, /help, /status, /adapter |
| Q24 | Status bar | **Full status** — adapter + channel + mode + signal + clients + active job + elapsed time |

### 10.4 Screen Design (Q25–Q28)

| # | Question | Decision |
|---|----------|----------|
| Q25 | ASCII logo | **Snake coiled around text** — ASCII art sidewinder snake + SIDEWINDER |
| Q26 | Scan results | **Full table, opencode vibe** — all airodump columns with styled borders |
| Q27 | Capture method | **Always show all methods** — let user pick: Passive, Deauth, PMKID |
| Q28 | Capture progress | **Live packet counters** — beacons, data, IVs, rate, elapsed time + progress bar |

### 10.5 Attack UX (Q29–Q32)

| # | Question | Decision |
|---|----------|----------|
| Q29 | Deauth target selection | **Visual table + checkboxes** — Space toggles, Enter confirms, all selected by default |
| Q30 | Cracking tools | **Both aircrack-ng + hashcat** — show both, let user pick |
| Q31 | Wordlist browser | **Auto-discover + manual** — scan /usr/share/wordlists/ and ~/wordlists/, manual path option |
| Q32 | Error display | **Rich error card** — What happened, Why, How to fix. Styled box with suggestions |

### 10.6 Multi-Adapter (Q33–Q34)

| # | Question | Decision |
|---|----------|----------|
| Q33 | Adapter selection | **Visual adapter cards** — each adapter as card: Name, Driver, Chipset, MAC, Mode, Status |
| Q34 | Regulatory domain | **Ask once + remember** — set BO on first run, save preference |

### 10.7 Confirmation UX (Q35–Q36)

| # | Question | Decision |
|---|----------|----------|
| Q35 | Confirmations | **Everything** — confirm before every action (scan, capture, deauth, crack, cleanup) |
| Q36 | Border style | **Minimal borders** — box-drawing characters (╭╮╰╯), subtle and clean |

### 10.8 Logo & Help (Q37–Q38)

| # | Question | Decision |
|---|----------|----------|
| Q37 | ASCII logo style | **Snake coiled around text** — compact, iconic ASCII art |
| Q38 | Help content | **Full tutorial** — complete WiFi audit tutorial on `?` press |

### 10.9 Session Resume (Q39)

| # | Question | Decision |
|---|----------|----------|
| Q39 | Session resume | **opencode vibe** — auto-detect session.json on launch, show: "Resume previous session? [Scan: 12 APs found] [Y/n]" |

### 10.10 Cyber Expert Questions (Q41–Q48)

| # | Question | Decision |
|---|----------|----------|
| Q41 | Rate limiting | **User controls** — show current rate, let user adjust with +/- keys during attack |
| Q42 | Channel scanning | **All at once** — scan all channels simultaneously (if adapter supports it) |
| Q43 | Hidden SSIDs | **Show with marker** — show `[HIDDEN]` in SSID column, still show BSSID/CH/signal |
| Q44 | WPS detection | **Always show** — show "WPS: Yes" or "WPS: Locked" column in scan |
| Q45 | MAC randomization | **Detect + warn** — if MAC changes between scans, show warning |
| Q46 | Client fingerprinting | **Full fingerprint** — vendor + device type + OS guess from probe requests |
| Q47 | Cooldown after attack | **User controls** — show cooldown timer, user can override. Default 10 sec |
| Q48 | Log file naming | **Timestamp + target** — `YYYYMMDD_HHMMSS_BSSID.jsonl` |

### 10.11 Client Fingerprinting (Q49)

| # | Question | Decision |
|---|----------|----------|
| Q49 | Fingerprint details | **Vendor + device type + OS guess** — e.g., "Apple iPhone (iOS 16+)" or "Samsung Galaxy (Android 13)" |

### 10.12 Multi-Channel Capture (Q50)

| # | Question | Decision |
|---|----------|----------|
| Q50 | Channel handling | **Lock to target channel** — after scan, lock adapter to target's channel for capture |

### 10.13 Ctrl+C Behavior (Q51)

| # | Question | Decision |
|---|----------|----------|
| Q51 | Ctrl+C force quit | **Always confirm** — no force quit after multiple presses, user must answer prompt |

### 10.14 Startup Check (Q52)

| # | Question | Decision |
|---|----------|----------|
| Q52 | Startup validation | **Full check** — root, iw, aircrack-ng, airmon-ng, hashcat, adapter present. Show results in styled table |

### 10.15 Accessibility (Q53–Q56)

| # | Question | Decision |
|---|----------|----------|
| Q53 | Color blindness | **Colors only** — no special accessibility mode |
| Q54 | Unicode support | **Graceful fallback** — try Unicode (╭╮╰╯▶[*]✗), fallback to ASCII (-+, > Y/N) |
| Q55 | Hint display | **Bottom hint bar** — always show 2-3 most relevant key hints, change contextually |
| Q56 | Screen transitions | **Fade effect** — brief fade animation between screens |

### 10.16 Post-Crack UX (Q57–Q59)

| # | Question | Decision |
|---|----------|----------|
| Q57 | Password display | **Styled result card** — show SSID, BSSID, Password, Method, Time taken. Offer save/copy/try again |
| Q58 | Cleanup flow | **Show files + confirm** — list all files to be deleted, user confirms each group |
| Q59 | Version checking | **None** — no update checking on startup |

### 10.17 Final Lock-in (Q60)

| # | Question | Decision |
|---|----------|----------|
| Q60 | Ready to implement | **Yes** — all 60 UX decisions locked in |

---

## 11. TUI Color Palette

### 11.1 WiFi-Themed Colors (Matching opencode vibe, not colors)

| Element | Color | Hex | Usage |
|---------|-------|-----|-------|
| Primary | Warm Green | `#4CAF50` | Scan results, active elements |
| Secondary | Cyan | `#00BCD4` | RF info, signal strength |
| Accent | Purple | `#9C27B0` | Highlights, selected items |
| Success | Bright Green | `#00E676` | Handshake captured, password found |
| Error | Red | `#F44336` | Errors, warnings |
| Warning | Orange | `#FF9800` | Rate limits, cooldowns |
| Info | Blue | `#2196F3` | Help text, hints |
| Muted | Gray | `#9E9E9E` | Secondary text, borders |
| Background | Dark | `#1A1A2E` | Terminal background |
| Text | Light | `#E0E0E0` | Primary text |

### 11.2 Signal Strength Visual Indicators

| Signal | Bar | Color | Text |
|--------|-----|-------|------|
| Excellent (>-50) | `██████████` | Bright Green | `-47dBm` |
| Good (-50 to -60) | `████████░░` | Green | `-55dBm` |
| Fair (-60 to -70) | `██████░░░░` | Yellow | `-65dBm` |
| Weak (-70 to -80) | `████░░░░░░` | Orange | `-75dBm` |
| Very Weak (<-80) | `██░░░░░░░░` | Red | `-85dBm` |

---

## 12. TUI Layout (opencode Style)

### 12.1 Screen Structure

```
┌─────────────────────────────────────────────────────────────────┐
│ [ASCII LOGO] SIDEWINDER v0.1                    [adapter: wlan0]│
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ Main Content Area ─────────────────────────────────────┐   │
│  │                                                          │   │
│  │  (Scan results, capture progress, crack status, etc.)   │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ j/k: navigate  Enter: select  Esc: back  /: search  ?: help   │
├─────────────────────────────────────────────────────────────────┤
│ wlan1mon │ Ch:6 │ Monitor │ -47dBm │ 3 clients │ Ready │ 2:30 │
└─────────────────────────────────────────────────────────────────┘
```

### 12.2 Main Menu (opencode Style)

```
╭─────────────────────────────────────────────────────────────────╮
│                                                                 │
│    ▗▄▄▄▖ ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▖ │
│    █    █ █ SIDEWINDER v0.1 — Native WiFi Audit Tool        █ │
│    █▄▄▄▄█▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█ │
│                                                                 │
│    What do you want to do?                                      │
│                                                                 │
│    ▶ [1]  Scan WiFi networks (see what's around)                │
│      [2]  Target a specific network (attack mode)               │
│      [3]  Crack a captured handshake                            │
│      [4]  View saved captures & results                         │
│      [5]  Hardware & settings                                   │
│      [6]  Cleanup (restore normal mode)                         │
│      [7]  Help & tutorial                                       │
│      [0]  Exit                                                  │
│                                                                 │
│    ──────────────────────────────────────────────────────────   │
│    Tip: Press [1] to scan, or [/] for commands                  │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

### 12.3 Scan Results (Full Table, opencode Vibe)

```
╭─────────────────────────────────────────────────────────────────╮
│ ▗▄▄▄▖ SIDEWINDER — Scanning... (Ctrl+C to stop)                │
│ █  █                                                             │
├─────────────────────────────────────────────────────────────────┤
│ BSSID               CH  Signal  Rate   Privacy  Cipher  ESSID   │
├─────────────────────────────────────────────────────────────────┤
│ ▶ AA:BB:CC:DD:EE:F1   6  ████████░░  54e  WPA2     CCMP    Home │
│   AA:BB:CC:DD:EE:F2   1  ██████████  54e  WPA2     CCMP    Cafe │
│   AA:BB:CC:DD:EE:F3  11  ██████░░░░  54e  WPA2     CCMP    [HIDDEN]│
│   AA:BB:CC:DD:EE:F4   6  ████░░░░░░  54e  WPA      TKIP    Guest│
│   AA:BB:CC:DD:EE:F5   1  ████████░░  54e  WPA2     CCMP    Office│
├─────────────────────────────────────────────────────────────────┤
│ Found: 5 APs │ 12 clients │ Channel: 6 │ Elapsed: 0:45        │
├─────────────────────────────────────────────────────────────────┤
│ j/k: navigate  Enter: select target  Esc: back  /: filter      │
╰─────────────────────────────────────────────────────────────────╯
```

### 12.4 Capture Method Selection

```
╭─────────────────────────────────────────────────────────────────╮
│ ▗▄▄▄▖ SIDEWINDER — Capture Method                              │
│ █  █                                                             │
├─────────────────────────────────────────────────────────────────┤
│ Target: Home (AA:BB:CC:DD:EE:F1) — Channel 6                   │
│                                                                 │
│ Select capture method:                                          │
│                                                                 │
│ ▶ [1]  Passive Capture (listen for handshake)                   │
│       [2]  Deauth + Capture (kick clients, recapture)           │
│       [3]  PMKID Capture (router-only, no clients needed)       │
│                                                                 │
│ ────────────────────────────────────────────────────────────── │
│ Note: Deauth requires root and may disrupt network.            │
│       PMKID requires compatible adapter (rtw88/rtw89).          │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

### 12.5 Live Capture Progress

```
╭─────────────────────────────────────────────────────────────────╮
│ ▗▄▄▄▖ SIDEWINDER — Capturing Handshake                         │
│ █  █                                                             │
├─────────────────────────────────────────────────────────────────┤
│ Target: Home (AA:BB:CC:DD:EE:F1) — Ch:6 — Method: Deauth      │
│                                                                 │
│ ┌─ Capture Stats ───────────────────────────────────────────┐   │
│ │ Beacons: 1,234  │  Data: 567  │  IVs: 890               │   │
│ │ Rate: 45/s      │  Signal: -47dBm  │  Elapsed: 2:30      │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─ EAPOL Handshake ─────────────────────────────────────────┐   │
│ │ M1: [*]  M2: [*]  M3: ✗  M4: ✗    [Partial]                │   │
│ │ ████████████████░░░░░░░░░░░░░░  50%                       │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ Press Ctrl+C to stop capture                                    │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

### 12.6 Deauth Target Selection (Checkboxes)

```
╭─────────────────────────────────────────────────────────────────╮
│ ▗▄▄▄▖ SIDEWINDER — Select Deauth Targets                       │
│ █  █                                                             │
├─────────────────────────────────────────────────────────────────┤
│ Target: Home (AA:BB:CC:DD:EE:F1) — Channel 6                   │
│                                                                 │
│ Clients connected:                                              │
│                                                                 │
│ ▶ [[*]]  AA:11:22:33:44:55  Apple iPhone 15  (-47dBm)  342 pkts │
│   [[*]]  BB:11:22:33:44:55  Samsung Galaxy S24 (-52dBm)  218 pkts│
│   [[*]]  CC:11:22:33:44:55  Intel Laptop     (-65dBm)  156 pkts│
│   [ ]  DD:11:22:33:44:55  Unknown           (-78dBm)   42 pkts│
│                                                                 │
│ ────────────────────────────────────────────────────────────── │
│ Space: toggle  ↑↓: navigate  Enter: confirm  a: select all     │
│ Rate: [5 deauths/sec]  +/-: adjust                             │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

### 12.7 Crack Progress

```
╭─────────────────────────────────────────────────────────────────╮
│ ▗▄▄▄▖ SIDEWINDER — Cracking Handshake                          │
│ █  █                                                             │
├─────────────────────────────────────────────────────────────────┤
│ Wordlist: /usr/share/wordlists/rockyou.txt (14,344,391 keys)   │
│ Method: aircrack-ng (CPU)                                       │
│                                                                 │
│ ┌─ Progress ─────────────────────────────────────────────────┐   │
│ │ ████████████████████░░░░░░░░░░░░░░░░░░░░░  45%            │   │
│ │ Keys tested: 6,454,976 / 14,344,391                       │   │
│ │ Speed: 12,345 keys/sec  │  ETA: 15:23                     │   │
│ │ Current: password12345                                     │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ Press Ctrl+C to stop cracking                                   │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

### 12.8 Styled Result Card (Password Found)

```
╭─────────────────────────────────────────────────────────────────╮
│ ▗▄▄▄▖ SIDEWINDER — Password Found!                             │
│ █  █                                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─ RESULT ──────────────────────────────────────────────────┐   │
│ │                                                            │   │
│ │  SSID:     Home                                            │   │
│ │  BSSID:    AA:BB:CC:DD:EE:F1                               │   │
│ │  Password: supersecretpassword123                          │   │
│ │  Method:   aircrack-ng (CPU)                               │   │
│ │  Time:     15:23                                           │   │
│ │  Keys:     6,454,976 tested                                │   │
│ │                                                            │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ [1] Save to file  [2] Copy to clipboard  [3] Try another wordlist│
│ [4] Attack another network  [5] Cleanup  [6] Main menu          │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

### 12.9 Full Tutorial (Help Screen)

```
╭─────────────────────────────────────────────────────────────────╮
│ ▗▄▄▄▖ SIDEWINDER — WiFi Audit Tutorial                         │
│ █  █                                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Welcome to Sidewinder! This tutorial covers the basics.        │
│                                                                 │
│  Phase 1: Scan                                                  │
│  ─────────────                                                  │
│  1. Press [1] to scan WiFi networks                             │
│  2. Wait for results (auto-hops all channels)                   │
│  3. Press Enter to stop when you see your target                │
│  4. Select target from the list                                 │
│                                                                 │
│  Phase 2: Capture                                               │
│  ───────────────                                                │
│  1. Choose capture method (passive/deauth/pmkid)                │
│  2. Select deauth targets if applicable                         │
│  3. Wait for EAPOL handshake (M1-M4)                            │
│  4. Press Ctrl+C when complete                                  │
│                                                                 │
│  Phase 3: Crack                                                 │
│  ─────────────                                                  │
│  1. Select wordlist (auto-discovers common paths)               │
│  2. Choose tool (aircrack-ng or hashcat)                        │
│  3. Wait for password                                           │
│                                                                 │
│  Phase 4: Cleanup                                               │
│  ───────────────                                                │
│  1. Press [6] to restore normal mode                            │
│  2. Confirm file deletion                                       │
│  3. Exit safely                                                 │
│                                                                 │
│ ──────────────────────────────────────────────────────────────  │
│ Press Esc to return to main menu                                │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

---

## 13. Keybinding Reference

| Key | Action | Context |
|-----|--------|---------|
| `j` / `↓` | Navigate down | Any list |
| `k` / `↑` | Navigate up | Any list |
| `Enter` | Select / Confirm | Any selection |
| `Esc` | Go back / Cancel | Any screen |
| `/` | Search / Filter | Scan results |
| `?` | Open help/tutorial | Any screen |
| `Space` | Toggle checkbox | Deauth targets |
| `a` | Select all | Deauth targets |
| `+` / `-` | Adjust rate | Deauth/capture |
| `Tab` | Switch panels | Multi-panel screens |
| `Ctrl+C` | Graceful exit | Any screen |

---

## 14. Slash Commands

| Command | Action | Description |
|---------|--------|-------------|
| `/scan` | Start scan | Begin WiFi network scan |
| `/target` | Select target | Choose attack target |
| `/capture` | Start capture | Begin handshake capture |
| `/crack` | Start crack | Begin password cracking |
| `/cleanup` | Cleanup | Restore normal mode |
| `/help` | Open help | Show tutorial |
| `/status` | Show status | Display current adapter/channel/mode |
| `/adapter` | Switch adapter | Change active adapter |
| `/quit` | Exit | Graceful exit with cleanup |

---

## 15. Backend Architecture (Priority #1)

### 15.1 Core Principle

> **"The heart of Sidewinder is the backend working of attacks, not UI."**

UI is the presentation layer. Backend is the engine. Every attack must:
1. **Work reliably** — robust subprocess management
2. **Show everything** — live logs, no silent waits
3. **Fail gracefully** — never crash, always recover
4. **Explain itself** — user always knows what's happening

### 15.2 opencode → Sidewinder Workflow Mapping

| opencode Concept | Sidewinder Equivalent | Description |
|------------------|----------------------|-------------|
| **Session** | **Audit Session** | Persist scan results, target, captures, logs |
| **Agent** | **Attack Phase** | Scan → Target → Capture → Crack → Cleanup |
| **Tool Registry** | **Attack Registry** | Each attack is a registered tool with metadata |
| **Permission Engine** | **Safety Engine** | Confirmations, rate limits, scope control |
| **Streaming Output** | **Live Log Stream** | Real-time subprocess stdout/stderr |
| **Storage** | **Session Storage** | JSONL logs, PCAP files, session.json |
| **Config System** | **Attack Config** | Default options, saved preferences |

### 15.3 Backend-First Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SIDEWINDER ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    TUI LAYER (rich)                       │   │
│  │  Main Menu │ Scan │ Capture │ Crack │ Logs │ Help        │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                     │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │                   SESSION MANAGER                         │   │
│  │  state.json │ JSONL Logger │ Config │ Resume             │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                     │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │                  SAFETY ENGINE                            │   │
│  │  Confirmations │ Rate Limits │ Scope │ Warnings          │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                     │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │                 ATTACK REGISTRY                           │   │
│  │  Scan │ Monitor │ Deauth │ Capture │ Crack │ Cleanup     │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                     │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │              SUBPROCESS MANAGER                           │   │
│  │  ProcessPool │ StreamParser │ ZombieKiller │ RetryLogic  │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                     │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │                 LIVE LOG ENGINE                           │   │
│  │  RingBuffer │ NerdScreen │ PacketCounters │ EAPOLTracker │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                     │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │              EXCEPTION HANDLER                            │   │
│  │  ErrorClassifier │ RecoveryEngine │ UserNotifier │ Logger │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 15.4 Live Log / Nerd Screen (Never Feel Stuck)

> **"The user must never feel stuck and waiting. There must be all possible indications."**

Every operation shows:
1. **What's happening** — current action description
2. **Raw data** — live subprocess output
3. **Parsed stats** — structured metrics
4. **Progress** — percentage/ETA when calculable
5. **Nerd mode** — full packet-level detail

**Key indicators always visible:**
- Beacon counter, Data counter, IV counter
- Rate (packets/sec), Signal (dBm), Channel
- EAPOL M1-M4 handshake status
- Deauth sent/ACK/no-ACK counts
- Keys tested, Speed, ETA, Current key
- Elapsed time

### 15.5 Extensive Tooltip System

> **"The user won't be in wonder 'which one I should choose' or 'what the heck this option does'."**

Every menu item, every option, every flag has a tooltip explaining:
1. **What it does** — plain English description
2. **When to use** — use case scenario
3. **Risk level** — safe / caution / dangerous
4. **Requires** — root, monitor mode, compatible adapter
5. **Example** — concrete example output

### 15.6 Exception Handling (Learned from Wcrack's 133 Bugs)

Wcrack's top bugs:
1. **Pipe deadlocks** — subprocess stdout/stderr blocking
2. **Zombie processes** — orphaned airodump-ng/scapy
3. **Race conditions** — NM re-asserting control during scan
4. **Silent failures** — errors swallowed, user stuck waiting
5. **Missing recovery** — no retry logic, no fallback

**Sidewinder's solution:**
1. **Never swallow errors** — always notify user
2. **Always show what's happening** — live log, no silent waits
3. **Automatic retry** — with exponential backoff
4. **Graceful degradation** — fallback options when primary fails
5. **User-readable messages** — "What happened, Why, How to fix"

### 15.7 Error Display Format

```
╭─────────────────────────────────────────────────────────────────╮
│ ▗▄▄▄▖ ERROR — Adapter Disconnected                             │
│ █  █                                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─ What Happened ───────────────────────────────────────────┐   │
│ │ The WiFi adapter vanished during scan operation.          │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─ Why ─────────────────────────────────────────────────────┐   │
│ │ USB adapter was physically removed or lost power.         │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─ How to Fix ──────────────────────────────────────────────┐   │
│ │ 1. Re-insert the USB adapter                              │   │
│ │ 2. Check USB cable connection                             │   │
│ │ 3. Try a different USB port                               │   │
│ │ 4. Press Enter to rescan adapters                         │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ Raw error: [Errno 19] No such device                          │
│ Time: 2026-06-05T14:32:15.123456                               │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```
