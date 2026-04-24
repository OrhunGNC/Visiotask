import json
import os
from src.utils.config import CONFIG_FILE

class AppState:
    def __init__(self):
        self.IMAGE_FILES = []
        self.MACRO_SEQUENCE = []
        self.SCREEN_RATIO = "16:9"
        self.SCREEN_WIDTH = 1920
        self.SCREEN_HEIGHT = 1080
        self.SCAN_AREA = "all"
        self.CUSTOM_REGION = None
        self.CLICK_MODE = "background"  # "background" or "foreground"
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.IMAGE_FILES = data.get("IMAGE_FILES", [])
                    self.MACRO_SEQUENCE = data.get("MACRO_SEQUENCE", [])
                    self.SCREEN_RATIO = data.get("SCREEN_RATIO", "16:9")
                    self.SCREEN_WIDTH = data.get("SCREEN_WIDTH", 1920)
                    self.SCREEN_HEIGHT = data.get("SCREEN_HEIGHT", 1080)
                    self.SCAN_AREA = data.get("SCAN_AREA", "all")
                    self.CUSTOM_REGION = data.get("CUSTOM_REGION", None)
                    self.CLICK_MODE = data.get("CLICK_MODE", "background")
            except Exception:
                pass

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({
                    "IMAGE_FILES": self.IMAGE_FILES,
                    "MACRO_SEQUENCE": self.MACRO_SEQUENCE,
                    "SCREEN_RATIO": self.SCREEN_RATIO,
                    "SCREEN_WIDTH": self.SCREEN_WIDTH,
                    "SCREEN_HEIGHT": self.SCREEN_HEIGHT,
                    "SCAN_AREA": self.SCAN_AREA,
                    "CUSTOM_REGION": self.CUSTOM_REGION,
                    "CLICK_MODE": self.CLICK_MODE
                }, f, indent=4)
        except Exception:
            pass

state = AppState()