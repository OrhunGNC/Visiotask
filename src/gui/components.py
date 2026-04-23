import tkinter as tk

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
        self.configure(bg="#2A2F3A")
        
        w, h = 460, 280
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        
        self.transient(parent)
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()
        
        main_frame = tk.Frame(self, bg="#1A1D26")
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
