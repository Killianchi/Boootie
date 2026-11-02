"""Time a few safe actions and show where the time goes.

    uv run scripts/bench.py                         system input (moves your pointer)
    uv run scripts/bench.py --input cua             Cua Driver, persistent connection
    uv run scripts/bench.py --input cua --cli       Cua Driver, one process per call (the old way)

Sequence (safe on the home screen): screenshot, home, tap the clock, Spotlight "Settings", home.
Columns: total time, capture before the action, sending the input, waiting for the screen to settle.
"""

import json
import os
import sys
import time

from boootie.phone import Phone


def main() -> None:
    argv = sys.argv[1:]
    mode = argv[argv.index("--input") + 1] if "--input" in argv else "system"
    if "--cli" in argv:
        os.environ["BOOOTIE_CUA_TRANSPORT"] = "cli"
    phone = Phone(fake="--fake" in argv, label="bench", input_mode=mode, ios_cursor=False if "--no-cursor" in argv else None)
    print(f"input: {phone.inp.name}"
          + (f" ({os.environ.get('BOOOTIE_CUA_TRANSPORT', 'mcp')})" if mode == "cua" else "")
          + f", iOS cursor: {'on' if phone.cursor else 'off'}\n")

    t = time.monotonic()
    phone.screenshot()
    print(f"{'screenshot':12} {round((time.monotonic() - t) * 1000):6} ms")

    steps = [("home", phone.home), ("tap clock", lambda: phone.tap(45, 22)),
             ("spotlight", lambda: phone.spotlight("Settings")), ("home", phone.home)]
    print(f"\n{'action':12} {'total':>7} {'capture':>8} {'input':>7} {'settle':>7}   input breakdown")
    for name, fn in steps:
        fn()
        e = json.loads((phone.log.dir / "log.jsonl").read_text().splitlines()[-1])
        tm = e.get("timing", {})
        calls = " ".join(f"{c['tool']}={c['ms']}" for c in tm.get("cua_calls", []))
        print(f"{name:12} {e['ms']:>5} ms {tm.get('grab_ms', 0):>6} ms {tm.get('input_ms', 0):>5} ms "
              f"{tm.get('settle_ms', 0):>5} ms   {calls}")
        time.sleep(0.5)
    if phone.cursor:
        time.sleep(3)  # let the pointer fade out
    print(f"\nlog: {phone.log.dir / 'log.jsonl'}")


if __name__ == "__main__":
    main()
