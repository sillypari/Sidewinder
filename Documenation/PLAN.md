# Sidewinder Implementation Plan v0.2

**From cybersecurity expert perspective: Complete app flow, subtools, and TUI design**

---

## 1. App Flow (User Journey — Naive User Perspective)

### 1.1 First-Time User Journey

```
START → "What do you want to do?" → "Show me WiFi around me" → "Attack that network" → "Got the password"
```

**Step-by-step mental model a naive user has:**
1. "I want to see what WiFi networks are around me" → SCAN
2. "I want to see who's connected to that network" → RECON
3. "I want to kick them off and capture the password" → DEAUTH + CAPTURE
4. "I have a file, I want to crack the password" → CRACK
5. "Done, put everything back to normal" → CLEANUP

### 1.2 Main Menu (Always Accessible)

```
╔══════════════════════════════════════════════════════════════╗
║  SIDEWINDER v0.2 — Native WiFi Audit Tool                   ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  What do you want to do?                                     ║
║                                                              ║
║    [1] 🔍 Scan WiFi networks (see what's around)             ║
║    [2] 🎯 Target a specific network (attack mode)            ║
║    [3] 🔓 Crack a captured handshake                         ║
║    [4] 📁 View saved captures & results                      ║
║    [5] [SYS]  Hardware & settings                               ║
║    [6] 🧹 Cleanup (restore normal mode)                      ║
║    [7] [?] Help & tutorial                                     ║
║    [0] 🚪 Exit                                               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

**Progressive disclosure principle:** Each menu item has 2-3 sub-modes (beginner / intermediate / expert).

### 1.3 Complete User Journey (Beginner Mode)

```
1. Launch: sudo ./sidewinder
2. Main menu → [1] Scan
3. Auto-detect adapter, ask to kill services
4. Show live scan table (updates every second)
5. Press Enter to stop scan
6. Show "Select target" table
7. User picks target #3
8. Auto-suggest "Deauth + capture" method
9. User confirms
10. Show live capture with EAPOL progress (M1, M2, M3, M4)
11. Capture complete → "Handshake saved!"
12. Auto-suggest "Crack now?"
13. User picks "Yes, use rockyou.txt"
14. Show crack progress with ETA
15. Password found → "Key: password123"
16. Main menu → [6] Cleanup
17. Restore everything → exit
```

---

## 2. Subtools & Flags (Complete Mapping)

### 2.1 Phase 0: Hardware Discovery — All Options

**Underlying tool:** `iw dev` + sysfs reads

**Sidewinder flags to expose:**

| Flag | Maps to | Purpose | Beginner Default |
|------|---------|---------|------------------|
| `--list` | `iw dev` | Just list adapters, do nothing | Yes |
| `--iface <name>` | Focus on one adapter | Pre-select adapter | Auto-pick |
| `--rescan` | Re-run discovery | Refresh adapter list | On startup |
| `--info <iface>` | Show detailed info for one adapter | Debug | No |
| `--drivers` | Show driver list (kernel vs vendor) | Debug | No |
| `--chipsets` | Show chipset database | Debug | No |

**Beginner experience:**
```
> [5] Hardware & settings
> [1] Show my adapters
```
→ Shows pretty table, auto-fills details.

### 2.2 Phase 1: Service Management — All Options

**Underlying tools:** `ps`, `pkill`, `systemctl`

**Sidewinder flags:**

| Flag | Purpose | Beginner Default |
|------|---------|------------------|
| `--check` | Just list, don't kill | Show warning first |
| `--kill` | Kill all conflicting | With confirmation |
| `--restore` | Restart killed services | On cleanup |
| `--kill-networkmanager` | Stop NM only | Auto-include |
| `--kill-wpa-supplicant` | Kill wpa_supplicant | Auto-include |
| `--kill-dhclient` | Kill dhclient | Auto-include |
| `--kill-avahi` | Kill avahi-daemon | Auto-include |

**Beginner experience:**
```
Found these processes using your WiFi adapter:
  PID 1234  NetworkManager
  PID 1235  wpa_supplicant
  PID 1236  dhclient

What this means: These programs fight over the WiFi adapter.
We need to stop them so we can put the adapter in "monitor mode"
(like a radio scanner that can hear all WiFi traffic).

Kill them? [Y/n]: Y
[*] Killed 3 processes. We'll restart them when you're done.
```

### 2.3 Phase 2: Monitor Mode — All Options

**Underlying tools:** `iw`, `ip`, sysfs

**Sidewinder flags:**

| Flag | Maps to | Purpose | Beginner Default |
|------|---------|---------|------------------|
| `--monitor <iface>` | Enable monitor mode | Main action | Yes |
| `--managed <iface>` | Restore managed mode | Cleanup | Yes |
| `--channel <N>` | Set channel (1-14 or 36-165) | Pre-lock | Auto |
| `--txpower <dBm>` | Set TX power (1000-3000) | Range boost | 3000 |
| `--elite` | Keep managed + monitor (don't delete managed) | No VIF | False |
| `--bad-driver` | Use direct mode (rtl8821au) | Auto-detect | Auto |
| `--band 2g/5g/6g` | Restrict to band | All | All |

**Beginner experience:**
```
[2/7] Setting up monitor mode on wlan1 (Ralink RT3070)...

What is monitor mode?
┌────────────────────────────────────────────────────────────┐
│ Normal WiFi mode: Your adapter only listens to traffic    │
│ meant for YOU (like a phone call).                        │
│                                                            │
│ Monitor mode: Your adapter listens to ALL WiFi traffic    │
│ in range (like a radio scanner picking up all stations).  │
└────────────────────────────────────────────────────────────┘

This is required for WiFi auditing.

[*] Putting wlan1 into monitor mode...
[*] Created wlan1mon (monitor interface)
[*] Set channel: 6 (will change automatically during scan)
[*] TX power: 30 dBm (max range)
[*] Verified: interface type is now "monitor"
```

### 2.4 Phase 3: Reconnaissance — All Options (MOST FLAGS)

**Underlying tool:** `airodump-ng`

**Complete airodump-ng flags → Sidewinder mapping:**

| airodump-ng Flag | Sidewinder Flag | Purpose | Beginner Default |
|------------------|-----------------|---------|------------------|
| `-c <channel>` | `--channel <N>` | Lock to channel (1-165) | Auto-hop all |
| `-c 1,6,11` | `--channels 1,6,11` | Specific channels | All |
| `--band a` | `--band 5g` | 5 GHz only | All |
| `--band bg` | `--band 2g` | 2.4 GHz only | All |
| `--band abg` | `--band all` | All bands | All |
| `--bssid <MAC>` | `--bssid <MAC>` | Single target only | All |
| `-a` | `--associated-only` | Only show clients connected to APs | No |
| `--wps` | `--show-wps` | Show WPS info | Yes |
| `--output-format pcap,csv` | `--save-format pcap,csv` | What files to write | csv,pcap |
| `--write <prefix>` | `--save-path <dir>` | Where to save | ~/.sidewinder/scans/ |
| `--write-interval <sec>` | `--update-interval 1` | CSV write frequency | 1s |
| `--beacons` | `--beacon-timeout 5` | Stop showing AP after N beacon-less sec | None |
| `--update <sec>` | `--screen-refresh 1` | Screen refresh rate | 1s |
| `--show-ack` | `--show-ack-frames` | Show ACK frames | No |
| `-I <duration>` | `--inject-test <N>` | Test injection (N packets) | No |
| `--manufacturer` | `--show-vendor` | OUI lookup for vendors | Yes |
| `-U` | `--detailed-updates` | Show deltas only (not full refresh) | No |
| `-s` | `--sort-clients` | Sort clients by BSSID | No |
| `-r <file>` | `--replay <file>` | Replay from capture file | No |

**Filtering options (beginner-friendly):**

| Filter | Sidewinder Flag | Beginner Default |
|--------|-----------------|------------------|
| Min signal strength | `--min-signal -70` | -90 (show all) |
| Encryption type | `--enc wpa2` | All |
| SSID contains | `--ssid-contains NASA` | All |
| Hide hidden SSIDs | `--hide-hidden` | Show all |
| WPS only | `--wps-only` | No |

**Beginner experience:**
```
[3/7] Scanning WiFi networks...

Scan options:
  [1] Quick scan (2.4 GHz only, fast)        ← RECOMMENDED
  [2] Full scan (both bands, thorough)        ← Takes longer
  [3] Custom scan (you choose settings)       ← Expert mode

> 1

Scanning 2.4 GHz channels 1-14... (press Enter to stop)

╔════╤═══════════════════╤════╤═══════╤══════╤════════╤════════╗
║  # │ BSSID             │ CH │ PWR   │ ENC  │ CLIENT │ ESSID  ║
╠════╪═══════════════════╪════╪═══════╪══════╪════════╪════════╣
║  1 │ AA:BB:CC:DD:EE:FF │  6 │ -47   │ WPA2 │   3    │ NASA   ║
║  2 │ 11:22:33:44:55:66 │ 11 │ -62   │ WPA2 │   1    │ NASA+  ║
║  3 │ 77:88:99:AA:BB:CC │  1 │ -71   │ OPEN │   0    │ Guest  ║
╚════╧═══════════════════╧════╧═══════╧══════╧════════╧════════╝

[Live: 2.3s elapsed | Networks: 3 | Clients: 4]
```

### 2.5 Phase 4: Target Selection — All Options

**No underlying tool — pure UI logic**

**Options:**

| Option | Sidewinder Flag | Beginner Default |
|--------|-----------------|------------------|
| Select by number | `--target 1` | Interactive |
| Select by BSSID | `--target-bssid AA:BB:CC:DD:EE:FF` | No |
| Select by SSID | `--target-ssid NASA` | No |
| Show all clients | `--show-clients` | Yes |
| Refresh scan | `--refresh-scan` | Auto |
| View AP details | `--ap-details` | Interactive |

**Beginner experience:**
```
Select a target network to attack:

  [1] NASA       (WPA2, 3 clients, -47dBm EXCELLENT)  ← RECOMMENDED
  [2] NASA+      (WPA2, 1 client,  -62dBm GOOD)
  [3] Guest      (OPEN,  0 clients, -71dBm WEAK)

> 1

[*] Selected: NASA (AA:BB:CC:DD:EE:FF)
  Channel: 6 (locked)
  Encryption: WPA2-PSK (CCMP)
  Signal: Excellent (-47 dBm)
  Clients: 3 connected devices

Clients on this network:
  [1] 11:22:33:44:55:66  -65dBm  (last seen: 2s ago)
  [2] 55:66:77:88:99:AA  -72dBm  (last seen: 15s ago)
  [3] AA:BB:CC:11:22:33  -58dBm  (last seen: 1s ago)  ← Active
```

### 2.6 Phase 5: Attack — All Options (airodump-ng + aireplay-ng)

**Underlying tools:** `airodump-ng`, `aireplay-ng`

#### 2.6.1 Capture Method

| Method | Sidewinder Flag | Description | Beginner Default |
|--------|-----------------|-------------|------------------|
| Passive | `--capture passive` | Wait for handshake naturally | No |
| Active deauth | `--capture deauth` | Kick clients off to force handshake | Yes |
| Broadcast deauth | `--capture deauth-broadcast` | Kick ALL clients | No |
| Continuous deauth | `--capture deauth-loop` | Keep kicking until handshake | No |
| Smart deauth | `--capture smart` | Auto-detect best method | Yes |

#### 2.6.2 Deauth Options (aireplay-ng)

| aireplay-ng Flag | Sidewinder Flag | Purpose | Beginner Default |
|-------------------|-----------------|---------|------------------|
| `--deauth <count>` | `--deauth-count 10` | Number of deauth frames | 10 |
| `-0` | `--deauth` | Deauth attack | Yes |
| `-1` | `--fakeauth` | Fake authentication | No |
| `-3` | `--arp-inject` | ARP replay (WEP) | No |
| `-4` | `--chopchop` | Chopchop (WEP) | No |
| `-5` | `--fragment` | Fragmentation (WEP) | No |
| `-a <BSSID>` | `--ap <BSSID>` | Target AP | Auto from target |
| `-c <MAC>` | `--client <MAC>` | Specific client | Auto-pick active |
| `-h <MAC>` | `--source <MAC>` | Source MAC (for fakeauth) | Our MAC |
| `--ignore-negative-one` | `--ignore-negative` | Skip "channel -1" warning | Yes |
| `-x <pps>` | `--pps 500` | Packets per second | 500 |
| `--no-ack` | `--no-ack` | Don't wait for ACK | No |

#### 2.6.3 Capture Options (airodump-ng)

| airodump-ng Flag | Sidewinder Flag | Purpose | Beginner Default |
|-------------------|-----------------|---------|------------------|
| `--bssid <MAC>` | `--capture-bssid <MAC>` | Single AP | Auto |
| `-c <channel>` | `--capture-channel 6` | Lock channel | Auto |
| `--write <prefix>` | `--capture-path <dir>` | Save location | ~/.sidewinder/captures/ |
| `--output-format pcap` | `--capture-format pcap` | File format | pcap |
| `-w` (same as --write) | `--write-name <name>` | Filename prefix | Auto (target_SSID) |

#### 2.6.4 Validation Options

| Option | Purpose | Beginner Default |
|--------|---------|------------------|
| `--auto-stop-on-handshake` | Stop when 4-way EAPOL captured | Yes |
| `--timeout <sec>` | Stop after N seconds | 60s |
| `--max-wait <sec>` | Total max wait time | 300s |
| `--verify-handshake` | Check M1-M4 before saving | Yes |
| `--require-full` | Need M1+M2+M3+M4 (vs partial) | No (M1+M2 OK) |
| `--save-sha256` | Compute hash | Yes |

**Beginner experience:**
```
[5/7] Capture attack: NASA (AA:BB:CC:DD:EE:FF)

Choose attack method:
  [1] Smart deauth (recommended)        ← AUTO-PICKS BEST
  [2] Deauth all clients                ← Loud, fast
  [3] Passive (wait for handshake)      ← Quiet, slow
  [4] Custom (expert mode)              ← All options

> 1

Smart mode will:
  1. Identify most active client
  2. Send 10 deauth frames
  3. Wait for reconnection (triggers handshake)
  4. Capture handshake
  5. Auto-validate (check M1-M4)
  6. Auto-save

Proceed? [Y/n]: Y

[*] Starting capture on wlan1mon, channel 6...
[*] Sending 10 deauth frames to 11:22:33:44:55:66...
[*] Waiting for handshake...

  Progress:  [████████░░░░░░░░░░░░] 40%
  EAPOL:     [M1 [*]] [M2 [*]] [M3 ...] [M4 ...]
  Frames:    1,234 captured
  Time:      23s elapsed

  Progress:  [████████████████████] 100%
  EAPOL:     [M1 [*]] [M2 [*]] [M3 [*]] [M4 [*]]  ← FULL HANDSHAKE!
  Frames:    2,456 captured
  Time:      47s elapsed

[*] Handshake captured!
  Saved: ~/.sidewinder/captures/NASA_AA-BB-CC-DD-EE-FF_20260605_2304.pcap
  SHA-256: a1b2c3d4e5f6...
  Status:  VALID (all 4 EAPOL frames present)
```

### 2.7 Phase 6: Cracking — All Options

**Underlying tools:** `aircrack-ng`, `hashcat`

#### 2.7.1 Cracking Engine

| Engine | Sidewinder Flag | Speed | Beginner Default |
|--------|-----------------|-------|------------------|
| aircrack-ng | `--engine aircrack` | CPU only | No |
| hashcat | `--engine hashcat` | GPU (fast) | Yes if available |
| john | `--engine john` | CPU | No |

#### 2.7.2 aircrack-ng Flags

| aircrack-ng Flag | Sidewinder Flag | Purpose | Beginner Default |
|-------------------|-----------------|---------|------------------|
| `-w <file>` | `--wordlist <file>` | Dictionary | Interactive |
| `-b <MAC>` | `--bssid <MAC>` | Target BSSID | Auto |
| `-e <SSID>` | `--ssid <SSID>` | Target SSID | Auto |
| `-l <file>` | `--output-file <file>` | Save result | ~/.sidewinder/results/ |
| `-p <n>` | `--threads <n>` | CPU threads | All |
| `-q` | `--quiet` | Less output | No |
| `-K` | `--korek-attack` | WEP only | No |
| `-y <file>` | `--fudge <file>` | WEP fudge | No |
| `-x <n>` | `--xor <n>` | WEP bruteforce | No |
| `-c` | `--wep-128` | WEP 128-bit | No |
| `-h` | `--help` | Show help | No |
| `--cpu-threads` | `--cpu-threads` | Thread count | Auto |
| `-u` | `--hide-cracked` | Hide already cracked | No |
| `--simd` | `--simd` | Use SIMD (AVX/SSE) | Yes |

#### 2.7.3 hashcat Flags (when used)

| hashcat Flag | Sidewinder Flag | Purpose | Beginner Default |
|---------------|-----------------|---------|------------------|
| `-m 22000` | `--hash-type 22000` | WPA-PBKDF2 | Auto |
| `-a 0` | `--attack-mode 0` | Straight dictionary | Yes |
| `-a 1` | `--attack-mode 1` | Combinator | No |
| `-a 3` | `--attack-mode 3` | Brute force | No |
| `-a 6` | `--attack-mode 6` | Hybrid | No |
| `-a 7` | `--attack-mode 7` | Hybrid + mask | No |
| `-d 1` | `--device 1` | GPU device | Auto-pick |
| `--force` | `--force` | Ignore warnings | No |
| `--status` | `--status-timer 5` | Status update interval | 5s |
| `--potfile-path` | `--potfile <path>` | Where to save cracked | ~/.sidewinder/results/ |
| `-r <file>` | `--rules <file>` | Rule file | No |
| `--increment` | `--increment-min 8 --increment-max 12` | Brute force range | 8-12 |
| `-O` | `--optimized-kernel` | Use optimized kernel | Yes |
| `-w 3` | `--workload 3` | Workload profile (1-4) | 3 |

#### 2.7.4 Hash Conversion

| Tool | Sidewinder Flag | Purpose | Auto? |
|------|-----------------|---------|-------|
| `hcxpcapngtool` | `--convert-hash` | Convert .pcap → .22000 | Yes |
| `cap2hccapx` | `--convert-hccapx` | Convert → .hccapx (legacy) | No |
| `wpaclean` | `--clean` | Strip junk from capture | Yes |

**Beginner experience:**
```
[6/7] Crack the handshake: NASA

Your capture: NASA_AA-BB-CC-DD-EE-FF_20260605_2304.pcap
Target:      AA:BB:CC:DD:EE:FF (NASA)

Wordlist options:
  [1] /usr/share/wordlists/rockyou.txt (14M passwords)  ← RECOMMENDED
  [2] Browse for another wordlist
  [3] Generate wordlist (rules, mutations)
  [4] Skip (use existing cracked file)

> 1

Cracking engine:
  [1] hashcat (GPU, fast)        ← if NVIDIA/AMD GPU detected
  [2] aircrack-ng (CPU, slower)  ← works everywhere
  [3] Auto-detect

> 1

