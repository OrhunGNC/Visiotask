import sys
import os
import threading
import time
import shutil
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
from PIL import Image, ImageTk
import windnd

import cv2
import numpy as np
import mss
import pyautogui
import keyboard

# --- Configuration ---
pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = True

if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(sys.executable)
    RESOURCE_DIR = sys._MEIPASS
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))

# Setup image directory in AppData\Local
local_app_data = os.getenv('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local'))
APP_DATA_DIR = os.path.join(local_app_data, 'Visiotask')
IMAGE_DIR = os.path.join(APP_DATA_DIR, 'images')
os.makedirs(IMAGE_DIR, exist_ok=True)

import json
CONFIG_FILE = os.path.join(APP_DATA_DIR, "config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return data.get("IMAGE_FILES", []), data.get("MACRO_SEQUENCE", [])
        except Exception:
            pass
    return [], []

def save_config():
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump({"IMAGE_FILES": IMAGE_FILES, "MACRO_SEQUENCE": MACRO_SEQUENCE}, f, indent=4)
    except Exception:
        pass

IMAGE_FILES, MACRO_SEQUENCE = load_config()


# --- Macro Logic ---
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

def run_macro(stop_event, log, screen_ratio, scan_side):
    screen_width, screen_height = pyautogui.size()
    half_width = screen_width // 2

    if scan_side == "left":
        search_region = (0, 0, half_width, screen_height)
        search_label = "left half"
    elif scan_side == "right":
        search_region = (half_width, 0, screen_width - half_width, screen_height)
        search_label = "right half"
    else:
        search_region = None
        search_label = "full screen"

    log("[i] --- Macro running (press Q to stop) ---")
    log(f"[i] Screen: {screen_width}x{screen_height} | ratio: {screen_ratio} | scanning: {search_label}")

    if not MACRO_SEQUENCE:
        log("[!] Macro sequence is empty. Please add images first.")
        return

    while not stop_event.is_set():
        if keyboard.is_pressed('q'):
            stop_event.set()
            break

        skip_next = False
        block_next = False
        
        for idx, step in enumerate(MACRO_SEQUENCE):
            if stop_event.is_set() or keyboard.is_pressed('q'):
                break
                
            if skip_next:
                log(f"[~] Skipping {step['name']} due to previous condition.")
                skip_next = False
                # If we skipped an item, we should cancel the block or carry it over? 
                # Preserving it is usually safer, but let's reset it to be consistent with normal flow.
                block_next = False
                continue

            img_name = step["name"]
            try:
                wait_time = float(step.get("wait", 0))
            except ValueError:
                wait_time = 0

            double_click = step.get("double_click", False)

            if block_next:
                # Blocking step: keep searching until found
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
                # Normal behavior
                found = find_and_click(img_name, img_name.upper(), 0.75, search_region, log, double_click)
                if found:
                    if wait_time > 0:
                        time.sleep(wait_time)
                else:
                    if step.get("skip_next", False):
                        skip_next = True

            block_next = (wait_time == 0)
                    
        time.sleep(0.1)

    log("[i] --- Macro stopped ---")


# --- Custom UI Components ---
class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, bg_color, fg_color, hover_color, command, radius=8, font=("Segoe UI", 12, "bold"), width=160, height=44, outline_color=None, **kwargs):
        super().__init__(parent, bg=parent["bg"], highlightthickness=0, width=width, height=height, **kwargs)
        self.command = command
        self.radius = radius
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.hover_color = hover_color
        self.outline_color = outline_color or bg_color
        self.text = text
        self.font = font
        self.req_width = width
        self.req_height = height
        self.disabled = False
        
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Configure>", self._draw)
        
    def set_state(self, state):
        self.disabled = (state == tk.DISABLED)
        self.config(cursor="" if self.disabled else "hand2")
        self._draw()
        
    def _draw(self, event=None):
        self.delete("all")
        w = max(self.winfo_width(), self.req_width)
        h = max(self.winfo_height(), self.req_height)
        if w < 10 or h < 10: return
        
        color = "#2A2F3A" if self.disabled and not self.outline_color else self.bg_color
        out_col = "#2A2F3A" if self.disabled else self.outline_color
        
        self.create_polygon(self._get_points(w, h, self.radius), fill=color, outline=out_col, smooth=True)
        fg = "#9CA3AF" if self.disabled else self.fg_color
        self.create_text(w/2, h/2, text=self.text, fill=fg, font=self.font)

    def _get_points(self, w, h, r):
        w, h = w-1, h-1
        return [r, 0, w-r, 0, w, 0, w, r, w, h-r, w, h, w-r, h, r, h, 0, h, 0, h-r, 0, r, 0, 0, r, 0]

    def _on_enter(self, event):
        if not self.disabled:
            self._draw_state(self.hover_color)

    def _on_leave(self, event):
        if not self.disabled:
            self._draw_state(self.bg_color)

    def _on_press(self, event):
        if not self.disabled:
            self._draw_state(self.hover_color)

    def _on_release(self, event):
        if not self.disabled:
            self._draw_state(self.bg_color)
            if self.command:
                self.command()

    def _draw_state(self, color):
        self.delete("all")
        w = max(self.winfo_width(), self.req_width)
        h = max(self.winfo_height(), self.req_height)
        out_col = self.hover_color if color == self.hover_color and self.outline_color != self.bg_color else self.outline_color
        self.create_polygon(self._get_points(w, h, self.radius), fill=color, outline=out_col, smooth=True)
        self.create_text(w/2, h/2, text=self.text, fill=self.fg_color, font=self.font)

class ToggleSwitch(tk.Canvas):
    def __init__(self, parent, variable, width=50, height=26, **kwargs):
        super().__init__(parent, bg=parent["bg"], highlightthickness=0, width=width, height=height, cursor="hand2", **kwargs)
        self.variable = variable
        self.w = width
        self.h = height
        self.active_bg = "#FF7A18"       # Bright orange indicator
        self.active_hover = "#FFA559"
        self.inactive_bg = "#4B5563"     # More distinct dark gray off state
        self.inactive_hover = "#6B7280"
        self.thumb_color = "#FFFFFF"
        self._is_hovered = False
        
        self.bind("<Button-1>", self._toggle)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.variable.trace_add("write", self._update_draw)
        self._draw()
        
    def _toggle(self, event):
        self.variable.set(not self.variable.get())
        
    def _on_enter(self, event):
        self._is_hovered = True
        self._draw()
        
    def _on_leave(self, event):
        self._is_hovered = False
        self._draw()
        
    def _update_draw(self, *args):
        self._draw()

    def _draw(self):
        self.delete("all")
        state = self.variable.get()
        if state:
            bg = self.active_hover if self._is_hovered else self.active_bg
        else:
            bg = self.inactive_hover if self._is_hovered else self.inactive_bg
            
        r = self.h / 2
        w, h = self.w, self.h
        
        # Draw standard rounded box using precise coordinates
        self.create_arc(0, 0, self.h, self.h, start=90, extent=180, fill=bg, outline=bg)
        self.create_arc(self.w - self.h, 0, self.w, self.h, start=270, extent=180, fill=bg, outline=bg)
        self.create_rectangle(self.h/2, 0, self.w - self.h/2, self.h, fill=bg, outline=bg)
        
        thumb_r = r - 3
        cx = self.w - r if state else r
        
        # Slight shadow/outline for thumb to pop it out
        self.create_oval(cx-thumb_r, r-thumb_r+1, cx+thumb_r, r+thumb_r+1, fill="#1E2530", outline="")
        # Main thumb
        self.create_oval(cx-thumb_r, r-thumb_r, cx+thumb_r, r+thumb_r, fill=self.thumb_color, outline=self.thumb_color)

