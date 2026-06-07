# Sidewinder UI Audit — Inconsistencies, Duplication & §14 Gaps

> Audit date: 2026-06-06  
> Files examined: `ui/screens.py`, `ui/components.py`, `ui/colors.tcss`, `ui/app.py`  
> Reference spec: `TUI.md §13–14`

---

## Executive Summary

The codebase has **3 categories of problems** stopping us from reaching the §14 goals:

| Category | Count | Severity |
|---|---|---|
| Duplication / dead CSS | 8 | Medium |
| Inconsistency (markup style, pattern drift) | 11 | High |
| §14 goals not yet implemented | 9 | Critical |

---

## 1. Duplication Issues

### 1.1 `#nav-bar` CSS defined twice
**File:** `colors.tcss` — lines 39–46 AND 741–748  
Both blocks set the same `background`, `color`, `height`, `border-top`, `padding`.  
The second block also adds `width: 100%` (harmless but redundant).  
**Fix:** Delete lines 39–46 (the first block — it appears before the "OpenCode Layout Refactoring" section that owns `#nav-bar`).

```diff
- #nav-bar {
-     background: $surface;
-     color: $foreground;
-     dock: bottom;
-     height: 1;
-     border-top: solid $accent 30%;
-     padding: 0 4;
- }
```

### 1.2 `#result-card` CSS defined twice
**File:** `colors.tcss` — lines 377–383 AND 511–516  
First definition has `margin: 1 4`, second has `margin: 1 0`. The second one wins (cascade), making the first a dead rule.  
**Fix:** Delete the first definition (lines 377–383).

### 1.3 `#method-list` CSS defined twice
**File:** `colors.tcss` — lines 349–354 AND 551–556  
First: `width: 2fr; padding: 1 2;`  
Second: `width: 2fr; padding: 1 4 2 4;` — second wins.  
**Fix:** Delete the first definition (lines 349–354).

### 1.4 `eapol_status_display()` called in two separate places
**File:** `components.py`  
- `EAPOLTracker.render()` calls it (line 299)  
- `AttackProgressPanel.render()` calls it (line 402)  
Both produce identical markup but are separate widget classes. This is acceptable architecturally, but the helper function is not re-exported so it is invisible from screens.  
**Fix:** Export `eapol_status_display` in `__init__.py` or document it clearly.

### 1.5 `action_cleanup` dispatched in 3 different places
- `MainMenuScreen.on_list_view_selected` (line 144) calls `self.app.action_cleanup()`  
- `MainMenuScreen.action_menu_6` (line 164) calls `self.app.action_cleanup()`  
- `CleanupScreen.action_run_cleanup` (line 1424) calls `await self.app.action_cleanup()`  
The `menu_6` action is also redundant since the list-view handler already dispatches to it.  
**Fix:** Remove the `on_list_view_selected` dispatch for `cleanup` and keep only `action_menu_6 → push_screen(CleanupScreen())`.

### 1.6 `DataTable` import duplicated in several screen `compose()` methods
**File:** `screens.py`  
`CaptureListScreen.compose()` (line 1703) and `CaptureListScreen.action_crack()` / `action_cursor_*` (lines 1747, 1761, 1765) all import `DataTable` locally via `from textual.widgets import DataTable`, but `DataTable` is already imported at the top of the file (line 26).  
**Fix:** Remove the three local imports.

### 1.7 `HelpScreen` has no hints bar, but every other screen does
All screens yield a `Static(id="*-hints")` at the bottom, but `HelpScreen.compose()` (line 1119) skips this entirely. The tutorial text already says "Press Esc or q to close" as inline text (line 1107), making it the only screen with in-content hints rather than the standard bar.  
**Fix:** Add a consistent hints bar to `HelpScreen`, remove the in-content "Press Esc" text.

### 1.8 `TargetCard` and `ClientRow` components exist but are never used
**File:** `components.py` lines 349–387  
Both `TargetCard` and `ClientRow` are defined as reusable widgets per TUI.md §7, but no screen actually mounts them. `DeauthSelectScreen` uses a raw `DataTable` instead of `ClientRow`, and `APDetailsScreen` has no `TargetCard`.  
**Fix:** Either use them or mark as `# TODO: wire up` to avoid confusion.

---

## 2. Inconsistency Issues

### 2.1 Rich markup style — mixed `[$var]` vs `[bold $var]` patterns
**File:** `screens.py`  
Closing tags are inconsistent:
- Some use `[/$text-muted]` (correct theme-variable form)
- Some use `[/]` (bare close — works but non-semantic)
- `HelpScreen` TUTORIAL (lines 1055–1107) uses hardcoded colour names like `[bold green]`, `[bold cyan]` instead of `[$success]`, `[$secondary]`

