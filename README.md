# Visiotask

**Note:** The source code for this project was authored using vibecoding techniques, powered by a combination of Claude Opus 4.6, GPT 5.3-Codex, and Gemini 3.1 Pro.

Visiotask is an image-based screen automation and macro execution tool. It uses computer vision to detect specific UI elements and images on your screen and interacts with them by automatically clicking on the matched elements. It provides a sleek, modern, dark-themed GUI to control the macro and configure scanning settings.

## Features & Functions

### Image-Based Macro Execution
- **Template Matching:** Utilizes OpenCV (`cv2.matchTemplate`) and `mss` for high-performance, real-time screen grabbing and image recognition to find visual targets on the screen.
- **Automated Clicking:** Supports three click modes:
  - **Background mode:** Sends click events via Win32 `SendMessage` without moving the cursor — you keep using your PC.
  - **Foreground mode:** `pyautogui.click()` moves the physical cursor (original behaviour).
  - **🆕 Window mode:** Select a specific application window/tab. The macro captures and clicks **only** that window — even when it's behind other windows. You can play games, browse, or work while the macro operates on the selected tab in the background.
- **Customizable Macro Sequence:** Executes a sequence of image searches with individual customizable properties:
  - **Wait Times:** Set delays between clicks. A wait time of `0.0` turns the step into a *blocking search* (the macro will infinitely search until the image appears).
  - **Double Click:** Toggle whether the action requires a single or double-click.
  - **Conditional Skips:** Configure the macro to skip the next step if the current image isn't found.

### Smart Scanning Options
- **Scan Area Selection:** Optimizes performance by restricting the visual search area. You can set the scan area to the "left" or "right" half of the screen, or scan "all" of it (full screen). *(In Window mode, the entire target window is captured regardless of this setting.)*
- **Screen Ratio Support:** Supports different monitor aspect ratios (e.g., 16:9 and 32:9) to correctly map search regions.

### User Interface (GUI)
- **Modern Dark Theme:** A fully custom Tkinter interface utilizing clean typography, rounded buttons, custom toggle switches, smooth scrollbars, and a polished dark color palette.
- **Drag and Drop Support:** Easily import new template images by dragging and dropping image files (`.png`, `.jpg`, `.bmp`) directly into the application.
- **Status & Logging:** Features a real-time log box that provides diagnostic output—such as which images have been clicked, confidence values, and coordinates—giving you complete visibility into the macro's operations.
- **Tabbed Management:**
  - **Run Macro:** The main control panel to start the macro, configure run timers (auto-stop), select scan area / screen ratio / click mode / target window, and view logs.
  - **Macro Sequence:** Allows users to view and manage the active sequence of steps. Reorder items, set wait times, toggle double-clicks, and edit skip conditions all inline without restarting the application.
  - **Manage Images:** A dedicated tab for handling the template images. Features quick-action row buttons to easily **Rename**, **Replace**, or **Delete** images using a modern icon-driven UI, plus dynamic prompts for auto-naming new additions.

### Fail-Safes and Hotkeys
- **Instant Kill Switch:** The macro runs in a separate background thread. You can instantly stop the macro execution at any time by pressing the `Q` key on your keyboard.
- **PyAutoGUI Failsafe:** Available in foreground mode. In background/window mode, the failsafe is not needed since the cursor is never moved.

### Click Modes
- **Background:** Clicks are sent as Win32 messages (`WM_LBUTTONDOWN` / `WM_LBUTTONUP`) directly to the window under the screen coordinates. Your physical mouse cursor stays wherever you left it.
- **Foreground:** Restores the original `pyautogui` behaviour — the cursor physically moves to the target and clicks. Use this if background mode doesn't work with a specific application (some apps ignore synthetic messages).
- **🆕 Window:** Select a specific application window/tab from a dropdown list. The macro:
  1. Captures that window's content via `PrintWindow` (works even when the window is behind other windows).
  2. Performs template matching against the captured content.
  3. Sends click messages directly to that window's HWND — no cursor movement, no need for the window to be on top.

  **Use case:** You can play a full-screen game while Visiotask automates a browser tab, Discord, or any other application running behind it.

## Setup & Execution

1. Make sure to install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python visiotask.py
   ```

## How to Use Window Mode

1. Open the target application (e.g., a browser tab, a game launcher).
2. In Visiotask, set **Click mode** to `window`.
3. Select the target window from the **Target win** dropdown.
4. Click ↻ to refresh the list if you don't see your window.
5. Add your template images and start the macro.
6. Visiotask will now capture and click only in that window — you can freely use your PC.