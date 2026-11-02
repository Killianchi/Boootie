"""boootie MCP server: Claude's eyes and hands on the iPhone (stdio transport).

    uv run boootie-mcp              real phone
    uv run boootie-mcp --dry-run    log + draw targets, never touch mouse/keyboard
    uv run boootie-mcp --fake       pretend phone, for testing without a Mac
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import threading

from mcp.server.mcpserver import Image as MCPImage
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from PIL import Image

from . import killswitch
from .phone import Phone

GUIDE = (Path(__file__).parent / "guide.md").read_text()
ASK_FIRST = (
    " Before anything irreversible (sending, posting, paying, buying, deleting, calling, "
    "changing security settings) ask the user to confirm first."
)

mcp = MCPServer("boootie", instructions=GUIDE)
phone: Phone | None = None
_lock = threading.Lock()  # tools run in worker threads; one action at a time


def tool(**kw):
    return mcp.tool(structured_output=False, **kw)


def _do(action) -> list:
    """Run one phone call at a time; turn failures into messages Claude can read."""
    with _lock:
        try:
            return _result(action())
        except Exception as e:
            raise ToolError(f"{type(e).__name__}: {e}") from e


def _result(img: Image.Image, note: str = "") -> list:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    text = f"Screenshot {img.width}x{img.height} px. Coordinates for all tools are pixels in this image."
    if phone and phone.dry_run:
        text += " [DRY RUN: nothing was actually pressed; the screen has not changed.]"
    if note:
        text += " " + note
    return [text, MCPImage(data=buf.getvalue(), format="jpeg")]


@tool()
def screenshot() -> list:
    """Return the current iPhone screen as an image, plus its width and height in pixels.
    All coordinate tools use this image's pixel coordinates."""
    return _do(lambda: phone.screenshot())


@tool(description="""Tap at (x, y) in screenshot pixels. Returns the screen after it settles.""" + ASK_FIRST)
def tap(x: float, y: float) -> list:
    return _do(lambda: phone.tap(x, y))


@tool()
def long_press(x: float, y: float, seconds: float = 1.0) -> list:
    """Touch and hold at (x, y) for `seconds` (context menus, jiggle mode). Returns the settled screen."""
    return _do(lambda: phone.long_press(x, y, seconds))


@tool()
def swipe(x1: float, y1: float, x2: float, y2: float, duration_ms: int = 300) -> list:
    """Drag a finger from (x1, y1) to (x2, y2). Swiping up (y2 < y1) moves content up, revealing
    what is below. Use a longer duration_ms (600+) for precise, non-flinging drags.
    From the left edge (x1 about 2) to the right = go back. Returns the settled screen."""
    return _do(lambda: phone.swipe(x1, y1, x2, y2, duration_ms))


@tool()
def scroll(direction: str, amount: int = 3, x: float | None = None, y: float | None = None) -> list:
    """Scroll with the mouse wheel. direction: up|down|left|right ("down" reveals content further
    down). amount: 1-20 steps (3 is about a third of a screen). Optional x, y: where to scroll
    (default: screen centre). If nothing moves, use swipe instead. Returns the settled screen."""
    return _do(lambda: phone.scroll(direction, amount, x, y))


@tool(description="""Type text into the focused field (tap the field first). Handles any characters
    (é, ü, emoji): plain ASCII is typed as keys, anything else is pasted via the clipboard.
    method: auto|keys|paste. Does not press enter.""" + ASK_FIRST)
def type_text(text: str, method: str = "auto") -> list:
    return _do(lambda: phone.type_text(text, method))


@tool(description="""Press one key: enter, backspace, escape, tab, space, up, down, left, right.""" + ASK_FIRST)
def press_key(key: str) -> list:
    return _do(lambda: phone.press_key(key))


@tool()
def home() -> list:
    """Go to the home screen (iPhone Mirroring Cmd+1). Good for resetting when lost."""
    return _do(lambda: phone.home())


@tool()
def app_switcher() -> list:
    """Open the app switcher (iPhone Mirroring Cmd+2)."""
    return _do(lambda: phone.app_switcher())


@tool()
def spotlight(query: str = "") -> list:
    """Open Spotlight search (iPhone Mirroring Cmd+3) and type `query`. The best way to open an app:
    spotlight("Settings"), then tap the result or press_key("enter")."""
    return _do(lambda: phone.spotlight(query))


def main() -> None:
    global phone
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="never move the mouse or press keys")
    p.add_argument("--fake", action="store_true", help="use a pretend phone (no Mac needed)")
    p.add_argument("--width", type=int, default=460, help="screenshot width in pixels")
    a = p.parse_args()

    phone = Phone(dry_run=a.dry_run, fake=a.fake, width=a.width)
    print(f"[boootie] run folder: {phone.log.dir}", file=sys.stderr)
    if a.dry_run:
        print("[boootie] DRY RUN: no input will be sent", file=sys.stderr)
    if not a.fake:
        if killswitch.start_hotkey_listener():
            print("[boootie] kill switch: Ctrl+Option+Cmd+K (resume: Ctrl+Option+Cmd+R)", file=sys.stderr)
        else:
            print("[boootie] kill-switch hotkey unavailable (grant Input Monitoring); "
                  "`uv run boootie-kill on` still works", file=sys.stderr)
    if killswitch.is_killed():
        print("[boootie] note: kill switch is currently ON", file=sys.stderr)
    mcp.run("stdio")


if __name__ == "__main__":
    main()
