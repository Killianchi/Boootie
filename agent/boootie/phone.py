"""The phone: screenshot, actions, settle-wait, dry-run, kill switch, logging.

Used by both the MCP server and the milestone test scripts, so what you test is
exactly what Claude gets.
"""

from __future__ import annotations

import os
import time
from typing import Callable

from PIL import Image, ImageChops

from . import killswitch
from .geometry import MARGIN, PHONE_ASPECT, Frame, content_rect, crop_box, make_frame, to_screen
from .cursor import IOSCursor
from .inputs import CuaInput, SystemInput
from .runlog import RunLog, draw_marks

SETTLE_INTERVAL = 0.15  # seconds between frame comparisons
SETTLE_CAP = 3.0  # give up waiting after this long
SETTLE_THRESHOLD = 0.003  # fraction of changed pixels that still counts as "still"

IOS_POINTER_PT = 19.0  # AssistiveTouch pointer diameter on the phone, in iPhone points
IPHONE_WIDTH_PT = 390.0  # iPhone screen width in points (16e, 14 Pro: 390-393)

SPECIAL_KEYS = {"enter", "return", "backspace", "delete", "escape", "esc", "tab", "space",
                "up", "down", "left", "right"}


def _env_float(name: str) -> float | None:
    v = os.environ.get(name)
    return float(v) if v else None


