# Visiotask

**Note:** The source code for this project was authored using vibecoding techniques, powered by a combination of Claude Opus 4.6, GPT 5.3-Codex, and Gemini 3.1 Pro.

Visiotask is an image-based screen automation and macro execution tool. It uses computer vision to detect specific UI elements and images on your screen and interacts with them by automatically clicking on the matched elements. It provides a sleek, modern, dark-themed GUI to control the macro and configure scanning settings.

## Features & Functions

### Image-Based Macro Execution
- **Template Matching:** Utilizes OpenCV (`cv2.matchTemplate`) and `mss` for high-performance, real-time screen grabbing and image recognition to find visual targets on the screen.
- **Automated Clicking:** Uses `pyautogui` to perform precise mouse clicks on the center of the recognized image targets once they are found with a specified confidence threshold.
- **Customizable Macro Sequence:** Executes a sequence of image searches with individual customizable properties:
  - **Wait Times:** Set delays between clicks. A wait time of `0.0` turns the step into a *blocking search* (the macro will infinitely search until the image appears).
  - **Double Click:** Toggle whether the action requires a single or double-click.
  - **Conditional Skips:** Configure the macro to skip the next step if the current image isn't found.

### Smart Scanning Options
- **Scan Area Selection:** Optimizes performance by restricting the visual search area. You can set the scan area to the "left" or "right" half of the screen, or scan "all" of it (full screen).
- **Screen Ratio Support:** Supports different monitor aspect ratios (e.g., 16:9 and 32:9) to correctly map search regions.

### User Interface (GUI)
- **Modern Dark Theme:** A fully custom Tkinter interface utilizing clean typography, rounded buttons, custom toggle switches, smooth scrollbars, and a polished dark color palette.
- **Drag and Drop Support:** Easily import new template images by dragging and dropping image files (`.png`, `.jpg`, `.bmp`) directly into the application.
- **Status & Logging:** Features a real-time log box that provides diagnostic output—such as which images have been clicked, confidence values, and coordinates—giving you complete visibility into the macro's operations.
- **Tabbed Management:**
  - **Run Macro:** The main control panel to start the macro, configure run timers (auto-stop), select scan area / screen ratio, and view logs.
  - **Macro Sequence:** Allows users to view and manage the active sequence of steps. Reorder items, set wait times, toggle double-clicks, and edit skip conditions all inline without restarting the application.
  - **Manage Images:** A dedicated tab for handling the template images. Features quick-action row buttons to easily **Rename**, **Replace**, or **Delete** images using a modern icon-driven UI, plus dynamic prompts for auto-naming new additions.

### Fail-Safes and Hotkeys
- **Instant Kill Switch:** The macro runs in a separate background thread. You can instantly stop the macro execution at any time by pressing the `Q` key on your keyboard.
- **PyAutoGUI Failsafe:** Built-in failsafe is enabled so you can throw your mouse cursor to the corners of the screen to abort operations if needed.

## Setup & Execution

1. Make sure to install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the application:
   ```bash
   python visiotask.py
   ```
