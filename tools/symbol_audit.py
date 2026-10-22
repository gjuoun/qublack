#!/usr/bin/env python3
"""Audit the height of the symbols that sit next to hanzi in QuBlack Mono.

Recursive draws its ASCII punctuation around the Latin cap height; after the upm-833 move that put
quotes, brackets, braces and slashes far below the hanzi top, while Sarasa Term keeps them nearly
flush. The two references disagree in a 2:1 cell (hanzi-flush is perfect in Chinese but oversized in
English), so tools/symbol_targets.py blends them per glyph class and this tool asserts the built
faces hit that blended target exactly — the same target the build applies.

Reported alongside, for the three scenes the pose has to survive:
  CN  the glyph's ink top relative to the hanzi ink box (blended away from Sarasa's pure ratio)
  EN  the headroom above the Latin cap, as a share of cap height

usage: symbol_audit.py [--check]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from symbol_targets import FIXED_SYMBOLS, QUOTE_BLEND, SYMBOL_BLEND, boxes, target  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DONORS = Path.home() / "code/gjuoun/lishu-mono/assets/work"
STYLES = ["Regular", "Italic", "Bold", "BoldItalic"]
TOLERANCE_UNITS = 1.5
UNTOUCHED = {"\u201c": "already flush", "\u201d": "already flush", "\u2018": "already flush",
             "\u2019": "already flush", "\u00ab": "matches Sarasa", "\u00bb": "matches Sarasa",
             "<": "math convention", ">": "math convention", "\u2026": "QuBlack better than Sarasa",
             "\u3001": "CJK skeleton", "\u3002": "CJK skeleton", "\uff1a": "CJK skeleton",
             "\uff1b": "CJK skeleton", "\u300d": "CJK convention"}


def ink(font: TTFont, char: str) -> dict[str, float] | None:
    name = font.getBestCmap().get(ord(char))
    if name is None:
        return None
    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    if not pen.bounds:
        return None
    upm = font["head"].unitsPerEm
    x0, y0, x1, y1 = (value / upm for value in pen.bounds)
    return {"top": y1, "bottom": y0, "height": y1 - y0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fonts", type=Path, default=REPO / "fonts")
    parser.add_argument("--donors", type=Path, default=DEFAULT_DONORS)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    failures = 0
    for style in STYLES:
        built = TTFont(str(args.fonts / f"QuBlackMono-{style}.ttf"))
        reference = TTFont(str(args.donors / f"SarasaTermSC-{style}.ttf"))
        han_top, han_h, cap_top, cap_h = boxes(built)
        problems: list[str] = []
        worst = 0.0
        for char in FIXED_SYMBOLS:
            expected = target(built, reference, char)
            box = ink(built, char)
            if expected is None or box is None:
                continue
            upm = built["head"].unitsPerEm
            top_units = box["top"] * upm
            height_units = box["height"] * upm
            delta = max(abs(top_units - expected[0]), abs(height_units - expected[1]))
            worst = max(worst, delta)
            if delta > TOLERANCE_UNITS:
                problems.append(f"{char!r} off by {delta:.1f} units")
        status = "PASS" if not problems else "FAIL"
        if problems:
            failures += 1
        print(
            f"{status}  QuBlackMono-{style}: {len(FIXED_SYMBOLS) - len(problems)}/{len(FIXED_SYMBOLS)} "
            f"symbols on the blended target (worst {worst:.1f} units, tolerance {TOLERANCE_UNITS}) · "
            f"blend quotes {QUOTE_BLEND:.2f} / delimiters {SYMBOL_BLEND:.2f}"
        )
        for problem in problems[:4]:
            print(f"        {problem}")

        # scene context, informational
        if not args.check:
            cap_pct = []
            han_pct = []
            for char in FIXED_SYMBOLS:
                box = ink(built, char)
                if not box:
                    continue
                cap_pct.append((box["top"] - cap_top / upm) / (cap_h / upm) * 100)
                han_pct.append((han_top / upm - box["top"]) / (han_h / upm) * 100)
            print(
                f"        EN scene: symbols sit {min(cap_pct):+.0f}%..{max(cap_pct):+.0f}% of cap height above cap · "
                f"CN scene: {min(han_pct):.1f}%..{max(han_pct):.1f}% below the hanzi top"
            )

    print(
        f"symbol heights: {len(STYLES) - failures}/{len(STYLES)} mono faces on the blended target"
    )
    if not args.check:
        print("untouched by ruling: " + ", ".join(f"{char} ({why})" for char, why in UNTOUCHED.items()))
    return 1 if (args.check and failures) else 0


if __name__ == "__main__":
    sys.exit(main())
