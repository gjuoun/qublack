#!/usr/bin/env python3
"""Instance the pinned Recursive variable donor into the Latin master each style needs.

Recursive ships five axes (MONO, CASL, wght, slnt, CRSV). QuBlack Linear is one point in that
space; only wght and slnt move between faces:

    mono  MONO=1  CASL=0  CRSV=0
    sans  MONO=0  CASL=0  CRSV=0
    upright italics  slnt=0 / slnt=-15      wght 400 / 700

Instancing is cheap (1,304 glyphs, ~1 s) but repeated eight times per build, so the per-style
results are cached under ~/.cache/qublack keyed by donor size, mode and style.

Measured: at these coordinates the instance reproduces the shipped Recursive statics to within
0.9 units of ink bounds on all 94 mapped ASCII glyphs — same drawing, minus the overlap removal
the statics carry.

usage: latin_masters.py <donor-vf> [--mode mono] [--style Regular] [--out face.ttf]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

CACHE = Path.home() / ".cache" / "qublack"
DEFAULT_DONOR = "Recursive_VF_1.085.ttf"

# Everything the Linear design pins, except the two axes a face is allowed to move along.
MODE_AXES = {
    "mono": {"MONO": 1.0, "CASL": 0.0, "CRSV": 0.0},
    "sans": {"MONO": 0.0, "CASL": 0.0, "CRSV": 0.0},
}
STYLE_AXES = {
    "Regular": {"wght": 400.0, "slnt": 0.0},
    "Bold": {"wght": 700.0, "slnt": 0.0},
    "Italic": {"wght": 400.0, "slnt": -15.0},
    "BoldItalic": {"wght": 700.0, "slnt": -15.0},
}


def donor_for(sources: Path) -> Path:
    return sources / DEFAULT_DONOR


def location(mode: str, style: str) -> dict[str, float]:
    try:
        axes = dict(MODE_AXES[mode])
        axes.update(STYLE_AXES[style])
    except KeyError as error:
        raise SystemExit(f"unknown {error.args[0]!r}; expected {sorted(MODE_AXES)} / {sorted(STYLE_AXES)}") from None
    return axes


def instance(donor: Path, mode: str, style: str, cache: Path = CACHE) -> TTFont:
    """Return the donor instanced at one style, reusing the cached static when possible."""
    cache.mkdir(parents=True, exist_ok=True)
    cached = cache / f"{donor.stem}-{donor.stat().st_size}-{mode}-{style}.ttf"
    if cached.exists():
        return TTFont(str(cached), lazy=True)
    print(f"[latin] instancing {donor.name} at {mode}/{style} {location(mode, style)}", flush=True)
    variable = TTFont(str(donor))
    static = instantiateVariableFont(variable, location(mode, style), inplace=True, updateFontNames=False)
    static.save(str(cached))
    return TTFont(str(cached), lazy=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("donor", type=Path)
    parser.add_argument("--mode", choices=sorted(MODE_AXES), default="mono")
    parser.add_argument("--style", choices=sorted(STYLE_AXES), default="Regular")
    parser.add_argument("--out", type=Path, help="write the instance here")
    args = parser.parse_args()

    master = instance(args.donor, args.mode, args.style)
    axes = {axis.axisTag: (axis.minValue, axis.defaultValue, axis.maxValue) for axis in []}
    print(f"instance {args.mode}/{args.style} {location(args.mode, args.style)} glyphs {len(master.getGlyphOrder())}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        master.save(str(args.out))
        print(f"saved {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
