# Visiotask Context & Architecture

### Project DNA
Visiotask is a Python-based automation tool with a GUI for executing sequential, image-based macro tasks. It detects specified images on screen and performs configurable actions (like clicking and double-clicking) based on customizable wait times. Users configure steps graphically and let the application sequence through them with logic for fallbacks and visual confirmation.

### Architecture Map
```
src/
├── main.py               # Entry Point
├── gui/                  # GUI Layer
│   ├── __init__.py
│   ├── app.py            # Main Tkinter App setup and views
│   ├── components.py     # Custom UI widgets (RoundedButton, ToggleSwitch, etc.)
│   └── overlay.py        # Frameless full-screen interactive overlay for region selection
├── engine/               # Core Engine
│   ├── __init__.py
│   └── macro.py          # Macro threading, sequence handling, branching logic
├── image/                # Image Logic
│   ├── __init__.py
│   └── vision.py         # OpenCV/mss screen scanning and matching
└── utils/                # Config & Utils
    ├── __init__.py
    ├── config.py         # System settings, directories, and constants
    └── state.py          # State singleton holding MACRO_SEQUENCE, IMAGE_FILES, and CUSTOM_REGION
```

### Change Ledger
- **gui/app.py & utils/state.py**: Removed manual "Screen ratio" inputs from the UI. The application now auto-detects `SCREEN_WIDTH` and `SCREEN_HEIGHT` via `tkinter` attributes on startup, mathematically determines the dynamic `SCREEN_RATIO`, and suppresses all bounding warnings for "all" scan types. These values are automatically passed into `state` and serialized quietly.
- **gui/overlay.py**: Added `RegionSelectorOverlay` class utilizing `mss` and `PIL` to capture the screen, dim it dynamically, and allow users to drag a bounding box indicating the region mapping parametrically. Added confirmation and cancellation callbacks.
- **utils/state.py**: Added parameter support for `.CUSTOM_REGION` array to save the new parametric mappings into the JSON file.
- **gui/app.py**: Linked the "Select Region" capability by extending combobox options resolving state transitions to trigger `RegionSelectorOverlay` passing logic states.
- **engine/macro.py**: Implemented conditions to intercept a "custom" enum checking if `CUSTOM_REGION` array contains coordinates to process region slices mapping directly into `image/vision.py -> find_and_click()`.
- `utils/config.py`: Extracted core constants, path resolution logic, and `APP_DATA_DIR` paths out of `visiotask.py`. Setup global directories.
- `utils/state.py`: Introduced the `AppState` class holding JSON config data to bypass earlier `global` mutation issues. Now serves as a singleton imported by other modules.
- `image/vision.py`: Extracted OpenCV mapping loop and `mss` screen grabber into `find_and_click`. Handled mouse logic to decouple cv2 dependencies from GUI logic.
- `engine/macro.py`: Contains `run_macro()` method which iterates the sequence states asynchronously running scans and resolving branching (skip conditions, block next).
- `gui/components.py`: Pulled out custom canvas subclasses like `RoundedButton`, `SmoothScrollbar`, `ToggleSwitch` into separate UI classes.
- `gui/app.py`: Reduced Tkinter boilerplate and event handlers out of `visiotask.py`. Uses `src.utils.state` exclusively for sequence reads replacing python globals. Now cleanly isolates `MacroApp` class.
- `main.py`: Simple entry loop starting `root.mainloop()`.
- Deleted single file `visiotask.py` logic footprint.

### Logic Flow
1. **Entry**: `main.py` opens `gui/app.py`.
2. **Config**: At launch `utils/state.py` fetches the last known state (`MACRO_SEQUENCE`).
3. **Trigger**: When 'Start Macro' is hit, a daemon thread launches `engine/macro.py -> run_macro()`.
4. **Execution Loop**: `run_macro` walks down the sequence structure consulting `state.py`.
5. **Pattern Recognition**: For each step, `run_macro` calls `image/vision.py -> find_and_click()` passing the image metadata.
6. **Action**: If found, `pyautogui` mimics the input, else `run_macro` handles retry/skipping delays via timers.

### Dependency Map
- **`main.py`** depends on `gui/app.py`.
- **`gui/app.py`** depends on `utils/config.py`, `utils/state.py`, `gui/components.py`, `engine/macro.py`.
- **`engine/macro.py`** depends on `utils/state.py`, `image/vision.py`.
- **`image/vision.py`** depends on `utils/config.py`.
- **`utils/state.py`** depends on `utils/config.py`.

(No circular dependencies. Safe structure adhering to Separation of Concerns).
