import time
import keyboard
import pyautogui
from src.image.vision import find_and_click
from src.utils.state import state

# Disable PyAutoGUI's failsafe which crashes the thread when the mouse touches screen corners
pyautogui.FAILSAFE = False

def run_macro(stop_event, log, screen_ratio, scan_side):
    screen_width, screen_height = pyautogui.size()
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

    except pyautogui.FailSafeException:
        log("[!] PyAutoGUI FailSafe triggered (Mouse mapped to corner). Stopping.")
    except Exception as e:
        log(f"[!] An error occurred during execution: {e}")
    finally:
        stop_event.set()
        log("[i] --- Macro stopped ---")
