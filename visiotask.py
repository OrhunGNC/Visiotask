import sys
import os
import threading
import time
import shutil
import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
from PIL import Image, ImageTk

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
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

IMAGE_FILES = [
    'firstimage.png',
    'secondimage.png',
    'thirdimage.png',
    'fourthimage.png',
    'fifthimage.png',
    'sixthimage.png',
]

MACRO_SEQUENCE = [
    {"name": "firstimage.png", "wait": 0.5, "skip_next": False},
    {"name": "secondimage.png", "wait": 0.3, "skip_next": True},
    {"name": "thirdimage.png", "wait": 0.5, "skip_next": False},
    {"name": "fourthimage.png", "wait": 1.5, "skip_next": False},
    {"name": "fifthimage.png", "wait": 0.0, "skip_next": False},
    {"name": "sixthimage.png", "wait": 1.0, "skip_next": False},
]


# --- Macro Logic ---
def find_and_click(image_file, name, confidence=0.75, region=None, log=None):
    image_path = os.path.join(SCRIPT_DIR, image_file)
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
        pyautogui.click(center_x, center_y)
        if log:
            log(f"[+] {name} clicked  ({max_val:.2f}  @{center_x},{center_y})")
        return True
    return False

def is_image_visible(image_file, confidence=0.75, region=None, log=None):
    """Check if image exists on screen without clicking."""
    image_path = os.path.join(SCRIPT_DIR, image_file)
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
    _, max_val, _, _ = cv2.minMaxLoc(result)
    return max_val >= confidence



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

    log("--- Macro running (press Q to stop) ---")
    log(f"Screen: {screen_width}x{screen_height} | ratio: {screen_ratio} | scanning: {search_label}")

    while not stop_event.is_set():
        if keyboard.is_pressed('q'):
            stop_event.set()
            break

        skip_next = False
        
        for idx, step in enumerate(MACRO_SEQUENCE):
            if stop_event.is_set() or keyboard.is_pressed('q'):
                break
                
            if skip_next:
                log(f"[i] Skipping {step['name']} due to previous condition.")
                skip_next = False
                continue

            img_name = step["name"]
            wait_time = step["wait"]

            found = find_and_click(img_name, img_name.upper(), 0.75, search_region, log)
            if found:
                time.sleep(wait_time)
            else:
                if step.get("skip_next", False):
                    skip_next = True

    log("--- Macro stopped ---")


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, bg_color, fg_color, hover_color, command, radius=15, font=("Segoe UI Semibold", 14), width=200, height=50, **kwargs):
        super().__init__(parent, bg=parent["bg"], highlightthickness=0, width=width, height=height, **kwargs)
        self.command = command
        self.radius = radius
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.hover_color = hover_color
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
        self._draw()
        
    def set_text_color(self, color):
        self.fg_color = color
        self._draw()
        
    def configure(self, **kwargs):
        if 'state' in kwargs:
            self.set_state(kwargs['state'])
            
    def config(self, **kwargs):
        self.configure(**kwargs)

    def _draw(self, event=None):
        self.delete("all")
        w = max(self.winfo_width(), self.req_width)
        h = max(self.winfo_height(), self.req_height)
        if w < 10 or h < 10:
            return
        
        color = self.bg_color
        if self.disabled:
            color = "#555555" # Example disabled background
            
        r = self.radius
        points = [
            r, 0,
            w-r, 0,
            w, 0, w, r,
            w, h-r,
            w, h, w-r, h,
            r, h,
            0, h, 0, h-r,
            0, r,
            0, 0, r, 0
        ]
        self.create_polygon(points, fill=color, outline=color, smooth=True)
        
        fg = "#999999" if self.disabled else self.fg_color
        self.create_text(w/2, h/2, text=self.text, fill=fg, font=self.font)

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
        r = self.radius
        points = [
            r, 0,
            w-r, 0,
            w, 0, w, r,
            w, h-r,
            w, h, w-r, h,
            r, h,
            0, h, 0, h-r,
            0, r,
            0, 0, r, 0
        ]
        self.create_polygon(points, fill=color, outline=color, smooth=True)
        self.create_text(w/2, h/2, text=self.text, fill=self.fg_color, font=self.font)


