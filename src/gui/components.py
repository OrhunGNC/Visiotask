import tkinter as tk
import math


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
        self.active_bg = "#FF7A18"
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
        self.create_rectangle(self.h/2, 0, self.w - self.h/2, self.h, fill=bg, outline=bg)
        
        thumb_r = r - 3
        cx = self.w - r if state else r
        
        self.create_oval(cx-thumb_r, r-thumb_r+1, cx+thumb_r, r+thumb_r+1, fill="#1E2530", outline="")
        self.create_oval(cx-thumb_r, r-thumb_r, cx+thumb_r, r+thumb_r, fill=self.thumb_color, outline=self.thumb_color)


class CustomDropdown(tk.Frame):
    """A premium custom dropdown to replace ttk.Combobox with dark fill, orange hover, and smooth arrow."""

    def __init__(self, parent, variable, values, width=14, font=("Segoe UI", 11), bg="#0B1120", fg="#E5E7EB", accent="#FF7A1A", border_color="#253044", height=6, **kwargs):
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

        # Main button area
        self._btn_frame = tk.Frame(self, bg=bg, highlightthickness=1, highlightbackground=border_color, cursor="hand2")
        self._btn_frame.pack(fill=tk.X)

        self._value_label = tk.Label(self._btn_frame, textvariable=variable, font=font, bg=bg, fg=fg, anchor="w", padx=12, pady=8)
        self._value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Arrow icon
        self._arrow_canvas = tk.Canvas(self._btn_frame, width=24, height=24, bg=bg, highlightthickness=0, cursor="hand2")
        self._arrow_canvas.pack(side=tk.RIGHT, padx=(0, 8), pady=6)
        self._draw_arrow(filled=False)

        # Bind events
        for w in (self, self._btn_frame, self._value_label, self._arrow_canvas):
            w.bind("<Button-1>", self._toggle)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

        self._value_label.bind("<Enter>", self._on_enter)
        self._value_label.bind("<Leave>", self._on_leave)

    def _draw_arrow(self, filled=False):
        c = self._arrow_canvas
        c.delete("all")
        color = self._accent if filled else "#6B7280"
        # Down-pointing chevron
        c.create_polygon(6, 9, 12, 16, 18, 9, fill=color, outline=color, smooth=False)

    def _on_enter(self, event=None):
        self._btn_frame.configure(highlightbackground=self._accent)

    def _on_leave(self, event=None):
        if not self._is_open:
            self._btn_frame.configure(highlightbackground=self._border_color)

    def _toggle(self, event=None):
        if self._is_open:
            self._close_popup()
        else:
            self._open_popup()

    def _open_popup(self):
        self._is_open = True
        self._draw_arrow(filled=True)
        self._btn_frame.configure(highlightbackground=self._accent)

        # Create popup as a Toplevel to avoid clipping
        self._popup = tk.Toplevel(self)
        self._popup.overrideredirect(True)
        self._popup.attributes("-topmost", True)
        self._popup.configure(bg="#0E1628")

        # Position below the dropdown button
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self._popup.geometry(f"+{x}+{y}")

        # Make the popup width match the button
        self.update_idletasks()
        btn_width = self.winfo_width()
        popup_width = max(btn_width, 160)

        for val in self._values:
            row = tk.Frame(self._popup, bg="#0E1628", cursor="hand2")
            row.pack(fill=tk.X)
            lbl = tk.Label(row, text=val, font=self._font, bg="#0E1628", fg=self._fg, anchor="w", padx=16, pady=8)
            lbl.pack(fill=tk.X)

            def _select(v=val):
                self._variable.set(v)
                self._close_popup()

            for w in (row, lbl):
                w.bind("<Button-1>", lambda e, v=val: _select(v))
                w.bind("<Enter>", lambda e, r=row, l=lbl: (r.configure(bg="#152036"), l.configure(bg="#152036", fg=self._accent)))
                w.bind("<Leave>", lambda e, r=row, l=lbl: (r.configure(bg="#0E1628"), l.configure(bg="#0E1628", fg=self._fg)))

        # Separator line at bottom
        tk.Frame(self._popup, bg=self._accent, height=1).pack(fill=tk.X)

        # Bind click-outside to close
        self._popup.bind("<FocusOut>", lambda e: self._close_popup())
        self._popup.focus_set()

        # Also close on Escape
        self._popup.bind("<Escape>", lambda e: self._close_popup())

        # Click outside handler on root
        self._click_outside_id = self.bind_all("<Button-1>", self._on_click_outside, add="+")

    def _on_click_outside(self, event):
        # Close popup if click is outside the dropdown and popup
        if self._popup and self._popup.winfo_exists():
            try:
                px = self._popup.winfo_rootx()
                py = self._popup.winfo_rooty()
                pw = self._popup.winfo_width()
                ph = self._popup.winfo_height()
                ex, ey = event.x_root, event.y_root
                if not (px <= ex <= px + pw and py <= ey <= py + ph):
                    # Also check if click is on the dropdown button itself
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
        self._btn_frame.configure(highlightbackground=self._border_color)
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
        """Update the dropdown values list."""
        self._values = values

    def configure(self, **kwargs):
        """Handle standard configure calls."""
        if "values" in kwargs:
            self._values = kwargs.pop("values")
        if "state" in kwargs:
            state = kwargs.pop("state")
            if state == "readonly" or state == tk.DISABLED:
                self._btn_frame.configure(cursor="")
                for w in (self._value_label, self._arrow_canvas):
                    try:
                        w.configure(state=state)
                    except Exception:
                        pass
        super().configure(**kwargs)


