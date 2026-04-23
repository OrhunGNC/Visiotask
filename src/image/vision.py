import os
import time
import cv2
import numpy as np
import mss
import pyautogui
from src.utils.config import IMAGE_DIR

def find_and_click(image_file, name, confidence=0.75, region=None, log=None, double_click=False):
    image_path = os.path.join(IMAGE_DIR, image_file)
    template = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if template is None:
        if log:
            log(f"[!] Could not load {image_file}")
        return False

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
        
        if double_click:
            pyautogui.click(center_x, center_y)
            time.sleep(0.1)
            pyautogui.click(center_x, center_y)
            action_name = "double-clicked"
        else:
            pyautogui.click(center_x, center_y)
            action_name = "clicked"
            
        if log:
            log(f"[+] {name} {action_name} ({max_val:.2f} @{center_x},{center_y})")
        return True
    return False