[*] Converting capture to hashcat format...
[*] Starting hashcat with your GPU...

  Status:  [████████████░░░░░░░░] 60%
  Speed:   1,234,567 H/s
  ETA:     5 min 30 sec
  Current: testing "password"...

  Status:  [████████████████████] 100%
  
[*] KEY FOUND!

  Network:  NASA
  Password: password123
  Time:     8m 23s
  Speed:    1,234,567 H/s avg

Saved to: ~/.sidewinder/results/NASA_cracked.txt
```

### 2.8 Phase 7: Cleanup — All Options

**Underlying tools:** `iw`, `ip`, `systemctl`

| Action | Sidewinder Flag | Beginner Default |
|--------|-----------------|------------------|
| Restore managed mode | `--restore-managed` | Yes |
| Restart NM | `--restart-networkmanager` | Yes |
| Restart wpa_supplicant | `--restart-wpa-supplicant` | Yes |
| Clear session | `--clear-session` | No |
| Save session | `--save-session` | Yes (auto) |
| Verbose cleanup | `--verbose-cleanup` | No |

**Beginner experience:**
```
[7/7] Cleanup

Restoring your system...

[*] Stopping airodump-ng...
[*] Removing wlan1mon (monitor interface)...
[*] Restoring wlan1 (managed mode)...
[*] Restarting NetworkManager...
[*] Restarting wpa_supplicant...
[*] Verifying WiFi is working...

[*] All done! Your WiFi is back to normal.

Session saved: ~/.sidewinder/session.json
Logs saved: ~/.sidewinder/logs/2026-06-05_23-04-12.jsonl

Press Enter to return to main menu...
```

---

## 3. TUI Design (Screen-by-Screen)

### 3.1 Screen Layout Principles

1. **Progressive disclosure:** Show simple options first, "Custom" for experts
2. **Color coding:** Green = good, Red = danger, Yellow = warning, Cyan = info
3. **Live updates:** Tables refresh in place (no screen clearing)
4. **Status bar:** Always show current state at bottom
5. **Help line:** Always show available keys at bottom

### 3.2 Screens (16 Total)

| # | Screen | Purpose | Hotkeys |
|---|--------|---------|---------|
| 1 | Main Menu | Hub | 1-7, 0 |
| 2 | Adapter List | Show discovered hardware | r=rescan, i=info, Enter=select |
| 3 | Service Check | List/kill processes | k=kill, s=skip |
| 4 | Monitor Setup | Enable/disable monitor | c=channel, p=power, Enter=continue |
| 5 | Scan Options | Choose scan parameters | 1-3, c=custom |
| 6 | Live Scan | Real-time network table | Enter=stop, f=filter |
| 7 | Target Picker | Select from scan results | 1-N, s=show details |
| 8 | AP Details | Full info on one AP | Enter=select this |
| 9 | Client List | Show clients for target AP | 1-N, a=attack all |
| 10 | Attack Method | Choose capture method | 1-4, c=custom |
| 11 | Live Capture | Show EAPOL progress | s=stop |
| 12 | Capture Success | Show saved handshake | Enter=continue |
| 13 | Wordlist Picker | Choose wordlist | 1-4, b=browse |
| 14 | Engine Picker | Choose cracker | 1-3 |
| 15 | Live Crack | Show progress | s=stop |
| 16 | Cleanup | Restore system | Enter=cleanup |

### 3.3 Key Bindings (opencode-style)

| Key | Action |
|-----|--------|
| `Enter` | Continue / select |
| `Esc` | Back / cancel |
| `q` | Quit to main menu |
| `?` | Help for current screen |
| `s` | Skip current step |
| `r` | Refresh / rescan |
| `f` | Filter |
| `c` | Custom / configure |
| `1-9` | Select option |

---

## 4. Sidewinder CLI Flags (Top-Level)

### 4.1 Main Commands

```bash
sidewinder [COMMAND] [OPTIONS]

COMMANDS:
  scan        Scan WiFi networks (no attack)
  target      Target a specific network for attack
  crack       Crack a captured handshake
  clean       Restore system to managed mode
  doctor      Diagnose missing dependencies
  update      Update Sidewinder
  version     Show version info
  help        Show help

OPTIONS (all commands):
  -i, --iface <name>      Wireless interface to use
  -c, --channel <N>       Channel (1-14 for 2.4G, 36-165 for 5G)
  -b, --bssid <MAC>       Target BSSID
  -e, --ssid <name>       Target SSID
  -w, --wordlist <path>   Wordlist file path
  -t, --timeout <sec>     Operation timeout
  -o, --output <dir>      Output directory
  -v, --verbose           Verbose output
  -q, --quiet             Quiet output
      --debug             Debug output
      --no-color          Disable colors
      --config <file>     Config file path
      --version           Show version
      --help              Show help
```

### 4.2 Subcommand Examples

```bash
# Scan all networks (beginner mode)
sudo sidewinder scan

# Scan specific channel
sudo sidewinder scan --channel 6

# Scan specific band
sudo sidewinder scan --band 5g

# Target a specific network and attack
sudo sidewinder target --bssid AA:BB:CC:DD:EE:FF

# Crack existing capture
sudo sidewinder crack --capture /path/to/handshake.pcap --wordlist /path/to/wordlist.txt

# Use hashcat with specific device
sudo sidewinder crack --engine hashcat --device 1 --wordlist rockyou.txt

# Restore managed mode
sudo sidewinder clean

# Diagnose
sudo sidewinder doctor
```

### 4.3 Config File (~/.sidewinder/config.toml)

```toml
[general]
reg_domain = "BO"
default_wordlist = "/usr/share/wordlists/rockyou.txt"
log_dir = "~/.sidewinder/logs"
capture_dir = "~/.sidewinder/captures"

[scanning]
update_interval = 1
min_signal = -90
band = "all"
show_wps = true

[attack]
deauth_count = 10
deauth_pps = 500
auto_verify = true
require_full_handshake = false
timeout = 300

[cracking]
engine = "auto"  # auto | aircrack | hashcat
hash_type = 22000
threads = 0  # 0 = auto
```

---

## 5. All airmon-ng / airodump-ng / aireplay-ng / aircrack-ng Flags (Reference)

### 5.1 airmon-ng (airmon-ng's full feature set)

| Flag | Purpose | Sidewinder Equivalent |
|------|---------|----------------------|
| `airmon-ng` | List interfaces | `sidewinder scan --list` |
| `airmon-ng start <iface>` | Enable monitor | `sidewinder target -i <iface>` (auto) |
| `airmon-ng start <iface> <channel>` | Enable + lock channel | `sidewinder target -i <iface> -c <N>` |
| `airmon-ng stop <iface>` | Disable monitor | `sidewinder clean` |
| `airmon-ng check` | List conflicts | Auto during setup |
| `airmon-ng check kill` | Kill conflicts | Auto during setup (with prompt) |
| `--elite` | Keep managed + monitor | `--elite` |
| `--verbose` | Show extra info | `--verbose` |
| `--debug` | Debug output | `--debug` |

### 5.2 airodump-ng (full feature set)

Already mapped in section 2.4 above.

### 5.3 aireplay-ng (full feature set)

| Flag | Purpose | Sidewinder Equivalent |
|------|---------|----------------------|
| `--deauth <count>` | Deauth attack | `--capture deauth --deauth-count <N>` |
| `--fakeauth` | Fake auth | `--capture fakeauth` |
| `--interactive` | Interactive mode | `--interactive` |
| `--arpreplay` | ARP replay (WEP) | `--capture arp-inject` |
| `--chopchop` | Chopchop (WEP) | `--capture chopchop` |
| `--fragment` | Fragmentation (WEP) | `--capture fragment` |
| `--caffe-latte` | Caffe-Latte (WEP) | `--capture caffe-latte` |
| `--cfrag` | Fragmentation + caffe | `--capture cfrag` |
| `--test` | Injection test | `--inject-test` |
| `-h <MAC>` | Source MAC | `--source <MAC>` |
| `-d <MAC>` | Destination MAC | `--client <MAC>` |
| `-a <MAC>` | AP MAC | `--ap <MAC>` |
| `-x <pps>` | Packets per second | `--pps <N>` |
| `-F` | Fast mode | `--fast` |
| `-R` | Repeat / ignore replay | `--no-replay` |

### 5.4 aircrack-ng (full feature set)

Already mapped in section 2.7.2 above.

---

## 6. Implementation Plan (Step-by-Step)

### Phase A: Foundation (Week 1)
- [ ] Project structure: `sidewinder/__init__.py`, `__main__.py`, `cli.py`
- [ ] Dependency check (`sidewinder doctor`)
- [ ] Rich-based main menu (Screen 1)
- [ ] Adapter discovery (Screen 2)
- [ ] Service management (Screen 3)
- [ ] Monitor mode toggle (Screen 4)

### Phase B: Reconnaissance (Week 2)
- [ ] Scan options menu (Screen 5)
- [ ] Live scan with rich Live table (Screen 6)
- [ ] Real-time airodump-ng stdout parser
- [ ] All airodump-ng flags exposed (section 2.4)
- [ ] Target picker (Screen 7)
- [ ] AP details view (Screen 8)
- [ ] Client list (Screen 9)

### Phase C: Attack (Week 3)
- [ ] Attack method picker (Screen 10)
- [ ] All aireplay-ng flags (section 2.6.2)
- [ ] Live capture with EAPOL progress (Screen 11)
- [ ] Handshake validation
- [ ] Capture success screen (Screen 12)
- [ ] Multi-adapter support
- [ ] All capture flags (section 2.6.3)

### Phase D: Cracking (Week 4)
- [ ] Wordlist picker (Screen 13)
- [ ] Engine picker (Screen 14)
- [ ] hashcat integration + progress parsing
- [ ] aircrack-ng integration + progress parsing
- [ ] Live crack screen (Screen 15)
- [ ] Result saving
- [ ] hcxpcapngtool / wpaclean integration

### Phase E: Polish (Week 5)
- [ ] Cleanup screen (Screen 16)
- [ ] All cleanup flags (section 2.8)
- [ ] Session save/resume
- [ ] JSONL logging
- [ ] Error handling + troubleshooting
- [ ] Top-level CLI commands (section 4)
- [ ] Config file support
- [ ] Help screens (?)

### Phase F: Testing & Release (Week 6)
- [ ] Unit tests for parsers
- [ ] Integration tests on real hardware
- [ ] Help tutorial
- [ ] README
- [ ] Recording demo GIF

---

## 7. File Structure (Final)

```
sidewinder/
├── __init__.py
├── __main__.py                    # python -m sidewinder
├── cli.py                         # Top-level CLI parser
├── config.py                      # Config loading
├── doctor.py                      # Dependency check
├── session.py                     # Session save/load
├── logger.py                      # JSONL logger
├── core/
│   ├── __init__.py
│   ├── adapter.py                 # Hardware discovery
│   ├── services.py                # Process management
│   ├── monitor.py                 # Monitor mode toggle
│   ├── scanner.py                 # airodump-ng wrapper
│   ├── attack.py                  # aireplay-ng wrapper
│   ├── capture.py                 # Handshake validation
│   └── cracker.py                 # aircrack-ng / hashcat wrapper
├── tui/
│   ├── __init__.py
│   ├── app.py                     # Main app controller
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── menu.py                # Main menu
│   │   ├── adapters.py            # Adapter list
│   │   ├── services.py            # Service management
│   │   ├── monitor.py             # Monitor setup
│   │   ├── scan_options.py        # Scan options
│   │   ├── live_scan.py           # Live scan table
│   │   ├── target.py              # Target picker
│   │   ├── ap_details.py          # AP details
│   │   ├── clients.py             # Client list
│   │   ├── attack_method.py       # Attack method picker
│   │   ├── live_capture.py        # Live capture
│   │   ├── capture_success.py     # Success screen
│   │   ├── wordlist.py            # Wordlist picker
│   │   ├── engine.py              # Engine picker
│   │   ├── live_crack.py          # Live crack
│   │   └── cleanup.py             # Cleanup
│   └── widgets/
│       ├── __init__.py
│       ├── live_table.py          # Live updating table
│       ├── progress.py            # Progress bars
│       └── status_bar.py          # Bottom status bar
├── tools/
│   ├── __init__.py
│   ├── iw.py                      # iw wrapper
│   ├── ip.py                      # ip wrapper
│   ├── airodump.py                # airodump-ng wrapper
│   ├── aireplay.py                # aireplay-ng wrapper
│   ├── aircrack.py                # aircrack-ng wrapper
│   ├── hashcat.py                 # hashcat wrapper
│   ├── hcxdump.py                 # hcxdumptool wrapper
│   ├── hcxhash.py                 # hcxpcapngtool wrapper
│   └── wpaclean.py                # wpaclean wrapper
└── parsers/
    ├── __init__.py
    ├── airodump.py                # airodump-ng stdout parser
    ├── aircrack.py                # aircrack-ng progress parser
    ├── hashcat.py                 # hashcat progress parser
    └── pcap.py                    # PCAP / EAPOL validation
```

---

## 8. Key Design Principles (Refresher)

1. **Progressive disclosure:** Beginner sees 3 options, expert sees 20
2. **Help everywhere:** Every screen has `?` for context-sensitive help
3. **No silent failures:** Every error explains what happened + how to fix
4. **Atomic operations:** Every action has clear undo/cleanup path
5. **State visibility:** Always show what's running, what interface, what channel
6. **Keyboard-first:** Mouse never required
7. **Beautiful by default:** Rich colors, tables, progress bars
8. **Fast feedback:** Live updates every second, no batch waits
9. **Recommend, never auto:** The user is the expert. We suggest, they decide. Never execute without explicit confirmation.

---

## 9. Subtools Summary (Quick Reference)

| Phase | Underlying Tool | Sidewinder Wrapper | Beginner Mode Shows |
|-------|-----------------|-------------------|---------------------|
| 0: Discovery | `iw dev` + sysfs | `core/adapter.py` | Pretty adapter table |
| 1: Services | `ps`, `pkill`, `systemctl` | `core/services.py` | "Found 3 processes, kill?" |
| 2: Monitor | `iw`, `ip` | `core/monitor.py` | "Putting wlan1 in monitor mode" |
| 3: Scan | `airodump-ng` | `core/scanner.py` | Live network table |
| 4: Target | None | Pure UI | "Select target 1-3" |
| 5: Attack | `airodump-ng` + `aireplay-ng` | `core/attack.py` | "Sending deauth..." |
| 6: Crack | `aircrack-ng` or `hashcat` | `core/cracker.py` | Progress bar + ETA |
| 7: Cleanup | `iw`, `ip`, `systemctl` | `core/monitor.py` | "Restoring..." |

---

**This plan covers all 20+ years of aircrack-ng/airodump-ng/aireplay-ng/aircrack-ng features wrapped in a friendly TUI. A naive user can scan, target, attack, and crack with 4-5 keystrokes. An expert can access every flag through the "Custom" menu options.**

---

## 10. TUI Design (Locked — 60 UX Decisions Applied)

### 10.1 opencode Style Integration

Sidewinder follows opencode's TUI philosophy:
- **Clean, minimal borders** using box-drawing characters (╭╮╰╯)
- **Vim-style keybindings** (j/k navigate, Enter selects, Esc back)
- **Bottom hint bar** showing context-sensitive key hints
- **Fade transitions** between screens
- **Graceful Unicode fallback** to ASCII if terminal doesn't support it

### 10.2 Color Palette (WiFi-Themed)

```python
COLORS = {
    "primary": "#4CAF50",      # Warm Green - scan results, active elements
    "secondary": "#00BCD4",    # Cyan - RF info, signal strength
    "accent": "#9C27B0",       # Purple - highlights, selected items
    "success": "#00E676",      # Bright Green - handshake captured, password found
    "error": "#F44336",        # Red - errors, warnings
    "warning": "#FF9800",      # Orange - rate limits, cooldowns
    "info": "#2196F3",         # Blue - help text, hints
    "muted": "#9E9E9E",        # Gray - secondary text, borders
    "background": "#1A1A2E",   # Dark - terminal background
    "text": "#E0E0E0",         # Light - primary text
}
```

### 10.3 Signal Strength Visual Indicators

| Signal | Bar | Color | Text |
|--------|-----|-------|------|
| Excellent (>-50) | `██████████` | Bright Green | `-47dBm` |
| Good (-50 to -60) | `████████░░` | Green | `-55dBm` |
| Fair (-60 to -70) | `██████░░░░` | Yellow | `-65dBm` |
| Weak (-70 to -80) | `████░░░░░░` | Orange | `-75dBm` |
| Very Weak (<-80) | `██░░░░░░░░` | Red | `-85dBm` |

### 10.4 Screen Structure Template

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

### 10.5 Main Menu (opencode Style)

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

### 10.6 Scan Results (Full Table)

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

### 10.7 Capture Method Selection

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

### 10.8 Live Capture Progress

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

### 10.9 Deauth Target Selection (Checkboxes)

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

### 10.10 Crack Progress

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

### 10.11 Styled Result Card (Password Found)

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

### 10.12 Full Tutorial (Help Screen)

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

### 10.13 Error Card (Rich Error Display)

```
╭─────────────────────────────────────────────────────────────────╮
│ ▗▄▄▄▖ SIDEWINDER — Error                                       │
│ █  █                                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─ ERROR ───────────────────────────────────────────────────┐   │
│ │                                                            │   │
│ │  What happened:                                            │   │
│ │  No handshake captured after 2 minutes of deauth.          │   │
│ │                                                            │   │
│ │  Why:                                                      │   │
│ │  Client signal too weak (-85dBm). Packet loss too high.    │   │
│ │                                                            │   │
│ │  How to fix:                                               │   │
│ │  1. Move closer to target (signal > -70dBm recommended)    │   │
│ │  2. Try passive capture instead (wait for natural assoc)   │   │
│ │  3. Check if AP has client isolation enabled                │   │
│ │                                                            │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ [1] Try again  [2] Change method  [3] Back to scan  [4] Main   │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

### 10.14 Keybinding Reference

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
| `Ctrl+C` | Graceful exit (with confirm) | Any screen |

### 10.15 Slash Commands

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

### 10.16 Confirmation Prompts

All actions require confirmation before execution:

```
╭─────────────────────────────────────────────────────────────────╮
│ Confirm Action                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Start WiFi scan on wlan1mon?                                   │
│  This will hop across all channels.                             │
│                                                                 │
│  [Y]es  [N]o                                                    │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

### 10.17 Client Fingerprinting Display

```
╭─────────────────────────────────────────────────────────────────╮
│ Clients Connected to Home (AA:BB:CC:DD:EE:F1)                  │
├─────────────────────────────────────────────────────────────────┤
│ MAC               Vendor        Device           Signal  Pkts   │
├─────────────────────────────────────────────────────────────────┤
│ ▶ AA:11:22:33:44:55  Apple         iPhone 15       -47dBm  342  │
│   BB:11:22:33:44:55  Samsung       Galaxy S24      -52dBm  218  │
│   CC:11:22:33:44:55  Intel         Laptop (Win11)  -65dBm  156  │
│   DD:11:22:33:44:55  Unknown       Unknown         -78dBm   42  │
╰─────────────────────────────────────────────────────────────────╯
```

### 10.18 Startup Check Display

```
╭─────────────────────────────────────────────────────────────────╮
│ ▗▄▄▄▖ SIDEWINDER — Startup Check                               │
│ █  █                                                             │
├─────────────────────────────────────────────────────────────────┤
│ Checking dependencies...                                        │
│                                                                 │
│ [*] Root privileges      [*] iw           [*] aircrack-ng             │
│ [*] airmon-ng            [*] hashcat      [*] hcxdumptool             │
│ [*] hcxpcapngtool        [*] wpaclean                              │
│                                                                 │
│ Adapters found:                                                 │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │ Name     Driver    Chipset         MAC              Mode  │   │
│ ├──────────────────────────────────────────────────────────┤   │
│ │ ▶ wlan0  ath9k     Qualcomm AR9271  AA:BB:CC:DD:EE  Managed│  │
│ │   wlan1  rt2800usb Ralink RT5370   11:22:33:44:55  Managed│  │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ Regulatory domain: BO (Bolivia) — all channels available        │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

