"""
Background and foreground mouse clicking for Windows.

- Background mode (default): Sends WM_LBUTTONDOWN / WM_LBUTTONUP messages
  directly to the window under the target coordinates via ctypes Win32 API.
  The physical cursor is NOT moved — the user retains full mouse control
  while Visiotask clicks in the background.

- Foreground mode: Falls back to pyautogui.click() which physically moves
  the cursor (original behaviour).

Both modes use mss for screen capture (no cursor movement needed for
template matching).
"""

import ctypes
import ctypes.wintypes
import time

# ── Win32 constants ───────────────────────────────────────────────
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP   = 0x0202
MK_LBUTTON     = 0x0001

user32 = ctypes.windll.user32


def _window_from_point(x: int, y: int) -> int:
    """Return the HWND of the topmost window at (x, y) in screen coords."""
    return user32.WindowFromPoint(ctypes.wintypes.POINT(x, y))


def _make_lparam(x: int, y: int) -> int:
    """Pack coordinates into an LPARAM (low=WORD x, high=WORD y)."""
    return (y << 16) | (x & 0xFFFF)


def background_click(x: int, y: int, double_click: bool = False) -> bool:
    """
    Send a left-click to the window at screen coordinates (x, y) without
    moving the physical cursor.

    Returns True if the click was dispatched successfully.
    """
    hwnd = _window_from_point(x, y)
    if not hwnd:
        return False

    # Convert screen coordinates to the window-local coordinates that
    # WM_LBUTTONDOWN / WM_LBUTTONUP expect.
    point = ctypes.wintypes.POINT(x, y)
    user32.ScreenToClient(hwnd, ctypes.byref(point))
    lparam = (point.y << 16) | (point.x & 0xFFFF)

    # Send the messages.  SendMessage is synchronous — the click is
    # fully processed before we return, mirroring pyautogui.click()'s
    # blocking semantics.
    def _click():
        user32.SendMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
        user32.SendMessageW(hwnd, WM_LBUTTONUP, 0, lparam)

    _click()

    if double_click:
        # Windows generates a dblclick when two quick clicks land on the
        # same spot within the double-click time, but sending WM_LBUTTONDBLCLK
        # ourselves is more reliable across applications.
        time.sleep(0.05)
        _click()

    return True


def foreground_click(x: int, y: int, double_click: bool = False) -> None:
    """
    Click using pyautogui — moves the physical cursor (original behaviour).
    """
    import pyautogui
    pyautogui.FAILSAFE = False
    if double_click:
        pyautogui.click(x, y)
        time.sleep(0.1)
        pyautogui.click(x, y)
    else:
        pyautogui.click(x, y)