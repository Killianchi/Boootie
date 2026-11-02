"""Coordinate mapping between screenshot pixels and macOS screen points.

Three coordinate systems are involved:

* screen points  - global macOS coordinates (top-left origin). Window bounds from
                   CGWindowListCopyWindowInfo and CGEvent positions both use these.
* capture pixels - what the window capture returns. On a Retina display there are
                   `scale` (usually 2) pixels per point.
* image pixels   - the downscaled screenshot Claude sees. Fixed width (default 460),
                   height follows the phone's aspect ratio. Every coordinate tool
                   takes coordinates in THIS system.

Retina never leaks into the mapping: image pixels go straight to points via the
content rect, which is in points. Pixels only matter when cropping the capture.
"""

from __future__ import annotations

from dataclasses import dataclass

# iPhone screens are ~19.5:9. 2556/1179 (iPhone 14 Pro .. 16) and 2532/1170 (12..14)
# differ by 0.2%, so one value works for every Face ID iPhone.
PHONE_ASPECT = 2556 / 1179


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.w / 2, self.y + self.h / 2)


@dataclass(frozen=True)
class Frame:
    """Everything needed to map one screenshot back onto the screen."""

    content: Rect  # phone screen area, in screen points
    img_w: int  # screenshot size, in image pixels
    img_h: int


MARGIN = 8.0  # black border around the phone screen inside the window, in points (measured)


def content_rect(
    window: Rect, aspect: float = PHONE_ASPECT, top_inset: float | None = None, margin: float = MARGIN
) -> Rect:
    """The phone-screen part of the iPhone Mirroring window, in screen points.

    Measured on macOS 15: the window is the phone screen with an 8 pt black border on
    the left, right and bottom, and a taller strip on top (title bar + border, ~38 pt).
    So: width = window width - 2 * margin, height = width * aspect, anchored to the
    bottom border; whatever is left at the top is title bar. `top_inset` overrides the
    top edge if that guess is ever wrong.
    """
    w = window.w - 2 * margin
    if top_inset is None:
        h = w * aspect
        top_inset = window.h - margin - h
    top_inset = min(max(0.0, top_inset), window.h - margin - 1)
    return Rect(window.x + margin, window.y + top_inset, w, window.h - margin - top_inset)


def image_size(content: Rect, width: int) -> tuple[int, int]:
    """Screenshot size for a given content rect: fixed width, height from the aspect."""
    return width, round(width * content.h / content.w)


def make_frame(content: Rect, width: int) -> Frame:
    w, h = image_size(content, width)
    return Frame(content, w, h)


def in_image(frame: Frame, x: float, y: float) -> bool:
    return 0 <= x <= frame.img_w and 0 <= y <= frame.img_h


def to_screen(frame: Frame, x: float, y: float) -> tuple[float, float]:
    """Image pixel (x, y) -> global screen point. The one mapping every action uses."""
    if not in_image(frame, x, y):
        raise ValueError(
            f"({x}, {y}) is outside the screenshot (0..{frame.img_w}, 0..{frame.img_h})"
        )
    c = frame.content
    return (c.x + x * c.w / frame.img_w, c.y + y * c.h / frame.img_h)


def to_image(frame: Frame, sx: float, sy: float) -> tuple[float, float]:
    """Global screen point -> image pixel. Inverse of to_screen."""
    c = frame.content
    return ((sx - c.x) * frame.img_w / c.w, (sy - c.y) * frame.img_h / c.h)


def crop_box(window: Rect, content: Rect, cap_w: int, cap_h: int) -> tuple[int, int, int, int]:
    """Pixel box (left, top, right, bottom) of `content` inside a capture of `window`.

    The scale is measured from the capture itself rather than assumed, so this works
    on Retina (2x), non-Retina (1x) and scaled display modes alike.
    """
    sx = cap_w / window.w
    sy = cap_h / window.h
    left = round((content.x - window.x) * sx)
    top = round((content.y - window.y) * sy)
    right = round((content.x + content.w - window.x) * sx)
    bottom = round((content.y + content.h - window.y) * sy)
    return (max(0, left), max(0, top), min(cap_w, right), min(cap_h, bottom))
