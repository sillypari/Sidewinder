# Sidewinder — Implementation Tracker

**Last Updated:** 2026-06-05  
**Version:** v0.7.0  
**Implementation follows:** [IMPLEMENTATION.md](./IMPLEMENTATION.md)  
**Bug tracker:** [Bug.md](../Bug.md)

---

## Legend

| Symbol | Meaning |
|--------|---------|
| [OK] | Working — tested, no known bugs |
| 🔧 | In Progress — being built right now |
| [WARN] | Buggy — implemented but has known issues |
| [FAIL] | Not Started |
| 🔒 | Blocked — depends on something else |
| ⏭️ | Deferred — intentionally skipped to later phase |

---

## Phase 1: Core Pipeline

### 1.1 Project Structure + Dependencies
| Item | Status | Notes |
|------|--------|-------|
| Directory layout | [OK] | `sidewinder/core/`, `adapters/`, `ui/`, `tests/` |
| `pyproject.toml` (textual, scapy) | [OK] | textual>=0.40, scapy>=2.5 |
| `sidewinder.py` entry point | [OK] | Root check + tool check + session resume + logging + TUI launch |
| `Makefile` | [FAIL] | Not started |
| `README.md` | [FAIL] | Not started |

### 1.2 Adapter Detection System
| Item | Status | Notes |
|------|--------|-------|
| sysfs reads (PHY, driver, VID/PID, MAC) | [WARN] | `core/adapter.py` (298 lines) — sysfs reads still synchronous (BUG-009) |
| lsusb/lspci chipset detection | [OK] | `core/adapter.py` — async via SubprocessManager |
| iw capability detection | [OK] | `core/adapter.py` — async via SubprocessManager |
| KNOWN_DEVICES registry (RT5370, RTL8821AU, MT7902) | [OK] | `core/adapter.py` |
| Async adapter detection pipeline | [OK] | `core/adapter.py`, `adapters/__init__.py` |
| Unit tests | [OK] | `tests/test_adapter.py` (cross-platform skip) |

### 1.3 Subprocess Manager
| Item | Status | Notes |
|------|--------|-------|
| `SubprocessManager.run()` with process group isolation | [OK] | `core/subprocess_mgr.py` (286 lines) |
| `SubprocessManager.stream()` for real-time output | [OK] | `core/subprocess_mgr.py` |
| SIGTERM → 0.5s → SIGKILL teardown | [OK] | `core/subprocess_mgr.py` |
| Zombie prevention (`start_new_session=True`) | [OK] | `core/subprocess_mgr.py` |
| Unit tests | [OK] | `tests/test_subprocess.py` (cross-platform skip) |

### 1.4 Monitor Mode (Native iw/ip)
| Item | Status | Notes |
|------|--------|-------|
| `enter_monitor_mode()` (standard mac80211 path) | [OK] | `core/monitor.py` (264 lines) |
| `exit_monitor_mode()` | [OK] | `core/monitor.py` |
| Bad driver fallback (`enter_monitor_mode_bad_driver`) | [OK] | `core/monitor.py` |
| Channel lock + verification | [OK] | `core/monitor.py` |
| TX power setting (3000 mW) | [OK] | `core/monitor.py` |
| Interface type=803 verification | [OK] | `core/monitor.py` |
| Unit tests | [OK] | `tests/test_monitor.py` (cross-platform skip) |

### 1.5 Service Management
| Item | Status | Notes |
|------|--------|-------|
| Kill conflicting processes (NM, wpa_supplicant, dhclient) | [OK] | `core/services.py` (225 lines) |
| `ServiceManager.restore()` with readiness poll | [OK] | `core/services.py` |
| `systemctl is-active` verification loop | [OK] | `core/services.py` |
| Unit tests | [OK] | `tests/test_services.py` (cross-platform skip) |

### 1.6 Scan Engine (Airodump-ng Parser)
| Item | Status | Notes |
|------|--------|-------|
| `Network` + `Client` dataclasses | [OK] | `core/session.py` |
| Airodump-ng stdout state machine parser | [OK] | `core/scanner.py` (261 lines) |
| Real-time 1s refresh | [OK] | `core/scanner.py` |
| Hidden SSID handling | [OK] | `core/scanner.py` |
| WPS detection | [OK] | `core/scanner.py` |
| `import os` at module top level | [WARN] | Still inside `scan()` method body (BUG-013) |
| Unit tests | [FAIL] | `tests/test_scanner.py` not created yet |