class SmoothScrollbar(tk.Canvas):
    def __init__(self, parent, target_canvas, width=8, **kwargs):
        super().__init__(parent, bg="#0F172A", highlightthickness=0, width=width, **kwargs)
        self.target = target_canvas
        self.thumb_color = "#2A3441"
        self.hover_color = "#3B4756"
        self.thumb_id = self.create_rectangle(0, 0, width, 0, fill=self.thumb_color, outline="")
        self.first = 0.0
        self.last = 1.0
        self._drag_y = 0
        self._drag_start_first = 0.0
        self._hovered = False

        self.bind("<ButtonPress-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Configure>", lambda e: self._redraw())
        
        self.target.configure(yscrollcommand=self.set)

    def set(self, first, last):
        self.first = float(first)
        self.last = float(last)
        if self.last - self.first >= 1.0:
            self.itemconfig(self.thumb_id, state="hidden")
        else:
            self.itemconfig(self.thumb_id, state="normal")
            self._redraw()

    def _redraw(self):
        h = self.winfo_height()
        w = self.winfo_width()
        self.coords(self.thumb_id, 0, h * self.first, w, h * self.last)

    def _on_enter(self, e):
        self._hovered = True
        self.itemconfig(self.thumb_id, fill=self.hover_color)

    def _on_leave(self, e):
        self._hovered = False
        self.itemconfig(self.thumb_id, fill=self.thumb_color)

    def _on_click(self, e):
        h = self.winfo_height()
        if h == 0: return
        fraction = e.y / h
        if fraction < self.first or fraction > self.last:
            self.target.yview_moveto(fraction - (self.last - self.first) / 2)
        self._drag_y = e.y
        self._drag_start_first = float(self.first)

    def _on_drag(self, e):
        h = self.winfo_height()
        if h == 0: return
        dy = e.y - self._drag_y
        self.target.yview_moveto(self._drag_start_first + (dy / h))

class CustomInputDialog(tk.Toplevel):
    def __init__(self, parent, title_text, label_text, ok_text="Add Image", default_value=""):
        super().__init__(parent)
        self.result = None
        self.overrideredirect(True)
        self.configure(bg="#2A2F3A") # Thin border color
        
        # INCREASED SIZE to fit everything cleanly
        w, h = 460, 280
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        # Ensure it stays on top and actually grabs focus
        self.transient(parent)
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()
        
        main_frame = tk.Frame(self, bg="#1A1D26")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1) # 1px simulated border
        
        # Drag handling logic
        self._drag_data = {"x": 0, "y": 0}
        def _on_drag_start(event):
            self._drag_data["x"] = event.x
            self._drag_data["y"] = event.y

        def _on_drag_motion(event):
            dx = event.x - self._drag_data["x"]
            dy = event.y - self._drag_data["y"]
            self.geometry(f"+{self.winfo_x() + dx}+{self.winfo_y() + dy}")

        main_frame.bind("<ButtonPress-1>", _on_drag_start)
        main_frame.bind("<B1-Motion>", _on_drag_motion)
        
        lbl_title = tk.Label(main_frame, text=title_text, font=("Segoe UI", 18, "bold"), bg="#1A1D26", fg="#E5E7EB")
        lbl_title.pack(anchor="w", padx=30, pady=(24, 16))
        lbl_title.bind("<ButtonPress-1>", _on_drag_start)
        lbl_title.bind("<B1-Motion>", _on_drag_motion)
        
        tk.Label(main_frame, text=label_text, font=("Segoe UI", 12), bg="#1A1D26", fg="#E5E7EB").pack(anchor="w", padx=30)
        
        input_frame = tk.Frame(main_frame, bg="#0F1117", highlightthickness=1, highlightbackground="#2A2F3A")
        input_frame.pack(fill=tk.X, padx=30, pady=(8, 4))
        
        self.entry_var = tk.StringVar(value=default_value)
        self.entry = tk.Entry(input_frame, textvariable=self.entry_var, font=("Segoe UI", 12), bg="#0F1117", fg="#E5E7EB", insertbackground="#E5E7EB", bd=0)
        self.entry.pack(fill=tk.X, padx=12, pady=10)
        self.entry.bind("<Return>", lambda e: self._on_submit())
        
        # Ensure entry gets the focus and selects text
        def _focus_and_select():
            self.entry.focus_force()
            if default_value:
                idx = default_value.rfind('.')
                if idx > 0:
                    self.entry.select_range(0, idx)
                else:
                    self.entry.select_range(0, tk.END)
        self.after(100, _focus_and_select)
        
        tk.Label(main_frame, text="e.g. icon.png", font=("Segoe UI", 10), bg="#1A1D26", fg="#9CA3AF").pack(anchor="w", padx=30)
        
        btn_frame = tk.Frame(main_frame, bg="#1A1D26")
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=30, pady=(10, 24))
        
        self.btn_submit = RoundedButton(btn_frame, ok_text, bg_color="#FF7A18", fg_color="#FFFFFF", hover_color="#FF8C36", command=self._on_submit, width=120, height=44, font=("Segoe UI", 11, "bold"))
        self.btn_submit.pack(side=tk.RIGHT)
        
        self.btn_cancel = RoundedButton(btn_frame, "Cancel", bg_color="#1A1D26", fg_color="#E5E7EB", hover_color="#2A2F3A", outline_color="#2A2F3A", command=self._on_cancel, width=100, height=44, font=("Segoe UI", 11))
        self.btn_cancel.pack(side=tk.RIGHT, padx=(0, 16))

        self.grab_set()
        self.wait_window(self)

    def _on_submit(self):
        self.result = self.entry_var.get().strip()
        self.destroy()

    def _on_cancel(self):
        self.destroy()

def _bind_mousewheel(canvas, widget):
    widget.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
    for child in widget.winfo_children():
        _bind_mousewheel(canvas, child)

