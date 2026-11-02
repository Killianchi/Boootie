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
from .geometry import PHONE_ASPECT, Frame, content_rect, crop_box, make_frame, to_screen
from .runlog import RunLog, draw_marks

SETTLE_INTERVAL = 0.2  # seconds between frame comparisons
SETTLE_CAP = 3.0  # give up waiting after this long
SETTLE_THRESHOLD = 0.003  # fraction of changed pixels that still counts as "still"

SPECIAL_KEYS = {"enter", "return", "backspace", "delete", "escape", "esc", "tab", "space",
                "up", "down", "left", "right"}


def _env_float(name: str) -> float | None:
    v = os.environ.get(name)
    return float(v) if v else None


class Phone:
    def __init__(self, dry_run: bool = False, fake: bool = False, width: int = 460, label: str = ""):
        if fake:
            from . import fake as backend
        else:
            from . import mac as backend
        self.b = backend
        self.dry_run = dry_run
        self.width = width
        self.aspect = _env_float("BOOOTIE_ASPECT") or PHONE_ASPECT
        self.top_inset = _env_float("BOOOTIE_TOP_INSET")  # points; None = auto
        self.scroll_sign = -1 if os.environ.get("BOOOTIE_SCROLL_INVERT") else 1
        self.log = RunLog(label=label or ("dry" if dry_run else ""))

    # ------------------------------------------------------------ seeing

    def grab(self) -> tuple[Image.Image, Frame, object]:
        """Find the window (bounds re-read every time), capture it, crop the title bar,
        downscale to the fixed screenshot size."""
        win = self.b.find_window()
        content = content_rect(win.bounds, self.aspect, self.top_inset)
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
        time.sleep(0.15)
        prev = self.grab()[0]
        while time.monotonic() - t0 < SETTLE_CAP:
            time.sleep(SETTLE_INTERVAL)
            cur = self.grab()[0]
            if changed_fraction(prev, cur) < SETTLE_THRESHOLD:
                return cur, round((time.monotonic() - t0) * 1000)
            prev = cur
        return prev, round((time.monotonic() - t0) * 1000)

    # ------------------------------------------------------------ acting

    def _act(self, tool: str, args: dict, plan: Callable[[Frame], tuple[list[dict], Callable[[], None]]]) -> Image.Image:
        """Shared wrapper for every action: kill switch, fresh frame, draw target,
        perform (unless dry run), settle, log."""
        t0 = time.monotonic()
        i = self.log.next()
        entry: dict = {"i": i, "tool": tool, "args": args, "dry_run": self.dry_run}
        try:
            killswitch.check()
            before, frame, win = self.grab()
            marks, do = plan(frame)  # validates coordinates before anything moves
            entry["marks"] = marks
            entry["window"] = vars(win.bounds)
            entry["frame"] = self.log.save(draw_marks(before, marks), f"{i:03d}_{tool}.png")
            if self.dry_run:
                return before
            self.b.activate(win)
            killswitch.check()
            do()
            after, entry["settle_ms"] = self.settle()
            entry["after"] = self.log.save(after, f"{i:03d}_{tool}_after.jpg")
            return after
        except Exception as e:
            entry["error"] = f"{type(e).__name__}: {e}"
            raise
        finally:
            entry["ms"] = round((time.monotonic() - t0) * 1000)
            self.log.write(entry)

    def tap(self, x: float, y: float) -> Image.Image:
        def plan(f):
            sx, sy = to_screen(f, x, y)

            def do():
                self.b.move(sx, sy)
                time.sleep(0.05)
                self.b.mouse_down(sx, sy)
                time.sleep(0.07)
                self.b.mouse_up(sx, sy)

            return [{"kind": "dot", "x": x, "y": y, "screen": [sx, sy]}], do

        return self._act("tap", {"x": x, "y": y}, plan)

    def long_press(self, x: float, y: float, seconds: float = 1.0) -> Image.Image:
        def plan(f):
            sx, sy = to_screen(f, x, y)

            def do():
                self.b.move(sx, sy)
                time.sleep(0.05)
                self.b.mouse_down(sx, sy)
                time.sleep(seconds)
                self.b.mouse_up(sx, sy)

            return [{"kind": "dot", "x": x, "y": y, "long": True, "screen": [sx, sy]}], do

        return self._act("long_press", {"x": x, "y": y, "seconds": seconds}, plan)

    def swipe(self, x1: float, y1: float, x2: float, y2: float, duration_ms: int = 300) -> Image.Image:
        def plan(f):
            a, b = to_screen(f, x1, y1), to_screen(f, x2, y2)

            def do():
                steps = max(8, duration_ms // 16)
                self.b.move(*a)
                time.sleep(0.05)
                self.b.mouse_down(*a)
                for k in range(1, steps + 1):
                    t = k / steps
                    self.b.drag_to(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                    time.sleep(duration_ms / 1000 / steps)
                self.b.mouse_up(*b)

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
            # "down" = reveal content further down = wheel moves negative.
            dy = {"up": 1, "down": -1}.get(direction, 0) * self.scroll_sign
            dx = {"left": 1, "right": -1}.get(direction, 0) * self.scroll_sign

            def do():
                for _ in range(amount * 6):
                    self.b.scroll(sx, sy, dy * 15, dx * 15)
                    time.sleep(0.012)

            L = 40 + 12 * amount
            vx, vy = {"up": (0, -L), "down": (0, L), "left": (-L, 0), "right": (L, 0)}[direction]
            return [{"kind": "arrow", "x1": px, "y1": py, "x2": px + vx, "y2": py + vy, "screen": [sx, sy]}], do

        return self._act("scroll", {"direction": direction, "amount": amount, "x": x, "y": y}, plan)

    def _type(self, text: str, method: str) -> None:
        if method == "paste":
            self.b.paste(text)
            return
        if method == "keys":
            self.b.type_keys(text)
            return
        # auto: key presses for plain ASCII runs, clipboard paste for everything else
        run, run_keys = "", None
        for ch in text + "\0":
            k = ch != "\0" and self.b.can_type_with_keys(ch)
            if ch == "\0" or (run and k != run_keys):
                if run:
                    (self.b.type_keys if run_keys else self.b.paste)(run)
                    time.sleep(0.15)
                run = ""
            if ch != "\0":
                run, run_keys = run + ch, k

    def type_text(self, text: str, method: str = "auto") -> Image.Image:
        if method not in ("auto", "keys", "paste"):
            raise ValueError("method must be auto, keys or paste")

        def plan(f):
            return [{"kind": "text", "text": f"type: {text}"}], lambda: self._type(text, method)

        return self._act("type_text", {"text": text, "method": method}, plan)

    def press_key(self, key: str) -> Image.Image:
        key = key.lower().strip()
        if key not in SPECIAL_KEYS:
            raise ValueError(f"unsupported key {key!r}; use one of {sorted(SPECIAL_KEYS)}")

        def plan(f):
            return [{"kind": "text", "text": f"key: {key}"}], lambda: self.b.key(key)

        return self._act("press_key", {"key": key}, plan)

    def _shortcut(self, tool: str, digit: str) -> Image.Image:
        def plan(f):
            return [{"kind": "text", "text": f"{tool} (Cmd+{digit})"}], lambda: self.b.key(digit, cmd=True)

        return self._act(tool, {}, plan)

    # iPhone Mirroring menu shortcuts: View > Home Screen / App Switcher / Spotlight.
    def home(self) -> Image.Image:
        return self._shortcut("home", "1")

    def app_switcher(self) -> Image.Image:
        return self._shortcut("app_switcher", "2")

    def spotlight(self, query: str = "") -> Image.Image:
        def plan(f):
            def do():
                self.b.key("3", cmd=True)
                time.sleep(0.8)  # let the search field appear and take focus
                if query:
                    self._type(query, "auto")

            return [{"kind": "text", "text": f"spotlight: {query}"}], do

        return self._act("spotlight", {"query": query}, plan)


def changed_fraction(a: Image.Image, b: Image.Image) -> float:
    """Fraction of pixels that differ noticeably, on quarter-size greyscale copies."""
    size = (max(1, a.width // 4), max(1, a.height // 4))
    ga, gb = a.convert("L").resize(size), b.convert("L").resize(size)
    hist = ImageChops.difference(ga, gb).histogram()
    return sum(hist[13:]) / (size[0] * size[1])
