# SWCLI — Shortcomings vs Current Adapter-Aware Implementation

> **Problem:** SWCLI pipelines execute generic iw/ip commands for all adapters.
> The current adapter classes apply chipset-specific optimizations derived from
> deep driver analysis (8821au, RT5572, mt7902, rtw88 source in `DriversAnalysis/`).
> SWCLI ignores these, resulting in slower capture, dropped packets, and failed operations.

---

## 1. Missing Per-Chipset Monitor Mode Entry

### Current (correct):

```
RT5370:    mac80211 VIF path → power_save off → OFDM rate → iwpriv CAM
RTL8821AU: morrownr check → type-in-place → radiotap fcsfail+otherbss
MT7902:    BLOCKED with actionable error
```

### SWCLI (wrong):

```
ALL adapters: ip link down → iw phy add type monitor → ip link up → set channel
```

**Impact:** RT5370 keeps power save ON (drops 30-50% of beacons). RTL8821AU skips radiotap flags (no FCS-failed frame capture). MT7902 is never blocked — user wastes time on a card that can't inject.

### Fix required:

SWCLI `monitor <interface>` must detect chipset and delegate to the correct adapter class method, not run raw iw commands.

---

## 2. No Power Save Disable (RT5370)

### Current (`rt5370.py:116`):

```python
await set_power_save(mon_iface, enable=False)
```

### SWCLI:

No power_save command anywhere in pipeline.

**Impact:** RT5370 enters power save during capture. Card sleeps between beacons. You miss handshake M1/M3 frames sent by the AP. Capture fails silently — no error, just no data.

---

## 3. No Radiotap Flags (RTL8821AU)

### Current (`rtl8821au.py:145-148`):

```python
await run(["iw", "dev", mon_iface, "set", "monitor", "fcsfail", "otherbss"])
```

### SWCLI:

No `set monitor fcsfail otherbss` in pipeline.

**Impact:**
- `fcsfail` — Without this, frames with bad FCS are discarded. You lose corrupted frames that still contain valid EAPOL data.
- `otherbss` — Without this, frames from other BSSes on the same channel are dropped. Injection targeting fails because you can't see the client's response.

---

## 4. No morrownr Driver Detection (RTL8821AU)

### Current (`rtl8821au.py:39-64, 129-138`):

```python
if not await detect_rtl8821au_morrownr():
    if await detect_rtw88_loaded():
        raise RuntimeError("rtw88 driver loaded — monitor mode not supported")
```

### SWCLI:

No driver check. Runs `iw` commands blindly.

**Impact:** If rtw88 is loaded (Ubuntu default), `iw dev set type monitor` fails silently or the interface appears in monitor mode but can't inject. User spends 20 minutes debugging before realizing the wrong driver is loaded.

---

## 5. No VHT80 on 5GHz (RTL8821AU)

### Current (`rtl8821au.py:174-177`):

```python
if channel >= 36:
    await set_channel(iface, channel, bandwidth="80MHz")
else:
    await set_channel(iface, channel, bandwidth="HT20")
```

### SWCLI:

Always uses default channel width (20MHz).

**Impact:** 5GHz capture runs at 20MHz instead of 80MHz. Throughput is 4x lower. On busy 5GHz networks with multiple APs on adjacent channels, 20MHz picks up more interference.

---

## 6. No iwpriv Legacy Fallback (RT5370)

### Current (`rt5370.py:124-140`):

```python
which_result = await run(["which", "iwpriv"], timeout=3, check=False)
if which_result.returncode == 0:
    for cmd_arg in ["PSMode=CAM", "FixedTxMode=OFDM", "HtMcs=0"]:
        await run(["iwpriv", mon_iface, "set", cmd_arg], check=False)
```

### SWCLI:

No iwpriv commands. No kernel version detection.

**Impact:** On kernels < 5.0 (older Kali, Debian), RT5370 doesn't get CAM mode or OFDM rate lock. Capture quality degrades on legacy systems where iwpriv is the only way to control power save.

---

## 7. No CARD_SETTINGS Application

### Current (`base.py:14-34`):

```python
CARD_SETTINGS = {
    "RT5370":    {"capture": {"power_save": "off", "htmcs": "0", "rate": "OFDM"}},
    "RTL8821AU": {"capture": {"flags": "fcsfail otherbss", "band": "auto"}},
    "MT7902":    {"capture": None},
}
```