# --- GUI ---
class MacroApp:
    BG = "#0F1117"
    CARD = "#1A1D26"
    BORDER = "#2A2F3A"
    PRIMARY = "#FF7A18"
    PRIMARY_HOVER = "#FF8C36"
    SUCCESS = "#22C55E"
    WARNING = "#FACC15"
    ERROR = "#EF4444"
    TEXT = "#E5E7EB"
    TEXT_SEC = "#9CA3AF"

    def __init__(self, root):
        self.root = root
        self.root.title("Visiotask")
        self.root.configure(bg=self.BG)
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        icon_path = os.path.join(RESOURCE_DIR, "icon.ico")
        if os.path.exists(icon_path):
            try: self.root.iconbitmap(icon_path)
            except Exception: pass
        
        try:
            import ctypes
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(2)), 4)
            # Allow drag & drop bypassing UIPI if running in elevated mode
            ctypes.windll.user32.ChangeWindowMessageFilterEx(hwnd, 0x0233, 1, None) # WM_DROPFILES
            ctypes.windll.user32.ChangeWindowMessageFilterEx(hwnd, 0x0049, 1, None) # WM_COPYGLOBALDATA
        except Exception:
            pass

        # Hook drag and drop
        try:
            windnd.hook_dropfiles(self.root, func=self._on_drop)
        except Exception as e:
            print("Drag and Drop hook failed:", e)

        self.stop_event = threading.Event()
        self.macro_thread = None
        self.timer_val = 0
        self.remaining_time = 0
        self.screen_ratio_var = tk.StringVar(value="32:9")
        self.scan_area_var = tk.StringVar(value="left")
        
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TCombobox", fieldbackground=self.BG, background=self.CARD, foreground=self.TEXT, bordercolor=self.BORDER, arrowcolor=self.TEXT_SEC, padding=6)
        self.style.map("TCombobox", fieldbackground=[("readonly", self.BG)])
        
        self.current_view = "Run Macro"
        self.sidebar_buttons = {}
        self.views = {}

        self._build_ui()
        self._check_images()
        self.root.bind("<Alt-F4>", lambda _event: self._close_window())

    def _build_ui(self):
        # Sidebar
        self.sidebar = tk.Frame(self.root, bg=self.CARD, width=240)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        
        brand_frame = tk.Frame(self.sidebar, bg=self.CARD)
        brand_frame.pack(pady=(30, 40), padx=20, anchor="w", fill=tk.X)
        
        icon_path = os.path.join(RESOURCE_DIR, "icon.ico")
        if os.path.exists(icon_path):
            try:
                pil_icon = Image.open(icon_path).resize((28, 28))
                self._sidebar_icon = ImageTk.PhotoImage(pil_icon)
                tk.Label(brand_frame, image=self._sidebar_icon, bg=self.CARD).pack(side=tk.LEFT, padx=(0, 10))
            except Exception: pass
            
        tk.Label(brand_frame, text="Visiotask", font=("Segoe UI", 20, "bold"), bg=self.CARD, fg=self.PRIMARY).pack(side=tk.LEFT)
        
        # Main View
        self.main_content = tk.Frame(self.root, bg=self.BG)
        self.main_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        for name in ["Run Macro", "Macro Sequence", "Manage Images"]:
            self._create_sidebar_btn(name)

        self._build_run_macro_view()
        self._build_sequence_view()
        self._build_images_view()
        
        self._show_view("Run Macro")

    def _create_sidebar_btn(self, name):
        btn = tk.Frame(self.sidebar, bg=self.CARD, cursor="hand2")
        btn.pack(fill=tk.X, pady=2)
        
        indicator = tk.Frame(btn, bg=self.CARD, width=4)
        indicator.pack(side=tk.LEFT, fill=tk.Y)
        
        lbl = tk.Label(btn, text=name, font=("Segoe UI", 12), bg=self.CARD, fg=self.TEXT_SEC, cursor="hand2")
        lbl.pack(side=tk.LEFT, padx=16, pady=12)
        
        def on_enter(e):
            if self.current_view != name:
                btn.configure(bg=self.BORDER)
                lbl.configure(bg=self.BORDER, fg=self.TEXT)
                indicator.configure(bg=self.BORDER)
                
        def on_leave(e):
            if self.current_view != name:
                btn.configure(bg=self.CARD)
                lbl.configure(bg=self.CARD, fg=self.TEXT_SEC)
                indicator.configure(bg=self.CARD)
                
        def on_click(e): self._show_view(name)
            
        for w in (btn, indicator, lbl):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)
            
        self.sidebar_buttons[name] = {"frame": btn, "label": lbl, "indicator": indicator}

    def _show_view(self, name):
        self.current_view = name
        for v in self.views.values(): v.pack_forget()
        
        for b_name, b_dict in self.sidebar_buttons.items():
            if b_name == name:
                b_dict["frame"].configure(bg=self.BORDER)
                b_dict["label"].configure(bg=self.BORDER, fg=self.TEXT, font=("Segoe UI", 12, "bold"))
                b_dict["indicator"].configure(bg=self.PRIMARY)
            else:
                b_dict["frame"].configure(bg=self.CARD)
                b_dict["label"].configure(bg=self.CARD, fg=self.TEXT_SEC, font=("Segoe UI", 12))
                b_dict["indicator"].configure(bg=self.CARD)
                
        if name in self.views:
            self.views[name].pack(fill=tk.BOTH, expand=True, padx=32, pady=32)
            if name == "Macro Sequence": self._refresh_sequence_list()
            elif name == "Manage Images": self._refresh_image_list()

    def _build_run_macro_view(self):
        view = tk.Frame(self.main_content, bg=self.BG)
        self.views["Run Macro"] = view
        
        tk.Label(view, text="Run Macro", font=("Segoe UI", 24, "bold"), bg=self.BG, fg=self.TEXT).pack(anchor="w")
        tk.Label(view, text="Configure settings and monitor execution.", font=("Segoe UI", 12), bg=self.BG, fg=self.TEXT_SEC).pack(anchor="w", pady=(0, 24))
        
        top_panels = tk.Frame(view, bg=self.BG)
        top_panels.pack(fill=tk.X, pady=(0, 24))
        top_panels.columnconfigure(0, weight=1, minsize=300)
        top_panels.columnconfigure(1, weight=1)
        
        # Configuration Card
        config_card = tk.Frame(top_panels, bg=self.CARD, bd=0)
        config_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        
        tk.Label(config_card, text="Configuration", font=("Segoe UI", 14, "bold"), bg=self.CARD, fg=self.TEXT).pack(anchor="w", padx=20, pady=(20, 10))
        
        grid = tk.Frame(config_card, bg=self.CARD)
        grid.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        ttk.Combobox(grid, textvariable=self.screen_ratio_var, values=("16:9", "32:9"), state="readonly", width=12, font=("Segoe UI", 10)).grid(row=0, column=1, sticky="w", padx=16, pady=8)
        tk.Label(grid, text="Screen ratio", font=("Segoe UI", 11), bg=self.CARD, fg=self.TEXT_SEC).grid(row=0, column=0, sticky="w")
        
        ttk.Combobox(grid, textvariable=self.scan_area_var, values=("left", "right", "all"), state="readonly", width=12, font=("Segoe UI", 10)).grid(row=1, column=1, sticky="w", padx=16, pady=8)
        tk.Label(grid, text="Scan area", font=("Segoe UI", 11), bg=self.CARD, fg=self.TEXT_SEC).grid(row=1, column=0, sticky="w")
        
        self.timer_var = tk.StringVar(value="")
        timer_frame = tk.Frame(grid, bg=self.BG, highlightthickness=1, highlightbackground=self.BORDER)
        self.timer_entry = tk.Entry(timer_frame, textvariable=self.timer_var, width=5, font=("Segoe UI", 11), bg=self.BG, fg=self.TEXT, insertbackground=self.TEXT, bd=0)
        self.timer_entry.pack(side=tk.LEFT, padx=6, pady=4)
        tk.Label(timer_frame, text="minutes", font=("Segoe UI", 11), bg=self.BG, fg=self.TEXT_SEC).pack(side=tk.LEFT, padx=(0, 6))
        timer_frame.grid(row=2, column=1, sticky="w", padx=16, pady=8)
        tk.Label(grid, text="Stop after", font=("Segoe UI", 11), bg=self.CARD, fg=self.TEXT_SEC).grid(row=2, column=0, sticky="w")
        
        # Status Card
        status_card = tk.Frame(top_panels, bg=self.CARD, bd=0)
        status_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        
        status_inner = tk.Frame(status_card, bg=self.CARD)
        status_inner.place(relx=0.5, rely=0.45, anchor="center")
        
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(status_inner, textvariable=self.status_var, font=("Segoe UI", 16, "bold"), bg=self.CARD, fg=self.TEXT_SEC)
        self.status_label.pack()
        
        self.timer_display_var = tk.StringVar(value="")
        self.timer_display_label = tk.Label(status_inner, textvariable=self.timer_display_var, font=("Consolas", 32, "bold"), bg=self.CARD, fg=self.PRIMARY)
        self.timer_display_label.pack(pady=(4,0))
        
        btn_frame = tk.Frame(status_card, bg=self.CARD)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=20)
        
        btn_inner = tk.Frame(btn_frame, bg=self.CARD)
        btn_inner.pack(anchor="center")
        
        self.start_btn = RoundedButton(btn_inner, text="Start Macro", bg_color=self.PRIMARY, fg_color="#FFF", hover_color=self.PRIMARY_HOVER, command=self._start, width=150, height=44)
        self.start_btn.pack(side=tk.LEFT, padx=8)
        
        self.stop_btn = RoundedButton(btn_inner, text="Stop", bg_color=self.CARD, fg_color=self.TEXT, hover_color=self.BORDER, outline_color=self.BORDER, command=self._stop, width=100, height=44)
        self.stop_btn.pack(side=tk.LEFT, padx=8)
        self.stop_btn.set_state(tk.DISABLED)

        # Footer Hint
        self.hint_frame = tk.Frame(view, bg=self.BG)
        self.hint_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))
        
        hint_inner = tk.Frame(self.hint_frame, bg=self.BG)
        hint_inner.pack(anchor="center")
        
        self.hint_icon = tk.Label(hint_inner, text="⌨", font=("Segoe UI", 12), bg=self.BG, fg="#9aa4b2")
        self.hint_icon.pack(side=tk.LEFT, padx=(4, 6))
        
        self.hint_text1 = tk.Label(hint_inner, text="Press", font=("Segoe UI", 10), bg=self.BG, fg="#9aa4b2")
        self.hint_text1.pack(side=tk.LEFT)
        
        # Q Key Badge
        self.hint_badge = tk.Frame(hint_inner, bg="#1f2430", highlightbackground="#2a2f3a", highlightthickness=1)
        self.hint_badge.pack(side=tk.LEFT, padx=6)
        self.hint_badge_lbl = tk.Label(self.hint_badge, text="Q", font=("Segoe UI", 8, "bold"), bg="#1f2430", fg="#E5E7EB", pady=1, padx=4)
        self.hint_badge_lbl.pack()
        
        self.hint_text2 = tk.Label(hint_inner, text="to stop the macro anytime", font=("Segoe UI", 10), bg=self.BG, fg="#9aa4b2")
        self.hint_text2.pack(side=tk.LEFT)

        # Log Panel
        log_card = tk.Frame(view, bg=self.CARD, bd=0)
        log_card.pack(fill=tk.BOTH, expand=True)

        log_header = tk.Frame(log_card, bg=self.CARD)
        log_header.pack(fill=tk.X, padx=20, pady=(16, 8))
        tk.Label(log_header, text="Execution Log", font=("Segoe UI", 14, "bold"), bg=self.CARD, fg=self.TEXT).pack(side=tk.LEFT)
        tk.Button(log_header, text="Clear", font=("Segoe UI", 10), fg=self.TEXT_SEC, bg=self.CARD, bd=0, activebackground=self.CARD, cursor="hand2", command=self._clear_log).pack(side=tk.RIGHT)

        log_frame = tk.Frame(log_card, bg=self.BG)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        self.log_text = tk.Text(log_frame, font=("Segoe UI", 11), bg=self.BG, fg=self.TEXT, insertbackground=self.TEXT, bd=0, highlightthickness=0, state=tk.DISABLED, wrap=tk.WORD, padx=12, pady=12)
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview, bg=self.BG, troughcolor=self.CARD, bd=0)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.log_text.tag_config("success", foreground=self.SUCCESS)
        self.log_text.tag_config("error", foreground=self.ERROR)
        self.log_text.tag_config("warning", foreground=self.WARNING)
        self.log_text.tag_config("info", foreground=self.TEXT_SEC)

    def _build_sequence_view(self):
        view = tk.Frame(self.main_content, bg=self.BG)
        self.views["Macro Sequence"] = view
        
        header_frame = tk.Frame(view, bg=self.BG)
        header_frame.pack(fill=tk.X, pady=(0, 24))
        tk.Label(header_frame, text="Macro Sequence", font=("Segoe UI", 24, "bold"), bg=self.BG, fg=self.TEXT).pack(anchor="w")
        tk.Label(header_frame, text="Arrange image checks, wait times, and conditions.", font=("Segoe UI", 12), bg=self.BG, fg=self.TEXT_SEC).pack(anchor="w")
        tk.Label(header_frame, text="* Setting Wait to 0.0 forces the macro to search infinitely until the next image is found.", font=("Segoe UI", 10, "italic"), bg=self.BG, fg="#8E96A4").pack(anchor="w", pady=(4, 0))
        tk.Label(header_frame, text="* Skip Next forces the macro to skip the next image if the selected one is not found.", font=("Segoe UI", 10, "italic"), bg=self.BG, fg="#8E96A4").pack(anchor="w", pady=(2, 0))

        # Fixed Column Headers
        list_header_row = tk.Frame(view, bg=self.BG, pady=4, padx=16)
        list_header_row.pack(fill=tk.X, padx=(0, 8))
        
        tk.Label(list_header_row, text="", bg=self.BG, width=3).pack(side=tk.LEFT)
        tk.Label(list_header_row, text="Image", font=("Segoe UI", 10, "bold"), bg=self.BG, fg=self.TEXT_SEC, width=15, anchor="w").pack(side=tk.LEFT, padx=(50, 10))
        
        headers_right = tk.Frame(list_header_row, bg=self.BG)
        headers_right.pack(side=tk.RIGHT)
        
        hd_trash = tk.Frame(headers_right, bg=self.BG, width=40, height=20)
        hd_trash.pack_propagate(False)
        hd_trash.pack(side=tk.RIGHT)

        hd_skip = tk.Frame(headers_right, bg=self.BG, width=80, height=20)
        hd_skip.pack_propagate(False)
        hd_skip.pack(side=tk.RIGHT, padx=10)
        tk.Label(hd_skip, text="Skip Next", font=("Segoe UI", 10, "bold"), bg=self.BG, fg=self.TEXT_SEC).pack(expand=True)

        hd_dc = tk.Frame(headers_right, bg=self.BG, width=70, height=20)
        hd_dc.pack_propagate(False)
        hd_dc.pack(side=tk.RIGHT, padx=10)
        tk.Label(hd_dc, text="Double", font=("Segoe UI", 10, "bold"), bg=self.BG, fg=self.TEXT_SEC).pack(expand=True)

        hd_wait = tk.Frame(headers_right, bg=self.BG, width=80, height=20)
        hd_wait.pack_propagate(False)
        hd_wait.pack(side=tk.RIGHT, padx=(10, 14))
        tk.Label(hd_wait, text="Wait (s)", font=("Segoe UI", 10, "bold"), bg=self.BG, fg=self.TEXT_SEC).pack(expand=True)

        # Subtle separator
        tk.Frame(view, bg="#1E2530", height=1).pack(fill=tk.X, pady=0)

        list_container = tk.Frame(view, bg=self.BG)
        list_container.pack(fill=tk.BOTH, expand=True)

        self.seq_canvas = tk.Canvas(list_container, bg=self.BG, highlightthickness=0, bd=0)
        scrollbar = SmoothScrollbar(list_container, target_canvas=self.seq_canvas)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.seq_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.seq_scroll_frame = tk.Frame(self.seq_canvas, bg=self.BG, bd=0)

        def _update_seq_scrollregion(e=None):
            w = self.seq_scroll_frame.winfo_width()
            h = self.seq_scroll_frame.winfo_height()
            ch = self.seq_canvas.winfo_height()
            self.seq_canvas.configure(scrollregion=(0, 0, w, max(h, ch)))

        self.seq_scroll_frame.bind("<Configure>", _update_seq_scrollregion)
        self.seq_canvas.bind("<Configure>", lambda e: [self.seq_canvas.itemconfig(self.seq_canvas_window, width=e.width), _update_seq_scrollregion()])
        self.seq_canvas_window = self.seq_canvas.create_window((0, 0), window=self.seq_scroll_frame, anchor="nw")

    def _refresh_sequence_list(self):
        for widget in self.seq_scroll_frame.winfo_children(): widget.destroy()

        if not hasattr(self, '_seq_images'): self._seq_images = []
        self._seq_images.clear()
        self.seq_skip_vars = []
        self.seq_dc_vars = []

        if not MACRO_SEQUENCE:
            tk.Label(self.seq_scroll_frame, text="No sequence steps.", font=("Segoe UI", 12), bg=self.BG, fg=self.TEXT_SEC).pack(pady=40)
            return

        for i, step in enumerate(MACRO_SEQUENCE):
            card = tk.Frame(self.seq_scroll_frame, bg=self.CARD, pady=8, padx=16)
            if i > 0:
                card.pack(fill=tk.X, pady=(6, 0))
            else:
                card.pack(fill=tk.X, pady=0)
            
            # Hover effect
            def on_enter(e, c=card): c.configure(bg="#212631")
            def on_leave(e, c=card): c.configure(bg=self.CARD)
            card.bind("<Enter>", on_enter)
            card.bind("<Leave>", on_leave)
            
            reorder_frame = tk.Frame(card, bg=self.CARD)
            reorder_frame.pack(side=tk.LEFT)
            reorder_frame.bind("<Enter>", on_enter)
            reorder_frame.bind("<Leave>", on_leave)
            tk.Button(reorder_frame, text="▲", font=("Segoe UI", 8), bg=self.CARD, fg=self.TEXT_SEC, bd=0, cursor="hand2", command=lambda idx=i: self._move_seq(idx, -1), state=tk.NORMAL if i > 0 else tk.DISABLED).pack()
            tk.Button(reorder_frame, text="▼", font=("Segoe UI", 8), bg=self.CARD, fg=self.TEXT_SEC, bd=0, cursor="hand2", command=lambda idx=i: self._move_seq(idx, 1), state=tk.NORMAL if i < len(MACRO_SEQUENCE)-1 else tk.DISABLED).pack()

            img_path = os.path.join(IMAGE_DIR, step["name"])
            lbl_preview = tk.Label(card, bg=self.BORDER, width=32, height=32)
            if os.path.isfile(img_path):
                try:
                    pil_img = Image.open(img_path)
                    pil_img.thumbnail((32, 32))
                    tk_img = ImageTk.PhotoImage(pil_img)
                    self._seq_images.append(tk_img)
                    lbl_preview.config(image=tk_img, width=0, height=0)
                except Exception: lbl_preview.config(text="Err", fg=self.ERROR)
            lbl_preview.pack(side=tk.LEFT, padx=(12, 12))
            lbl_preview.bind("<Enter>", on_enter)
            lbl_preview.bind("<Leave>", on_leave)

            name_lbl = tk.Label(card, text=step["name"], font=("Segoe UI", 11, "bold"), bg=self.CARD, fg=self.TEXT, width=16, anchor="w")
            name_lbl.pack(side=tk.LEFT)
            name_lbl.bind("<Enter>", on_enter)
            name_lbl.bind("<Leave>", on_leave)

            actions = tk.Frame(card, bg=self.CARD)
            actions.pack(side=tk.RIGHT, fill=tk.Y)
            actions.bind("<Enter>", on_enter)
            actions.bind("<Leave>", on_leave)

            # Controls aligned exactly under headers
            
            # 1. Delete button (far right)
            btn_frame = tk.Frame(actions, bg=self.CARD, width=40)
            btn_frame.pack_propagate(False)
            btn_frame.pack(side=tk.RIGHT, fill=tk.Y)
            btn_frame.bind("<Enter>", on_enter)
            btn_frame.bind("<Leave>", on_leave)
            
            del_btn = tk.Button(btn_frame, text="🗑", font=("Segoe UI Symbol", 12), bg=self.CARD, fg=self.ERROR, bd=0, cursor="hand2", command=lambda n=step["name"]: self._delete_image(n))
            del_btn.pack(expand=True)
            del_btn.bind("<Enter>", lambda e, btn=del_btn, c=card: [c.configure(bg="#212631"), btn.configure(bg="#212631")])
            del_btn.bind("<Leave>", lambda e, btn=del_btn, c=card: [c.configure(bg=self.CARD), btn.configure(bg=self.CARD)])

            # 2. Skip Toggle
            skip_frame = tk.Frame(actions, bg=self.CARD, width=80)
            skip_frame.pack_propagate(False)
            skip_frame.pack(side=tk.RIGHT, padx=10, fill=tk.Y)
            skip_frame.bind("<Enter>", on_enter)
            skip_frame.bind("<Leave>", on_leave)
            skip_var = tk.BooleanVar(value=step.get("skip_next", False))
            self.seq_skip_vars.append(skip_var)
            sw = ToggleSwitch(skip_frame, skip_var)
            sw.pack(expand=True)
            skip_var.trace_add("write", lambda *args, idx=i, v=skip_var: self._update_seq_skip(idx, v))

            # 3. Double Click Toggle
            dc_frame = tk.Frame(actions, bg=self.CARD, width=70)
            dc_frame.pack_propagate(False)
            dc_frame.pack(side=tk.RIGHT, padx=10, fill=tk.Y)
            dc_frame.bind("<Enter>", on_enter)
            dc_frame.bind("<Leave>", on_leave)
            dc_var = tk.BooleanVar(value=step.get("double_click", False))
            if not hasattr(self, "seq_dc_vars"): self.seq_dc_vars = []
            self.seq_dc_vars.append(dc_var)
            sw_dc = ToggleSwitch(dc_frame, dc_var)
            sw_dc.pack(expand=True)
            dc_var.trace_add("write", lambda *args, idx=i, v=dc_var: self._update_seq_dc(idx, v))

            # 4. Wait Entry
            wait_frame = tk.Frame(actions, bg=self.CARD, width=80)
            wait_frame.pack_propagate(False)
            wait_frame.pack(side=tk.RIGHT, padx=(10, 14), fill=tk.Y)
            wait_frame.bind("<Enter>", on_enter)
            wait_frame.bind("<Leave>", on_leave)
            
            wait_var = tk.StringVar(value=str(step.get("wait", 0)))
            
            border_frame = tk.Frame(wait_frame, bg="#4B5563") # clear visible border
            border_frame.pack(expand=True, pady=4)
            
            entry_frame = tk.Frame(border_frame, bg="#1E2530")
            entry_frame.pack(padx=1, pady=1, fill=tk.BOTH, expand=True) # 1px simulated geometric border
            
            wait_entry = tk.Entry(entry_frame, textvariable=wait_var, width=5, font=("Segoe UI", 11, "bold"), bg="#1E2530", fg="#FFFFFF", insertbackground="#FFFFFF", bd=0, justify="center")
            wait_entry.pack(padx=4, pady=4)
            wait_var.trace_add("write", lambda *args, idx=i, v=wait_var: self._update_seq_wait(idx, v))
            
            # Allow focus events to cascade entry frame styling correctly
            def _on_focus_in(e, bf=border_frame, ef=entry_frame, we=wait_entry): 
                bf.configure(bg="#FF7A18")
                ef.configure(bg="#2A2F3A")
                we.configure(bg="#2A2F3A")
            def _on_focus_out(e, bf=border_frame, ef=entry_frame, we=wait_entry): 
                bf.configure(bg="#4B5563")
                ef.configure(bg="#1E2530")
                we.configure(bg="#1E2530")
            wait_entry.bind("<FocusIn>", _on_focus_in)
            wait_entry.bind("<FocusOut>", _on_focus_out)

        _bind_mousewheel(self.seq_canvas, self.seq_scroll_frame)
        self.seq_canvas.bind("<MouseWheel>", lambda e: self.seq_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def _build_images_view(self):
        view = tk.Frame(self.main_content, bg=self.BG)
        self.views["Manage Images"] = view
        
        header = tk.Frame(view, bg=self.BG)
        header.pack(fill=tk.X, pady=(0, 24))
        
        titles = tk.Frame(header, bg=self.BG)
        titles.pack(side=tk.LEFT)
        tk.Label(titles, text="Manage Images", font=("Segoe UI", 24, "bold"), bg=self.BG, fg=self.TEXT).pack(anchor="w")
        tk.Label(titles, text="Upload and maintain images.", font=("Segoe UI", 12), bg=self.BG, fg=self.TEXT_SEC).pack(anchor="w")

        RoundedButton(header, text="Add New Image", bg_color=self.PRIMARY, fg_color="#FFF", hover_color=self.PRIMARY_HOVER, command=self._add_new_image, width=140, height=40).pack(side=tk.RIGHT)

        list_container = tk.Frame(view, bg=self.BG)
        list_container.pack(fill=tk.BOTH, expand=True)

        self.img_canvas = tk.Canvas(list_container, bg=self.BG, highlightthickness=0, bd=0)
        scrollbar = SmoothScrollbar(list_container, target_canvas=self.img_canvas)
        self.img_scroll_frame = tk.Frame(self.img_canvas, bg=self.BG, bd=0)

        def _update_img_scrollregion(e=None):
            w = self.img_scroll_frame.winfo_width()
            h = self.img_scroll_frame.winfo_height()
            ch = self.img_canvas.winfo_height()
            self.img_canvas.configure(scrollregion=(0, 0, w, max(h, ch)))

        self.img_scroll_frame.bind("<Configure>", _update_img_scrollregion)
        self.img_canvas.bind("<Configure>", lambda e: [self.img_canvas.itemconfig(self.img_canvas_window, width=e.width), _update_img_scrollregion()])
        self.img_canvas_window = self.img_canvas.create_window((0, 0), window=self.img_scroll_frame, anchor="nw")
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.img_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.image_status_labels = {}

    def _refresh_image_list(self):
        for widget in self.img_scroll_frame.winfo_children(): widget.destroy()
        self.image_status_labels.clear()

        if not hasattr(self, '_grid_images'): self._grid_images = []
        self._grid_images.clear()

        def create_action_btn(parent, text, default_fg, hover_fg, command, px):
            btn = tk.Button(parent, text=text, font=("Segoe UI", 10), bg=self.CARD, fg=default_fg, activebackground=self.CARD, activeforeground=hover_fg, bd=0, cursor="hand2", command=command)
            btn.bind("<Enter>", lambda e, b=btn, c=hover_fg: b.config(fg=c))
            btn.bind("<Leave>", lambda e, b=btn, c=default_fg: b.config(fg=c))
            btn.pack(side=tk.LEFT, padx=px)
            return btn

        for i, img_name in enumerate(IMAGE_FILES):
            card = tk.Frame(self.img_scroll_frame, bg=self.CARD, pady=12, padx=16)
            if i > 0:
                card.pack(fill=tk.X, pady=(10, 0))
            else:
                card.pack(fill=tk.X, pady=0)
            
            img_path = os.path.join(IMAGE_DIR, img_name)
            lbl_preview = tk.Label(card, bg=self.BORDER, width=40, height=40)
            if os.path.isfile(img_path):
                try:
                    pil_img = Image.open(img_path)
                    pil_img.thumbnail((40, 40))
                    tk_img = ImageTk.PhotoImage(pil_img)
                    self._grid_images.append(tk_img)
                    lbl_preview.config(image=tk_img, width=0, height=0)
                except: lbl_preview.config(text="Err", fg=self.ERROR)
            lbl_preview.pack(side=tk.LEFT, padx=(0, 16))

            details = tk.Frame(card, bg=self.CARD)
            details.pack(side=tk.LEFT, fill=tk.Y)
            tk.Label(details, text=img_name, font=("Segoe UI", 12, "bold"), bg=self.CARD, fg=self.TEXT).pack(anchor="w")
            
            status_frame = tk.Frame(details, bg=self.CARD)
            status_frame.pack(fill=tk.X)
            indicator = tk.Canvas(status_frame, width=10, height=10, bg=self.CARD, highlightthickness=0)
            indicator.pack(side=tk.LEFT, pady=2)
            lbl_status = tk.Label(status_frame, text="Checking...", font=("Segoe UI", 10), bg=self.CARD, fg=self.TEXT_SEC)
            lbl_status.pack(side=tk.LEFT, padx=6)
            self.image_status_labels[img_name] = (indicator, lbl_status)

            actions = tk.Frame(card, bg=self.CARD)
            actions.pack(side=tk.RIGHT, fill=tk.Y)
            create_action_btn(actions, "✏ Rename", "#AAB4C3", "#D1D5DB", lambda n=img_name: self._rename_image(n), (0, 16))
            create_action_btn(actions, "🔄 Replace", "#FF8A3D", "#FF9D5C", lambda n=img_name: self._upload_image(n), (0, 16))
            create_action_btn(actions, "🗑 Delete", "#E05252", "#EF4444", lambda n=img_name: self._delete_image(n), (0, 5))

        self._update_image_statuses()
        
        _bind_mousewheel(self.img_canvas, self.img_scroll_frame)
        self.img_canvas.bind("<MouseWheel>", lambda e: self.img_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def _close_window(self):
        self.stop_event.set()
        self.root.destroy()

    def _check_images(self):
        missing = [n for n in IMAGE_FILES if not os.path.isfile(os.path.join(IMAGE_DIR, n))]
        if missing: self._log(f"[-] Missing images: {', '.join(missing)}")
        else: self._log("[+] All image files found.")

    def _log(self, input_msg):
        def _append(msg=input_msg):
            self.log_text.configure(state=tk.NORMAL)
            timestamp = time.strftime("[%H:%M:%S] ")
            tag = "info"
            icon = "ℹ"
            
            if msg.startswith("[+]"): tag, icon, msg = "success", "✔", msg[3:].strip()
            elif msg.startswith("[-]"): tag, icon, msg = "error", "❌", msg[3:].strip()
            elif msg.startswith("[!]"): tag, icon, msg = "error", "❌", msg[3:].strip()
            elif msg.startswith("[~]"): tag, icon, msg = "warning", "⚠", msg[3:].strip()
            elif msg.startswith("[i]"): msg = msg[3:].strip()
                
            self.log_text.insert(tk.END, f"{timestamp}{icon} {msg}\n", tag)
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
        self.root.after(0, _append)

    def _clear_log(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _start(self):
        if self.macro_thread and self.macro_thread.is_alive(): return

        ratio = self.screen_ratio_var.get()
        area = self.scan_area_var.get()
        t_input = self.timer_var.get().strip()

        if area == "all" and ratio != "16:9":
            messagebox.showerror("Invalid", "Scan area 'all' is allowed only when ratio is 16:9.")
            return

        self.timer_val = 0
        if t_input:
            try: self.timer_val = float(t_input) * 60
            except ValueError: return messagebox.showerror("Invalid", "Timer must be valid minutes.")

        self.stop_event.clear()
        self.start_btn.set_state(tk.DISABLED)
        self.stop_btn.set_state(tk.NORMAL)
        self.status_var.set("Running")
        self.status_label.configure(fg=self.SUCCESS)
        self._update_hint_state(True)
        self.timer_display_var.set("")
        
        if self.timer_val > 0:
            self.remaining_time = self.timer_val
            self._update_timer()

        self.macro_thread = threading.Thread(target=self._macro_worker, daemon=True)
        self.macro_thread.start()

    def _update_timer(self):
        if self.stop_event.is_set():
            self.timer_display_var.set("")
            return
        if self.remaining_time <= 0:
            self._log("[i] Timer finished. Stopping.")
            self.stop_event.set()
            self.timer_display_var.set("00:00")
            return
        m, s = divmod(int(self.remaining_time), 60)
        self.timer_display_var.set(f"{m:02d}:{s:02d}")
        self.remaining_time -= 1
        self.root.after(1000, self._update_timer)

    def _macro_worker(self):
        run_macro(self.stop_event, self._log, self.screen_ratio_var.get(), self.scan_area_var.get())
        self.root.after(0, self._on_macro_done)

    def _update_hint_state(self, is_running):
        color = "#e5e7eb" if is_running else "#9aa4b2"
        badge_bg = "#2563eb" if is_running else "#1f2430"
        badge_border = "#3b82f6" if is_running else "#2a2f3a"
        badge_fg = "#ffffff" if is_running else "#e5e7eb"
        
        try:
            self.hint_icon.configure(fg=color)
            self.hint_text1.configure(fg=color)
            self.hint_text2.configure(fg=color)
            self.hint_badge.configure(bg=badge_bg, highlightbackground=badge_border)
            self.hint_badge_lbl.configure(bg=badge_bg, fg=badge_fg)
        except AttributeError:
            pass

    def _on_macro_done(self):
        self.start_btn.set_state(tk.NORMAL)
        self.stop_btn.set_state(tk.DISABLED)
        self.status_var.set("Stopped")
        self.status_label.configure(fg=self.ERROR)
        self._update_hint_state(False)

    def _stop(self):
        self.stop_event.set()
        self._log("[i] Stopping...")

    def _on_drop(self, files):
        if not files:
            return
            
        for file_item in files:
            # Handle different formats returned by windnd (bytes vs str)
            try:
                path = file_item if isinstance(file_item, str) else file_item.decode('utf-8')
            except UnicodeDecodeError:
                path = file_item.decode('gbk', errors='ignore')
                
            path = os.path.normpath(path)
                
            if not os.path.isfile(path): continue
            
            ext = os.path.splitext(path)[1].lower()
            if ext not in ['.png', '.jpg', '.jpeg', '.bmp']:
                self._log(f"[-] Dropped file is not a supported image: {path}")
                continue
                
            original_filename = os.path.basename(path)
            
            # Show dialog prefilled with original filename
            dialog = CustomInputDialog(self.root, "Add Dropped Image", "Filename:", ok_text="Add", default_value=original_filename)
            new_name = dialog.result
            
            if not new_name:
                continue
                
            if not new_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')): 
                new_name += ext if ext else ".png"
                
            if new_name in IMAGE_FILES:
                messagebox.showinfo("Exists", f"Image '{new_name}' already exists.")
                continue
                
            try:
                shutil.copy(path, os.path.join(IMAGE_DIR, new_name))
                IMAGE_FILES.append(new_name)
                MACRO_SEQUENCE.append({"name": new_name, "wait": 0.5, "skip_next": False, "double_click": False})
                save_config()
                self._log(f"[+] Added target via drop: {new_name}")
                if self.current_view in ["Manage Images", "Macro Sequence"]:
                    self._refresh_image_list()
                    if self.current_view == "Macro Sequence":
                        self._refresh_sequence_list()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _add_new_image(self):
        dialog = CustomInputDialog(self.root, "Add New Image", "Filename (Optional):")
        
        if dialog.result is None:
            return  # User clicked Cancel or closed the popup
            
        new_name = dialog.result
            
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
        if not path:
            return
            
        if not new_name:
            new_name = os.path.basename(path)
            
        if not new_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            ext = os.path.splitext(path)[1].lower()
            new_name += ext if ext else ".png"

        if new_name in IMAGE_FILES: 
            return messagebox.showinfo("Exists", "Already exists.")
            
        try:
            shutil.copy(path, os.path.join(IMAGE_DIR, new_name))
            IMAGE_FILES.append(new_name)
            MACRO_SEQUENCE.append({"name": new_name, "wait": 0.5, "skip_next": False, "double_click": False})
            save_config()
            self._log(f"[+] Added target: {new_name}")
            if self.current_view in ["Manage Images", "Macro Sequence"]:
                self._refresh_image_list()
                if self.current_view == "Macro Sequence":
                    self._refresh_sequence_list()
        except Exception as e: 
            messagebox.showerror("Error", str(e))

    def _update_image_statuses(self):
        for img_name, (indicator, label) in self.image_status_labels.items():
            if os.path.isfile(os.path.join(IMAGE_DIR, img_name)):
                indicator.create_oval(1, 1, 9, 9, fill=self.SUCCESS, outline=self.SUCCESS)
                label.config(text="Found", fg=self.SUCCESS)
            else:
                indicator.create_oval(1, 1, 9, 9, fill=self.ERROR, outline=self.ERROR)
                label.config(text="Missing", fg=self.ERROR)

    def _upload_image(self, target_name):
        path = filedialog.askopenfilename(filetypes=[("Image", "*.png *.jpg *.jpeg *.bmp")])
        if path:
            try:
                shutil.copy(path, os.path.join(IMAGE_DIR, target_name))
                self._log(f"[+] Replaced {target_name}")
                self._update_image_statuses()
                if self.current_view in ["Manage Images", "Macro Sequence"]:
                    self._refresh_image_list()
                    self._refresh_sequence_list()
            except Exception as e: messagebox.showerror("Error", str(e))

    def _rename_image(self, target):
        dialog = CustomInputDialog(self.root, "Rename Image", "New Filename:", ok_text="Save", default_value=target)
        new_name = dialog.result
        if not new_name: return
        
        ext = os.path.splitext(target)[1]
        if not new_name.lower().endswith(tuple(['.png', '.jpg', '.jpeg', '.bmp'])):
            new_name += ext if ext else ".png"

        if new_name == target:
            return

        if new_name in IMAGE_FILES:
            return messagebox.showinfo("Exists", "An image with that name already exists.")

        old_path = os.path.join(IMAGE_DIR, target)
        new_path = os.path.join(IMAGE_DIR, new_name)
        
        try:
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
                
            idx = IMAGE_FILES.index(target)
            IMAGE_FILES[idx] = new_name
            
            for step in MACRO_SEQUENCE:
                if step["name"] == target:
                    step["name"] = new_name
            
            save_config()
            self._log(f"[+] Renamed {target} to {new_name}")
            
            if self.current_view in ["Manage Images", "Macro Sequence"]:
                self._refresh_image_list()
                if self.current_view == "Macro Sequence":
                    self._refresh_sequence_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename: {e}")

    def _delete_image(self, target):
        try:
            if os.path.isfile(os.path.join(IMAGE_DIR, target)): os.remove(os.path.join(IMAGE_DIR, target))
            if target in IMAGE_FILES: IMAGE_FILES.remove(target)
            global MACRO_SEQUENCE
            MACRO_SEQUENCE = [s for s in MACRO_SEQUENCE if s["name"] != target]
            save_config()
            self._log(f"[-] Deleted {target}")
            if self.current_view in ["Manage Images", "Macro Sequence"]:
                self._refresh_image_list()
                self._refresh_sequence_list()
        except Exception as e: messagebox.showerror("Error", str(e))

    def _move_seq(self, idx, dir):
        nx = idx + dir
        if 0 <= nx < len(MACRO_SEQUENCE):
            MACRO_SEQUENCE[idx], MACRO_SEQUENCE[nx] = MACRO_SEQUENCE[nx], MACRO_SEQUENCE[idx]
            save_config()
            self._refresh_sequence_list()

    def _update_seq_wait(self, idx, var):
        try:
            val = float(var.get())
            if val >= 0: MACRO_SEQUENCE[idx]["wait"] = val; save_config()
        except ValueError: pass

    def _update_seq_skip(self, idx, var):
        MACRO_SEQUENCE[idx]["skip_next"] = var.get()
        save_config()

    def _update_seq_dc(self, idx, var):
        MACRO_SEQUENCE[idx]["double_click"] = var.get()
        save_config()

def main():
    root = tk.Tk()
    MacroApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
