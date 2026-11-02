"""Milestone 1: permissions, find the window, print its bounds, save screenshots.

    uv run boootie-check
"""

from __future__ import annotations

import subprocess
import sys

from PIL import ImageDraw

PANES = {
    "Screen Recording": "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
    "Accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    "Input Monitoring": "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent",
}


def main() -> None:
    fake = "--fake" in sys.argv
    from .phone import Phone

    phone = Phone(fake=fake, label="check")
    b = phone.b

    print("== Permissions (granted to the app running this command, e.g. Terminal) ==")
    perms = {
        "Screen Recording": b.has_screen_recording() or b.request_screen_recording(),
        "Accessibility": b.has_accessibility(prompt=True),
        "Input Monitoring": b.has_input_monitoring(prompt=True),
    }
    for name, ok in perms.items():
        note = "" if name != "Input Monitoring" else " (only for the kill-switch hotkey)"
        print(f"  {'OK     ' if ok else 'MISSING'} {name}{note}")
    missing = [n for n, ok in perms.items() if not ok]
    if missing and not fake:
        print("\nOpening System Settings for the missing permissions. For each one:")
        print("  1. Turn on your terminal app (Terminal / iTerm / Ghostty...). Add it with + if it is not listed.")
        print("  2. Quit the terminal completely (Cmd+Q) and reopen it; macOS only applies it on restart.")
        print("  3. Run `uv run boootie-check` again.")
        for n in missing:
            subprocess.run(["open", PANES[n]])
        if "Screen Recording" in missing:
            sys.exit(1)

    print("\n== iPhone Mirroring window ==")
    try:
        win = b.find_window()
    except Exception as e:
        sys.exit(f"  {e}")
    from .geometry import content_rect, crop_box, make_frame

    bw = win.bounds
    content = content_rect(bw, phone.aspect, phone.top_inset)
    frame = make_frame(content, phone.width)
    cap = b.capture(win)
    box = crop_box(bw, content, *cap.size)
    print(f"  window id {win.id}, pid {win.pid}")
    print(f"  bounds (points): x={bw.x:.0f} y={bw.y:.0f} w={bw.w:.0f} h={bw.h:.0f}")
    print(f"  title bar strip: {content.y - bw.y:.1f} pt (override with BOOOTIE_TOP_INSET=<pt>)")
    print(f"  phone content (points): x={content.x:.0f} y={content.y:.0f} w={content.w:.0f} h={content.h:.0f}")
    print(f"  capture: {cap.width}x{cap.height} px -> scale {cap.width / bw.w:.2f} px/pt")
    print(f"  screenshot size: {frame.img_w}x{frame.img_h} px")

    outlined = cap.copy()
    ImageDraw.Draw(outlined).rectangle(box, outline=(255, 40, 90), width=4)
    outlined.save(phone.log.dir / "window_full.png")
    img = cap.crop(box).resize((frame.img_w, frame.img_h))
    img.save(phone.log.dir / "screenshot.png")
    print(f"\nSaved to {phone.log.dir}:")
    print("  window_full.png  whole window, red box = what counts as the phone screen")
    print("  screenshot.png   what Claude will see")
    print("Check: the red box should hug the phone screen exactly, with no title bar inside it.")
