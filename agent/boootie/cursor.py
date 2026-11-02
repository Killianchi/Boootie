"""An iOS-style "AssistiveTouch" pointer drawn on top of the screen: the AI's cursor.

It is only a picture (a transparent, click-through window), so your real pointer
stays yours. It runs as a separate helper process because AppKit windows need the
main thread's event loop, which the MCP server's main thread is busy with.

    client:  IOSCursor().glide(x, y, diameter, ms) / .press() / .release()
    helper:  python -m boootie.cursor   (reads those commands on stdin)

Look, modelled on the iOS pointer: a translucent grey disc with a faint light rim
and soft shadow; it shrinks and darkens while pressed, glides with an ease-out
curve, and fades away after a few seconds of rest.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time

IDLE_FADE_AFTER = 2.5  # seconds at rest before the pointer fades, like iOS
FPS = 60


class IOSCursor:
    """Client: start the helper on first use, send it commands. Never raises: if the
    overlay can't run, actions carry on without it."""

    def __init__(self):
        self.p: subprocess.Popen | None = None
        self.ok = True

    def _send(self, line: str) -> None:
        if not self.ok:
            return
        try:
            if self.p is None or self.p.poll() is not None:
                self.p = subprocess.Popen(
                    [sys.executable, "-m", "boootie.cursor"], stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL, text=True,  # stdout is the MCP channel: keep it clean
                )
            self.p.stdin.write(line + "\n")
            self.p.stdin.flush()
        except Exception as e:  # pragma: no cover - depends on the desktop
            print(f"[boootie] iOS cursor overlay disabled: {e}", file=sys.stderr)
            self.ok = False

    def glide(self, x: float, y: float, diameter: float, ms: int = 220) -> None:
        self._send(f"glide {x:.1f} {y:.1f} {diameter:.1f} {int(ms)}")

    def press(self) -> None:
        self._send("press")

    def release(self) -> None:
        self._send("release")

    def close(self) -> None:
        if self.p and self.p.poll() is None:
            self.p.stdin.close()


def ease_out(t: float) -> float:
    """Cubic ease-out: fast start, gentle landing (how the iOS pointer settles)."""
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** 3


# ---------------------------------------------------------------- helper process


def run_overlay() -> None:  # pragma: no cover - needs macOS
    import objc
    from AppKit import (
        NSApplication,
        NSApplicationActivationPolicyAccessory,
        NSBackingStoreBuffered,
        NSBezierPath,
        NSColor,
        NSGraphicsContext,
        NSMakeRect,
        NSScreen,
        NSShadow,
        NSStatusWindowLevel,
        NSView,
        NSWindow,
        NSWindowCollectionBehaviorCanJoinAllSpaces,
        NSWindowCollectionBehaviorFullScreenAuxiliary,
        NSWindowCollectionBehaviorIgnoresCycle,
        NSWindowCollectionBehaviorStationary,
        NSWindowStyleMaskBorderless,
    )
    from PyObjCTools import AppHelper

    BOX = 64.0  # window size in points; the disc is drawn centred inside it

    class PointerView(NSView):
        def initWithFrame_(self, frame):
            self = objc.super(PointerView, self).initWithFrame_(frame)
            if self is None:
                return None
            self.diameter = 16.0
            self.press_amount = 0.0  # 0 = resting, 1 = fully pressed (animated)
            return self

        def isFlipped(self):
            return True

        def drawRect_(self, rect):
            p = self.press_amount
            d = self.diameter * (1.0 - 0.18 * p)  # shrinks while pressed
            b = self.bounds()
            r = NSMakeRect((b.size.width - d) / 2, (b.size.height - d) / 2, d, d)

            NSGraphicsContext.saveGraphicsState()
            shadow = NSShadow.alloc().init()
            shadow.setShadowBlurRadius_(4.0)
            shadow.setShadowOffset_((0, -1))
            shadow.setShadowColor_(NSColor.colorWithCalibratedWhite_alpha_(0.0, 0.22))
            shadow.set()

            disc = NSBezierPath.bezierPathWithOvalInRect_(r)
            # translucent grey, darker when pressed
            NSColor.colorWithCalibratedWhite_alpha_(0.42 - 0.14 * p, 0.55 + 0.15 * p).setFill()
            disc.fill()

            NSGraphicsContext.restoreGraphicsState()  # no shadow on the rim
            rim = NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(r.origin.x + 0.5, r.origin.y + 0.5,
                                                                    d - 1, d - 1))
            rim.setLineWidth_(1.0)
            NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.35).setStroke()
            rim.stroke()

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)  # no Dock icon

    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(0, 0, BOX, BOX), NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False)
    win.setOpaque_(False)
    win.setBackgroundColor_(NSColor.clearColor())
    win.setHasShadow_(False)
    win.setIgnoresMouseEvents_(True)  # clicks go straight through to whatever is below
    win.setLevel_(NSStatusWindowLevel)
    win.setCollectionBehavior_(
        NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorStationary
        | NSWindowCollectionBehaviorIgnoresCycle | NSWindowCollectionBehaviorFullScreenAuxiliary)
    view = PointerView.alloc().initWithFrame_(NSMakeRect(0, 0, BOX, BOX))
    win.setContentView_(view)
    win.setAlphaValue_(0.0)
    win.orderFrontRegardless()

    primary_h = NSScreen.screens()[0].frame().size.height  # Quartz (top-left) -> Cocoa (bottom-left)
    s = {"pos": None, "from": (0, 0), "to": (0, 0), "t0": 0.0, "dur": 0.0,
         "pressed": False, "last": 0.0, "alpha": 0.0}

    def place(x, y):
        win.setFrameOrigin_((x - BOX / 2, primary_h - y - BOX / 2))

    def handle(line: str) -> None:
        parts = line.split()
        if not parts:
            return
        now = time.monotonic()
        s["last"] = now
        if parts[0] == "glide":
            x, y, d, ms = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
            view.diameter = d
            if s["pos"] is None or s["alpha"] < 0.05:
                s["pos"] = (x, y)  # appear at the target if hidden, like iOS on first touch
            s["from"], s["to"], s["t0"], s["dur"] = s["pos"], (x, y), now, ms / 1000
        elif parts[0] == "press":
            s["pressed"] = True
        elif parts[0] == "release":
            s["pressed"] = False

    def tick() -> None:
        now = time.monotonic()
        if s["pos"] is not None:
            t = (now - s["t0"]) / s["dur"] if s["dur"] > 0 else 1.0
            e = ease_out(t)
            (fx, fy), (tx, ty) = s["from"], s["to"]
            s["pos"] = (fx + (tx - fx) * e, fy + (ty - fy) * e)
            place(*s["pos"])
            # press animation (~80 ms) and fade in / fade out when idle
            target_p = 1.0 if s["pressed"] else 0.0
            view.press_amount += (target_p - view.press_amount) * 0.35
            view.setNeedsDisplay_(True)
            busy = s["pressed"] or t < 1.0 or now - s["last"] < IDLE_FADE_AFTER
            s["alpha"] += ((1.0 if busy else 0.0) - s["alpha"]) * (0.3 if busy else 0.08)
            win.setAlphaValue_(s["alpha"])
        AppHelper.callLater(1 / FPS, tick)

    def read_stdin() -> None:
        for line in sys.stdin:
            AppHelper.callAfter(handle, line)
        AppHelper.callAfter(AppHelper.stopEventLoop)  # parent went away

    threading.Thread(target=read_stdin, daemon=True).start()
    AppHelper.callLater(1 / FPS, tick)
    AppHelper.runEventLoop()


if __name__ == "__main__":
    run_overlay()