class Phone:
    def __init__(self, dry_run: bool = False, fake: bool = False, width: int = 460, label: str = "",
                 input_mode: str | None = None, ios_cursor: bool | None = None):
        if fake:
            from . import fake as backend
        else:
            from . import mac as backend
        self.b = backend
        self.dry_run = dry_run
        self.width = width
        self.aspect = _env_float("BOOOTIE_ASPECT") or PHONE_ASPECT
        self.top_inset = _env_float("BOOOTIE_TOP_INSET")  # points; None = auto
        self.margin = _env_float("BOOOTIE_MARGIN") if os.environ.get("BOOOTIE_MARGIN") else MARGIN
        scroll_sign = -1 if os.environ.get("BOOOTIE_SCROLL_INVERT") else 1

        # How input reaches the window: "system" (real pointer) or "cua" (background).
        input_mode = input_mode or os.environ.get("BOOOTIE_INPUT", "system")
        if input_mode == "cua":
            self.inp = CuaInput(backend)
        elif input_mode == "system":
            self.inp = SystemInput(backend, scroll_sign)
        else:
            raise ValueError("input_mode must be 'system' or 'cua'")

        # The AI's iOS-style pointer overlay: on by default with background input,
        # where it is the only sign of where the AI is pointing.
        if ios_cursor is None:
            ios_cursor = input_mode == "cua"
        self.cursor = IOSCursor() if (ios_cursor and not fake) else None
        self._diam = 16.0
        self.log = RunLog(label=label or ("dry" if dry_run else ""))

    # ------------------------------------------------------------ seeing

    def grab(self) -> tuple[Image.Image, Frame, object]:
        """Find the window (bounds re-read every time), capture it, crop the title bar,
        downscale to the fixed screenshot size."""
        win = self.b.find_window()
        content = content_rect(win.bounds, self.aspect, self.top_inset, self.margin)
        frame = make_frame(content, self.width)
        cap = self.b.capture(win)
        img = cap.crop(crop_box(win.bounds, content, *cap.size))
        return img.resize((frame.img_w, frame.img_h), Image.LANCZOS), frame, win

    def screenshot(self) -> Image.Image:
        t0 = time.monotonic()
        i = self.log.next()
        entry = {"i": i, "tool": "screenshot"}
        try:
            img, frame, win = self.grab()
            entry["frame"] = self.log.save(img, f"{i:03d}_screenshot.jpg")
            entry["window"] = vars(win.bounds)
            return img
        except Exception as e:
            entry["error"] = str(e)
            raise
        finally:
            entry["ms"] = round((time.monotonic() - t0) * 1000)
            self.log.write(entry)

    def settle(self) -> tuple[Image.Image, int]:
        """Wait until the screen stops changing (or SETTLE_CAP), return the last frame."""
        t0 = time.monotonic()
        time.sleep(0.1)
        prev = self.grab()[0]
        while time.monotonic() - t0 < SETTLE_CAP:
            time.sleep(SETTLE_INTERVAL)
            cur = self.grab()[0]
            if changed_fraction(prev, cur) < SETTLE_THRESHOLD:
                return cur, round((time.monotonic() - t0) * 1000)
            prev = cur
        return prev, round((time.monotonic() - t0) * 1000)

    # ------------------------------------------------------------ acting

    def _act(self, tool: str, args: dict, plan: Callable[[Frame], tuple[list[dict], Callable[[object], None]]],
             keys: bool = False) -> Image.Image:
        """Shared wrapper for every action: kill switch, fresh frame, draw target,
        perform (unless dry run), settle, log. `keys`: the action types, so (with the
        system input) the window must be confirmed frontmost first."""
        t0 = time.monotonic()
        i = self.log.next()
        entry: dict = {"i": i, "tool": tool, "args": args, "dry_run": self.dry_run, "input": self.inp.name}
        try:
            killswitch.check()
            tg = time.monotonic()
            before, frame, win = self.grab()
            timing = entry["timing"] = {"grab_ms": round((time.monotonic() - tg) * 1000)}
            marks, do = plan(frame)  # validates coordinates before anything moves
            self._diam = IOS_POINTER_PT * frame.content.w / IPHONE_WIDTH_PT
            entry["marks"] = marks
            entry["window"] = vars(win.bounds)
            entry["frame"] = self.log.save(draw_marks(before, marks), f"{i:03d}_{tool}.png")
            if self.dry_run:
                self._preview(marks)
                return before
            ti = time.monotonic()
            if hasattr(self.inp, "calls"):
                self.inp.calls = []
            self.inp.prepare(win, keys)
            killswitch.check()
            do(win)
            timing["input_ms"] = round((time.monotonic() - ti) * 1000)
            if getattr(self.inp, "calls", None):
                timing["cua_calls"] = self.inp.calls
            after, timing["settle_ms"] = self.settle()
            entry["after"] = self.log.save(after, f"{i:03d}_{tool}_after.jpg")
            return after
        except Exception as e:
            entry["error"] = f"{type(e).__name__}: {e}"
            if getattr(self.inp, "log", None):
                entry["cua_calls"] = self.inp.log[-3:]
            raise
        finally:
            entry["ms"] = round((time.monotonic() - t0) * 1000)
            self.log.write(entry)

    # -- the AI's pointer overlay

    def _glide(self, sx: float, sy: float, ms: int = 160, wait: bool = True) -> None:
        """Move the AI pointer. The input call itself takes a moment, so we only wait
        ~60% of the glide: the pointer lands as the tap does, without adding a pause."""
        if self.cursor:
            self.cursor.glide(sx, sy, self._diam, ms)
            if wait:
                time.sleep(ms / 1000 * 0.6)

    def _press(self, down: bool) -> None:
        if self.cursor:
            (self.cursor.press if down else self.cursor.release)()

    def _preview(self, marks: list[dict]) -> None:
        """Dry run: show where the AI would act, without acting."""
        for m in marks:
            if "screen" in m:
                self._glide(m["screen"][0], m["screen"][1])
                self._press(True)
                time.sleep(0.1)
                self._press(False)

    # -- actions

    def tap(self, x: float, y: float) -> Image.Image:
        def plan(f):
            sx, sy = to_screen(f, x, y)

            def do(win):
                self._glide(sx, sy)
                self._press(True)
                self.inp.tap(win, sx, sy)
                self._press(False)

            return [{"kind": "dot", "x": x, "y": y, "screen": [sx, sy]}], do

        return self._act("tap", {"x": x, "y": y}, plan)

    def long_press(self, x: float, y: float, seconds: float = 1.0) -> Image.Image:
        def plan(f):
            sx, sy = to_screen(f, x, y)

            def do(win):
                self._glide(sx, sy)
                self._press(True)
                self.inp.long_press(win, sx, sy, seconds)
                self._press(False)

            return [{"kind": "dot", "x": x, "y": y, "long": True, "screen": [sx, sy]}], do

        return self._act("long_press", {"x": x, "y": y, "seconds": seconds}, plan)

    def swipe(self, x1: float, y1: float, x2: float, y2: float, duration_ms: int = 300) -> Image.Image:
        def plan(f):
            a, b = to_screen(f, x1, y1), to_screen(f, x2, y2)

            def do(win):
                self._glide(*a)
                self._press(True)
                self._glide(*b, ms=duration_ms, wait=False)  # pointer travels with the finger
                self.inp.swipe(win, a, b, duration_ms)
                self._press(False)

            mark = {"kind": "arrow", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "screen": [*a, *b]}
            return [mark], do

        return self._act("swipe", {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration_ms": duration_ms}, plan)

    def scroll(self, direction: str, amount: int = 3, x: float | None = None, y: float | None = None) -> Image.Image:
        if direction not in ("up", "down", "left", "right"):
            raise ValueError("direction must be up, down, left or right")
        amount = max(1, min(int(amount), 20))

        def plan(f):
            px = f.img_w / 2 if x is None else x
            py = f.img_h / 2 if y is None else y
            sx, sy = to_screen(f, px, py)

            def do(win):
                self._glide(sx, sy)
                self.inp.scroll(win, sx, sy, direction, amount)

            L = 40 + 12 * amount
            vx, vy = {"up": (0, -L), "down": (0, L), "left": (-L, 0), "right": (L, 0)}[direction]
            return [{"kind": "arrow", "x1": px, "y1": py, "x2": px + vx, "y2": py + vy, "screen": [sx, sy]}], do

        return self._act("scroll", {"direction": direction, "amount": amount, "x": x, "y": y}, plan)

    def type_text(self, text: str, method: str = "auto") -> Image.Image:
        if method not in ("auto", "keys", "paste"):
            raise ValueError("method must be auto, keys or paste")

        def plan(f):
            return [{"kind": "text", "text": f"type: {text}"}], lambda win: self.inp.type_text(win, text, method)

        return self._act("type_text", {"text": text, "method": method}, plan, keys=True)

    def press_key(self, key: str) -> Image.Image:
        key = key.lower().strip()
        if key not in SPECIAL_KEYS:
            raise ValueError(f"unsupported key {key!r}; use one of {sorted(SPECIAL_KEYS)}")

        def plan(f):
            return [{"kind": "text", "text": f"key: {key}"}], lambda win: self.inp.key(win, key)

        return self._act("press_key", {"key": key}, plan, keys=True)

    def _shortcut(self, tool: str, digit: str) -> Image.Image:
        def plan(f):
            return [{"kind": "text", "text": f"{tool} (Cmd+{digit})"}], lambda win: self.inp.key(win, digit, cmd=True)

        return self._act(tool, {}, plan, keys=True)

    # iPhone Mirroring menu shortcuts: View > Home Screen / App Switcher / Spotlight.
    def home(self) -> Image.Image:
        return self._shortcut("home", "1")

    def app_switcher(self) -> Image.Image:
        return self._shortcut("app_switcher", "2")

    def spotlight(self, query: str = "") -> Image.Image:
        def plan(f):
            def do(win):
                self.inp.key(win, "3", cmd=True)
                time.sleep(0.5)  # let the search field appear and take focus
                if query:
                    self.inp.type_text(win, query, "auto")

            return [{"kind": "text", "text": f"spotlight: {query}"}], do

        return self._act("spotlight", {"query": query}, plan, keys=True)


def changed_fraction(a: Image.Image, b: Image.Image) -> float:
    """Fraction of pixels that differ noticeably, on quarter-size greyscale copies."""
    size = (max(1, a.width // 4), max(1, a.height // 4))
    ga, gb = a.convert("L").resize(size), b.convert("L").resize(size)
    hist = ImageChops.difference(ga, gb).histogram()
    return sum(hist[13:]) / (size[0] * size[1])