### 1.7 Target Selection
| Item | Status | Notes |
|------|--------|-------|
| `lock_channel()` with verification | [OK] | `core/monitor.py` |
| Channel lock verification (`iw dev info`) | [OK] | `core/monitor.py` |
| Target data model | [OK] | `core/session.py` (`Network` dataclass) |

### 1.8 Capture Engine
| Item | Status | Notes |
|------|--------|-------|
| `capture_passive()` — starts airodump-ng | [OK] | `core/capture.py` (351 lines) |
| `poll_eapol()` — separate async task polling PCAP | [WARN] | `core/capture.py` — PcapReader never closed (BUG-019) |
| `capture_deauth()` — explicit channel, 1s startup delay | [OK] | `core/capture.py` |
| PCAP file polling (every 2s) | [OK] | `core/capture.py` |
| 5-min timeout | [OK] | `core/capture.py` |
| SHA-256 via `with open()` | [OK] | `core/capture.py` — fixed (BUG-020) |
| `on_progress` typed as Callable | [OK] | `core/capture.py` — fixed (BUG-017) |
| Unit tests | [OK] | `tests/test_capture.py` (cross-platform skip) |

### 1.9 EAPOL Validation
| Item | Status | Notes |
|------|--------|-------|
| `is_m1/m2/m3/m4()` — correct IEEE 802.11-2020 bitmasks | [OK] | `core/capture.py` |
| `validate_handshake()` via scapy | [OK] | `core/capture.py` |
| `HandshakeResult` dataclass | [OK] | `core/session.py` |
| SHA-256 computation | [OK] | `core/capture.py` |
| Unit tests | [OK] | `tests/test_capture.py` (cross-platform skip) |

### 1.10 Crack Engine
| Item | Status | Notes |
|------|--------|-------|
| `crack_aircrack()` with progress streaming | [OK] | `core/cracker.py` (294 lines) |
| `crack_hashcat()` with hcxpcapngtool conversion | [OK] | `core/cracker.py` |
| `read_hashcat_potfile()` — hash-to-BSSID matching | [OK] | `core/cracker.py` |
| Progress parsing (keys/s, ETA, current key) | [OK] | `core/cracker.py` |
| `CrackResult` dataclass | [OK] | `core/session.py` |
| Unit tests | [OK] | `tests/test_cracker.py` |

### 1.11 Cleanup System
| Item | Status | Notes |
|------|--------|-------|
| `cleanup()` — kills processes, deletes VIF, restores managed | [OK] | `core/cleanup.py` (173 lines) |
| `cleanup_files()` — temp file removal with confirmation | [OK] | `core/cleanup.py` |
| Signal handlers (SIGINT/SIGTERM) | [OK] | `sidewinder.py` (sync + async) |
| `loop=` deprecated param removed | [OK] | `core/cleanup.py` — fixed (BUG-016) |
| `action_cleanup()` wired in UI | [OK] | `ui/app.py` — fixed (BUG-014) |
| Unit tests | [FAIL] | `tests/test_cleanup.py` not created yet |

### 1.12 Deauth Attack Module
| Item | Status | Notes |
|------|--------|-------|
| `DeauthConfig` dataclass | [OK] | `attacks/deauth.py` |
| `DeauthResult` dataclass | [OK] | `attacks/deauth.py` |
| `run_deauth()` — full attack flow | [OK] | `attacks/deauth.py` |
| Rate limiting (count + bursts + cooldown) | [OK] | `attacks/deauth.py` |
| Adapter injection validation | [OK] | `attacks/deauth.py` |
| `on_progress` typed as Callable | [OK] | `attacks/deauth.py` — fixed (BUG-018) |
| Unused imports cleaned | [OK] | `attacks/deauth.py` — fixed (BUG-024) |
| `detect_adapter()` called with await | [WARN] | Missing await (BUG-042) |
| Unit tests | [FAIL] | Not created yet |

