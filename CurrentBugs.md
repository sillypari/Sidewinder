# Sidewinder Current Bugs & Issues

> Generated from full TUI audit — 2026-06-06
> 22 screens, 17 widgets, 856 lines TCSS, 13 themes

---

## Critical Bugs (8)

### BUG-065: Cleanup async never runs
- **File:** `screens.py:441`
- **Code:** `self.app.action_cleanup()` — `action_cleanup` is `async def` but called without `await`
- **Impact:** Cleanup silently never runs. User thinks it worked but nothing happened.
- **Fix:** Use `asyncio.ensure_future(self.app.action_cleanup())` or make `action_cleanup` sync.

### BUG-066: CaptureListScreen discards selected file
- **File:** `screens.py:2400`
- **Code:** `self.app.push_screen(CrackProgressScreen())` — `full_path` not passed
- **Impact:** User selects a capture file → crack screen gets `cap_file=""` → tries `session.captures[-1]` or errors.
- **Fix:** `CrackProgressScreen(cap_file=full_path)` + push `WordlistPickerScreen` first.

### BUG-067: ScanScreen columns wiped on resize
- **File:** `screens.py:574+589`
- **Code:** `_setup_columns` calls `table.clear(columns=True)` on every `on_resize`
- **Impact:** All scan data disappears when terminal resizes. Rows reappear only when `add_network` fires again.
- **Fix:** Only clear columns if column set changed, or preserve rows during rebuild.

### BUG-068: ScanOptionsScreen ignores all options
- **File:** `screens.py:2259-2261`
- **Code:** `action_start_scan` pushes `ScanScreen()` without passing band/channels/hidden
- **Impact:** User configures band, channel, hidden SSID → all settings silently discarded.
- **Fix:** Pass options to `ScanScreen(band=..., channels=..., hidden=...)`.

### BUG-069: 4 slash commands unimplemented
- **File:** `screens.py:1842-1843`
- **Commands:** `/capture`, `/crack`, `/status`, `/adapter`
- **Impact:** User sees "not fully wired yet" warning.
- **Fix:** Wire to appropriate screens.

### BUG-070: Evil Twin has no completion path
- **File:** `screens.py:1063-1071`
- **Code:** `engine.start_rogue_ap` called but no completion handler
- **Impact:** Always results in "No handshake captured" → dead end.
- **Fix:** Add completion callback or redirect to monitoring screen.

### BUG-071: ScanScreen no "done" action
- **File:** `screens.py:664`
- **Code:** `action_stop_scan` only cancels task, no next step
- **Impact:** After stopping scan, user is stranded with static table. Must press Enter or Esc manually.
- **Fix:** After stop, auto-push `TargetSelectScreen` or show "Select a target" prompt.

### BUG-072: `compose_prompt()` never called
- **File:** `screens.py:84-95`
- **Code:** Base `SidewinderScreen.compose()` defines `prompt-area` but never yields `compose_prompt()` output
- **Impact:** All keyboard hints invisible across 22 screens. 20+ hint IDs and CSS rules orphaned.
- **Fix:** Add `yield from self.compose_prompt()` in the prompt-area Vertical.

---

## Unreachable Screens (4)

| Screen | Line | Why Unreachable | Fix |
|--------|------|-----------------|-----|
| `CleanupScreen` | 1993 | MainMenu[6] uses inline confirm → broken async | Wire MainMenu[6] to push CleanupScreen |
| `ServiceCheckScreen` | 2077 | Nothing pushes it | Add from AdapterScreen or MainMenu |
| `MonitorSetupScreen` | 2137 | Nothing pushes it | Add from AdapterScreen |
| `ScanOptionsScreen` | 2226 | Options not passed to ScanScreen | Wire to ScanScreen with params |

---

## Dead Widgets (8 of 17)

| Widget | File:Line | Why Dead |
|--------|-----------|----------|
| `EAPOLTracker` | `components.py:315` | Superseded by `AttackProgressPanel` |
| `StatusBar` | `components.py:345` | Never instantiated |
| `TargetCard` | `components.py:379` | `TargetSelectScreen` uses DataTable |
| `ClientRow` | `components.py:399` | `DeauthSelectScreen` uses DataTable |
| `SignalBar` | `components.py:472` | Signal done inline via `signal_bar()` |
| `ChannelIndicator` | `components.py:480` | Never used |
| `AdapterCard` | `components.py:490` | `AdapterScreen` uses DataTable |
| `AttackStatus` | `components.py:501` | Never used |