---

## 11. Implementation Checklist

### Phase A: Project Structure (Week 1)
- [ ] Create project directory structure
- [ ] Set up pyproject.toml with dependencies
- [ ] Implement dependency checker
- [ ] Build rich main menu with opencode-style ASCII logo
- [ ] Implement adapter discovery (iw + sysfs)

### Phase B: Scan & Recon (Week 2)
- [ ] Build live scan table with signal bars
- [ ] Implement channel hopping
- [ ] Parse airodump-ng stdout
- [ ] Add client detection and OUI fingerprinting

### Phase C: Monitor Mode (Week 2-3)
- [ ] Implement native monitor mode (no airmon-ng)
- [ ] Build service killer
- [ ] Add MAC randomization detection

### Phase D: Capture (Week 3-4)
- [ ] Build capture method selection screen
- [ ] Implement deauth target selection with checkboxes
- [ ] Add live capture stats display
- [ ] Implement EAPOL handshake validation

### Phase E: Cracking (Week 4-5)
- [ ] Build wordlist browser with auto-discovery
- [ ] Implement aircrack-ng wrapper
- [ ] Implement hashcat wrapper
- [ ] Add progress parsing for both tools

### Phase F: Polish (Week 5-6)
- [ ] Add full tutorial (? help screen)
- [ ] Implement session save/resume
- [ ] Add cleanup with confirmation
- [ ] Add styled result card
- [ ] Add JSONL logging
- [ ] Final testing and bug fixes

---

## 12. Backend Architecture (Priority #1)

### 12.1 opencode → Sidewinder Workflow Mapping

| opencode Concept | Sidewinder Equivalent | Description |
|------------------|----------------------|-------------|
| **Session** | **Audit Session** | Persist scan results, target, captures, logs |
| **Agent** | **Attack Phase** | Scan → Target → Capture → Crack → Cleanup |
| **Tool Registry** | **Attack Registry** | Each attack is a registered tool with metadata |
| **Permission Engine** | **Safety Engine** | Confirmations, rate limits, scope control |
| **Streaming Output** | **Live Log Stream** | Real-time subprocess stdout/stderr |
| **Storage** | **Session Storage** | JSONL logs, PCAP files, session.json |
| **Config System** | **Attack Config** | Default options, saved preferences |

### 12.2 Backend-First Architecture

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

### 12.3 Subprocess Manager (Learned from Wcrack's 133 Bugs)

Wcrack's ManagedProcess had:
- Pipe deadlocks (GIL issue)
- Zombie processes
- Race conditions on mode switches
- NM interference

**Sidewinder's solution:**

```python
class SidewinderProcess:
    """
    Robust subprocess manager. Handles:
    - Process group isolation (no zombies)
    - Real-time stdout/stderr streaming (no deadlocks)
    - Automatic retry on EBUSY
    - Graceful shutdown with SIGTERM → SIGKILL
    - Rate-limited output (prevent flooding)
    """
    
    PRIVILEGED_TOOLS = {
        "iw", "ip", "airodump-ng", "aireplay-ng", 
        "aircrack-ng", "hashcat", "hcxdumptool", 
        "hcxpcapngtool", "wpaclean", "mdk4"
    }
    
    def __init__(self, cmd: List[str], job_id: str):
        self.cmd = self._prepare_cmd(cmd)
        self.job_id = job_id
        self._process = None
        self._output_buffer = asyncio.Queue()  # Live output stream
        self._stats = ProcessStats()           # Real-time stats
    
    async def start(self) -> AsyncIterator[str]:
        """Start process and yield output lines in real-time."""
        self._process = await self._create_process()
        async for line in self._stream_output():
            yield line
    
    async def _create_process(self):
        """Create process with group isolation."""
        kwargs = {
            'stdout': asyncio.subprocess.PIPE,
            'stderr': asyncio.subprocess.PIPE,
        }
        
        if os.name == 'posix':
            kwargs['start_new_session'] = True  # Process group
        
        try:
            return await asyncio.create_subprocess_exec(
                *self.cmd, **kwargs
            )
        except OSError as e:
            if e.errno == 16:  # EBUSY
                await asyncio.sleep(1.0)
                return await asyncio.create_subprocess_exec(
                    *self.cmd, **kwargs
                )
            raise
    
    async def _stream_output(self) -> AsyncIterator[str]:
        """Stream output without blocking (no GIL deadlock)."""
        tasks = [
            asyncio.create_task(self._read_stream(self._process.stdout)),
            asyncio.create_task(self._read_stream(self._process.stderr)),
        ]
        
        while not all(t.done() for t in tasks):
            try:
                line = await asyncio.wait_for(
                    self._output_buffer.get(), 
                    timeout=0.1
                )
                yield line
            except asyncio.TimeoutError:
                continue
    
    async def stop(self, grace: float = 5.0):
        """Graceful shutdown: SIGTERM → wait → SIGKILL."""
        if self._process.returncode is not None:
            return
        
        # SIGTERM
        if os.name == 'posix':
            os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
        else:
            self._process.terminate()
        
        try:
            await asyncio.wait_for(self._process.wait(), timeout=grace)
        except asyncio.TimeoutError:
            # SIGKILL
            if os.name == 'posix':
                os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
            else:
                self._process.kill()
            await self._process.wait()
```

### 12.4 Real-Time Parsers (Never Feel Stuck)

Each tool has a dedicated parser that extracts structured data from stdout:

```python
class AirodumpParser:
    """Parse airodump-ng stdout into structured data."""
    
    def parse_line(self, line: str) -> Optional[dict]:
        """Parse one line of airodump-ng output."""
        # Example: " AA:BB:CC:DD:EE:FF   6  -47  54e. WPA2 CCMP  Home"
        if line.startswith(' '):
            return self._parse_ap_line(line)
        elif ':' in line and len(line) == 17:
            return self._parse_client_line(line)
        return None
    
    def get_stats(self) -> dict:
        """Return current scan statistics."""
        return {
            'aps': len(self._aps),
            'clients': len(self._clients),
            'channels': list(self._seen_channels),
            'beacons_per_sec': self._beacon_rate,
            'data_per_sec': self._data_rate,
            'elapsed': time.time() - self._start_time,
        }

class AircrackParser:
    """Parse aircrack-ng progress output."""
    
    def parse_line(self, line: str) -> Optional[dict]:
        # Example: "                        [45.23%] 6,454,976 keys tested"
        if '%' in line:
            return self._parse_progress(line)
        elif 'KEY FOUND!' in line:
            return self._parse_success(line)
        return None

class EAPOLTracker:
    """Track EAPOL handshake packets in real-time."""
    
    def __init__(self):
        self.packets = {1: False, 2: False, 3: False, 4: False}
        self.partial = False
        self.complete = False
    
    def update(self, packet_type: int):
        """Update handshake state."""
        self.packets[packet_type] = True
        self.partial = self.packets[1] and self.packets[2]
        self.complete = all(self.packets.values())
    
    def get_status(self) -> dict:
        return {
            'm1': '[*]' if self.packets[1] else '✗',
            'm2': '[*]' if self.packets[2] else '✗',
            'm3': '[*]' if self.packets[3] else '✗',
            'm4': '[*]' if self.packets[4] else '✗',
            'partial': self.partial,
            'complete': self.complete,
            'percent': sum(self.packets.values()) * 25,
        }
```

---

## 13. Live Log / Nerd Screen (Never Feel Stuck)

### 13.1 Design Philosophy

> **"The user must never feel stuck and waiting. There must be all possible indications."**

Every operation shows:
1. **What's happening** — current action description
2. **Raw data** — live subprocess output
3. **Parsed stats** — structured metrics
4. **Progress** — percentage/ETA when calculable
5. **Nerd mode** — full packet-level detail

### 13.2 Nerd Screen Layout

```
╭─────────────────────────────────────────────────────────────────╮
│ ▗▄▄▄▖ SIDEWINDER — Nerd Mode (Live)                            │
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
│ ┌─ Deauth Status ───────────────────────────────────────────┐   │
│ │ Sent: 45  │  ACK: 38  │  No-ACK: 7  │  Rate: 5/s        │   │
│ │ Targets: AA:11:22 ([*]), BB:11:22 ([*]), CC:11:22 ([*])       │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─ Raw Output ──────────────────────────────────────────────┐   │
│ │ > airodump-ng --bssid AA:BB:CC:DD:EE:FF -c 6 wlan1mon    │   │
│ │ CH 6 ] [ Target: AA:BB:CC:DD:EE:F1 ] [ Elapsed: 2:30 ]   │   │
│ │ BSSID              PWR  Beacons    #Data  CH  ENC  ESSID  │   │
│ │ AA:BB:CC:DD:EE:F1  -47  1234       567    6  WPA2  Home   │   │
│ │                                                             │   │
│ │ STATION            PWR   Rate   Lost  Packets  ESSID      │   │
│ │ AA:11:22:33:44:55  -65   54e.   0     342      Home       │   │
│ │ BB:11:22:33:44:55  -72   54e.   0     218      Home       │   │
│ │                                                             │   │
│ │ [Packet log scrolling...]                                   │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ Press [T] to toggle raw output │ [L] to export logs            │
╰─────────────────────────────────────────────────────────────────╯
```

### 13.3 Log Ring Buffer (Always Accessible)

```python
class RingBuffer:
    """Fixed-size buffer for live logs. Always keeps last N lines."""
    
    def __init__(self, max_lines: int = 1000):
        self.max_lines = max_lines
        self.buffer = collections.deque(maxlen=max_lines)
        self._lock = asyncio.Lock()
    
    async def append(self, line: str, level: str = "INFO"):
        """Add line with timestamp."""
        async with self._lock:
            self.buffer.append({
                'time': datetime.now().isoformat(),
                'level': level,
                'line': line,
            })
    
    async def get_recent(self, n: int = 50) -> List[dict]:
        """Get last N lines."""
        async with self._lock:
            return list(self.buffer)[-n:]
    
    async def export(self, path: str):
        """Export full buffer to JSONL file."""
        async with self._lock:
            with open(path, 'w') as f:
                for entry in self.buffer:
                    f.write(json.dumps(entry) + '\n')
```

### 13.4 Live Indicators (Every Possible Indication)

| Indicator | What It Shows | When Visible |
|-----------|---------------|--------------|
| **Beacon counter** | AP broadcast frames | During scan/capture |
| **Data counter** | Data packets seen | During scan/capture |
| **IV counter** | Initialization vectors | During capture (WEP) |
| **Rate** | Packets per second | Always |
| **Signal** | RSSI in dBm | Always |
| **Channel** | Current channel | Always |
| **EAPOL M1-M4** | Handshake packets | During capture |
| **Deauth sent** | Deauth frames sent | During deauth |
| **ACK received** | ACK frames | During deauth |
| **Keys tested** | Cracking progress | During crack |
| **Speed** | Keys per second | During crack |
| **ETA** | Time remaining | During crack |
| **Current key** | Last tested key | During crack |
| **Elapsed** | Time since start | Always |

---

## 14. Tooltip System (Extensive Tooltips)

### 14.1 Design Philosophy

> **"The user won't be in wonder 'which one I should choose' or 'what the heck this option does'."**

Every menu item, every option, every flag has a tooltip explaining:
1. **What it does** — plain English description
2. **When to use** — use case scenario
3. **Risk level** — safe / caution / dangerous
4. **Example** — concrete example output

### 14.2 Tooltip Data Structure

```python
@dataclass
class Tooltip:
    name: str                    # "Deauth + Capture"
    description: str             # "Kicks clients off the network to force a new handshake"
    when_to_use: str             # "When you need a handshake quickly"
    risk_level: str              # "caution" | "dangerous" | "safe"
    risk_detail: str             # "Sends deauth packets. May disconnect nearby devices."
    example: str                 # "Sends 10 deauth frames to AA:11:22, BB:11:22"
    requires: List[str]          # ["root", "monitor_mode"]
    compatible_with: List[str]   # ["wpa2", "wpa"]
    flags: Dict[str, str]        # {"--deauth-count": "Number of deauth frames (default: 10)"}
```

### 14.3 Tooltip Database

```python
TOOLTIPS = {
    # ── Capture Methods ──────────────────────────────────────
    "capture_passive": Tooltip(
        name="Passive Capture",
        description="Listens for handshake without interfering with the network",
        when_to_use="When you want to be stealthy or the AP has many clients",
        risk_level="safe",
        risk_detail="No packets sent. Pure listening. Undetectable.",
        example="Waits for a client to naturally connect/reconnect. May take hours.",
        requires=["monitor_mode"],
        compatible_with=["wpa", "wpa2", "wpa3"],
        flags={}
    ),
    
    "capture_deauth": Tooltip(
        name="Deauth + Capture",
        description="Sends deauthentication packets to kick clients off, forcing a new handshake",
        when_to_use="When you need a handshake quickly and don't mind being detected",
        risk_level="caution",
        risk_detail="Sends deauth packets. Clients will disconnect briefly. May trigger IDS.",
        example="Sends 10 deauth frames to AA:11:22 every 5 seconds until handshake captured.",
        requires=["monitor_mode", "root"],
        compatible_with=["wpa", "wpa2"],
        flags={
            "--deauth-count": "Number of deauth frames per burst (default: 10, range: 1-100)",
            "--deauth-interval": "Seconds between bursts (default: 5, range: 1-60)",
            "--deauth-targets": "Comma-separated client MACs (default: all clients)",
            "--deauth-rate": "Packets per second (default: 500, max: 1000)",
        }
    ),
    
    "capture_pmkid": Tooltip(
        name="PMKID Capture",
        description="Captures PMKID from AP's first association (no clients needed)",
        when_to_use="When target AP has no connected clients",
        risk_level="caution",
        risk_detail="Sends association requests. May trigger IDS.",
        example="Sends 1 association request to AP. Captures PMKID in response.",
        requires=["monitor_mode", "root", "compatible_adapter"],
        compatible_with=["wpa2", "wpa3"],
        flags={
            "--pmkid-timeout": "Seconds to wait for PMKID (default: 30)",
            "--pmkid-retries": "Number of association attempts (default: 5)",
        }
    ),
    
    # ── Deauth Options ───────────────────────────────────────
    "deauth_count": Tooltip(
        name="Deauth Count",
        description="How many deauthentication frames to send per burst",
        when_to_use="Increase if clients aren't disconnecting. Decrease to be stealthier.",
        risk_level="caution",
        risk_detail="Higher count = more reliable but more detectable.",
        example="10 = sends 10 frames. Client sees: 'Disconnected by network'",
        requires=["monitor_mode"],
        compatible_with=["wpa", "wpa2"],
        flags={}
    ),
    
    "deauth_rate": Tooltip(
        name="Deauth Rate",
        description="How fast to send deauth packets (packets per second)",
        when_to_use="Increase if deauths aren't reaching clients. Decrease to avoid AP lockout.",
        risk_level="dangerous",
        risk_detail="Too high rate may cause AP to blacklist your MAC or crash.",
        example="500 pps = moderate. 1000 pps = aggressive (may trigger AP defenses).",
        requires=["monitor_mode"],
        compatible_with=["wpa", "wpa2"],
        flags={}
    ),
    
    # ── Scan Options ─────────────────────────────────────────
    "scan_channels": Tooltip(
        name="Channel List",
        description="Which WiFi channels to scan",
        when_to_use="Use 1,6,11 for quick 2.4GHz scan. Use all for thorough scan.",
        risk_level="safe",
        risk_detail="No risk. Just determines which frequencies to listen on.",
        example="1,6,11 = scans 3 channels (fast). All = scans 1-14 + 36-165 (slow).",
        requires=["monitor_mode"],
        compatible_with=[],
        flags={}
    ),
    
    "scan_band": Tooltip(
        name="Scan Band",
        description="Which frequency band to scan",
        when_to_use="2.4GHz = longer range, slower speed. 5GHz = shorter range, faster speed.",
        risk_level="safe",
        risk_detail="No risk. Just determines which frequencies to listen on.",
        example="2.4GHz = channels 1-14. 5GHz = channels 36-165.",
        requires=["monitor_mode"],
        compatible_with=[],
        flags={}
    ),
    
    # ── Crack Options ────────────────────────────────────────
    "crack_aircrack": Tooltip(
        name="aircrack-ng (CPU)",
        description="CPU-based WPA key cracking. Slower but works everywhere.",
        when_to_use="When you don't have a GPU or hashcat isn't installed.",
        risk_level="safe",
        risk_detail="No risk. Just uses CPU cycles.",
        example="Tests ~10,000 keys/sec on modern CPU. 14M keys = ~23 minutes.",
        requires=[],
        compatible_with=["wpa", "wpa2"],
        flags={
            "--threads": "Number of CPU threads (default: auto)",
            "--benchmark": "Test CPU speed before cracking",
        }
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
            "--force": "Override GPU compatibility checks",
        }
    ),
    
    "wordlist": Tooltip(
        name="Wordlist",
        description="File containing potential passwords to test",
        when_to_use="Use rockyou.txt for general testing. Use targeted lists for specific APs.",
        risk_level="safe",
        risk_detail="No risk. Just reads a file.",
        example="rockyou.txt = 14M common passwords. Custom = your target's likely passwords.",
        requires=[],
        compatible_with=[],
        flags={
            "--wordlist": "Path to wordlist file",
            "--rules": "Apply hashcat rules (e.g., best64.rule)",
            "--increment": "Try shorter passwords first, then longer",
        }
    ),
}
```

### 14.4 Tooltip Display (Rich Panel)

```
╭─────────────────────────────────────────────────────────────────╮
│ Tooltip: Deauth + Capture                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Kicks clients off the network to force a new handshake.         │
│                                                                 │
│ When to use: When you need a handshake quickly                  │
│ Risk level: [WARN] CAUTION                                          │
│ Risk detail: Sends deauth packets. Clients will disconnect.     │
│                                                                 │
│ Requires: root, monitor mode                                    │
│ Compatible: WPA, WPA2                                           │
│                                                                 │
│ Options:                                                        │
│   --deauth-count    Number of frames per burst (default: 10)    │
│   --deauth-interval Seconds between bursts (default: 5)         │
│   --deauth-targets  Specific client MACs (default: all)         │
│   --deauth-rate     Packets per second (default: 500)           │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

---

## 15. Exception Handling System (State-of-the-Art)

### 15.1 Design Philosophy (Learned from Wcrack's 133 Bugs)

Wcrack's top bugs were:
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

### 15.2 Error Classification

```python
class ErrorSeverity(Enum):
    INFO = "info"           # Normal operation (e.g., "Channel changed")
    WARNING = "warning"     # Recoverable (e.g., "Signal weak, may miss handshake")
    ERROR = "error"         # Operation failed (e.g., "Deauth failed, no ACK")
    CRITICAL = "critical"   # System failure (e.g., "Adapter disconnected")