class ProgressRing(tk.Canvas):
    """A glowing circular progress ring with animated green pulse and play icon."""

    def __init__(self, parent, size=140, ring_width=6, bg_color="#0E1628",
                 ring_color="#00E676", inactive_color="#1E2A40",
                 pulse_color="#00E676", icon_color="#FFFFFF", **kwargs):
        super().__init__(parent, width=size, height=size, bg=bg_color,
                         highlightthickness=0, **kwargs)
        self._size = size
        self._ring_width = ring_width
        self._ring_color = ring_color
        self._inactive_color = inactive_color
        self._pulse_color = pulse_color
        self._icon_color = icon_color
        self._bg_color = bg_color
        self._is_running = False
        self._pulse_phase = 0
        self._pulse_after_id = None
        self._draw()

    def _draw(self):
        self.delete("all")
        s = self._size
        cx, cy = s / 2, s / 2
        r = (s / 2) - self._ring_width - 8

        # Outer glow (subtle)
        if self._is_running:
            glow_alpha_shifts = [4, 8, 12]
            for i, offset in enumerate(glow_alpha_shifts):
                glow_r = r + offset
                stipple = "gray25" if i == 0 else ("gray12" if i == 1 else "")
                if stipple:
                    self.create_oval(cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r,
                                     outline=self._pulse_color, width=1, stipple=stipple)

        # Inactive ring (background track)
        self.create_oval(cx - r, cy - r, cx + r, cy + r,
                         outline=self._inactive_color, width=self._ring_width)

        # Active arc
        if self._is_running:
            # Draw full circle in active color with glow
            self.create_oval(cx - r, cy - r, cx + r, cy + r,
                             outline=self._ring_color, width=self._ring_width + 2)

        # Center icon: play triangle or idle circle
        icon_r = 18
        if self._is_running:
            # Play triangle pointing right
            points = [
                cx - 8, cy - 12,
                cx - 8, cy + 12,
                cx + 12, cy
            ]
            self.create_polygon(points, fill=self._icon_color, outline=self._icon_color)
        else:
            # Idle: right-pointing triangle (play icon) in muted color
            points = [
                cx - 8, cy - 12,
                cx - 8, cy + 12,
                cx + 12, cy
            ]
            self.create_polygon(points, fill="#4B5563", outline="#4B5563")

    def set_running(self, running):
        self._is_running = running
        self._draw()
        if running:
            self._start_pulse()
        else:
            self._stop_pulse()

    def _start_pulse(self):
        self._stop_pulse()
        self._pulse_phase = 0
        self._pulse_tick()

    def _pulse_tick(self):
        if not self._is_running:
            return
        self._pulse_phase = (self._pulse_phase + 1) % 60
        self._draw()

        # Subtle glow pulsing via ring color intensity
        if self._pulse_phase < 20:
            self._ring_color = "#00E676"
        elif self._pulse_phase < 40:
            self._ring_color = "#00CC6A"
        else:
            self._ring_color = "#33FF99"

        self._pulse_after_id = self.after(80, self._pulse_tick)

    def _stop_pulse(self):
        if self._pulse_after_id:
            try:
                self.after_cancel(self._pulse_after_id)
            except Exception:
                pass
            self._pulse_after_id = None
        self._ring_color = "#00E676"
        self._is_running = False
        self._draw()


