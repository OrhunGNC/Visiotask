import tkinter as tk
import math


# ─────────────────────────────────────────────────────────────
#  Premium UI Component Library
# ─────────────────────────────────────────────────────────────

class RoundedButton(tk.Canvas):
    """Premium button with rounded corners, hover glow, and press animation."""

    def __init__(self, parent, text, bg_color, fg_color, hover_color, command,
                 radius=10, font=("Segoe UI Variable", 12, "bold"),
                 width=160, height=46, outline_color=None, glow_color=None, **kwargs):
        super().__init__(parent, bg=parent["bg"], highlightthickness=0,
                         width=width, height=height, **kwargs)
        self.command = command
        self.radius = radius
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.hover_color = hover_color
        self.outline_color = outline_color or bg_color
        self.glow_color = glow_color or hover_color
        self.text = text
        self.font = font
        self.req_width = width
        self.req_height = height
        self.disabled = False
        self._pressed = False

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
        if w < 10 or h < 10:
            return

        color = "#253044" if self.disabled and not self.outline_color else self.bg_color
        out_col = "#253044" if self.disabled else self.outline_color

        self.create_polygon(self._get_points(w, h, self.radius),
                           fill=color, outline=out_col, smooth=True)
        fg = "#6B7280" if self.disabled else self.fg_color
        self.create_text(w / 2, h / 2, text=self.text, fill=fg, font=self.font)

    def _get_points(self, w, h, r):
        w, h = w - 1, h - 1
        return [r, 0, w-r, 0, w, 0, w, r, w, h-r, w, h,
                w-r, h, r, h, 0, h, 0, h-r, 0, r, 0, 0, r, 0]

    def _on_enter(self, event):
        if not self.disabled:
            self._draw_hover()

    def _on_leave(self, event):
        if not self.disabled:
            self._pressed = False
            self._draw()

    def _on_press(self, event):
        if not self.disabled:
            self._pressed = True
            self._draw_pressed()

    def _on_release(self, event):
        if not self.disabled:
            was_pressed = self._pressed
            self._pressed = False
            if was_pressed:
                self._draw_hover()
                if self.command:
                    self.command()

    def _draw_hover(self):
        self.delete("all")
        w = max(self.winfo_width(), self.req_width)
        h = max(self.winfo_height(), self.req_height)
        # Subtle glow outline on hover
        self.create_polygon(self._get_points(w, h, self.radius),
                           fill=self.hover_color, outline=self.glow_color,
                           width=1, smooth=True)
        self.create_text(w / 2, h / 2, text=self.text, fill=self.fg_color, font=self.font)

    def _draw_pressed(self):
        self.delete("all")
        w = max(self.winfo_width(), self.req_width)
        h = max(self.winfo_height(), self.req_height)
        # Slightly darker on press
        self.create_polygon(self._get_points(w, h, self.radius),
                           fill=self.bg_color, outline=self.outline_color,
                           smooth=True)
        self.create_text(w / 2, h / 2 + 1, text=self.text, fill=self.fg_color, font=self.font)


class ToggleSwitch(tk.Canvas):
    def __init__(self, parent, variable, width=50, height=26, **kwargs):
        super().__init__(parent, bg=parent["bg"], highlightthickness=0,
                         width=width, height=height, cursor="hand2", **kwargs)
        self.variable = variable
        self.w = width
        self.h = height
        self.active_bg = "#FF7A1A"
        self.active_hover = "#FFA559"
        self.inactive_bg = "#4B5563"
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

        self.create_arc(0, 0, self.h, self.h, start=90, extent=180, fill=bg, outline=bg)
        self.create_arc(self.w - self.h, 0, self.w, self.h, start=270, extent=180, fill=bg, outline=bg)
        self.create_rectangle(self.h / 2, 0, self.w - self.h / 2, self.h, fill=bg, outline=bg)

        thumb_r = r - 3
        cx = self.w - r if state else r

        self.create_oval(cx - thumb_r, r - thumb_r + 1, cx + thumb_r, r + thumb_r + 1,
                         fill="#0A1020", outline="")
        self.create_oval(cx - thumb_r, r - thumb_r, cx + thumb_r, r + thumb_r,
                         fill=self.thumb_color, outline=self.thumb_color)