This means TUTORIAL text **ignores the active theme**. Switching themes has no effect on the help screen.  
**Fix:** Replace all hardcoded colour names in TUTORIAL with `$`-prefixed theme variables.

### 2.2 `AdapterScreen` uses `[green]YES[/green]` hardcoded
**File:** `screens.py` line 216–217  
```python
mon = "[green]YES[/green]" if a.monitor_capable else "[red]NO[/red]"
```
Should be `[$success]` / `[$error]` to respect themes.

### 2.3 `TooltipPanel` and `ErrorCard` use hardcoded Rich colours
**File:** `components.py` lines 192–220, 254–282  
Both `ErrorCard.render()` and `TooltipPanel.render()` use literal colour strings (`"green"`, `"yellow"`, `"red"`, `"cyan"`, `"blue"`) instead of `$success`, `$warning`, `$error`, `$secondary`, `$info`.  
This is the same theme-blindness problem as 2.1.  
**Fix:** Map severity/risk levels to `$`-prefixed variables.

### 2.4 Inconsistent title styling — `$primary` vs `$secondary`
Different screens use different colours for their title headers:
| Screen | Title colour |
|---|---|
| `AdapterScreen` | `[bold $primary]` |
| `ScanScreen` | `[bold $primary]` |
| `CaptureMethodScreen` | `[bold $primary]` |
| `CrackProgressScreen` | `[bold $primary]` |
| `MonitorSetupScreen` | `[bold $primary]` |
| `ResultScreen` | *(no title, uses card)* |

But their CSS `#*-title` rules apply `color: $secondary`, overriding the inline `$primary` markup. So the rendered color depends on which wins — CSS or inline markup.  
**Fix:** Standardise all screen titles to use a single approach: either CSS `color: $primary` with plain-text widget content, or markup `[bold $primary]Title[/bold $primary]` with no CSS override.

### 2.5 `ScanScreen` missing `j/k` bindings that `TargetSelectScreen` has
**File:** `screens.py`  
`TargetSelectScreen.BINDINGS` includes `j/k` for navigation (lines 434–435).  
`ScanScreen.BINDINGS` does NOT include `j/k` (lines 242–246), even though both show a `DataTable` and are meant to support vim navigation (TUI.md §5 keybinding table).  
**Fix:** Add `j/k` bindings to `ScanScreen` to match spec.

### 2.6 `action_menu_4` is defined out of numerical order
**File:** `screens.py`  
`MainMenuScreen` defines actions in order: `menu_1`, `menu_2`, `menu_3`, `menu_5`, `menu_6`, `menu_7`, `menu_0`... and then `menu_4` appears later (line 177–178) with a comment "# Also handle menu_4 for view". This is a leftover from a refactor.  
**Fix:** Move `action_menu_4` next to the other `action_menu_*` methods in numerical order.

### 2.7 `CrackProgressScreen.action_stop` silently falls through to wrong screen
**File:** `screens.py` lines 888–893  
When Esc is pressed, if the session has captures, it pushes `WordlistPickerScreen()` — but the screen is named "CrackProgressScreen" and the binding shows "Stop". Users expect `Esc` on a progress screen to stop and return to the previous screen, not open a picker.  
This is a UX inconsistency vs every other screen's `action_back` / `action_stop` patterns.  
**Fix:** Always `pop_screen()` on Esc/Stop; open `WordlistPickerScreen` as a separate explicit keybind or via the main menu flow.

### 2.8 `TargetSelectScreen` has its own `DataTable` but never populates it
**File:** `screens.py` lines 438–474  
`TargetSelectScreen.compose()` yields a `DataTable` with columns (BSSID, CH, Signal, Privacy, ESSID, Clients) and there's no `on_mount` that loads data from `self.app.session.scan_results`.  
The table is always empty.  
**Fix:** Add `on_mount` that populates the table from `session.scan_results`, same pattern as `ScanScreen.add_network()`.

### 2.9 Double `Footer()` pattern — some screens redundant vs app-level
**File:** `screens.py`  
Every screen yields `Footer()`. The app-level `SidewinderApp.compose()` also yields `Header()` (line 90). The Header is app-level; Footer is per-screen. This is technically correct for Textual, but it means the Footer is instantiated separately 16+ times per session lifetime, each with its own keybinding display.  
The Footer shows keybinds from each screen's `BINDINGS`, which is correct — but `Footer` is imported but only used in screens, yet it's listed in the top-level import block (line 27) suggesting it was originally intended to be app-level.  
**Note:** Low severity, but worth documenting. Currently working correctly.

### 2.10 `ServiceCheckScreen` binds `k` to "kill_services" — conflicts with vim `k` (up)
**File:** `screens.py` lines 1438–1441  
`k` is bound to `kill_conflicting`. In every other screen, `k` means "cursor up" (vim navigation). On this screen, vim-`k` is hijacked for a destructive action.  
**Fix:** Rebind kill to `ctrl+k` or `K` (uppercase), leaving `k` for navigation.

