import os
import sys

# Configuration settings
LOCAL_APP_DATA = os.getenv('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
APP_DATA_DIR = os.path.join(LOCAL_APP_DATA, 'Visiotask')
IMAGE_DIR = os.path.join(APP_DATA_DIR, 'images')
CONFIG_FILE = os.path.join(APP_DATA_DIR, "config.json")

os.makedirs(IMAGE_DIR, exist_ok=True)

if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
    RESOURCE_DIR = sys._MEIPASS
else:
    # Relative to src/utils/config.py -> src/utils -> src -> root
    SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    RESOURCE_DIR = SCRIPT_DIR
