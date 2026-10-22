#!/usr/bin/env python3
"""Assert that every QuBlack Mono face ships Recursive's `at.alt`, point for point.

The build imports the alternate through the same transform every other ASCII glyph gets (scaled
into the 500-unit cell), so the check scales the donor's `at.alt` by that same factor and compares
the resulting integer coordinates. A face still carrying the default `at` fails on point count and
on coordinates.

usage: check_at.py [--fonts fonts] [--donors <rec_mono dir>]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.misc.roundTools import otRound
from fontTools.ttLib import TTFont

REPO = Path(__file__).resolve().parent.parent
STYLES = ["Regular", "Italic", "Bold", "BoldItalic"]
DEFAULT_DONORS = Path.home() / "code/gjuoun/lishu-mono/assets/work/rec_mono"


def points(font: TTFont, name: str) -> list[tuple[int, int]]:
    glyph = font["glyf"][name]
    coordinates = getattr(glyph, "coordinates", None)
    if coordinates is None:
        return []
    return [(int(x), int(y)) for x, y in coordinates]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fonts", type=Path, default=REPO / "fonts")
    parser.add_argument("--donors", type=Path, default=DEFAULT_DONORS)
    args = parser.parse_args()

    failures = 0
    for style in STYLES:
        built_path = args.fonts / f"QuBlackMono-{style}.ttf"
        donor_path = args.donors / f"RecursiveMonoLnrSt-{style}.ttf"
        if not built_path.exists() or not donor_path.exists():
            print(f"FAIL  {style}: missing {built_path.name} or {donor_path.name}")
            failures += 1
            continue

        built = TTFont(str(built_path))
        donor = TTFont(str(donor_path))
        built_name = built.getBestCmap()[0x40]
        built_points = points(built, built_name)
        donor_points = points(donor, "at.alt")
        default_points = points(donor, "at")

        cell = donor["hmtx"].metrics[donor.getBestCmap()[0x4D]][0]
        scale = 500.0 / cell
        # The build scales the floats and fontTools rounds with otRound at compile time; doing the
        # same here makes the comparison exact rather than ±1 off a rounding convention.
        expected = [(otRound(x * scale), otRound(y * scale)) for x, y in donor_points]

        same_count = len(built_points) == len(expected)
        deltas = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(built_points, expected)]
        worst = max(deltas) if deltas else 0
        is_alt = len(built_points) != len(default_points)

        if same_count and worst == 0 and is_alt:
            print(
                f"PASS  QuBlackMono-{style}: @ is at.alt ({len(built_points)} points, "
                f"max coordinate delta {worst})"
            )
        else:
            failures += 1
            print(
                f"FAIL  QuBlackMono-{style}: points {len(built_points)} vs at.alt {len(expected)} / "
                f"at {len(default_points)}, worst delta {worst}"
            )

    print(f"at.alt check: {len(STYLES) - failures}/{len(STYLES)} mono faces match Recursive point-for-point")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
