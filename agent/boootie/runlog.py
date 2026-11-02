"""Run folder: one per server/script start, holding a log.jsonl and annotated frames.

    runs/2026-11-02_14-03-11/
        log.jsonl                 one line per tool call
        003_tap.png               the frame the action was aimed at, target drawn on it
        003_tap_after.jpg         what the screen looked like once it settled
"""

from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw

DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "runs"
RED, BLUE = (255, 40, 90), (0, 160, 255)


class RunLog:
    def __init__(self, root: Path | None = None, label: str = ""):
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.dir = Path(root or DEFAULT_ROOT) / (stamp + (f"_{label}" if label else ""))
        self.dir.mkdir(parents=True, exist_ok=True)
        self.n = 0

    def next(self) -> int:
        self.n += 1
        return self.n

    def save(self, img: Image.Image, name: str) -> str:
        path = self.dir / name
        img.save(path, quality=85) if name.endswith(".jpg") else img.save(path)
        return name

    def write(self, entry: dict) -> None:
        entry = {"ts": datetime.now().isoformat(timespec="milliseconds"), **entry}
        with open(self.dir / "log.jsonl", "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")


def draw_marks(img: Image.Image, marks: list[dict]) -> Image.Image:
    """Draw targets on a copy of the frame: dots for taps, arrows for swipes/scrolls."""
    out = img.copy()
    d = ImageDraw.Draw(out)
    for m in marks:
        if m["kind"] == "dot":
            x, y, r = m["x"], m["y"], m.get("r", 9)
            color = BLUE if m.get("long") else RED
            d.ellipse([x - r, y - r, x + r, y + r], outline=color, width=3)
            d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=color)
        elif m["kind"] == "arrow":
            _arrow(d, m["x1"], m["y1"], m["x2"], m["y2"])
        elif m["kind"] == "text":
            d.rectangle([0, 0, out.width, 22], fill=(0, 0, 0))
            d.text((6, 5), m["text"][:70], fill=(255, 255, 255))
    return out


def _arrow(d: ImageDraw.ImageDraw, x1, y1, x2, y2) -> None:
    d.line([x1, y1, x2, y2], fill=RED, width=4)
    d.ellipse([x1 - 5, y1 - 5, x1 + 5, y1 + 5], outline=RED, width=3)
    ang = math.atan2(y2 - y1, x2 - x1)
    for side in (-0.5, 0.5):
        a = ang + math.pi + side
        d.line([x2, y2, x2 + 16 * math.cos(a), y2 + 16 * math.sin(a)], fill=RED, width=4)


def main() -> None:
    """`uv run boootie-runs [N]`: summarise the last N runs (steps per run) for tasks.md."""
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    runs = sorted(p for p in DEFAULT_ROOT.glob("*") if (p / "log.jsonl").exists())[-n:]
    if not runs:
        print(f"no runs in {DEFAULT_ROOT}")
        return
    for run in runs:
        lines = [json.loads(l) for l in (run / "log.jsonl").read_text().splitlines() if l.strip()]
        actions = [l for l in lines if l["tool"] != "screenshot"]
        errors = [l for l in lines if l.get("error")]
        secs = sum(l.get("ms", 0) for l in lines) / 1000
        tools = " ".join(l["tool"] for l in actions)
        print(f"{run.name}: {len(actions)} actions, {len(lines) - len(actions)} screenshots, "
              f"{len(errors)} errors, {secs:.0f}s in tools")
        print(f"    {tools[:200]}")