# --- GUI ---
class MacroApp:
    BG = "#000000"
    CARD = "#1e1e1e"
    SURFACE = "#171717"
    BORDER = "#2e2e2e"
    FG = "#f4f7ff"
    MUTED = "#9aa6bf"
    ACCENT = "#ff6b3d"
    GREEN = "#9de5b2"
    RED = "#f49ab6"
    HEADER = "#151515"

    ICON_APP = "\u270E"
    ICON_GEAR = "\u2699"
    ICON_MONITOR = "\U0001F5A5"
    ICON_EYE = "\U0001F441"
    ICON_LIST = "\u2630"
    ICON_PLAY = "\u25B6"
    ICON_STOP = "\u25A0"

    def __init__(self, root):
        self.root = root
        self.root.title("Visiotask")
        self.root.configure(bg=self.BG)
        self.root.resizable(True, True)
        self.root.attributes("-topmost", True)
        
        # Apply dark theme to Windows title bar
        try:
            import ctypes
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:
            pass

        self.stop_event = threading.Event()
        self.macro_thread = None
        self.screen_ratio_var = tk.StringVar(value="32:9")
        self.scan_area_var = tk.StringVar(value="left")
        self.style = ttk.Style()
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.is_maximized = False
        self.normal_geometry = ""
        self.accent_canvas = None

        self._setup_styles()
        self._build_ui()
        self._check_images()
        self.root.bind("<Alt-F4>", lambda _event: self._close_window())

    def _setup_styles(self):
        self.style.theme_use("clam")
        self.style.configure(
            "Dark.TCombobox",
            fieldbackground=self.SURFACE,
            background=self.SURFACE,
            foreground=self.FG,
            bordercolor=self.BORDER,
            lightcolor=self.BORDER,
            darkcolor=self.BORDER,
            arrowcolor=self.FG,
            insertcolor=self.FG,
            selectbackground="#2c3550",
            selectforeground=self.FG,
            padding=6,
        )
        self.style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", self.SURFACE), ("disabled", "#1a1f2a")],
            foreground=[("disabled", self.MUTED)],
        )
        self.style.configure(
            "Dark.TNotebook", 
            background=self.BG, 
            borderwidth=0
        )
        self.style.configure(
            "Dark.TNotebook.Tab", 
            background=self.CARD, 
            foreground=self.FG, 
            padding=[10, 5], 
            font=("Segoe UI", 10),
            borderwidth=0
        )
        self.style.map(
            "Dark.TNotebook.Tab", 
            background=[("selected", self.SURFACE)], 
            foreground=[("selected", self.ACCENT)]
        )

    def _build_ui(self):
        shell = tk.Frame(self.root, bg=self.BG)
        shell.pack(fill=tk.BOTH, expand=True)

        body = tk.Frame(shell, bg=self.BG)
        body.pack(fill=tk.BOTH, expand=True, padx=(18, 8), pady=(6, 14))

        self.accent_canvas = tk.Canvas(
            body,
            width=12,
            bg=self.BG,
            highlightthickness=0,
            bd=0,
        )
        self.accent_canvas.pack(side=tk.RIGHT, fill=tk.Y)
        self.accent_canvas.bind("<Configure>", self._draw_right_accent)

        self.notebook = ttk.Notebook(body, style="Dark.TNotebook")
        self.notebook.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.tab_macro = tk.Frame(self.notebook, bg=self.BG)
        self.tab_images = tk.Frame(self.notebook, bg=self.BG)
        self.tab_sequence = tk.Frame(self.notebook, bg=self.BG)
        
        self.notebook.add(self.tab_macro, text="Run Macro")
        self.notebook.add(self.tab_sequence, text="Macro Sequence")
        self.notebook.add(self.tab_images, text="Manage Images")

        main = tk.Frame(self.tab_macro, bg=self.BG)
        main.pack(fill=tk.BOTH, expand=True)

        self._build_sequence_tab(self.tab_sequence)
        self._build_images_tab(self.tab_images)

        tk.Label(
            main,
            text="Visiotask",
            font=("Segoe UI Semibold", 24),
            bg=self.BG,
            fg=self.FG,
        ).pack(pady=(18, 14))

        config_section = self._create_panel(main)
        config_section.pack(fill=tk.X, padx=14, pady=(0, 10))

        config_header = tk.Frame(config_section, bg=self.CARD)
        config_header.pack(fill=tk.X, padx=14, pady=(12, 8))

        tk.Label(
            config_header,
            text=self.ICON_GEAR,
            font=("Segoe UI Symbol", 16),
            bg=self.CARD,
            fg=self.FG,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(
            config_header,
            text="Configuration",
            font=("Segoe UI Semibold", 11),
            bg=self.CARD,
            fg=self.FG,
            anchor="w",
        ).pack(side=tk.LEFT)

        config_grid = tk.Frame(config_section, bg=self.CARD)
        config_grid.pack(fill=tk.X, padx=14, pady=(8, 14))

        label_frame1 = tk.Frame(config_grid, bg=self.CARD, width=150, height=30)
        label_frame1.pack_propagate(False)
        label_frame1.grid(row=0, column=0, sticky="w", padx=(0, 10), pady=4)
        tk.Label(
            label_frame1,
            text=self.ICON_MONITOR,
            font=("Segoe UI Symbol", 15),
            bg=self.CARD,
            fg=self.FG,
        ).pack(side="left")
        tk.Label(
            label_frame1,
            text="Screen ratio:",
            font=("Segoe UI", 10),
            bg=self.CARD,
            fg=self.FG,
            anchor="w",
        ).pack(side="left", padx=(8, 0))

        self.screen_ratio_menu = ttk.Combobox(
            config_grid,
            textvariable=self.screen_ratio_var,
            values=("16:9", "32:9"),
            state="readonly",
            width=16,
            style="Dark.TCombobox",
            font=("Segoe UI", 12),
        )
        self.screen_ratio_menu.grid(row=0, column=1, sticky="w", pady=4)

        label_frame2 = tk.Frame(config_grid, bg=self.CARD, width=150, height=30)
        label_frame2.pack_propagate(False)
        label_frame2.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=4)
        tk.Label(
            label_frame2,
            text=self.ICON_EYE,
            font=("Segoe UI Symbol", 15),
            bg=self.CARD,
            fg=self.FG,
        ).pack(side="left")
        tk.Label(
            label_frame2,
            text="Scan area:",
            font=("Segoe UI", 10),
            bg=self.CARD,
            fg=self.FG,
            anchor="w",
        ).pack(side="left", padx=(8, 0))

        self.scan_area_menu = ttk.Combobox(
            config_grid,
            textvariable=self.scan_area_var,
            values=("left", "right", "all"),
            state="readonly",
            width=16,
            style="Dark.TCombobox",
            font=("Segoe UI", 12),
        )
        self.scan_area_menu.grid(row=1, column=1, sticky="w", pady=4)

        self.screen_ratio_var.trace_add("write", self._on_ratio_changed)

        ready_section = self._create_panel(main)
        ready_section.pack(fill=tk.X, padx=14, pady=(0, 10))

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(
            ready_section,
            textvariable=self.status_var,
            font=("Segoe UI Semibold", 16),
            bg=self.CARD,
            fg=self.FG,
        )
        self.status_label.pack(pady=(12, 10))

        tk.Label(
            ready_section,
            text="Note: 'all' scan area allowed only with 16:9.",
            font=("Segoe UI", 9),
            bg=self.CARD,
            fg=self.MUTED,
            anchor="w",
        ).pack(fill=tk.X, padx=14, pady=(0, 12))

        q_label = tk.Label(
            main,
            text="[Q] Press Q on your keyboard anytime to stop the macro",
            font=("Segoe UI", 10),
            bg=self.BG,
            fg=self.FG,
        )
        q_label.pack(side=tk.BOTTOM, pady=(4, 10))

        btn_frame = tk.Frame(main, bg=self.BG)
        btn_frame.pack(side=tk.BOTTOM, pady=(0, 20))

        log_wrap = self._create_panel(main)
        log_wrap.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 10))

        log_header = tk.Frame(log_wrap, bg=self.CARD)
        log_header.pack(fill=tk.X, padx=14, pady=(12, 6))

        tk.Label(
            log_header,
            text=self.ICON_LIST,
            font=("Segoe UI Symbol", 11),
            bg=self.CARD,
            fg=self.FG,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(
            log_header,
            text="Log",
            font=("Segoe UI Semibold", 11),
            bg=self.CARD,
            fg=self.FG,
            anchor="w",
        ).pack(side=tk.LEFT)

        log_frame = tk.Frame(log_wrap, bg=self.SURFACE, bd=0, highlightthickness=1, highlightbackground=self.BORDER)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 12))

        self.log_text = tk.Text(
            log_frame,
            height=6,
            width=64,
            font=("Consolas", 9),
            bg=self.SURFACE,
            fg=self.FG,
            insertbackground=self.FG,
            relief="flat",
            state=tk.DISABLED,
            wrap=tk.WORD,
            padx=8,
            pady=8,
        )
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview, bg=self.SURFACE, troughcolor=self.CARD)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.start_btn = RoundedButton(
            btn_frame,
            text=f"{self.ICON_PLAY}  START Macro",
            font=("Segoe UI Semibold", 14),
            bg_color=self.GREEN,
            fg_color="#102118",
            hover_color="#87dca1",
            command=self._start,
            width=220,
            height=60,
            radius=20,
            cursor="hand2"
        )
        self.start_btn.pack(side=tk.LEFT, padx=12)

        self.stop_btn = RoundedButton(
            btn_frame,
            text=f"{self.ICON_STOP}  STOP Macro",
            font=("Segoe UI Semibold", 14),
            bg_color=self.RED,
            fg_color="#24111a",
            hover_color="#ee85a8",
            command=self._stop,
            width=220,
            height=60,
            radius=20,
            cursor="hand2"
        )
        self.stop_btn.pack(side=tk.LEFT, padx=12)
        self.stop_btn.set_state(tk.DISABLED)

    def _create_panel(self, parent):
        panel = tk.Frame(
            parent,
            bg=self.CARD,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.BORDER,
        )
        return panel

    def _draw_right_accent(self, event):
        self.accent_canvas.delete("all")
        x = 6
        y0 = 20
        y1 = max(22, event.height - 20)
        self.accent_canvas.create_line(x, y0, x, y1, fill=self.ACCENT, width=4, capstyle=tk.ROUND)

    def _close_window(self):
        self.stop_event.set()
        self.root.destroy()

    def _check_images(self):
        missing = []
        for name in IMAGE_FILES:
            path = os.path.join(SCRIPT_DIR, name)
            if not os.path.isfile(path):
                missing.append(name)
        if missing:
            self._log(f"[!] Missing images: {', '.join(missing)}")
        else:
            self._log("[+] All image files found.")

    def _log(self, msg):
        def _append():
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.insert(tk.END, msg + "\n")
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
        self.root.after(0, _append)

    def _on_ratio_changed(self, *_):
        if self.screen_ratio_var.get() != "16:9" and self.scan_area_var.get() == "all":
            self.scan_area_var.set("left")
            self._log("[i] 'all' scan area is only for 16:9. Switched to left half.")

    def _start(self):
        if self.macro_thread and self.macro_thread.is_alive():
            return

        selected_ratio = self.screen_ratio_var.get()
        selected_scan_area = self.scan_area_var.get()

        if selected_scan_area == "all" and selected_ratio != "16:9":
            messagebox.showerror("Invalid Selection", "Scan area 'all' is allowed only when ratio is 16:9.")
            return

        self.stop_event.clear()
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.screen_ratio_menu.configure(state="disabled")
        self.scan_area_menu.configure(state="disabled")
        self.status_var.set("Running...")
        self.status_label.configure(fg=self.ACCENT)
        self._log(f"[i] Ratio: {selected_ratio} | Scan area: {selected_scan_area}")

        self.macro_thread = threading.Thread(target=self._macro_worker, daemon=True)
        self.macro_thread.start()

    def _macro_worker(self):
        run_macro(
            self.stop_event,
            self._log,
            self.screen_ratio_var.get(),
            self.scan_area_var.get(),
        )
        self.root.after(0, self._on_macro_done)

    def _on_macro_done(self):
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        self.screen_ratio_menu.configure(state="readonly")
        self.scan_area_menu.configure(state="readonly")
        self.status_var.set("Stopped")
        self.status_label.configure(fg=self.RED)

    def _stop(self):
        self.stop_event.set()
        self._log("Stopping...")

    def _build_images_tab(self, parent):
        tk.Label(
            parent,
            text="Manage Macro Images",
            font=("Segoe UI Semibold", 20),
            bg=self.BG,
            fg=self.FG,
        ).pack(pady=(18, 5))
        
        btn_add = tk.Button(
            parent, text="Add New Custom Image",
            font=("Segoe UI Semibold", 10), bg=self.ACCENT, fg="#102118",
            activebackground="#ff8b66", activeforeground="#102118",
            relief="flat", bd=0, padx=14, pady=6, cursor="hand2",
            command=self._add_new_image
        )
        btn_add.pack(pady=(0, 10))

        # Scrollable container for images
        list_frame = tk.Frame(parent, bg=self.BG)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 14))

        self.img_canvas = tk.Canvas(list_frame, bg=self.BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.img_canvas.yview, bg=self.BG, troughcolor=self.CARD)
        self.scrollable_frame = self._create_panel(self.img_canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.img_canvas.configure(
                scrollregion=self.img_canvas.bbox("all")
            )
        )
        
        # Make the canvas window match the canvas width
        self.img_canvas.bind(
            "<Configure>",
            lambda e: self.img_canvas.itemconfig(self.img_canvas_window, width=e.width)
        )

        self.img_canvas_window = self.img_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.img_canvas.configure(yscrollcommand=scrollbar.set)

        self.img_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.image_status_labels = {}
        self._refresh_image_list()

    def _refresh_image_list(self):
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.image_status_labels.clear()

        for img_name in IMAGE_FILES:
            row = tk.Frame(self.scrollable_frame, bg=self.CARD)
            row.pack(fill=tk.X, padx=14, pady=8)
            
            lbl_name = tk.Label(row, text=img_name, font=("Segoe UI", 11), bg=self.CARD, fg=self.FG, width=16, anchor="w")
            lbl_name.pack(side=tk.LEFT)
            
            lbl_status = tk.Label(row, text="Status: Unknown", font=("Segoe UI", 10), bg=self.CARD, fg=self.MUTED, width=14, anchor="w")
            lbl_status.pack(side=tk.LEFT)
            self.image_status_labels[img_name] = lbl_status
            
            btn_upload = tk.Button(
                row, text="Upload/Replace", 
                font=("Segoe UI", 9), bg=self.SURFACE, fg=self.FG, 
                activebackground=self.BORDER, activeforeground=self.FG,
                relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                command=lambda n=img_name: self._upload_image(n)
            )
            btn_upload.pack(side=tk.LEFT, padx=5)
            
            btn_delete = tk.Button(
                row, text="Delete", 
                font=("Segoe UI", 9), bg=self.RED, fg="#24111a", 
                activebackground="#ee85a8", activeforeground="#24111a",
                relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
                command=lambda n=img_name: self._delete_image(n)
            )
            btn_delete.pack(side=tk.LEFT, padx=5)
            
        self._update_image_statuses()

    def _add_new_image(self):
        from tkinter import simpledialog
        new_name = simpledialog.askstring("New Image", "Enter filename for the new image (e.g. custom_image.png):", parent=self.root)
        if not new_name:
            return
            
        if not new_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            new_name += ".png"
            
        if new_name in IMAGE_FILES:
            messagebox.showinfo("Exists", "Image is already in the list.")
            return
            
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
        if file_path:
            target_path = os.path.join(SCRIPT_DIR, new_name)
            try:
                shutil.copy(file_path, target_path)
                IMAGE_FILES.append(new_name)
                # also add to end of sequence
                MACRO_SEQUENCE.append({"name": new_name, "wait": 0.5, "skip_next": False})
                self._log(f"[+] Added new image track target: {new_name}")
                self._refresh_image_list()
                self._refresh_sequence_list()
                self._check_images()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add image:\n{e}")

    def _update_image_statuses(self):
        for img_name, label in self.image_status_labels.items():
            path = os.path.join(SCRIPT_DIR, img_name)
            if os.path.isfile(path):
                label.config(text="Status: Found", fg=self.GREEN)
            else:
                label.config(text="Status: Missing", fg=self.RED)

    def _upload_image(self, target_name):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
        if file_path:
            target_path = os.path.join(SCRIPT_DIR, target_name)
            try:
                shutil.copy(file_path, target_path)
                self._log(f"[+] Replaced {target_name}")
                self._update_image_statuses()
                self._check_images()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to scale or copy image:\n{e}")

    def _delete_image(self, target_name):
        target_path = os.path.join(SCRIPT_DIR, target_name)
        if os.path.isfile(target_path):
            try:
                os.remove(target_path)
                self._log(f"[-] Deleted {target_name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete image:\n{e}")
                return
                
        if target_name in IMAGE_FILES:
            IMAGE_FILES.remove(target_name)
            
        # Also remove from sequence
        global MACRO_SEQUENCE
        MACRO_SEQUENCE = [s for s in MACRO_SEQUENCE if s["name"] != target_name]
            
        self._log(f"[-] Removed {target_name} from list")
        self._refresh_image_list()
        self._refresh_sequence_list()
        self._check_images()

    def _build_sequence_tab(self, parent):
        tk.Label(
            parent,
            text="Macro Execution Sequence",
            font=("Segoe UI Semibold", 20),
            bg=self.BG,
            fg=self.FG,
        ).pack(pady=(18, 5))
        
        info_lbl = tk.Label(
            parent,
            text="Arrange the order of images to search for, add wait times, and skip conditions.",
            font=("Segoe UI", 10),
            bg=self.BG,
            fg=self.MUTED,
        )
        info_lbl.pack(pady=(0, 10))
        
        list_frame = tk.Frame(parent, bg=self.BG)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 14))

        self.seq_canvas = tk.Canvas(list_frame, bg=self.BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.seq_canvas.yview, bg=self.BG, troughcolor=self.CARD)
        self.seq_scrollable_frame = self._create_panel(self.seq_canvas)

        self.seq_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.seq_canvas.configure(
                scrollregion=self.seq_canvas.bbox("all")
            )
        )
        self.seq_canvas.bind(
            "<Configure>",
            lambda e: self.seq_canvas.itemconfig(self.seq_canvas_window, width=e.width)
        )
        self.seq_canvas_window = self.seq_canvas.create_window((0, 0), window=self.seq_scrollable_frame, anchor="nw")
        self.seq_canvas.configure(yscrollcommand=scrollbar.set)
        self.seq_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self._refresh_sequence_list()

    def _refresh_sequence_list(self):
        for widget in self.seq_scrollable_frame.winfo_children():
            widget.destroy()

        if not hasattr(self, '_preview_images'):
            self._preview_images = []
        self._preview_images.clear()

        for i, step in enumerate(MACRO_SEQUENCE):
            row = tk.Frame(self.seq_scrollable_frame, bg=self.CARD)
            row.pack(fill=tk.X, padx=14, pady=6)
            
            # Reorder controls
            ctrl_frame = tk.Frame(row, bg=self.CARD)
            ctrl_frame.pack(side=tk.LEFT, padx=(0, 10))
            
            btn_up = tk.Button(
                ctrl_frame, text="▲", font=("Segoe UI", 8), bg=self.SURFACE, fg=self.FG, bd=0, 
                command=lambda idx=i: self._move_seq(idx, -1), state=tk.NORMAL if i > 0 else tk.DISABLED
            )
            btn_up.pack(side=tk.TOP, pady=2)
            
            btn_down = tk.Button(
                ctrl_frame, text="▼", font=("Segoe UI", 8), bg=self.SURFACE, fg=self.FG, bd=0, 
                command=lambda idx=i: self._move_seq(idx, 1), state=tk.NORMAL if i < len(MACRO_SEQUENCE)-1 else tk.DISABLED
            )
            btn_down.pack(side=tk.TOP, pady=2)

            # Image Preview
            img_path = os.path.join(SCRIPT_DIR, step["name"])
            if os.path.isfile(img_path):
                try:
                    pil_img = Image.open(img_path)
                    pil_img.thumbnail((36, 36))
                    tk_img = ImageTk.PhotoImage(pil_img)
                    self._preview_images.append(tk_img) # keep reference
                    lbl_preview = tk.Label(row, image=tk_img, bg=self.CARD, width=40, height=40)
                    lbl_preview.pack(side=tk.LEFT, padx=(0, 10))
                except Exception:
                    lbl_preview = tk.Label(row, text="N/A", font=("Segoe UI", 8), bg=self.BORDER, fg=self.FG, width=5, height=2)
                    lbl_preview.pack(side=tk.LEFT, padx=(0, 10))
            else:
                lbl_preview = tk.Label(row, text="Err", font=("Segoe UI", 8), bg=self.RED, fg=self.BG, width=5, height=2)
                lbl_preview.pack(side=tk.LEFT, padx=(0, 10))

            # Name
            lbl_name = tk.Label(row, text=step["name"], font=("Segoe UI Semibold", 11), bg=self.CARD, fg=self.ACCENT, width=15, anchor="w")
            lbl_name.pack(side=tk.LEFT)
            
            # Wait time
            tk.Label(row, text="Wait (s):", font=("Segoe UI", 9), bg=self.CARD, fg=self.FG).pack(side=tk.LEFT)
            wait_var = tk.StringVar(value=str(step["wait"]))
            wait_entry = tk.Entry(row, textvariable=wait_var, width=4, font=("Segoe UI", 10), bg=self.SURFACE, fg=self.FG, bd=0, insertbackground=self.FG)
            wait_entry.pack(side=tk.LEFT, padx=3)
            wait_var.trace_add("write", lambda *args, idx=i, v=wait_var: self._update_seq_wait(idx, v))

            # Skip next
            tk.Label(row, text="Skip next if missing:", font=("Segoe UI", 9), bg=self.CARD, fg=self.FG).pack(side=tk.LEFT, padx=(6,0))
            # Create the BooleanVar and save a reference to it in the widget so it doesn't get garbage collected
            skip_var = tk.BooleanVar(value=step["skip_next"])
            skip_chk = tk.Checkbutton(row, variable=skip_var, bg=self.CARD, fg=self.FG, activebackground=self.CARD, activeforeground=self.FG, selectcolor=self.ACCENT)
            skip_chk.var = skip_var # Keep reference to prevent GC!
            skip_chk.pack(side=tk.LEFT)
            skip_var.trace_add("write", lambda *args, idx=i, v=skip_var: self._update_seq_skip(idx, v))

    def _move_seq(self, index, direction):
        new_idx = index + direction
        if 0 <= new_idx < len(MACRO_SEQUENCE):
            MACRO_SEQUENCE[index], MACRO_SEQUENCE[new_idx] = MACRO_SEQUENCE[new_idx], MACRO_SEQUENCE[index]
            self._refresh_sequence_list()

    def _update_seq_wait(self, index, var):
        try:
            val = float(var.get())
            if val >= 0:
                MACRO_SEQUENCE[index]["wait"] = val
        except ValueError:
            pass

    def _update_seq_skip(self, index, var):
        MACRO_SEQUENCE[index]["skip_next"] = var.get()


def main():
    root = tk.Tk()
    root.geometry("600x760+120+70")
    root.minsize(500, 600)
    MacroApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