class CustomDropdown(tk.Frame):
    """Premium dropdown with dark fill, soft orange hover, and smooth arrow."""

    def __init__(self, parent, variable, values, width=14,
                 font=("Segoe UI Variable", 11),
                 bg="#0A1020", fg="#E5E7EB", accent="#FF7A1A",
                 border_color="#1E2D42", height=6, **kwargs):
        self._bg = bg
        self._fg = fg
        self._accent = accent
        self._border_color = border_color
        self._hover_border = accent
        self._font = font
        self._values = values
        self._variable = variable
        self._is_open = False
        self._popup = None
        self._width_chars = width
        self._list_height = height

        super().__init__(parent, bg=bg, **kwargs)

        # Outer frame for shadow effect
        self._shadow = tk.Frame(self, bg="#050910")
        self._shadow.pack(fill=tk.X, padx=0, pady=0)

        # Main button area with soft rounded corners via highlight
        self._btn_frame = tk.Frame(self._shadow, bg=bg,
                                    highlightthickness=1,
                                    highlightbackground=border_color,
                                    highlightcolor=border_color,
                                    cursor="hand2")
        self._btn_frame.pack(fill=tk.X, padx=1, pady=1)

        self._value_label = tk.Label(self._btn_frame, textvariable=variable,
                                     font=font, bg=bg, fg=fg, anchor="w",
                                     padx=14, pady=7)
        self._value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Arrow icon — smooth chevron
        self._arrow_canvas = tk.Canvas(self._btn_frame, width=20, height=20,
                                         bg=bg, highlightthickness=0, cursor="hand2")
        self._arrow_canvas.pack(side=tk.RIGHT, padx=(0, 10), pady=7)
        self._draw_arrow(filled=False)

        # Bind events
        for w in (self, self._shadow, self._btn_frame, self._value_label, self._arrow_canvas):
            w.bind("<Button-1>", self._toggle)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _draw_arrow(self, filled=False):
        c = self._arrow_canvas
        c.delete("all")
        color = self._accent if filled else "#5A6B82"
        # Smooth chevron
        c.create_polygon(4, 7, 10, 13, 16, 7, fill=color, outline=color, smooth=False)

    def _on_enter(self, event=None):
        self._btn_frame.configure(highlightbackground=self._accent,
                                   highlightcolor=self._accent)

    def _on_leave(self, event=None):
        if not self._is_open:
            self._btn_frame.configure(highlightbackground=self._border_color,
                                       highlightcolor=self._border_color)

    def _toggle(self, event=None):
        if self._is_open:
            self._close_popup()
        else:
            self._open_popup()

    def _open_popup(self):
        self._is_open = True
        self._draw_arrow(filled=True)
        self._btn_frame.configure(highlightbackground=self._accent,
                                   highlightcolor=self._accent)

        self._popup = tk.Toplevel(self)
        self._popup.overrideredirect(True)
        self._popup.attributes("-topmost", True)
        self._popup.configure(bg="#0D1726")

        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self._popup.geometry(f"+{x}+{y}")

        self.update_idletasks()
        btn_width = self.winfo_width()

        # Top separator line
        tk.Frame(self._popup, bg=self._accent, height=1).pack(fill=tk.X)

        for val in self._values:
            row = tk.Frame(self._popup, bg="#0D1726", cursor="hand2")
            row.pack(fill=tk.X)
            lbl = tk.Label(row, text=val, font=self._font, bg="#0D1726",
                           fg=self._fg, anchor="w", padx=16, pady=8)
            lbl.pack(fill=tk.X)

            def _select(v=val):
                self._variable.set(v)
                self._close_popup()

            for w in (row, lbl):
                w.bind("<Button-1>", lambda e, v=val: _select(v))
                w.bind("<Enter>", lambda e, r=row, l=lbl: (
                    r.configure(bg="#14203A"), l.configure(bg="#14203A", fg=self._accent)))
                w.bind("<Leave>", lambda e, r=row, l=lbl: (
                    r.configure(bg="#0D1726"), l.configure(bg="#0D1726", fg=self._fg)))

        self._popup.bind("<FocusOut>", lambda e: self._close_popup())
        self._popup.focus_set()
        self._popup.bind("<Escape>", lambda e: self._close_popup())
        self._click_outside_id = self.bind_all("<Button-1>", self._on_click_outside, add="+")

    def _on_click_outside(self, event):
        if self._popup and self._popup.winfo_exists():
            try:
                px = self._popup.winfo_rootx()
                py = self._popup.winfo_rooty()
                pw = self._popup.winfo_width()
                ph = self._popup.winfo_height()
                ex, ey = event.x_root, event.y_root
                if not (px <= ex <= px + pw and py <= ey <= py + ph):
                    bx = self.winfo_rootx()
                    by = self.winfo_rooty()
                    bw = self.winfo_width()
                    bh = self.winfo_height()
                    if not (bx <= ex <= bx + bw and by <= ey <= by + bh):
                        self._close_popup()
            except tk.TclError:
                self._close_popup()

    def _close_popup(self):
        self._is_open = False
        self._draw_arrow(filled=False)
        self._btn_frame.configure(highlightbackground=self._border_color,
                                   highlightcolor=self._border_color)
        try:
            self.unbind_all("<Button-1>", self._click_outside_id)
        except Exception:
            pass
        try:
            self.unbind_all("<Button-1>")
        except Exception:
            pass
        if self._popup and self._popup.winfo_exists():
            self._popup.destroy()
        self._popup = None

    def configure_values(self, values):
        self._values = values

    def configure(self, **kwargs):
        if "values" in kwargs:
            self._values = kwargs.pop("values")
        if "state" in kwargs:
            state = kwargs.pop("state")
            if state in ("readonly", tk.DISABLED):
                self._btn_frame.configure(cursor="")
        super().configure(**kwargs)


