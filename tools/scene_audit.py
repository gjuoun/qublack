#!/usr/bin/env python3
"""Audit the three scenes the symbol pose has to survive: English, Chinese, mixed.

One criterion covers all three: the symbol's ink top must sit inside the band a CJK monospace lays
out for it —

    Latin cap top  <=  symbol ink top  <=  hanzi ink top + 5% of the hanzi ink height

In pure English that keeps the symbols just above the caps (the CJK-mono convention the ruling
accepts); in pure Chinese they lean toward the hanzi top; in mixed lines they never step outside
the taller of their two neighbours, so the transition stays smooth. The 5% headroom mirrors Sarasa,
whose parens exceed its own hanzi top by ~1.7%.

The pose itself is asserted by tools/symbol_audit.py against the blended target; this tool checks
the scene-level consequences and prints the numbers gemini-4-argon judges from the PNGs.

usage: scene_audit.py [--style Regular]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from symbol_targets import FIXED_SYMBOLS, boxes  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DONORS = Path.home() / "code/gjuoun/lishu-mono/assets/work"
HEADROOM = 0.05


def bounds(font: TTFont, char: str) -> dict[str, float] | None:
    name = font.getBestCmap().get(ord(char))
    if not name:
        return None
    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    if not pen.bounds:
        return None
    upm = font["head"].unitsPerEm
    x0, y0, x1, y1 = (value / upm for value in pen.bounds)
    return {"top": y1, "bottom": y0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--style", default="Regular")
    parser.add_argument("--fonts", type=Path, default=REPO / "fonts")
    args = parser.parse_args()

    qublack = TTFont(str(args.fonts / f"QuBlackMono-{args.style}.ttf"))
    han_top, han_h, cap_top, cap_h = boxes(qublack)
    upm = qublack["head"].unitsPerEm
    han_top, han_h, cap_top, cap_h = han_top / upm, han_h / upm, cap_top / upm, cap_h / upm
    upper = han_top + HEADROOM * han_h

    failures: list[str] = []
    rows: list[str] = []
    for char in FIXED_SYMBOLS:
        box = bounds(qublack, char)
        if box is None:
            continue
        top = box["top"]
        above_cap = (top - cap_top) / cap_h
        below_han = (han_top - top) / han_h
        rows.append(
            f"  {char!r:4} top {top:.3f}em · cap +{above_cap * 100:.0f}% · hanzi -{below_han * 100:.1f}%"
        )
        if not (cap_top - 0.001 <= top <= upper):
            failures.append(f"{char!r} outside the cap..hanzi band (top {top:.3f}em)")

    print(f"== QuBlackMono-{args.style} scene band: cap {cap_top:.3f}em .. hanzi+5% {upper:.3f}em")
    print("\n".join(rows))
    verdict = "PASS" if not failures else "FAIL"
    print(
        f"{verdict}  scenes: EN symbols sit above the cap, CN leans to the hanzi top, "
        f"mixed lines bridge both ({len(FIXED_SYMBOLS) - len(failures)}/{len(FIXED_SYMBOLS)} inside the band)"
    )
    for failure in failures[:6]:
        print(f"        {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
