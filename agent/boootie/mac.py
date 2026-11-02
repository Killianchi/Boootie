"""macOS backend: find and capture the iPhone Mirroring window, send mouse/keyboard events.

Needs two permissions for the app that runs this process (Terminal, iTerm, Claude...):
Screen Recording (capture) and Accessibility (synthetic input).
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from dataclasses import dataclass

import Quartz
from AppKit import (
    NSApplicationActivateIgnoringOtherApps,
    NSPasteboard,
    NSPasteboardTypeString,
    NSRunningApplication,
    NSWorkspace,
)
from PIL import Image

from .geometry import Rect

BUNDLE_ID = "com.apple.ScreenContinuity"  # iPhone Mirroring
OWNER_NAME = "iPhone Mirroring"  # English name, fallback if the bundle lookup fails


class WindowNotFound(RuntimeError):
    pass


@dataclass(frozen=True)
class Window:
    id: int
    pid: int
    bounds: Rect  # screen points
    on_screen: bool


# ---------------------------------------------------------------- window + capture


def _mirroring_pids() -> set[int]:
    apps = NSRunningApplication.runningApplicationsWithBundleIdentifier_(BUNDLE_ID)
    return {int(a.processIdentifier()) for a in apps}


def find_window() -> Window:
    """Locate the iPhone Mirroring window. Called fresh on every action."""
    pids = _mirroring_pids()
    infos = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionAll | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )
    best = None
    for w in infos or []:
        mine = w.get("kCGWindowOwnerPID") in pids or w.get("kCGWindowOwnerName") == OWNER_NAME
        if not mine or w.get("kCGWindowLayer", 0) != 0:
            continue
        b = w["kCGWindowBounds"]
        r = Rect(float(b["X"]), float(b["Y"]), float(b["Width"]), float(b["Height"]))
        if r.w < 100 or r.h < 100:  # skip menus, tooltips, invisible helpers
            continue
        cand = Window(int(w["kCGWindowNumber"]), int(w["kCGWindowOwnerPID"]), r,
                      bool(w.get("kCGWindowIsOnscreen", False)))
        if best is None or (cand.on_screen, r.w * r.h) > (best.on_screen, best.bounds.w * best.bounds.h):
            best = cand
    if best is None:
        raise WindowNotFound(
            "iPhone Mirroring window not found. Open the iPhone Mirroring app and connect to the phone."
        )
    if not best.on_screen:
        raise WindowNotFound(
            "iPhone Mirroring is running but its window is not on screen "
            "(minimised, hidden, or on another Space). Bring it to the front."
        )
    return best


def _cgimage_to_pil(cg) -> Image.Image:
    w, h = Quartz.CGImageGetWidth(cg), Quartz.CGImageGetHeight(cg)
    bpr = Quartz.CGImageGetBytesPerRow(cg)
    data = Quartz.CGDataProviderCopyData(Quartz.CGImageGetDataProvider(cg))
    return Image.frombuffer("RGBA", (w, h), bytes(data), "raw", "BGRA", bpr, 1).convert("RGB")


def capture(win: Window) -> Image.Image:
    """Capture the whole window (title bar included) at full Retina resolution."""
    cg = None
    if hasattr(Quartz, "CGWindowListCreateImage"):
        cg = Quartz.CGWindowListCreateImage(
            Quartz.CGRectNull,
            Quartz.kCGWindowListOptionIncludingWindow,
            win.id,
            Quartz.kCGWindowImageBoundsIgnoreFraming | Quartz.kCGWindowImageBestResolution,
        )
    if cg is not None and Quartz.CGImageGetWidth(cg) > 1:
        return _cgimage_to_pil(cg)
    # Fallback: the screencapture CLI (slower, but survives API deprecation).
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        r = subprocess.run(["screencapture", "-x", "-o", f"-l{win.id}", f.name], capture_output=True)
        if r.returncode != 0:
            raise RuntimeError(f"screen capture failed: {r.stderr.decode().strip()}")
        img = Image.open(f.name)
        img.load()
        if img.width <= 1:
            raise RuntimeError("Screen capture returned an empty image. Is Screen Recording permission granted?")
        return img.convert("RGB")


def _frontmost_pid() -> int | None:
    """Owner of the frontmost normal window, from the live window list.

    (NSWorkspace.frontmostApplication is not used: in a process without a running
    AppKit event loop, like this one, it can keep returning a stale answer.)
    """
    infos = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )
    for w in infos or []:  # ordered front to back
        b = w.get("kCGWindowBounds", {})
        if (w.get("kCGWindowLayer", 0) == 0 and w.get("kCGWindowAlpha", 1) > 0
                and b.get("Width", 0) > 50 and b.get("Height", 0) > 50):
            return int(w["kCGWindowOwnerPID"])
    return None


def _wait_front(pid: int, seconds: float) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if _frontmost_pid() == pid:
            return True
        time.sleep(0.05)
    return False


def activate(win: Window, required: bool = True) -> None:
    """Bring iPhone Mirroring to the front so it receives keyboard events.

    Tries, in order: NSRunningApplication.activate, `open -b` (LaunchServices), and a
    click on the window's black border beside the phone screen (focuses the window
    without touching the phone). `required=False` is for mouse-only actions, where
    the click itself focuses the window anyway.
    """
    if _frontmost_pid() == win.pid:
        return
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(win.pid)
    if app is not None:
        app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
    if _wait_front(win.pid, 0.3):
        return
    subprocess.run(["open", "-b", BUNDLE_ID], capture_output=True)
    if _wait_front(win.pid, 0.5):
        return
    b = win.bounds
    x, y = b.x + 3, b.y + b.h / 2  # left border, outside the phone screen
    move(x, y)
    time.sleep(0.05)
    mouse_down(x, y)
    mouse_up(x, y)
    if _wait_front(win.pid, 0.5) or not required:
        time.sleep(0.1)
        return
    raise RuntimeError(
        "Could not bring iPhone Mirroring to the front; keystrokes would go to the wrong app. "
        "Click the iPhone Mirroring window once and try again."
    )


# ---------------------------------------------------------------- permissions


def has_screen_recording() -> bool:
    return bool(Quartz.CGPreflightScreenCaptureAccess())


def request_screen_recording() -> bool:
    return bool(Quartz.CGRequestScreenCaptureAccess())


def has_accessibility(prompt: bool = False) -> bool:
    from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt

    return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: prompt}))


def has_input_monitoring(prompt: bool = False) -> bool:
    """Needed only for the kill-switch hotkey listener."""
    if prompt and hasattr(Quartz, "CGRequestListenEventAccess"):
        return bool(Quartz.CGRequestListenEventAccess())
    if hasattr(Quartz, "CGPreflightListenEventAccess"):
        return bool(Quartz.CGPreflightListenEventAccess())
    return True


# ---------------------------------------------------------------- mouse


def _post(ev) -> None:
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)


def _mouse(kind, x: float, y: float) -> None:
    ev = Quartz.CGEventCreateMouseEvent(None, kind, (x, y), Quartz.kCGMouseButtonLeft)
    if kind in (Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseUp):
        Quartz.CGEventSetIntegerValueField(ev, Quartz.kCGMouseEventClickState, 1)
    _post(ev)


def move(x: float, y: float) -> None:
    _mouse(Quartz.kCGEventMouseMoved, x, y)


def mouse_down(x: float, y: float) -> None:
    _mouse(Quartz.kCGEventLeftMouseDown, x, y)


def mouse_up(x: float, y: float) -> None:
    _mouse(Quartz.kCGEventLeftMouseUp, x, y)


def drag_to(x: float, y: float) -> None:
    _mouse(Quartz.kCGEventLeftMouseDragged, x, y)


def scroll(x: float, y: float, dy: int, dx: int = 0) -> None:
    """One scroll-wheel event at (x, y), in pixels. dy > 0 scrolls content up (shows what is above)."""
    move(x, y)
    ev = Quartz.CGEventCreateScrollWheelEvent(None, Quartz.kCGScrollEventUnitPixel, 2, int(dy), int(dx))
    Quartz.CGEventSetLocation(ev, (x, y))
    _post(ev)


# ---------------------------------------------------------------- keyboard

# macOS virtual key codes (ANSI layout).
KEYCODES = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9,
    "b": 11, "q": 12, "w": 13, "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19,
    "3": 20, "4": 21, "6": 22, "5": 23, "=": 24, "9": 25, "7": 26, "-": 27, "8": 28,
    "0": 29, "]": 30, "o": 31, "u": 32, "[": 33, "i": 34, "p": 35, "l": 37, "j": 38,
    "'": 39, "k": 40, ";": 41, "\\": 42, ",": 43, "/": 44, "n": 45, "m": 46, ".": 47,
    "`": 50, " ": 49,
    "return": 36, "enter": 36, "tab": 48, "space": 49, "backspace": 51, "delete": 51,
    "escape": 53, "esc": 53, "left": 123, "right": 124, "down": 125, "up": 126,
}
SHIFTED = dict(zip('~!@#$%^&*()_+{}|:"<>?', "`1234567890-=[]\\;',./"))
MODIFIER_KEYCODES = {"cmd": 55, "shift": 56}


def _modifier(code: int, down: bool, flags: int) -> None:
    ev = Quartz.CGEventCreateKeyboardEvent(None, code, down)
    Quartz.CGEventSetFlags(ev, flags)
    _post(ev)
    time.sleep(0.012)


def key(name: str, cmd: bool = False, shift: bool = False, text: str | None = None) -> None:
    """Press and release one key, optionally with Cmd/Shift.

    The modifier keys themselves are pressed around the key: iPhone Mirroring ignores
    flags on the key event when forwarding to the phone, so Shift+2 would arrive as "2".
    """
    code = KEYCODES[name]
    mods = [(MODIFIER_KEYCODES["cmd"], Quartz.kCGEventFlagMaskCommand)] if cmd else []
    if shift:
        mods.append((MODIFIER_KEYCODES["shift"], Quartz.kCGEventFlagMaskShift))
    flags = 0
    for mod_code, mask in mods:
        flags |= mask
        _modifier(mod_code, True, flags)
    for down in (True, False):
        ev = Quartz.CGEventCreateKeyboardEvent(None, code, down)
        Quartz.CGEventSetFlags(ev, flags)
        if text:
            Quartz.CGEventKeyboardSetUnicodeString(ev, len(text), text)
        _post(ev)
        time.sleep(0.012)
    for mod_code, mask in reversed(mods):
        flags &= ~mask
        _modifier(mod_code, False, flags)


def can_type_with_keys(ch: str) -> bool:
    return ch.lower() in KEYCODES or ch in SHIFTED or ch == "\n"


def type_keys(text: str) -> None:
    """Type ASCII text as real key presses (US layout)."""
    for ch in text:
        if ch == "\n":
            key("return")
        elif ch in SHIFTED:
            key(SHIFTED[ch], shift=True, text=ch)
        elif ch.isupper():
            key(ch.lower(), shift=True, text=ch)
        else:
            key(ch, text=ch)
        time.sleep(0.02)


def paste(text: str) -> None:
    """Put text on the Mac clipboard and press Cmd+V (reaches the phone via Universal Clipboard)."""
    set_clipboard(text)
    time.sleep(0.3)  # give the clipboard time to sync to the phone
    key("v", cmd=True)


def set_clipboard(text: str) -> None:
    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(text, NSPasteboardTypeString)