### 1.13 Error Classification + Session Management
| Item | Status | Notes |
|------|--------|-------|
| `Severity` + `Category` enums | [OK] | `core/errors.py` (339 lines) |
| `SidewinderError` dataclass | [OK] | `core/errors.py` |
| `ERROR_DB` with 20+ error types | [OK] | `core/errors.py` |
| Dead `AdapterError` class removed | [OK] | `core/errors.py` — fixed (BUG-022) |
| `Session` dataclass | [OK] | `core/session.py` (249 lines) |
| `Session.save()` | [OK] | `core/session.py` |
| `Session.load()` with nested deserialization | [OK] | `core/session.py` |
| Unit tests | [OK] | `tests/test_errors.py` (18 pass), `tests/test_session.py` (23 pass) |

---

## Phase 2: Card Optimization

### 2.1 Adapter Abstraction Layer
| Item | Status | Notes |
|------|--------|-------|
| `Adapter` ABC with all abstract methods | [OK] | `adapters/base.py` (95 lines) |
| Type checking (pyright-compatible) | [OK] | `adapters/base.py` |

### 2.2 RT5370 Direct Driver
| Item | Status | Notes |
|------|--------|-------|
| Modern `iw` commands (power_save off, bitrates) | [OK] | `adapters/rt5370.py` (171 lines) |
| Legacy `iwpriv` fallback (gated on `which iwpriv`) | [OK] | `adapters/rt5370.py` — async via SubprocessManager |
| `init_rt5370_optimized()` | [OK] | `adapters/rt5370.py` |
| Async `_apply_optimizations()` | [OK] | `adapters/rt5370.py` — fixed (BUG-012) |
| Unit tests | [FAIL] | `tests/test_rt5370.py` not created yet |

### 2.3 RTL8821AU morrownr Detection
| Item | Status | Notes |
|------|--------|-------|
| `detect_rtl8821au_morrownr()` (lsmod check) | [OK] | `adapters/rtl8821au.py` (204 lines) — async via SubprocessManager |
| rtw88 detection + warning | [OK] | `adapters/rtl8821au.py` — async via SubprocessManager |
| Installation steps display | [OK] | `adapters/rtl8821au.py` |
| Unit tests | [FAIL] | `tests/test_rtl8821au.py` not created yet |

### 2.4 RTL8821AU Monitor Mode (Radiotap)
| Item | Status | Notes |
|------|--------|-------|
| `init_rtl8821au_optimized()` | [OK] | `adapters/rtl8821au.py` |
| Radiotap flags (`fcsfail otherbss`) | [OK] | `adapters/rtl8821au.py` |
| Unit tests | [FAIL] | `tests/test_rtl8821au.py` not created yet |

### 2.5 RTL8821AU Injection Engine
| Item | Status | Notes |
|------|--------|-------|
| `inject_deauth()` via aireplay-ng | [OK] | `adapters/rtl8821au.py` |
| Unit tests | [FAIL] | `tests/test_rtl8821au.py` not created yet |

### 2.6 MT7902 Detection + Protection
| Item | Status | Notes |
|------|--------|-------|
| `detect_mt7902()` (lspci check) | [OK] | `adapters/mt7902.py` — async via SubprocessManager |
| `MT7902_RESTRICTIONS` dict | [OK] | `adapters/mt7902.py` |
| `check_adapter_allowed()` | [OK] | `adapters/mt7902.py` |
| `inject_frame()` override — raises SidewinderError | [OK] | `adapters/mt7902.py:130` |
| Unit tests | [FAIL] | `tests/test_mt7902.py` not created yet |

### 2.7 Multi-Adapter Manager
| Item | Status | Notes |
|------|--------|-------|
| `AdapterManager.discover()` | [OK] | `adapters/__init__.py` |
| `get_best_for_operation()` (RTL8821AU > RT5370) | [OK] | `adapters/__init__.py` |
| `get_internet_adapter()` (MT7902 preferred) | [OK] | `adapters/__init__.py` |
| Unit tests | [FAIL] | `tests/test_adapter_manager.py` not created yet |

