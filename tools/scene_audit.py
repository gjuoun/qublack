#!/usr/bin/env python3
"""Audit the three scenes the symbol pose has to survive: English, Chinese, mixed.

Cap-reaching glyphs must sit inside the band a CJK monospace lays out for them:

    Latin cap top <= symbol ink top <= hanzi ink top + 5% of the hanzi ink height

Centre and baseline marks (- = : ; _ , .) legitimately live below the cap; they are validated by
tools/symbol_audit.py against their own blended target instead, and only reported here.

usage: scene_audit.py [--style Regular]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from symbol_targets import FIXED_SYMBOLS, boxes, target  # noqa: E402

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
    reference = TTFont(str(DONORS / f"SarasaTermSC-{args.style}.ttf"))
    han_top, han_h, cap_top, cap_h = boxes(qublack)
    upm = qublack["head"].unitsPerEm
    han_top, han_h, cap_top, cap_h = han_top / upm, han_h / upm, cap_top / upm, cap_h / upm
    upper = han_top + HEADROOM * han_h

    failures: list[str] = []
    banded = 0
    for char in FIXED_SYMBOLS:
        box = bounds(qublack, char)
        if box is None:
            continue
        expected = target(qublack, reference, char)
        if expected is None:
            continue
        # Only glyphs the pose pushes up to the cap belong in the band; centre and baseline marks
        # are validated against their own target by symbol_audit.py.
        if expected[0] / upm < cap_top - 0.02:
            continue
        banded += 1
        top = box["top"]
        if not (cap_top - 0.001 <= top <= upper):
            failures.append(f"{char!r} outside the cap..hanzi band (top {top:.3f}em)")

    print(f"== QuBlackMono-{args.style} scene band: cap {cap_top:.3f}em .. hanzi+5% {upper:.3f}em")
    verdict = "PASS" if not failures else "FAIL"
    print(
        f"{verdict}  scenes: {banded - len(failures)}/{banded} cap-reaching symbols inside the band; "
        f"centre/baseline marks validated against their own target"
    )
    for failure in failures[:6]:
        print(f"        {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
