"""Fake backend (--fake): a pretend phone so the server can be tested without a Mac.

It draws a grid with labelled cells at 2x "Retina" scale and records every input
event, which is enough to check the MCP plumbing, mapping and run logs.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageDraw

from .geometry import PHONE_ASPECT, Rect

SCALE = 2
BOUNDS = Rect(900, 100, 330, round(330 * PHONE_ASPECT) + 28)  # 28 pt title strip
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
    img = Image.new("RGB", (w, h), (30, 30, 36))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, 28 * SCALE], fill=(200, 60, 60))  # "title bar": must be cropped away
    cols, rows = 4, 8
    top = 28 * SCALE
    cw, ch = w / cols, (h - top) / rows
    for r in range(rows):
        for c in range(cols):
            x0, y0 = c * cw, top + r * ch
            d.rectangle([x0 + 6, y0 + 6, x0 + cw - 6, y0 + ch - 6], outline=(120, 160, 255), width=3)
            d.text((x0 + 16, y0 + 16), f"R{r}C{c}", fill=(230, 230, 230))
    d.text((16, h - 40), f"events: {len(events)}", fill=(255, 220, 120))
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
