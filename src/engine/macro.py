import time
import keyboard
from src.image.vision import find_and_click
from src.utils.state import state


def run_macro(stop_event, log, screen_ratio, scan_side):
    screen_width, screen_height = _screen_size()
    half_width = screen_width // 2

    if scan_side == "left":
        search_region = (0, 0, half_width, screen_height)
        search_label = "left half"
    elif scan_side == "right":
        search_region = (half_width, 0, screen_width - half_width, screen_height)
        search_label = "right half"
    elif scan_side == "custom" and state.CUSTOM_REGION:
        search_region = tuple(state.CUSTOM_REGION)
        search_label = f"custom region {search_region}"
    else:
        search_region = None
        search_label = "full screen"

    log("[i] --- Macro running (press Q to stop) ---")
    log(f"[i] Screen: {screen_width}x{screen_height} | ratio: {screen_ratio} | scanning: {search_label}")
    log(f"[i] Click mode: {getattr(state, 'CLICK_MODE', 'background')}")
    if getattr(state, 'CLICK_MODE', 'background') == "window" and state.TARGET_HWND:
        from src.engine.background_click import get_window_title, is_window_valid
        win_title = get_window_title(state.TARGET_HWND) or "(unknown)"
        log(f"[i] Target window: {win_title} (HWND {state.TARGET_HWND})")
        if not is_window_valid(state.TARGET_HWND):
            log("[!] Target window handle is invalid. Try selecting the window again.")
            return
        # In window mode we capture the full target window — scan region is irrelevant
        search_region = None
        search_label = f"window: {win_title}"
    elif getattr(state, 'CLICK_MODE', 'background') == "window" and not state.TARGET_HWND:
        # Window mode selected but no target window resolved
        log("[!] Window mode selected but no target window found. Select a window and try again.")
        return

    if not state.MACRO_SEQUENCE:
        log("[!] Macro sequence is empty. Please add images first.")
        return

    try:
        while not stop_event.is_set():
            if keyboard.is_pressed('q'):
                stop_event.set()
                break

            skip_next = False
            block_next = False
            
            for idx, step in enumerate(state.MACRO_SEQUENCE):
                if stop_event.is_set() or keyboard.is_pressed('q'):
                    break
                    
                if skip_next:
                    log(f"[~] Skipping {step['name']} due to previous condition.")
                    skip_next = False
                    block_next = False
                    continue

                img_name = step["name"]
                try:
                    wait_time = float(step.get("wait", 0))
                except ValueError:
                    wait_time = 0

                double_click = step.get("double_click", False)

                if block_next:
                    found = False
                    while not stop_event.is_set():
                        if keyboard.is_pressed('q'):
                            break
                        found = find_and_click(img_name, img_name.upper(), 0.75, search_region, log, double_click)
                        if found:
                            break
                        time.sleep(0.1)
                    
                    if found and wait_time > 0:
                        time.sleep(wait_time)
                else:
                    found = find_and_click(img_name, img_name.upper(), 0.75, search_region, log, double_click)
                    if found:
                        if wait_time > 0:
                            time.sleep(wait_time)
                    else:
                        if step.get("skip_next", False):
                            skip_next = True

                block_next = (wait_time == 0)
                    
            time.sleep(0.1)

    except Exception as e:
        log(f"[!] An error occurred during execution: {e}")
    finally:
        stop_event.set()
        log("[i] --- Macro stopped ---")


def _screen_size():
    """Return screen dimensions — uses Win32 API to avoid any pyautogui import."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        import pyautogui
        return pyautogui.size()