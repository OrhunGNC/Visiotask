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
GA_ROOT = 2                          # GetAncestor — get root owner

# Minimum client-area size for a window to be considered a valid target.
# Filters out tooltips, tray icons, and other tiny sub-windows.
MIN_WINDOW_WIDTH = 64
MIN_WINDOW_HEIGHT = 48

# ── Lazy Win32 API access ─────────────────────────────────────────
# Do NOT call ctypes.windll at module level — it crashes in packaged
# executables (PyInstaller / cx_Freeze).  Instead, resolve each DLL
# lazily on first use so the import always succeeds.

_user32 = None
_gdi32  = None

def _get_user32():
    global _user32
    if _user32 is None:
        _user32 = ctypes.windll.user32
    return _user32

def _get_gdi32():
    global _gdi32
    if _gdi32 is None:
        _gdi32 = ctypes.windll.gdi32
    return _gdi32


# ══════════════════════════════════════════════════════════════════
#  Window enumeration — list visible top-level windows
# ══════════════════════════════════════════════════════════════════

_enum_callback_t = ctypes.WINFUNCTYPE(
    ctypes.wintypes.BOOL,
    ctypes.wintypes.HWND,
    ctypes.wintypes.LPARAM,
)

_visible_windows_cache: list = []   # [(hwnd, title), ...]

def _enum_callback(hwnd, _lparam):
    user32 = _get_user32()
    if user32.IsWindowVisible(hwnd) and user32.GetParent(hwnd) == 0:
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value.strip()
            if title:
                # Walk up to root owner — some apps have child top-level
                # windows (like toolbars) that are tiny.  We want the
                # main application window.
                root = user32.GetAncestor(hwnd, GA_ROOT)
                if root and root != hwnd:
                    # Use the root owner's dimensions instead
                    client_rect = RECT()
                    if user32.GetClientRect(root, ctypes.byref(client_rect)):
                        cw = client_rect.right - client_rect.left
                        ch = client_rect.bottom - client_rect.top
                        # If the root is also tiny, skip this window entirely
                        if cw < MIN_WINDOW_WIDTH or ch < MIN_WINDOW_HEIGHT:
                            return True
                _visible_windows_cache.append((hwnd, title))
    return True


def _client_area_size(hwnd) -> tuple:
    """Return (width, height) of a window's client area."""
    user32 = _get_user32()
    rect = RECT()
    if user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return (rect.right - rect.left, rect.bottom - rect.top)
    return (0, 0)


def enumerate_windows() -> list:
    """Return a list of (hwnd, title) for usable visible top-level windows.

    Filters out windows with a client area smaller than MIN_WINDOW_WIDTH x
    MIN_WINDOW_HEIGHT to avoid listing tooltips, tray icons, and other
    tiny sub-windows that would be useless as macro targets.
    """
    global _visible_windows_cache
    _visible_windows_cache = []
    _get_user32().EnumWindows(_enum_callback_t(_enum_callback), 0)

    # Second pass: filter out windows with tiny client areas
    filtered = []
    for hwnd, title in _visible_windows_cache:
        # Walk to root owner for size check
        user32 = _get_user32()
        root = user32.GetAncestor(hwnd, GA_ROOT)
        check_hwnd = root if root else hwnd
        cw, ch = _client_area_size(check_hwnd)
        if cw >= MIN_WINDOW_WIDTH and ch >= MIN_WINDOW_HEIGHT:
            # Store the root owner as the target — this ensures we always
            # capture and click the main application window, not a sub-window
            filtered.append((check_hwnd, title))

    filtered.sort(key=lambda x: x[1].lower())
    return filtered


def find_window_by_title(title: str):
    """Find a window by exact title. Returns the root-owner HWND or None."""
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
    user32 = _get_user32()
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


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize",          ctypes.wintypes.DWORD),
        ("biWidth",         ctypes.wintypes.LONG),
        ("biHeight",        ctypes.wintypes.LONG),
        ("biPlanes",        ctypes.wintypes.WORD),
        ("biBitCount",      ctypes.wintypes.WORD),
        ("biCompression",   ctypes.wintypes.DWORD),
        ("biSizeImage",     ctypes.wintypes.DWORD),
        ("biXPelsPerMeter", ctypes.wintypes.LONG),
        ("biYPelsPerMeter", ctypes.wintypes.LONG),
        ("biClrUsed",       ctypes.wintypes.DWORD),
        ("biClrImportant",  ctypes.wintypes.DWORD),
    ]


