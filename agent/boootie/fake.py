"""Fake backend (--fake): a pretend phone so the server can be tested without a Mac.

It draws a grid with labelled cells at 2x "Retina" scale and records every input
event, which is enough to check the MCP plumbing, mapping and run logs.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw

from .geometry import Rect

SCALE = 2
BOUNDS = Rect(1038, 96, 318, 701)  # same as a measured real window
MARGIN, TOP = 8, 38  # black border; title bar + border
events: list[tuple] = []


class WindowNotFound(RuntimeError):
    pass


@dataclass(frozen=True)
class Window:
    id: int
    pid: int
    bounds: Rect
    on_screen: bool


def find_window() -> Window:
    return Window(1, 1, BOUNDS, True)


def capture(win: Window) -> Image.Image:
    w, h = round(win.bounds.w * SCALE), round(win.bounds.h * SCALE)
    img = Image.new("RGB", (w, h), (0, 0, 0))  # black border, as in the real window
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 20 * SCALE], fill=(200, 60, 60))  # "title bar": must be cropped away
    x0, y0, x1, y1 = MARGIN * SCALE, TOP * SCALE, w - MARGIN * SCALE, h - MARGIN * SCALE
    cols, rows = 4, 8
    cw, ch = (x1 - x0) / cols, (y1 - y0) / rows
    for r in range(rows):
        for c in range(cols):
            cx, cy = x0 + c * cw, y0 + r * ch
            d.rectangle([cx, cy, cx + cw, cy + ch], fill=(40, 40, 60), outline=(120, 160, 255), width=3)
            d.text((cx + 12, cy + 12), f"R{r}C{c}", fill=(230, 230, 230))
    d.text((x0 + 12, y1 - 30), f"events: {len(events)}", fill=(255, 220, 120))
    return img


def activate(win: Window) -> None:
    pass


def has_screen_recording() -> bool:
    return True


def request_screen_recording() -> bool:
    return True


def has_accessibility(prompt: bool = False) -> bool:
    return True


def has_input_monitoring(prompt: bool = False) -> bool:
    return True


def _rec(*e):
    events.append(e)


def move(x, y): _rec("move", x, y)
def mouse_down(x, y): _rec("down", x, y)
def mouse_up(x, y): _rec("up", x, y)
def drag_to(x, y): _rec("drag", x, y)
def scroll(x, y, dy, dx=0): _rec("scroll", x, y, dy, dx)
def key(name, cmd=False, shift=False, text=None): _rec("key", name, cmd, shift)
def can_type_with_keys(ch): return ch.isascii()
def type_keys(text): _rec("type", text)
def paste(text): _rec("paste", text)
