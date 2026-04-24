import tkinter as tk
from PIL import Image, ImageTk, ImageEnhance
import mss


class RegionSelectorOverlay(tk.Toplevel):
    def __init__(self, parent, on_select_callback, on_cancel_callback):
        super().__init__(parent)
        self.on_select = on_select_callback
        self.on_cancel = on_cancel_callback
        
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.state("zoomed")  # Fullscreen
        self.configure(cursor="cross")

        # Capture the entire screen using mss
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            sct_img = sct.grab(monitor)
            self.bg_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        # Create a dimmed version of the screenshot
        enhancer = ImageEnhance.Brightness(self.bg_img)
        self.dim_img = enhancer.enhance(0.4)
        
        self.tk_bg = ImageTk.PhotoImage(self.dim_img)

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, image=self.tk_bg, anchor="nw")

        # Instruction overlay text
        self.canvas.create_text(
            monitor["width"] // 2, 50,
            text="Click and drag to select a region. Press Escape to cancel.",
            fill="white", font=("Segoe UI", 16, "bold"), justify="center"
        )

        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.crop_img_id = None
        self.tk_crop = None

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", lambda e: self._cancel())

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
        if self.crop_img_id:
            self.canvas.delete(self.crop_img_id)
            self.crop_img_id = None

    def on_drag(self, event):
        cur_x, cur_y = event.x, event.y
        x0, y0 = min(self.start_x, cur_x), min(self.start_y, cur_y)
        x1, y1 = max(self.start_x, cur_x), max(self.start_y, cur_y)

        # Draw the bright un-dimmed cropped image section to indicate selection
        if x1 - x0 > 0 and y1 - y0 > 0:
            crop = self.bg_img.crop((x0, y0, x1, y1))
            self.tk_crop = ImageTk.PhotoImage(crop)
            if self.crop_img_id:
                self.canvas.itemconfig(self.crop_img_id, image=self.tk_crop)
                self.canvas.coords(self.crop_img_id, x0, y0)
            else:
                self.crop_img_id = self.canvas.create_image(x0, y0, image=self.tk_crop, anchor="nw")

        # Draw/update the red selection rectangle
        if self.rect_id:
            self.canvas.coords(self.rect_id, x0, y0, x1, y1)
        else:
            self.rect_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline="red", width=2)
            
        if self.rect_id:
            self.canvas.tag_raise(self.rect_id)

    def on_release(self, event):
        x0, y0 = min(self.start_x, event.x), min(self.start_y, event.y)
        x1, y1 = max(self.start_x, event.x), max(self.start_y, event.y)
        w, h = x1 - x0, y1 - y0

        if w > 10 and h > 10:
            self.on_select(x0, y0, w, h)
        else:
            self._cancel()
        self.destroy()

    def _cancel(self):
        self.on_cancel()
        self.destroy()


class ScreenshotOverlay(tk.Toplevel):
    """
    Full-screen overlay that captures the screen, lets the user drag-select
    a region, crops it, and saves it as a template image for the macro.

    Calls on_capture(crop_image, x, y, w, h) with the PIL Image of the crop
    and the on_cancel() callback if the user presses Escape.
    """

    def __init__(self, parent, on_capture_callback, on_cancel_callback):
        super().__init__(parent)
        self.on_capture = on_capture_callback
        self.on_cancel = on_cancel_callback
        self.parent_app = parent

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.state("zoomed")  # Fullscreen
        self.configure(cursor="cross")

        # Capture the entire screen using mss
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            self.full_screenshot = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        # Create a dimmed version for the background
        enhancer = ImageEnhance.Brightness(self.full_screenshot)
        self.dim_img = enhancer.enhance(0.4)

        self.tk_dim = ImageTk.PhotoImage(self.dim_img)

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, image=self.tk_dim, anchor="nw")

        # Instruction text
        self.canvas.create_text(
            self.full_screenshot.width // 2, 50,
            text="Drag to select the area to capture as a template image. Press Escape to cancel.",
            fill="white", font=("Segoe UI", 16, "bold"), justify="center"
        )

        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.crop_img_id = None
        self.tk_crop = None

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", lambda e: self._cancel())

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None
        if self.crop_img_id:
            self.canvas.delete(self.crop_img_id)
            self.crop_img_id = None

    def on_drag(self, event):
        cur_x, cur_y = event.x, event.y
        x0, y0 = min(self.start_x, cur_x), min(self.start_y, cur_y)
        x1, y1 = max(self.start_x, cur_x), max(self.start_y, cur_y)

        # Show the bright un-dimmed crop of the selected area
        if x1 - x0 > 0 and y1 - y0 > 0:
            crop = self.full_screenshot.crop((x0, y0, x1, y1))
            self.tk_crop = ImageTk.PhotoImage(crop)
            if self.crop_img_id:
                self.canvas.itemconfig(self.crop_img_id, image=self.tk_crop)
                self.canvas.coords(self.crop_img_id, x0, y0)
            else:
                self.crop_img_id = self.canvas.create_image(x0, y0, image=self.tk_crop, anchor="nw")

        # Red selection rectangle
        if self.rect_id:
            self.canvas.coords(self.rect_id, x0, y0, x1, y1)
        else:
            self.rect_id = self.canvas.create_rectangle(x0, y0, x1, y1, outline="#FF7A18", width=2)

        if self.rect_id:
            self.canvas.tag_raise(self.rect_id)

    def on_release(self, event):
        x0, y0 = min(self.start_x, event.x), min(self.start_y, event.y)
        x1, y1 = max(self.start_x, event.x), max(self.start_y, event.y)
        w, h = x1 - x0, y1 - y0

        if w > 2 and h > 2:
            # Crop the selected region from the original (un-dimmed) screenshot
            crop = self.full_screenshot.crop((x0, y0, x1, y1))
            self.on_capture(crop, x0, y0, w, h)
        else:
            self._cancel()
        self.destroy()

    def _cancel(self):
        self.on_cancel()
        self.destroy()