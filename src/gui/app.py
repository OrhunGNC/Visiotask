import os
import shutil
import threading
import time
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import windnd
from src.utils.config import RESOURCE_DIR, IMAGE_DIR
from src.utils.state import state
from src.gui.components import (RoundedButton, ToggleSwitch, SmoothScrollbar,
                                 CustomDropdown, ProgressRing, CustomInputDialog, _bind_mousewheel)
from src.engine.macro import run_macro


class MacroApp:
    # Premium dark cyber-industrial palette — refined
    BG = "#060B16"
    BG_GRADIENT = "#080E1C"          # Subtle gradient layer
    CARD = "#0B1322"                  # Main card surface
    CARD_RAISED = "#0F1A2E"          # Hover/select layer
    CARD_GLOW = "#0D1829"            # Active item glow bg
    BORDER = "#1E2D42"                # Soft borders
    BORDER_FOCUS = "#FF7A1A"         # Orange focus borders
    BORDER_SUBTLE = "#14203A"        # Very subtle separators
    SHADOW = "#030710"               # Card shadow color
    PRIMARY = "#FF7A1A"              # Bright saturated orange
    PRIMARY_HOVER = "#FF9040"        # Orange hover
    PRIMARY_DIM = "#2A1800"          # Very dim orange for bg
    PRIMARY_GLOW = "#FF7A1A"         # Glow ring
    SUCCESS = "#00E676"              # Neon green
    SUCCESS_DIM = "#0A2E1A"         # Dim green
    WARNING = "#FACC15"
    ERROR = "#EF4444"
    TEXT = "#E8ECF1"                  # Slightly brighter text
    TEXT_SEC = "#7A8BA0"             # Refined secondary
    TEXT_DIM = "#4A5A70"             # Dimmed text
    INPUT_BG = "#080E1A"            # Input field background
    INPUT_BORDER = "#1E2D42"        # Input border
    INPUT_FOCUS = "#FF7A1A"          # Input focus border

    def __init__(self, root):
        self.root = root
        self.root.title("Visiotask")
        self.root.configure(bg=self.BG)
        self.root.geometry("1060x720")
        self.root.minsize(1060, 720)

        icon_path = os.path.join(RESOURCE_DIR, "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # Dark title bar on Windows
        try:
            import ctypes
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(2)), 4)
            ctypes.windll.user32.ChangeWindowMessageFilterEx(hwnd, 0x0233, 1, None)
            ctypes.windll.user32.ChangeWindowMessageFilterEx(hwnd, 0x0049, 1, None)
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
        self.scan_area_var = tk.StringVar(value=state.SCAN_AREA)
        self.click_mode_var = tk.StringVar(value=getattr(state, "CLICK_MODE", "background"))

        # Screen resolution detection
        w = self.root.winfo_screenwidth()
        h = self.root.winfo_screenheight()
        state.SCREEN_WIDTH = w
        state.SCREEN_HEIGHT = h
        if w > 0 and h > 0:
            import math
            gcd = math.gcd(w, h)
            state.SCREEN_RATIO = f"{w // gcd}:{h // gcd}"
        state.save_config()

        def _on_settings_change(*args):
            state.SCAN_AREA = self.scan_area_var.get()
            state.CLICK_MODE = self.click_mode_var.get()
            if state.CLICK_MODE != "window":
                state.TARGET_HWND = None
            state.save_config()

        self.scan_area_var.trace_add("write", _on_settings_change)
        self.click_mode_var.trace_add("write", _on_settings_change)

        self.current_view = "Run Macro"
        self.sidebar_buttons = {}
        self.views = {}

        self._build_ui()
        self._check_images()
        self.root.bind("<Alt-F4>", lambda _: self._close_window())

    # ──────────────────────────────────────────────────────
    #  UI BUILD — Layout
    # ──────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Sidebar (235px) ────────────────────────────
        self.sidebar = tk.Frame(self.root, bg=self.BG, width=235)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Subtle right separator
        tk.Frame(self.sidebar, bg=self.BORDER_SUBTLE, width=1).place(relx=1, rely=0, relheight=1)

        # Logo — compact
        brand_frame = tk.Frame(self.sidebar, bg=self.BG)
        brand_frame.pack(pady=(24, 36), padx=18, anchor="w", fill=tk.X)

        icon_path = os.path.join(RESOURCE_DIR, "icon.ico")
        if os.path.exists(icon_path):
            try:
                pil_icon = Image.open(icon_path).resize((22, 22))
                self._sidebar_icon = ImageTk.PhotoImage(pil_icon)
                tk.Label(brand_frame, image=self._sidebar_icon, bg=self.BG).pack(side=tk.LEFT, padx=(0, 8))
            except Exception:
                pass

        tk.Label(brand_frame, text="Visiotask", font=("Segoe UI Variable", 15, "bold"),
                 bg=self.BG, fg=self.PRIMARY).pack(side=tk.LEFT)

        # Navigation — only the three specified items
        for name in ["Run Macro", "Macro Sequence", "Manage Images"]:
            self._create_sidebar_btn(name)

        # ── Main Content ────────────────────────────────
        self.main_content = tk.Frame(self.root, bg=self.BG)
        self.main_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_run_macro_view()
        self._build_sequence_view()
        self._build_images_view()
        self._show_view("Run Macro")

    def _draw_line_icon(self, canvas, icon_type, color, size=16):
        """Draw a minimal line icon on a small canvas."""
        canvas.delete("all")
        s = size
        p = 2  # padding
        if icon_type == "play":
            # Play triangle — thin strokes
            canvas.create_polygon(p+3, p+2, p+3, s-2, s-3, s//2,
                                  fill="", outline=color, width=1.5)
        elif icon_type == "sequence":
            # Stacked lines — list icon
            for i in range(3):
                y = p + 3 + i * 4
                canvas.create_line(p + 2, y, s - 2, y, fill=color, width=1.5)
        elif icon_type == "images":
            # Grid of 4 squares
            hs = (s - 4) // 2
            canvas.create_rectangle(p+1, p+1, p+hs, p+hs, outline=color, width=1.5)
            canvas.create_rectangle(s-hs-1, p+1, s-2, p+hs, outline=color, width=1.5)
            canvas.create_rectangle(p+1, s-hs-1, p+hs, s-2, outline=color, width=1.5)
            canvas.create_rectangle(s-hs-1, s-hs-1, s-2, s-2, outline=color, width=1.5)

    def _create_sidebar_btn(self, name):
        # Active glow background frame (shows on active item)
        glow = tk.Frame(self.sidebar, bg=self.BG, cursor="hand2")
        glow.pack(fill=tk.X, pady=1, padx=8)

        # Inner button frame — gets rounded appearance
        btn = tk.Frame(glow, bg=self.BG, cursor="hand2")
        btn.pack(fill=tk.X)

        # Left indicator bar (3px)
        indicator = tk.Frame(btn, bg=self.BG, width=3)
        indicator.pack(side=tk.LEFT, fill=tk.Y, pady=6)
        indicator.pack_propagate(False)

        # Line icon canvas
        icon_type = {"Run Macro": "play", "Macro Sequence": "sequence",
                     "Manage Images": "images"}.get(name, "play")

        icon_canvas = tk.Canvas(btn, width=18, height=16, bg=self.BG,
                                 highlightthickness=0, cursor="hand2")
        icon_canvas.pack(side=tk.LEFT, padx=(14, 6), pady=8)
        self._draw_line_icon(icon_canvas, icon_type, self.TEXT_DIM)

        # Text label
        lbl = tk.Label(btn, text=name, font=("Segoe UI Variable", 11),
                       bg=self.BG, fg=self.TEXT_SEC, cursor="hand2")
        lbl.pack(side=tk.LEFT, padx=(0, 14), pady=8)

        def on_enter(e):
            if self.current_view != name:
                glow.configure(bg=self.BG)
                btn.configure(bg=self.CARD_GLOW)
                lbl.configure(bg=self.CARD_GLOW, fg=self.TEXT)
                icon_canvas.configure(bg=self.CARD_GLOW)
                indicator.configure(bg=self.CARD_GLOW)
                self._draw_line_icon(icon_canvas, icon_type, self.TEXT_SEC)

        def on_leave(e):
            if self.current_view != name:
                glow.configure(bg=self.BG)
                btn.configure(bg=self.BG)
                lbl.configure(bg=self.BG, fg=self.TEXT_SEC)
                icon_canvas.configure(bg=self.BG)
                indicator.configure(bg=self.BG)
                self._draw_line_icon(icon_canvas, icon_type, self.TEXT_DIM)

        def on_click(e):
            self._show_view(name)

        for w in (glow, btn, indicator, lbl, icon_canvas):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

        self.sidebar_buttons[name] = {
            "glow": glow, "frame": btn, "label": lbl,
            "indicator": indicator, "icon": icon_canvas, "icon_type": icon_type
        }

    def _show_view(self, name):
        self.current_view = name
        for v in self.views.values():
            v.pack_forget()

        for b_name, b_dict in self.sidebar_buttons.items():
            icon_type = b_dict["icon_type"]
            if b_name == name:
                b_dict["glow"].configure(bg=self.CARD_GLOW)
                b_dict["frame"].configure(bg=self.CARD_GLOW)
                b_dict["label"].configure(bg=self.CARD_GLOW, fg=self.TEXT,
                                          font=("Segoe UI Variable", 11, "bold"))
                b_dict["indicator"].configure(bg=self.PRIMARY)
                b_dict["icon"].configure(bg=self.CARD_GLOW)
                self._draw_line_icon(b_dict["icon"], icon_type, self.PRIMARY)
                # Add subtle glow border to indicator
                b_dict["glow"].configure(bg=self.PRIMARY_DIM)
            else:
                b_dict["glow"].configure(bg=self.BG)
                b_dict["frame"].configure(bg=self.BG)
                b_dict["label"].configure(bg=self.BG, fg=self.TEXT_SEC,
                                           font=("Segoe UI Variable", 11))
                b_dict["indicator"].configure(bg=self.BG)
                b_dict["icon"].configure(bg=self.BG)
                self._draw_line_icon(b_dict["icon"], icon_type, self.TEXT_DIM)

        if name in self.views:
            self.views[name].pack(fill=tk.BOTH, expand=True, padx=28, pady=24)
            if name == "Macro Sequence":
                self._refresh_sequence_list()
            elif name == "Manage Images":
                self._refresh_image_list()

    # ──────────────────────────────────────────────────────
    #  RUN MACRO VIEW — Premium Polish
    # ──────────────────────────────────────────────────────

    def _build_run_macro_view(self):
        view = tk.Frame(self.main_content, bg=self.BG)
        self.views["Run Macro"] = view

        # ── Title Section (compact) ─────────────────
        title_frame = tk.Frame(view, bg=self.BG)
        title_frame.pack(fill=tk.X, pady=(0, 4))

        tk.Label(title_frame, text="Run Macro",
                 font=("Segoe UI Variable", 22, "bold"),
                 bg=self.BG, fg=self.TEXT).pack(anchor="w")
        tk.Label(title_frame, text="Configure settings and monitor execution.",
                 font=("Segoe UI Variable", 11), bg=self.BG,
                 fg=self.TEXT_SEC).pack(anchor="w", pady=(2, 0))

        # Subtle divider
        tk.Frame(view, bg=self.BORDER_SUBTLE, height=1).pack(fill=tk.X, pady=(10, 18))

        # ── Top Row: Config + Status ─────────────────
        top_row = tk.Frame(view, bg=self.BG)
        top_row.pack(fill=tk.X, pady=(0, 14))
        top_row.columnconfigure(0, weight=5, minsize=400)
        top_row.columnconfigure(1, weight=3, minsize=240)

        # ── Configuration Card ─────────────────────────
        config_shadow = tk.Frame(top_row, bg=self.SHADOW)
        config_shadow.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        config_card = tk.Frame(config_shadow, bg=self.CARD,
                                 highlightthickness=1,
                                 highlightbackground=self.BORDER)
        config_card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # Card header with gear icon
        config_header = tk.Frame(config_card, bg=self.CARD)
        config_header.pack(fill=tk.X, padx=22, pady=(18, 10))

        # Draw a small gear icon
        gear_canvas = tk.Canvas(config_header, width=20, height=20, bg=self.CARD,
                                highlightthickness=0)
        gear_canvas.pack(side=tk.LEFT, padx=(0, 8))
        gc = self.PRIMARY
        # Gear circle + teeth
        gear_canvas.create_oval(3, 3, 17, 17, outline=gc, width=1.5)
        gear_canvas.create_oval(7, 7, 13, 13, outline=gc, width=1.5)
        for angle_x, angle_y in [(10, 1), (10, 19), (1, 10), (19, 10)]:
            gear_canvas.create_line(10, 10, angle_x, angle_y, fill=gc, width=1.5)

        tk.Label(config_header, text="Configuration",
                 font=("Segoe UI Variable", 14, "bold"),
                 bg=self.CARD, fg=self.TEXT).pack(side=tk.LEFT)

        # Configuration fields — compact vertical rhythm
        config_body = tk.Frame(config_card, bg=self.CARD)
        config_body.pack(fill=tk.X, padx=22, pady=(0, 18))

        # ── Scan Area (hidden when click mode is "window") ────────
        self.scan_area_section = tk.Frame(config_body, bg=self.CARD)
        self.scan_area_section.pack(fill=tk.X, pady=(0, 12))

        tk.Label(self.scan_area_section, text="Scan Area",
                 font=("Segoe UI Variable", 10),
                 bg=self.CARD, fg=self.TEXT_SEC).pack(anchor="w", pady=(0, 4))

        scan_row = tk.Frame(self.scan_area_section, bg=self.CARD)
        scan_row.pack(fill=tk.X)

        self.scan_area_dropdown = CustomDropdown(
            scan_row, self.scan_area_var, ("left", "right", "all", "custom"),
            width=14, font=("Segoe UI Variable", 11),
            bg=self.INPUT_BG, fg=self.TEXT, accent=self.PRIMARY,
            border_color=self.INPUT_BORDER)
        self.scan_area_dropdown.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_select_region = tk.Button(
            scan_row, text="Select Region", font=("Segoe UI Variable", 10),
            bg=self.BORDER, fg=self.TEXT_SEC, bd=0, cursor="hand2",
            activebackground="#2A3A50", activeforeground=self.TEXT,
            padx=14, pady=5, command=self._open_region_selector)
        self.btn_select_region.pack(side=tk.LEFT)
        self.btn_select_region.bind("<Enter>",
            lambda e: self.btn_select_region.configure(bg="#2A3A50", fg=self.TEXT))
        self.btn_select_region.bind("<Leave>",
            lambda e: self.btn_select_region.configure(bg=self.BORDER, fg=self.TEXT_SEC))

        # ── Stop After ────────
        self.stop_after_label = tk.Label(config_body, text="Stop After",
                                          font=("Segoe UI Variable", 10),
                                          bg=self.CARD, fg=self.TEXT_SEC)
        self.stop_after_label.pack(anchor="w", pady=(0, 4))
        self.timer_row = tk.Frame(config_body, bg=self.CARD)
        self.timer_row.pack(fill=tk.X, pady=(0, 12))

        timer_border = tk.Frame(self.timer_row, bg=self.INPUT_BORDER)
        timer_border.pack(side=tk.LEFT)
        timer_inner = tk.Frame(timer_border, bg=self.INPUT_BG)
        timer_inner.pack(padx=1, pady=1)
        self.timer_var = tk.StringVar(value="")
        self.timer_entry = tk.Entry(timer_inner, textvariable=self.timer_var, width=6,
                                     font=("Segoe UI Variable", 11), bg=self.INPUT_BG,
                                     fg=self.TEXT, insertbackground=self.TEXT,
                                     bd=0, highlightthickness=0)
        self.timer_entry.pack(side=tk.LEFT, padx=10, pady=6)
        tk.Label(timer_inner, text="min", font=("Segoe UI Variable", 10),
                 bg=self.INPUT_BG, fg=self.TEXT_DIM).pack(side=tk.LEFT, padx=(0, 8))

        self.timer_entry.bind("<FocusIn>",
            lambda e: timer_border.configure(bg=self.INPUT_FOCUS))
        self.timer_entry.bind("<FocusOut>",
            lambda e: timer_border.configure(bg=self.INPUT_BORDER))

        # ── Click Mode ────────
        self._make_config_label(config_body, "Click Mode")
        self.click_mode_dropdown = CustomDropdown(
            config_body, self.click_mode_var,
            ("background", "foreground", "window"),
            width=14, font=("Segoe UI Variable", 11),
            bg=self.INPUT_BG, fg=self.TEXT, accent=self.PRIMARY,
            border_color=self.INPUT_BORDER)
        self.click_mode_dropdown.pack(fill=tk.X, pady=(0, 12), anchor="w")

        # ── Target Window (hidden unless window mode) ──
        self.target_window_frame = tk.Frame(config_body, bg=self.CARD)

        self._make_config_label_inner(self.target_window_frame, "Target Window")
        target_row = tk.Frame(self.target_window_frame, bg=self.CARD)
        target_row.pack(fill=tk.X, pady=(0, 0))

        self.window_var = tk.StringVar(value=state.TARGET_WINDOW_TITLE)
        self.window_dropdown = CustomDropdown(
            target_row, self.window_var, [],
            width=28, font=("Segoe UI Variable", 11),
            bg=self.INPUT_BG, fg=self.TEXT, accent=self.PRIMARY,
            border_color=self.INPUT_BORDER)
        self.window_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        # Refresh button — integrated with dropdown
        self.btn_refresh = tk.Button(
            target_row, text="↻", font=("Segoe UI", 11, "bold"),
            bg=self.INPUT_BG, fg=self.TEXT_SEC, bd=0, cursor="hand2",
            width=2, height=1,
            activebackground=self.PRIMARY_DIM, activeforeground=self.PRIMARY,
            command=self._refresh_windows)
        self.btn_refresh.pack(side=tk.LEFT)
        self.btn_refresh.bind("<Enter>",
            lambda e: self.btn_refresh.configure(bg=self.PRIMARY_DIM, fg=self.PRIMARY))
        self.btn_refresh.bind("<Leave>",
            lambda e: self.btn_refresh.configure(bg=self.INPUT_BG, fg=self.TEXT_SEC))

        self.window_var.trace_add("write", self._on_window_change)
        self.click_mode_var.trace_add("write", self._on_click_mode_change)
        self._on_click_mode_change()
        try:
            self._refresh_windows()
        except Exception:
            pass

        # ── Status Card ─────────────────────────────────
        status_shadow = tk.Frame(top_row, bg=self.SHADOW)
        status_shadow.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        status_card = tk.Frame(status_shadow, bg=self.CARD,
                                 highlightthickness=1,
                                 highlightbackground=self.BORDER)
        status_card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # Status content — vertically centered
        status_center = tk.Frame(status_card, bg=self.CARD)
        status_center.place(relx=0.5, rely=0.40, anchor="center")

        # Progress ring
        self.progress_ring = ProgressRing(status_center, size=108, ring_width=4,
                                           bg_color=self.CARD)
        self.progress_ring.pack(pady=(16, 10))

        # Status text
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(status_center, textvariable=self.status_var,
                                     font=("Segoe UI Variable", 14, "bold"),
                                     bg=self.CARD, fg=self.TEXT_DIM)
        self.status_label.pack()

        # Elapsed timer
        self.timer_display_var = tk.StringVar(value="")
        self.timer_display_label = tk.Label(status_center,
                                            textvariable=self.timer_display_var,
                                            font=("Segoe UI Variable", 26, "bold"),
                                            bg=self.CARD, fg=self.TEXT_DIM)
        self.timer_display_label.pack(pady=(2, 0))

        # Action buttons — equal width, perfectly aligned
        btn_frame = tk.Frame(status_card, bg=self.CARD)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=18, padx=18)

        btn_inner = tk.Frame(btn_frame, bg=self.CARD)
        btn_inner.pack(anchor="center")

        self.start_btn = RoundedButton(
            btn_inner, text="▶  Start Macro",
            bg_color=self.PRIMARY, fg_color="#FFFFFF",
            hover_color=self.PRIMARY_HOVER,
            glow_color="#FF9040",
            command=self._start,
            width=180, height=46, radius=10,
            font=("Segoe UI Variable", 11, "bold"))
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.stop_btn = RoundedButton(
            btn_inner, text="■  Stop",
            bg_color=self.CARD, fg_color=self.TEXT_SEC,
            hover_color="#14203A",
            outline_color=self.BORDER,
            glow_color=self.TEXT_SEC,
            command=self._stop,
            width=120, height=46, radius=10,
            font=("Segoe UI Variable", 11))
        self.stop_btn.pack(side=tk.LEFT)
        self.stop_btn.set_state(tk.DISABLED)

        # ── Execution Log ─────────────────────────────
        log_shadow = tk.Frame(view, bg=self.SHADOW)
        log_shadow.pack(fill=tk.BOTH, expand=True)

        log_card = tk.Frame(log_shadow, bg=self.CARD,
                             highlightthickness=1,
                             highlightbackground=self.BORDER)
        log_card.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # Log header with terminal icon
        log_header = tk.Frame(log_card, bg=self.CARD)
        log_header.pack(fill=tk.X, padx=20, pady=(14, 8))

        log_title_frame = tk.Frame(log_header, bg=self.CARD)
        log_title_frame.pack(side=tk.LEFT)

        log_icon = tk.Canvas(log_title_frame, width=18, height=18, bg=self.CARD,
                              highlightthickness=0)
        log_icon.pack(side=tk.LEFT, padx=(0, 8))
        # Terminal icon: rectangle with > prompt
        log_icon.create_rectangle(1, 2, 17, 16, outline="#5A6B82", width=1.5)
        log_icon.create_line(4, 6, 8, 9, fill=self.SUCCESS, width=1.5)
        log_icon.create_line(4, 9, 10, 9, fill=self.SUCCESS, width=1.5)

        tk.Label(log_title_frame, text="Execution Log",
                 font=("Segoe UI Variable", 13, "bold"),
                 bg=self.CARD, fg=self.TEXT).pack(side=tk.LEFT)

        # Ghost clear button
        clear_btn = tk.Button(log_header, text="Clear",
                               font=("Segoe UI Variable", 9),
                               fg=self.TEXT_DIM, bg=self.CARD, bd=0,
                               activebackground=self.CARD,
                               activeforeground=self.ERROR,
                               cursor="hand2",
                               command=self._clear_log)
        clear_btn.pack(side=tk.RIGHT)
        clear_btn.bind("<Enter>", lambda e: clear_btn.configure(fg=self.ERROR))
        clear_btn.bind("<Leave>", lambda e: clear_btn.configure(fg=self.TEXT_DIM))

        # Terminal-style log area with rounded appearance
        log_frame = tk.Frame(log_card, bg=self.INPUT_BG,
                              highlightthickness=1,
                              highlightbackground=self.BORDER)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        self.log_text = tk.Text(log_frame, font=("Cascadia Code", 10),
                                bg=self.INPUT_BG, fg=self.TEXT,
                                insertbackground=self.TEXT,
                                bd=0, highlightthickness=0,
                                state=tk.DISABLED, wrap=tk.WORD,
                                padx=14, pady=12,
                                spacing1=2, spacing3=2)
        scrollbar = SmoothScrollbar(log_frame, target_canvas=self.log_text)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.log_text.tag_config("success", foreground=self.SUCCESS)
        self.log_text.tag_config("error", foreground=self.ERROR)
        self.log_text.tag_config("warning", foreground=self.WARNING)
        self.log_text.tag_config("info", foreground=self.TEXT_SEC)

        # ── Footer ────────────────────────────────────
        footer = tk.Frame(view, bg=self.BG)
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        footer_inner = tk.Frame(footer, bg=self.BG)
        footer_inner.pack(anchor="center")

        tk.Label(footer_inner, text="Press ", font=("Segoe UI Variable", 10),
                 bg=self.BG, fg=self.TEXT_DIM).pack(side=tk.LEFT)

        # Q key badge
        self.hint_badge = tk.Frame(footer_inner, bg="#0D1829",
                                    highlightbackground="#1E2D42",
                                    highlightthickness=1)
        self.hint_badge.pack(side=tk.LEFT, padx=3)
        self.hint_badge_lbl = tk.Label(self.hint_badge, text="Q",
                                        font=("Segoe UI Variable", 8, "bold"),
                                        bg="#0D1829", fg=self.TEXT, pady=1, padx=5)
        self.hint_badge_lbl.pack()

        tk.Label(footer_inner, text=" to stop the macro  ·  Window mode: works behind other apps",
                 font=("Segoe UI Variable", 10), bg=self.BG,
                 fg=self.TEXT_DIM).pack(side=tk.LEFT)

    def _make_config_label(self, parent, text):
        """Compact label above a form field."""
        tk.Label(parent, text=text, font=("Segoe UI Variable", 10),
                 bg=self.CARD, fg=self.TEXT_SEC).pack(anchor="w", pady=(0, 4))

    def _make_config_label_inner(self, parent, text):
        """Compact label inside a sub-frame."""
        tk.Label(parent, text=text, font=("Segoe UI Variable", 10),
                 bg=self.CARD, fg=self.TEXT_SEC).pack(anchor="w", pady=(0, 4))

    def _open_region_selector(self):
        from src.gui.overlay import RegionSelectorOverlay
        self.root.attributes("-alpha", 0.0)

        def on_select(x, y, w, h):
            state.CUSTOM_REGION = [x, y, w, h]
            self.scan_area_var.set("custom")
            state.save_config()
            self.root.attributes("-alpha", 1.0)
            self._log(f"[+] Region selected and saved parametrically: ({x},{y}, {w}x{h})")

        def on_cancel():
            self.root.attributes("-alpha", 1.0)
            self._log("[-] Region selection cancelled.")

        RegionSelectorOverlay(self.root, on_select, on_cancel)

    # ──────────────────────────────────────────────────────
    #  MACRO SEQUENCE VIEW
    # ──────────────────────────────────────────────────────

    def _build_sequence_view(self):
        view = tk.Frame(self.main_content, bg=self.BG)
        self.views["Macro Sequence"] = view

        header_frame = tk.Frame(view, bg=self.BG)
        header_frame.pack(fill=tk.X, pady=(0, 4))
        tk.Label(header_frame, text="Macro Sequence",
                 font=("Segoe UI Variable", 22, "bold"),
                 bg=self.BG, fg=self.TEXT).pack(anchor="w")
        tk.Label(header_frame, text="Arrange image checks, wait times, and conditions.",
                 font=("Segoe UI Variable", 11), bg=self.BG,
                 fg=self.TEXT_SEC).pack(anchor="w", pady=(2, 0))

        # Notes
        notes = tk.Frame(view, bg=self.BG)
        notes.pack(fill=tk.X, pady=(6, 12))
        tk.Label(notes, text="• Setting Wait to 0.0 forces infinite search until next image is found.",
                 font=("Segoe UI Variable", 9), bg=self.BG, fg=self.TEXT_DIM).pack(anchor="w")
        tk.Label(notes, text="• Skip Next skips the next image if the selected one is not found.",
                 font=("Segoe UI Variable", 9), bg=self.BG, fg=self.TEXT_DIM).pack(anchor="w")

        # Divider
        tk.Frame(view, bg=self.BORDER_SUBTLE, height=1).pack(fill=tk.X, pady=(0, 8))

        # Column headers — fixed-width frames packed RIGHT first, then LEFT, then expand
        list_header = tk.Frame(view, bg="#091320", padx=10, pady=10)
        list_header.pack(fill=tk.X, padx=(0, 6))

        # Right-aligned columns (pack RIGHT first)
        for text, w in [("🗑", 40), ("Skip", 64), ("Double", 64), ("Wait (s)", 74)]:
            col = tk.Frame(list_header, bg="#091320", width=w)
            col.pack_propagate(False)
            col.pack(side=tk.RIGHT, padx=(0, 4))
            tk.Label(col, text=text, font=("Segoe UI Variable", 9, "bold"),
                     bg="#091320", fg="#6B7D94").pack(expand=True)

        # Drag handle column
        drag_col = tk.Frame(list_header, bg="#091320", width=28)
        drag_col.pack_propagate(False)
        drag_col.pack(side=tk.LEFT)

        # Image column (flexible, fills rest)
        img_col = tk.Frame(list_header, bg="#091320")
        img_col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        tk.Label(img_col, text="Image", font=("Segoe UI Variable", 9, "bold"),
                 bg="#091320", fg="#6B7D94").pack(side=tk.LEFT)

        # Scrollable list
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
        self.seq_canvas.bind("<Configure>",
            lambda e: [self.seq_canvas.itemconfig(self.seq_canvas_window, width=e.width),
                       _update_seq_scrollregion()])
        self.seq_canvas_window = self.seq_canvas.create_window((0, 0),
            window=self.seq_scroll_frame, anchor="nw")

    def _refresh_sequence_list(self):
        for widget in self.seq_scroll_frame.winfo_children():
            widget.destroy()
        if not hasattr(self, '_seq_images'):
            self._seq_images = []
        self._seq_images.clear()
        self.seq_skip_vars = []
        self.seq_dc_vars = []

        if not state.MACRO_SEQUENCE:
            tk.Label(self.seq_scroll_frame, text="No sequence steps.",
                     font=("Segoe UI Variable", 11), bg=self.BG,
                     fg=self.TEXT_DIM).pack(pady=32)
            return

        for i, step in enumerate(state.MACRO_SEQUENCE):
            # ── Row card (fixed 58px height per design system) ──
            row_outer = tk.Frame(self.seq_scroll_frame, bg=self.CARD, height=58)
            row_outer.pack_propagate(False)
            row_outer.pack(fill=tk.X, pady=(4, 0))

            row = tk.Frame(row_outer, bg=self.CARD, padx=10,
                           highlightthickness=1, highlightbackground=self.BORDER)

            def on_row_enter(e, r=row, ro=row_outer):
                r.configure(highlightbackground=self.PRIMARY, bg=self.CARD_RAISED)
                ro.configure(bg=self.CARD_RAISED)
            def on_row_leave(e, r=row, ro=row_outer):
                r.configure(highlightbackground=self.BORDER, bg=self.CARD)
                ro.configure(bg=self.CARD)

            row.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

            # ── Right columns (pack RIGHT first, fixed widths matching header) ──

            # Delete column (40px)
            del_col = tk.Frame(row, bg=self.CARD, width=40)
            del_col.pack_propagate(False)
            del_col.pack(side=tk.RIGHT, pady=4)
            del_btn = tk.Button(del_col, text="🗑", font=("Segoe UI Symbol", 10),
                                bg=self.CARD, fg="#7A4A4A", bd=0, cursor="hand2",
                                command=lambda n=step["name"]: self._delete_image(n))
            del_btn.pack(expand=True)
            del_btn.bind("<Enter>", lambda e, b=del_btn, r=row, ro=row_outer:
                         (b.configure(fg=self.ERROR, bg=self.CARD_RAISED),
                          r.configure(highlightbackground=self.PRIMARY),
                          ro.configure(bg=self.CARD_RAISED)))
            del_btn.bind("<Leave>", lambda e, b=del_btn, r=row, ro=row_outer:
                         (b.configure(fg="#7A4A4A", bg=self.CARD),
                          r.configure(highlightbackground=self.BORDER),
                          ro.configure(bg=self.CARD)))

            # Double click column (64px)
            dc_col = tk.Frame(row, bg=self.CARD, width=64)
            dc_col.pack_propagate(False)
            dc_col.pack(side=tk.RIGHT, padx=(0, 4), pady=4)
            dc_var = tk.BooleanVar(value=step.get("double_click", False))
            if not hasattr(self, "seq_dc_vars"):
                self.seq_dc_vars = []
            self.seq_dc_vars.append(dc_var)
            sw_dc = ToggleSwitch(dc_col, dc_var)
            sw_dc.pack(expand=True)
            dc_var.trace_add("write",
                lambda *a, idx=i, v=dc_var: self._update_seq_dc(idx, v))

            # Skip column (64px)
            skip_col = tk.Frame(row, bg=self.CARD, width=64)
            skip_col.pack_propagate(False)
            skip_col.pack(side=tk.RIGHT, padx=(0, 4), pady=4)
            skip_var = tk.BooleanVar(value=step.get("skip_next", False))
            self.seq_skip_vars.append(skip_var)
            sw_skip = ToggleSwitch(skip_col, skip_var)
            sw_skip.pack(expand=True)
            skip_var.trace_add("write",
                lambda *a, idx=i, v=skip_var: self._update_seq_skip(idx, v))

            # Wait column (74px)
            wait_col = tk.Frame(row, bg=self.CARD, width=74)
            wait_col.pack_propagate(False)
            wait_col.pack(side=tk.RIGHT, padx=(0, 4), pady=4)
            wait_var = tk.StringVar(value=str(step.get("wait", 0)))
            wait_border = tk.Frame(wait_col, bg=self.INPUT_BORDER)
            wait_border.pack(expand=True)
            wait_inner = tk.Frame(wait_border, bg=self.INPUT_BG)
            wait_inner.pack(padx=1, pady=1)
            wait_entry = tk.Entry(wait_inner, textvariable=wait_var, width=4,
                                   font=("Cascadia Code", 10),
                                   bg=self.INPUT_BG, fg="#FFFFFF",
                                   insertbackground="#FFFFFF", bd=0, justify="center")
            wait_entry.pack(padx=4, pady=3)
            wait_var.trace_add("write",
                lambda *a, idx=i, v=wait_var: self._update_seq_wait(idx, v))

            def _on_focus_in(e, bf=wait_border, ef=wait_inner, we=wait_entry):
                bf.configure(bg=self.INPUT_FOCUS)
                ef.configure(bg="#0D1825")
                we.configure(bg="#0D1825")
            def _on_focus_out(e, bf=wait_border, ef=wait_inner, we=wait_entry):
                bf.configure(bg=self.INPUT_BORDER)
                ef.configure(bg=self.INPUT_BG)
                we.configure(bg=self.INPUT_BG)
            wait_entry.bind("<FocusIn>", _on_focus_in)
            wait_entry.bind("<FocusOut>", _on_focus_out)

            # ── Left columns ──

            # Drag handle column (28px)
            drag_col = tk.Frame(row, bg=self.CARD, width=28)
            drag_col.pack_propagate(False)
            drag_col.pack(side=tk.LEFT, fill=tk.Y, pady=4)
            drag_lbl = tk.Label(drag_col, text="⠿", font=("Segoe UI", 10),
                                bg=self.CARD, fg=self.TEXT_DIM, cursor="hand2")
            drag_lbl.pack(expand=True)
            drag_lbl.bind("<Enter>", on_row_enter)
            drag_lbl.bind("<Leave>", on_row_leave)

            # Image column (flexible, expand)
            img_col = tk.Frame(row, bg=self.CARD)
            img_col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8), pady=4)

            img_path = os.path.join(IMAGE_DIR, step["name"])
            lbl_preview = tk.Label(img_col, bg=self.BORDER, width=28, height=28)
            if os.path.isfile(img_path):
                try:
                    pil_img = Image.open(img_path)
                    pil_img.thumbnail((28, 28))
                    tk_img = ImageTk.PhotoImage(pil_img)
                    self._seq_images.append(tk_img)
                    lbl_preview.config(image=tk_img, width=0, height=0)
                except Exception:
                    lbl_preview.config(text="Err", fg=self.ERROR)
            lbl_preview.pack(side=tk.LEFT, padx=(0, 10))
            lbl_preview.bind("<Enter>", on_row_enter)
            lbl_preview.bind("<Leave>", on_row_leave)

            name_lbl = tk.Label(img_col, text=step["name"],
                                font=("Segoe UI Variable", 10, "bold"),
                                bg=self.CARD, fg=self.TEXT, anchor="w")
            name_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            name_lbl.bind("<Enter>", on_row_enter)
            name_lbl.bind("<Leave>", on_row_leave)

            row.bind("<Enter>", on_row_enter)
            row.bind("<Leave>", on_row_leave)
            row_outer.bind("<Enter>", on_row_enter)
            row_outer.bind("<Leave>", on_row_leave)

        _bind_mousewheel(self.seq_canvas, self.seq_scroll_frame)
        self.seq_canvas.bind("<MouseWheel>",
            lambda e: self.seq_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    # ──────────────────────────────────────────────────────
    #  MANAGE IMAGES VIEW
    # ──────────────────────────────────────────────────────

    def _build_images_view(self):
        view = tk.Frame(self.main_content, bg=self.BG)
        self.views["Manage Images"] = view

        header = tk.Frame(view, bg=self.BG)
        header.pack(fill=tk.X, pady=(0, 4))
        titles = tk.Frame(header, bg=self.BG)
        titles.pack(side=tk.LEFT)
        tk.Label(titles, text="Manage Images",
                 font=("Segoe UI Variable", 22, "bold"),
                 bg=self.BG, fg=self.TEXT).pack(anchor="w")
        tk.Label(titles, text="Upload and maintain images.",
                 font=("Segoe UI Variable", 11), bg=self.BG,
                 fg=self.TEXT_SEC).pack(anchor="w", pady=(2, 0))

        # Divider
        tk.Frame(view, bg=self.BORDER_SUBTLE, height=1).pack(fill=tk.X, pady=(10, 14))

        RoundedButton(header, text="Add New Image",
                      bg_color=self.PRIMARY, fg_color="#FFF",
                      hover_color=self.PRIMARY_HOVER,
                      command=self._add_new_image,
                      width=130, height=38, radius=10,
                      font=("Segoe UI Variable", 10, "bold")).pack(side=tk.RIGHT)

        btn_row = tk.Frame(header, bg=self.BG)
        btn_row.pack(side=tk.RIGHT, padx=(0, 8))
        RoundedButton(btn_row, text="📸 Capture",
                      bg_color=self.BORDER, fg_color=self.TEXT,
                      hover_color="#2A3A50",
                      command=self._capture_screenshot,
                      width=110, height=38, radius=10,
                      font=("Segoe UI Variable", 10)).pack(side=tk.RIGHT)

        list_container = tk.Frame(view, bg=self.BG)
        list_container.pack(fill=tk.BOTH, expand=True)

        self.img_canvas = tk.Canvas(list_container, bg=self.BG,
                                     highlightthickness=0, bd=0)
        scrollbar = SmoothScrollbar(list_container, target_canvas=self.img_canvas)
        self.img_scroll_frame = tk.Frame(self.img_canvas, bg=self.BG, bd=0)

        def _update_img_scrollregion(e=None):
            w = self.img_scroll_frame.winfo_width()
            h = self.img_scroll_frame.winfo_height()
            ch = self.img_canvas.winfo_height()
            self.img_canvas.configure(scrollregion=(0, 0, w, max(h, ch)))

        self.img_scroll_frame.bind("<Configure>", _update_img_scrollregion)
        self.img_canvas.bind("<Configure>",
            lambda e: [self.img_canvas.itemconfig(self.img_canvas_window, width=e.width),
                       _update_img_scrollregion()])
        self.img_canvas_window = self.img_canvas.create_window((0, 0),
            window=self.img_scroll_frame, anchor="nw")

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.img_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.image_status_labels = {}

    def _refresh_image_list(self):
        for widget in self.img_scroll_frame.winfo_children():
            widget.destroy()
        self.image_status_labels.clear()
        if not hasattr(self, '_grid_images'):
            self._grid_images = []
        self._grid_images.clear()

        def create_action_btn(parent, text, default_fg, hover_fg, command, px):
            btn = tk.Button(parent, text=text, font=("Segoe UI Variable", 10),
                            bg=self.CARD, fg=default_fg,
                            activebackground=self.CARD_RAISED, activeforeground=hover_fg,
                            bd=0, cursor="hand2", command=command)
            btn.bind("<Enter>", lambda e, b=btn, c=hover_fg: b.config(fg=c))
            btn.bind("<Leave>", lambda e, b=btn, c=default_fg: b.config(fg=c))
            btn.pack(side=tk.LEFT, padx=px)
            return btn

        for i, img_name in enumerate(state.IMAGE_FILES):
            card = tk.Frame(self.img_scroll_frame, bg=self.CARD, pady=10, padx=14)
            card.pack(fill=tk.X, pady=(6, 0))

            img_path = os.path.join(IMAGE_DIR, img_name)
            lbl_preview = tk.Label(card, bg=self.BORDER, width=36, height=36)
            if os.path.isfile(img_path):
                try:
                    pil_img = Image.open(img_path)
                    pil_img.thumbnail((36, 36))
                    tk_img = ImageTk.PhotoImage(pil_img)
                    self._grid_images.append(tk_img)
                    lbl_preview.config(image=tk_img, width=0, height=0)
                except Exception:
                    lbl_preview.config(text="Err", fg=self.ERROR)
            lbl_preview.pack(side=tk.LEFT, padx=(0, 14))

            details = tk.Frame(card, bg=self.CARD)
            details.pack(side=tk.LEFT, fill=tk.Y)
            tk.Label(details, text=img_name, font=("Segoe UI Variable", 11, "bold"),
                     bg=self.CARD, fg=self.TEXT).pack(anchor="w")

            status_frame = tk.Frame(details, bg=self.CARD)
            status_frame.pack(fill=tk.X)
            indicator = tk.Canvas(status_frame, width=8, height=8, bg=self.CARD,
                                    highlightthickness=0)
            indicator.pack(side=tk.LEFT, pady=2)
            lbl_status = tk.Label(status_frame, text="Checking...",
                                   font=("Segoe UI Variable", 9),
                                   bg=self.CARD, fg=self.TEXT_SEC)
            lbl_status.pack(side=tk.LEFT, padx=6)
            self.image_status_labels[img_name] = (indicator, lbl_status)

            actions = tk.Frame(card, bg=self.CARD)
            actions.pack(side=tk.RIGHT, fill=tk.Y)
            create_action_btn(actions, "✏ Rename", "#7A8BA0", "#D1D5DB",
                               lambda n=img_name: self._rename_image(n), (0, 12))
            create_action_btn(actions, "🔄 Replace", "#FF8A3D", "#FF9D5C",
                               lambda n=img_name: self._upload_image(n), (0, 12))
            create_action_btn(actions, "🗑 Delete", "#E05252", "#EF4444",
                               lambda n=img_name: self._delete_image(n), (0, 4))

        self._update_image_statuses()
        _bind_mousewheel(self.img_canvas, self.img_scroll_frame)
        self.img_canvas.bind("<MouseWheel>",
            lambda e: self.img_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    # ──────────────────────────────────────────────────────
    #  CORE LOGIC
    # ──────────────────────────────────────────────────────

    def _close_window(self):
        self.stop_event.set()
        self.root.destroy()

    def _check_images(self):
        missing = [n for n in state.IMAGE_FILES
                    if not os.path.isfile(os.path.join(IMAGE_DIR, n))]
        if missing:
            self._log(f"[-] Missing images: {', '.join(missing)}")
        else:
            self._log("[+] All image files found.")

    def _log(self, input_msg):
        def _append(msg=input_msg):
            self.log_text.configure(state=tk.NORMAL)
            timestamp = time.strftime("[%H:%M:%S] ")
            tag = "info"
            icon = "ℹ"
            if msg.startswith("[+]"):
                tag, icon, msg = "success", "✔", msg[3:].strip()
            elif msg.startswith("[-]"):
                tag, icon, msg = "error", "❌", msg[3:].strip()
            elif msg.startswith("[!]"):
                tag, icon, msg = "error", "❌", msg[3:].strip()
            elif msg.startswith("[~]"):
                tag, icon, msg = "warning", "⚠", msg[3:].strip()
            elif msg.startswith("[i]"):
                msg = msg[3:].strip()
            self.log_text.insert(tk.END, f"{timestamp}{icon} {msg}\n", tag)
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
        self.root.after(0, _append)

    def _clear_log(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _on_click_mode_change(self, *args):
        if self.click_mode_var.get() == "window":
            self.scan_area_section.pack_forget()
            self.target_window_frame.pack(fill=tk.X, pady=(0, 0))
        else:
            self.target_window_frame.pack_forget()
            # Re-insert scan area section before Stop After label
            self.scan_area_section.pack(fill=tk.X, pady=(0, 12),
                                        before=self.stop_after_label)

    def _on_window_change(self, *args):
        state.TARGET_WINDOW_TITLE = self.window_var.get()
        state.save_config()

    def _refresh_windows(self):
        from src.engine.background_click import enumerate_windows
        try:
            windows = enumerate_windows()
            titles = [t for _, t in windows]
            self.window_dropdown.configure_values(titles)
            if self.window_var.get() not in titles and titles:
                self.window_var.set("")
        except Exception:
            self.window_dropdown.configure_values([])

    def _start(self):
        if self.macro_thread and self.macro_thread.is_alive():
            return

        if state.CLICK_MODE == "window" and state.TARGET_WINDOW_TITLE:
            from src.engine.background_click import find_window_by_title
            hwnd = find_window_by_title(state.TARGET_WINDOW_TITLE)
            if hwnd:
                state.TARGET_HWND = hwnd
                self._log(f"[+] Target window found: {state.TARGET_WINDOW_TITLE} (HWND {hwnd})")
            else:
                state.TARGET_HWND = None
                self._log(f"[!] Could not find window: {state.TARGET_WINDOW_TITLE}")
                return messagebox.showerror("Window Not Found",
                    f"Could not find window \"{state.TARGET_WINDOW_TITLE}\".\n"
                    "Make sure the application is open, then click ↻ to refresh.")
        else:
            state.TARGET_HWND = None

        ratio = state.SCREEN_RATIO
        area = self.scan_area_var.get()
        t_input = self.timer_var.get().strip()

        self.timer_val = 0
        if t_input:
            try:
                self.timer_val = float(t_input) * 60
            except ValueError:
                return messagebox.showerror("Invalid", "Timer must be valid minutes.")

        self.stop_event.clear()
        self.start_btn.set_state(tk.DISABLED)
        self.stop_btn.set_state(tk.NORMAL)
        self.status_var.set("Running")
        self.status_label.configure(fg=self.WARNING)
        self.progress_ring.set_running(True)
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
        run_macro(self.stop_event, self._log, state.SCREEN_RATIO,
                  self.scan_area_var.get())
        self.root.after(0, self._on_macro_done)

    def _on_macro_done(self):
        self.start_btn.set_state(tk.NORMAL)
        self.stop_btn.set_state(tk.DISABLED)
        self.status_var.set("Stopped")
        self.status_label.configure(fg=self.ERROR)
        self.progress_ring.set_running(False)

    def _stop(self):
        self.stop_event.set()
        self._log("[i] Stopping...")

    def _on_drop(self, files):
        if not files:
            return
        for file_item in files:
            try:
                path = file_item if isinstance(file_item, str) else file_item.decode('utf-8')
            except UnicodeDecodeError:
                path = file_item.decode('gbk', errors='ignore')
            path = os.path.normpath(path)
            if not os.path.isfile(path):
                continue
            ext = os.path.splitext(path)[1].lower()
            if ext not in ['.png', '.jpg', '.jpeg', '.bmp']:
                self._log(f"[-] Dropped file is not a supported image: {path}")
                continue
            original_filename = os.path.basename(path)
            dialog = CustomInputDialog(self.root, "Add Dropped Image", "Filename:",
                                       ok_text="Add", default_value=original_filename)
            new_name = dialog.result
            if not new_name:
                continue
            if not new_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                new_name += ext if ext else ".png"
            if new_name in state.IMAGE_FILES:
                messagebox.showinfo("Exists", f"Image '{new_name}' already exists.")
                continue
            try:
                shutil.copy(path, os.path.join(IMAGE_DIR, new_name))
                state.IMAGE_FILES.append(new_name)
                state.MACRO_SEQUENCE.append({"name": new_name, "wait": 0.5,
                                              "skip_next": False, "double_click": False})
                state.save_config()
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
            return
        new_name = dialog.result
        path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
        if not path:
            return
        if not new_name:
            new_name = os.path.basename(path)
        if not new_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            ext = os.path.splitext(path)[1].lower()
            new_name += ext if ext else ".png"
        if new_name in state.IMAGE_FILES:
            return messagebox.showinfo("Exists", "Already exists.")
        try:
            shutil.copy(path, os.path.join(IMAGE_DIR, new_name))
            state.IMAGE_FILES.append(new_name)
            state.MACRO_SEQUENCE.append({"name": new_name, "wait": 0.5,
                                          "skip_next": False, "double_click": False})
            state.save_config()
            self._log(f"[+] Added target: {new_name}")
            if self.current_view in ["Manage Images", "Macro Sequence"]:
                self._refresh_image_list()
                if self.current_view == "Macro Sequence":
                    self._refresh_sequence_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _capture_screenshot(self):
        from src.gui.overlay import ScreenshotOverlay
        self.root.attributes("-alpha", 0.0)
        self.root.update()

        def on_capture(crop_image, x, y, w, h):
            self.root.attributes("-alpha", 1.0)
            default_name = f"capture_{w}x{h}.png"
            dialog = CustomInputDialog(self.root, "Save Captured Image", "Filename:",
                                       ok_text="Save", default_value=default_name)
            new_name = dialog.result
            if not new_name:
                return
            if not new_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                new_name += ".png"
            if new_name in state.IMAGE_FILES:
                messagebox.showinfo("Exists", f"Image '{new_name}' already exists.")
                return
            try:
                save_path = os.path.join(IMAGE_DIR, new_name)
                crop_image.save(save_path)
                state.IMAGE_FILES.append(new_name)
                state.MACRO_SEQUENCE.append({"name": new_name, "wait": 0.5,
                                              "skip_next": False, "double_click": False})
                state.save_config()
                self._log(f"[+] Captured screenshot as: {new_name} ({w}x{h})")
                if self.current_view in ["Manage Images", "Macro Sequence"]:
                    self._refresh_image_list()
                    if self.current_view == "Macro Sequence":
                        self._refresh_sequence_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save captured image: {e}")

        def on_cancel():
            self.root.attributes("-alpha", 1.0)
            self._log("[-] Screenshot capture cancelled.")

        ScreenshotOverlay(self.root, on_capture, on_cancel)

    def _update_image_statuses(self):
        for img_name, (indicator, label) in self.image_status_labels.items():
            if os.path.isfile(os.path.join(IMAGE_DIR, img_name)):
                indicator.create_oval(1, 1, 7, 7, fill=self.SUCCESS, outline=self.SUCCESS)
                label.config(text="Found", fg=self.SUCCESS)
            else:
                indicator.create_oval(1, 1, 7, 7, fill=self.ERROR, outline=self.ERROR)
                label.config(text="Missing", fg=self.ERROR)

    def _upload_image(self, target_name):
        path = filedialog.askopenfilename(
            filetypes=[("Image", "*.png *.jpg *.jpeg *.bmp")])
        if path:
            try:
                shutil.copy(path, os.path.join(IMAGE_DIR, target_name))
                self._log(f"[+] Replaced {target_name}")
                self._update_image_statuses()
                if self.current_view in ["Manage Images", "Macro Sequence"]:
                    self._refresh_image_list()
                    self._refresh_sequence_list()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _rename_image(self, target):
        dialog = CustomInputDialog(self.root, "Rename Image", "New Filename:",
                                    ok_text="Save", default_value=target)
        new_name = dialog.result
        if not new_name:
            return
        ext = os.path.splitext(target)[1]
        if not new_name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            new_name += ext if ext else ".png"
        if new_name == target:
            return
        if new_name in state.IMAGE_FILES:
            return messagebox.showinfo("Exists", "An image with that name already exists.")
        old_path = os.path.join(IMAGE_DIR, target)
        new_path = os.path.join(IMAGE_DIR, new_name)
        try:
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
            idx = state.IMAGE_FILES.index(target)
            state.IMAGE_FILES[idx] = new_name
            for step in state.MACRO_SEQUENCE:
                if step["name"] == target:
                    step["name"] = new_name
            state.save_config()
            self._log(f"[+] Renamed {target} to {new_name}")
            if self.current_view in ["Manage Images", "Macro Sequence"]:
                self._refresh_image_list()
                if self.current_view == "Macro Sequence":
                    self._refresh_sequence_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename: {e}")

    def _delete_image(self, target):
        try:
            if os.path.isfile(os.path.join(IMAGE_DIR, target)):
                os.remove(os.path.join(IMAGE_DIR, target))
            if target in state.IMAGE_FILES:
                state.IMAGE_FILES.remove(target)
            state.MACRO_SEQUENCE = [s for s in state.MACRO_SEQUENCE if s["name"] != target]
            state.save_config()
            self._log(f"[-] Deleted {target}")
            if self.current_view in ["Manage Images", "Macro Sequence"]:
                self._refresh_image_list()
                self._refresh_sequence_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _move_seq(self, idx, dir):
        nx = idx + dir
        if 0 <= nx < len(state.MACRO_SEQUENCE):
            state.MACRO_SEQUENCE[idx], state.MACRO_SEQUENCE[nx] = \
                state.MACRO_SEQUENCE[nx], state.MACRO_SEQUENCE[idx]
            state.save_config()
            self._refresh_sequence_list()

    def _update_seq_wait(self, idx, var):
        try:
            val = float(var.get())
            if val >= 0:
                state.MACRO_SEQUENCE[idx]["wait"] = val
                state.save_config()
        except ValueError:
            pass

    def _update_seq_skip(self, idx, var):
        state.MACRO_SEQUENCE[idx]["skip_next"] = var.get()
        state.save_config()

    def _update_seq_dc(self, idx, var):
        state.MACRO_SEQUENCE[idx]["double_click"] = var.get()
        state.save_config()