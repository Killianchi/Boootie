"""Milestone 2: test input directly, without Claude.

    uv run scripts/m2_input.py corners          move the cursor to the 4 corners + centre (no clicks)
    uv run scripts/m2_input.py focus            bring iPhone Mirroring to the front (needed before typing)
    uv run scripts/m2_input.py center           tap the centre of the screen
    uv run scripts/m2_input.py tap X Y          tap a point (pixels in screenshot.png)
    uv run scripts/m2_input.py swipe            swipe left, then right (home screen pages)
    uv run scripts/m2_input.py scroll           scroll down 3, then up 3
    uv run scripts/m2_input.py home|switcher    Cmd+1 / Cmd+2
    uv run scripts/m2_input.py spotlight TEXT   Cmd+3 and type TEXT (try "Settings", then "café über")
    uv run scripts/m2_input.py type TEXT        type into whatever field is focused
    uv run scripts/m2_input.py all              corners, home, swipe, spotlight, home

    uv run scripts/m2_input.py cursor --input cua   only animate the AI's iOS pointer (no input)

Add --dry-run to any of these to only draw targets. Add --input cua to send everything
through Cua Driver in the background (your pointer stays put; the AI's iOS-style
pointer shows where it acts). Add --ios-cursor to show that pointer with system input.
Every step saves annotated frames to runs/<timestamp>_m2/.
"""

import sys
import time

from boootie.geometry import to_screen
from boootie.phone import Phone


def corners(phone: Phone, press: bool = False) -> None:
    """Visit the 4 corners + centre: with the AI's iOS pointer if it's on, else the real one."""
    img, frame, win = phone.grab()
    phone._diam = 19 * frame.content.w / 390
    if not phone.cursor:
        phone.b.activate(win, required=False)
    W, H = frame.img_w, frame.img_h
    for name, (x, y) in {"top-left": (4, 4), "top-right": (W - 4, 4), "bottom-right": (W - 4, H - 4),
                         "bottom-left": (4, H - 4), "centre": (W / 2, H / 2)}.items():
        sx, sy = to_screen(frame, x, y)
        print(f"  cursor -> {name}: image ({x:.0f}, {y:.0f}) = screen ({sx:.1f}, {sy:.1f})")
        if phone.cursor:
            phone._glide(sx, sy, ms=450)
            if press:
                phone._press(True)
                time.sleep(0.15)
                phone._press(False)
        else:
            phone.b.move(sx, sy)
        time.sleep(1.2)
    which = "AI's round pointer" if phone.cursor else "cursor"
    print(f"The {which} should have sat exactly on each corner of the phone screen (not the title bar).")


def focus(phone: Phone) -> None:
    win = phone.grab()[2]
    print(f"  iPhone Mirroring pid {win.pid}; frontmost pid before: {phone.b._frontmost_pid()}")
    try:
        phone.b.activate(win)
        print("  OK: iPhone Mirroring is frontmost")
    except RuntimeError as e:
        print(f"  FAILED: {e}")
    print(f"  frontmost pid after: {phone.b._frontmost_pid()}")


def main() -> None:
    argv = sys.argv[1:]
    input_mode = None
    if "--input" in argv:
        i = argv.index("--input")
        input_mode = argv[i + 1]
        del argv[i:i + 2]
    ios_cursor = True if "--ios-cursor" in argv else None
    args = [a for a in argv if a not in ("--dry-run", "--ios-cursor")]
    if not args:
        sys.exit(__doc__)
    phone = Phone(dry_run="--dry-run" in argv, label="m2", input_mode=input_mode, ios_cursor=ios_cursor)
    print(f"input: {phone.inp.name}, iOS cursor: {'on' if phone.cursor else 'off'}")
    cmd, rest = args[0], args[1:]
    f = phone.grab()[1]
    W, H = f.img_w, f.img_h
    print(f"screenshot size {W}x{H}; logging to {phone.log.dir}")

    steps = {
        "corners": lambda: corners(phone),
        "focus": lambda: focus(phone),
        "cursor": lambda: corners(phone, press=True),
        "center": lambda: phone.tap(W / 2, H / 2),
        "tap": lambda: phone.tap(float(rest[0]), float(rest[1])),
        "swipe": lambda: (phone.swipe(W * 0.8, H / 2, W * 0.2, H / 2), phone.swipe(W * 0.2, H / 2, W * 0.8, H / 2)),
        "scroll": lambda: (phone.scroll("down", 3), phone.scroll("up", 3)),
        "home": phone.home,
        "switcher": phone.app_switcher,
        "spotlight": lambda: phone.spotlight(" ".join(rest) or "Settings"),
        "type": lambda: phone.type_text(" ".join(rest)),
    }
    if cmd == "cursor" and not phone.cursor:
        sys.exit("the iOS cursor is off: add --input cua or --ios-cursor")
    if cmd == "all":
        for name in ["corners", "home", "swipe", "spotlight", "home"]:
            print(f"-- {name}")
            steps[name]()
            time.sleep(1)
    elif cmd in steps:
        steps[cmd]()
    else:
        sys.exit(__doc__)
    if phone.cursor:
        time.sleep(3.5)  # let the pointer fade out before the overlay exits
    print(f"done. Look at the frames in {phone.log.dir}")


if __name__ == "__main__":
    main()
