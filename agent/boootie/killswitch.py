"""Global kill switch.

State is a file (~/.boootie/KILLED) so every process sees it: the MCP server, the
test scripts, and the `boootie-kill` command.

    Ctrl+Option+Cmd+K   kill: block all phone actions
    Ctrl+Option+Cmd+R   resume
    uv run boootie-kill on|off|status

The two hotkeys are separate on purpose: if two servers are running, both see the
key press, and a toggle would cancel itself out.
"""

from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path

STATE = Path.home() / ".boootie" / "KILLED"
KEY_K, KEY_R = 40, 15  # macOS virtual key codes


class Killed(RuntimeError):
    pass


def is_killed() -> bool:
    return STATE.exists()


def set_killed(on: bool) -> None:
    if on:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text("killed\n")
    else:
        STATE.unlink(missing_ok=True)


def check() -> None:
    if is_killed():
        raise Killed(
            "KILL SWITCH IS ON: all phone actions are blocked. Stop and tell the user. "
            "They re-enable it with Ctrl+Option+Cmd+R or `uv run boootie-kill off`."
        )


def _notify(msg: str) -> None:
    print(f"[boootie] {msg}", file=sys.stderr, flush=True)
    subprocess.Popen(["osascript", "-e", f'display notification "{msg}" with title "boootie"'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def start_hotkey_listener() -> bool:
    """Listen for the hotkeys in a background thread. Returns False if macOS refuses
    (grant Input Monitoring to the app running this process); the file and the
    `boootie-kill` command still work then."""
    import CoreFoundation as CF
    import Quartz

    want = Quartz.kCGEventFlagMaskControl | Quartz.kCGEventFlagMaskAlternate | Quartz.kCGEventFlagMaskCommand
    ready = threading.Event()
    result = {"ok": False}

    def callback(proxy, etype, event, refcon):
        if etype in (Quartz.kCGEventTapDisabledByTimeout, Quartz.kCGEventTapDisabledByUserInput):
            Quartz.CGEventTapEnable(result["tap"], True)
            return event
        if (Quartz.CGEventGetFlags(event) & want) == want:
            code = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            if code == KEY_K and not is_killed():
                set_killed(True)
                _notify("KILL SWITCH ON: phone actions blocked")
            elif code == KEY_R and is_killed():
                set_killed(False)
                _notify("Kill switch off: phone actions allowed")
        return event

    def run():
        tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap, Quartz.kCGHeadInsertEventTap, Quartz.kCGEventTapOptionListenOnly,
            1 << Quartz.kCGEventKeyDown, callback, None,
        )
        if tap is None:
            ready.set()
            return
        result.update(ok=True, tap=tap)
        src = CF.CFMachPortCreateRunLoopSource(None, tap, 0)
        CF.CFRunLoopAddSource(CF.CFRunLoopGetCurrent(), src, CF.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(tap, True)
        ready.set()
        CF.CFRunLoopRun()

    threading.Thread(target=run, name="boootie-killswitch", daemon=True).start()
    ready.wait(2)
    return result["ok"]


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "on":
        set_killed(True)
    elif cmd == "off":
        set_killed(False)
    elif cmd != "status":
        sys.exit("usage: boootie-kill on|off|status")
    print("KILLED (actions blocked)" if is_killed() else "armed (actions allowed)")
