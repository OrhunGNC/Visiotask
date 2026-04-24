"""
Background and foreground mouse clicking for Windows.

Click modes:
- foreground:  pyautogui.click() — physically moves cursor (original behaviour)
- background:  Win32 SendMessage to window under cursor point (no cursor movement)
- window:      Select a specific target window by title.  Screenshots are
               captured from that window via PrintWindow (works even when
               the window is behind others) and clicks are sent directly to
               its HWND.  The user can freely use their PC / play games while
               the macro operates on the selected tab in the background.
"""

import ctypes
import ctypes.wintypes
import time

# ── Win32 constants ───────────────────────────────────────────────
WM_LBUTTONDOWN  = 0x0201
WM_LBUTTONUP    = 0x0202
WM_LBUTTONDBLCLK = 0x0203
MK_LBUTTON      = 0x0001

PW_RENDERFULLCONTENT = 0x00000002   # Windows 8.1+  — captures DX/GL content

user32  = ctypes.windll.user32
gdi32   = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32


# ══════════════════════════════════════════════════════════════════
#  Window enumeration — list visible top-level windows
# ══════════════════════════════════════════════════════════════════

_enum_callback_t = ctypes.WINFUNCTYPE(
    ctypes.wintypes.BOOL,
    ctypes.wintypes.HWND,
    ctypes.wintypes.LPARAM,
)

_visible_windows_cache: list[tuple[int, str]] = []   # [(hwnd, title), ...]

def _enum_callback(hwnd, _lparam):
    if user32.IsWindowVisible(hwnd) and user32.GetParent(hwnd) == 0:
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.strip()
            if title:
                _visible_windows_cache.append((hwnd, title))
    return True


def enumerate_windows() -> list[tuple[int, str]]:
    """Return a list of (hwnd, title) for all visible top-level windows."""
    global _visible_windows_cache
    _visible_windows_cache = []
    user32.EnumWindows(_enum_callback_t(_enum_callback), 0)
    # Sort by title for a nice dropdown
    _visible_windows_cache.sort(key=lambda x: x[1].lower())
    return list(_visible_windows_cache)


def find_window_by_title(title: str) -> int | None:
    """Find a window by exact title. Returns HWND or None."""
    windows = enumerate_windows()
    for hwnd, t in windows:
        if t == title:
            return hwnd
    # Partial match fallback
    for hwnd, t in windows:
        if title.lower() in t.lower():
            return hwnd
    return None


def get_window_title(hwnd: int) -> str:
    """Get the title of a window by its HWND."""
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


# ══════════════════════════════════════════════════════════════════
#  Background screenshot — capture a window even when occluded
# ══════════════════════════════════════════════════════════════════

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.wintypes.LONG),
                ("top", ctypes.wintypes.LONG),
                ("right", ctypes.wintypes.LONG),
                ("bottom", ctypes.wintypes.LONG)]