### SWCLI:

Documents the matrix (`SWCLI_CONTEXT.md:814-836`) but never reads or applies it.

**Impact:** The settings matrix is dead documentation. Every adapter gets the same generic treatment regardless of what the driver analysis proved is optimal.

---

## 8. No Failover on Adapter Failure

### Current (`adapters/__init__.py:72-110`):

```python
class FailoverManager:
    async def execute_with_failover(self, func, *args):
        try:
            return await func(self._primary, *args)
        except Exception:
            return await func(self._backup, *args)
```

### SWCLI:

User must manually detect failure, pick another adapter, and restart.

**Impact:** If RTL8821AU disconnects mid-capture (USB flaky), SWCLI crashes. User must notice, run `swcli adapters` again, re-enter monitor mode on RT5370, and restart capture from scratch. Lost 5+ minutes.

---

## 9. No Adapter Priority Auto-Selection

### Current (`adapter.py:269-300`):

```python
def get_best_adapter(adapters, operation):
    # RTL8821AU (10) > RTL8812AU (9) > RT5370 (5) > MT7902 (1)
```

### SWCLI:

User must manually specify which adapter to use for every command.

**Impact:** User might pick MT7902 for capture (can't), or RT5370 for 5GHz (doesn't support it). No guidance on which card is best for the operation.

---

## 10. No Injection Rate/Mode Optimization

### Current (`base.py:18-19`):

```python
"RT5370": {"inject": {"power_save": "off", "rate": "OFDM", "mcs": "0"}},
```

### SWCLI:

aireplay-ng runs with default rate settings.

**Impact:** RT5370 deauth frames sent at CCK rate (1 Mbps) instead of OFDM (6 Mbps). CCK has shorter range, lower throughput. Deauth takes more retries to reach the target AP.

---

## 11. No Cleanup of Adapter-Specific State

### Current:

Each adapter class tracks its `_mon_iface` and cleans up on exit.

### SWCLI:

User must remember and pass the monitor interface name to every cleanup command.

**Impact:** If user forgets `swcli monitor stop`, the monitor VIF stays up. Next `swcli adapters` shows a phantom monitor interface. No automatic state tracking.

---

## Summary: What SWCLI Must Add

| Shortcoming | Fix | Files to change |
|-------------|-----|-----------------|
| Generic monitor entry | Detect chipset, call adapter-specific `enter_monitor()` | `SWCLI_PIPELINES.md` §2.1 |
| No power save disable | Add `iw dev set power_save off` for RT5370 | `SWCLI_PIPELINES.md` §2.1 |
| No radiotap flags | Add `iw dev set monitor fcsfail otherbss` for RTL8821AU | `SWCLI_PIPELINES.md` §2.1 |
| No driver detection | Check `lsmod` for morrownr vs rtw88 before monitor entry | `SWCLI_PIPELINES.md` §2.1 |
| No VHT80 on 5GHz | Set `bandwidth="80MHz"` for channels >= 36 | `SWCLI_PIPELINES.md` §2.1 |
| No iwpriv fallback | Detect kernel version, apply iwpriv if < 5.0 | `SWCLI_PIPELINES.md` §2.1 |
| Dead CARD_SETTINGS | Wire settings matrix into execution flow | `SWCLI_PIPELINES.md` §2.1, §4.1 |
| No failover | Implement `execute_with_failover` in CLI layer | New: `SWCLI_PIPELINES.md` §8 |
| No priority selection | Auto-suggest best adapter per operation | `SWCLI_PIPELINES.md` §1.1 |
| No injection optimization | Apply CARD_SETTINGS rate/mcs before aireplay-ng | `SWCLI_PIPELINES.md` §5.1 |
| No adapter state tracking | Store mon_iface in session, auto-cleanup on exit | `SWCLI_PIPELINES.md` §7.1 |

---

## Root Cause

SWCLI was designed as a **generic command executor** (like airmon-ng + airodump-ng).
The current adapter classes are **chipset-aware engines** (like a custom firmware).

The gap is that SWCLI treats all adapters as identical hardware.
The driver analysis in `DriversAnalysis/` proved they are not.