class ProgressRing(tk.Canvas):
    """Animated circular progress ring with pulsing glow and play icon.
    States: idle (dim), running (yellow pulse), stopped (red)."""

    # Ring states
    STATE_IDLE = "idle"
    STATE_RUNNING = "running"
    STATE_STOPPED = "stopped"

    def __init__(self, parent, size=120, ring_width=5, bg_color="#0B1322",
                 **kwargs):
        super().__init__(parent, width=size, height=size, bg=bg_color,
                         highlightthickness=0, **kwargs)
        self._size = size
        self._ring_width = ring_width
        self._bg_color = bg_color
        self._ring_state = self.STATE_IDLE
        self._ring_color = "#FACC15"  # default running color
        self._pulse_phase = 0
        self._pulse_after_id = None
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self._size
        cx, cy = s / 2, s / 2
        r = (s / 2) - self._ring_width - 10

        is_running = self._ring_state == self.STATE_RUNNING
        is_stopped = self._ring_state == self.STATE_STOPPED

        # Outer glow rings when running
        if is_running:
            for offset, stipple in [(8, "gray12"), (5, "gray25"), (3, "gray50")]:
                glow_r = r + offset
                self.create_oval(cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r,
                                 outline=self._ring_color, width=1, stipple=stipple)

        # Background track
        track_color = "#172240"
        self.create_oval(cx - r, cy - r, cx + r, cy + r,
                         outline=track_color, width=self._ring_width + 1)

        # Active / stopped ring
        if is_running:
            self.create_oval(cx - r, cy - r, cx + r, cy + r,
                             outline=self._ring_color, width=self._ring_width + 2)
        elif is_stopped:
            self.create_oval(cx - r, cy - r, cx + r, cy + r,
                             outline="#EF4444", width=self._ring_width + 2)
        else:
            # Idle: dim dashed ring
            self.create_oval(cx - r, cy - r, cx + r, cy + r,
                             outline="#1E3050", width=self._ring_width)

        # Center icon — play triangle
        points = [cx - 7, cy - 10, cx - 7, cy + 10, cx + 11, cy]
        if is_running:
            self.create_polygon(points, fill="#FFFFFF", outline="#FFFFFF")
        elif is_stopped:
            # Red play icon when stopped
            self.create_polygon(points, fill="#EF4444", outline="#EF4444")
        else:
            # Muted play icon when idle
            self.create_polygon(points, fill="#3A4D66", outline="#3A4D66")

    def set_running(self, running):
        """Set ring state. True = running (yellow), False = stopped (red)."""
        self._ring_state = self.STATE_RUNNING if running else self.STATE_STOPPED
        self._draw()
        if running:
            self._start_pulse()
        else:
            self._stop_pulse()

    def set_idle(self):
        """Reset ring to idle (dim) state."""
        self._ring_state = self.STATE_IDLE
        self._stop_pulse()

    def _start_pulse(self):
        self._stop_pulse()
        self._pulse_phase = 0
        self._pulse_tick()

    def _pulse_tick(self):
        if self._ring_state != self.STATE_RUNNING:
            return
        self._pulse_phase = (self._pulse_phase + 1) % 40
        self._draw()

        # Intensity cycling for amber/yellow neon glow
        if self._pulse_phase < 13:
            self._ring_color = "#FACC15"
        elif self._pulse_phase < 26:
            self._ring_color = "#E5A80D"
        else:
            self._ring_color = "#FFD84D"

        self._pulse_after_id = self.after(70, self._pulse_tick)

    def _stop_pulse(self):
        if self._pulse_after_id:
            try:
                self.after_cancel(self._pulse_after_id)
            except Exception:
                pass
            self._pulse_after_id = None
        self._ring_color = "#FACC15"
        if self._ring_state != self.STATE_STOPPED:
            self._ring_state = self.STATE_IDLE
        self._draw()