---

## Dead Widget Files (3 of 3)

| File | Widget | Why Dead |
|------|--------|----------|
| `widgets/center_middle.py` | `CenterMiddle` | Never imported; `Center` used instead |
| `widgets/confirmation.py` | `ConfirmationModal` | Never imported; `InlineConfirm` used instead |
| `widgets/help_screen.py` | `HelpScreen` (modal) | Conflicts with `screens.py:HelpScreen` (tutorial) |

---

## Dead CSS Rules

| Selector | Line | Why Dead |
|----------|------|----------|
| `StatusBar` | 46-52 | StatusBar widget is dead code |
| `#scan-table-container` | 332-334 | ID never used |
| `#eapol-tracker` | 340-345 | EAPOLTracker is dead code |
| `#scan-hints` | 514 | compose_prompt never called |
| `#target-hints` | 514 | compose_prompt never called |
| `#method-hints` | 573 | compose_prompt never called |
| `#capture-hints` | 514 | compose_prompt never called |
| `#deauth-hints` | 514 | compose_prompt never called |
| `#crack-hints` | 514 | compose_prompt never called |
| `#result-hints` | 514 | compose_prompt never called |
| `#error-hints` | 514 | compose_prompt never called |
| `#resume-options` | 582 | compose_prompt never called |
| `#wordlist-hints` | 615 | compose_prompt never called |
| `#engine-hints` | 615 | compose_prompt never called |
| `#cleanup-hints` | 615 | compose_prompt never called |
| `#services-hints` | 615 | compose_prompt never called |
| `#monitor-hints` | 615 | compose_prompt never called |
| `#scanopts-hints` | 615 | compose_prompt never called |
| `#apdetails-hints` | 615 | compose_prompt never called |
| `#captures-hints` | 615 | compose_prompt never called |

---

## Unimplemented Commands

| Command | Status | Should Do |
|---------|--------|-----------|
| `/capture` | ❌ "not fully wired" | Push `CaptureMethodScreen` |
| `/crack` | ❌ "not fully wired" | Push `WordlistPickerScreen` |
| `/status` | ❌ "not fully wired" | Show session info overlay |
| `/adapter` | ❌ "not fully wired" | Push `AdapterScreen` |

---

## UX Flow Issues

### Scan → Target → Capture (the core flow)
```
MainMenu[1] → ScanScreen → (select) → APDetailsScreen → [C] → CaptureMethodScreen
                                                                      │
                                          ┌────────────────────────────┤
                                          │                            │
                                     [1] Passive                  [2] Deauth
                                          │                            │
                              CaptureProgressScreen          DeauthSelectScreen
                                          │                            │
                                    (handshake?)              CaptureProgressScreen
                                          │                            │
                              WordlistPickerScreen ←──────── (handshake?)
                                          │
                              EnginePickerScreen
                                          │
                              CrackProgressScreen
                                          │
                                    ResultScreen ✅
```

**What works:** Passive/deauth capture → wordlist → engine → crack → result ✅

**What breaks:**
- PMKID/WPS/EvilTwin: no backend wiring, cosmetic only
- No "done scanning" action
- Resize destroys scan data
- CaptureListScreen discards selection

### Settings Flow
```
MainMenu[5] → AdapterScreen → (shows adapters) → ???
```
**What breaks:**
- No way to switch adapters
- MonitorSetupScreen unreachable
- ServiceCheckScreen unreachable

### Cleanup Flow
```
MainMenu[6] → InlineConfirm → action_cleanup() → (async never runs) → ???
```
**What breaks:**
- Cleanup never actually runs (async bug)
- CleanupScreen unreachable

### Session Management
- No `/session` command
- Session auto-saves but no UI to load/list/delete

---

## Priority Fix Order

1. **BUG-065** (cleanup async) — one-line fix, critical
2. **BUG-072** (compose_prompt) — enables keyboard hints on all screens
3. **BUG-067** (resize wipe) — data loss on user action
4. **BUG-066** (capture discard) — wrong file cracked
5. **BUG-069** (slash commands) — 4 commands dead
6. **BUG-071** (scan done action) — UX dead end
7. **BUG-068** (scan options) — options discarded
8. **BUG-070** (evil twin) — attack dead end
9. Wire 4 unreachable screens
10. Remove 8 dead widgets + 3 dead files
11. Clean orphaned CSS (20+ rules)
12. Add `/session` commands
