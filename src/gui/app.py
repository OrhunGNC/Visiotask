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
    # Premium dark cyber-industrial palette
    BG = "#060B16"
    CARD = "#0E1628"
    CARD_RAISED = "#111B2E"
    BORDER = "#253044"
    BORDER_SUBTLE = "#1A2538"
    PRIMARY = "#FF7A1A"
    PRIMARY_HOVER = "#FF8C36"
    PRIMARY_DIM = "#3D2500"
    SUCCESS = "#00E676"
    SUCCESS_DIM = "#003D1A"
    WARNING = "#FACC15"
    ERROR = "#EF4444"
    TEXT = "#E5E7EB"
    TEXT_SEC = "#6B7280"
    TEXT_DIM = "#4B5563"

    def __init__(self, root):
        self.root = root
        self.root.title("Visiotask")
        self.root.configure(bg=self.BG)
        self.root.geometry("1100x750")
        self.root.minsize(1100, 750)
        
        icon_path = os.path.join(RESOURCE_DIR, "icon.ico")
        if os.path.exists(icon_path):
            try: self.root.iconbitmap(icon_path)
            except Exception: pass
        
        # Dark title bar on Windows
        try:
            import ctypes
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(2)), 4)
            ctypes.windll.user32.ChangeWindowMessageFilterEx(hwnd, 0x0233, 1, None)  # WM_DROPFILES
            ctypes.windll.user32.ChangeWindowMessageFilterEx(hwnd, 0x0049, 1, None)  # WM_COPYGLOBALDATA
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

        # Perform automatic screen resolution/ratio detection quietly
        w = self.root.winfo_screenwidth()
        h = self.root.winfo_screenheight()
        state.SCREEN_WIDTH = w
        state.SCREEN_HEIGHT = h
        if w > 0 and h > 0:
            import math
            gcd = math.gcd(w, h)
            state.SCREEN_RATIO = f"{w//gcd}:{h//gcd}"
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
        self.root.bind("<Alt-F4>", lambda _event: self._close_window())

    def _build_ui(self):
        # ── Sidebar ──────────────────────────────────────
        self.sidebar = tk.Frame(self.root, bg=self.BG, width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Subtle right separator line
        sep = tk.Frame(self.sidebar, bg=self.BORDER_SUBTLE, width=1)
        sep.place(relx=1, rely=0, relheight=1)

        # Logo area
        brand_frame = tk.Frame(self.sidebar, bg=self.BG)
        brand_frame.pack(pady=(32, 48), padx=24, anchor="w", fill=tk.X)

        icon_path = os.path.join(RESOURCE_DIR, "icon.ico")
        if os.path.exists(icon_path):
            try:
                pil_icon = Image.open(icon_path).resize((30, 30))
                self._sidebar_icon = ImageTk.PhotoImage(pil_icon)
                tk.Label(brand_frame, image=self._sidebar_icon, bg=self.BG).pack(side=tk.LEFT, padx=(0, 10))
            except Exception: pass

        tk.Label(brand_frame, text="Visiotask", font=("Segoe UI Variable", 18, "bold"), bg=self.BG, fg=self.PRIMARY).pack(side=tk.LEFT)

        # Navigation items — only the three specified
        for name in ["Run Macro", "Macro Sequence", "Manage Images"]:
            self._create_sidebar_btn(name)

        # ── Main Content ──────────────────────────────────
        self.main_content = tk.Frame(self.root, bg=self.BG)
        self.main_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self._build_run_macro_view()
        self._build_sequence_view()
        self._build_images_view()
        
        self._show_view("Run Macro")

    def _create_sidebar_btn(self, name):
        btn = tk.Frame(self.sidebar, bg=self.BG, cursor="hand2")
        btn.pack(fill=tk.X, pady=1)

        # Orange left indicator bar
        indicator = tk.Frame(btn, bg=self.BG, width=3)
        indicator.pack(side=tk.LEFT, fill=tk.Y)
        indicator.pack_propagate(False)

        # Icon mapping
        icon_map = {
            "Run Macro": "▶",
            "Macro Sequence": "⟳",
            "Manage Images": "⊞",
        }
        icon_text = icon_map.get(name, "•")

        icon_lbl = tk.Label(btn, text=icon_text, font=("Segoe UI", 11), bg=self.BG, fg=self.TEXT_DIM, cursor="hand2", width=2)
        icon_lbl.pack(side=tk.LEFT, padx=(20, 8))

        lbl = tk.Label(btn, text=name, font=("Segoe UI Variable", 12), bg=self.BG, fg=self.TEXT_SEC, cursor="hand2")
        lbl.pack(side=tk.LEFT, padx=(0, 20), pady=11)

        def on_enter(e):
            if self.current_view != name:
                btn.configure(bg="#0A1525")
                lbl.configure(bg="#0A1525", fg=self.TEXT)
                icon_lbl.configure(bg="#0A1525", fg=self.TEXT_SEC)
                indicator.configure(bg="#253044")

        def on_leave(e):
            if self.current_view != name:
                btn.configure(bg=self.BG)
                lbl.configure(bg=self.BG, fg=self.TEXT_SEC)
                icon_lbl.configure(bg=self.BG, fg=self.TEXT_DIM)
                indicator.configure(bg=self.BG)

        def on_click(e): self._show_view(name)

        for w in (btn, indicator, lbl, icon_lbl):
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)
            
        self.sidebar_buttons[name] = {"frame": btn, "label": lbl, "indicator": indicator, "icon": icon_lbl}

    def _show_view(self, name):
        self.current_view = name
        for v in self.views.values():
            v.pack_forget()
        
        for b_name, b_dict in self.sidebar_buttons.items():
            if b_name == name:
                b_dict["frame"].configure(bg="#0A1525")
                b_dict["label"].configure(bg="#0A1525", fg=self.TEXT, font=("Segoe UI Variable", 12, "bold"))
                b_dict["indicator"].configure(bg=self.PRIMARY)
                b_dict["icon"].configure(bg="#0A1525", fg=self.PRIMARY)
            else:
                b_dict["frame"].configure(bg=self.BG)
                b_dict["label"].configure(bg=self.BG, fg=self.TEXT_SEC, font=("Segoe UI Variable", 12))
                b_dict["indicator"].configure(bg=self.BG)
                b_dict["icon"].configure(bg=self.BG, fg=self.TEXT_DIM)
                
        if name in self.views:
            self.views[name].pack(fill=tk.BOTH, expand=True, padx=36, pady=36)
            if name == "Macro Sequence": self._refresh_sequence_list()
            elif name == "Manage Images": self._refresh_image_list()

    # ═══════════════════════════════════════════════════════════
    #  RUN MACRO VIEW — Premium Redesign
    # ═══════════════════════════════════════════════════════════

    def _build_run_macro_view(self):
        view = tk.Frame(self.main_content, bg=self.BG)
        self.views["Run Macro"] = view

        # ── Title Section ─────────────────────────────
        title_frame = tk.Frame(view, bg=self.BG)
        title_frame.pack(fill=tk.X, pady=(0, 28))

        tk.Label(title_frame, text="Run Macro", font=("Segoe UI Variable", 28, "bold"), bg=self.BG, fg=self.TEXT).pack(anchor="w")
        tk.Label(title_frame, text="Configure settings and monitor execution.", font=("Segoe UI Variable", 12), bg=self.BG, fg=self.TEXT_SEC).pack(anchor="w", pady=(4, 0))

        # ── Top Panels: Config + Status ──────────────
        top_row = tk.Frame(view, bg=self.BG)
        top_row.pack(fill=tk.X, pady=(0, 20))
        top_row.columnconfigure(0, weight=3, minsize=380)
        top_row.columnconfigure(1, weight=2, minsize=260)

        # ── Configuration Card ──────────────────────
        config_card = tk.Frame(top_row, bg=self.CARD, bd=0, highlightthickness=0)
        config_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        # Card header with icon
        config_header = tk.Frame(config_card, bg=self.CARD)
        config_header.pack(fill=tk.X, padx=28, pady=(24, 16))

        icon_canvas = tk.Canvas(config_header, width=28, height=28, bg=self.CARD, highlightthickness=0)
        icon_canvas.pack(side=tk.LEFT, padx=(0, 10))
        # Draw a gear-like icon
        icon_canvas.create_oval(4, 4, 24, 24, outline=self.PRIMARY, width=2)
        icon_canvas.create_line(14, 2, 14, 8, fill=self.PRIMARY, width=2)
        icon_canvas.create_line(14, 20, 14, 26, fill=self.PRIMARY, width=2)
        icon_canvas.create_line(2, 14, 8, 14, fill=self.PRIMARY, width=2)
        icon_canvas.create_line(20, 14, 26, 14, fill=self.PRIMARY, width=2)

        tk.Label(config_header, text="Configuration", font=("Segoe UI Variable", 16, "bold"), bg=self.CARD, fg=self.TEXT).pack(side=tk.LEFT)

        # Configuration fields with vertical rhythm
        config_body = tk.Frame(config_card, bg=self.CARD)
        config_body.pack(fill=tk.X, padx=28, pady=(0, 28))

        # ── Scan Area ────────
        row_scan = tk.Frame(config_body, bg=self.CARD)
        row_scan.pack(fill=tk.X, pady=(0, 16))

        tk.Label(row_scan, text="Scan Area", font=("Segoe UI Variable", 11), bg=self.CARD, fg=self.TEXT_SEC).pack(anchor="w", pady=(0, 6))
        scan_area_row = tk.Frame(row_scan, bg=self.CARD)
        scan_area_row.pack(fill=tk.X)

        self.scan_area_dropdown = CustomDropdown(scan_area_row, self.scan_area_var, ("left", "right", "all", "custom"), width=14, font=("Segoe UI Variable", 11), bg="#0B1120", fg=self.TEXT, accent=self.PRIMARY, border_color="#253044")
        self.scan_area_dropdown.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_select_region = tk.Button(scan_area_row, text="Select Region", font=("Segoe UI Variable", 10), bg=self.BORDER, fg=self.TEXT_SEC, bd=0, cursor="hand2", activebackground="#304563", activeforeground=self.TEXT, padx=16, pady=6, command=self._open_region_selector)
        self.btn_select_region.pack(side=tk.LEFT)

        # Hover effects for Select Region button
        self.btn_select_region.bind("<Enter>", lambda e: self.btn_select_region.configure(bg="#304563", fg=self.TEXT))
        self.btn_select_region.bind("<Leave>", lambda e: self.btn_select_region.configure(bg=self.BORDER, fg=self.TEXT_SEC))

        # ── Stop After (Timer) ────────
        row_timer = tk.Frame(config_body, bg=self.CARD)
        row_timer.pack(fill=tk.X, pady=(0, 16))

        tk.Label(row_timer, text="Stop After", font=("Segoe UI Variable", 11), bg=self.CARD, fg=self.TEXT_SEC).pack(anchor="w", pady=(0, 6))
        timer_row = tk.Frame(row_timer, bg=self.CARD)
        timer_row.pack(fill=tk.X)

        timer_border = tk.Frame(timer_row, bg="#253044", bd=0)
        timer_border.pack(side=tk.LEFT, padx=(0, 8))
        timer_inner = tk.Frame(timer_border, bg="#0B1120")
        timer_inner.pack(padx=1, pady=1)
        self.timer_var = tk.StringVar(value="")
        self.timer_entry = tk.Entry(timer_inner, textvariable=self.timer_var, width=8, font=("Segoe UI Variable", 11), bg="#0B1120", fg=self.TEXT, insertbackground=self.TEXT, bd=0, highlightthickness=0)
        self.timer_entry.pack(side=tk.LEFT, padx=12, pady=8)
        tk.Label(timer_inner, text="minutes", font=("Segoe UI Variable", 10), bg="#0B1120", fg=self.TEXT_SEC).pack(side=tk.LEFT, padx=(0, 10))

        # Focus effects for timer entry
        self.timer_entry.bind("<FocusIn>", lambda e: timer_border.configure(bg=self.PRIMARY))
        self.timer_entry.bind("<FocusOut>", lambda e: timer_border.configure(bg="#253044"))

        # ── Click Mode ────────
        row_click = tk.Frame(config_body, bg=self.CARD)
        row_click.pack(fill=tk.X, pady=(0, 16))

        tk.Label(row_click, text="Click Mode", font=("Segoe UI Variable", 11), bg=self.CARD, fg=self.TEXT_SEC).pack(anchor="w", pady=(0, 6))
        self.click_mode_dropdown = CustomDropdown(row_click, self.click_mode_var, ("background", "foreground", "window"), width=14, font=("Segoe UI Variable", 11), bg="#0B1120", fg=self.TEXT, accent=self.PRIMARY, border_color="#253044")
        self.click_mode_dropdown.pack(anchor="w")

        # ── Target Window ────────
        self.target_window_frame = tk.Frame(config_body, bg=self.CARD)
        # Will be shown/hidden based on click mode

        tk.Label(self.target_window_frame, text="Target Window", font=("Segoe UI Variable", 11), bg=self.CARD, fg=self.TEXT_SEC).pack(anchor="w", pady=(0, 6))
        target_row = tk.Frame(self.target_window_frame, bg=self.CARD)
        target_row.pack(fill=tk.X)

        self.window_var = tk.StringVar(value=state.TARGET_WINDOW_TITLE)
        self.window_dropdown = CustomDropdown(target_row, self.window_var, [], width=28, font=("Segoe UI Variable", 11), bg="#0B1120", fg=self.TEXT, accent=self.PRIMARY, border_color="#253044")
        self.window_dropdown.pack(side=tk.LEFT, padx=(0, 8))

        # Refresh button — square, icon-only style
        self.btn_refresh = tk.Button(target_row, text="↻", font=("Segoe UI", 12, "bold"), bg=self.BORDER, fg=self.TEXT_SEC, bd=0, cursor="hand2", width=3, height=1, activebackground=self.PRIMARY_DIM, activeforeground=self.PRIMARY, command=self._refresh_windows)
        self.btn_refresh.pack(side=tk.LEFT)
        self.btn_refresh.bind("<Enter>", lambda e: self.btn_refresh.configure(bg=self.PRIMARY_DIM, fg=self.PRIMARY))
        self.btn_refresh.bind("<Leave>", lambda e: self.btn_refresh.configure(bg=self.BORDER, fg=self.TEXT_SEC))

        self.window_var.trace_add("write", self._on_window_change)
        self.click_mode_var.trace_add("write", self._on_click_mode_change)
        self._on_click_mode_change()  # set initial visibility
        try:
            self._refresh_windows()  # populate window list
        except Exception:
            pass  # Win32 APIs may not be available in all environments

        # ── Status Card ──────────────────────────────
        status_card = tk.Frame(top_row, bg=self.CARD, bd=0, highlightthickness=0)
        status_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        # Center the content in the status card
        status_inner = tk.Frame(status_card, bg=self.CARD)
        status_inner.place(relx=0.5, rely=0.42, anchor="center")

        # Progress ring
        self.progress_ring = ProgressRing(status_inner, size=130, ring_width=5, bg_color=self.CARD)
        self.progress_ring.pack(pady=(20, 12))

        # Status text
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(status_inner, textvariable=self.status_var, font=("Segoe UI Variable", 16, "bold"), bg=self.CARD, fg=self.TEXT_SEC)
        self.status_label.pack()

        # Elapsed timer
        self.timer_display_var = tk.StringVar(value="")
        self.timer_display_label = tk.Label(status_inner, textvariable=self.timer_display_var, font=("Segoe UI Variable", 28, "bold"), bg=self.CARD, fg=self.TEXT_DIM)
        self.timer_display_label.pack(pady=(4, 0))

        # Action buttons
        btn_frame = tk.Frame(status_card, bg=self.CARD)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=24, padx=24)

        btn_inner = tk.Frame(btn_frame, bg=self.CARD)
        btn_inner.pack(anchor="center")

        self.start_btn = RoundedButton(btn_inner, text="▶  Start Macro", bg_color=self.PRIMARY, fg_color="#FFFFFF", hover_color=self.PRIMARY_HOVER, command=self._start, width=170, height=48, radius=10, font=("Segoe UI Variable", 12, "bold"))
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = RoundedButton(btn_inner, text="■  Stop", bg_color=self.CARD, fg_color=self.TEXT_SEC, hover_color="#1A2237", outline_color=self.BORDER, command=self._stop, width=110, height=48, radius=10, font=("Segoe UI Variable", 12))
        self.stop_btn.pack(side=tk.LEFT)
        self.stop_btn.set_state(tk.DISABLED)

        # ── Execution Log ─────────────────────────────
        log_card = tk.Frame(view, bg=self.CARD, bd=0)
        log_card.pack(fill=tk.BOTH, expand=True)

        log_header = tk.Frame(log_card, bg=self.CARD)
        log_header.pack(fill=tk.X, padx=24, pady=(20, 10))

        # Log title with icon
        log_title_frame = tk.Frame(log_header, bg=self.CARD)
        log_title_frame.pack(side=tk.LEFT)

        log_icon = tk.Canvas(log_title_frame, width=20, height=20, bg=self.CARD, highlightthickness=0)
        log_icon.pack(side=tk.LEFT, padx=(0, 8))
        # Terminal-like icon
        log_icon.create_rectangle(2, 4, 18, 16, outline=self.TEXT_SEC, width=1)
        log_icon.create_line(4, 8, 8, 10, fill=self.SUCCESS, width=1)
        log_icon.create_line(4, 12, 10, 10, fill=self.SUCCESS, width=1)

        tk.Label(log_title_frame, text="Execution Log", font=("Segoe UI Variable", 14, "bold"), bg=self.CARD, fg=self.TEXT).pack(side=tk.LEFT)

        # Clear button aligned right
        clear_btn = tk.Button(log_header, text="Clear", font=("Segoe UI Variable", 10), fg=self.TEXT_SEC, bg=self.CARD, bd=0, activebackground=self.CARD, activeforeground=self.TEXT, cursor="hand2", command=self._clear_log)
        clear_btn.pack(side=tk.RIGHT)
        clear_btn.bind("<Enter>", lambda e: clear_btn.configure(fg=self.ERROR))
        clear_btn.bind("<Leave>", lambda e: clear_btn.configure(fg=self.TEXT_SEC))

        # Terminal-style log area
        log_frame = tk.Frame(log_card, bg="#060B16")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        self.log_text = tk.Text(log_frame, font=("Cascadia Code", 11), bg="#060B16", fg=self.TEXT, insertbackground=self.TEXT, bd=0, highlightthickness=0, state=tk.DISABLED, wrap=tk.WORD, padx=16, pady=14)
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
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(12, 0))

        footer_inner = tk.Frame(footer, bg=self.BG)
        footer_inner.pack(anchor="center")

        tk.Label(footer_inner, text="⌨  Press ", font=("Segoe UI Variable", 10), bg=self.BG, fg="#6B7280").pack(side=tk.LEFT)

        # Q key badge
        self.hint_badge = tk.Frame(footer_inner, bg="#111B2E", highlightbackground="#253044", highlightthickness=1)
        self.hint_badge.pack(side=tk.LEFT, padx=4)
        self.hint_badge_lbl = tk.Label(self.hint_badge, text="Q", font=("Segoe UI Variable", 8, "bold"), bg="#111B2E", fg="#E5E7EB", pady=1, padx=5)
        self.hint_badge_lbl.pack()

        tk.Label(footer_inner, text=" to stop the macro  |  Window mode works behind other apps", font=("Segoe UI Variable", 10), bg=self.BG, fg="#6B7280").pack(side=tk.LEFT)

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

    # ═══════════════════════════════════════════════════════════
    #  MACRO SEQUENCE VIEW
    # ═══════════════════════════════════════════════════════════

    def _build_sequence_view(self):
        view = tk.Frame(self.main_content, bg=self.BG)
        self.views["Macro Sequence"] = view
        
        header_frame = tk.Frame(view, bg=self.BG)
        header_frame.pack(fill=tk.X, pady=(0, 24))
        tk.Label(header_frame, text="Macro Sequence", font=("Segoe UI Variable", 24, "bold"), bg=self.BG, fg=self.TEXT).pack(anchor="w")
        tk.Label(header_frame, text="Arrange image checks, wait times, and conditions.", font=("Segoe UI Variable", 12), bg=self.BG, fg=self.TEXT_SEC).pack(anchor="w")
        tk.Label(header_frame, text="* Setting Wait to 0.0 forces the macro to search infinitely until the next image is found.", font=("Segoe UI Variable", 10, "italic"), bg=self.BG, fg="#6B7280").pack(anchor="w", pady=(4, 0))
        tk.Label(header_frame, text="* Skip Next forces the macro to skip the next image if the selected one is not found.", font=("Segoe UI Variable", 10, "italic"), bg=self.BG, fg="#6B7280").pack(anchor="w", pady=(2, 0))

        # Fixed Column Headers
        list_header_row = tk.Frame(view, bg=self.BG, pady=4, padx=16)
        list_header_row.pack(fill=tk.X, padx=(0, 8))
        
        tk.Label(list_header_row, text="", bg=self.BG, width=3).pack(side=tk.LEFT)
        tk.Label(list_header_row, text="Image", font=("Segoe UI Variable", 10, "bold"), bg=self.BG, fg=self.TEXT_SEC, width=15, anchor="w").pack(side=tk.LEFT, padx=(50, 10))
        
        headers_right = tk.Frame(list_header_row, bg=self.BG)
        headers_right.pack(side=tk.RIGHT)
        
        hd_trash = tk.Frame(headers_right, bg=self.BG, width=40, height=20)
        hd_trash.pack_propagate(False)
        hd_trash.pack(side=tk.RIGHT)

        hd_skip = tk.Frame(headers_right, bg=self.BG, width=80, height=20)
        hd_skip.pack_propagate(False)
        hd_skip.pack(side=tk.RIGHT, padx=10)
        tk.Label(hd_skip, text="Skip Next", font=("Segoe UI Variable", 10, "bold"), bg=self.BG, fg=self.TEXT_SEC).pack(expand=True)

        hd_dc = tk.Frame(headers_right, bg=self.BG, width=70, height=20)
        hd_dc.pack_propagate(False)
        hd_dc.pack(side=tk.RIGHT, padx=10)
        tk.Label(hd_dc, text="Double", font=("Segoe UI Variable", 10, "bold"), bg=self.BG, fg=self.TEXT_SEC).pack(expand=True)

        hd_wait = tk.Frame(headers_right, bg=self.BG, width=80, height=20)
        hd_wait.pack_propagate(False)
        hd_wait.pack(side=tk.RIGHT, padx=(10, 14))
        tk.Label(hd_wait, text="Wait (s)", font=("Segoe UI Variable", 10, "bold"), bg=self.BG, fg=self.TEXT_SEC).pack(expand=True)

        # Subtle separator
        tk.Frame(view, bg=self.BORDER_SUBTLE, height=1).pack(fill=tk.X, pady=0)

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

        if not state.MACRO_SEQUENCE:
            tk.Label(self.seq_scroll_frame, text="No sequence steps.", font=("Segoe UI Variable", 12), bg=self.BG, fg=self.TEXT_SEC).pack(pady=40)
            return

        for i, step in enumerate(state.MACRO_SEQUENCE):
            card = tk.Frame(self.seq_scroll_frame, bg=self.CARD, pady=8, padx=16)
            if i > 0:
                card.pack(fill=tk.X, pady=(6, 0))
            else:
                card.pack(fill=tk.X, pady=0)
            
            # Hover effect
            def on_enter(e, c=card): c.configure(bg=self.CARD_RAISED)
            def on_leave(e, c=card): c.configure(bg=self.CARD)
            card.bind("<Enter>", on_enter)
            card.bind("<Leave>", on_leave)
            
            reorder_frame = tk.Frame(card, bg=self.CARD)
            reorder_frame.pack(side=tk.LEFT)
            reorder_frame.bind("<Enter>", on_enter)
            reorder_frame.bind("<Leave>", on_leave)
            tk.Button(reorder_frame, text="▲", font=("Segoe UI", 8), bg=self.CARD, fg=self.TEXT_SEC, bd=0, cursor="hand2", command=lambda idx=i: self._move_seq(idx, -1), state=tk.NORMAL if i > 0 else tk.DISABLED).pack()
            tk.Button(reorder_frame, text="▼", font=("Segoe UI", 8), bg=self.CARD, fg=self.TEXT_SEC, bd=0, cursor="hand2", command=lambda idx=i: self._move_seq(idx, 1), state=tk.NORMAL if i < len(state.MACRO_SEQUENCE)-1 else tk.DISABLED).pack()

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

            name_lbl = tk.Label(card, text=step["name"], font=("Segoe UI Variable", 11, "bold"), bg=self.CARD, fg=self.TEXT, width=16, anchor="w")
            name_lbl.pack(side=tk.LEFT)
            name_lbl.bind("<Enter>", on_enter)
            name_lbl.bind("<Leave>", on_leave)

            actions = tk.Frame(card, bg=self.CARD)
            actions.pack(side=tk.RIGHT, fill=tk.Y)
            actions.bind("<Enter>", on_enter)
            actions.bind("<Leave>", on_leave)

            # 1. Delete button
            btn_frame = tk.Frame(actions, bg=self.CARD, width=40)
            btn_frame.pack_propagate(False)
            btn_frame.pack(side=tk.RIGHT, fill=tk.Y)
            btn_frame.bind("<Enter>", on_enter)
            btn_frame.bind("<Leave>", on_leave)
            
            del_btn = tk.Button(btn_frame, text="🗑", font=("Segoe UI Symbol", 12), bg=self.CARD, fg=self.ERROR, bd=0, cursor="hand2", command=lambda n=step["name"]: self._delete_image(n))
            del_btn.pack(expand=True)
            del_btn.bind("<Enter>", lambda e, btn=del_btn, c=card: [c.configure(bg=self.CARD_RAISED), btn.configure(bg=self.CARD_RAISED)])
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
            
            border_frame = tk.Frame(wait_frame, bg="#253044")
            border_frame.pack(expand=True, pady=4)
            
            entry_frame = tk.Frame(border_frame, bg="#0B1120")
            entry_frame.pack(padx=1, pady=1, fill=tk.BOTH, expand=True)
            
            wait_entry = tk.Entry(entry_frame, textvariable=wait_var, width=5, font=("Segoe UI Variable", 11, "bold"), bg="#0B1120", fg="#FFFFFF", insertbackground="#FFFFFF", bd=0, justify="center")
            wait_entry.pack(padx=4, pady=4)
            wait_var.trace_add("write", lambda *args, idx=i, v=wait_var: self._update_seq_wait(idx, v))
            
            # Focus effects for wait entry
            def _on_focus_in(e, bf=border_frame, ef=entry_frame, we=wait_entry): 
                bf.configure(bg=self.PRIMARY)
                ef.configure(bg="#152036")
                we.configure(bg="#152036")
            def _on_focus_out(e, bf=border_frame, ef=entry_frame, we=wait_entry): 
                bf.configure(bg="#253044")
                ef.configure(bg="#0B1120")
                we.configure(bg="#0B1120")
            wait_entry.bind("<FocusIn>", _on_focus_in)
            wait_entry.bind("<FocusOut>", _on_focus_out)

        _bind_mousewheel(self.seq_canvas, self.seq_scroll_frame)
        self.seq_canvas.bind("<MouseWheel>", lambda e: self.seq_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    # ═══════════════════════════════════════════════════════════
    #  MANAGE IMAGES VIEW
    # ═══════════════════════════════════════════════════════════

    def _build_images_view(self):
        view = tk.Frame(self.main_content, bg=self.BG)
        self.views["Manage Images"] = view
        
        header = tk.Frame(view, bg=self.BG)
        header.pack(fill=tk.X, pady=(0, 24))
        
        titles = tk.Frame(header, bg=self.BG)
        titles.pack(side=tk.LEFT)
        tk.Label(titles, text="Manage Images", font=("Segoe UI Variable", 24, "bold"), bg=self.BG, fg=self.TEXT).pack(anchor="w")
        tk.Label(titles, text="Upload and maintain images.", font=("Segoe UI Variable", 12), bg=self.BG, fg=self.TEXT_SEC).pack(anchor="w")

        RoundedButton(header, text="Add New Image", bg_color=self.PRIMARY, fg_color="#FFF", hover_color=self.PRIMARY_HOVER, command=self._add_new_image, width=140, height=40).pack(side=tk.RIGHT)

        # Screenshot capture button
        btn_row = tk.Frame(header, bg=self.BG)
        btn_row.pack(side=tk.RIGHT, padx=(0, 8))
        RoundedButton(btn_row, text="📸 Capture", bg_color=self.BORDER, fg_color=self.TEXT, hover_color="#304563", command=self._capture_screenshot, width=120, height=40).pack(side=tk.RIGHT)

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
            btn = tk.Button(parent, text=text, font=("Segoe UI Variable", 10), bg=self.CARD, fg=default_fg, activebackground=self.CARD, activeforeground=hover_fg, bd=0, cursor="hand2", command=command)
            btn.bind("<Enter>", lambda e, b=btn, c=hover_fg: b.config(fg=c))
            btn.bind("<Leave>", lambda e, b=btn, c=default_fg: b.config(fg=c))
            btn.pack(side=tk.LEFT, padx=px)
            return btn

        for i, img_name in enumerate(state.IMAGE_FILES):
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
            tk.Label(details, text=img_name, font=("Segoe UI Variable", 12, "bold"), bg=self.CARD, fg=self.TEXT).pack(anchor="w")
            
            status_frame = tk.Frame(details, bg=self.CARD)
            status_frame.pack(fill=tk.X)
            indicator = tk.Canvas(status_frame, width=10, height=10, bg=self.CARD, highlightthickness=0)
            indicator.pack(side=tk.LEFT, pady=2)
            lbl_status = tk.Label(status_frame, text="Checking...", font=("Segoe UI Variable", 10), bg=self.CARD, fg=self.TEXT_SEC)
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

    # ═══════════════════════════════════════════════════════════
    #  CORE LOGIC
    # ═══════════════════════════════════════════════════════════

    def _close_window(self):
        self.stop_event.set()
        self.root.destroy()

    def _check_images(self):
        missing = [n for n in state.IMAGE_FILES if not os.path.isfile(os.path.join(IMAGE_DIR, n))]
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

    def _on_click_mode_change(self, *args):
        """Show/hide the Target Window selector based on click mode."""
        if self.click_mode_var.get() == "window":
            self.target_window_frame.pack(fill=tk.X, pady=(0, 0))
        else:
            self.target_window_frame.pack_forget()

    def _on_window_change(self, *args):
        """Persist the selected window title to state."""
        state.TARGET_WINDOW_TITLE = self.window_var.get()
        state.save_config()

    def _refresh_windows(self):
        """Populate the target window dropdown with currently visible windows."""
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
        if self.macro_thread and self.macro_thread.is_alive(): return

        # Resolve target window HWND when click_mode == "window"
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
                    f"Make sure the application is open, then click ↻ to refresh the list.")
        else:
            state.TARGET_HWND = None

        ratio = state.SCREEN_RATIO
        area = self.scan_area_var.get()
        t_input = self.timer_var.get().strip()

        if area == "all" and ratio not in ["16:9", "16:10", "16:11"]:
            pass

        self.timer_val = 0
        if t_input:
            try: self.timer_val = float(t_input) * 60
            except ValueError: return messagebox.showerror("Invalid", "Timer must be valid minutes.")

        self.stop_event.clear()
        self.start_btn.set_state(tk.DISABLED)
        self.stop_btn.set_state(tk.NORMAL)
        self.status_var.set("Running")
        self.status_label.configure(fg=self.SUCCESS)
        self.progress_ring.set_running(True)
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
        run_macro(self.stop_event, self._log, state.SCREEN_RATIO, self.scan_area_var.get())
        self.root.after(0, self._on_macro_done)

    def _update_hint_state(self, is_running):
        # Currently not changing footer style on run state — subtle text stays
        pass

    def _on_macro_done(self):
        self.start_btn.set_state(tk.NORMAL)
        self.stop_btn.set_state(tk.DISABLED)
        self.status_var.set("Stopped")
        self.status_label.configure(fg=self.ERROR)
        self.progress_ring.set_running(False)
        self._update_hint_state(False)

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
                
            if not os.path.isfile(path): continue
            
            ext = os.path.splitext(path)[1].lower()
            if ext not in ['.png', '.jpg', '.jpeg', '.bmp']:
                self._log(f"[-] Dropped file is not a supported image: {path}")
                continue
                
            original_filename = os.path.basename(path)
            
            dialog = CustomInputDialog(self.root, "Add Dropped Image", "Filename:", ok_text="Add", default_value=original_filename)
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
                state.MACRO_SEQUENCE.append({"name": new_name, "wait": 0.5, "skip_next": False, "double_click": False})
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
        
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp")])
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
            state.MACRO_SEQUENCE.append({"name": new_name, "wait": 0.5, "skip_next": False, "double_click": False})
            state.save_config()
            self._log(f"[+] Added target: {new_name}")
            if self.current_view in ["Manage Images", "Macro Sequence"]:
                self._refresh_image_list()
                if self.current_view == "Macro Sequence":
                    self._refresh_sequence_list()
        except Exception as e: 
            messagebox.showerror("Error", str(e))

    def _capture_screenshot(self):
        """Open a fullscreen overlay to screenshot and crop a region, then save as template."""
        from src.gui.overlay import ScreenshotOverlay

        self.root.attributes("-alpha", 0.0)
        self.root.update()

        def on_capture(crop_image, x, y, w, h):
            self.root.attributes("-alpha", 1.0)
            default_name = f"capture_{w}x{h}.png"
            dialog = CustomInputDialog(self.root, "Save Captured Image", "Filename:", ok_text="Save", default_value=default_name)
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
                state.MACRO_SEQUENCE.append({"name": new_name, "wait": 0.5, "skip_next": False, "double_click": False})
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
            if os.path.isfile(os.path.join(IMAGE_DIR, target)): os.remove(os.path.join(IMAGE_DIR, target))
            if target in state.IMAGE_FILES: state.IMAGE_FILES.remove(target)
            
            state.MACRO_SEQUENCE = [s for s in state.MACRO_SEQUENCE if s["name"] != target]
            state.save_config()
            self._log(f"[-] Deleted {target}")
            if self.current_view in ["Manage Images", "Macro Sequence"]:
                self._refresh_image_list()
                self._refresh_sequence_list()
        except Exception as e: messagebox.showerror("Error", str(e))

    def _move_seq(self, idx, dir):
        nx = idx + dir
        if 0 <= nx < len(state.MACRO_SEQUENCE):
            state.MACRO_SEQUENCE[idx], state.MACRO_SEQUENCE[nx] = state.MACRO_SEQUENCE[nx], state.MACRO_SEQUENCE[idx]
            state.save_config()
            self._refresh_sequence_list()

    def _update_seq_wait(self, idx, var):
        try:
            val = float(var.get())
            if val >= 0: state.MACRO_SEQUENCE[idx]["wait"] = val; state.save_config()
        except ValueError: pass

    def _update_seq_skip(self, idx, var):
        state.MACRO_SEQUENCE[idx]["skip_next"] = var.get()
        state.save_config()

    def _update_seq_dc(self, idx, var):
        state.MACRO_SEQUENCE[idx]["double_click"] = var.get()
        state.save_config()