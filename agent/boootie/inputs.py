"""Two ways to deliver input to the iPhone Mirroring window.

SystemInput  synthetic events through the system mouse/keyboard (moves your real
             pointer, needs the window in front). The original, proven path.
CuaInput     Cua Driver (https://github.com/trycua/cua, MIT) posts events straight to
             the iPhone Mirroring process: your pointer stays where it is and the
             window does not need to be in front. Experimental: whether iPhone
             Mirroring accepts background events has to be tested.

Both take screen points (from geometry.to_screen) and the window they belong to.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time

from PIL import Image

# ------------------------------------------------------------------ shared


def split_runs(text: str, typeable) -> list[tuple[str, bool]]:
    """Split text into runs of (chars, typeable-as-keys). 'café' -> [('caf', True), ('é', False)]."""
    runs: list[tuple[str, bool]] = []
    for ch in text:
        k = bool(typeable(ch))
        if runs and runs[-1][1] == k:
            runs[-1] = (runs[-1][0] + ch, k)
        else:
            runs.append((ch, k))
    return runs


# ------------------------------------------------------------------ system mouse + keyboard


class SystemInput:
    name = "system"
    moves_pointer = True

    def __init__(self, backend, scroll_sign: int = 1):
        self.b = backend
        self.scroll_sign = scroll_sign

    def prepare(self, win, keys: bool) -> None:
        self.b.activate(win, required=keys)

    def tap(self, win, sx, sy) -> None:
        self.b.move(sx, sy)
        time.sleep(0.05)
        self.b.mouse_down(sx, sy)
        time.sleep(0.07)
        self.b.mouse_up(sx, sy)

    def long_press(self, win, sx, sy, seconds: float) -> None:
        self.b.move(sx, sy)
        time.sleep(0.05)
        self.b.mouse_down(sx, sy)
        time.sleep(seconds)
        self.b.mouse_up(sx, sy)

    def swipe(self, win, a, b, duration_ms: int) -> None:
        steps = max(8, duration_ms // 16)
        self.b.move(*a)
        time.sleep(0.05)
        self.b.mouse_down(*a)
        for k in range(1, steps + 1):
            t = k / steps
            self.b.drag_to(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            time.sleep(duration_ms / 1000 / steps)
        self.b.mouse_up(*b)

    def scroll(self, win, sx, sy, direction: str, amount: int) -> None:
        # "down" = reveal content further down = wheel moves negative.
        dy = {"up": 1, "down": -1}.get(direction, 0) * self.scroll_sign
        dx = {"left": 1, "right": -1}.get(direction, 0) * self.scroll_sign
        for _ in range(amount * 6):
            self.b.scroll(sx, sy, dy * 15, dx * 15)
            time.sleep(0.012)

    def key(self, win, name: str, cmd: bool = False) -> None:
        self.b.key(name, cmd=cmd)

    def type_text(self, win, text: str, method: str) -> None:
        if method == "paste":
            self.b.paste(text)
        elif method == "keys":
            self.b.type_keys(text)
        else:  # auto: key presses for plain ASCII, clipboard paste for the rest
            for run, keys in split_runs(text, self.b.can_type_with_keys):
                (self.b.type_keys if keys else self.b.paste)(run)
                time.sleep(0.15)


# ------------------------------------------------------------------ Cua Driver

# boootie key names -> Cua Driver key names
CUA_KEYS = {"enter": "return", "return": "return", "backspace": "delete", "delete": "delete",
            "escape": "escape", "esc": "escape", "tab": "tab", "space": "space",
            "up": "up", "down": "down", "left": "left", "right": "right"}


class CuaError(RuntimeError):
    pass


CUA_LOCATIONS = [
    "~/.local/bin/cua-driver", "/usr/local/bin/cua-driver", "/opt/homebrew/bin/cua-driver",
    "~/.cua-driver/bin/cua-driver", "/Applications/CuaDriver.app/Contents/MacOS/cua-driver",
    "~/Applications/CuaDriver.app/Contents/MacOS/cua-driver",
]


def find_cua_driver() -> str:
    """$BOOOTIE_CUA_BIN, then PATH, then the usual install locations (Claude Desktop
    starts servers with a minimal PATH, so PATH alone is not enough)."""
    if os.environ.get("BOOOTIE_CUA_BIN"):
        return os.environ["BOOOTIE_CUA_BIN"]
    found = shutil.which("cua-driver")
    if found:
        return found
    for p in CUA_LOCATIONS:
        p = os.path.expanduser(p)
        if os.access(p, os.X_OK):
            return p
    return "cua-driver"


class CuaInput:
    """Background input through the `cua-driver` CLI (its daemon must be running).

    Cua addresses windows in "window-local screenshot pixels" of the last
    get_window_state snapshot. We take one native-resolution snapshot per window
    size, measure the pixels-per-point scale from it, and convert screen points.
    """

    name = "cua"
    moves_pointer = False

    def __init__(self, backend, session: str = "boootie", binary: str | None = None):
        self.b = backend  # for set_clipboard (non-ASCII typing)
        self.session = session
        self.bin = binary or find_cua_driver()
        self.delivery = os.environ.get("BOOOTIE_CUA_DELIVERY", "background")  # or "foreground"
        self._scale: dict[tuple, float] = {}
        self._started = False
        self.log: list[dict] = []  # last calls, for debugging

    # -- plumbing

    def _start(self) -> None:
        """First use: open our session and hide Cua's own arrow (boootie draws the iOS one)."""
        if not self._started:
            self._started = True
            self._run("start_session", {"session": self.session}, check=False)
            self._run("set_agent_cursor_enabled", {"session": self.session, "enabled": False}, check=False)

    def _call(self, tool: str, args: dict, check: bool = True) -> str:
        self._start()
        return self._run(tool, args, check)

    def _run(self, tool: str, args: dict, check: bool = True) -> str:
        try:
            r = subprocess.run([self.bin, "call", tool, json.dumps(args)],
                               capture_output=True, text=True, timeout=30)
        except FileNotFoundError:
            raise CuaError("cua-driver is not installed. Install it: "
                           '/bin/bash -c "$(curl -fsSL https://cua.ai/driver/install.sh)"') from None
        out = (r.stdout or "") + (r.stderr or "")
        self.log = (self.log + [{"tool": tool, "args": args, "rc": r.returncode, "out": out[-500:]}])[-20:]
        failed = r.returncode != 0 or '"isError": true' in out or '"isError":true' in out
        if check and failed:
            raise CuaError(f"cua-driver {tool} failed: {out.strip()[-400:]}")
        return out

    def _target(self, win) -> dict:
        args = {"pid": win.pid, "window_id": win.id, "session": self.session, "post_action_wait": "none"}
        if self.delivery != "background":
            args["delivery_mode"] = self.delivery
        return args

    def scale(self, win) -> float:
        key = (win.id, round(win.bounds.w), round(win.bounds.h))
        if key not in self._scale:
            with tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, "state.png")
                self._call("get_window_state", {
                    "pid": win.pid, "window_id": win.id, "session": self.session,
                    "include_accessibility_tree": False, "max_image_dimension": 0,
                    "screenshot_out_file": path,
                })
                with Image.open(path) as img:
                    self._scale[key] = img.width / win.bounds.w
        return self._scale[key]

    def px(self, win, sx, sy) -> tuple[float, float]:
        """Screen point -> Cua window-local screenshot pixel."""
        s = self.scale(win)
        return (round((sx - win.bounds.x) * s, 1), round((sy - win.bounds.y) * s, 1))

    def _pointer(self, tool: str, win, args: dict) -> None:
        try:
            self._call(tool, {**self._target(win), **args})
        except CuaError:
            # The snapshot may have gone stale (Cua re-snapshots, window resized): retry once.
            self._scale.clear()
            self.scale(win)
            self._call(tool, {**self._target(win), **args})

    # -- actions

    def prepare(self, win, keys: bool) -> None:
        pass  # background delivery: nothing to bring to the front

    def tap(self, win, sx, sy) -> None:
        x, y = self.px(win, sx, sy)
        self._pointer("click", win, {"x": x, "y": y})

    def long_press(self, win, sx, sy, seconds: float) -> None:
        x, y = self.px(win, sx, sy)  # a drag that doesn't move = touch and hold
        self._pointer("drag", win, {"from_x": x, "from_y": y, "to_x": x, "to_y": y,
                                    "duration_ms": int(seconds * 1000), "steps": 10})

    def swipe(self, win, a, b, duration_ms: int) -> None:
        (x1, y1), (x2, y2) = self.px(win, *a), self.px(win, *b)
        self._pointer("drag", win, {"from_x": x1, "from_y": y1, "to_x": x2, "to_y": y2,
                                    "duration_ms": duration_ms, "steps": max(10, duration_ms // 16)})

    def scroll(self, win, sx, sy, direction: str, amount: int) -> None:
        x, y = self.px(win, sx, sy)
        self._pointer("scroll", win, {"x": x, "y": y, "direction": direction, "amount": amount})

    def key(self, win, name: str, cmd: bool = False) -> None:
        if cmd:
            self._call("hotkey", {**self._target(win), "keys": ["cmd", name]})
        else:
            self._call("press_key", {**self._target(win), "key": CUA_KEYS.get(name, name)})

    def _paste(self, win, text: str) -> None:
        self.b.set_clipboard(text)
        time.sleep(0.3)  # let Universal Clipboard sync to the phone
        self.key(win, "v", cmd=True)

    def type_text(self, win, text: str, method: str) -> None:
        if method == "paste":
            self._paste(win, text)
            return
        if method == "keys":
            self._call("type_text", {**self._target(win), "text": text})
            return
        for run, ascii_ in split_runs(text, lambda c: c.isascii() and (c.isprintable() or c == "\n")):
            if ascii_:
                self._call("type_text", {**self._target(win), "text": run})
            else:
                self._paste(win, run)
            time.sleep(0.15)