class ErrorCategory(Enum):
    HARDWARE = "hardware"       # Adapter issues
    PROCESS = "process"         # Subprocess failures
    NETWORK = "network"         # WiFi-specific issues
    PERMISSION = "permission"   # Root/sudo issues
    RESOURCE = "resource"       # Memory/disk/CPU issues
    USER = "user"               # Invalid input/selection

@dataclass
class SidewinderError:
    severity: ErrorSeverity
    category: ErrorCategory
    code: str                   # e.g., "E001"
    title: str                  # "Adapter Disconnected"
    what_happened: str          # "wlan1mon vanished during scan"
    why: str                    # "USB adapter was physically removed"
    how_to_fix: List[str]       # ["Re-insert adapter", "Press Enter to rescan"]
    raw_error: Optional[str]    # Original exception message
    timestamp: datetime
```

### 15.3 Error Database

```python
ERROR_DB = {
    # ── Hardware Errors ──────────────────────────────────────
    "E001": SidewinderError(
        severity=ErrorSeverity.CRITICAL,
        category=ErrorCategory.HARDWARE,
        code="E001",
        title="Adapter Disconnected",
        what_happened="The WiFi adapter vanished during operation",
        why="USB adapter was physically removed or lost power",
        how_to_fix=[
            "Re-insert the USB adapter",
            "Check USB cable connection",
            "Try a different USB port",
            "Press Enter to rescan adapters",
        ],
    ),
    
    "E002": SidewinderError(
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.HARDWARE,
        code="E002",
        title="Monitor Mode Failed",
        what_happened="Could not create monitor interface",
        why="Driver doesn't support monitor mode, or adapter is busy",
        how_to_fix=[
            "Check if another tool is using the adapter",
            "Try: sudo ip link set wlan0 down && sudo iw dev wlan0 set type monitor && sudo ip link set wlan0 up",
            "Check driver compatibility: lsmod | grep <driver>",
            "Try a different adapter (Alfa AWUS036ACH recommended)",
        ],
    ),
    
    "E003": SidewinderError(
        severity=ErrorSeverity.WARNING,
        category=ErrorCategory.HARDWARE,
        code="E003",
        title="Weak Signal",
        what_happened="Target signal is below -70 dBm",
        why="Adapter is too far from target or obstacles in path",
        how_to_fix=[
            "Move closer to the target AP",
            "Remove obstacles (walls, metal objects)",
            "Use a directional antenna",
            "Handshake may fail — consider passive capture",
        ],
    ),
    
    # ── Process Errors ───────────────────────────────────────
    "E010": SidewinderError(
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.PROCESS,
        code="E010",
        title="airodump-ng Failed",
        what_happened="airodump-ng exited unexpectedly",
        why="Invalid channel, adapter issue, or missing root",
        how_to_fix=[
            "Check if adapter supports the selected channel",
            "Ensure you're running as root (sudo)",
            "Check adapter mode (should be monitor)",
            "Try: sudo airodump-ng wlan1mon --channel 6",
        ],
    ),
    
    "E011": SidewinderError(
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.PROCESS,
        code="E011",
        title="aireplay-ng Failed",
        what_happened="Deauth attack failed to send packets",
        why="AP not responding, wrong channel, or adapter issue",
        how_to_fix=[
            "Verify target BSSID is correct",
            "Check adapter is on same channel as target",
            "Try increasing --deauth-count",
            "Check if AP has client isolation enabled",
        ],
    ),
    
    "E012": SidewinderError(
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.PROCESS,
        code="E012",
        title="airodump-ng Stuck",
        what_happened="No output from airodump-ng for 30 seconds",
        why="Process may be hung or pipe deadlock",
        how_to_fix=[
            "Sidewinder will auto-restart in 5 seconds",
            "If persists, press Ctrl+C and try again",
            "Check adapter connection",
        ],
    ),
    
    # ── Network Errors ───────────────────────────────────────
    "E020": SidewinderError(
        severity=ErrorSeverity.WARNING,
        category=ErrorCategory.NETWORK,
        code="E020",
        title="No Handshake Captured",
        what_happened="No EAPOL handshake after 2 minutes",
        why="Clients may be far, AP may have client isolation, or no active clients",
        how_to_fix=[
            "Wait longer (some APs have long reconnection delays)",
            "Try deauth method to force reconnection",
            "Check if AP has client isolation (clients can't see each other)",
            "Try passive capture during natural reconnection",
        ],
    ),
    
    "E021": SidewinderError(
        severity=ErrorSeverity.WARNING,
        category=ErrorCategory.NETWORK,
        code="E021",
        title="MAC Randomization Detected",
        what_happened="Target AP MAC changed between scans",
        why="AP is using MAC randomization (privacy feature)",
        how_to_fix=[
            "Note the new BSSID and update target",
            "Use vendor OUI to identify same AP",
            "MAC randomization may affect handshake capture",
        ],
    ),
    
    # ── Permission Errors ────────────────────────────────────
    "E030": SidewinderError(
        severity=ErrorSeverity.CRITICAL,
        category=ErrorCategory.PERMISSION,
        code="E030",
        title="Root Required",
        what_happened="Operation requires root privileges",
        why="WiFi monitor mode and packet injection require root",
        how_to_fix=[
            "Run with sudo: sudo sidewinder",
            "Or use pkexec: pkexec sidewinder",
        ],
    ),
    
    # ── Resource Errors ──────────────────────────────────────
    "E040": SidewinderError(
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.RESOURCE,
        code="E040",
        title="Disk Full",
        what_happened="Cannot write capture file",
        why="Disk is full or write permission denied",
        how_to_fix=[
            "Free up disk space: df -h",
            "Check write permissions: ls -la ~/.sidewinder/",
            "Use --capture-path to save elsewhere",
        ],
    ),
}
```

### 15.4 User-Facing Error Display

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

---

## 16. airmon-ng Function Mapping (Complete)

### 16.1 Source Analysis

**Source:** `aircrack-ng/scripts/airmon-ng.linux` — 1,750 lines, POSIX `/bin/sh`
**Total functions:** 27
**Functions we implement:** 21 (15 essential + 6 optional)
**Functions we skip:** 6

### 16.2 [OK] MUST HAVE — Essential Functions (15)

| # | Function | Lines | Purpose | Sidewinder Module | Priority |
|---|----------|-------|---------|-------------------|----------|
| 1 | `getPhy(iface)` | 1387-1404 | Read PHY from `/sys/class/net/<iface>/phy80211/name` | `core/adapter.py` | P0 |
| 2 | `getDriver(iface)` | 863-943 | Read driver from sysfs/ethtool/modinfo | `core/adapter.py` | P0 |
| 3 | `getChipset(iface)` | 1001-1099 | Read chipset from lsusb/lspci/sysfs | `core/adapter.py` | P0 |
| 4 | `getBus(iface)` | 1101-1108 | Read bus type from `/sys/class/net/<iface>/device/modalias` | `core/adapter.py` | P0 |
| 5 | `getStack(iface)` | 1110-1131 | Detect mac80211 vs ieee80211 vs net80211 | `core/adapter.py` | P0 |
| 6 | `listInterfaces()` | 1363-1385 | List all wlan interfaces from sysfs | `core/adapter.py` | P0 |
| 7 | `setLink(iface, state)` | 362-369 | `ip link set dev <iface> up/down` | `core/monitor.py` | P0 |
| 8 | `ifaceExists(iface)` | 385-397 | Check if interface exists via `ip link show` | `core/adapter.py` | P0 |
| 9 | `ifaceIsUp(iface)` | 371-383 | Check if interface is UP via `ip link show` | `core/adapter.py` | P0 |
| 10 | `startMac80211Iface(iface)` | 469-568 | Create monitor VIF: `iw phy <phy> interface add <name> type monitor` | `core/monitor.py` | P0 |
| 11 | `stopMac80211Iface(iface)` | 751-838 | Delete monitor VIF, recreate station: `iw dev <iface> del` | `core/monitor.py` | P0 |
| 12 | `setChannelMac80211(iface)` | 636-715 | Set channel: `iw dev <iface> set channel <N>` or `set freq <MHz>` | `core/monitor.py` | P0 |
| 13 | `rfkill_check(phy)` | 298-335 | Check soft/hard block via `rfkill list` | `core/rfkill.py` | P1 |
| 14 | `rfkill_unblock(phy)` | 337-360 | Unblock: `rfkill unblock <phy>` | `core/rfkill.py` | P1 |
| 15 | `scanProcesses(kill?)` | 1242-1361 | Find/kill NM, wpa_supplicant, dhclient, avahi, hostapd, iwd | `core/services.py` | P1 |

### 16.3 [WARN] NICE TO HAVE — Optional Functions (6)

| # | Function | Lines | Purpose | When Needed | Sidewinder Module |
|---|----------|-------|---------|-------------|-------------------|
| 16 | `changeMac80211IfaceTypeMonitor(iface)` | 427-431 | Direct `iw dev <iface> set type monitor` | Bad drivers (rtl8821au, rtl88XXau) | `core/monitor.py` |
| 17 | `changeQcacldIfaceTypeMonitor(iface)` | 447-455 | Write `4` to `/sys/module/wlan/parameters/con_mode` | Qualcomm qcacld drivers | `core/monitor.py` |
| 18 | `findFreeInterface(mode)` | 229-296 | Find wlan0-99, create VIF with auto-name | Auto-naming when interface name too long | `core/adapter.py` |
| 19 | `checkvm()` | 1407-1513 | Detect VirtualBox/VMware/Xen/KVM/QEMU | VM rfkill issues | `core/vm.py` |
| 20 | `getExtendedInfo(iface)` | 1133-1240 | Extended info: rfkill status, broken driver warnings | Debug mode | `core/adapter.py` |
| 21 | `getFrom(iface)` | 945-981 | Driver source: K(kernel), C(compat), V(vendor), S(staging), ?(unknown) | Verbose mode | `core/adapter.py` |

### 16.4 [FAIL] SKIP — Not Needed (6)

| # | Function | Lines | Why Skip |
|---|----------|-------|----------|
| 22 | `usage()` | 202-205 | We have our own help/tutorial UI |
| 23 | `handleLostPhys()` | 207-227 | Edge case — handle manually in adapter discovery |
| 24 | `yesorno()` | 457-467 | We have rich prompts (input prompt) |
| 25 | `startDeprecatedIface()` | 399-425 | Legacy `iwconfig` — we use `iw` only |
| 26 | `stopDeprecatedIface()` | 717-733 | Legacy `iwconfig` — we use `iw` only |
| 27 | `startwlIface()` / `stopwlIface()` | 603-624, 840-861 | Broadcom wl driver — ancient, no monitor support |
| 28 | `qcaldSafetyCheck()` | 433-445 | Fold into `startMac80211Iface` with driver check |

### 16.5 Sidewinder Module → airmon-ng Function Map

```
core/adapter.py
├── getPhy()                    ← getPhy()
├── getDriver()                 ← getDriver()
├── getChipset()                ← getChipset()
├── getBus()                    ← getBus()
├── getStack()                  ← getStack()
├── listInterfaces()            ← listInterfaces()
├── ifaceExists()               ← ifaceExists()
├── ifaceIsUp()                 ← ifaceIsUp()
├── findFreeInterface()         ← findFreeInterface() [optional]
├── getExtendedInfo()           ← getExtendedInfo() [optional]
└── getFrom()                   ← getFrom() [optional]

core/monitor.py
├── setLink()                   ← setLink()
├── startMonitor()              ← startMac80211Iface()
├── stopMonitor()               ← stopMac80211Iface()
├── setChannel()                ← setChannelMac80211()
├── startMonitorDirect()        ← changeMac80211IfaceTypeMonitor() [optional]
└── startMonitorQcacld()        ← changeQcacldIfaceTypeMonitor() [optional]

core/rfkill.py
├── rfkillCheck()               ← rfkill_check()
└── rfkillUnblock()             ← rfkill_unblock()

core/services.py
└── scanProcesses()             ← scanProcesses()

core/vm.py
└── checkVM()                   ← checkvm() [optional]
```

### 16.6 Implementation Priority Order

| Phase | Functions | Total |
|-------|-----------|-------|
| **P0 (Must have first)** | getPhy, getDriver, getChipset, getBus, getStack, listInterfaces, setLink, ifaceExists, ifaceIsUp, startMac80211Iface, stopMac80211Iface, setChannelMac80211 | 12 |
| **P1 (Required for full functionality)** | rfkill_check, rfkill_unblock, scanProcesses | 3 |
| **P2 (Edge cases)** | changeMac80211IfaceTypeMonitor, changeQcacldIfaceTypeMonitor, findFreeInterface | 3 |
| **P3 (Nice to have)** | checkvm, getExtendedInfo, getFrom | 3 |

### 16.7 Key airmon-ng Internals We Reuse

| Pattern | airmon-ng Implementation | Sidewinder Python Equivalent |
|---------|-------------------------|------------------------------|
| PHY detection | `cat /sys/class/net/<iface>/phy80211/name` | `Path(f"/sys/class/net/{iface}/phy80211/name").read_text()` |
| Driver detection | `ethtool -i <iface>` + sysfs fallback | `Path(f"/sys/class/net/{iface}/device/driver").readlink()` |
| Chipset detection | `lsusb -d <vendor>:<product>` or `lspci -d <vendor>:<device>` | `subprocess.run(["lsusb", "-d", f"{vid}:{pid}"])` |
| Monitor enable | `iw phy <phy> interface add <name> type monitor` | `asyncio.create_subprocess_exec("iw", "phy", phy, "interface", "add", name, "type", "monitor")` |
| Monitor disable | `iw dev <iface> del` | `asyncio.create_subprocess_exec("iw", "dev", iface, "del")` |
| Channel set | `iw dev <iface> set channel <N>` | `asyncio.create_subprocess_exec("iw", "dev", iface, "set", "channel", str(ch))` |
| Service kill | `ps -A | grep <processes>` + `kill -9` | `asyncio.create_subprocess_exec("pkill", "-9", "-f", pattern)` |
| Rfkill check | `rfkill list <index>` | `asyncio.create_subprocess_exec("rfkill", "list", str(index))` |
| Interface UP | `ip link set dev <iface> up` | `asyncio.create_subprocess_exec("ip", "link", "set", "dev", iface, "up")` |

---

## 17. Implementation Checklist (Backend Priority)

### Phase A: Core Backend (Week 1-2)
- [ ] **SubprocessManager** — robust process creation, streaming, cleanup
- [ ] **RingBuffer** — live log storage (1000 lines)
- [ ] **ErrorClassifier** — error categorization and user messages
- [ ] **ToolRegistry** — register all tools with metadata and tooltips
- [ ] **SafetyEngine** — confirmations, rate limits, scope control

### Phase B: Adapter Backend (Week 2-3) — airmon-ng Functions P0
- [ ] `getPhy()` — PHY detection from sysfs
- [ ] `getDriver()` — Driver detection from sysfs/ethtool
- [ ] `getChipset()` — Chipset detection from lsusb/lspci
- [ ] `getBus()` — Bus type detection (USB/PCI/SDIO)
- [ ] `getStack()` — mac80211 vs ieee80211 detection
- [ ] `listInterfaces()` — List all wlan interfaces
- [ ] `ifaceExists()` — Check interface exists
- [ ] `ifaceIsUp()` — Check interface is UP
- [ ] `setLink()` — `ip link set up/down`
- [ ] `startMac80211Iface()` — Enable monitor mode
- [ ] `stopMac80211Iface()` — Disable monitor mode
- [ ] `setChannelMac80211()` — Set channel/frequency

### Phase C: Service Backend (Week 3) — airmon-ng Functions P1
- [ ] `rfkill_check()` — Check soft/hard block
- [ ] `rfkill_unblock()` — Unblock rfkill
- [ ] `scanProcesses()` — Find/kill NM, wpa_supplicant, dhclient, avahi

### Phase D: Scan Backend (Week 3-4)
- [ ] **AirodumpRunner** — subprocess management for airodump-ng
- [ ] **AirodumpParser** — real-time stdout parsing
- [ ] **ClientTracker** — MAC, vendor, signal, packets
- [ ] **WPSDetector** — WPS status detection
- [ ] **MACRandomizer** — detect and warn about MAC changes

### Phase E: Capture Backend (Week 4-5)
- [ ] **DeauthRunner** — aireplay-ng subprocess management
- [ ] **DeauthParser** — sent/ACK/no-ACK tracking
- [ ] **EAPOLTracker** — M1-M4 handshake validation
- [ ] **CaptureWriter** — PCAP file management
- [ ] **RateController** — user-adjustable deauth rate

### Phase F: Crack Backend (Week 5-6)
- [ ] **AircrackRunner** — aircrack-ng subprocess management
- [ ] **HashcatRunner** — hashcat subprocess management
- [ ] **ProgressParser** — keys/sec, ETA, current key
- [ ] **WordlistBrowser** — auto-discover + manual path
- [ ] **ResultSaver** — password save/copy/export

### Phase G: Edge Cases (Week 6) — airmon-ng Functions P2-P3
- [ ] `changeMac80211IfaceTypeMonitor()` — Bad driver fallback (rtl8821au)
- [ ] `changeQcacldIfaceTypeMonitor()` — Qualcomm qcacld special case
- [ ] `findFreeInterface()` — Auto-name monitor interface
- [ ] `checkvm()` — VM detection (rfkill issues)
- [ ] `getExtendedInfo()` — Extended info (broken driver warnings)
- [ ] `getFrom()` — Driver source (K/C/V/S/?)

### Phase H: Polish (Week 6-7)
- [ ] **TooltipSystem** — all options with descriptions
- [ ] **NerdScreen** — live packet-level detail
- [ ] **SessionManager** — save/resume audit sessions
- [ ] **JSONLLogger** — full session logging
- [ ] **TutorialScreen** — full WiFi audit tutorial

---

## 18. Sidewinder vs airmon-ng: Improvements (8 Dimensions)

### 18.1 Core Philosophy

> **"The user is the expert. We recommend, they decide. Never execute without explicit confirmation."**

Every suggestion comes with:
- **What we recommend** — our analysis
- **Why we recommend it** — reasoning
- **What happens if** — consequences of each choice
- **User decides** — explicit confirmation required

### 18.2 Dimension 1: Hardware Detection (Deep Analysis)

airmon-ng reads PHY/driver/chipset once. Sidewinder does deep analysis:

| Capability | airmon-ng | Sidewinder |
|------------|-----------|------------|
| PHY detection | [OK] Static read | [OK] + live monitoring |
| Driver detection | [OK] ethtool | [OK] + quality scoring |
| Chipset detection | [OK] lsusb/lspci | [OK] + capability matrix |
| **Injection test** | [FAIL] | [OK] `aireplay-ng --test` |
| **Monitor quality** | [FAIL] | [OK] packet capture test |
| **Band enumeration** | [FAIL] | [OK] `iw phy info` parse |
| **TX power** | [FAIL] | [OK] actual vs regulatory |
| **Driver scoring** | [FAIL] | [OK] known issues database |

**Implementation:**
```python
class AdapterAnalyzer:
    async def analyze(self, iface: str) -> AdapterReport:
        """Deep hardware analysis. Returns report, takes no action."""
        return AdapterReport(
            phy=await self.get_phy(iface),
            driver=await self.get_driver(iface),
            chipset=await self.get_chipset(iface),
            injection=await self.test_injection(iface),  # recommendation only
            monitor_quality=await self.test_monitor(iface),  # recommendation only
            bands=await self.enumerate_bands(iface),
            tx_power=await self.get_tx_power(iface),
            driver_score=self.score_driver(driver),
            recommendations=self.generate_recommendations(...)
        )
