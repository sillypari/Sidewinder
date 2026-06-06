# Sidewinder TUI Architecture Guide

> Reference: opencode's `@opentui/solid` TUI → mapped to Python/Textual equivalents
> Last updated: 2026-06-06

---

## Table of Contents

1. [Framework Choice](#1-framework-choice)
2. [Architecture Pattern](#2-architecture-pattern)
3. [opencode Reference → Sidewinder Mapping](#3-opencode-reference--sidewinder-mapping)
4. [Theme System](#4-theme-system)
5. [Keybinding System](#5-keybinding-system)
6. [Screen Architecture](#6-screen-architecture)
7. [Component System](#7-component-system)
8. [Real-Time Updates](#8-real-time-updates)
9. [Screen-by-Screen Implementation](#9-screen-by-screen-implementation)
10. [Navigation Flow](#10-navigation-flow)
11. [State Management](#11-state-management)
12. [File Structure](#12-file-structure)

---

## 1. Framework Choice

### opencode: `@opentui/solid` (TypeScript)
- SolidJS reactivity (`createSignal`, `createEffect`)
- JSX terminal primitives (`<box>`, `<scrollbox>`, `<text>`)
- `CliRenderer` at 60fps
- Context-based dependency injection (20+ providers)

### Sidewinder: `textual` (Python)
- Reactive attributes (`reactive[T]`)
- Declarative `compose()` → `yield` widgets
- Async event loop integration
- Screen stack navigation (`push_screen`/`pop_screen`)

**Why Textual is correct for Sidewinder:**
- Python-native (no FFI, no build step)
- Async-first (matches our asyncio attack engines)
- Built-in DataTable, ProgressBar, Input, OptionList
- TCSS (Textual CSS) for styling
- Screen stack for navigation
- Message system for component communication

---

## 2. Architecture Pattern

### opencode: Elm/MVU + Context Providers
```
Model:    createStore (signals, derived state)
View:     JSX components → terminal primitives
Update:   event handlers, SSE subscriptions
Context:  20+ nested providers (theme, route, sync, keymap, SDK...)
```

### Sidewinder: App State + Screen Stack
```
Model:    SidewinderApp (holds session, adapters, managers)
View:     Screen classes → compose() yields widgets
Update:   action handlers, async tasks, reactive attributes
State:    App-level attributes + screen-local reactive vars
```

**Key difference:** opencode uses deep provider nesting. Sidewinder uses a flat app state with screen-local reactivity. This is simpler and appropriate for our single-user, single-process tool.

---

## 3. opencode Reference → Sidewinder Mapping

| opencode Concept | opencode File | Sidewinder Equivalent | Sidewinder File |
|---|---|---|---|
| App entry + provider tree | `app.tsx` (34KB) | `SidewinderApp` | `ui/app.py` |
| Route state (home/session/plugin) | `context/route.tsx` | Screen stack (`push_screen`) | `ui/app.py` |
| Theme context (33 themes) | `context/theme.tsx` (36KB) | TCSS + reactive colors | `ui/colors.tcss` |
| Keymap provider (modal, leader) | `keymap.tsx` + `config/keybind.ts` | `Binding` list per screen | Each screen class |
| Sync provider (SSE events) | `context/sync.tsx` (24KB) | asyncio tasks + reactive | `core/scanner.py`, `core/capture.py` |
| SDK provider (API client) | `context/sdk.tsx` | SubprocessManager | `core/subprocess_mgr.py` |
| Home screen (logo + prompt) | `routes/home.tsx` | MainMenuScreen | `ui/screens.py` |
| Session screen (messages + sidebar) | `routes/session/index.tsx` (88KB) | ScanScreen + TargetSelect | `ui/screens.py` |
| Sidebar (42 cols) | `routes/session/sidebar.tsx` | AdapterStatusWidget | `ui/components.py` |
| Footer (status bar) | `routes/session/footer.tsx` | Status bar in Screen | `ui/screens.py` |
| Prompt (multi-line input) | `component/prompt/index.tsx` (60KB) | Input widget | `ui/screens.py` |
| Dialog system (stack-based) | `ui/dialog.tsx` | push_screen (modal screens) | `ui/screens.py` |
| Toast notifications | `ui/toast.tsx` | `self.notify()` | Built-in Textual |
| Command palette | `component/command-palette.tsx` | CommandPaletteScreen | `ui/screens.py` |
| Plugin slots (extension points) | `plugin/slots.tsx` | Not needed (monolithic) | N/A |
| Logo component | `component/logo.tsx` (28KB) | LogoWidget | `ui/components.py` |
| Spinner component | `component/spinner.tsx` | ProgressBar (indeterminate) | Built-in Textual |
| Border styles | `component/border.tsx` | TCSS `border: tall` | `ui/colors.tcss` |

---

## 4. Theme System

### opencode: JSON Theme Files
```json
{
  "defs": { "base": "#1e1e2e" },
  "theme": {
    "primary": "#89b4fd",
    "background": { "dark": "#1e1e2e", "light": "#eff1f5" },
    "text": "#cdd6f4"
  }
}
```
33 built-in themes. System theme auto-detected from terminal palette.

### Sidewinder: TCSS + Semantic Color Map

**Current:** Single `colors.tcss` with hardcoded hex values.

**Target:** Theme dataclass + TCSS variables + runtime switching.

```python
# ui/theme.py
from dataclasses import dataclass

@dataclass
class SidewinderTheme:
    """Semantic color slots — one per visual role."""
    # Core
    primary: str = "#4CAF50"        # Green — success, active, selected
    secondary: str = "#00BCD4"      # Cyan — info, headers, highlights
    accent: str = "#9C27B0"         # Purple — special actions
    error: str = "#F44336"          # Red — errors, danger
    warning: str = "#FF9800"        # Orange — warnings, caution
    success: str = "#00E676"        # Bright green — passwords found
    info: str = "#2196F3"           # Blue — informational

    # Text
    text: str = "#E6EDF3"           # Primary text
    text_muted: str = "#8B949E"     # Secondary text
    text_dim: str = "#484F58"       # Dimmed text

    # Background
    bg: str = "#0A0A0A"             # Screen background
    bg_panel: str = "#161B22"       # Panel/card background
    bg_element: str = "#21262D"     # Input, button background
    bg_hover: str = "#18181B"       # Hover state

    # Border
    border: str = "#30363D"         # Default border
    border_active: str = "#4CAF50"  # Focused/active border
    border_subtle: str = "#21262D"  # Subtle separation

    # WiFi-specific
    signal_strong: str = "#00E676"
    signal_medium: str = "#FF9800"
    signal_weak: str = "#F44336"
    enc_wpa3: str = "#00BCD4"
    enc_wpa2: str = "#00E676"
    enc_wpa: str = "#4CAF50"
    enc_wep: str = "#FF9800"
    enc_open: str = "#F44336"

# 3 built-in themes
THEMES = {
    "sidewinder": SidewinderTheme(),                          # Default green
    "cyberpunk": SidewinderTheme(primary="#FF00FF", secondary="#00FFFF", ...),
    "midnight": SidewinderTheme(primary="#6C7086", secondary="#89B4FA", ...),
}
```

**TCSS variable binding:**
```css
/* colors.tcss — uses CSS variables injected at runtime */
Screen {
    background: $bg;
    color: $text;
}
```

**Runtime theme switching:**
```python
class SidewinderApp(App):
    def switch_theme(self, name: str) -> None:
        theme = THEMES[name]
        self.query_one(Screen).styles.background = theme.bg
        # ... update reactive color vars
```

---

## 5. Keybinding System

### opencode: Modal Keymap with Leader Key
```typescript
// config/keybind.ts
session_new: keybind("<leader>n", "Create a new session"),
session_list: keybind("<leader>l", "List all sessions"),
```
- Modal modes (base, modal for dialogs)
- Leader key (`ctrl+x`) with timeout
- Timed sequences (`<leader>l`)
- Priority-based resolution
- 100+ bindings

### Sidewinder: Textual Binding Lists

**Per-screen bindings (current pattern):**
```python
class ScanScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "select_target", "Select"),
        Binding("s", "stop_scan", "Stop"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]
```

**Global bindings (app-level):**
```python
class SidewinderApp(App):
    BINDINGS = [
        Binding("question_mark", "help", "Help"),
        Binding("slash", "command", "Command"),
    ]
```

**Target: Vim-style throughout, consistent across screens:**
| Key | Action | Available On |
|-----|--------|-------------|
| `j` / `k` | Navigate down/up | All list screens |
| `Enter` | Select/confirm | All selection screens |
| `Esc` | Back/cancel | All screens |
| `/` | Command palette | Global |
| `?` | Help | Global |
| `1`-`9` | Quick select | Main menu, method picker |
| `Space` | Toggle checkbox | Deauth select |
| `a` | Select all | Deauth select |
| `s` | Stop | Scan, capture |
| `r` | Refresh | Adapter screen |
| `+` / `-` | Adjust rate | Deauth select |
| `e` / `d` | Enable/disable monitor | Monitor setup |
| `k` / `r` | Kill/restore services | Service check |

**No leader key needed** — Sidewinder is single-user, single-task. opencode needs leader keys because it has 100+ commands. We have ~20.

---

## 6. Screen Architecture

### opencode: Route-based (Home → Session → Plugin)
```tsx
<Switch>
  <Match when={route.data.type === "home"}>
    <Home />
  </Match>
  <Match when={route.data.type === "session"}>
    <Session />
  </Match>
</Switch>
```

### Sidewinder: Screen Stack (push/pop)
```python
# Navigate forward
self.app.push_screen(ScanScreen())

# Navigate back
self.app.pop_screen()

# Replace current
self.app.screen.replace(NewScreen())
```

**Screen hierarchy:**
```
SidewinderApp
├── MainMenuScreen (home)
│   ├── [1] ScanScreen
│   │   └── CaptureMethodScreen(target)
│   │       ├── [1] CaptureProgressScreen(method="passive")
│   │       └── [2] DeauthSelectScreen
│   │           └── CaptureProgressScreen(method="deauth")
│   │               └── ResultScreen(password, ssid, ...)
│   ├── [2] TargetSelectScreen
│   │   └── CaptureMethodScreen(target)
│   ├── [3] CrackProgressScreen (standalone entry)
│   │   └── ResultScreen
│   ├── [4] (stub — view captures)
│   ├── [5] AdapterScreen
│   │   └── MonitorSetupScreen(adapter_name)
│   ├── [6] CleanupScreen
│   ├── [7] HelpScreen
│   └── [0] Exit
├── CommandPaletteScreen (overlay, from /)
├── ErrorScreen (overlay, on error)
├── ResumeScreen (overlay, on startup)
├── WordlistPickerScreen (modal)
├── EnginePickerScreen (modal)
└── ServiceCheckScreen
```

---

## 7. Component System

### opencode: Plugin Slots (extensible)
```tsx
<TuiPluginRuntime.Slot name="sidebar_content" mode="replace">
  <MyCustomComponent />
</TuiPluginRuntime.Slot>
```

### Sidewinder: Reusable Widget Classes (fixed)
```python
# ui/components.py — all reusable widgets

class LogoWidget(Static): ...          # ASCII snake logo
class AdapterStatusWidget(Static): ... # Live adapter status
class EAPOLTracker(Static): ...        # M1-M4 handshake progress
class ErrorCard(Static): ...           # Structured error display
class TooltipPanel(Static): ...        # Context-sensitive help
```

**New components to add:**

```python
class StatusBar(Static):
    """Bottom status bar — adapter | channel | mode | signal | elapsed."""
    adapter: reactive[str] = reactive("--")
    channel: reactive[str] = reactive("--")
    mode: reactive[str] = reactive("managed")
    signal: reactive[int] = reactive(-100)
    elapsed: reactive[str] = reactive("00:00:00")

class ScanStatsBar(Static):
    """Live scan stats — networks | clients | elapsed."""
    networks: reactive[int] = reactive(0)
    clients: reactive[int] = reactive(0)
    elapsed: reactive[str] = reactive("00:00")

class TargetCard(Static):
    """AP detail card with signal bar, encryption, WPS status."""
    # Used in TargetSelectScreen and APDetailsScreen

class ClientRow(Static):
    """Single client row with MAC, vendor, signal, checkbox."""
    # Used in DeauthSelectScreen

class AttackProgressPanel(Static):
    """Combined stats + EAPOL + progress bar."""
    # Used in CaptureProgressScreen and CrackProgressScreen

class PasswordCard(Static):
    """Styled result card — SSID, BSSID, password, method, time."""
    # Used in ResultScreen
```

---

## 8. Real-Time Updates

### opencode: SSE Event Stream + Batch Rendering
```typescript
// SSE connection with 16ms batch window
for await (const event of events.stream) {
    queue.push(event)
    if (queue.length >= batchLimit) flush()
}
// Batch flush to SolidJS
batch(() => { for (const e of queue) emitter.emit("event", e) })
```

### Sidewinder: asyncio Tasks + Reactive Attributes

**Pattern 1: Polling (for airodump-ng output)**
```python
async def _scan_loop(self) -> None:
    """Poll airodump CSV every 1 second."""
    while self.scanning:
        networks = self._parser.parse_csv(self._csv_path)
        self.call_from_thread(self._update_table, networks)
        await asyncio.sleep(1)
```

**Pattern 2: Callback (for EAPOL detection)**
```python
def on_eapol(m1, m2, m3, m4, status):
    self.call_from_thread(self._tracker.update, m1, m2, m3, m4, status)

await capture_passive(iface, bssid, channel, on_eapol=on_eapol)
```

**Pattern 3: Background process streaming**
```python
async for line in self.mgr.stream(cmd):
    # line is already decoded str
    self.call_from_thread(self._update_progress, line)
```

**Pattern 4: Timer-based tick (for elapsed time)**
```python
def on_mount(self) -> None:
    self._timer = self.set_interval(1.0, self._tick)

def _tick(self) -> None:
    self.elapsed += 1
    h, m, s = self.elapsed // 3600, (self.elapsed % 3600) // 60, self.elapsed % 60
    self.query_one("#timer", Static).update(f"{h:02d}:{m:02d}:{s:02d}")
```

**Critical rule:** Never call `self.query_one()` from a background thread. Always use `self.call_from_thread()` or `self.run_from_thread()`.

---

## 9. Screen-by-Screen Implementation

### Screen 0: MainMenuScreen (Home)

**opencode reference:** `routes/home.tsx` — centered logo + prompt
**Sidewinder equivalent:** Logo + adapter status + numbered menu

```
┌─────────────────────────────────────────────────────┐
│  Sidewinder                          v0.7.0    [?] │
├─────────────────────────────────────────────────────┤
│                                                     │
│    ███████╗██╗██████╗ ███████╗██╗    ██╗██╗███╗... │
│    ██╔════╝██║██╔══██╗██╔════╝██║    ██║██║████╗.. │
│    ╚█████╗ ██║██║  ██║█████╗  ██║ █╗ ██║██║██╔██╗. │
│     ╚═══██╗██║██║  ██║██╔══╝  ██║███╗██║██║██║╚██╗ │
│    ██████╔╝██║██████╔╝███████╗╚███╔███╔╝██║██║ ╚███│
│    ╚═════╝ ╚═╝╚═════╝ ╚══════╝ ╚══╝╚══╝ ╚═╝╚═╝  ╚│
│                                                     │
│  Interface : wlx5c628b765de2                       │
│  Status    : READY                                  │
│  Channel   : --                                     │
│  Mode      : managed                                │
│                                                     │
│   [1] Scan WiFi networks                           │
│   [2] Target a specific network                    │
│   [3] Crack a captured handshake                   │
│   [4] View saved captures                          │
│   [5] Hardware & settings                          │
│   [6] Cleanup & restore                            │
│   [7] Help & tutorial                              │
│   [0] Exit                                         │
│                                                     │
│   / command   ? help   Esc quit                    │
│                                                     │
├─────────────────────────────────────────────────────┤
│ wlx5c... │ Ch:-- │ managed │ sidewinder v0.7.0     │
└─────────────────────────────────────────────────────┘
```

**Implementation:**
```python
class MainMenuScreen(Screen):
    BINDINGS = [
        Binding("1", "menu_1", "Scan"),
        Binding("2", "menu_2", "Target"),
        Binding("3", "menu_3", "Crack"),
        Binding("4", "menu_4", "View"),
        Binding("5", "menu_5", "Settings"),
        Binding("6", "menu_6", "Cleanup"),
        Binding("7", "menu_7", "Help"),
        Binding("0", "menu_0", "Exit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield LogoWidget(id="logo")
            yield AdapterStatusWidget(id="adapter-status")
            with Vertical(id="menu"):
                for key, label, action in MAIN_MENU_ITEMS:
                    yield Static(f" [[bold magenta]{key}[/bold magenta]] {label}")
        yield Footer()
```

---

### Screen 1: ScanScreen (Live WiFi Scan)

**opencode reference:** `routes/session/index.tsx` — scrollable list + live updates
**Sidewinder equivalent:** DataTable with live airodump-ng output

```
┌──────────────────────────────────────────────────────────────┐
│  WiFi Scan                              SCANNING... (12)     │
├──────────────────────────────────────────────────────────────┤
│  BSSID            CH  Signal   Privacy  ESSID        WPS    │
│  ──────────────── ── ──────── ──────── ──────────── ────── │
│  AA:BB:CC:DD:EE:01  6  ██████░░░░ -45  WPA2  MyNetwork     │
│  AA:BB:CC:DD:EE:02  1  ████░░░░░░ -62  WPA2  Neighbor      │
│  AA:BB:CC:DD:EE:03  11 ████████░░ -38  WPA3  Office_5G  ✓  │
│  [HIDDEN]           1  ██░░░░░░░░ -78  WPA2  [HIDDEN]      │
│  ...                                                          │
├──────────────────────────────────────────────────────────────┤
│  Enter: select   s: stop   j/k: navigate   Esc: back        │
└──────────────────────────────────────────────────────────────┘
```

**Key features:**
- DataTable with 9 columns (BSSID, CH, Signal, Rate, Privacy, Cipher, ESSID, WPS, Clients)
- Signal bar visualization (█░ characters)
- Hidden SSIDs marked as `[HIDDEN]`
- WPS column shows green check if enabled
- Auto-refresh every 1 second
- `j/k` vim navigation
- `Enter` selects target → pushes CaptureMethodScreen

**Implementation:**
```python
class ScanScreen(Screen):
    scanning: reactive[bool] = reactive(False)
    network_count: reactive[int] = reactive(0)

    def on_mount(self) -> None:
        self.scanning = True
        adapter = self.app._adapter_manager.get_best_for_operation("scan")
        self._scan_engine = ScanEngine(SubprocessManager())
        self.scan_task = asyncio.create_task(self._run_scan(adapter))

    async def _run_scan(self, adapter) -> None:
        await self._scan_engine.scan(
            mon_iface=adapter.iface,
            on_network=lambda n: self.call_from_thread(self.add_network, n)
        )

    def add_network(self, network) -> None:
        table = self.query_one("#scan-table", DataTable)
        # Add or update row
        bar = signal_bar(network.signal)
        row_data = (network.bssid, str(network.channel), bar, ...)
        try:
            table.update_row(network.bssid, *row_data)
        except KeyError:
            table.add_row(*row_data, key=network.bssid)
        self.network_count = len(table.rows)
```

---

### Screen 2: CaptureMethodScreen (Attack Selection)

**opencode reference:** `component/dialog-model.tsx` — card-based selection with descriptions
**Sidewinder equivalent:** Two-panel layout — method list + tooltip

```
┌────────────────────────────────┬────────────────────────────┐
│  Capture Method                │  Passive Capture           │
│                                │                            │
│  [1] Passive Capture           │  Listens passively for a   │
│      Listen for handshake      │  WPA handshake without     │
│      Risk: SAFE                │  sending any packets.      │
│                                │                            │
│  [2] Deauth + Capture          │  When to use               │
│      Kick clients, force       │  When you want to be       │
│      Risk: CAUTION             │  stealthy or the AP has    │
│                                │  many active clients.      │
│                                │                            │
│                                │  Risk level: SAFE          │
│                                │  No packets sent.          │
│                                │  Pure listening.           │
│                                │                            │
│                                │  Requires                  │
│                                │  • monitor_mode            │
├────────────────────────────────┴────────────────────────────┤
│  1-2: select   Esc: back                                    │
└─────────────────────────────────────────────────────────────┘
```

**Key features:**
- Horizontal split: method list (left) + tooltip panel (right)
- Tooltip updates on `j/k` navigation
- Risk level color coding (green/yellow/red)
- Requirements listed
- `1` or `2` to select, `Esc` to go back

---

### Screen 3: CaptureProgressScreen (Live Capture)

**opencode reference:** `routes/session/index.tsx` — live streaming content
**Sidewinder equivalent:** Stats + EAPOL tracker + progress bar

```
┌──────────────────────────────────────────────────────────────┐
│  Capturing Handshake — Method: Passive                       │
├──────────────────────────┬───────────────────────────────────┤
│  Beacons:  1,247         │  4-Way Handshake                  │
│  Data:     89            │                                    │
│  Signal:   ████████░░ -42│  [green]M1[/]  [green]M2[/]       │
│  Elapsed:  00:02:34      │  [dim]M3[/]    [dim]M4[/]         │
│                          │                                    │
│                          │  Status: PARTIAL                  │
├──────────────────────────┴───────────────────────────────────┤
│  ████████████████████░░░░░░░░░░░░░░░░░  58%                  │
├──────────────────────────────────────────────────────────────┤
│  Esc: stop capture   Ctrl+C: stop                            │
└──────────────────────────────────────────────────────────────┘
```

**Key features:**
- Left panel: live stats (beacons, data, signal, elapsed)
- Right panel: EAPOL M1-M4 tracker with color coding
- Progress bar (indeterminate during capture, determinate when complete)
- Timer updates every 1 second
- EAPOL status updates via callback from capture engine
- Auto-stops when M1+M2+M3+M4 all captured

---

### Screen 4: DeauthSelectScreen (Client Selection)

**opencode reference:** `component/dialog-select.tsx` — checkbox list
**Sidewinder equivalent:** DataTable with checkboxes + rate control

```
┌──────────────────────────────────────────────────────────────┐
│  Select Deauth Targets                                       │
├──────────────────────────────────────────────────────────────┤
│  [SEL]  MAC               Signal    Packets                  │
│  ─────  ────────────────  ────────  ───────                  │
│  ✓      AA:BB:CC:DD:EE:10  ████░░░   234                    │
│  ✓      AA:BB:CC:DD:EE:11  ██████░   567                    │
│    ✓    AA:BB:CC:DD:EE:12  ██░░░░░    89                    │
│                                                              │
│  Deauth rate: 10 frames/burst  (+/- to adjust)              │
├──────────────────────────────────────────────────────────────┤
│  Space: toggle   a: all   Enter: confirm   Esc: back        │
└──────────────────────────────────────────────────────────────┘
```

**Key features:**
- `Space` toggles individual client
- `a` selects/deselects all
- `+/-` adjusts deauth rate (5/10/20/30 frames/burst)
- Client fingerprinting (vendor) shown next to MAC
- `Enter` confirms selection → pushes CaptureProgressScreen

---

### Screen 5: ResultScreen (Password Found)

**opencode reference:** Not applicable (opencode doesn't have this)
**Sidewinder equivalent:** Styled result card

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│   ✓ PASSWORD FOUND!                                          │
│                                                              │
│   ┌─ RESULT ──────────────────────────────────────────┐     │
│   │  SSID:     MyNetwork                               │     │
│   │  BSSID:    AA:BB:CC:DD:EE:01                       │     │
│   │  Password: hunter2                                  │     │
│   │  Method:   Deauth + Aircrack-ng                    │     │
│   │  Keys:     1,247,893 tested                        │     │
│   │  Time:     00:03:21                                 │     │
│   └────────────────────────────────────────────────────┘     │
│                                                              │
│   [1] Save to file   [2] Copy to clipboard                  │
│   [4] Attack another   [6] Main menu                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

### Screen 6: AdapterScreen (Hardware & Settings)

**opencode reference:** `routes/session/sidebar.tsx` — info panel
**Sidewinder equivalent:** DataTable of all adapters

```
┌──────────────────────────────────────────────────────────────┐
│  Hardware & Adapters                                         │
├──────────────────────────────────────────────────────────────┤
│  Interface        Chipset    Driver    Bands   Monitor Inject│
│  ──────────────── ────────── ───────── ─────── ─────── ─────│
│  wlx5c628b765de2  RTL8821AU  rtw88     2.4/5G  YES     YES  │
│  wlx001ea6c65744  RT5370     rt2800usb 2.4G    YES     YES  │
│  wlo1             MT7902     mt7921e   2.4/5G  NO      NO   │
├──────────────────────────────────────────────────────────────┤
│  r: refresh   Esc: back                                      │
└──────────────────────────────────────────────────────────────┘
```

---

### Screen 7: CommandPaletteScreen (Slash Commands)

**opencode reference:** `component/command-palette.tsx`
**Sidewinder equivalent:** Input + filtered OptionList

```
┌──────────────────────────────────────────────────────────────┐
│  Command Palette                                             │
├──────────────────────────────────────────────────────────────┤
│  [/scan                                                     ]│
│                                                              │
│  /scan - Start WiFi scan                                    │
│  /target - Select target network                            │
│  /capture - Start capture                                   │
│  /crack - Start crack                                       │
│  /cleanup - Cleanup & restore                               │
│  /help - Open help tutorial                                 │
│  /status - Show current status                              │
│  /adapter - Switch adapter                                  │
│  /quit - Exit Sidewinder                                    │
├──────────────────────────────────────────────────────────────┤
│  Enter: submit   Esc: close                                  │
└──────────────────────────────────────────────────────────────┘
```

**Key features:**
- Input field at top for filtering
- OptionList below showing matching commands
- Fuzzy match on command name and description
- `Enter` executes selected command
- `Esc` closes palette

---

## 10. Navigation Flow

### Forward Navigation (Push)
```python
# Main menu → Scan
self.app.push_screen(ScanScreen())

# Scan → Capture Method (with target)
self.app.push_screen(CaptureMethodScreen(target=selected_network))

# Capture Method → Deauth Select
self.app.push_screen(DeauthSelectScreen())

# Deauth Select → Capture Progress
self.app.push_screen(CaptureProgressScreen(
    target=self.app.session.selected_target,
    method="deauth",
    selected_clients=selected
))

# Capture Progress → Result
self.app.push_screen(ResultScreen(
    password=password,
    ssid=ssid,
    bssid=bssid,
    method=method,
    keys_tested=keys
))
```

### Back Navigation (Pop)
```python
def action_back(self) -> None:
    self.app.pop_screen()
```

### Reset Navigation (Pop to root)
```python
def action_main_menu(self) -> None:
    while len(self.app.screen_stack) > 1:
        self.app.pop_screen()
```

### Modal Navigation (Push + dismiss)
```python
# Push modal
self.app.push_screen(WordlistPickerScreen())

# Dismiss with result (from within the screen)
self.dismiss(selected_path)
```

---

## 11. State Management

### App-Level State (shared across screens)
```python
class SidewinderApp(App):
    def __init__(self):
        self.session: Session = Session()           # Current session
        self._adapter_manager: AdapterManager       # Detected adapters
        self._service_manager: ServiceManager       # Process management
        self._cleanup_manager: CleanupManager       # Cleanup routines
        self._scan_engine: ScanEngine               # Active scan
```

### Screen-Level State (local to screen)
```python
class ScanScreen(Screen):
    scanning: reactive[bool] = reactive(False)      # Is scan running?
    network_count: reactive[int] = reactive(0)      # Networks found
    _scan_engine: ScanEngine                        # Scan engine instance
    scan_task: asyncio.Task                         # Background scan task
```

### Session Propagation
```python
# Set target during scan selection
self.app.session.selected_target = selected_network

# Read target in downstream screens
target = self.app.session.selected_target
```

**Critical rule:** Always set `session.selected_target` before pushing CaptureMethodScreen. Currently broken (BUG-004).

---

## 12. File Structure

```
sidewinder/ui/
├── __init__.py
├── app.py              # SidewinderApp — entry point, global state, slash commands
├── screens.py          # All 20 screen classes
├── components.py       # Reusable widgets (Logo, EAPOLTracker, ErrorCard, etc.)
├── colors.tcss         # Textual CSS theme
└── theme.py            # Theme dataclass + built-in themes (NEW)

sidewinder/core/
├── session.py          # Session, Network, Client dataclasses
├── scanner.py          # ScanEngine — airodump-ng wrapper
├── capture.py          # capture_passive, capture_deauth, poll_eapol
├── cracker.py          # aircrack-ng / hashcat wrapper
├── monitor.py          # enter/exit monitor mode
├── services.py         # kill/restore NetworkManager, wpa_supplicant
├── cleanup.py          # full_cleanup — restore everything
├── errors.py           # SidewinderError, ERROR_DB
├── subprocess_mgr.py   # SubprocessManager — async process management
├── adapter.py          # AdapterInfo, discover_all_adapters
├── attack.py           # BaseAttackEngine, AttackConfig, AttackResult
├── config.py           # SidewinderConfig — JSON config
├── fingerprint.py      # Fingerprinter — OUI lookup
├── intelligence.py     # IntelligenceEngine — attack recommendations
├── tooltips.py         # TOOLTIPS database
├── logger.py           # Rotating file logger
├── rfkill.py           # rfkill check/unblock
└── vm.py               # VM detection

sidewinder/adapters/
├── __init__.py         # AdapterManager, FailoverManager
├── base.py             # Adapter ABC, CARD_SETTINGS
├── rt5370.py           # RT5370Adapter
├── rtl8821au.py        # RTL8821AUAdapter
└── mt7902.py           # MT7902Adapter

sidewinder/attacks/
├── __init__.py         # Exports: AttackConfig, AttackResult, etc.
├── deauth.py           # DeauthConfig, DeauthResult, run_deauth
├── evil_twin.py        # EvilTwinEngine
├── pmkid.py            # PMKIDEngine
└── wps.py              # WPSEngine
```

---

## Appendix A: opencode Theme JSON Structure (Reference)

```json
{
  "name": "catppuccin",
  "defs": {
    "base": "#1e1e2e",
    "mantle": "#181825",
    "crust": "#11111b",
    "surface0": "#313244",
    "surface1": "#45475a",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "blue": "#89b4fa",
    "green": "#a6e3a1",
    "red": "#f38ba8",
    "yellow": "#f9e2af",
    "peach": "#fab387",
    "mauve": "#cba6f7"
  },
  "theme": {
    "primary": "blue",
    "secondary": "mauve",
    "accent": "peach",
    "error": "red",
    "warning": "yellow",
    "success": "green",
    "text": "text",
    "textMuted": "subtext",
    "background": "base",
    "backgroundPanel": "mantle",
    "backgroundElement": "surface0",
    "border": "surface1",
    "borderActive": "blue"
  }
}
```

## Appendix B: TCSS Color Variables (Target)

```css
/* Target: CSS variables bound to theme at runtime */
Screen {
    background: $bg;
    color: $text;
}

Header {
    background: $bg_panel;
    color: $primary;
    border-bottom: tall $border;
}

DataTable > .datatable--header {
    background: $secondary;
    color: $bg;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: $primary;
    color: $bg;
    text-style: bold;
}

/* ... etc */
```

## Appendix C: Binding Reference (All Screens)

| Screen | Key | Action | Description |
|--------|-----|--------|-------------|
| Global | `?` | `help` | Open help |
| Global | `/` | `command` | Command palette |
| MainMenu | `1`-`7`, `0` | `menu_N` | Quick menu |
| MainMenu | `Esc` | `quit` | Exit |
| ScanScreen | `Enter` | `select_target` | Select AP |
| ScanScreen | `s` | `stop_scan` | Stop scanning |
| ScanScreen | `j/k` | `cursor_down/up` | Navigate |
| ScanScreen | `Esc` | `back` | Back to menu |
| CaptureMethod | `1/2` | `method_N` | Select method |
| CaptureMethod | `j/k` | `cursor_down/up` | Navigate |
| CaptureMethod | `Esc` | `back` | Back |
| CaptureProgress | `Esc` | `stop` | Stop capture |
| CaptureProgress | `Ctrl+C` | `stop` | Stop capture |
| DeauthSelect | `Space` | `toggle` | Toggle client |
| DeauthSelect | `a` | `select_all` | Select all |
| DeauthSelect | `Enter` | `confirm` | Start deauth |
| DeauthSelect | `+/-` | `adjust_rate` | Change rate |
| DeauthSelect | `Esc` | `back` | Back |
| CrackProgress | `Esc` | `stop` | Stop crack |
| ResultScreen | `1` | `save` | Save to file |
| ResultScreen | `2` | `copy` | Copy password |
| ResultScreen | `4` | `attack_another` | New scan |
| ResultScreen | `6` | `main_menu` | Back to menu |
| AdapterScreen | `r` | `refresh` | Re-detect |
| AdapterScreen | `Esc` | `back` | Back |
| HelpScreen | `Esc/q` | `back` | Close |
| CommandPalette | `Enter` | `submit` | Execute command |
| CommandPalette | `Esc` | `back` | Close |

---

## 13. EXACT SIZING, PADDING, AND LAYOUT SPECIFICATION

> **This is the single source of truth for all UI dimensions.**
> Every screen MUST follow these exact specifications. No guessing.

### 13.1 Global Layout Rules

#### Terminal Root Box
```
width:  terminal.columns      (full width)
height: terminal.rows         (full height)
direction: column             (vertical stacking)
background: $bg
```

#### Vertical Zones (top to bottom)
```
┌─────────────────────────────────────────┐ ← row 0
│  HEADER (1 row, always)                │
├─────────────────────────────────────────┤ ← row 1
│                                         │
│  CONTENT AREA (flex: 1, fills rest)    │
│                                         │
├─────────────────────────────────────────┤ ← row terminal.rows-2
│  FOOTER (1 row, always)                │
└─────────────────────────────────────────┘ ← row terminal.rows-1
```

**Fixed elements:**
- `Header()` = exactly **1 row** tall
- `Footer()` = exactly **1 row** tall
- Content area = `terminal.rows - 2` rows available

---

### 13.2 Logo Specifications

#### opencode Logo (reference)
```
Width:  40 characters (19 left + 1 gap + 20 right)
Height: 4 lines
Colors: Left = dim gray (#90), Right = white/bold
Gap:    1 space between left and right halves
```

#### Sidewinder Logo (target)
```
Width:  ~50 characters (adjust to fit snake ASCII)
Height: 6 lines
Colors: Line 1-2 = $primary (green), Line 3-6 = $text (white)
```

#### Logo Placement (Home Screen)
```
┌──────────────────────────────────────────────────────┐
│  [Header: 1 row]                                     │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ← empty space: flex-grow=1 (fills top half) →       │
│                                                      │
│  ← empty space: height=4 rows (spacer below flex) →  │
│                                                      │
│  ╔═══╗                                               │
│  ║ S ║ ← Logo: 6 rows tall, centered horizontally   │
│  ║ I ║   paddingLeft: 2, paddingRight: 2             │
│  ║ D ║   maxWidth: terminal.width - 4                │
│  ║ E ║                                               │
│  ║ W ║                                               │
│  ╚═══╝                                               │
│                                                      │
│  ← empty space: height=1 row (spacer) →              │
│                                                      │
│  ┌────────────────────────────────────────┐          │
│  │  [Prompt: maxWidth=75 chars, centered] │          │
│  └────────────────────────────────────────┘          │
│                                                      │
│  ← empty space: flex-grow=1 (fills bottom half) →    │
│                                                      │
├──────────────────────────────────────────────────────┤
│  [Footer: 1 row]                                     │
└──────────────────────────────────────────────────────┘
```

**Exact values:**
```python
# Home screen compose()
yield Horizontal(
    Padding(
        Vertical(
            Spacer(flex=1),                    # top flex
            Spacer(height=4),                  # spacer
            LogoWidget(),                      # logo
            Spacer(height=1),                  # spacer
            Horizontal(
                Padding(
                    PromptWidget(),
                    left=2, right=2,           # horizontal padding
                ),
                max_width=75,                  # or auto: max(75, width * 0.7)
            ),
            Spacer(flex=1),                    # bottom flex
        ),
        left=2, right=2,                       # page padding
    ),
    width="100%",
)
```

**Prompt max width calculation (from opencode):**
```python
# opencode: promptMaxWidth = configured === "auto" ? Math.max(75, Math.floor(dimensions().width * 0.7)) : configured ?? 75
prompt_max_width = max(75, int(terminal_width * 0.7))
```

---

### 13.3 DataTable Specifications

#### Column Widths (Scan Screen)
```
BSSID:         17 chars  (AA:BB:CC:DD:EE:FF)
CH:             3 chars  (1-196)
Signal:        10 chars  (█░ bar + -XX dBm)
Rate:           8 chars  (54e mb/s)
Privacy:        7 chars  (WPA2)
Cipher:         7 chars  (CCMP)
ESSID:         20 chars  (truncated)
WPS:            4 chars  (YES/NO/---)
Clients:        3 chars  (0-99)
```

#### Column Widths (Adapter Screen)
```
Interface:     18 chars  (wlx5c628b765de2)
Chipset:       10 chars  (RTL8821AU)
Driver:        12 chars  (rtw88_8821au)
Bands:          7 chars  (2.4/5G)
Monitor:        6 chars  (YES/NO)
Inject:         6 chars  (YES/NO)
```

#### Column Widths (Deauth Select Screen)
```
SEL:            4 chars  (✓/✗)
MAC:           17 chars  (AA:BB:CC:DD:EE:FF)
Vendor:        15 chars  (truncated)
Signal:        10 chars  (█░ bar + -XX)
Packets:        6 chars  (0-9999)
```

#### DataTable Height
```
Header row:     1 row
Separator:      1 row (─ chars)
Data rows:      terminal.rows - 7 rows
                (header=1, separator=1, footer hints=1, padding=4)
Min rows:       5
Max rows:       30
```

#### Row Height
```
Each row = exactly 1 line
No multi-line rows
No word wrapping in cells
Truncate with "..." if too long
```

#### Cursor Highlight
```
Background: $primary
Text color: $bg
Bold:       True
```

---

### 13.4 Panel/Card Specifications

#### ErrorCard Dimensions
```
maxWidth:   terminal.width - 8
padding:    2 top/bottom, 3 left/right
border:     tall ($error color)
```
```
┌───────────────────────────────────────────┐ ← 3 chars from edge
│                                           │ ← 2 chars top padding
│  ⚠ ERROR: Network manager is running      │
│                                           │
│  What happened:                           │
│    NetworkManager interferes with monitor  │
│                                           │
│  How to fix:                              │
│    Run: sudo systemctl stop NetworkManager │
│                                           │ ← 2 chars bottom padding
└───────────────────────────────────────────┘
```

#### TooltipPanel Dimensions
```
maxWidth:   40 characters (fixed)
minHeight:  8 rows
padding:    1 top/bottom, 2 left/right
border:     rounded ($border)
```
```
┌──────────────────────────────┐
│  Passive Capture             │
│                              │
│  Listen for handshake...     │
│                              │
│  Risk: SAFE                  │
│  Requires: monitor mode      │
└──────────────────────────────┘
```

#### PasswordCard Dimensions (Result Screen)
```
width:      50 characters
padding:    2 all sides
border:     heavy ($success color)
alignment:  center
```
```
┌──────────────────────────────────────────────┐
│                                              │
│   ✓ PASSWORD FOUND!                          │
│                                              │
│   SSID:     MyNetwork                        │
│   BSSID:    AA:BB:CC:DD:EE:01                │
│   Password: hunter2                          │
│   Method:   Deauth + Aircrack-ng             │
│                                              │
└──────────────────────────────────────────────┘
```

---

### 13.5 Input Box Specifications

#### Command Palette Input
```
maxWidth:   terminal.width - 4
height:     1 row
padding:    0 left, 1 right (cursor space)
border:     none (just the text)
placeholder: "Type a command..."
```

#### Prompt Input (Home Screen)
```
maxWidth:   75 chars (or 70% of terminal width)
height:     auto (1-5 rows, grows with input)
padding:    1 top, 1 bottom
border:     tall ($border, $border_active when focused)
placeholder: rotates through suggestions
```

#### Input Box (General)
```
All Input widgets:
  minWidth:  20 chars
  maxWidth:  terminal.width - 10
  height:    1 row (fixed, single-line)
  padding:   0
  border:    tall ($border)
```

---

### 13.6 Progress Bar Specifications

#### Capture/Crack Progress Bar
```
width:      100% of content area
height:     1 row
bar_char:   █ (filled)
empty_char: ░ (empty)
color:      $primary (default), $success (complete), $error (failed)
show_pct:   True (right-aligned)
```
```
████████████████████░░░░░░░░░░░░░░░░░░░░  52%
```

---

### 13.7 Status Bar / Footer Specifications

#### Status Bar (Bottom)
```
height:     1 row
width:      100%
padding:    1 left, 1 right
segments:
  [adapter]  │  [channel]  │  [mode]  │  [signal]  │  [elapsed]
```
```
 wlx5c... │ Ch:6 │ monitor │ ████░ -42 │ 00:02:34
```

#### Hints Bar (Bottom of screen, above footer)
```
height:     1 row
width:      100%
padding:    1 left
color:      $text_muted
content:    "j/k: navigate  Enter: select  Esc: back"
```

---

### 13.8 Screen-by-Screen Layout (Exact Dimensions)

#### MainMenuScreen
```
Total height: terminal.rows
Header:       1 row
Content:      terminal.rows - 4 rows (header + footer + 2 padding)
Footer:       1 row

Layout (vertical):
  Header                                          [1 row]
  ┌─────────────────────────────────────────┐
  │  Spacer(flex=1)                         │ [variable]
  │  Spacer(height=4)                       │ [4 rows]
  │  LogoWidget()                           │ [6 rows]
  │  Spacer(height=1)                       │ [1 row]
  │  AdapterStatusWidget()                  │ [3 rows]
  │  Spacer(height=1)                       │ [1 row]
  │  Menu items (8 items × 1 row each)      │ [8 rows]
  │  Spacer(height=1)                       │ [1 row]
  │  Hints                                   │ [1 row]
  │  Spacer(flex=1)                         │ [variable]
  └─────────────────────────────────────────┘
  Footer                                          [1 row]
```

#### ScanScreen
```
Total height: terminal.rows
Header:       1 row
DataTable:    terminal.rows - 5 rows (header, hints, footer, padding)
Footer:       1 row

Layout (vertical):
  Header                                          [1 row]
  ┌─────────────────────────────────────────┐
  │  "WiFi Scan — SCANNING... (12)"         │ [1 row, title]
  │  DataTable                              │ [terminal.rows - 7]
  │  ─────────────────────────────────────  │ [1 row, separator]
  │  "Enter: select  s: stop  Esc: back"    │ [1 row, hints]
  └─────────────────────────────────────────┘
  Footer                                          [1 row]

DataTable columns (in order):
  BSSID(17) | CH(3) | Signal(10) | Rate(8) | Privacy(7) | Cipher(7) | ESSID(20) | WPS(4) | Clients(3)
```

#### CaptureMethodScreen
```
Total height: terminal.rows
Layout:       Horizontal split

┌──────────────────────────┬────────────────────┐
│  Method List             │  Tooltip Panel      │
│  width: 50%              │  width: 50%         │
│  padding: 2 left/right   │  padding: 1         │
│                          │  border: rounded    │
│  [1] Passive             │  Passive Capture    │
│      Listen for...       │  ─────────────      │
│  [2] Deauth              │  When to use...     │
│      Kick clients...     │                     │
│                          │  Risk: SAFE         │
│                          │  Requires: monitor  │
├──────────────────────────┴────────────────────┤
│  1-2: select  Esc: back                       │
└───────────────────────────────────────────────┘

Method list:
  Each item = 3 rows (title, description, blank)
  Cursor highlight = $primary bg
  Width = 50% of terminal (or 40 chars min)
```

#### CaptureProgressScreen
```
Total height: terminal.rows
Layout:       2-column horizontal split

┌──────────────────────┬───────────────────────┐
│  Stats Panel          │  EAPOL Tracker        │
│  width: 50%           │  width: 50%           │
│  padding: 1           │  padding: 1           │
│                       │                       │
│  Beacons:  1,247      │  M1: ● M2: ●         │
│  Data:     89         │  M3: ○ M4: ○         │
│  Signal:   ████ -42   │                       │
│  Elapsed:  00:02:34   │  Status: PARTIAL      │
├───────────────────────┴───────────────────────┤
│  ████████████████████░░░░░░░░░░░  58%          │
├───────────────────────────────────────────────┤
│  Esc: stop                                     │
└───────────────────────────────────────────────┘

Progress bar:
  width:   100% of content area
  height:  1 row
  margin:  1 row top
```

#### DeauthSelectScreen
```
Total height: terminal.rows
Layout:       DataTable + rate control

┌───────────────────────────────────────────────┐
│  Select Deauth Targets                        │ [1 row]
├───────────────────────────────────────────────┤
│  [✓]  MAC              Vendor    Signal  Pkts │ [header]
│  ───  ───────────────  ────────  ──────  ──── │ [separator]
│  ✓    AA:BB:CC:DD:EE:10 Intel    ████░    234 │ [data rows]
│  ✓    AA:BB:CC:DD:EE:11 Apple    ██████   567 │
│      AA:BB:CC:DD:EE:12 Realtek  ██░░░     89 │
├───────────────────────────────────────────────┤
│  Deauth rate: 10 frames/burst  (+/- to adj)  │ [1 row]
├───────────────────────────────────────────────┤
│  Space: toggle  a: all  Enter: confirm        │ [hints]
└───────────────────────────────────────────────┘

DataTable rows: terminal.rows - 8
Rate control:   1 row at bottom
Hints:          1 row at bottom
```

#### ResultScreen
```
Total height: terminal.rows
Layout:       Centered card

┌───────────────────────────────────────────────┐
│  Spacer(flex=1)                               │
│  ┌─────────────────────────────────────────┐  │
│  │  ╔══ PASSWORD FOUND! ══╗                │  │
│  │  ║                     ║                │  │
│  │  ║  SSID:     MyNetwork ║               │  │
│  │  ║  BSSID:    AA:BB:... ║               │  │
│  │  ║  Password: hunter2   ║               │  │
│  │  ║  Method:   Deauth    ║               │  │
│  │  ║  Time:     00:03:21  ║               │  │
│  │  ╚═══════════════════════╝               │  │
│  └─────────────────────────────────────────┘  │
│  Spacer(height=1)                             │
│  [1] Save   [2] Copy   [4] Again   [6] Menu │
│  Spacer(flex=1)                               │
└───────────────────────────────────────────────┘

Card: 50 chars wide, centered
Menu items: 1 row, centered
```

#### CommandPaletteScreen
```
Total height: terminal.rows
Layout:       Centered overlay

┌───────────────────────────────────────────────┐
│  Spacer(flex=1)                               │
│  ┌─────────────────────────────────────────┐  │
│  │  [/scan                              ]  │  │ [Input: 1 row]
│  ├─────────────────────────────────────────┤  │
│  │  /scan — Start WiFi scan               │  │ [OptionList]
│  │  /status — Show current status          │  │ [max 8 items]
│  │  /help — Open help                      │  │
│  └─────────────────────────────────────────┘  │
│  Spacer(flex=1)                               │
└───────────────────────────────────────────────┘

Input box:     width = terminal.width - 6
OptionList:    max height = 8 rows
Border:        tall ($border_active)
Centered:      horizontally + vertically
```

#### AdapterScreen
```
Total height: terminal.rows
Layout:       DataTable

┌───────────────────────────────────────────────┐
│  Hardware & Adapters                          │ [1 row title]
├───────────────────────────────────────────────┤
│  Interface     Chipset  Driver  Bands  Mon In│ [header]
│  ────────────  ──────── ─────── ────── ─────│ [separator]
│  wlx5c...      RTL8821AU rtw88  2.4/5G YES YES│ [data rows]
│  wlx001...     RT5370    rt2800 2.4G   YES YES│
│  wlo1          MT7902    mt7921e 2.4/5G NO  NO│
├───────────────────────────────────────────────┤
│  r: refresh  Esc: back                        │ [hints]
└───────────────────────────────────────────────┘

DataTable rows: terminal.rows - 6
```

#### HelpScreen
```
Total height: terminal.rows
Layout:       Scrollable Static

┌───────────────────────────────────────────────┐
│  WiFi Audit Tutorial                          │ [1 row title]
├───────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐  │
│  │  Scrollable content                     │  │ [terminal.rows - 5]
│  │                                         │  │
│  │  ## Quick Start                         │  │
│  │  1. Select adapter [5]                  │  │
│  │  2. Enable monitor mode [e]             │  │
│  │  3. Scan networks [1]                   │  │
│  │  ...                                    │  │
│  │                                         │  │
│  └─────────────────────────────────────────┘  │
├───────────────────────────────────────────────┤
│  Esc: close                                   │ [hints]
└───────────────────────────────────────────────┘

Content: scrollable, auto-scrolls to bottom
Border:  tall ($border)
```

#### ResumeScreen
```
Total height: terminal.rows
Layout:       Centered confirmation

┌───────────────────────────────────────────────┐
│  Spacer(flex=1)                               │
│  ┌─────────────────────────────────────────┐  │
│  │  Resume previous session?               │  │
│  │                                         │  │
│  │  Session: 12 APs found at 14:30         │  │
│  │  Last scan: wlx5c... on channel 6       │  │
│  │                                         │  │
│  │  [Y] Resume   [n] New session           │  │
│  └─────────────────────────────────────────┘  │
│  Spacer(flex=1)                               │
└───────────────────────────────────────────────┘

Dialog: 50 chars wide, centered
```

---

### 13.9 Spacing Reference

#### Padding Values (by widget type)
```
Screen content:    paddingLeft=2, paddingRight=2
Panel (Vertical):  paddingLeft=1, paddingRight=1
Card (Static):     paddingLeft=2, paddingRight=2, paddingTop=1, paddingBottom=1
DataTable:         paddingLeft=0, paddingRight=0 (full width)
Input:             paddingLeft=0 (border handles padding)
Button:            paddingLeft=2, paddingRight=2
```

#### Gap Values
```
Between menu items:      0 (each is its own Static)
Between table rows:      0 (DataTable handles spacing)
Between panels:          1 (Horizontal gap=1)
Between logo halves:     1 (gap=1 in Flex row)
Between header/content:  0 (border handles separation)
```

#### Margin Values
```
Logo from top:           flex=1 (centered vertically)
Prompt from logo:        height=1 (1 row spacer)
Content from header:     0
Content from footer:     0
Progress bar from stats: marginTop=1 (1 row)
Hints from content:      0 (directly below)
```

---

### 13.10 Border Styles

```
Standard panels:     border: tall $border
Active/focused:      border: tall $border_active
Error cards:         border: heavy $error
Success cards:       border: heavy $success
Tooltips:            border: rounded $border
No border:           border: hidden
```

**Border character reference:**
```
tall:    ╭╮╰╯│ (box drawing)
heavy:   ╔╗╚╝█ (double line)
rounded: ╭╮╰╯─ (rounded corners)
none:    (no border)
```

---

### 13.11 Color Application Rules

```
Primary ($primary):    Active cursor, selected items, progress bars, logo accent
Secondary ($secondary): Headers, section titles, info highlights
Error ($error):        Error cards, danger warnings, open networks, weak signal
Warning ($warning):    Caution states, WEP encryption, medium signal
Success ($success):    Password found, complete states, strong signal, WPA3
Info ($info):          Informational messages, status updates
Text ($text):          Primary text, menu items, table data
Text muted:           Hints, secondary info, dimmed text
Text dim:             Disabled items, placeholders
Background ($bg):     Screen background
Panel ($bg_panel):    Card/panel backgrounds
Element ($bg_element): Input backgrounds, button backgrounds
Border ($border):     Default borders
Border active:        Focused element borders
```

---

### 13.12 Typography Rules

```
Bold:       Menu titles, column headers, password display, status values
Dim:        Hints, secondary text, disabled items
Italic:     Tooltips descriptions, error explanations
Underline:  Section headers in help screen
Reverse:    Selected items (when $primary bg + $text fg)
Monospace:  All text (terminal default)
```

**No custom fonts** — terminal monospace only.

---

### 13.13 Animation/Transition Rules

```
Screen transitions:   fade (0.3s)
Cursor movement:      instant (no animation)
Progress bar:         smooth update (1s interval)
Timer:                1s tick
Scan refresh:         1s poll
EAPOL update:         instant (callback-driven)
Toast notifications:  3s auto-dismiss, slide in from bottom
```

---

### 13.14 Minimum Terminal Size

```
Minimum width:   80 columns
Minimum height:  24 rows
Recommended:     120×40+
Optimal:         160×50+

If terminal < 80 cols:
  Show: "Terminal too small. Minimum 80×24 required."
  Exit gracefully.

If terminal < 100 cols:
  Hide: WPS column, Clients column
  Show: "Some columns hidden. Resize to 100+ for full view."
```

---

### 13.15 Responsive Behavior

```
Width >= 120 cols:
  - Sidebar visible (if applicable)
  - All columns shown
  - Full tooltip panel

Width 80-119 cols:
  - Sidebar hidden
  - WPS/Clients columns hidden
  - Tooltip panel compressed

Height >= 40 rows:
  - Full logo + menu
  - All content visible

Height 24-39 rows:
  - Logo may be compressed (fewer spacers)
  - Content area smaller but functional
```

---

### 13.16 Widget Composition Pattern (Standard Screen)

Every screen follows this template:

```python
class SomeScreen(Screen):
    """Standard screen layout."""
    
    BINDINGS = [...]  # Always: escape→back, j/k→navigate, enter→select
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)           # 1 row, always
        
        with Vertical(id="content"):
            yield Static("[bold]Title[/bold]")  # 1 row
            yield DataTable(id="table")         # flex=1 (fills space)
            yield Static("hints text", id="hints")  # 1 row
        
        yield Footer()                          # 1 row, always
```

**The Vertical(id="content") must have:**
- `padding_left=2, padding_right=2` (via TCSS or wrapper)
- The DataTable must have `expand=True, fill=True` to fill available space

---

### 13.17 Quick Reference Card

```
LOGO:     40w × 6h, centered, padding=2
PROMPT:   maxWidth=75, height=auto, centered
DATATABLE: full width, header=1 row, cursor=$primary
PANEL:    padding=1-2, border=tall
CARD:     width=50, centered, border=heavy
INPUT:    height=1, border=tall
PROGRESS: height=1, █░ chars, percentage right-aligned
STATUS:   height=1, segments separated by │
HINTS:    height=1, $text_muted, left-aligned
ERROR:    maxWidth=term-8, padding=2-3, border=heavy $error
TOOLTIP:  width=40, padding=1-2, border=rounded
SPACER:   flex=1 (fills remaining space)
HEADER:   height=1, always present
FOOTER:   height=1, always present
MIN TERM: 80×24
PAD:      screen=2, panel=1, card=2-1-2-1
GAP:      between panels=1, between items=0
```

---

## 14. OpenCode-Inspired Architecture (WiFi Audit Adaptation)

> Source: OpenCode TUI research — neo-brutalist terminal aesthetic,
> panel-based layout, dense information, leader key system.
> Adapted for Sidewinder's single-user, single-process WiFi audit context.

### 14.1 Visual Language: Neo-Brutalist Terminal

OpenCode uses Unicode block characters as structural elements, not decorative. Sidewinder adopts this:

```
OpenCode Symbol    Usage                      Sidewinder Adaptation
─────────────────────────────────────────────────────────────────────
┃ (U+2503)         Content frame borders      Scan table borders, panel edges
█ (U+2588)         Thick sidebar separator    Adapter panel divider
▄ ▀ ╹              Corner/edge details        Panel corners, input frame
→                   Read operations            "Scanning...", "Reading adapter..."
←                   Write operations           "Saving capture...", "Cracking..."
▣ (U+25A3)         Completed tool calls       ✅ Handshake captured, ✅ Crack done
■                   Completed steps            EAPOL M1 ■ M2 ■ M3 □ M4
⬝                   Remaining steps            Progress indicators
● (orange dot)      Tips and hints             "● Deauth forces reconnection"
△                   Permission-required        "△ Requires root"
```

### 14.2 Panel Layout: WiFi Audit Zones

OpenCode divides screen into Left (chat), Right (sidebar), Bottom (prompt), Status bar.
Sidewinder adapts this for WiFi audit workflow:

```
┌──────────────────────────────────────────────────────────────────────┐
│ ● SIDEWINDER v0.11                    [wlan0] [MON] [CH:6] [87dBm] │  ← Status bar (1 row)
├───────────────────────────────────────────█──────────────────────────┤
│                                               │                      │
│  MAIN CONTENT AREA                            │  SIDEBAR             │
│  (scan results / capture progress / crack)    │  (adapter status)    │
│                                               │  (signal strength)   │
│  ┃ BSSID             CH  PWR   ENC  ESSID ┃  │  (channel info)      │
│  ┃ ─────────────────────────────────────── ┃  │  (client count)      │
│  ┃ AA:BB:CC:DD:EE:FF  6  -47   WPA2 NASA  ┃  │  (mode)              │
│  ┃ 11:22:33:44:55:66 11  -62   WPA2 NASA+ ┃  │  (attack history)    │
│  ┃ 77:88:99:AA:BB:CC  1  -71   OPEN Guest ┃  │                      │
│                                               │                      │
│  [Live: 2.3s | Networks: 3 | Clients: 4]      │  ▣ Handshake: YES    │
│                                               │  ■ M1 ■ M2 ■ M3 □ M4 │
├───────────────────────────────────────────────┤                      │
│ ┃ ╹▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀ ┃ │  ● Next: crack?      │
│ ┃ > scan --band 2g --channel 6              ┃ │                      │
│ ┃ ╹▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄ ┃ ├──────────────────────┤
│                                               │ ~/sidewinder:main    │
│  /scan  /target  /crack  /cleanup  ? help     │ • Sidewinder v0.11   │
└───────────────────────────────────────────────┴──────────────────────┘
  ↑ Input/prompt area (3 rows)                    ↑ Footer (1 row)
```

**Key mapping from OpenCode → Sidewinder:**

| OpenCode Zone | OpenCode Content | Sidewinder Zone | Sidewinder Content |
|---|---|---|---|
| Left panel | Chat messages | Main content | Scan/capture/crack tables |
| Right panel (42 cols) | Session title, tokens, cost | Sidebar (20 cols) | Adapter, signal, channel, clients |
| Bottom prompt | User input + model name | Input area | Slash commands + current operation |
| Status bar | ~/path:branch + version | Status bar | Adapter + mode + channel + signal |
| Footer | Version string | Footer | Hints + keybinds |

### 14.3 Dense Information Principle

OpenCode: "No decorative whitespace wasted; every region carries semantic content."

Sidewinder application:

```
WASTE (current)                    DENSE (OpenCode-inspired)
─────────────────────────────────────────────────────────────
[1] Scan WiFi networks             [1] Scan ─────────── ● scanning...
[2] Target a specific network      [2] Target ────────── ■ NASA (AA:BB:CC)
[3] Crack a captured handshake     [3] Crack ─────────── ▣ password123
[4] View saved captures            [4] Captures ──────── 3 files, 1 cracked
[5] Hardware & settings            [5] Settings ──────── RTL8821AU [MON]
[6] Cleanup & restore              [6] Cleanup ───────── ▣ restored
[7] Help & tutorial                [7] Help ──────────── ?
[0] Exit                           [0] Exit ──────────── ⏻
```

Each menu item shows its current state inline. No need to navigate to see status.

### 14.4 Leader Key System (Adapted)

OpenCode uses `ctrl+x` as leader key for nested commands. Sidewinder adapts this for WiFi audit:

```
OpenCode: ctrl+x m → model switcher
          ctrl+x t → theme picker
          ctrl+x l → session list

Sidewinder: ctrl+a → attack submenu
              ctrl+a d → deauth attack
              ctrl+a p → PMKID capture
              ctrl+a w → WPS pixie-dust
              ctrl+a e → evil twin
            ctrl+s → scan submenu
              ctrl+s f → full scan
              ctrl+s b → band scan
              ctrl+s c → channel lock
            ctrl+c → capture submenu
              ctrl+c p → passive capture
              ctrl+c a → active deauth capture
            ctrl+x → context actions (screen-specific)
```

**Implementation in Textual:**

```python
# BINDINGS with ctrl+ prefix for leader-style navigation
BINDINGS = [
    Binding("ctrl+a", "attack_menu", "Attack", show=False),
    Binding("ctrl+s", "scan_menu", "Scan", show=False),
    Binding("ctrl+c", "capture_menu", "Capture", show=False),
]

def action_attack_menu(self) -> None:
    """Show attack submenu as inline overlay."""
    self.query_one("#attack-overlay").display = True
```

### 14.5 Inline Dialogs (Not Modals)

OpenCode: "Permission dialog expands the prompt box inline — no modal overlay."

Sidewinder adaptation — **inline confirmations** instead of push_screen modals:

```
CURRENT (modal):                    OPENCODE-INSPIRED (inline):
┌─────────────────────┐             ┌──────────────────────────────┐
│                     │             │ [1] Scan  [2] Target  ...    │
│   ┌──────────────┐  │             │                              │
│   │ Confirm?     │  │             │ △ Kill NetworkManager?       │
│   │ [Y]es  [N]o  │  │             │ ▸ Allow once  Allow always  │
│   └──────────────┘  │             │   ⇆ select  enter confirm   │
│                     │             │                              │
└─────────────────────┘             └──────────────────────────────┘
```

**Textual implementation:**

```python
class InlineConfirm(Widget):
    """Expandable confirmation bar — sits at bottom of current screen."""
    
    DEFAULT_CSS = """
    InlineConfirm {
        dock: bottom;
        height: 3;
        background: $surface;
        border-top: tall $accent;
        display: none;
    }
    InlineConfirm.active {
        display: block;
    }
    """
    
    def confirm(self, message: str, on_yes: Callable, on_no: Callable) -> None:
        self.query_one("#confirm-msg").update(message)
        self.add_class("active")
        self._on_yes = on_yes
        self._on_no = on_no
```

### 14.6 Widget Palette (WiFi Audit Widgets)

OpenCode widget set → Sidewinder equivalents:

| OpenCode Widget | OpenCode Usage | Sidewinder Widget | Sidewinder Usage |
|---|---|---|---|
| `Text` | Inline text with color | `Static` | All text rendering |
| `Box` | Layout container | `Vertical` / `Horizontal` | Panel layouts |
| `ScrollBox` | Scrollable region | `VerticalScroll` | Scan results, logs |
| `Input` | Text entry | `Input` | Command entry, filter |
| `Code` | Syntax-highlighted code | `DataTable` | Scan tables, results |
| `Diff` | Side-by-side diff | `Horizontal` split | Before/after views |
| `Select` | Selection widget | `Select` | Adapter picker, engine |
| `ASCII-Font` | Logo rendering | `LogoWidget` | SIDEWINDER ASCII art |
| `Line-Number` | Code line numbers | Row numbers in DataTable | Target numbering |

**WiFi-specific widgets to add:**

```python
class SignalBar(Widget):
    """Visual signal strength indicator: ▁▃▅▇█"""
    
class EAPOLTracker(Widget):
    """M1 ■ M2 ■ M3 □ M4 progress display"""

class ChannelIndicator(Widget):
    """CH: 6 (2.4GHz) with band coloring"""

class AdapterCard(Widget):
    """█ Adapter: RTL8821AU [MON] 5GHz 80MHz"""

class AttackStatus(Widget):
    """▣ Deauth: 10/10 frames sent, 3 clients"""
```

### 14.7 Theme System (Live Switching)

OpenCode: 33 themes, live switching via `ctrl+x t`, no restart.

Sidewinder: 13 themes, live switching via `/theme` command palette.

**OpenCode theme structure:**
```json
{
  "defs": { "base": "#1e1e2e" },
  "theme": {
    "primary": "#89b4fa",
    "background": "#1e1e2e",
    "text": "#cdd6f4"
  }
}
```

**Sidewinder theme structure (already implemented):**
```python
@dataclass
class SidewinderTheme:
    primary: str = "#4CAF50"
    background: str = "#0A0A0A"
    surface: str = "#161B22"
    # ... WiFi-specific: signal colors, encryption colors, method colors
```

**Live switching mechanism (already working):**
```python
def palette_option_highlighted(self, event) -> None:
    """Preview theme on highlight (before selection)."""
    theme_name = event.option.id.replace("theme-", "")
    if theme_name in self.themes:
        self.theme = theme_name  # Instant preview
```

### 14.8 Status Bar (Always Visible)

OpenCode: `~/path:branch` left, `• OpenCode 1.2.20` right.

Sidewinder: `wlan0 [MON] CH:6 87dBm` left, `● scanning... 02:30` right.

```
┌──────────────────────────────────────────────────────────────────────┐
│ wlan0 [MON] CH:6 87dBm │ Networks: 12 │ Clients: 8 │ ● 02:30      │
└──────────────────────────────────────────────────────────────────────┘

Segments:
  [adapter] [mode] [channel] [signal] │ [networks] [clients] │ [status] [time]
  
Colors:
  adapter:  $foreground (default)
  mode:     $success (monitor), $warning (managed), $error (unknown)
  channel:  $secondary
  signal:   $success (> -50), $warning (-50 to -70), $error (< -70)
  status:   $primary (scanning), $success (done), $error (failed)
```

### 14.9 Responsive Layout Rules

OpenCode: Sidebar hides on narrow terminals. Content reflows.

Sidewinder: Same principle, WiFi-specific breakpoints.

```
Width >= 120 cols:
  ├─ Main content (flex=1)
  ├─ █ separator (1 col)
  └─ Sidebar (20 cols) — adapter details, signal, clients

Width 80-119 cols:
  ├─ Main content (full width)
  └─ Sidebar hidden — adapter info moves to status bar

Width < 80 cols:
  └─ "Terminal too small. Minimum 80×24 required."
```

### 14.10 Interaction Grammar

OpenCode's interaction vocabulary:
- `→` for read, `←` for write
- `▣` for completed, `■` for in-progress, `⬝` for remaining
- `●` for tips, `△` for permissions
- `⇆` for selection navigation

Sidewinder's WiFi audit vocabulary:

```
Symbol   Meaning              Example
──────   ──────────────────   ─────────────────────────
→        Scanning             → Scanning 2.4GHz channels...
←        Capturing            ← Sending deauth frames...
▣        Completed            ▣ Handshake captured!
■        In progress          ■ M1 ■ M2 ■ M3 □ M4
⬝        Remaining            ⬝ 3 frames until timeout
●        Tip                  ● Deauth forces reconnection
△        Requires action      △ Kill NetworkManager first?
✓        Success              ✓ Password found: admin123
✗        Failure              ✗ Capture timeout
↻        Retry                ↻ Retrying deauth (2/3)
⊕        Selected             ⊕ NASA (AA:BB:CC:DD:EE:FF)
⊖        Deselected           ⊕ Guest (OPEN)
```

### 14.11 Keybind Reference (Leader-Style)

```
GLOBAL (always active):
  /           Command palette (fuzzy search)
  ?           Help screen
  Esc         Back / cancel / close
  ctrl+c      Quit (with confirmation)

SCREEN-SPECIFIC:
  1-7, 0      Main menu selection
  j/k         Navigate up/down (tables)
  Enter       Select / confirm
  Space       Toggle checkbox (deauth clients)
  C           Start capture (from AP details)
  s           Stop scan / capture
  r           Refresh / rescan

LEADER STYLE (ctrl+ prefix):
  ctrl+a      Attack submenu
  ctrl+s      Scan submenu  
  ctrl+c      Capture submenu
  ctrl+x      Context actions (screen-specific)

SLASH COMMANDS:
  /scan       Start WiFi scan
  /target     Select target network
  /crack      Start cracking
  /capture    Start capture
  /cleanup    Restore system
  /help       Open help
  /status     Show status
  /adapter    Switch adapter
  /theme      Switch theme
  /compact    Toggle compact mode
  /quit       Exit
```

### 14.12 What We're NOT Copying

OpenCode has features that don't apply to Sidewinder:

| OpenCode Feature | Why Not Sidewinder |
|---|---|
| Multi-line prompt (60KB component) | We use slash commands, not free-form chat |
| SSE streaming (24KB sync provider) | Single process, no server |
| 20+ context providers | Flat app state is simpler for our use case |
| Plugin slots | Monolithic tool, no extensions needed |
| LLM token counting | Not an AI assistant |
| Cost tracking | Not a paid API |
| Model switching | Not an AI model |
| Diff rendering | We show tables, not code diffs |
| Mouse tracking | Optional, keyboard-first |
| External editor (! prefix) | Not composing long messages |