class SmoothScrollbar(tk.Canvas):
    def __init__(self, parent, target_canvas, width=8, **kwargs):
        super().__init__(parent, bg="#060B16", highlightthickness=0, width=width, **kwargs)
        self.target = target_canvas
        self.thumb_color = "#253044"
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
        self.configure(bg="#253044")
        
        w, h = 460, 280
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        self.transient(parent)
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()
        
        main_frame = tk.Frame(self, bg="#0E1628")
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
        
        lbl_title = tk.Label(main_frame, text=title_text, font=("Segoe UI", 18, "bold"), bg="#0E1628", fg="#E5E7EB")
        lbl_title.pack(anchor="w", padx=30, pady=(24, 16))
        lbl_title.bind("<ButtonPress-1>", _on_drag_start)
        lbl_title.bind("<B1-Motion>", _on_drag_motion)
        
        tk.Label(main_frame, text=label_text, font=("Segoe UI", 12), bg="#0E1628", fg="#E5E7EB").pack(anchor="w", padx=30)
        
        input_frame = tk.Frame(main_frame, bg="#060B16", highlightthickness=1, highlightbackground="#253044")
        input_frame.pack(fill=tk.X, padx=30, pady=(8, 4))
        
        self.entry_var = tk.StringVar(value=default_value)
        self.entry = tk.Entry(input_frame, textvariable=self.entry_var, font=("Segoe UI", 12), bg="#060B16", fg="#E5E7EB", insertbackground="#E5E7EB", bd=0)
        self.entry.pack(fill=tk.X, padx=12, pady=10)
        self.entry.bind("<Return>", lambda e: self._on_submit())
        
        def _focus_and_select():
            self.entry.focus_force()
            if default_value:
                idx = default_value.rfind('.')
                if idx > 0:
                    self.entry.select_range(0, idx)
                else:
                    self.entry.select_range(0, tk.END)
        self.after(100, _focus_and_select)
        
        tk.Label(main_frame, text="e.g. icon.png", font=("Segoe UI", 10), bg="#0E1628", fg="#6B7280").pack(anchor="w", padx=30)
        
        btn_frame = tk.Frame(main_frame, bg="#0E1628")
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=30, pady=(10, 24))
        
        self.btn_submit = RoundedButton(btn_frame, ok_text, bg_color="#FF7A1A", fg_color="#FFFFFF", hover_color="#FF8C36", command=self._on_submit, width=120, height=44, font=("Segoe UI", 11, "bold"))
        self.btn_submit.pack(side=tk.RIGHT)
        
        self.btn_cancel = RoundedButton(btn_frame, "Cancel", bg_color="#0E1628", fg_color="#E5E7EB", hover_color="#1A2237", outline_color="#253044", command=self._on_cancel, width=100, height=44, font=("Segoe UI", 11))
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