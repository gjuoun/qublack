#!/usr/bin/env python3
"""Audit the height of the symbols that sit next to hanzi in QuBlack Mono.

Recursive draws its ASCII punctuation around the Latin cap height; after the upm-833 move that puts
quotes, brackets, braces and slashes ~23-24% of the em below the hanzi top, while Sarasa Term keeps
them nearly flush. This tool measures both faces with one definition — the glyph's ink top relative
to the hanzi ink box — and asserts the QuBlack faces land on the Sarasa ratio.

  top ratio    = (hanzi ink top - glyph ink top) / hanzi ink height
  height ratio = glyph ink height / hanzi ink height

Both are scale-free, so a face at upm 833 and one at upm 1000 compare directly.

usage:
  symbol_audit.py                      # report every face against its Sarasa counterpart
  symbol_audit.py --check              # exit 1 if any fixable glyph is off by more than 2 points
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

REPO = Path(__file__).resolve().parent.parent
DEFAULT_DONORS = Path.home() / "code/gjuoun/lishu-mono/assets/work"
STYLES = ["Regular", "Italic", "Bold", "BoldItalic"]

# The 11 characters the delta fixes (13 glyph names once the two quote pairs are counted).
FIXED = ['"', "'", "(", ")", "[", "]", "{", "}", "/", "\\", "|"]
# Measured and deliberately left alone (recorded so the next audit does not re-open them).
UNTOUCHED = {"\u201c": "already flush", "\u201d": "already flush", "\u2018": "already flush",
             "\u2019": "already flush", "\u00ab": "matches Sarasa", "\u00bb": "matches Sarasa",
             "<": "math convention", ">": "math convention", "\u2026": "QuBlack better than Sarasa",
             "\u3001": "CJK skeleton", "\u3002": "CJK skeleton", "\uff1a": "CJK skeleton",
             "\uff1b": "CJK skeleton", "\u300d": "CJK convention"}
HANZI = "\u6c49"
TOLERANCE = 0.02


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


def ratios(path: Path, chars: list[str]) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    font = TTFont(str(path))
    hanzi = ink(font, HANZI)
    if hanzi is None:
        raise SystemExit(f"{path}: no hanzi glyph")
    out: dict[str, dict[str, float]] = {}
    for char in chars:
        box = ink(font, char)
        if box is None:
            continue
        out[char] = {
            "top": box["top"],
            "bottom": box["bottom"],
            "height": box["height"],
            "topRatio": (hanzi["top"] - box["top"]) / hanzi["height"],
            "heightRatio": box["height"] / hanzi["height"],
        }
    return out, hanzi


def reference(style: str, donors: Path) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    return ratios(donors / f"SarasaTermSC-{style}.ttf", FIXED)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fonts", type=Path, default=REPO / "fonts")
    parser.add_argument("--donors", type=Path, default=DEFAULT_DONORS)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    failures = 0
    for style in STYLES:
        built, hanzi = ratios(args.fonts / f"QuBlackMono-{style}.ttf", FIXED)
        target, _ = reference(style, args.donors)
        worst = 0.0
        problems: list[str] = []
        for char in FIXED:
            if char not in built or char not in target:
                continue
            top_delta = built[char]["topRatio"] - target[char]["topRatio"]
            height_delta = built[char]["heightRatio"] - target[char]["heightRatio"]
            worst = max(worst, abs(top_delta), abs(height_delta))
            if abs(top_delta) > TOLERANCE or abs(height_delta) > TOLERANCE:
                problems.append(
                    f"{char!r} top {built[char]['topRatio'] * 100:+.1f}% vs "
                    f"{target[char]['topRatio'] * 100:+.1f}%, height {built[char]['heightRatio'] * 100:+.1f}% vs "
                    f"{target[char]['heightRatio'] * 100:+.1f}%"
                )
        status = "PASS" if not problems else "FAIL"
        if problems:
            failures += 1
        print(
            f"{status}  QuBlackMono-{style}: {len(FIXED) - len(problems)}/{len(FIXED)} symbols on the "
            f"Sarasa ratio (worst delta {worst * 100:.2f} points, tolerance {TOLERANCE * 100:.0f})"
        )
        for problem in problems[:4]:
            print(f"        {problem}")

    print(
        f"symbol heights: {len(STYLES) - failures}/{len(STYLES)} mono faces match Sarasa within "
        f"{TOLERANCE * 100:.0f} points"
    )
    if not args.check:
        print("untouched by ruling: " + ", ".join(f"{char} ({why})" for char, why in UNTOUCHED.items()))
    return 1 if (args.check and failures) else 0


if __name__ == "__main__":
    sys.exit(main())
