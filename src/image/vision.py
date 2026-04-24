import os
import cv2
import numpy as np
import mss
from src.utils.config import IMAGE_DIR
from src.utils.state import state
from src.engine.background_click import (
    background_click, foreground_click, window_click,
    capture_window, is_window_valid, _walk_to_root
)


def find_and_click(image_file, name, confidence=0.75, region=None, log=None, double_click=False):
    image_path = os.path.join(IMAGE_DIR, image_file)
    template = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if template is None:
        if log:
            log(f"[!] Could not load {image_file}")
        return False

    th, tw = template.shape[:2]
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

        # Walk to root owner — in case the selected HWND is a sub-control
        actual_hwnd = _walk_to_root(target_hwnd)
        if actual_hwnd != target_hwnd:
            if log:
                log(f"[i] Redirected to root window (HWND {actual_hwnd})")

        result = capture_window(actual_hwnd)
        if result is None:
            if log:
                from src.engine.background_click import get_window_title
                win_title = get_window_title(actual_hwnd) or ""
                log(f"[!] Failed to capture window '{win_title}' (HWND {actual_hwnd}). "
                    f"Make sure it is not minimized.")
            return False

        screenshot_bgr, win_w, win_h = result

        # Guard: template must fit inside the captured window
        if th > screenshot_bgr.shape[0] or tw > screenshot_bgr.shape[1]:
            if log:
                log(f"[!] Template {name} ({tw}x{th}) is larger than window "
                    f"({win_w}x{win_h}). Re-capture the image inside the target window.")
            return False

        match = cv2.matchTemplate(screenshot_bgr, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(match)

        if max_val >= confidence:
            # Coordinates are relative to the window's client area
            client_x = max_loc[0] + tw // 2
            client_y = max_loc[1] + th // 2

            success = window_click(actual_hwnd, client_x, client_y, double_click=double_click)
            if not success:
                # Fallback: try background click via screen coordinates
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

    # Guard: template must fit inside the screenshot/region
    if th > screenshot_bgr.shape[0] or tw > screenshot_bgr.shape[1]:
        if log:
            log(f"[!] Template {name} ({tw}x{th}) is larger than the search area "
                f"({screenshot_bgr.shape[1]}x{screenshot_bgr.shape[0]}). "
                f"Re-capture the image or use a smaller template.")
        return False

    result = cv2.matchTemplate(screenshot_bgr, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= confidence:
        center_x = max_loc[0] + tw // 2 + (region[0] if region else 0)
        center_y = max_loc[1] + th // 2 + (region[1] if region else 0)

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