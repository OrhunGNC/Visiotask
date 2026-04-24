import os
import cv2
import numpy as np
import mss
from src.utils.config import IMAGE_DIR
from src.utils.state import state
from src.engine.background_click import background_click, foreground_click, window_click, capture_window, is_window_valid


def find_and_click(image_file, name, confidence=0.75, region=None, log=None, double_click=False):
    image_path = os.path.join(IMAGE_DIR, image_file)
    template = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if template is None:
        if log:
            log(f"[!] Could not load {image_file}")
        return False

    click_mode = getattr(state, "CLICK_MODE", "background")
    target_hwnd = getattr(state, "TARGET_HWND", None)

    # ── Window-targeted mode ──────────────────────────────────────
    # Capture the specific window via PrintWindow (works behind others)
    # and send clicks directly to its HWND.  Scan region is ignored
    # because we capture the full client area of the target window.
    if click_mode == "window" and target_hwnd:
        if not is_window_valid(target_hwnd):
            if log:
                log(f"[!] Target window no longer exists (HWND {target_hwnd})")
            return False

        result = capture_window(target_hwnd)
        if result is None:
            if log:
                log(f"[!] Failed to capture target window (HWND {target_hwnd})")
            return False

        screenshot_bgr, win_w, win_h = result
        match = cv2.matchTemplate(screenshot_bgr, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(match)

        if max_val >= confidence:
            th, tw = template.shape[:2]
            # Coordinates are relative to the window's client area
            client_x = max_loc[0] + tw // 2
            client_y = max_loc[1] + th // 2

            success = window_click(target_hwnd, client_x, client_y, double_click=double_click)
            if not success:
                # Fallback: try background click via screen coordinates
                # (requires the window to still be visible on screen)
                bg_success = background_click(client_x, client_y, double_click=double_click)
                if not bg_success:
                    foreground_click(client_x, client_y, double_click=double_click)

            action_name = "clicked (win)" if not double_click else "double-clicked (win)"
            if log:
                log(f"[+] {name} {action_name} ({max_val:.2f} @ client {client_x},{client_y})")
            return True

        return False

    # ── Screen-based modes (background / foreground) ──────────────
    with mss.mss() as sct:
        if region:
            monitor = {"left": region[0], "top": region[1], "width": region[2], "height": region[3]}
        else:
            monitor = sct.monitors[1]
        screenshot = np.array(sct.grab(monitor))
        screenshot_bgr = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

    result = cv2.matchTemplate(screenshot_bgr, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= confidence:
        h, w = template.shape[:2]
        center_x = max_loc[0] + w // 2 + (region[0] if region else 0)
        center_y = max_loc[1] + h // 2 + (region[1] if region else 0)

        if click_mode == "background":
            success = background_click(center_x, center_y, double_click=double_click)
            if not success:
                foreground_click(center_x, center_y, double_click=double_click)
            action_name = "clicked (bg)" if not double_click else "double-clicked (bg)"
        else:
            foreground_click(center_x, center_y, double_click=double_click)
            action_name = "double-clicked" if double_click else "clicked"

        if log:
            log(f"[+] {name} {action_name} ({max_val:.2f} @{center_x},{center_y})")
        return True
    return False