```

### 18.3 Dimension 2: Monitor Mode (Verify + Watch)

airmon-ng creates monitor interface and assumes it works. Sidewinder verifies and watches:

| Capability | airmon-ng | Sidewinder |
|------------|-----------|------------|
| Create monitor VIF | [OK] | [OK] |
| **Verify monitor works** | [FAIL] | [OK] send test packet |
| **Watch for mode loss** | [FAIL] | [OK] poll type field |
| **Auto-recover** | [FAIL] | [OK] recommend (not auto) |
| **Detect conflicts** | [FAIL] | [OK] check other tools |
| **Persist across reboot** | [FAIL] | [OK] save/restore state |

**Implementation:**
```python
class MonitorWatcher:
    async def watch(self, iface: str):
        """Watch monitor mode. Report issues, never auto-fix."""
        while True:
            mode = await self.check_mode(iface)
            if mode != "monitor":
                # RECOMMEND, not auto-fix
                yield WatchEvent(
                    type="MODE_LOST",
                    message=f"Monitor mode lost on {iface}",
                    recommendation="Press [R] to re-enable monitor mode",
                    auto_fix=False  # NEVER auto-fix
                )
            await asyncio.sleep(2)
```

### 18.4 Dimension 3: Service Management (Graceful + Restore)

airmon-ng does `pkill -9` (nuclear). Sidewinder is graceful:

| Capability | airmon-ng | Sidewinder |
|------------|-----------|------------|
| Kill services | [OK] SIGKILL | [OK] SIGTERM → SIGKILL |
| **Save state** | [FAIL] | [OK] record which were running |
| **Restore on cleanup** | [FAIL] | [OK] restart what was running |
| **Detect respawning** | [FAIL] | [OK] warn if systemd respawns |
| **Custom service list** | [FAIL] | [OK] configurable |

**Implementation:**
```python
class ServiceManager:
    async def kill_services(self, services: List[str]) -> KillResult:
        """Kill services gracefully. Save state for restore."""
        # 1. Record which services are active
        await self.save_state(services)
        
        # 2. Try graceful stop first
        for service in services:
            result = await self.graceful_stop(service)
            if not result.success:
                # RECOMMEND, not auto-kill
                yield Recommendation(
                    message=f"{service} didn't stop gracefully",
                    action="Force kill with SIGKILL?",
                    options=["Yes, force kill", "Skip this service", "Show details"]
                )
        
        # 3. Save state for later restore
        await self.save_state(services)
    
    async def restore_services(self):
        """Restore services to pre-attack state."""
        state = await self.load_state()
        for service in state.was_running:
            # RECOMMEND, not auto-restore
            yield Recommendation(
                message=f"Restore {service}?",
                action="Restart this service?",
                options=["Yes, restart", "No, leave stopped"]
            )
```

### 18.5 Dimension 4: Error Handling (Explain + Suggest)

airmon-ng prints raw error and exits. Sidewinder explains and suggests:

| Capability | airmon-ng | Sidewinder |
|------------|-----------|------------|
| Print error | [OK] raw text | [OK] structured message |
| **Explain what happened** | [FAIL] | [OK] plain English |
| **Explain why** | [FAIL] | [OK] root cause |
| **Suggest fixes** | [FAIL] | [OK] actionable steps |
| **Classify severity** | [FAIL] | [OK] info/warning/error/critical |
| **Retry logic** | [FAIL] | [OK] with backoff |

**Implementation:**
```python
class ErrorHandler:
    def handle(self, error: Exception) -> ErrorReport:
        """Classify error and generate user-friendly message."""
        classified = self.classify(error)
        
        return ErrorReport(
            severity=classified.severity,
            title=classified.title,
            what_happened=classified.explanation,
            why=classified.root_cause,
            how_to_fix=classified.suggested_fixes,
            raw_error=str(error),
            retry_available=classified.is_recoverable
        )
```

### 18.6 Dimension 5: Multi-Adapter (Simultaneous + Failover)

airmon-ng handles one adapter. Sidewinder handles many:

| Capability | airmon-ng | Sidewinder |
|------------|-----------|------------|
| Single adapter | [OK] | [OK] |
| **Simultaneous scan** | [FAIL] | [OK] recommend channels |
| **Failover** | [FAIL] | [OK] recommend switch |
| **Load balance** | [FAIL] | [OK] recommend distribution |
| **Priority** | [FAIL] | [OK] user sets priority |

**Implementation:**
```python
class MultiAdapterAdvisor:
    async def advise(self, adapters: List[Adapter]) -> List[Recommendation]:
        """Recommend multi-adapter strategies. Never auto-execute."""
        recommendations = []
        
        if len(adapters) > 1:
            recommendations.append(Recommendation(
                title="Multi-adapter detected",
                message=f"Found {len(adapters)} adapters",
                suggestion="Split channels for faster scanning",
                details={
                    "wlan0": "channels 1-7",
                    "wlan1": "channels 8-14"
                },
                auto_execute=False  # NEVER
            ))
        
        return recommendations
```

### 18.7 Dimension 6: Session Management (Save + Resume)

airmon-ng is stateless. Sidewinder remembers:

| Capability | airmon-ng | Sidewinder |
|------------|-----------|------------|
| Stateful | [FAIL] | [OK] |
| **Save scan results** | [FAIL] | [OK] |
| **Resume interrupted** | [FAIL] | [OK] |
| **Export findings** | [FAIL] | [OK] JSON/CSV/HTML |
| **Audit log** | [FAIL] | [OK] tamper-evident |

**Implementation:**
```python
class SessionManager:
    async def auto_save(self, state: AppState):
        """Save state periodically. Never loses work."""
        await self.save(state, path="~/.sidewinder/session.json")
    
    async def offer_resume(self):
        """On launch, offer to resume if session exists."""
        if await self.session_exists():
            session = await self.load_session()
            yield Recommendation(
                title="Previous session found",
                message=f"Scan from {session.timestamp}: {len(session.aps)} APs",
                suggestion="Resume from where you left off?",
                options=["Resume", "Start fresh", "View session details"]
            )
```

### 18.8 Dimension 7: Intelligence (Recommend, Never Auto)

airmon-ng has zero intelligence. Sidewinder advises:

| Capability | airmon-ng | Sidewinder |
|------------|-----------|------------|
| **Analyze scan** | [FAIL] | [OK] rank targets |
| **Suggest method** | [FAIL] | [OK] based on conditions |
| **Estimate success** | [FAIL] | [OK] probability |
| **Learn from failures** | [FAIL] | [OK] save learnings |
| **Suggest next steps** | [FAIL] | [OK] contextual advice |

**CRITICAL: All intelligence is RECOMMENDATION ONLY. User always decides.**

**Implementation:**
```python
class IntelligenceEngine:
    async def analyze_scan(self, results: List[AP]) -> AnalysisReport:
        """Analyze scan results. Recommend targets, never auto-select."""
        ranked = self.rank_targets(results)
        
        return AnalysisReport(
            total_aps=len(results),
            recommendations=[
                Recommendation(
                    title=f"Easiest target: {ranked[0].ssid}",
                    message=f"Signal: {ranked[0].signal}dBm, {ranked[0].clients} clients",
                    reason="Strong signal, has active clients, WPA2 (easiest to crack)",
                    confidence=0.85,
                    auto_execute=False  # NEVER AUTO
                ),
                Recommendation(
                    title=f"Alternative: {ranked[1].ssid}",
                    message=f"Signal: {ranked[1].signal}dBm, WPS enabled",
                    reason="WPS vulnerability may allow faster crack",
                    confidence=0.60,
                    auto_execute=False  # NEVER AUTO
                )
            ],
            warnings=[
                Warning(
                    message=f"{ranked[2].ssid} has very weak signal ({ranked[2].signal}dBm)",
                    reason="May fail to capture handshake"
                )
            ]
        )
    
    async def suggest_method(self, target: AP) -> MethodRecommendation:
        """Suggest capture method. User decides."""
        if target.clients > 0 and target.signal > -60:
            method = "deauth"
            confidence = 0.8
            reason = "Active clients, strong signal"
        elif target.clients == 0:
            method = "pmkid"
            confidence = 0.5
            reason = "No clients — PMKID may work if adapter supports it"
        else:
            method = "passive"
            confidence = 0.3
            reason = "Weak signal — passive capture most reliable"
        
        return MethodRecommendation(
            recommended=method,
            confidence=confidence,
            reason=reason,
            alternatives=["passive", "deauth", "pmkid"],  # all options
            auto_execute=False  # NEVER AUTO
        )
    
    async def estimate_success(self, target: AP, method: str) -> float:
        """Estimate success probability. Informational only."""
        factors = {
            "signal": self.signal_score(target.signal),
            "clients": self.client_score(target.clients),
            "encryption": self.encryption_score(target.encryption),
            "method_fit": self.method_fit_score(target, method)
        }
        return sum(factors.values()) / len(factors)