def _walk_to_root(hwnd: int) -> int:
    """Walk up from hWnd to its root owner window using GetAncestor(GA_ROOT).

    This ensures we always capture the main application window, not a
    tiny child or owner-drawn control that happens to have its own HWND.
    """
    user32 = _get_user32()
    root = user32.GetAncestor(hwnd, GA_ROOT)
    return root if root else hwnd


def capture_window(hwnd: int):
    """
    Capture a window's client area as a numpy BGR array (OpenCV-compatible),
    even when the window is behind other windows.

    If the given HWND has a tiny client area (e.g. a sub-control), this
    function walks up to the root owner window and captures that instead.

    Returns (bgr_array, width, height) or None on failure.
    The window must NOT be minimized — it can be behind other windows but
    should be restored or normal.
    """
    import numpy as np

    user32 = _get_user32()
    gdi32  = _get_gdi32()

    # Walk up to root owner — if the user somehow selected a child window,
    # we want to capture the main application window instead.
    capture_hwnd = _walk_to_root(hwnd)

    # Get client area dimensions
    rect = RECT()
    if not user32.GetClientRect(capture_hwnd, ctypes.byref(rect)):
        return None
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    if w <= 0 or h <= 0:
        return None

    # If the capture area is suspiciously small, log and return None
    # This shouldn't happen after enumerate_windows filtering, but just in case
    if w < MIN_WINDOW_WIDTH or h < MIN_WINDOW_HEIGHT:
        return None

    # Create device contexts
    hdc_window = user32.GetDC(capture_hwnd)
    if not hdc_window:
        return None
    hdc_mem = gdi32.CreateCompatibleDC(hdc_window)
    if not hdc_mem:
        user32.ReleaseDC(capture_hwnd, hdc_window)
        return None

    # Create bitmap
    h_bitmap = gdi32.CreateCompatibleBitmap(hdc_window, w, h)
    if not h_bitmap:
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(capture_hwnd, hdc_window)
        return None

    old_bitmap = gdi32.SelectObject(hdc_mem, h_bitmap)

    # PrintWindow captures the window content even if occluded
    # PW_RENDERFULLCONTENT (0x02) captures DirectX / WebGL content
    result = user32.PrintWindow(capture_hwnd, hdc_mem, PW_RENDERFULLCONTENT)

    if not result:
        # Fallback: try without PW_RENDERFULLCONTENT (older Windows versions)
        result = user32.PrintWindow(capture_hwnd, hdc_mem, 0)

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
    user32.ReleaseDC(capture_hwnd, hdc_window)

    if not result and not buffer.raw:
        return None

    # Convert BGRA buffer to BGR numpy array for OpenCV
    img = np.frombuffer(buffer, dtype=np.uint8).reshape((h, w, 4))
    bgr = img[:, :, :3].copy()  # Drop alpha channel, keep BGR

    return (bgr, w, h)


def is_window_valid(hwnd: int) -> bool:
    """Check if a window handle is still valid (window still exists)."""
    return bool(_get_user32().IsWindow(hwnd))


# ══════════════════════════════════════════════════════════════════
#  Click dispatching
# ══════════════════════════════════════════════════════════════════

def _window_from_point(x: int, y: int) -> int:
    """Return the HWND of the topmost window at (x, y) in screen coords."""
    return _get_user32().WindowFromPoint(ctypes.wintypes.POINT(x, y))


def background_click(x: int, y: int, double_click: bool = False) -> bool:
    """
    Send a left-click to the window at screen coordinates (x, y) without
    moving the physical cursor.

    Returns True if the click was dispatched successfully.
    """
    hwnd = _window_from_point(x, y)
    if not hwnd:
        return False

    user32 = _get_user32()
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

    Walks up to the root owner window first — this ensures clicks go to
    the main application window, not a tiny sub-control.
    """
    # Walk to root owner for click targeting too
    target_hwnd = _walk_to_root(hwnd)
    if not is_window_valid(target_hwnd):
        return False

    user32 = _get_user32()
    lparam = (client_y << 16) | (client_x & 0xFFFF)

    def _click():
        user32.SendMessageW(target_hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
        user32.SendMessageW(target_hwnd, WM_LBUTTONUP, 0, lparam)

    _click()
    if double_click:
        time.sleep(0.05)
        user32.SendMessageW(target_hwnd, WM_LBUTTONDBLCLK, MK_LBUTTON, lparam)

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