### 2.11 Hints bar ID names are inconsistent
Every `*-hints` Static widget has a unique `id=` but the CSS groups them in a single selector:
```css
#scan-hints, #target-hints, #method-hints, ...
```
If a new screen is added without updating the CSS selector, its hints get no styling.  
**Fix:** Use a shared CSS class `.hints` instead of grouping individual IDs.

---

## 3. §14 Goals Not Yet Implemented

These are features explicitly required by **TUI.md §14** (OpenCode-inspired architecture) that are missing from the current code.

### 3.1 [§14.3] Dense Information — Main Menu items show NO live state
**Current:** Menu just shows label text (`"Scan WiFi networks"`)  
**Required (§14.3):**
```
[1] Scan ─────────── ● scanning...
[2] Target ────────── ■ NASA (AA:BB:CC)
[5] Settings ──────── RTL8821AU [MON]
```
Each item should show inline live state. This requires the `MainMenuScreen` to have reactive properties that update menu labels dynamically.  
**Missing:** Reactive menu label updates, state-aware item rendering.

### 3.2 [§14.4] Leader Key System — `ctrl+a`, `ctrl+s`, `ctrl+c` submenus
**Current:** No `ctrl+` bindings anywhere in the app.  
**Required:** `ctrl+a` → attack submenu, `ctrl+s` → scan submenu, `ctrl+c` → capture submenu  
**Missing:** All leader-key bindings and their overlay/submenu widgets.

### 3.3 [§14.5] Inline Dialogs — `InlineConfirm` class is in CSS but not in Python
**Current:** `colors.tcss` has `InlineConfirm` and `InlineConfirm.active` CSS rules (lines 806–818). But there is **no `InlineConfirm` Python class** anywhere in `components.py` or `screens.py`.  
Modal `push_screen` is used instead (e.g., `ResumeScreen`, `ErrorScreen`).  
**Missing:** `InlineConfirm` widget class, integration into `CleanupScreen` and any action needing confirmation.

### 3.4 [§14.2 / §14.9] Sidebar Layout — `#right-sidebar` CSS exists but is never mounted
**Current:** `colors.tcss` defines `#right-sidebar`, `#left-container`, `#main-content`, `#screen-layout`, `#sidebar-sep`, `#prompt-area` (lines 730–800). None of these IDs appear in any `compose()` method.  
**Missing:** The actual sidebar layout in screens. No screen uses the OpenCode-style dual-panel layout with a persistent right sidebar.

### 3.5 [§14.8] Status Bar — only `ScanScreen` has a `StatusBar`
**Current:** `StatusBar` component exists and is used only in `ScanScreen` (line 267).  
**Required:** Status bar should be persistent across all screens (visible always), showing adapter + mode + channel + signal.  
**Missing:** App-level or base-screen `StatusBar` mount. Currently it only appears during scanning.

### 3.6 [§14.10] Interaction Grammar — symbols `→`, `←`, `▣`, `■`, `⬝`, `●`, `△` not used
**Current:** The codebase uses standard ASCII `*` for selections, plain text for status.  
**Required:** The symbolic vocabulary defined in §14.10 (e.g., `→ Scanning 2.4GHz`, `▣ Handshake captured!`, `■ M1 ■ M2 □ M3 □ M4`) is not applied anywhere.  
**Missing:** Symbol vocabulary integration in `ScanScreen`, `CaptureProgressScreen`, `DeauthSelectScreen`, `MainMenuScreen`.

### 3.7 [§14.9] Responsive Layout — no breakpoint handling
**Current:** No `on_resize` handler checks terminal width and hides/shows sidebar. `ScanScreen` has a basic `on_resize` that re-calls `_setup_columns` to add/remove WPS and Clients columns, but only at a `>= 100` threshold.  
**Required:**
```
>= 120 cols: Main + Sidebar (20 cols)
80–119 cols: Main only, adapter info in status bar
< 80 cols: "Terminal too small" message
```
**Missing:** Global `on_resize` handler, sidebar hide/show logic, minimum-size guard screen.

### 3.8 [§14.11] Slash Commands — `/capture`, `/status`, `/adapter`, `/session` not wired
**Current:** `CommandPaletteScreen._execute_command()` handles: `/scan`, `/target`, `/help`, `/cleanup`, `/theme`, `/compact`, `/quit`.  
**Missing from `SLASH_COMMANDS` and `_execute_command`:**
- `/capture` → `CaptureMethodScreen`
- `/status` → show adapter status toast or screen
- `/adapter` → `AdapterScreen`
- `/session` → session management screen (no screen exists for this)
- `/crack` → `CrackProgressScreen` (listed in `SLASH_COMMANDS` dict but not in `_execute_command` handler — dead entry)