class SmoothScrollbar(tk.Canvas):
    def __init__(self, parent, target_canvas, width=6, **kwargs):
        super().__init__(parent, bg="#060B16", highlightthickness=0, width=width, **kwargs)
        self.target = target_canvas
        self.thumb_color = "#1E2D42"
        self.hover_color = "#2D4060"
        self.track_id = self.create_rectangle(0, 0, width, 0, fill="#0A1220", outline="")
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
        self.coords(self.track_id, 1, 0, w - 1, h)
        self.coords(self.thumb_id, 1, h * self.first, w - 1, h * self.last)

    def _on_enter(self, e):
        self._hovered = True
        self.itemconfig(self.thumb_id, fill=self.hover_color)

    def _on_leave(self, e):
        self._hovered = False
        self.itemconfig(self.thumb_id, fill=self.thumb_color)

    def _on_click(self, e):
        h = self.winfo_height()
        if h == 0:
            return
        fraction = e.y / h
        if fraction < self.first or fraction > self.last:
            self.target.yview_moveto(fraction - (self.last - self.first) / 2)
        self._drag_y = e.y
        self._drag_start_first = float(self.first)

    def _on_drag(self, e):
        h = self.winfo_height()
        if h == 0:
            return
        dy = e.y - self._drag_y
        self.target.yview_moveto(self._drag_start_first + (dy / h))


class CustomInputDialog(tk.Toplevel):
    def __init__(self, parent, title_text, label_text, ok_text="Add Image", default_value=""):
        super().__init__(parent)
        self.result = None
        self.overrideredirect(True)
        self.configure(bg="#1E2D42")

        w, h = 440, 260
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.transient(parent)
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()

        # Shadow layer
        main_frame = tk.Frame(self, bg="#0B1322")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

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

        lbl_title = tk.Label(main_frame, text=title_text,
                              font=("Segoe UI Variable", 17, "bold"),
                              bg="#0B1322", fg="#E5E7EB")
        lbl_title.pack(anchor="w", padx=28, pady=(22, 14))
        lbl_title.bind("<ButtonPress-1>", _on_drag_start)
        lbl_title.bind("<B1-Motion>", _on_drag_motion)

        tk.Label(main_frame, text=label_text, font=("Segoe UI Variable", 11),
                 bg="#0B1322", fg="#9CA3AF").pack(anchor="w", padx=28)

        # Input with orange focus border
        self._input_border = tk.Frame(main_frame, bg="#1E2D42")
        self._input_border.pack(fill=tk.X, padx=28, pady=(8, 4))
        self._input_inner = tk.Frame(self._input_border, bg="#080E1A")
        self._input_inner.pack(fill=tk.X, padx=1, pady=1)

        self.entry_var = tk.StringVar(value=default_value)
        self.entry = tk.Entry(self._input_inner, textvariable=self.entry_var,
                              font=("Segoe UI Variable", 12), bg="#080E1A", fg="#E5E7EB",
                              insertbackground="#E5E7EB", bd=0, highlightthickness=0)
        self.entry.pack(fill=tk.X, padx=12, pady=9)
        self.entry.bind("<Return>", lambda e: self._on_submit())
        self.entry.bind("<FocusIn>", lambda e: self._input_border.configure(bg="#FF7A1A"))
        self.entry.bind("<FocusOut>", lambda e: self._input_border.configure(bg="#1E2D42"))

        tk.Label(main_frame, text="e.g. icon.png", font=("Segoe UI Variable", 9),
                  bg="#0B1322", fg="#4B5563").pack(anchor="w", padx=28)

        btn_frame = tk.Frame(main_frame, bg="#0B1322")
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=28, pady=(8, 22))

        self.btn_submit = RoundedButton(btn_frame, ok_text,
                                         bg_color="#FF7A1A", fg_color="#FFFFFF",
                                         hover_color="#FF8C36",
                                         command=self._on_submit,
                                         width=110, height=40, radius=10,
                                         font=("Segoe UI Variable", 11, "bold"))
        self.btn_submit.pack(side=tk.RIGHT)

        self.btn_cancel = RoundedButton(btn_frame, "Cancel",
                                         bg_color="#0B1322", fg_color="#9CA3AF",
                                         hover_color="#14203A",
                                         outline_color="#1E2D42",
                                         command=self._on_cancel,
                                         width=90, height=40, radius=10,
                                         font=("Segoe UI Variable", 11))
        self.btn_cancel.pack(side=tk.RIGHT, padx=(0, 12))

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