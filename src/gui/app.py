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
from src.gui.components import RoundedButton, ToggleSwitch, SmoothScrollbar, CustomInputDialog, _bind_mousewheel, ShadowCard
from src.engine.macro import run_macro


class MacroApp:
    # Modern light palette inspired by travel-app draft
    BG = "#F5F6FA"
    CARD = "#FFFFFF"
    CARD_BORDER = "#E8E9ED"
    BORDER = "#D1D5DB"
    PRIMARY = "#6C5CE7"
    PRIMARY_HOVER = "#7C6FF0"
    PRIMARY_LIGHT = "#EDE9FE"
    SUCCESS = "#00B894"
    WARNING = "#FDCB6E"
    ERROR = "#E17055"
    TEXT = "#2D3436"
    TEXT_SEC = "#636E72"
    TEXT_LIGHT = "#B2BEC3"

    # Bottom nav
    NAV_BG = "#FFFFFF"
    NAV_ACTIVE = PRIMARY
    NAV_INACTIVE = TEXT_LIGHT
    NAV_HEIGHT = 72

    def __init__(self, root):
        self.root = root
        self.root.title("Visiotask")
        self.root.configure(bg=self.BG)
        self.root.geometry("900x720")
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
            ctypes.windll.user32.ChangeWindowMessageFilterEx(hwnd, 0x0233, 1, None)
            ctypes.windll.user32.ChangeWindowMessageFilterEx(hwnd, 0x0049, 1, None)
        except Exception:
            pass

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

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TCombobox", fieldbackground=self.BG, background=self.CARD, foreground=self.TEXT, bordercolor=self.BORDER, arrowcolor=self.TEXT_SEC, padding=6)
        self.style.map("TCombobox", fieldbackground=[("readonly", self.BG)])

        self.current_tab = "Dashboard"
        self.nav_buttons = {}
        self.tabs = {}

        self._build_ui()
        self._check_images()
        self.root.bind("<Alt-F4>", lambda _event: self._close_window())

    # ── UI Shell ──────────────────────────────────────────────────────────

    def _build_ui(self):
        # Main content area (fills everything above bottom nav)
        self.content_area = tk.Frame(self.root, bg=self.BG)
        self.content_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Bottom navigation bar
        self.nav_bar = tk.Frame(self.root, bg=self.NAV_BG, height=self.NAV_HEIGHT)
        self.nav_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.nav_bar.pack_propagate(False)

        # Top border line for nav bar
        tk.Frame(self.nav_bar, bg=self.CARD_BORDER, height=1).pack(side=tk.TOP, fill=tk.X)

        # Create 3 nav items
        self._create_nav_btn("Dashboard", "🏠", 0)
        self._create_nav_btn("Sequence", "☰", 1)
        self._create_nav_btn("Images", "🖼", 2)

        # Build tab contents
        self._build_dashboard_tab()
        self._build_sequence_tab()
        self._build_images_tab()

        self._show_tab("Dashboard")

    def _create_nav_btn(self, name, icon, col):
        btn = tk.Frame(self.nav_bar, bg=self.NAV_BG, cursor="hand2")
        btn.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        icon_lbl = tk.Label(btn, text=icon, font=("Segoe UI", 18), bg=self.NAV_BG, fg=self.NAV_INACTIVE, cursor="hand2")
        icon_lbl.pack(pady=(10, 0))

        text_lbl = tk.Label(btn, text=name, font=("Segoe UI", 10, "bold"), bg=self.NAV_BG, fg=self.NAV_INACTIVE, cursor="hand2")
        text_lbl.pack(pady=(0, 8))

        # Active indicator dot (hidden by default)
        dot = tk.Frame(btn, bg=self.NAV_BG, width=6, height=6)
        dot.place(relx=0.5, y=4, anchor="n")
        dot_canvas = tk.Canvas(dot, width=6, height=6, bg=self.NAV_BG, highlightthickness=0)
        dot_canvas.pack()
        dot_id = dot_canvas.create_oval(0, 0, 6, 6, fill=self.NAV_ACTIVE, outline="")
        dot_canvas.itemconfig(dot_id, state="hidden")

        def on_enter(e):
            if self.current_tab != name:
                icon_lbl.config(fg=self.TEXT_SEC)
                text_lbl.config(fg=self.TEXT_SEC)

        def on_leave(e):
            if self.current_tab != name:
                icon_lbl.config(fg=self.NAV_INACTIVE)
                text_lbl.config(fg=self.NAV_INACTIVE)

        def on_click(e): self._show_tab(name)

        for w in [btn, icon_lbl, text_lbl]:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

        self.nav_buttons[name] = {
            "frame": btn, "icon": icon_lbl, "label": text_lbl,
            "dot_canvas": dot_canvas, "dot_id": dot_id
        }

    def _show_tab(self, name):
        self.current_tab = name
        for tab in self.tabs.values():
            tab.pack_forget()

        for b_name, b_dict in self.nav_buttons.items():
            if b_name == name:
                b_dict["icon"].config(fg=self.NAV_ACTIVE)
                b_dict["label"].config(fg=self.NAV_ACTIVE)
                b_dict["dot_canvas"].itemconfig(b_dict["dot_id"], state="normal")
            else:
                b_dict["icon"].config(fg=self.NAV_INACTIVE)
                b_dict["label"].config(fg=self.NAV_INACTIVE)
                b_dict["dot_canvas"].itemconfig(b_dict["dot_id"], state="hidden")

        if name in self.tabs:
            self.tabs[name].pack(fill=tk.BOTH, expand=True, padx=24, pady=(24, 0))
            if name == "Sequence": self._refresh_sequence_list()
            elif name == "Images": self._refresh_image_list()

    # ── Dashboard Tab (was Run Macro) ─────────────────────────────────────

    def _build_dashboard_tab(self):
        tab = tk.Frame(self.content_area, bg=self.BG)
        self.tabs["Dashboard"] = tab

        # Scrollable wrapper for dashboard
        canvas = tk.Canvas(tab, bg=self.BG, highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(tab, command=canvas.yview, bg=self.BG, troughcolor=self.CARD, bd=0, highlightthickness=0)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_frame = tk.Frame(canvas, bg=self.BG)
        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def _update_region(e=None):
            canvas.configure(scrollregion=(0, 0, scroll_frame.winfo_width(), scroll_frame.winfo_height()))

        scroll_frame.bind("<Configure>", _update_region)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        _bind_mousewheel(canvas, scroll_frame)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # Greeting
        tk.Label(scroll_frame, text="Hello! 👋", font=("Segoe UI", 28, "bold"), bg=self.BG, fg=self.TEXT).pack(anchor="w")
        tk.Label(scroll_frame, text="Ready to automate your tasks.", font=("Segoe UI", 13), bg=self.BG, fg=self.TEXT_SEC).pack(anchor="w", pady=(0, 20))

        # Config Card
        config_card = ShadowCard(scroll_frame, bg=self.CARD)
        config_card.pack(fill=tk.X, pady=(0, 16))

        tk.Label(config_card.inner, text="Configuration", font=("Segoe UI", 14, "bold"), bg=self.CARD, fg=self.TEXT).pack(anchor="w", padx=20, pady=(16, 12))

        cfg_grid = tk.Frame(config_card.inner, bg=self.CARD)
        cfg_grid.pack(fill=tk.X, padx=20, pady=(0, 16))

        # Scan Area
        tk.Label(cfg_grid, text="Scan area", font=("Segoe UI", 11), bg=self.CARD, fg=self.TEXT_SEC).grid(row=0, column=0, sticky="w", pady=6)
        ttk.Combobox(cfg_grid, textvariable=self.scan_area_var, values=("left", "right", "all", "custom"), state="readonly", width=12, font=("Segoe UI", 10)).grid(row=0, column=1, sticky="w", padx=12, pady=6)
        self.btn_select_region = tk.Button(cfg_grid, text="Select Region", font=("Segoe UI", 9), bg=self.PRIMARY_LIGHT, fg=self.PRIMARY, bd=0, cursor="hand2", command=self._open_region_selector)
        self.btn_select_region.grid(row=0, column=2, sticky="w", padx=(0, 0))

        # Timer
        tk.Label(cfg_grid, text="Stop after", font=("Segoe UI", 11), bg=self.CARD, fg=self.TEXT_SEC).grid(row=1, column=0, sticky="w", pady=6)
        self.timer_var = tk.StringVar(value="")
        timer_frame = tk.Frame(cfg_grid, bg=self.BG, highlightthickness=1, highlightbackground=self.BORDER)
        self.timer_entry = tk.Entry(timer_frame, textvariable=self.timer_var, width=5, font=("Segoe UI", 11), bg=self.BG, fg=self.TEXT, insertbackground=self.TEXT, bd=0)
        self.timer_entry.pack(side=tk.LEFT, padx=6, pady=4)
        tk.Label(timer_frame, text="minutes", font=("Segoe UI", 11), bg=self.BG, fg=self.TEXT_SEC).pack(side=tk.LEFT, padx=(0, 6))
        timer_frame.grid(row=1, column=1, sticky="w", padx=12, pady=6)

        # Click Mode
        tk.Label(cfg_grid, text="Click mode", font=("Segoe UI", 11), bg=self.CARD, fg=self.TEXT_SEC).grid(row=2, column=0, sticky="w", pady=6)
        ttk.Combobox(cfg_grid, textvariable=self.click_mode_var, values=("background", "foreground", "window"), state="readonly", width=12, font=("Segoe UI", 10)).grid(row=2, column=1, sticky="w", padx=12, pady=6)

        # Target Window selector
        self.window_select_frame = tk.Frame(cfg_grid, bg=self.CARD)
        tk.Label(self.window_select_frame, text="Target win", font=("Segoe UI", 11), bg=self.CARD, fg=self.TEXT_SEC).pack(side=tk.LEFT)
        self.window_var = tk.StringVar(value=state.TARGET_WINDOW_TITLE)
        self.window_combo = ttk.Combobox(self.window_select_frame, textvariable=self.window_var, state="readonly", width=24, font=("Segoe UI", 10))
        self.window_combo.pack(side=tk.LEFT, padx=(8, 4))
        self.btn_refresh_windows = tk.Button(self.window_select_frame, text="↻", font=("Segoe UI", 10), bg=self.PRIMARY_LIGHT, fg=self.PRIMARY, bd=0, cursor="hand2", width=3, command=self._refresh_windows)
        self.btn_refresh_windows.pack(side=tk.LEFT, padx=(0, 4))
        self.window_var.trace_add("write", self._on_window_change)
        self.click_mode_var.trace_add("write", self._on_click_mode_change)
        self.window_select_frame.grid(row=3, column=0, columnspan=3, sticky="w", pady=4)
        self._on_click_mode_change()
        try:
            self._refresh_windows()
        except Exception:
            pass

        # Status Card
        status_card = ShadowCard(scroll_frame, bg=self.CARD)
        status_card.pack(fill=tk.X, pady=(0, 16))

        status_inner = tk.Frame(status_card.inner, bg=self.CARD)
        status_inner.pack(fill=tk.X, padx=20, pady=20)

        left_status = tk.Frame(status_inner, bg=self.CARD)
        left_status.pack(side=tk.LEFT, fill=tk.Y)

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(left_status, textvariable=self.status_var, font=("Segoe UI", 16, "bold"), bg=self.CARD, fg=self.TEXT_SEC)
        self.status_label.pack(anchor="w")

        self.timer_display_var = tk.StringVar(value="00:00")
        self.timer_display_label = tk.Label(left_status, textvariable=self.timer_display_var, font=("Consolas", 36, "bold"), bg=self.CARD, fg=self.PRIMARY)
        self.timer_display_label.pack(anchor="w", pady=(4, 0))

        btn_area = tk.Frame(status_inner, bg=self.CARD)
        btn_area.pack(side=tk.RIGHT, fill=tk.Y)

        self.start_btn = RoundedButton(btn_area, text="▶  Start Macro", bg_color=self.PRIMARY, fg_color="#FFF", hover_color=self.PRIMARY_HOVER, command=self._start, width=160, height=48)
        self.start_btn.pack(side=tk.TOP, pady=(0, 8))

        self.stop_btn = RoundedButton(btn_area, text="■  Stop", bg_color=self.CARD, fg_color=self.TEXT, hover_color=self.BORDER, outline_color=self.BORDER, command=self._stop, width=160, height=44)
        self.stop_btn.pack(side=tk.TOP)
        self.stop_btn.set_state(tk.DISABLED)

        # Hint line
        hint_frame = tk.Frame(scroll_frame, bg=self.BG)
        hint_frame.pack(fill=tk.X, pady=(0, 12))
        hint_inner = tk.Frame(hint_frame, bg=self.BG)
        hint_inner.pack(anchor="center")
        self.hint_icon = tk.Label(hint_inner, text="⌨", font=("Segoe UI", 12), bg=self.BG, fg=self.TEXT_SEC)
        self.hint_icon.pack(side=tk.LEFT, padx=(4, 6))
        self.hint_text1 = tk.Label(hint_inner, text="Press", font=("Segoe UI", 10), bg=self.BG, fg=self.TEXT_SEC)
        self.hint_text1.pack(side=tk.LEFT)
        self.hint_badge = tk.Frame(hint_inner, bg=self.PRIMARY, highlightbackground=self.PRIMARY, highlightthickness=1)
        self.hint_badge.pack(side=tk.LEFT, padx=6)
        self.hint_badge_lbl = tk.Label(self.hint_badge, text="Q", font=("Segoe UI", 8, "bold"), bg=self.PRIMARY, fg="#FFFFFF", pady=1, padx=4)
        self.hint_badge_lbl.pack()
        self.hint_text2 = tk.Label(hint_inner, text="to stop the macro  |  Window mode works behind other apps", font=("Segoe UI", 10), bg=self.BG, fg=self.TEXT_SEC)
        self.hint_text2.pack(side=tk.LEFT)

        # Log Card
        log_card = ShadowCard(scroll_frame, bg=self.CARD)
        log_card.pack(fill=tk.BOTH, expand=True, pady=(0, 16))

        log_header = tk.Frame(log_card.inner, bg=self.CARD)
        log_header.pack(fill=tk.X, padx=20, pady=(16, 8))
        tk.Label(log_header, text="Execution Log", font=("Segoe UI", 14, "bold"), bg=self.CARD, fg=self.TEXT).pack(side=tk.LEFT)
        tk.Button(log_header, text="Clear", font=("Segoe UI", 10), fg=self.TEXT_SEC, bg=self.CARD, bd=0, activebackground=self.CARD, activeforeground=self.TEXT, cursor="hand2", command=self._clear_log).pack(side=tk.RIGHT)

        log_frame = tk.Frame(log_card.inner, bg=self.BG)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 16))

        self.log_text = tk.Text(log_frame, font=("Segoe UI", 11), bg=self.BG, fg=self.TEXT, insertbackground=self.TEXT, bd=0, highlightthickness=0, state=tk.DISABLED, wrap=tk.WORD, padx=12, pady=12)
        log_scroll = tk.Scrollbar(log_frame, command=self.log_text.yview, bg=self.BG, troughcolor=self.CARD, bd=0, highlightthickness=0)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.log_text.tag_config("success", foreground=self.SUCCESS)
        self.log_text.tag_config("error", foreground=self.ERROR)
        self.log_text.tag_config("warning", foreground=self.WARNING)
        self.log_text.tag_config("info", foreground=self.TEXT_SEC)

    def _open_region_selector(self):
        from src.gui.overlay import RegionSelectorOverlay
        self.root.attributes("-alpha", 0.0)
        def on_select(x, y, w, h):
            state.CUSTOM_REGION = [x, y, w, h]
            self.scan_area_var.set("custom")
            state.save_config()
            self.root.attributes("-alpha", 1.0)
            self._log(f"[+] Region selected: ({x},{y}, {w}x{h})")
        def on_cancel():
            self.root.attributes("-alpha", 1.0)
            self._log("[-] Region selection cancelled.")
        RegionSelectorOverlay(self.root, on_select, on_cancel)

    # ── Sequence Tab ──────────────────────────────────────────────────────

    def _build_sequence_tab(self):
        tab = tk.Frame(self.content_area, bg=self.BG)
        self.tabs["Sequence"] = tab

        header = tk.Frame(tab, bg=self.BG)
        header.pack(fill=tk.X, pady=(0, 16))
        tk.Label(header, text="Macro Sequence", font=("Segoe UI", 24, "bold"), bg=self.BG, fg=self.TEXT).pack(anchor="w")
        tk.Label(header, text="Arrange image checks, wait times, and conditions.", font=("Segoe UI", 12), bg=self.BG, fg=self.TEXT_SEC).pack(anchor="w")
        tk.Label(header, text="* Wait = 0.0 forces infinite search until the image is found. Skip Next skips the next image if current is not found.", font=("Segoe UI", 9, "italic"), bg=self.BG, fg="#8E96A4").pack(anchor="w", pady=(4, 0))

        list_container = tk.Frame(tab, bg=self.BG)
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
        for widget in self.seq_scroll_frame.winfo_children():
            widget.destroy()

        if not hasattr(self, '_seq_images'):
            self._seq_images = []
        self._seq_images.clear()
        self.seq_skip_vars = []
        self.seq_dc_vars = []

        if not state.MACRO_SEQUENCE:
            empty = tk.Frame(self.seq_scroll_frame, bg=self.BG)
            empty.pack(pady=60)
            tk.Label(empty, text="No steps yet.", font=("Segoe UI", 14), bg=self.BG, fg=self.TEXT_LIGHT).pack()
            tk.Label(empty, text="Add images from the Images tab.", font=("Segoe UI", 11), bg=self.BG, fg=self.TEXT_SEC).pack(pady=(4, 0))
            return

        for i, step in enumerate(state.MACRO_SEQUENCE):
            card = ShadowCard(self.seq_scroll_frame, bg=self.CARD)
            if i > 0:
                card.pack(fill=tk.X, pady=(10, 0))
            else:
                card.pack(fill=tk.X, pady=0)

            # Inner horizontal layout
            inner = tk.Frame(card.inner, bg=self.CARD)
            inner.pack(fill=tk.X, padx=16, pady=12)

            # Reorder buttons
            reorder = tk.Frame(inner, bg=self.CARD)
            reorder.pack(side=tk.LEFT, padx=(0, 8))
            tk.Button(reorder, text="▲", font=("Segoe UI", 8), bg=self.CARD, fg=self.TEXT_SEC, bd=0, cursor="hand2",
                      command=lambda idx=i: self._move_seq(idx, -1), state=tk.NORMAL if i > 0 else tk.DISABLED).pack()
            tk.Button(reorder, text="▼", font=("Segoe UI", 8), bg=self.CARD, fg=self.TEXT_SEC, bd=0, cursor="hand2",
                      command=lambda idx=i: self._move_seq(idx, 1), state=tk.NORMAL if i < len(state.MACRO_SEQUENCE)-1 else tk.DISABLED).pack()

            # Image thumbnail
            img_path = os.path.join(IMAGE_DIR, step["name"])
            lbl_preview = tk.Label(inner, bg=self.BORDER, width=40, height=40)
            if os.path.isfile(img_path):
                try:
                    pil_img = Image.open(img_path)
                    pil_img.thumbnail((40, 40))
                    tk_img = ImageTk.PhotoImage(pil_img)
                    self._seq_images.append(tk_img)
                    lbl_preview.config(image=tk_img, width=0, height=0)
                except Exception:
                    lbl_preview.config(text="Err", fg=self.ERROR)
            lbl_preview.pack(side=tk.LEFT, padx=(0, 12))

            # Info
            info = tk.Frame(inner, bg=self.CARD)
            info.pack(side=tk.LEFT, fill=tk.Y)
            tk.Label(info, text=step["name"], font=("Segoe UI", 12, "bold"), bg=self.CARD, fg=self.TEXT, anchor="w").pack(anchor="w")

            meta = tk.Frame(info, bg=self.CARD)
            meta.pack(anchor="w", pady=(2, 0))
            tk.Label(meta, text=f"Step {i+1}", font=("Segoe UI", 9), bg=self.CARD, fg=self.TEXT_SEC).pack(side=tk.LEFT)
            dot = tk.Label(meta, text=" • ", font=("Segoe UI", 9), bg=self.CARD, fg=self.TEXT_LIGHT)
            dot.pack(side=tk.LEFT)

            # Wait badge
            wait_val = step.get("wait", 0)
            wait_color = self.PRIMARY if wait_val > 0 else self.TEXT_LIGHT
            wait_text = f"{wait_val}s wait"
            if wait_val == 0:
                wait_text = "∞ search"
            wait_badge = tk.Frame(meta, bg=self.PRIMARY_LIGHT if wait_val > 0 else self.BG, padx=6, pady=1)
            wait_badge.pack(side=tk.LEFT)
            tk.Label(wait_badge, text=wait_text, font=("Segoe UI", 9, "bold"), bg=wait_badge["bg"], fg=wait_color).pack()

            # Actions on the right
            actions = tk.Frame(inner, bg=self.CARD)
            actions.pack(side=tk.RIGHT, fill=tk.Y)

            # Wait entry
            wait_frame = tk.Frame(actions, bg=self.CARD, width=70)
            wait_frame.pack_propagate(False)
            wait_frame.pack(side=tk.RIGHT, padx=(8, 0), fill=tk.Y)
            wait_var = tk.StringVar(value=str(wait_val))
            border_frame = tk.Frame(wait_frame, bg=self.CARD_BORDER)
            border_frame.pack(expand=True, pady=4)
            entry_frame = tk.Frame(border_frame, bg="#FFFFFF")
            entry_frame.pack(padx=1, pady=1, fill=tk.BOTH, expand=True)
            wait_entry = tk.Entry(entry_frame, textvariable=wait_var, width=5, font=("Segoe UI", 11, "bold"), bg="#FFFFFF", fg=self.TEXT, insertbackground=self.TEXT, bd=0, justify="center")
            wait_entry.pack(padx=4, pady=4)
            wait_var.trace_add("write", lambda *args, idx=i, v=wait_var: self._update_seq_wait(idx, v))

            def _on_focus_in(e, bf=border_frame, ef=entry_frame, we=wait_entry):
                bf.configure(bg=self.PRIMARY)
            def _on_focus_out(e, bf=border_frame, ef=entry_frame, we=wait_entry):
                bf.configure(bg=self.CARD_BORDER)
            wait_entry.bind("<FocusIn>", _on_focus_in)
            wait_entry.bind("<FocusOut>", _on_focus_out)

            # Skip toggle
            skip_frame = tk.Frame(actions, bg=self.CARD, width=70)
            skip_frame.pack_propagate(False)
            skip_frame.pack(side=tk.RIGHT, padx=8, fill=tk.Y)
            skip_var = tk.BooleanVar(value=step.get("skip_next", False))
            self.seq_skip_vars.append(skip_var)
            sw = ToggleSwitch(skip_frame, skip_var, width=44, height=24)
            sw.pack(expand=True)
            skip_var.trace_add("write", lambda *args, idx=i, v=skip_var: self._update_seq_skip(idx, v))
            tk.Label(actions, text="Skip", font=("Segoe UI", 9), bg=self.CARD, fg=self.TEXT_SEC).pack(side=tk.RIGHT, padx=(0, 4))

            # Double click toggle
            dc_frame = tk.Frame(actions, bg=self.CARD, width=70)
            dc_frame.pack_propagate(False)
            dc_frame.pack(side=tk.RIGHT, padx=8, fill=tk.Y)
            dc_var = tk.BooleanVar(value=step.get("double_click", False))
            self.seq_dc_vars.append(dc_var)
            sw_dc = ToggleSwitch(dc_frame, dc_var, width=44, height=24)
            sw_dc.pack(expand=True)
            dc_var.trace_add("write", lambda *args, idx=i, v=dc_var: self._update_seq_dc(idx, v))
            tk.Label(actions, text="Dbl", font=("Segoe UI", 9), bg=self.CARD, fg=self.TEXT_SEC).pack(side=tk.RIGHT, padx=(0, 4))

            # Delete
            del_btn = tk.Button(actions, text="🗑", font=("Segoe UI Symbol", 14), bg=self.CARD, fg=self.ERROR, bd=0, cursor="hand2",
                                command=lambda n=step["name"]: self._delete_image(n))
            del_btn.pack(side=tk.RIGHT, padx=(12, 0))

        _bind_mousewheel(self.seq_canvas, self.seq_scroll_frame)
        self.seq_canvas.bind("<MouseWheel>", lambda e: self.seq_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    # ── Images Tab ────────────────────────────────────────────────────────

    def _build_images_tab(self):
        tab = tk.Frame(self.content_area, bg=self.BG)
        self.tabs["Images"] = tab

        header = tk.Frame(tab, bg=self.BG)
        header.pack(fill=tk.X, pady=(0, 16))

        titles = tk.Frame(header, bg=self.BG)
        titles.pack(side=tk.LEFT)
        tk.Label(titles, text="Your Images", font=("Segoe UI", 24, "bold"), bg=self.BG, fg=self.TEXT).pack(anchor="w")
        tk.Label(titles, text="Upload and manage target images.", font=("Segoe UI", 12), bg=self.BG, fg=self.TEXT_SEC).pack(anchor="w")

        btn_row = tk.Frame(header, bg=self.BG)
        btn_row.pack(side=tk.RIGHT)
        RoundedButton(btn_row, text="📸  Capture", bg_color=self.BORDER, fg_color=self.TEXT, hover_color="#D1D5DB",
                      command=self._capture_screenshot, width=120, height=40).pack(side=tk.RIGHT, padx=(8, 0))
        RoundedButton(btn_row, text="＋  Add New", bg_color=self.PRIMARY, fg_color="#FFF", hover_color=self.PRIMARY_HOVER,
                      command=self._add_new_image, width=120, height=40).pack(side=tk.RIGHT)

        list_container = tk.Frame(tab, bg=self.BG)
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
        for widget in self.img_scroll_frame.winfo_children():
            widget.destroy()
        self.image_status_labels.clear()

        if not hasattr(self, '_grid_images'):
            self._grid_images = []
        self._grid_images.clear()

        def create_action_btn(parent, text, default_fg, hover_fg, command, px):
            btn = tk.Button(parent, text=text, font=("Segoe UI", 10), bg=self.CARD, fg=default_fg, activebackground=self.CARD, activeforeground=hover_fg, bd=0, cursor="hand2", command=command)
            btn.bind("<Enter>", lambda e, b=btn, c=hover_fg: b.config(fg=c))
            btn.bind("<Leave>", lambda e, b=btn, c=default_fg: b.config(fg=c))
            btn.pack(side=tk.LEFT, padx=px)
            return btn

        if not state.IMAGE_FILES:
            empty = tk.Frame(self.img_scroll_frame, bg=self.BG)
            empty.pack(pady=60)
            tk.Label(empty, text="No images yet.", font=("Segoe UI", 14), bg=self.BG, fg=self.TEXT_LIGHT).pack()
            tk.Label(empty, text="Click Add New or drag & drop images here.", font=("Segoe UI", 11), bg=self.BG, fg=self.TEXT_SEC).pack(pady=(4, 0))
            return

        for i, img_name in enumerate(state.IMAGE_FILES):
            card = ShadowCard(self.img_scroll_frame, bg=self.CARD)
            if i > 0:
                card.pack(fill=tk.X, pady=(10, 0))
            else:
                card.pack(fill=tk.X, pady=0)

            inner = tk.Frame(card.inner, bg=self.CARD)
            inner.pack(fill=tk.X, padx=16, pady=12)

            img_path = os.path.join(IMAGE_DIR, img_name)
            lbl_preview = tk.Label(inner, bg=self.BORDER, width=48, height=48)
            if os.path.isfile(img_path):
                try:
                    pil_img = Image.open(img_path)
                    pil_img.thumbnail((48, 48))
                    tk_img = ImageTk.PhotoImage(pil_img)
                    self._grid_images.append(tk_img)
                    lbl_preview.config(image=tk_img, width=0, height=0)
                except Exception:
                    lbl_preview.config(text="Err", fg=self.ERROR)
            lbl_preview.pack(side=tk.LEFT, padx=(0, 16))

            details = tk.Frame(inner, bg=self.CARD)
            details.pack(side=tk.LEFT, fill=tk.Y)
            tk.Label(details, text=img_name, font=("Segoe UI", 13, "bold"), bg=self.CARD, fg=self.TEXT).pack(anchor="w")

            status_frame = tk.Frame(details, bg=self.CARD)
            status_frame.pack(fill=tk.X, pady=(4, 0))
            indicator = tk.Canvas(status_frame, width=10, height=10, bg=self.CARD, highlightthickness=0)
            indicator.pack(side=tk.LEFT, pady=2)
            lbl_status = tk.Label(status_frame, text="Checking...", font=("Segoe UI", 10), bg=self.CARD, fg=self.TEXT_SEC)
            lbl_status.pack(side=tk.LEFT, padx=6)
            self.image_status_labels[img_name] = (indicator, lbl_status)

            actions = tk.Frame(inner, bg=self.CARD)
            actions.pack(side=tk.RIGHT, fill=tk.Y)
            create_action_btn(actions, "✏ Rename", "#8E96A4", self.TEXT, lambda n=img_name: self._rename_image(n), (0, 14))
            create_action_btn(actions, "🔄 Replace", self.PRIMARY, self.PRIMARY_HOVER, lambda n=img_name: self._upload_image(n), (0, 14))
            create_action_btn(actions, "🗑 Delete", self.ERROR, "#FF7675", lambda n=img_name: self._delete_image(n), (0, 0))

        self._update_image_statuses()

        _bind_mousewheel(self.img_canvas, self.img_scroll_frame)
        self.img_canvas.bind("<MouseWheel>", lambda e: self.img_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    # ── Shared helpers / actions ──────────────────────────────────────────

    def _close_window(self):
        self.stop_event.set()
        self.root.destroy()

    def _check_images(self):
        missing = [n for n in state.IMAGE_FILES if not os.path.isfile(os.path.join(IMAGE_DIR, n))]
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
            self.window_select_frame.grid()
        else:
            self.window_select_frame.grid_remove()

    def _on_window_change(self, *args):
        state.TARGET_WINDOW_TITLE = self.window_var.get()
        state.save_config()

    def _refresh_windows(self):
        from src.engine.background_click import enumerate_windows
        try:
            windows = enumerate_windows()
            titles = [t for _, t in windows]
            self.window_combo["values"] = titles
            if self.window_var.get() not in titles and titles:
                self.window_var.set("")
        except Exception:
            self.window_combo["values"] = []

    def _start(self):
        if self.macro_thread and self.macro_thread.is_alive():
            return

        if state.CLICK_MODE == "window" and state.TARGET_WINDOW_TITLE:
            from src.engine.background_click import find_window_by_title
            hwnd = find_window_by_title(state.TARGET_WINDOW_TITLE)
            if hwnd:
                state.TARGET_HWND = hwnd
                self._log(f"[+] Target window: {state.TARGET_WINDOW_TITLE} (HWND {hwnd})")
            else:
                state.TARGET_HWND = None
                self._log(f"[!] Window not found: {state.TARGET_WINDOW_TITLE}")
                return messagebox.showerror("Window Not Found",
                    f'Could not find "{state.TARGET_WINDOW_TITLE}".\nMake sure the app is open, then click ↻ to refresh.')
        else:
            state.TARGET_HWND = None

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
                if self.current_tab in ["Images", "Sequence"]:
                    self._refresh_image_list()
                    if self.current_tab == "Sequence":
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
            if self.current_tab in ["Images", "Sequence"]:
                self._refresh_image_list()
                if self.current_tab == "Sequence":
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
                self._log(f"[+] Captured screenshot: {new_name} ({w}x{h})")
                if self.current_tab in ["Images", "Sequence"]:
                    self._refresh_image_list()
                    if self.current_tab == "Sequence":
                        self._refresh_sequence_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {e}")

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
                if self.current_tab in ["Images", "Sequence"]:
                    self._refresh_image_list()
                    self._refresh_sequence_list()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _rename_image(self, target):
        dialog = CustomInputDialog(self.root, "Rename Image", "New Filename:", ok_text="Save", default_value=target)
        new_name = dialog.result
        if not new_name:
            return
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
            if self.current_tab in ["Images", "Sequence"]:
                self._refresh_image_list()
                if self.current_tab == "Sequence":
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
            if self.current_tab in ["Images", "Sequence"]:
                self._refresh_image_list()
                self._refresh_sequence_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _move_seq(self, idx, dir):
        nx = idx + dir
        if 0 <= nx < len(state.MACRO_SEQUENCE):
            state.MACRO_SEQUENCE[idx], state.MACRO_SEQUENCE[nx] = state.MACRO_SEQUENCE[nx], state.MACRO_SEQUENCE[idx]
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
