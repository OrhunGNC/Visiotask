import os
import shutil
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import windnd
from src.utils.config import RESOURCE_DIR, IMAGE_DIR
from src.utils.state import state
from src.gui.components import RoundedButton, ToggleSwitch, SmoothScrollbar, CustomInputDialog, _bind_mousewheel
from src.engine.macro import run_macro


class MacroApp:
    # Dark sidebar palette
    SIDEBAR_BG = "#1E1E2D"
    SIDEBAR_HOVER = "#2A2A3D"
    SIDEBAR_ACTIVE_BG = "#2A2A3D"
    # Light main content palette
    BG = "#F5F6FA"
    CARD = "#FFFFFF"
    CARD_BORDER = "#E8E9ED"
    BORDER = "#D1D5DB"
    PRIMARY = "#6C5CE7"
    PRIMARY_HOVER = "#7C6FF0"
    SUCCESS = "#00B894"
    WARNING = "#FDCB6E"
    ERROR = "#E17055"
    TEXT = "#2D3436"
    TEXT_SEC = "#636E72"
    TEXT_LIGHT = "#B2BEC3"

    def __init__(self, root):
        self.root = root
        self.root.title("Visiotask")
        self.root.configure(bg=self.BG)
        self.root.geometry("1000x700")
        self.root.minsize(1000, 700)
        
        icon_path = os.path.join(RESOURCE_DIR, "icon.ico")
        if os.path.exists(icon_path):
            try: self.root.iconbitmap(icon_path)
            except Exception: pass
        
        try:
            import ctypes
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            # Use dark title bar to match the dark sidebar
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
            # Reset HWND when switching away from window mode
            if state.CLICK_MODE != "window":
                state.TARGET_HWND = None
            state.save_config()

        self.scan_area_var.trace_add("write", _on_settings_change)
        self.click_mode_var.trace_add("write", _on_settings_change)
        
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
        self.sidebar = tk.Frame(self.root, bg=self.SIDEBAR_BG, width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        
        brand_frame = tk.Frame(self.sidebar, bg=self.SIDEBAR_BG)
        brand_frame.pack(pady=(24, 32), padx=20, anchor="w", fill=tk.X)
        
        icon_path = os.path.join(RESOURCE_DIR, "icon.ico")
        if os.path.exists(icon_path):
            try:
                pil_icon = Image.open(icon_path).resize((28, 28))
                self._sidebar_icon = ImageTk.PhotoImage(pil_icon)
                tk.Label(brand_frame, image=self._sidebar_icon, bg=self.SIDEBAR_BG).pack(side=tk.LEFT, padx=(0, 10))
            except Exception: pass
            
        tk.Label(brand_frame, text="Visiotask", font=("Segoe UI", 18, "bold"), bg=self.SIDEBAR_BG, fg=self.PRIMARY).pack(side=tk.LEFT)
        
        # Main View
        self.main_content = tk.Frame(self.root, bg=self.BG)
        self.main_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        for name, icon in [("Run Macro", "▶"), ("Macro Sequence", "☰"), ("Manage Images", "🖼")]:
            self._create_sidebar_btn(name, icon)

        self._build_run_macro_view()
        self._build_sequence_view()
        self._build_images_view()
        
        self._show_view("Run Macro")

    def _create_sidebar_btn(self, name, icon=""):
        btn = tk.Frame(self.sidebar, bg=self.SIDEBAR_BG, cursor="hand2")
        btn.pack(fill=tk.X, pady=1, padx=12)
        
        indicator = tk.Frame(btn, bg=self.SIDEBAR_BG, width=3)
        indicator.pack(side=tk.LEFT, fill=tk.Y, pady=8)
        
        if icon:
            icon_lbl = tk.Label(btn, text=icon, font=("Segoe UI", 14), bg=self.SIDEBAR_BG, fg=self.TEXT_LIGHT, cursor="hand2")
            icon_lbl.pack(side=tk.LEFT, padx=(12, 8), pady=10)
        
        lbl = tk.Label(btn, text=name, font=("Segoe UI", 12), bg=self.SIDEBAR_BG, fg=self.TEXT_LIGHT, cursor="hand2")
        lbl.pack(side=tk.LEFT, padx=(0, 16), pady=10)
        
        def on_enter(e):
            if self.current_view != name:
                btn.configure(bg=self.SIDEBAR_HOVER)
                lbl.configure(bg=self.SIDEBAR_HOVER, fg="#FFFFFF")
                indicator.configure(bg=self.SIDEBAR_HOVER)
                if icon: icon_lbl.configure(bg=self.SIDEBAR_HOVER)
                
        def on_leave(e):
            if self.current_view != name:
                btn.configure(bg=self.SIDEBAR_BG)
                lbl.configure(bg=self.SIDEBAR_BG, fg=self.TEXT_LIGHT)
                indicator.configure(bg=self.SIDEBAR_BG)
                if icon: icon_lbl.configure(bg=self.SIDEBAR_BG)
                
        def on_click(e): self._show_view(name)
            
        widgets = [btn, indicator, lbl]
        if icon: widgets.append(icon_lbl)
        for w in widgets:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)
            
        self.sidebar_buttons[name] = {"frame": btn, "label": lbl, "indicator": indicator}
        if icon:
            self.sidebar_buttons[name]["icon"] = icon_lbl

    def _show_view(self, name):
        self.current_view = name
        for v in self.views.values(): v.pack_forget()
        
        for b_name, b_dict in self.sidebar_buttons.items():
            icon_lbl = b_dict.get("icon")
            if b_name == name:
                b_dict["frame"].configure(bg=self.SIDEBAR_HOVER)
                b_dict["label"].configure(bg=self.SIDEBAR_HOVER, fg="#FFFFFF", font=("Segoe UI", 12, "bold"))
                b_dict["indicator"].configure(bg=self.PRIMARY)
                if icon_lbl: icon_lbl.configure(bg=self.SIDEBAR_HOVER, fg="#FFFFFF")
            else:
                b_dict["frame"].configure(bg=self.SIDEBAR_BG)
                b_dict["label"].configure(bg=self.SIDEBAR_BG, fg=self.TEXT_LIGHT, font=("Segoe UI", 12))
                b_dict["indicator"].configure(bg=self.SIDEBAR_BG)
                if icon_lbl: icon_lbl.configure(bg=self.SIDEBAR_BG)
                
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
        
        ttk.Combobox(grid, textvariable=self.scan_area_var, values=("left", "right", "all", "custom"), state="readonly", width=12, font=("Segoe UI", 10)).grid(row=0, column=1, sticky="w", padx=16, pady=8)
        tk.Label(grid, text="Scan area", font=("Segoe UI", 11), bg=self.CARD, fg=self.TEXT_SEC).grid(row=0, column=0, sticky="w")
        
        # Add button for Interactive Region Selection
        self.btn_select_region = tk.Button(grid, text="Select Region", font=("Segoe UI", 9), bg=self.BORDER, fg=self.TEXT, bd=0, cursor="hand2", command=self._open_region_selector)
        self.btn_select_region.grid(row=0, column=2, sticky="w", padx=(0, 16))
        
        self.timer_var = tk.StringVar(value="")
        timer_frame = tk.Frame(grid, bg=self.BG, highlightthickness=1, highlightbackground=self.BORDER)
        self.timer_entry = tk.Entry(timer_frame, textvariable=self.timer_var, width=5, font=("Segoe UI", 11), bg=self.BG, fg=self.TEXT, insertbackground=self.TEXT, bd=0)
        self.timer_entry.pack(side=tk.LEFT, padx=6, pady=4)
        tk.Label(timer_frame, text="minutes", font=("Segoe UI", 11), bg=self.BG, fg=self.TEXT_SEC).pack(side=tk.LEFT, padx=(0, 6))
        timer_frame.grid(row=1, column=1, sticky="w", padx=16, pady=8)
        tk.Label(grid, text="Stop after", font=("Segoe UI", 11), bg=self.CARD, fg=self.TEXT_SEC).grid(row=1, column=0, sticky="w")
        
        # Click Mode: background = no cursor move, foreground = move cursor, window = target specific app
        ttk.Combobox(grid, textvariable=self.click_mode_var, values=("background", "foreground", "window"), state="readonly", width=12, font=("Segoe UI", 10)).grid(row=2, column=1, sticky="w", padx=16, pady=8)
        tk.Label(grid, text="Click mode", font=("Segoe UI", 11), bg=self.CARD, fg=self.TEXT_SEC).grid(row=2, column=0, sticky="w")

        # Target Window selector — only visible when click_mode == "window"
        self.window_select_frame = tk.Frame(grid, bg=self.CARD)
        tk.Label(self.window_select_frame, text="Target win", font=("Segoe UI", 11), bg=self.CARD, fg=self.TEXT_SEC).pack(side=tk.LEFT)
        self.window_var = tk.StringVar(value=state.TARGET_WINDOW_TITLE)
        self.window_combo = ttk.Combobox(self.window_select_frame, textvariable=self.window_var, state="readonly", width=24, font=("Segoe UI", 10))
        self.window_combo.pack(side=tk.LEFT, padx=(8, 4))
        self.btn_refresh_windows = tk.Button(self.window_select_frame, text="↻", font=("Segoe UI", 10), bg=self.BORDER, fg=self.TEXT, bd=0, cursor="hand2", width=3, command=self._refresh_windows)
        self.btn_refresh_windows.pack(side=tk.LEFT, padx=(0, 4))
        self.window_var.trace_add("write", self._on_window_change)
        self.click_mode_var.trace_add("write", self._on_click_mode_change)
        # Place in grid but initially hidden; will be shown when mode == "window"
        self.window_select_frame.grid(row=3, column=0, columnspan=3, sticky="w", padx=(0, 16), pady=4)
        self._on_click_mode_change()  # set initial visibility
        try:
            self._refresh_windows()        # populate window list
        except Exception:
            pass  # Win32 APIs may not be available in all environments

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
        
        self.hint_icon = tk.Label(hint_inner, text="⌨", font=("Segoe UI", 12), bg=self.BG, fg=self.TEXT_SEC)
        self.hint_icon.pack(side=tk.LEFT, padx=(4, 6))
        
        self.hint_text1 = tk.Label(hint_inner, text="Press", font=("Segoe UI", 10), bg=self.BG, fg=self.TEXT_SEC)
        self.hint_text1.pack(side=tk.LEFT)
        
        # Q Key Badge
        self.hint_badge = tk.Frame(hint_inner, bg=self.PRIMARY, highlightbackground=self.PRIMARY, highlightthickness=1)
        self.hint_badge.pack(side=tk.LEFT, padx=6)
        self.hint_badge_lbl = tk.Label(self.hint_badge, text="Q", font=("Segoe UI", 8, "bold"), bg=self.PRIMARY, fg="#FFFFFF", pady=1, padx=4)
        self.hint_badge_lbl.pack()
        
        self.hint_text2 = tk.Label(hint_inner, text="to stop the macro  |  Window mode: works behind other apps", font=("Segoe UI", 10), bg=self.BG, fg=self.TEXT_SEC)
        self.hint_text2.pack(side=tk.LEFT)

        # Log Panel
        log_card = tk.Frame(view, bg=self.CARD, bd=0)
        log_card.pack(fill=tk.BOTH, expand=True)

        log_header = tk.Frame(log_card, bg=self.CARD)
        log_header.pack(fill=tk.X, padx=20, pady=(16, 8))
        tk.Label(log_header, text="Execution Log", font=("Segoe UI", 14, "bold"), bg=self.CARD, fg=self.TEXT).pack(side=tk.LEFT)
        tk.Button(log_header, text="Clear", font=("Segoe UI", 10), fg=self.TEXT_SEC, bg=self.CARD, bd=0, activebackground=self.CARD, activeforeground=self.TEXT, cursor="hand2", command=self._clear_log).pack(side=tk.RIGHT)

        log_frame = tk.Frame(log_card, bg=self.BG)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        self.log_text = tk.Text(log_frame, font=("Segoe UI", 11), bg=self.BG, fg=self.TEXT, insertbackground=self.TEXT, bd=0, highlightthickness=0, state=tk.DISABLED, wrap=tk.WORD, padx=12, pady=12)
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview, bg=self.BG, troughcolor=self.CARD, bd=0, highlightthickness=0)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.log_text.tag_config("success", foreground=self.SUCCESS)
        self.log_text.tag_config("error", foreground=self.ERROR)
        self.log_text.tag_config("warning", foreground=self.WARNING)
        self.log_text.tag_config("info", foreground=self.TEXT_SEC)

    def _open_region_selector(self):
        from src.gui.overlay import RegionSelectorOverlay
        self.root.attributes("-alpha", 0.0) # Hide main window temporarily
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
        tk.Frame(view, bg=self.CARD_BORDER, height=1).pack(fill=tk.X, pady=0)

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
            tk.Label(self.seq_scroll_frame, text="No sequence steps.", font=("Segoe UI", 12), bg=self.BG, fg=self.TEXT_SEC).pack(pady=40)
            return

        for i, step in enumerate(state.MACRO_SEQUENCE):
            card = tk.Frame(self.seq_scroll_frame, bg=self.CARD, pady=8, padx=16)
            if i > 0:
                card.pack(fill=tk.X, pady=(6, 0))
            else:
                card.pack(fill=tk.X, pady=0)
            
            # Hover effect
            def on_enter(e, c=card): c.configure(bg="#F0F1F5")
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
            del_btn.bind("<Enter>", lambda e, btn=del_btn, c=card: [c.configure(bg="#F0F1F5"), btn.configure(bg="#F0F1F5")])
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
            
            border_frame = tk.Frame(wait_frame, bg=self.CARD_BORDER) # clear visible border
            border_frame.pack(expand=True, pady=4)
            
            entry_frame = tk.Frame(border_frame, bg="#FFFFFF")
            entry_frame.pack(padx=1, pady=1, fill=tk.BOTH, expand=True) # 1px simulated geometric border
            
            wait_entry = tk.Entry(entry_frame, textvariable=wait_var, width=5, font=("Segoe UI", 11, "bold"), bg="#FFFFFF", fg=self.TEXT, insertbackground=self.TEXT, bd=0, justify="center")
            wait_entry.pack(padx=4, pady=4)
            wait_var.trace_add("write", lambda *args, idx=i, v=wait_var: self._update_seq_wait(idx, v))
            
            # Allow focus events to cascade entry frame styling correctly
            def _on_focus_in(e, bf=border_frame, ef=entry_frame, we=wait_entry): 
                bf.configure(bg=self.PRIMARY)
                ef.configure(bg="#FFFFFF")
                we.configure(bg="#FFFFFF")
            def _on_focus_out(e, bf=border_frame, ef=entry_frame, we=wait_entry): 
                bf.configure(bg=self.CARD_BORDER)
                ef.configure(bg="#FFFFFF")
                we.configure(bg="#FFFFFF")
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

        # Screenshot capture button
        btn_row = tk.Frame(header, bg=self.BG)
        btn_row.pack(side=tk.RIGHT, padx=(0, 8))
        RoundedButton(btn_row, text="📸 Capture", bg_color=self.BORDER, fg_color=self.TEXT, hover_color="#D1D5DB", command=self._capture_screenshot, width=120, height=40).pack(side=tk.RIGHT)

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
            create_action_btn(actions, "✏ Rename", "#8E96A4", self.TEXT, lambda n=img_name: self._rename_image(n), (0, 16))
            create_action_btn(actions, "🔄 Replace", self.PRIMARY, self.PRIMARY_HOVER, lambda n=img_name: self._upload_image(n), (0, 16))
            create_action_btn(actions, "🗑 Delete", self.ERROR, "#FF7675", lambda n=img_name: self._delete_image(n), (0, 5))

        self._update_image_statuses()
        
        _bind_mousewheel(self.img_canvas, self.img_scroll_frame)
        self.img_canvas.bind("<MouseWheel>", lambda e: self.img_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

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
            self.window_select_frame.grid()
        else:
            self.window_select_frame.grid_remove()

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
            self.window_combo["values"] = titles
            # Preserve current selection if still valid
            if self.window_var.get() not in titles and titles:
                self.window_var.set("")
        except Exception:
            self.window_combo["values"] = []

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
            # Optionally just a warning, but we can auto-allow since we detect it natively, remove hard limit
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
        color = self.TEXT if is_running else self.TEXT_SEC
        badge_bg = self.PRIMARY if is_running else self.BORDER
        badge_border = self.PRIMARY_HOVER if is_running else self.BORDER
        badge_fg = "#FFFFFF" if is_running else self.TEXT
        
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

        # Hide the main window so it doesn't appear in the screenshot
        self.root.attributes("-alpha", 0.0)
        self.root.update()

        def on_capture(crop_image, x, y, w, h):
            self.root.attributes("-alpha", 1.0)
            # Ask the user for a filename
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

