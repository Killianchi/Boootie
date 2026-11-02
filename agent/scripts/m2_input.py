"""Milestone 2: test input directly, without Claude.

    uv run scripts/m2_input.py corners          move the cursor to the 4 corners + centre (no clicks)
    uv run scripts/m2_input.py center           tap the centre of the screen
    uv run scripts/m2_input.py tap X Y          tap a point (pixels in screenshot.png)
    uv run scripts/m2_input.py swipe            swipe left, then right (home screen pages)
    uv run scripts/m2_input.py scroll           scroll down 3, then up 3
    uv run scripts/m2_input.py home|switcher    Cmd+1 / Cmd+2
    uv run scripts/m2_input.py spotlight TEXT   Cmd+3 and type TEXT (try "Settings", then "café über")
    uv run scripts/m2_input.py type TEXT        type into whatever field is focused
    uv run scripts/m2_input.py all              corners, home, swipe, spotlight, home

Add --dry-run to any of these to only draw targets. Every step saves annotated
frames to runs/<timestamp>_m2/.
"""

import sys
import time

from boootie.geometry import to_screen
from boootie.phone import Phone


def corners(phone: Phone) -> None:
    img, frame, win = phone.grab()
    phone.b.activate(win)
    W, H = frame.img_w, frame.img_h
    for name, (x, y) in {"top-left": (4, 4), "top-right": (W - 4, 4), "bottom-right": (W - 4, H - 4),
                         "bottom-left": (4, H - 4), "centre": (W / 2, H / 2)}.items():
        sx, sy = to_screen(frame, x, y)
        print(f"  cursor -> {name}: image ({x:.0f}, {y:.0f}) = screen ({sx:.1f}, {sy:.1f})")
        phone.b.move(sx, sy)
        time.sleep(1.2)
    print("The cursor should have sat exactly on each corner of the phone screen (not the title bar).")


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    if not args:
        sys.exit(__doc__)
    phone = Phone(dry_run="--dry-run" in sys.argv, label="m2")
    cmd, rest = args[0], args[1:]
    f = phone.grab()[1]
    W, H = f.img_w, f.img_h
    print(f"screenshot size {W}x{H}; logging to {phone.log.dir}")

    steps = {
        "corners": lambda: corners(phone),
        "center": lambda: phone.tap(W / 2, H / 2),
        "tap": lambda: phone.tap(float(rest[0]), float(rest[1])),
        "swipe": lambda: (phone.swipe(W * 0.8, H / 2, W * 0.2, H / 2), phone.swipe(W * 0.2, H / 2, W * 0.8, H / 2)),
        "scroll": lambda: (phone.scroll("down", 3), phone.scroll("up", 3)),
        "home": phone.home,
        "switcher": phone.app_switcher,
        "spotlight": lambda: phone.spotlight(" ".join(rest) or "Settings"),
        "type": lambda: phone.type_text(" ".join(rest)),
    }
    if cmd == "all":
        for name in ["corners", "home", "swipe", "spotlight", "home"]:
            print(f"-- {name}")
            steps[name]()
            time.sleep(1)
    elif cmd in steps:
        steps[cmd]()
    else:
        sys.exit(__doc__)
    print(f"done. Look at the frames in {phone.log.dir}")


if __name__ == "__main__":
    main()
