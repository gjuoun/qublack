#!/usr/bin/env python3
"""Assert that every QuBlack Mono @ keeps Recursive at.alt as its source outline.

Delta 5 shipped Recursive at.alt for @; delta 10s census then applied the same y-only affine to it.
The outline is still at.alt: x is untouched and y is an exact affine of the source, so this tool
checks x point-for-point and y up to that affine.

usage: check_at.py [--fonts fonts] [--donors <rec_mono dir>]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

import latin_masters
from build_qublack import DEFAULT_SOURCES  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
STYLES = ["Regular", "Italic", "Bold", "BoldItalic"]
DEFAULT_DONORS = DEFAULT_SOURCES / "rec_mono"


def points(font: TTFont, name: str) -> list[tuple[float, float]]:
    glyph = font["glyf"][name]
    coordinates = getattr(glyph, "coordinates", None)
    if coordinates is None:
        return []
    return [(float(x), float(y)) for x, y in coordinates]


def profile(points: list[tuple[float, float]]) -> list[float]:
    ys = [y for _, y in points]
    top, bottom = max(ys), min(ys)
    height = top - bottom or 1
    return [(y - bottom) / height for _, y in points]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fonts", type=Path, default=REPO / "fonts/ttf")
    parser.add_argument("--donors", type=Path, default=DEFAULT_DONORS)
    parser.add_argument("--style", default=None, help="check one style only")
    parser.add_argument(
        "--latin-vf",
        type=Path,
        default=None,
        help="compare against the instanced Recursive VF the build used, not the static donor",
    )
    args = parser.parse_args()

    styles = [args.style] if args.style else STYLES
    failures = 0
    for style in styles:
        built_path = args.fonts / f"QuBlackMono-{style}.ttf"
        donor_path = args.donors / f"RecursiveMonoLnrSt-{style}.ttf"
        if not built_path.exists() or (args.latin_vf is None and not donor_path.exists()):
            print(f"FAIL  {style}: missing {built_path.name} or {donor_path.name}")
            failures += 1
            continue

        built = TTFont(str(built_path))
        donor = (
            TTFont(str(donor_path))
            if args.latin_vf is None
            else latin_masters.instance(args.latin_vf, "mono", style, args.donors)
        )
        built_points = points(built, built.getBestCmap()[0x40])
        donor_points = points(donor, "at.alt")
        default_points = points(donor, "at")

        if len(built_points) != len(donor_points):
            failures += 1
            print(f"FAIL  QuBlackMono-{style}: @ has {len(built_points)} points, at.alt has {len(donor_points)}")
            continue

        cell = donor["hmtx"].metrics[donor.getBestCmap()[0x4D]][0]
        scale = 500.0 / cell
        x_error = max(abs(bx - round(scale * dx)) for (bx, _), (dx, _) in zip(built_points, donor_points))
        bp, dp = profile(built_points), profile(donor_points)
        y_error = max(abs(a - b) for a, b in zip(bp, dp))
        is_alt = len(built_points) != len(default_points)

        if x_error <= 1 and y_error <= 0.002 and is_alt:
            print(
                f"PASS  QuBlackMono-{style}: @ is at.alt ({len(built_points)} points, x error {x_error:.1f}, "
                f"y profile error {y_error:.4f})"
            )
        else:
            failures += 1
            print(f"FAIL  QuBlackMono-{style}: x error {x_error:.1f}, y profile error {y_error:.4f}, alt={is_alt}")

    print(f"at.alt check: {len(styles) - failures}/{len(styles)} mono faces keep Recursive outline")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
