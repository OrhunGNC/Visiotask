# Graph Report - C:\Users\pc\source\repos\Visiotask  (2026-11-06)

## Corpus Check
- 15 files · ~20,789 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 203 nodes · 470 edges · 17 communities detected
- Extraction: 73% EXTRACTED · 27% INFERRED · 0% AMBIGUOUS · INFERRED: 127 edges (avg confidence: 0.71)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]

## God Nodes (most connected - your core abstractions)
1. `MacroApp` - 54 edges
2. `RoundedButton` - 20 edges
3. `CustomDropdown` - 20 edges
4. `SequenceReorderingTests` - 17 edges
5. `ProgressRing` - 16 edges
6. `SmoothScrollbar` - 16 edges
7. `ToggleSwitch` - 13 edges
8. `ScreenshotOverlay` - 13 edges
9. `CustomInputDialog` - 12 edges
10. `RegionSelectorOverlay` - 12 edges

## Surprising Connections (you probably didn't know these)
- `main()` --calls--> `MacroApp`  [INFERRED]
  C:\Users\pc\source\repos\Visiotask\src\main.py → C:\Users\pc\source\repos\Visiotask\src\gui\app.py
- `MacroApp` --uses--> `RoundedButton`  [INFERRED]
  C:\Users\pc\source\repos\Visiotask\src\gui\app.py → C:\Users\pc\source\repos\Visiotask\src\gui\components.py
- `MacroApp` --uses--> `ToggleSwitch`  [INFERRED]
  C:\Users\pc\source\repos\Visiotask\src\gui\app.py → C:\Users\pc\source\repos\Visiotask\src\gui\components.py
- `MacroApp` --uses--> `SmoothScrollbar`  [INFERRED]
  C:\Users\pc\source\repos\Visiotask\src\gui\app.py → C:\Users\pc\source\repos\Visiotask\src\gui\components.py
- `MacroApp` --uses--> `CustomDropdown`  [INFERRED]
  C:\Users\pc\source\repos\Visiotask\src\gui\app.py → C:\Users\pc\source\repos\Visiotask\src\gui\components.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.1
Nodes (3): MacroApp, Create a single image card placed with grid()., main()

### Community 1 - "Community 1"
Cohesion: 0.1
Nodes (32): background_click(), BITMAPINFOHEADER, capture_window(), _client_area_size(), _enum_callback(), enumerate_windows(), find_window_by_title(), foreground_click() (+24 more)

### Community 2 - "Community 2"
Cohesion: 0.1
Nodes (11): Draw a minimal line icon on a small canvas., Compact label inside a sub-frame., _bind_mousewheel(), CustomInputDialog, ProgressRing, Animated circular progress ring with pulsing glow and play icon.     States: id, Set ring state. True = running (green), False = stopped (red)., Reset ring to idle (dim) state. (+3 more)

### Community 3 - "Community 3"
Cohesion: 0.18
Nodes (6): AppState, descendants(), drag_geometry(), pointer(), Sequence regression checks without opening a window or touching user data., SequenceReorderingTests

### Community 4 - "Community 4"
Cohesion: 0.21
Nodes (4): CustomDropdown, Premium dropdown with dark fill, soft orange hover, and smooth arrow., Truncate display text if max_display_len is set., Update display label when variable changes (truncated if needed).

### Community 5 - "Community 5"
Cohesion: 0.16
Nodes (4): Compact label above a form field., Full-screen overlay that captures the screen, lets the user drag-select     a r, RegionSelectorOverlay, ScreenshotOverlay

### Community 6 - "Community 6"
Cohesion: 0.29
Nodes (3): Premium button with rounded corners, hover glow, and press animation., Generate smooth rounded rectangle polygon points using arc approximation., RoundedButton

### Community 7 - "Community 7"
Cohesion: 1.0
Nodes (2): README.md, requirements.txt

### Community 8 - "Community 8"
Cohesion: 1.0
Nodes (0):

### Community 9 - "Community 9"
Cohesion: 1.0
Nodes (0):

### Community 10 - "Community 10"
Cohesion: 1.0
Nodes (0):

### Community 11 - "Community 11"
Cohesion: 1.0
Nodes (0):

### Community 12 - "Community 12"
Cohesion: 1.0
Nodes (0):

### Community 13 - "Community 13"
Cohesion: 1.0
Nodes (0):

### Community 14 - "Community 14"
Cohesion: 1.0
Nodes (1): Supply deterministic screen geometry while keeping all Tk callbacks real.

### Community 15 - "Community 15"
Cohesion: 1.0
Nodes (1): createexe.txt

### Community 16 - "Community 16"
Cohesion: 1.0
Nodes (1): PROJECT_CONTEXT.md

## Knowledge Gaps
- **25 isolated node(s):** `Background and foreground mouse clicking for Windows.  Click modes: - foregro`, `Return (width, height) of a window's client area.`, `Return a list of (hwnd, title) for usable visible top-level windows.      Filt`, `Find a window by exact title. Returns the root-owner HWND or None.`, `Get the title of a window by its HWND.` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 7`** (2 nodes): `README.md`, `requirements.txt`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 8`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 9`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 10`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 11`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 12`** (1 nodes): `config.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 13`** (1 nodes): `__init__.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 14`** (1 nodes): `Supply deterministic screen geometry while keeping all Tk callbacks real.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 15`** (1 nodes): `createexe.txt`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 16`** (1 nodes): `PROJECT_CONTEXT.md`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MacroApp` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`?**
  _High betweenness centrality (0.452) - this node is a cross-community bridge._
- **Why does `run_macro()` connect `Community 1` to `Community 0`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._
- **Why does `RoundedButton` connect `Community 6` to `Community 0`, `Community 2`, `Community 5`?**
  _High betweenness centrality (0.102) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `MacroApp` (e.g. with `RoundedButton` and `ToggleSwitch`) actually correct?**
  _`MacroApp` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `RoundedButton` (e.g. with `MacroApp` and `Draw a minimal line icon on a small canvas.`) actually correct?**
  _`RoundedButton` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `CustomDropdown` (e.g. with `MacroApp` and `Draw a minimal line icon on a small canvas.`) actually correct?**
  _`CustomDropdown` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `ProgressRing` (e.g. with `MacroApp` and `Draw a minimal line icon on a small canvas.`) actually correct?**
  _`ProgressRing` has 6 INFERRED edges - model-reasoned connections that need verification._
