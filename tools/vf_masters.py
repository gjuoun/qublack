#!/usr/bin/env python3
"""Freeze every glyph a weight axis cannot interpolate, so varLib can build the masters.

Two masters can only be merged where the outlines share a point structure. In the v1.2.0 pipeline
that is true for the ASCII (one Recursive VF instance per weight) and for the CJK the Noto donor
covers, and false for everything still drawn by Sarasa's independent static weights — Hangul, the
CJK tail Noto lacks, kana, box drawing, arrows, most Latin-1 symbols.

For those glyphs the 700 master takes the 400 outline, so `gvar` stores no delta: the VF keeps
full cmap coverage and the glyph simply does not embolden on the axis. The static Bold faces keep
their Sarasa-bold drawings; the loss is inside the variable file only, and it is counted here so
the number is never a surprise.

usage: vf_masters.py <master400.ttf> <master700.ttf> [--out-dir DIR]
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vf_compat import block_for, signature  # noqa: E402


def freeze(light: TTFont, heavy: TTFont) -> dict[str, int]:
    """Copy the 400 outline into the 700 master wherever the point structure differs."""
    if light.getGlyphOrder() != heavy.getGlyphOrder():
        raise SystemExit("masters have different glyph orders; freeze cannot reconcile that")

    reverse = {name: codepoint for codepoint, name in light.getBestCmap().items()}
    buckets: dict[str, int] = {}
    glyf_light, glyf_heavy = light["glyf"], heavy["glyf"]
    for name in light.getGlyphOrder():
        if signature(light, name) == signature(heavy, name):
            continue
        glyf_heavy[name] = copy.deepcopy(glyf_light[name])
        heavy["hmtx"].metrics[name] = light["hmtx"].metrics[name]
        key = block_for(reverse[name]) if name in reverse else "unencoded"
        buckets[key] = buckets.get(key, 0) + 1
    return buckets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("light", type=Path)
    parser.add_argument("heavy", type=Path)
    parser.add_argument("--out-dir", type=Path, default=None, help="write the frozen masters here")
    args = parser.parse_args()

    light = TTFont(str(args.light))
    heavy = TTFont(str(args.heavy))
    buckets = freeze(light, heavy)
    frozen = sum(buckets.values())
    print(f"frozen {frozen} glyphs at the wght 400 outline")
    for key, count in sorted(buckets.items(), key=lambda item: -item[1]):
        print(f"  {key:14} {count}")
    if args.out_dir:
        args.out_dir.mkdir(parents=True, exist_ok=True)
        light.save(str(args.out_dir / args.light.name))
        heavy.save(str(args.out_dir / args.heavy.name))
        print(f"saved frozen masters -> {args.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