### 3.9 [§14.6] `ChannelIndicator`, `AdapterCard`, `AttackStatus` widgets — not implemented
**Required by §14.6:**
```python
class SignalBar(Widget): ...      # ▁▃▅▇█ visual bar (exists as function, not widget)
class EAPOLTracker(Widget): ...   # already implemented ✓
class ChannelIndicator(Widget): ...  # CH: 6 (2.4GHz) — MISSING
class AdapterCard(Widget): ...    # █ Adapter: RTL8821AU [MON] — MISSING
class AttackStatus(Widget): ...   # ▣ Deauth: 10/10 frames — MISSING
```
`signal_bar()` exists as a pure function but §14.6 calls for a `SignalBar` **widget** (reactive, live-updating).  
**Missing:** `ChannelIndicator`, `AdapterCard`, `AttackStatus` widget classes.

---

## 4. Priority Fix Order

| Priority | Issue | Effort | Impact |
|---|---|---|---|
| 🔴 P0 | 3.4 Sidebar CSS dead (layout never mounts) | High | Blocks OpenCode parity |
| 🔴 P0 | 3.5 StatusBar only in ScanScreen | Medium | Core UX gap |
| 🔴 P0 | 3.1 Dense menu — no live state | Medium | §14.3 core feature |
| 🔴 P0 | 2.8 TargetSelectScreen empty table | Low | Functional bug |
| 🟠 P1 | 2.1/2.3 Theme-blind hardcoded colours | Medium | Themes broken for TUTORIAL, ErrorCard, TooltipPanel |
| 🟠 P1 | 3.8 Dead `/crack` command entry | Low | Slash command broken |
| 🟠 P1 | 3.3 InlineConfirm CSS but no Python class | Medium | CSS waste + §14.5 gap |
| 🟠 P1 | 2.7 Esc on CrackProgress wrong screen | Low | UX regression |
| 🟡 P2 | 1.1–1.3 Duplicate CSS blocks | Low | Maintenance cleanup |
| 🟡 P2 | 2.5 ScanScreen missing j/k bindings | Low | Spec compliance |
| 🟡 P2 | 2.10 `k` conflicts with kill_services | Low | UX hazard |
| 🟡 P2 | 1.6 Local DataTable imports | Low | Code hygiene |
| 🟢 P3 | 3.2 Leader key system | High | §14.4 stretch goal |
| 🟢 P3 | 3.6 Interaction grammar symbols | Medium | Polish |
| 🟢 P3 | 3.7 Responsive layout | High | §14.9 |
| 🟢 P3 | 3.9 Missing widgets | Medium | §14.6 |

---

## 5. Files That Need Changes

| File | Issues |
|---|---|
| [`screens.py`](file:///c:/Users/Parikshit/Desktop/NewGenApps/Sidewinder/sidewinder/ui/screens.py) | 2.2, 2.5, 2.6, 2.7, 2.8, 2.9, 3.1, 3.4, 3.5, 3.8, 1.6 |
| [`components.py`](file:///c:/Users/Parikshit/Desktop/NewGenApps/Sidewinder/sidewinder/ui/components.py) | 2.3, 1.8, 3.9 |
| [`colors.tcss`](file:///c:/Users/Parikshit/Desktop/NewGenApps/Sidewinder/sidewinder/ui/colors.tcss) | 1.1, 1.2, 1.3, 2.11, 3.3, 3.4 |
| [`app.py`](file:///c:/Users/Parikshit/Desktop/NewGenApps/Sidewinder/sidewinder/ui/app.py) | 3.2, 3.5, 3.7 |

---

## 6. What Is Working Correctly

These items from TUI.md are **already implemented and correct**:

- ✅ Screen stack navigation (push/pop) — all 16 screens
- ✅ Keybinding system — per-screen `BINDINGS` 
- ✅ DataTable with signal bars in ScanScreen
- ✅ EAPOL tracker widget
- ✅ Theme system with live switching (13 themes)
- ✅ Command palette with fuzzy search
- ✅ LogoWidget (two-tone, ASCII art)
- ✅ AdapterStatusWidget with reactive updates
- ✅ Footer on every screen
- ✅ Header with clock
- ✅ TooltipPanel for CaptureMethodScreen
- ✅ PasswordCard result screen
- ✅ Session resume screen
- ✅ StatusBar component (used in ScanScreen)
- ✅ ScanStatsBar component
- ✅ AttackProgressPanel component
- ✅ Wordlist picker (DirectoryTree)
- ✅ Engine picker (Aircrack-ng vs Hashcat)
- ✅ Cleanup screen
- ✅ Monitor mode enable/disable screen
- ✅ Service check screen
- ✅ AP Details with attack recommendations
- ✅ 71/71 tests passing