def capture_window(hwnd: int) -> tuple | None:
    """
    Capture a window's client area as a numpy BGR array (OpenCV-compatible),
    even when the window is behind other windows.

    Returns (bgr_array, width, height) or None on failure.
    The window must NOT be minimized — it can be behind other windows but
    should be restored or normal.
    """
    import numpy as np

    # Get client area dimensions
    rect = RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    if w <= 0 or h <= 0:
        return None

    # Create device contexts
    hdc_window = user32.GetDC(hwnd)
    if not hdc_window:
        return None
    hdc_mem = gdi32.CreateCompatibleDC(hdc_window)
    if not hdc_mem:
        user32.ReleaseDC(hwnd, hdc_window)
        return None

    # Create bitmap
    h_bitmap = gdi32.CreateCompatibleBitmap(hdc_window, w, h)
    if not h_bitmap:
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(hwnd, hdc_window)
        return None

    old_bitmap = gdi32.SelectObject(hdc_mem, h_bitmap)

    # PrintWindow captures the window content even if occluded
    # PW_RENDERFULLCONTENT (0x02) captures DirectX / WebGL content
    result = user32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT)

    if not result:
        # Fallback: try without PW_RENDERFULLCONTENT (older Windows versions)
        result = user32.PrintWindow(hwnd, hdc_mem, 0)

    # Define BITMAPINFOHEADER for GetDIBits
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize",      ctypes.wintypes.DWORD),
            ("biWidth",     ctypes.wintypes.LONG),
            ("biHeight",    ctypes.wintypes.LONG),
            ("biPlanes",    ctypes.wintypes.WORD),
            ("biBitCount",  ctypes.wintypes.WORD),
            ("biCompression", ctypes.wintypes.DWORD),
            ("biSizeImage", ctypes.wintypes.DWORD),
            ("biXPelsPerMeter", ctypes.wintypes.LONG),
            ("biYPelsPerMeter", ctypes.wintypes.LONG),
            ("biClrUsed",   ctypes.wintypes.DWORD),
            ("biClrImportant", ctypes.wintypes.DWORD),
        ]

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = w
    bmi.biHeight = -h  # Negative = top-down (matches screen coords)
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0  # BI_RGB
    bmi.biSizeImage = w * h * 4

    buffer = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(hdc_mem, h_bitmap, 0, h, buffer, ctypes.byref(bmi), 0)

    # Cleanup GDI objects
    gdi32.SelectObject(hdc_mem, old_bitmap)
    gdi32.DeleteObject(h_bitmap)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_window)

    if not result and not buffer.raw:
        return None

    # Convert BGRA buffer to BGR numpy array for OpenCV
    img = np.frombuffer(buffer, dtype=np.uint8).reshape((h, w, 4))
    bgr = img[:, :, :3].copy()  # Drop alpha channel, keep BGR

    return (bgr, w, h)


def is_window_valid(hwnd: int) -> bool:
    """Check if a window handle is still valid (window still exists)."""
    return bool(user32.IsWindow(hwnd))


# ══════════════════════════════════════════════════════════════════
#  Click dispatching
# ══════════════════════════════════════════════════════════════════

def _window_from_point(x: int, y: int) -> int:
    """Return the HWND of the topmost window at (x, y) in screen coords."""
    return user32.WindowFromPoint(ctypes.wintypes.POINT(x, y))


def background_click(x: int, y: int, double_click: bool = False) -> bool:
    """
    Send a left-click to the window at screen coordinates (x, y) without
    moving the physical cursor.

    Returns True if the click was dispatched successfully.
    """
    hwnd = _window_from_point(x, y)
    if not hwnd:
        return False

    point = ctypes.wintypes.POINT(x, y)
    user32.ScreenToClient(hwnd, ctypes.byref(point))
    lparam = (point.y << 16) | (point.x & 0xFFFF)

    def _click():
        user32.SendMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
        user32.SendMessageW(hwnd, WM_LBUTTONUP, 0, lparam)

    _click()
    if double_click:
        time.sleep(0.05)
        _click()

    return True


def window_click(hwnd: int, client_x: int, client_y: int, double_click: bool = False) -> bool:
    """
    Send a left-click to client-area coordinates (client_x, client_y) of a
    specific window HWND, without moving the physical cursor or bringing
    the window to the foreground.

    This is the core of "window mode" — the target window can be behind
    other windows and your mouse stays wherever it is.
    """
    if not is_window_valid(hwnd):
        return False

    lparam = (client_y << 16) | (client_x & 0xFFFF)

    def _click():
        user32.SendMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
        user32.SendMessageW(hwnd, WM_LBUTTONUP, 0, lparam)

    _click()
    if double_click:
        time.sleep(0.05)
        user32.SendMessageW(hwnd, WM_LBUTTONDBLCLK, MK_LBUTTON, lparam)

    return True


def foreground_click(x: int, y: int, double_click: bool = False) -> None:
    """Click using pyautogui — moves the physical cursor (original behaviour)."""
    import pyautogui
    pyautogui.FAILSAFE = False
    if double_click:
        pyautogui.click(x, y)
        time.sleep(0.1)
        pyautogui.click(x, y)
    else:
        pyautogui.click(x, y)