### 2.8 Adapter-Specific Error Database
| Item | Status | Notes |
|------|--------|-------|
| `ADAPTER_ERRORS` — RT5370-specific messages | [OK] | `core/errors.py` |
| `ADAPTER_ERRORS` — RTL8821AU-specific messages | [OK] | `core/errors.py` |
| `ADAPTER_ERRORS` — MT7902-specific messages | [OK] | `core/errors.py` |
| Unit tests | [OK] | `tests/test_errors.py` (18 pass) |

### 2.9 Dual-Adapter Failover
| Item | Status | Notes |
|------|--------|-------|
| `FailoverManager.setup()` | [OK] | `adapters/__init__.py` |
| `FailoverManager.execute_with_failover()` | [OK] | `adapters/__init__.py` |
| Unit tests | [FAIL] | `tests/test_adapter_manager.py` not created yet |

### 2.10 Performance Tuning Per Card
| Item | Status | Notes |
|------|--------|-------|
| `CARD_SETTINGS` matrix | [OK] | `adapters/base.py` |
| Settings applied per operation | [OK] | `adapters/base.py` |
| Unit tests | [FAIL] | `tests/test_adapter_manager.py` not created yet |

### 2.11 Card-Specific Unit Tests
| Item | Status | Notes |
|------|--------|-------|
| `tests/test_rt5370.py` | [FAIL] | Not created yet |
| `tests/test_rtl8821au.py` | [FAIL] | Not created yet |
| `tests/test_mt7902.py` | [FAIL] | Not created yet |
| `tests/test_adapter_manager.py` | [FAIL] | Not created yet |

### 2.12 Integration Tests
| Item | Status | Notes |
|------|--------|-------|
| `test_full_pipeline_rt5370()` | [FAIL] | Needs all Phase 1+2 complete |
| `test_full_pipeline_rtl8821au()` | [FAIL] | Needs all Phase 1+2 complete |
| MT7902 blocked correctly | [FAIL] | Needs all Phase 1+2 complete |
| Failover test | [FAIL] | Needs all Phase 1+2 complete |

### 2.13 Core Infrastructure Modules
| Item | Status | Notes |
|------|--------|-------|
| `core/rfkill.py` — async rfkill check/unblock | [OK] | 55 lines — clean, not wired in |
| `core/vm.py` — VM detection (WSL, KVM, etc.) | [WARN] | 51 lines — `os.uname()` crashes on Windows (BUG-044), not wired in |
| `core/config.py` — JSON config manager | [WARN] | 68 lines — crashes on unknown keys (BUG-045), path traversal (BUG-046), not wired in |
| `core/logger.py` — TUI-safe rotating file logger | [WARN] | 57 lines — destroys all handlers (BUG-047), None exc_type crash (BUG-048), wired into cli.py |
| `core/attack.py` — BaseAttackEngine ABC | [WARN] | 77 lines — import in hot path (BUG-049), _main_task dead code (BUG-050), entirely unused |
| `cli.py` — argparse CLI entry point | [OK] | 86 lines — wired into __main__.py |
| `__main__.py` — `python -m sidewinder` | [OK] | 9 lines — wired, clean |

---

## Phase 3: UI (Textual TUI)

