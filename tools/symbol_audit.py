#!/usr/bin/env python3
"""Full-census audit of the symbols in Qu Black Mono (44 glyphs).

Harmonised glyphs (32): the built ink box must hit the blended target within 2 points of the
hanzi. Skeleton glyphs (Latin-1, arrows): they must sit within 6 points of Sarasa own ratio, the
band the census was triggered at.

usage: symbol_audit.py [--check] [--style Regular]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from symbol_targets import CENSUS, FIXED_SYMBOLS, QUOTE_BLEND, SYMBOL_BLEND, boxes, target  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
from build_qublack import DEFAULT_SOURCES  # noqa: E402

DEFAULT_DONORS = DEFAULT_SOURCES
STYLES = ["Regular", "Italic", "Bold", "BoldItalic"]
TOLERANCE = 0.02
UNTOUCHED_TOLERANCE = 0.06


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


def ratios(font: TTFont, char: str) -> tuple[float, float] | None:
    box = ink(font, char)
    han = ink(font, "汉")
    if box is None or han is None:
        return None
    han_h = han["top"] - han["bottom"]
    return ((han["top"] - box["top"]) / han_h, box["height"] / han_h)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fonts", type=Path, default=REPO / "fonts/ttf")
    parser.add_argument("--donors", type=Path, default=DEFAULT_DONORS)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--style", default=None)
    args = parser.parse_args()

    styles = [args.style] if args.style else STYLES
    failures = 0
    for style in styles:
        built = TTFont(str(args.fonts / f"QuBlackMono-{style}.ttf"))
        reference = TTFont(str(args.donors / f"SarasaTermSC-{style}.ttf"))
        han_top, han_h, cap_top, cap_h = boxes(built)
        problems: list[str] = []
        worst = 0.0
        rows: list[str] = []

        for char in CENSUS:
            built_ratio = ratios(built, char)
            sarasa_ratio = ratios(reference, char)
            if built_ratio is None or sarasa_ratio is None:
                continue
            deviation = (built_ratio[0] - sarasa_ratio[0]) * 100
            if char in FIXED_SYMBOLS:
                expected = target(built, reference, char)
                if expected is None:
                    continue
                tr = ((han_top - expected[0]) / han_h, expected[1] / han_h)
                delta = max(abs(built_ratio[0] - tr[0]), abs(built_ratio[1] - tr[1]))
                limit = TOLERANCE
            else:
                delta = max(abs(built_ratio[0] - sarasa_ratio[0]), abs(built_ratio[1] - sarasa_ratio[1]))
                limit = UNTOUCHED_TOLERANCE
            worst = max(worst, delta)
            if delta > limit:
                problems.append(f"{char!r} off by {delta * 100:.1f} points (census deviation {deviation:+.1f})")
            if not args.check:
                tag = "fix" if char in FIXED_SYMBOLS else "--"
                rows.append(f"  {char!r:6} {deviation:+7.1f} pts  {tag}")

        status = "PASS" if not problems else "FAIL"
        if problems:
            failures += 1
        print(
            f"{status}  QuBlackMono-{style}: {len(CENSUS) - len(problems)}/{len(CENSUS)} census symbols on target "
            f"(worst {worst * 100:.2f} points) · blend quotes {QUOTE_BLEND:.2f} / rest {SYMBOL_BLEND:.2f}"
        )
        for problem in problems[:6]:
            print(f"        {problem}")
        if rows and not args.check:
            print("   census (deviation from Sarasa hanzi-relative ratio):")
            print("\n".join(rows))

    print(f"symbol census: {len(styles) - failures}/{len(styles)} mono faces within tolerance across {len(CENSUS)} symbols")
    return 1 if (args.check and failures) else 0


if __name__ == "__main__":
    sys.exit(main())