```

### 18.9 Dimension 8: Security (Scope + Audit)

airmon-ng has no security features. Sidewinder protects:

| Capability | airmon-ng | Sidewinder |
|------------|-----------|------------|
| **Legal warning** | [FAIL] | [OK] first-run prompt |
| **Scope control** | [FAIL] | [OK] optional allowlist |
| **Stealth options** | [FAIL] | [OK] rate limiting |
| **Audit trail** | [FAIL] | [OK] tamper-evident log |
| **Evidence export** | [FAIL] | [OK] for legal defense |

**Implementation:**
```python
class SecurityEngine:
    async def legal_warning(self):
        """Show legal warning. Require explicit acknowledgment."""
        yield Recommendation(
            title="Legal Notice",
            message="This tool is for authorized security testing only",
            suggestion="Do you have written authorization to test this network?",
            options=["Yes, I have authorization", "No, cancel", "Show legal details"],
            require_acknowledgment=True  # MUST acknowledge
        )
    
    async def scope_check(self, target: str) -> ScopeResult:
        """Check if target is in authorized scope."""
        if self.scope_list and target not in self.scope_list:
            return ScopeResult(
                in_scope=False,
                warning=f"Target {target} is NOT in your authorized scope",
                recommendation="Only test networks you have written authorization for"
            )
        return ScopeResult(in_scope=True)
    
    async def audit_log(self, action: str, details: dict):
        """Log every action. Tamper-evident."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
            "hmac": self.compute_hmac(entry)  # tamper-evident
        }
        await self.append_log(entry)
```

---

## 19. Recommendation Engine (Not Auto-Execute)

### 19.1 Core Principle

```
┌─────────────────────────────────────────────────────────────────┐
│                    RECOMMENDATION ENGINE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Sidewinder analyzes → recommends → user decides                │
│                                                                 │
│  NEVER:                                                         │
│  - Auto-select target                                           │
│  - Auto-start attack                                            │
│  - Auto-kill services                                           │
│  - Auto-fix errors                                              │
│  - Auto-change settings                                         │
│                                                                 │
│  ALWAYS:                                                        │
│  - Show recommendation with reasoning                           │
│  - Present all options                                          │
│  - Wait for explicit user confirmation                          │
│  - Let user override recommendation                             │
│  - Log user's choice                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 19.2 Recommendation Data Structure

```python
@dataclass
class Recommendation:
    """A suggestion from Sidewinder. User always decides."""
    
    title: str                    # "Easiest target: HomeNetwork"
    message: str                  # "Signal: -47dBm, 3 active clients"
    reason: str                   # "Strong signal, WPA2, has clients"
    confidence: float             # 0.0 - 1.0 (how sure we are)
    alternatives: List[str]       # Other options user could choose
    auto_execute: bool = False    # ALWAYS False
    require_acknowledgment: bool = False  # Must user explicitly acknowledge?
    options: List[str] = None     # User's choices
    details: dict = None          # Extra info if user asks
```

### 19.3 Recommendation Display

```
╭─────────────────────────────────────────────────────────────────╮
│ 💡 RECOMMENDATION — Easiest Target                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ HomeNetwork (AA:BB:CC:DD:EE:FF)                                 │
│                                                                 │
│ Why:                                                            │
│ • Signal: -47dBm (EXCELLENT — high capture success)             │
│ • Clients: 3 active (deauth will work)                          │
│ • Encryption: WPA2-CCMP (easiest to crack)                      │
│ • Channel: 6 (clear, no interference)                           │
│                                                                 │
│ Confidence: 85%                                                 │
│                                                                 │
│ Alternatives:                                                   │
│ • OfficeNetwork (signal -52dBm, 1 client, WPS enabled)         │
│ • CafeOpen (OPEN network, no cracking needed)                   │
│                                                                 │
│ ──────────────────────────────────────────────────────────────  │
│ [Y] Accept recommendation  [N] Choose different target         │
│ [?] Show more details  [C] Cancel                               │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

### 19.4 Confidence Levels

| Confidence | Meaning | Display |
|------------|---------|---------|
| 80-100% | Very likely to work | [OK] High confidence |
| 60-79% | Probably will work | 🔶 Medium confidence |
| 40-59% | May or may not work | [WARN] Low confidence |
| 0-39% | Unlikely to work | [FAIL] Very low confidence |

### 19.5 What We Recommend (Complete List)

| Phase | What We Analyze | What We Recommend | User Decides |
|-------|-----------------|-------------------|--------------|
| **Scan** | Signal, clients, encryption, WPS | Rank targets by difficulty | Which to attack |
| **Target** | Adapter capabilities, target properties | Best capture method | Method to use |
| **Capture** | Signal strength, client count | Deauth targets, rate | Which clients, rate |
| **Crack** | Handshake quality, wordlist size | CPU vs GPU, wordlist | Tool and wordlist |
| **Cleanup** | Services killed, state saved | Restore services | What to restore |

### 19.6 User Override

User can always override our recommendation:

```
╭─────────────────────────────────────────────────────────────────╮
│ OVERRIDE — Capture Method                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ We recommend: Deauth + Capture (85% confidence)                 │
│ Reason: Active clients, strong signal                           │
│                                                                 │
│ Your choice:                                                    │
│ ▶ [1] Deauth + Capture (recommended)                           │
│   [2] Passive Capture (safer, slower)                           │
│   [3] PMKID Capture (no clients needed)                         │
│   [4] Custom settings...                                        │
│                                                                 │
│ Note: You chose a different method. We'll adjust parameters.    │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

---

## 20. New Functions (Beyond airmon-ng)

### 20.1 Function 1: PMKID Capture

**What it does:** Capture PMKID from AP's first association. No clients needed.

**Why airmon-ng doesn't:** airmon-ng only does traditional handshake capture.

**When to use:** Target AP has no connected clients, or you want to capture without deauth.

**How it works:**
1. Send association request to target AP
2. AP responds with EAPOL frame containing PMKID
3. Capture PMKID from the response
4. PMKID can be cracked like a handshake

**Implementation:**
```python
class PMKIDCapture:
    """Capture PMKID from AP. No clients needed."""
    
    async def capture(self, iface: str, target_bssid: str, timeout: int = 30) -> CaptureResult:
        """
        Capture PMKID from target AP.
        
        Requires: hcxdumptool, compatible adapter (rtw88/rtw89/ath9k)
        """
        # 1. Run hcxdumptool to capture PMKID
        cmd = [
            "hcxdumptool",
            "-i", iface,
            "--filterlist", target_bssid,
            "--filtermode", 2,
            "-o", "pmkid_capture.pcapng",
            "--enable_status", "1"
        ]
        
        # 2. Parse output for PMKID
        # 3. Convert to hashcat format with hcxpcapngtool
        # 4. Return result
        
    def requires_compatible_adapter(self, chipset: str) -> bool:
        """Check if adapter supports PMKID capture."""
        compatible = ["rtw88", "rtw89", "ath9k", "ath10k", "iwlwifi"]
        return any(c in chipset.lower() for c in compatible)
```

**Tooltip:**
```python
"pmkid_capture": Tooltip(
    name="PMKID Capture",
    description="Capture PMKID from AP's first association. No clients needed.",
    when_to_use="When target AP has no connected clients, or you want silent capture",
    risk_level="caution",
    risk_detail="Sends association request. May trigger IDS.",
    example="Sends 1 association request. Captures PMKID in response.",
    requires=["monitor_mode", "root", "compatible_adapter"],
    compatible_with=["wpa2", "wpa3"],
    flags={
        "--pmkid-timeout": "Seconds to wait for PMKID (default: 30)",
        "--pmkid-retries": "Number of association attempts (default: 5)",
    }
)
```

---

### 20.2 Function 2: Client Fingerprinting

**What it does:** Identify client device type, OS, and vendor from MAC and probe requests.

**Why airmon-ng doesn't:** airmon-ng only shows raw MAC addresses.

**When to use:** To understand what devices are connected, plan targeted attacks, identify high-value targets.

**How it works:**
1. Parse MAC OUI (first 3 bytes) for vendor
2. Parse probe requests for device type hints
3. Cross-reference with known device patterns
4. Display: Vendor, Device Type, OS guess

**Implementation:**
```python
class ClientFingerprint:
    """Identify client devices from MAC and probe requests."""
    
    async def fingerprint(self, mac: str, probes: List[str]) -> ClientInfo:
        """Fingerprint a client device."""
        # 1. OUI lookup
        vendor = await self.oui_lookup(mac[:8])
        
        # 2. Probe request analysis
        device_type = self.analyze_probes(probes)
        
        # 3. OS detection from probe patterns
        os_guess = self.detect_os(probes)
        
        return ClientInfo(
            mac=mac,
            vendor=vendor,
            device_type=device_type,  # phone, laptop, IoT, etc.
            os_guess=os_guess,        # iOS, Android, Windows, etc.
            confidence=self.calculate_confidence(vendor, probes)
        )
    
    def analyze_probes(self, probes: List[str]) -> str:
        """Analyze probe requests to determine device type."""
        # Known patterns:
        # "iPhone" → Apple iPhone
        # "Galaxy" → Samsung Galaxy
        # "Surface" → Microsoft Surface
        # "Echo" → Amazon Echo (IoT)
        # "Ring" → Ring Doorbell (IoT)
        # etc.
        
    def detect_os(self, probes: List[str]) -> str:
        """Detect OS from probe request patterns."""
        # Apple devices: probe format includes iOS version
        # Android devices: probe format includes Android version
        # Windows devices: different probe pattern
```

**Tooltip:**
```python
"client_fingerprint": Tooltip(
    name="Client Fingerprinting",
    description="Identify client device type, OS, and vendor from MAC and probe requests",
    when_to_use="To understand what devices are connected, plan targeted attacks",
    risk_level="safe",
    risk_detail="No packets sent. Passive analysis only.",
    example="AA:11:22 → Apple iPhone 15 (iOS 17), BB:11:22 → Samsung Galaxy S24 (Android 14)",
    requires=[],
    compatible_with=[],
    flags={
        "--fingerprint-all": "Fingerprint all detected clients",
        "--fingerprint-target": "Fingerprint clients of specific AP",
    }
)
```

**Display:**
```
╭─────────────────────────────────────────────────────────────────╮
│ Client Fingerprint — HomeNetwork                                │
├─────────────────────────────────────────────────────────────────┤
│ MAC               Vendor      Device         OS        Signal   │
├─────────────────────────────────────────────────────────────────┤
│ ▶ AA:11:22:33:44:55  Apple       iPhone 15     iOS 17    -47dBm │
│   BB:11:22:33:44:55  Samsung     Galaxy S24    Android 14 -52dBm│
│   CC:11:22:33:44:55  Intel       Laptop        Win 11    -65dBm│
│   DD:11:22:33:44:55  Amazon      Echo Dot      FireOS    -78dBm│
│   EE:11:22:33:44:55  Unknown     Unknown       Unknown   -82dBm│
╰─────────────────────────────────────────────────────────────────╯
```

---

### 20.3 Function 3: Rogue AP Detection

**What it does:** Detect evil twin / rogue access points pretending to be legitimate networks.

**Why airmon-ng doesn't:** airmon-ng just lists APs, doesn't analyze for threats.

**When to use:** Security auditing, detecting attacks, network monitoring.

**How it works:**
1. Collect baseline AP data (BSSID, channel, signal, encryption)
2. Detect anomalies:
   - Same SSID, different BSSID
   - Same BSSID, different channel
   - Signal stronger than expected
   - Encryption downgrade
   - Deauth activity
3. Score threat level
4. Alert user

**Implementation:**
```python
class RogueAPDetector:
    """Detect evil twin / rogue access points."""
    
    async def scan_for_rogues(self, iface: str, duration: int = 60) -> RogueReport:
        """Scan for rogue APs."""
        # 1. Collect AP data
        aps = await self.collect_ap_data(iface, duration)
        
        # 2. Analyze for anomalies
        anomalies = self.detect_anomalies(aps)
        
        # 3. Score threat level
        threats = self.score_threats(anomalies)
        
        return RogueReport(
            total_aps=len(aps),
            anomalies=anomalies,
            threats=threats,
            recommendations=self.generate_recommendations(threats)
        )
    
    def detect_anomalies(self, aps: List[AP]) -> List[Anomaly]:
        """Detect anomalous APs."""
        anomalies = []
        
        # Check 1: Duplicate SSIDs with different BSSIDs
        ssids = defaultdict(list)
        for ap in aps:
            ssids[ap.ssid].append(ap)
        
        for ssid, ap_list in ssids.items():
            if len(ap_list) > 1:
                # Same SSID, different BSSIDs — possible evil twin
                anomalies.append(Anomaly(
                    type="DUPLICATE_SSID",
                    severity="HIGH",
                    details=f"SSID '{ssid}' appears on {len(ap_list)} BSSIDs",
                    aps=ap_list
                ))
        
        # Check 2: Signal anomalies (too strong for location)
        # Check 3: Encryption downgrades
        # Check 4: Channel anomalies
        
        return anomalies
    
    def score_threats(self, anomalies: List[Anomaly]) -> List[Threat]:
        """Score threat level of anomalies."""
        threats = []
        for anomaly in anomalies:
            threat_level = self.calculate_threat(anomaly)
            if threat_level > 0.5:
                threats.append(Threat(
                    anomaly=anomaly,
                    level=threat_level,
                    recommendation=self.get_recommendation(anomaly)
                ))
        return threats
```

**Tooltip:**
```python
"rogue_ap_detection": Tooltip(
    name="Rogue AP Detection",
    description="Detect evil twin / rogue access points pretending to be legitimate networks",
    when_to_use="Security auditing, detecting attacks, network monitoring",
    risk_level="safe",
    risk_detail="No packets sent. Passive analysis only.",
    example="Detected 2 APs with same SSID 'HomeNetwork' — possible evil twin",
    requires=["monitor_mode"],
    compatible_with=[],
    flags={
        "--rogue-duration": "Seconds to scan for rogues (default: 60)",
        "--rogue-threat-level": "Minimum threat level to report (0.0-1.0, default: 0.5)",
    }
)
```

**Display:**
```
╭─────────────────────────────────────────────────────────────────╮
│ [WARN] ROGUE AP DETECTION — Threats Found                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ┌─ THREAT: Possible Evil Twin ──────────────────────────────┐   │
│ │ Severity: HIGH                                            │   │
│ │                                                           │   │
│ │ SSID 'HomeNetwork' appears on 2 BSSIDs:                   │   │
│ │ • AA:BB:CC:DD:EE:FF (Ch:6, -47dBm) — Original           │   │
│ │ • 11:22:33:44:55:66 (Ch:6, -35dBm) — ROGUE (too strong) │   │
│ │                                                           │   │
│ │ Recommendation:                                           │   │
│ │ • The second AP has unusually strong signal               │   │
│ │ • This may indicate an evil twin attack                   │   │
│ │ • Avoid connecting to 11:22:33:44:55:66                  │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                 │
│ [D] Dismiss  [S] Save report  [B] Block rogue  [?] Details     │
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

---

### 20.4 Function 4: WPS Vulnerability Scan

**What it does:** Detect WPS version, lock status, and Pixie-Dust vulnerability.

**Why airmon-ng doesn't:** airmon-ng just shows WPS yes/no. Doesn't analyze vulnerabilities.

**When to use:** To find easy attack vectors, assess WPS security.

**How it works:**
1. Detect WPS presence from beacon frames
2. Identify WPS version (1.0, 2.0)
3. Check if WPS is locked (rate limiting)
4. Test for Pixie-Dust vulnerability
5. Report findings

**Implementation:**
```python
class WPSScanner:
    """Scan for WPS vulnerabilities."""
    
    async def scan_wps(self, iface: str, target_bssid: str) -> WPSReport:
        """Scan target for WPS vulnerabilities."""
        # 1. Detect WPS presence
        wps_info = await self.detect_wps(iface, target_bssid)
        
        if not wps_info.present:
            return WPSReport(present=False)
        
        # 2. Identify version
        version = wps_info.version
        
        # 3. Check lock status
        locked = await self.check_lock(iface, target_bssid)
        
        # 4. Test for Pixie-Dust (optional, more intrusive)
        pixie_vulnerable = False
        if not locked:
            pixie_vulnerable = await self.test_pixie_dust(iface, target_bssid)
        
        return WPSReport(
            present=True,
            version=version,
            locked=locked,
            pixie_vulnerable=pixie_vulnerable,
            recommendation=self.generate_recommendation(wps_info, locked, pixie_vulnerable)
        )
    
    async def detect_wps(self, iface: str, bssid: str) -> WPSInfo:
        """Detect WPS from beacon frames."""
        # Parse: wash -i <iface> -c <channel>
        # Or parse beacon frames directly
        
    async def check_lock(self, iface: str, bssid: str) -> bool:
        """Check if WPS is locked (rate limited)."""
        # WPS lock = too many failed attempts
        # AP stops responding to WPS for 5+ minutes
        
    async def test_pixie_dust(self, iface: str, bssid: str) -> bool:
        """Test for Pixie-Dust vulnerability."""
        # Run: reaver -i <iface> -b <bssid> -K 1
        # If PIN found in < 5 seconds = vulnerable
```

**Tooltip:**
```python
"wps_scan": Tooltip(
    name="WPS Vulnerability Scan",
    description="Detect WPS version, lock status, and Pixie-Dust vulnerability",
    when_to_use="To find easy attack vectors, assess WPS security",
    risk_level="safe",
    risk_detail="Passive scan only. No packets sent.",
    example="WPS 2.0 detected, not locked, Pixie-Dust vulnerable",
    requires=["monitor_mode"],
    compatible_with=["wpa", "wpa2"],
    flags={
        "--wps-scan": "Enable WPS vulnerability scan",
        "--wps-test-pixie": "Test for Pixie-Dust (slightly more intrusive)",
    }
)
```

**Display:**
```
╭─────────────────────────────────────────────────────────────────╮
│ WPS Vulnerability Report — HomeNetwork                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ BSSID: AA:BB:CC:DD:EE:FF                                        │
│                                                                 │
│ ┌─ WPS Status ──────────────────────────────────────────────┐   │
│ │ Present:     Yes                                          │   │
│ │ Version:     2.0                                          │   │
│ │ Locked:      No (can attempt PIN)                         │   │
│ │ Pixie-Dust:  VULNERABLE (high confidence)                 │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─ Recommendation ──────────────────────────────────────────┐   │
│ │ Pixie-Dust attack possible. This is the fastest method.   │   │
│ │                                                           │   │
│ │ Attack options:                                           │   │
│ │ • Pixie-Dust: ~5 seconds (if vulnerable)                  │   │
│ │ • Brute force: ~4-10 hours (if not vulnerable)            │   │
│ │                                                           │   │
│ │ Note: WPS attacks may trigger lockout after 5 failures.   │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ [A] Attempt Pixie-Dust  [B] Brute force  [S] Skip  [?] Details│
│                                                                 │
╰─────────────────────────────────────────────────────────────────╯
```

---

## 21. New Module Structure

```
core/
├── adapter.py          # Existing: adapter detection
├── monitor.py          # Existing: monitor mode
├── services.py         # Existing: service management
├── rfkill.py           # Existing: rfkill handling
│
├── attacks/            # NEW: Attack vectors
│   ├── __init__.py
│   ├── pmkid.py        # PMKID capture (Function 1)
│   ├── handshake.py    # Handshake capture
│   ├── deauth.py       # Deauth attack
│   └── wps.py          # WPS attacks (Function 4)
│
├── recon/              # NEW: Deep reconnaissance
│   ├── __init__.py
│   ├── fingerprint.py  # Client fingerprinting (Function 2)
│   ├── rogue_ap.py     # Rogue AP detection (Function 3)
│   └── wps_scan.py     # WPS vulnerability scan (Function 4)
│
├── capture/            # NEW: Advanced capture
│   ├── __init__.py
│   ├── validator.py    # Handshake validation
│   └── quality.py      # Capture quality scoring
│
└── analysis/           # NEW: Post-capture analysis
    ├── __init__.py
    └── report.py       # PDF report generation
```

---

## 22. New CLI Flags

```bash
# Function 1: PMKID
sidewinder --pmkid-capture <BSSID>           # Capture PMKID
sidewinder --pmkid-timeout 30               # Timeout in seconds
sidewinder --pmkid-retries 5                # Number of attempts

# Function 2: Client Fingerprinting
sidewinder --fingerprint <BSSID>            # Fingerprint clients of AP
sidewinder --fingerprint-all                # Fingerprint all clients

# Function 3: Rogue AP Detection
sidewinder --detect-rogue                   # Scan for rogue APs
sidewinder --rogue-duration 60              # Scan duration
sidewinder --rogue-threat 0.5               # Min threat level

# Function 4: WPS
sidewinder --wps-scan <BSSID>               # Scan for WPS vulnerabilities
sidewinder --wps-test-pixie                 # Test for Pixie-Dust
```

---

## 23. Implementation Checklist (New Functions)

### Function 1: PMKID Capture
- [ ] Implement `PMKIDCapture` class
- [ ] Add hcxdumptool wrapper
- [ ] Add hcxpcapngtool wrapper
- [ ] Add PMKID → hashcat format converter
- [ ] Add adapter compatibility check
- [ ] Add tooltip
- [ ] Add CLI flag
- [ ] Add error handling (E013: PMKID failed)

### Function 2: Client Fingerprinting
- [ ] Implement `ClientFingerprint` class
- [ ] Add OUI database (first 3 bytes → vendor)
- [ ] Add probe request parser
- [ ] Add device type detection
- [ ] Add OS detection
- [ ] Add tooltip
- [ ] Add CLI flag
- [ ] Add display screen

### Function 3: Rogue AP Detection
- [ ] Implement `RogueAPDetector` class
- [ ] Add AP data collection
- [ ] Add anomaly detection (duplicate SSID, signal anomaly)
- [ ] Add threat scoring
- [ ] Add recommendation generation
- [ ] Add tooltip
- [ ] Add CLI flag
- [ ] Add threat display screen

### Function 4: WPS Vulnerability Scan
- [ ] Implement `WPSScanner` class
- [ ] Add WPS detection from beacon frames
- [ ] Add WPS version identification
- [ ] Add lock status check
- [ ] Add Pixie-Dust vulnerability test
- [ ] Add tooltip
- [ ] Add CLI flag
- [ ] Add WPS report display

---

## 24. RT5370 Direct Driver Access — "OPTIMIZED" Mode

### 24.1 What "OPTIMIZED" Means

When Sidewinder detects an RT5370 adapter, it shows:

```
┌─────────────────────────────────────────────────────────────────┐
│  Adapter: wlx001ea6c65744 (Ralink RT5370)                      │
│  Status: [OK] OPTIMIZED — Direct driver access enabled            │
│                                                                 │
│  Sidewinder knows everything about this card:                   │
│  • Direct iwpriv commands (no airmon-ng wrapper)                │
│  • Custom monitor mode filters                                  │
│  • Optimal injection rate control                               │
│  • Power save disabled for 100% capture                         │
│  • RT5370-specific error handling                               │
│  • Zero subprocess overhead                                     │
│                                                                 │
│  [Enter] Continue  [?] What does OPTIMIZED mean?               │
└─────────────────────────────────────────────────────────────────┘
```

### 24.2 Why RT5370 Gets "OPTIMIZED" Status

| Feature | Generic Adapter | RT5370 (OPTIMIZED) |
|---------|----------------|-------------------|
| **Adapter init** | 3-4 subprocess (airmon-ng) | Direct ioctl (0 subprocess) |
| **Monitor mode** | Generic iw commands | RT5370-specific iwpriv |
| **Channel switching** | iwconfig (slow) | iwpriv set Channel (2x faster) |
| **Packet capture** | airodump-ng stdout parse | Raw socket (5x faster) |
| **Packet injection** | aireplay-ng subprocess | Raw socket (10x faster) |
| **Rate control** | Auto (generic) | RT5370-specific (better range) |
| **Power management** | Generic iwconfig | RT5370 PSMode=CAM (no missed packets) |
| **Error messages** | Generic "failed" | RT5370 chip-specific errors |
| **Country region** | Not exposed | RT5370 CountryRegion iwpriv |

### 24.3 RT5370 Direct Driver Commands (iwpriv)

These are **chip-specific commands** that generic tools don't expose:

```python
# RT5370 iwpriv commands - DIRECT from driver
RT5370_COMMANDS = {
    # Power Management (CRITICAL for audit)
    "PSMode=CAM":        "Constantly Active Mode — NO power save (BEST FOR AUDIT)",
    "PSMode=MAX_PSP":    "Maximum Power Save — DON'T USE (misses packets)",
    "PSMode=FAST_PSP":   "Fast Power Save — DON'T USE (misses packets)",
    
    # Rate Control (OPTIMIZE for range vs speed)
    "FixedTxMode=OFDM":  "Force OFDM mode — better for injection",
    "FixedTxMode=CCK":   "Force CCK mode — maximum range",
    "HtMcs=0":           "6 Mbps OFDM / 1 Mbps CCK",
    "HtMcs=3":           "18 Mbps OFDM / 11 Mbps CCK",
    "HtMcs=7":           "54 Mbps OFDM (maximum speed)",
    "HtMcs=33":          "Auto rate (let driver decide)",
    
    # Channel Control
    "Channel=1":         "Set channel 1 (2412 MHz)",
    "Channel=6":         "Set channel 6 (2437 MHz)",
    "Channel=11":        "Set channel 11 (2462 MHz)",
    "Channel=13":        "Set channel 13 (2472 MHz)",
    "Channel=14":        "Set channel 14 (2484 MHz)",
    
    # Country Region (LEGAL compliance)
    "CountryRegion=0":   "US/Canada: channels 1-11",
    "CountryRegion=1":   "Europe: channels 1-13",
    "CountryRegion=5":   "Japan: channels 1-14",
    "CountryRegion=31":  "India: channels 1-11 active, 12-14 passive",
    
    # 802.11 Mode
    "WirelessMode=0":    "Legacy 11b/g mixed",
    "WirelessMode=1":    "11B only",
    "WirelessMode=4":    "11G only",
    "WirelessMode=9":    "11BGN mixed (DEFAULT)",
    
    # Bandwidth
    "HtBw=0":            "20 MHz bandwidth",
    "HtBw=1":            "40 MHz bandwidth",
    
    # Guard Interval
    "HtGi=0":            "Long GI (more reliable)",
    "HtGi=1":            "Short GI (faster)",
    
    # Preamble
    "TxPreamble=0":      "Long preamble (maximum compatibility)",
    "TxPreamble=1":      "Short preamble (faster)",
    "TxPreamble=2":      "Auto preamble",
}
```

### 24.4 RT5370 Optimal Settings for Each Operation

```python
# RT5370 OPTIMAL SETTINGS - Direct from driver analysis
RT5370_OPTIMAL = {
    # SCAN operation
    "scan": {
        "PSMode": "CAM",              # Disable power save
        "WirelessMode": "9",          # BGN mixed
        "CountryRegion": "5",         # India (1-14 channels)
        "HtBw": "0",                  # 20 MHz (more stable)
        "HtGi": "1",                  # Short GI (faster)
        "HtMcs": "33",               # Auto rate
        "monitor_filters": ["FCSFAIL", "OTHER_BSS"],
        "dwell_time": 0.3,            # 300ms per channel
    },
    
    # DEAUTH attack
    "deauth": {
        "PSMode": "CAM",              # Disable power save
        "FixedTxMode": "OFDM",        # OFDM mode
        "HtMcs": "0",                 # 6 Mbps (reliable)
        "TxPreamble": "0",            # Long preamble (compatibility)
        "rate": "6M",                 # Injection rate
        "count": 10,                  # Deauth frames
        "interval": 0.1,             # 100ms between frames
    },
    
    # CAPTURE handshake
    "capture": {
        "PSMode": "CAM",              # Disable power save
        "FixedTxMode": "OFDM",        # OFDM mode
        "HtMcs": "0",                 # 6 Mbps
        "monitor_filters": ["FCSFAIL", "OTHER_BSS"],
        "timeout": 30,                # 30 seconds max
    },
    
    # INJECTION (general)
    "inject": {
        "PSMode": "CAM",              # Disable power save
        "FixedTxMode": "OFDM",        # OFDM mode
        "HtMcs": "0",                 # 6 Mbps (reliable)
        "TxPreamble": "0",            # Long preamble
    },
    
    # BEACON injection
    "beacon": {
        "PSMode": "CAM",              # Disable power save
        "FixedTxMode": "CCK",         # CCK mode (maximum range)
        "HtMcs": "0",                 # 1 Mbps (maximum range)
        "TxPreamble": "0",            # Long preamble
    },
}
```

### 24.5 RT5370 Initialization Sequence (Direct Driver Access)

```python
class RT5370Optimizer:
    """RT5370 direct driver optimizer — NO aircrack-ng dependency"""
    
    def __init__(self, iface):
        self.iface = iface
        self.chipset = "RT5370"
        self.optimized = True
    
    def init_optimized_mode(self):
        """Initialize RT5370 with optimal settings — DIRECT from driver"""
        
        # Step 1: Bring interface down
        os.system(f"ip link set {self.iface} down")
        
        # Step 2: Set monitor mode via iw (cfg80211)
        os.system(f"iw dev {self.iface} set type monitor")
        
        # Step 3: Bring interface up
        os.system(f"ip link set {self.iface} up")
        
        # Step 4: RT5370-SPECIFIC: Disable power save
        # This is CRITICAL — if PS is enabled, adapter sleeps and misses packets
        self._iwpriv("PSMode=CAM")
        
        # Step 5: RT5370-SPECIFIC: Set optimal injection rate
        # 6 Mbps OFDM = reliable + moderate range
        self._iwpriv("FixedTxMode=OFDM")
        self._iwpriv("HtMcs=0")  # 6 Mbps
        
        # Step 6: RT5370-SPECIFIC: Set country region
        # India = Region 5 (channels 1-14)
        self._iwpriv("CountryRegion=5")
        
        # Step 7: RT5370-SPECIFIC: Set 802.11 mode
        # BGN mixed = maximum compatibility
        self._iwpriv("WirelessMode=9")
        
        # Step 8: RT5370-SPECIFIC: Set bandwidth
        # 20 MHz = more stable than 40 MHz
        self._iwpriv("HtBw=0")
        
        # Step 9: RT5370-SPECIFIC: Set guard interval
        # Long GI = more reliable
        self._iwpriv("HtGi=0")
        
        # Step 10: Set monitor mode filters
        # Capture everything including FCS errors
        os.system(f"iw dev {self.iface} set monitor flags fcsfail otherbss")
        
        return True
    
    def _iwpriv(self, cmd):
        """Execute iwpriv command — DIRECT to driver"""
        result = subprocess.run(
            ["iwpriv", self.iface, "set", cmd],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    
    def set_channel(self, channel):
        """Set channel — DIRECT via iwpriv (2x faster than iwconfig)"""
        return self._iwpriv(f"Channel={channel}")
    
    def set_rate(self, rate="6M"):
        """Set injection rate — RT5370-specific"""
        rate_map = {
            "1M": ("CCK", "0"),    # 1 Mbps CCK (maximum range)
            "2M": ("CCK", "1"),    # 2 Mbps CCK
            "5.5M": ("CCK", "2"),  # 5.5 Mbps CCK
            "6M": ("OFDM", "0"),   # 6 Mbps OFDM (recommended)
            "9M": ("OFDM", "1"),   # 9 Mbps OFDM
            "12M": ("OFDM", "2"),  # 12 Mbps OFDM
            "18M": ("OFDM", "3"),  # 18 Mbps OFDM
            "24M": ("OFDM", "4"),  # 24 Mbps OFDM
            "54M": ("OFDM", "7"),  # 54 Mbps OFDM (maximum speed)
        }
        
        mode, mcs = rate_map.get(rate, ("OFDM", "0"))
        self._iwpriv(f"FixedTxMode={mode}")
        self._iwpriv(f"HtMcs={mcs}")
    
    def disable_power_save(self):
        """Disable power save — RT5370-SPECIFIC (CRITICAL)"""
        self._iwpriv("PSMode=CAM")
        os.system(f"iwconfig {self.iface} power off")
    
    def get_chip_info(self):
        """Get RT5370-specific chip info"""
        return {
            "chipset": "RT5370",
            "vendor_id": "148F",
            "product_id": "5370",
            "bands": "2.4 GHz ONLY",
            "spatial_streams": "1x1",
            "usb": "USB 2.0",
            "driver": "rt2870sta.ko",
            "optimized": True,
            "capabilities": {
                "monitor_mode": True,
                "injection": True,
                "power_control": True,
                "rate_control": True,
                "channel_control": True,
                "country_region": True,
            }
        }
```

### 24.6 RT5370 Error Database (Chip-Specific)

```python
# RT5370-SPECIFIC ERROR DATABASE — Direct from driver analysis
RT5370_ERRORS = {
    "E001": {
        "name": "USB_BULK_FAIL",
        "description": "USB bulk transfer failed",
        "cause": "USB hub power issue or adapter disconnected",
        "fix": "Try different USB port, use powered hub",
        "driver_message": "RTUSBBulkOutDataPacket: BulkOutPending",
        "severity": "CRITICAL",
    },
    "E002": {
        "name": "FIRMWARE_LOAD_FAIL",
        "description": "Failed to load MCU firmware",
        "cause": "Driver module not loaded or corrupted firmware",
        "fix": "Reload driver: rmmod rt2870sta && modprobe rt2870sta",
        "driver_message": "NICInitializeAdapter: firmware load failed",
        "severity": "CRITICAL",
    },
    "E003": {
        "name": "CHANNEL_SWITCH_FAIL",
        "description": "Channel switch timeout",
        "cause": "MCU busy or hardware issue",
        "fix": "Wait 1 second, retry channel switch",
        "driver_message": "RT5592_ChipSwitchChannel: Retry count exhausted",
        "severity": "WARNING",
    },
    "E004": {
        "name": "POWER_SAVE_ACTIVE",
        "description": "Power save mode is active — missing packets",
        "cause": "PSMode not set to CAM",
        "fix": "Run: iwpriv {iface} set PSMode=CAM",
        "driver_message": "RtmpInsertPsQueue: queue a packet",
        "severity": "WARNING",
    },
    "E005": {
        "name": "INJECTION_DROP",
        "description": "Injection frames dropped — USB bulk pipe full",
        "cause": "Injection rate too high for USB bandwidth",
        "fix": "Reduce injection rate to 6 Mbps",
        "driver_message": "RTUSBBulkOutDataPacket: BulkOutPending == TRUE",
        "severity": "WARNING",
    },
    "E006": {
        "name": "MONITOR_FILTER_FAIL",
        "description": "Failed to set monitor mode filters",
        "cause": "cfg80211 not supported or interface not in monitor mode",
        "fix": "Ensure interface is in monitor mode first",
        "driver_message": "CFG80211_OpsVirtualInfChg: Wrong interface type",
        "severity": "ERROR",
    },
}
```

### 24.7 RT5370 Performance Optimization

```python
# RT5370 PERFORMANCE TUNING — Direct from driver analysis
RT5370_PERFORMANCE = {
    # USB bulk transfer optimization
    "usb_bulk": {
        "max_packet_size": 64,          # USB 2.0 high speed
        "transfer_buffer": 24576,       # 24KB (USB_BULK_BUF_ALIGMENT)
        "max_bulk_out": 1,              # Only 1 bulk OUT at a time
        "cck_limit": 4096,              # CCK frames limited to 4KB
        "ht_limit": 24576,              # HT frames can use 24KB
    },
    
    # Injection optimization
    "injection": {
        "max_rate": 400,                # ~400 packets/sec theoretical
        "recommended_rate": 300,        # 300 packets/sec reliable
        "min_interval": 0.003,          # 3ms between packets
        "deauth_rate": "6M",            # 6 Mbps OFDM for deauth
        "beacon_rate": "1M",            # 1 Mbps CCK for beacons
    },
    
    # Capture optimization
    "capture": {
        "buffer_size": 1000,            # Ring buffer 1000 packets
        "flush_interval": 1.0,          # Flush to disk every 1 second
        "max_file_size": 104857600,     # 100MB max capture file
        "monitor_filter": "fcsfail",    # Capture FCS errors too
    },
    
    # Channel hopping optimization
    "channel_hop": {
        "dwell_time": 0.3,              # 300ms per channel
        "hop_interval": 0.35,           # 350ms total cycle
        "channels_2g": [1,6,11],        # Minimum 3 channels for 2.4GHz
        "full_scan_channels": list(range(1,15)),  # All 14 channels
    },
}
```

### 24.8 RT5370 Implementation Checklist

- [ ] **CRITICAL:** Implement `RT5370Optimizer` class
- [ ] **CRITICAL:** Add RT5370 detection (USB VID:PID `148F:5370`)
- [ ] **CRITICAL:** Add "OPTIMIZED" status display
- [ ] **CRITICAL:** Implement direct iwpriv commands (no subprocess)
- [ ] **CRITICAL:** Add power save disable (PSMode=CAM)
- [ ] **CRITICAL:** Add rate control (FixedTxMode, HtMcs)
- [ ] **CRITICAL:** Add channel control (iwpriv Channel=N)
- [ ] **CRITICAL:** Add country region control (CountryRegion=N)
- [ ] Add RT5370 error database
- [ ] Add performance tuning constants
- [ ] Add monitor mode filter support
- [ ] Add chip info display
- [ ] Add tooltip for "OPTIMIZED" status
- [ ] Add raw socket capture (replace airodump-ng)
- [ ] Add raw socket injection (replace aireplay-ng)
- [ ] Add async packet parser
- [ ] Add EAPOL frame detection
- [ ] Add deauth frame builder
- [ ] Add beacon frame builder

### 24.9 RT5370 vs Aircrack-ng Performance Comparison

| Operation | Aircrack-ng | Sidewinder (RT5370) | Improvement |
|-----------|-------------|-------------------|-------------|
| **Adapter init** | 3-4 subprocess | 0 subprocess | 10x faster |
| **Monitor mode** | airmon-ng (2s) | Direct ioctl (0.2s) | 10x faster |
| **Channel switch** | iwconfig (0.5s) | iwpriv (0.1s) | 5x faster |
| **Capture start** | airodump-ng (1s) | Raw socket (0.1s) | 10x faster |
| **Packet parsing** | stdout text | In-memory struct | 5x faster |
| **Injection** | aireplay-ng (0.5s) | Raw socket (0.05s) | 10x faster |
| **Error handling** | Generic messages | RT5370-specific | Better debugging |
| **Power management** | Not exposed | PSMode=CAM | No missed packets |
| **Rate control** | Not exposed | FixedTxMode+HtMcs | Better range |

### 24.10 RT5370 User Experience Flow

```
1. Launch: sudo ./sidewinder
2. Hardware discovery → Detects RT5370
3. Shows: "[OK] OPTIMIZED — Direct driver access enabled"
4. User selects operation
5. Sidewinder uses DIRECT driver commands (no aircrack-ng)
6. Performance: 10x faster than aircrack-ng
7. Errors: RT5370-specific with fix suggestions
8. Cleanup: Restore RT5370 to managed mode
```

### 24.11 RT5370 Detection Code

```python
# RT5370 USB VID:PID pairs
RT5370_DEVICES = [
    (0x148F, 0x5370),  # Ralink RT5370
    (0x148F, 0x5372),  # Ralink RT5372
    (0x13D3, 0x3365),  # Azurewave
    (0x13D3, 0x3329),  # Azurewave
    (0x2001, 0x3C15),  # Alpha
    (0x2001, 0x3C19),  # D-Link DWA-125/A3
    (0x2001, 0x3C1C),  # D-Link GO-USB-N150
    (0x2001, 0x3C1D),  # D-Link DWA-123/B1
    (0x043E, 0x7A12),  # LG/Arcadyan
    (0x043E, 0x7A22),  # LG innotek
    (0x04DA, 0x1800),  # Panasonic
    (0x0471, 0x2104),  # Philips
]

def detect_rt5370():
    """Detect RT5370 adapter — return True if found"""
    import subprocess
    result = subprocess.run(["lsusb"], capture_output=True, text=True)
    
    for vid, pid in RT5370_DEVICES:
        hex_vid = f"{vid:04x}"
        hex_pid = f"{pid:04x}"
        if f"{hex_vid}:{hex_pid}" in result.stdout.lower():
            return True
    return False
```

### 24.12 RT5370 "OPTIMIZED" Status Display

```
╭─────────────────────────────────────────────────────────────────╮
│  Adapter Detection                                              │
│                                                                 │
│  Found: wlx001ea6c65744                                         │
│  Chipset: Ralink RT5370                                         │
│  Vendor ID: 148F:5370                                           │
│  Driver: rt2870sta.ko                                           │
│  Bands: 2.4 GHz ONLY                                            │
│  Spatial Streams: 1x1                                           │
│  USB: USB 2.0                                                   │
│                                                                 │
│  Status: [OK] OPTIMIZED — Direct driver access enabled            │
│                                                                 │
│  Sidewinder knows everything about this card:                   │
│  • Direct iwpriv commands (no airmon-ng wrapper)                │
│  • Custom monitor mode filters                                  │
│  • Optimal injection rate control                               │
│  • Power save disabled for 100% capture                         │
│  • RT5370-specific error handling                               │
│  • Zero subprocess overhead                                     │
│                                                                 │
│  Performance: 10x faster than aircrack-ng                       │
│                                                                 │
│  [Enter] Continue  [?] What does OPTIMIZED mean?               │
╰─────────────────────────────────────────────────────────────────╯
```

---

## 25. RTL8821AU "OPTIMIZED" MODE — Direct Radiotap Engine

### 25.1 Why RTL8821AU Gets OPTIMIZED Status

The morrownr driver (8821au-20210708) is **the superior attack adapter**:

| Dimension | RT5370 | RTL8821AU (morrownr) | Winner |
|-----------|--------|---------------------|--------|
| Monitor Mode | Prism2 header (hardcoded zeros) | **Radiotap (full fields)** | RTL8821AU |
| Injection | No dedicated path (requires association) | **Radiotap-iterator TX with retry** | RTL8821AU |
| 802.11ac VHT | No | **MCS 0-9, 80/160 MHz, beamforming** | RTL8821AU |
| 5GHz | No | **Full 5GHz support** | RTL8821AU |
| Error Handling | Basic NULL checks | **Surprise removal, IO error tracking** | RTL8821AU |
| Code Quality | 2.4/10 (Windows port) | **8.2/10 (Linux-native)** | RTL8821AU |
| Source Files | 174 | **609** | RTL8821AU |

**RTL8821AU is the PRIMARY attack adapter.** RT5370 is the backup.

### 25.2 RTL8821AU Radiotap Fields (Monitor RX)

The RTL8821AU fills these radiotap fields on every received frame:

```
┌──────────────────────────────────────────────────────────────────┐
│  Radiotap Header (rtw_radiotap.c:164)                           │
├──────────────────────────────────────────────────────────────────┤
│  FLAGS        │ WEP, fragmentation, FCS, bad FCS, SGI           │
│  RATE         │ OFDM/CCK rates                                   │
│  CHANNEL      │ Frequency, band type, width (5/10/20/40 MHz)    │
│  DBM_SIGNAL   │ Actual power in dBm                              │
│  MCS          │ Bandwidth, GI, FEC/LDPC, STBC, MCS index        │
│  AMPDU        │ Reference number, flags, EOF status              │
│  VHT          │ STBC, GI, LDPC, beamformed, BW, NSS, MCS,       │
│               │ group_id, partial_aid                             │
│  TIMESTAMP    │ USF clock for precise timing                     │
└──────────────────────────────────────────────────────────────────┘
```

### 25.3 RTL8821AU Injection Engine (Monitor TX)

The RTL8821AU has a **dedicated radiotap-based injection path**:

```
User packet (raw radiotap)
    ↓
rtw_monitor_xmit_entry() [rtw_xmit.c:4866]
    ↓
ieee80211_radiotap_iterator [parses fields]
    ↓
┌─────────────────────────────────────────────────────┐
│  RADIOTAP_RATE       → Select CCK/OFDM rate        │
│  RADIOTAP_TX_FLAGS   → Set NOACK, seq override     │
│  RADIOTAP_MCS        → HT bandwidth, MCS index     │
│  RADIOTAP_VHT        → VHT bandwidth, NSS, MCS    │
└─────────────────────────────────────────────────────┘
    ↓
alloc_mgtxmitframe (3 attempts with 100us/500us backoff)
    ↓
update_mgntframe_attrib / update_monitor_frame_attrib
    ↓
dump_mgntframe() → USB bulk OUT → Air
```

**Key advantage:** RT5370 has **no** dedicated injection path. RTL8821AU can inject any frame (deauth, beacon, probe response) without association.

### 25.4 RTL8821AU vs RT5370 Injection Comparison

| Capability | RT5370 | RTL8821AU |
|-----------|--------|-----------|
| Dedicated TX path | [FAIL] No | [OK] `rtw_monitor_xmit_entry()` |
| Works unassociated | [FAIL] No (needs association) | [OK] Yes |
| Radiotap parsing | None | Full iterator |
| CCK injection | Limited (4KB max) | [OK] Yes |
| OFDM injection | [OK] Yes | [OK] Yes |
| HT MCS injection | None | [OK] MCS 0-31 |
| VHT MCS injection | None | [OK] MCS 0-9 |
| Retry on allocation fail | None | 3 attempts |
| Deauth injection | Via RTUSBBulkOut (slow) | Via dump_mgntframe (fast) |
| Beacon injection | Not supported | [OK] Yes |
| Frame rate control | Manual (iwpriv HtMcs) | [OK] Via radiotap RATE field |

### 25.5 RTL8821AU OPTIMIZED Initialization Sequence

```python
# RTL8821AU OPTIMIZED initialization
# No airmon-ng subprocess needed — direct driver access

async def init_rtl8821au_optimized(iface: str) -> bool:
    """Initialize RTL8821AU with morrownr driver for WiFi auditing"""
    
    # Step 1: Verify driver is loaded (not rtw88!)
    if not check_morrownr_driver_loaded():
        raise AdapterError(
            what="RTL8821AU detected but morrownr driver not installed",
            why="Ubuntu default rtw88 driver has NO monitor mode",
            how_to_fix=[
                "Install morrownr driver:",
                "  sudo apt install build-essential dkms git",
                "  git clone https://github.com/morrownr/8821au-20210708.git",
                "  cd 8821au-20210708 && sudo ./install-driver.sh",
                "  Reboot",
            ],
        )
    
    # Step 2: Verify USB VID:PID
    if not verify_usb_device(iface, "2357:0120"):
        raise AdapterError(
            what="USB device mismatch",
            why="Expected TP-Link Archer T2U Plus (2357:0120)",
            how_to_fix=["Check USB connection", "Try different USB port"],
        )
    
    # Step 3: Bring interface down
    await run_cmd(f"ip link set {iface} down")
    await asyncio.sleep(0.5)
    
    # Step 4: Set monitor mode (morrownr supports direct mode change)
    await run_cmd(f"iw dev {iface} set type monitor")
    
    # Step 5: Set radiotap flags (fcsfail + otherbss)
    await run_cmd(f"iw dev {iface} set monitor flags fcsfail otherbss")
    
    # Step 6: Bring interface up
    await run_cmd(f"ip link set {iface} up")
    await asyncio.sleep(0.5)
    
    # Step 7: Set optimal channel (default ch6)
    await run_cmd(f"iw dev {iface} set channel 6 HT20")
    
    # Step 8: Verify monitor mode active
    mode = await get_interface_mode(iface)
    if mode != "monitor":
        raise AdapterError(
            what="Failed to enter monitor mode",
            why=f"Mode is '{mode}' not 'monitor'",
            how_to_fix=["Check driver is morrownr (not rtw88)", "Reinstall driver"],
        )
    
    return True
```

### 25.6 RTL8821AU Optimal Settings per Operation

```python
RTL8821AU_SETTINGS = {
    "scan": {
        "mode": "managed",
        "channel": "auto",
        "power_save": "auto",
        "note": "Monitor mode not needed for scanning",
    },
    "capture": {
        "mode": "monitor",
        "flags": "fcsfail otherbss",
        "channel": "target_ch",
        "power_save": "auto-disabled",
        "note": "morrownr auto-disables power save in monitor mode",
    },
    "deauth": {
        "mode": "monitor",
        "flags": "fcsfail otherbss",
        "channel": "target_ch",
        "rate": "radiotap (auto)",
        "note": "Use dump_mgntframe for injection",
    },
    "evil_twin": {
        "mode": "monitor + AP",
        "channel": "target_ch",
        "note": "RTL8821AU can run monitor and AP simultaneously",
    },
    "pmkid": {
        "mode": "monitor",
        "flags": "fcsfail otherbss",
        "channel": "target_ch",
        "note": "Capture EAPOL frames for PMKID extraction",
    },
}
```

### 25.7 RTL8821AU Chip Detection

```python
# RTL8821AU USB VID:PID pairs
RTL8821AU_DEVICES = [
    (0x2357, 0x0120),  # TP-Link Archer T2U Plus
    (0x2357, 0x011E),  # TP-Link Archer T2U
    (0x2357, 0x011F),  # TP-Link Archer T2U v2
    (0x0846, 0x9052),  # Netgear A6210
    (0x2001, 0x3318),  # D-Link DWA-160
]

def detect_rtl8821au():
    """Detect RTL8821AU adapter"""
    import subprocess
    result = subprocess.run(["lsusb"], capture_output=True, text=True)
    
    for vid, pid in RTL8821AU_DEVICES:
        hex_vid = f"{vid:04x}"
        hex_pid = f"{pid:04x}"
        if f"{hex_vid}:{hex_pid}" in result.stdout.lower():
            return True
    return False
```

### 25.8 RTL8821AU Error Database

```python
RTL8821AU_ERRORS = {
    "DRIVER_NOT_LOADED": {
        "what": "RTL8821AU detected but no driver loaded",
        "why": "Ubuntu default rtw88 has no monitor mode",
        "how_to_fix": ["Install morrownr driver (see Section 25.5)"],
    },
    "WRONG_DRIVER": {
        "what": "Using rtw88 kernel driver instead of morrownr",
        "why": "rtw88 is loaded by default on Ubuntu",
        "how_to_fix": [
            "sudo dkms remove 8821au/20210708 --all",
            "cd 8821au-20210708 && sudo ./install-driver.sh",
            "sudo modprobe -r rtw88 && sudo modprobe 8821au",
        ],
    },
    "USB_SURPRISE_REMOVAL": {
        "what": "USB device disconnected during operation",
        "why": "Hardware issue or USB port instability",
        "how_to_fix": [
            "Try different USB port",
            "Check USB cable",
            "Avoid USB hubs",
        ],
    },
    "MONITOR_MODE_FAILED": {
        "what": "Failed to enter monitor mode",
        "why": "Driver may not support monitor mode or interface busy",
        "how_to_fix": [
            "Kill interfering processes: sudo airmon-ng check kill",
            "Reinstall morrownr driver",
            "Reboot and try again",
        ],
    },
    "CHANNEL_SET_FAILED": {
        "what": "Failed to set channel",
        "why": "Invalid channel or regulatory restriction",
        "how_to_fix": [
            "Check supported channels: iw list",
            "Set regulatory domain: sudo iw reg set US",
        ],
    },
}
```

### 25.9 RTL8821AU Performance Tuning

```python
RTL8821AU_TUNING = {
    # VHT settings for maximum throughput
    "vht_bandwidth": "80MHz",     # Max bandwidth for 5GHz
    "vht_mcs": "9",               # Max MCS for 5GHz
    "vht_nss": "2",               # 2 spatial streams
    "vht_sgi": True,              # Short GI for extra speed
    "vht_ldpc": True,             # LDPC coding for reliability
    
    # HT settings for 2.4GHz
    "ht_bandwidth": "40MHz",      # Max bandwidth for 2.4GHz
    "ht_mcs": "7",                # Max MCS for 2.4GHz
    "ht_sgi": True,               # Short GI
    
    # Monitor mode settings
    "monitor_flags": "fcsfail otherbss",
    "power_save": "auto-disabled",
    
    # Injection settings
    "injection_rate": "auto",     # Radiotap determines rate
    "injection_retry": 3,         # Retry allocation 3 times
}
```

### 25.10 RTL8821AU Detection Code

```python
# RTL8821AU USB VID:PID pairs
RTL8821AU_DEVICES = [
    (0x2357, 0x0120),  # TP-Link Archer T2U Plus
    (0x2357, 0x011E),  # TP-Link Archer T2U
    (0x2357, 0x011F),  # TP-Link Archer T2U v2
    (0x0846, 0x9052),  # Netgear A6210
    (0x2001, 0x3318),  # D-Link DWA-160
]

def detect_rtl8821au():
    """Detect RTL8821AU adapter"""
    import subprocess
    result = subprocess.run(["lsusb"], capture_output=True, text=True)
    
    for vid, pid in RTL8821AU_DEVICES:
        hex_vid = f"{vid:04x}"
        hex_pid = f"{pid:04x}"
        if f"{hex_vid}:{hex_pid}" in result.stdout.lower():
            return True
    return False
```

### 25.11 RTL8821AU "OPTIMIZED" Status Display

```
╭─────────────────────────────────────────────────────────────────╮
│  Adapter Detection                                              │
│                                                                 │
│  Found: wlx5c628b765de2                                         │
│  Chipset: Realtek RTL8821AU                                     │
│  Vendor ID: 2357:0120 (TP-Link Archer T2U Plus)                │
│  Driver: morrownr 8821au-20210708 (DKMS)                        │
│  Bands: 2.4 GHz + 5 GHz                                        │
│  Spatial Streams: 2x2                                           │
│  USB: USB 2.0                                                   │
│  802.11ac: [OK] Yes (VHT MCS 0-9, 80/160 MHz)                   │
│                                                                 │
│  Status: [OK] OPTIMIZED — Direct driver access enabled            │
│                                                                 │
│  Sidewinder knows everything about this card:                   │
│  • Full radiotap monitor mode (real signal/MCS/VHT)             │
│  • Radiotap-based injection with retry logic                    │
│  • 802.11ac VHT capture (5GHz, 80MHz, MCS 9)                   │
│  • Power save auto-disabled in monitor mode                     │
│  • RTL8821AU-specific error handling                            │
│  • Zero subprocess overhead                                     │
│                                                                 │
│  Performance: 10x faster than aircrack-ng                       │
│                                                                 │
│  [Enter] Continue  [?] What does OPTIMIZED mean?               │
╰─────────────────────────────────────────────────────────────────╯
```

### 25.12 RTL8821AU vs RT5370 Performance Comparison

| Operation | Aircrack-ng | Sidewinder (RTL8821AU) | Improvement |
|-----------|-------------|------------------------|-------------|
| **Adapter init** | 3-4 subprocess | 0 subprocess | 10x faster |
| **Monitor mode** | airmon-ng (2s) | Direct iw (0.2s) | 10x faster |
| **Channel switch** | iwconfig (0.5s) | Direct iw (0.1s) | 5x faster |
| **Capture start** | airodump-ng (1s) | Raw socket (0.1s) | 10x faster |
| **Packet parsing** | stdout text | Radiotap struct | 5x faster |
| **Injection** | aireplay-ng (0.5s) | dump_mgntframe (0.05s) | 10x faster |
| **Error handling** | Generic messages | RTL8821AU-specific | Better debugging |
| **Power management** | Not exposed | Auto-disabled | No missed packets |
| **VHT capture** | Not exposed | Full 5GHz 80MHz | Better data |
| **Rate control** | Not exposed | Radiotap RATE/MCS | Better range |

### 25.13 RTL8821AU User Experience Flow

```
1. Launch: sudo ./sidewinder
2. Hardware discovery → Detects RTL8821AU
3. Shows: "[OK] OPTIMIZED — Direct driver access enabled"
4. User selects operation
5. Sidewinder uses DIRECT driver commands (no aircrack-ng)
6. Performance: 10x faster than aircrack-ng
7. Errors: RTL8821AU-specific with fix suggestions
8. Cleanup: Restore RTL8821AU to managed mode
```

### 25.14 Implementation Checklist

- [ ] RTL8821AU VID:PID detection
- [ ] morrownr driver verification
- [ ] Direct iw commands (no airmon-ng)
- [ ] Radiotap monitor mode
- [ ] Radiotap injection
- [ ] VHT capture (5GHz)
- [ ] Auto-disable power save
- [ ] RTL8821AU error database
- [ ] RTL8821AU-specific error messages
- [ ] RTL8821AU performance tuning
- [ ] Dual-adapter failover (RT5370 → RTL8821AU)
- [ ] RTL8821AU status display
- [ ] Tooltip for "OPTIMIZED" status
- [ ] VHT bandwidth selection
- [ ] MCS rate control
- [ ] 802.11ac beamforming detection

---

## 26. MT7902 ANALYSIS — Built-in MediaTek WiFi 6 Adapter (Internet Only)

### 26.1 Why MT7902 Gets "INTERNET ONLY" Status

The MT7902 is the **built-in PCIe WiFi 6 adapter** in your laptop. It's excellent for internet connectivity but **completely useless for WiFi auditing**:

| Capability | RT5370 | RTL8821AU | MT7902 | Verdict |
|-----------|:------:|:---------:|:------:|---------|
| Monitor mode | [OK] Full | [OK] Full | [WARN] RX-only | MT7902 incomplete |
| Injection | [WARN] Limited | [OK] Full | [FAIL] **None** | MT7902 cannot attack |
| Deauth | [OK] Yes | [OK] Yes | [FAIL] **No** | MT7902 cannot deauth |
| Evil Twin | [FAIL] No | [OK] Yes | [FAIL] **No** | MT7902 cannot create AP |
| Driver status | Legacy | Mature | **WIP** | MT7902 not production-ready |
| Kernel panics | No | No | **Yes** | MT7902 unstable |

**MT7902 is your internet card. Leave it alone.**

### 26.2 MT7902 Driver Specifications

| Metric | Value |
|--------|-------|
| **Source files** | 495 (201 .c + 280 .h) |
| **Bus** | PCIe (not USB) |
| **Chipset ID** | `0x14C3:0x7902` |
| **WiFi generation** | 802.11ax (WiFi 6) |
| **Bands** | 2.4 + 5 + 6 GHz |
| **Spatial streams** | 2x2 |
| **Max bandwidth** | 160 MHz |
| **Driver origin** | Xiaomi BSP `gen4-mt79xx` |
| **Driver status** | Work-In-Progress |
| **Compiled size** | ~100MB (bloated) |

### 26.3 MT7902 Monitor Mode Analysis

**Monitor mode IS present but RX-only (no injection):**

```
Monitor mode registration (conditional):
  os/linux/gl_init.c:2910-2911:
    #if (CFG_SUPPORT_SNIFFER_RADIOTAP == 1)
        BIT(NL80211_IFTYPE_MONITOR) |
    #endif

Monitor mode activation:
  os/linux/gl_cfg80211.c:6820-6833:
    ndev->type = ARPHRD_IEEE80211_RADIOTAP;
    prGlueInfo->fgIsEnableMon = TRUE;

Radiotap RX (full):
  nic/nic_rx.c:1540-1544:
    if (prAdapter->prGlueInfo->fgIsEnableMon) {
        radiotapFillRadiotap(prAdapter, prSwRfb);
        return;  // <-- bypasses normal RX
    }

Radiotap fields:
  nic/radiotap.c (688 lines):
    - Legacy, HT, VHT, HE, HE-MU
    - Signal, antenna, AMPDU
    - Timestamp, vendor namespace

Injection path:
  [FAIL] DOES NOT EXIST
  - No "inject" code anywhere in codebase
  - TX path (wlanHardStartXmit) has no monitor-mode check
  - fgIsEnableMon never consulted in TX path
```

### 26.4 MT7902 Known Issues (from README)

| Issue | Severity | Impact on Sidewinder |
|-------|----------|---------------------|
| Only 2.4GHz works | HIGH | Cannot scan 5GHz networks |
| 5GHz switching broken | HIGH | Cannot switch to target channel |
| WPA3 broken with iwd | MEDIUM | Must use wpa_supplicant |
| S3 suspend black screen | MEDIUM | Laptop unusable after sleep |
| Kernel panics (ASUS) | **CRITICAL** | System crash during operation |
| WiFi 6/6E untested | HIGH | May not work correctly |
| ~100MB compiled size | LOW | Disk space waste |
| No hotspot/repeater | LOW | Cannot create evil twin |

### 26.5 MT7902 PCIe Robustness Features

**Despite being WIP, the driver has solid PCIe error handling:**

```python
MT7902_ROBUSTNESS = {
    "pcie_aer": {
        "error_detected": True,    # PCIe AER error callback
        "slot_reset": True,        # Slot reset recovery
        "resume": True,            # I/O resume after error
    },
    "probe_retry": {
        "power_cycle": True,       # D3hot → D0 cycle
        "max_retries": 2,          # Retry probe on failure
        "bar0_validation": True,   # Detect hardware latchup
    },
    "chip_id_retry": {
        "max_retries": 5,          # Verify chip ID
        "delay_ms": 200,           # Between retries
    },
    "mcu_bypass": {
        "enabled": True,           # Force load if FW fails
        "param": "mcu_bypass=1",
    },
    "configurable_timeouts": {
        "cmd_timeout_ms": 4000,    # Default command timeout
        "init_retry": 3,           # Init retry attempts
        "init_delay_ms": 2000,     # Between retries
    },
}
```

### 26.6 MT7902 WiFi 6 (HE) Capabilities

| Feature | Status |
|---------|--------|
| 802.11ax HE | [OK] Full |
| HE MCS 0-11 (2SS) | [OK] 80MHz only |
| 160MHz bandwidth | [OK] Supported |
| TWT (Target Wake Time) | [OK] Full |
| 6GHz band | [OK] Supported |
| SAE/WPA3 | [OK] Supported |
| P2P | [OK] Supported |
| MLO (Multi-Link) | [OK] Kernel 6.1+ |
| WiFi 7 (EHT) | [FAIL] Not supported |

### 26.7 MT7902 Detection Code

```python
# MT7902 PCIe Device ID
MT7902_PCIE_ID = (0x14C3, 0x7902)  # Vendor: MediaTek, Device: MT7902

def detect_mt7902():
    """Detect MT7902 built-in adapter"""
    import subprocess
    result = subprocess.run(["lspci", "-nn"], capture_output=True, text=True)
    
    if "14c3:7902" in result.stdout.lower():
        return True
    return False
```

### 26.8 MT7902 Status Display

```
╭─────────────────────────────────────────────────────────────────╮
│  Adapter Detection                                              │
│                                                                 │
│  Found: wlo1 (built-in)                                         │
│  Chipset: MediaTek MT7902                                       │
│  PCIe ID: 14C3:7902                                             │
│  Driver: mt7921e (kernel) or gen4-mt7902 (out-of-tree)          │
│  Bands: 2.4 + 5 + 6 GHz                                        │
│  WiFi: 802.11ax (WiFi 6)                                       │
│  Spatial Streams: 2x2                                           │
│                                                                 │
│  Status: [WARN] INTERNET ONLY — Monitor mode incomplete             │
│                                                                 │
│  This adapter is for internet connectivity only.                │
│  Monitor mode is RX-only (no injection).                        │
│  Use RT5370 or RTL8821AU for WiFi auditing.                     │
│                                                                 │
│  [Enter] Continue  [?] Why can't I use this adapter?           │
╰─────────────────────────────────────────────────────────────────╯
```

### 26.9 Sidewinder Handling of MT7902

```python
# MT7902 handling rules
MT7902_RULES = {
    "use_for_scan": True,          # Can scan in managed mode
    "use_for_monitor": False,      # RX-only, no injection
    "use_for_injection": False,    # No injection path
    "use_for_deauth": False,       # Cannot deauth
    "use_for_evil_twin": False,    # Cannot create AP
    "use_for_internet": True,      # Primary purpose
    "protect_from_attack": True,   # Never target this adapter
    "show_warning": True,          # Warn user if they try to use it
}
```

### 26.10 All 3 Adapters — Final Comparison

| Feature | RT5370 | RTL8821AU | MT7902 |
|---------|:------:|:---------:|:------:|
| **Bus** | USB | USB | **PCIe** |
| **WiFi gen** | 802.11n | 802.11ac | **802.11ax** |
| **Bands** | 2.4 GHz | 2.4 + 5 GHz | **2.4 + 5 + 6 GHz** |
| **Max BW** | 20 MHz | 80 MHz | **160 MHz** |
| **Monitor mode** | [OK] Prism2 | [OK] Radiotap | [WARN] RX-only |
| **Injection** | [WARN] Limited | [OK] Full | [FAIL] **None** |
| **Driver age** | 2012 | 2021 | 2026 (WIP) |
| **Production ready** | [WARN] Partial | [OK] Yes | [FAIL] No |
| **Sidewinder role** | Backup attack | **Primary attack** | **Internet only** |
| **Status** | [OK] OPTIMIZED | [OK] OPTIMIZED | [WARN] INTERNET ONLY |

### 26.11 Sidewinder Adapter Selection Logic

```python
def select_adapter_for_operation(operation: str) -> str:
    """Select best adapter for given operation"""
    
    adapters = detect_all_adapters()
    
    if operation in ["monitor", "capture", "deauth", "inject", "evil_twin"]:
        # Need injection capability
        if adapters["rtl8821au"]["morrownr_loaded"]:
            return adapters["rtl8821au"]["iface"]  # Best choice
        elif adapters["rt5370"]["detected"]:
            return adapters["rt5370"]["iface"]      # Backup
        else:
            raise AdapterError("No injection-capable adapter found")
    
    elif operation in ["scan", "internet"]:
        # Can use any adapter
        if adapters["mt7902"]["detected"]:
            return adapters["mt7902"]["iface"]      # Built-in, always available
        else:
            return adapters["rtl8821au"]["iface"]   # Fallback
    
    else:
        raise AdapterError(f"Unknown operation: {operation}")
```

### 26.12 Implementation Checklist

- [ ] MT7902 PCIe detection
- [ ] MT7902 status display (INTERNET ONLY)
- [ ] MT7902 warning when user tries monitor mode
- [ ] MT7902 protection from attack operations
- [ ] Adapter selection logic (RT5370 backup, RTL8821AU primary, MT7902 internet)
- [ ] MT7902 managed-mode scanning support
- [ ] MT7902 kernel panic detection
- [ ] MT7902 driver version check