### 3.1 Textual TUI Framework Setup
| Item | Status | Notes |
|------|--------|-------|
| `SidewinderApp(App)` class | [OK] | `ui/app.py` (144 lines) |
| Vim-style keybindings (j/k/Enter/Esc//) | [OK] | `ui/app.py` |
| Color palette (`colors.tcss`) | [OK] | `ui/colors.tcss` |
| Screen management (push/pop) | [OK] | `ui/app.py` |

### 3.2 ASCII Logo + Branding
| Item | Status | Notes |
|------|--------|-------|
| Unicode snake logo | [OK] | `ui/components.py` (LOGO widget) |
| ASCII fallback | [OK] | `ui/components.py` |

### 3.3 Main Menu (opencode Style)
| Item | Status | Notes |
|------|--------|-------|
| 8-option menu (1-7, 0) | [OK] | `ui/screens.py` |
| Number key navigation | [OK] | `ui/screens.py` |
| j/k navigation | [OK] | `ui/screens.py` |
| Slash command palette (`/scan`, `/target`, etc.) | [OK] | `ui/app.py` + `ui/screens.py` — fully wired |
| `action_cleanup()` implemented | [OK] | `ui/app.py` — fixed (BUG-014) |

### 3.4 Scan Results Table
| Item | Status | Notes |
|------|--------|-------|
| DataTable with all airodump columns | [OK] | `ui/screens.py` |
| Signal bars (█/░ with color) | [OK] | `ui/components.py` |
| Real-time live update | [OK] | `ui/screens.py` |
| Hidden SSID `[HIDDEN]` display | [OK] | `ui/screens.py` |
| WPS column | [OK] | `ui/screens.py` |

### 3.5 Capture Method Selection
| Item | Status | Notes |
|------|--------|-------|
| Passive / Deauth selection | [OK] | `ui/screens.py` |
| Tooltips with risk level | [OK] | `ui/components.py` |
| Target Network passed from ScanScreen | [OK] | `ui/screens.py` — fixed (BUG-001) |

### 3.6 Live Capture Progress
| Item | Status | Notes |
|------|--------|-------|
| Capture stats panel (beacons/data/IVs) | [OK] | `ui/screens.py` |
| EAPOL M1-M4 tracker display | [OK] | `ui/components.py` |
| Progress bar | [OK] | `ui/components.py` |
| Elapsed timer | [OK] | `ui/screens.py` |

### 3.7 Deauth Target Selection
| Item | Status | Notes |
|------|--------|-------|
| Checkbox list of clients | [WARN] | `ui/screens.py` — checkboxes decorative, clients never collected (BUG-002) |
| Space toggle | [OK] | `ui/screens.py` |
| Rate control (+/-) | [OK] | `ui/screens.py` |
| `a` selects all | [OK] | `ui/screens.py` |

### 3.8 Crack Progress Display
| Item | Status | Notes |
|------|--------|-------|
| Progress bar with % | [OK] | `ui/screens.py` |
| Keys tested / total | [OK] | `ui/screens.py` |
| Speed (keys/s) + ETA | [OK] | `ui/screens.py` |
| Current key display | [OK] | `ui/screens.py` |

### 3.9 Result Card (Password Found)
| Item | Status | Notes |
|------|--------|-------|
| Password highlighted in green | [OK] | `ui/screens.py` |
| Save/copy/try-again options | [OK] | `ui/screens.py` |

### 3.10 Error Cards
| Item | Status | Notes |
|------|--------|-------|
| What/Why/HowToFix error panel | [OK] | `ui/components.py` |
| Severity-coded colors | [OK] | `ui/components.py` |
| Raw error + timestamp | [OK] | `ui/components.py` |

### 3.11 Help/Tutorial System
| Item | Status | Notes |
|------|--------|-------|
| 4-phase tutorial content | [OK] | `ui/screens.py` |
| `?` key opens help | [OK] | `ui/app.py` |
| Esc closes help | [OK] | `ui/app.py` |

### 3.12 Slash Commands + Status Bar
| Item | Status | Notes |
|------|--------|-------|
| 9 slash commands (/scan, /target, /capture, /crack, /cleanup, /help, /status, /adapter, /quit) | [OK] | `ui/app.py` |
| Status bar (adapter │ Ch │ Mode │ Signal │ Clients │ Job │ Elapsed) | [OK] | `ui/app.py` |
| Real-time status updates | [OK] | `ui/app.py` |

### 3.13 Session Resume Prompt
| Item | Status | Notes |
|------|--------|-------|
| `ResumeScreen` — shows session summary (adapter/scans/target/captures/cracked) | [OK] | `ui/screens.py` |
| Y/n keybinding to resume or start fresh | [OK] | `ui/screens.py` |
| Entry point passes existing session to TUI | [WARN] | `sidewinder.py:162` — discards sessions without scan results (BUG-004) |
| `SidewinderApp` accepts optional session param | [OK] | `ui/app.py:68` |
| Resume restores session state to workflow | [WARN] | Sets variable but doesn't restore state (BUG-005) |

---

## Unit Test Coverage

**51 passed, 4 skipped (Linux-only on Windows) — `pytest tests/`**

| Module | Test File | Status | Tests |
|--------|-----------|--------|-------|
| `core/errors.py` | `tests/test_errors.py` | [OK] | 18 pass |
| `core/session.py` | `tests/test_session.py` | [OK] | 23 pass |
| `core/adapter.py` | `tests/test_adapter.py` | [OK] | pass (cross-platform skip) |
| `core/subprocess_mgr.py` | `tests/test_subprocess.py` | [OK] | pass (cross-platform skip) |
| `core/monitor.py` | `tests/test_monitor.py` | [OK] | pass (cross-platform skip) |
| `core/services.py` | `tests/test_services.py` | [OK] | pass (cross-platform skip) |
| `core/capture.py` | `tests/test_capture.py` | [OK] | pass |
| `core/cracker.py` | `tests/test_cracker.py` | [OK] | pass |
| `core/scanner.py` | `tests/test_scanner.py` | [FAIL] | Not created |
| `core/cleanup.py` | `tests/test_cleanup.py` | [FAIL] | Not created |
| `adapters/base.py` | `tests/test_adapter_base.py` | [FAIL] | Not created |
| `adapters/rt5370.py` | `tests/test_rt5370.py` | [FAIL] | Not created |
| `adapters/rtl8821au.py` | `tests/test_rtl8821au.py` | [FAIL] | Not created |
| `adapters/mt7902.py` | `tests/test_mt7902.py` | [FAIL] | Not created |

---

## Known Bugs

**50 total — 27 fixed, 1 partially fixed, 22 remaining**

| Severity | Fixed | Remaining | IDs |
|----------|-------|-----------|-----|
| CRITICAL | 0 | 3 | 002, 004, 005 |
| HIGH | 4 | 1 | 009† partial. Remaining: 046 |
| MEDIUM | 8 | 9 | 013, 026, 027, 030, 031, 041, 042, 043, 044, 045, 047, 048, 049, 050 |
| LOW | 0 | 1 | 025 |

**Top 3 blockers (CRITICAL):**
1. BUG-002 — Deauth screen discards selected clients
2. BUG-004 — Resume discards sessions without scan results
3. BUG-005 — Resume doesn't restore state to workflow

See [Bug.md](../Bug.md) for full details.

---

## Changelog

| Date | Version | Change |
|------|---------|--------|
| 2026-06-05 | 0.1.0 | Implementation started — all files scaffolded |
| 2026-06-05 | 0.2.0 | All Phase 1 core modules complete. All Phase 2 adapter modules complete. All Phase 3 UI screens complete. 41 tests passing (errors + session). |
| 2026-06-05 | 0.3.0 | MT7902 inject_frame protection added. UI refinements (TargetScreen checkboxes, slash command notifications). pyproject.toml build backend fixed. Full test suite: 51 pass + 4 skip. Cross-platform skip markers. |
| 2026-06-05 | 0.4.0 | Signal handlers wired into entry point (sync + async). Deauth attack module created (attacks/deauth.py). Session resume prompt (ResumeScreen) — shows summary, Y/n to resume. Entry point passes session to TUI. |
| 2026-06-05 | 0.5.0 | Bug fixes: BUG-001 (target passing), BUG-003 (scan table update), BUG-010-012 (async adapter detection), BUG-014 (action_cleanup), BUG-015 (main menu navigation), BUG-016 (deprecated loop=), BUG-017-018 (callback types), BUG-019-020 (resource leaks), BUG-022 (dead AdapterError), BUG-024 (unused import), BUG-028-030 (zombie scans). New features: attacks/evil_twin.py (airbase-ng rogue AP), CommandPaletteScreen (fully wired slash commands). 3 CRITICAL bugs remain (002, 004, 005). |
| 2026-06-05 | 0.6.0 | Bug fixes: BUG-032-035 (EvilTwinEngine class with stop/timeout/validation/async callback), BUG-036-038 (CommandPalette single source of truth, empty highlight fallback, import cleanup), BUG-039 (asyncio.get_running_loop), BUG-021 (ps args= format), BUG-023 (re.sub for hashcat), BUG-040 (returncode None check). 27 of 43 bugs fixed. 3 CRITICAL remain (002, 004, 005). |
| 2026-06-05 | 0.7.0 | Phase 2 core modules: core/rfkill.py, core/vm.py, core/config.py, core/logger.py, core/attack.py, cli.py, __main__.py. 7 new bugs found (BUG-044 to BUG-050). 50 total bugs, 27 fixed, 22 remaining. 3 CRITICAL remain (002, 004, 005). |
