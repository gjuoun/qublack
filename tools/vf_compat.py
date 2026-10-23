#!/usr/bin/env python3
"""Compare two built masters and say, glyph by glyph, whether a weight axis can interpolate them.

A variable font needs the same point structure on both masters. The v1.2.0 pipeline gets that for
ASCII (one Recursive VF instance per weight) and for the CJK the Noto donor covers, and cannot get
it for anything copied from Sarasa's independently drawn static weights — that tail is frozen at
the 400 outline by tools/vf_masters.py and this tool is the gate on how big the tail is.

Mismatch classes, all printed per Unicode block:

  ascii         0x20-0x7E, the swapped Latin — must be 0 after the donor swap
  noto-covered  CJK codepoints the Noto master carries (only CJK outlines are installed from it;
                Noto also maps Latin, but those glyphs still come from the Sarasa skeleton).
                Must stay under --max-noto: TTGlyphPen drops a coincident duplicate point, so a
                glyph whose donor points coincide at one weight comes out one point shorter.
                Measured: 2 of 27,897 CJK glyphs (U+5605, U+7A4A); a real break shows thousands.
  freeze        everything else — allowed, counted, and capped by --max-freeze

usage: vf_compat.py [--check] [--report] [--max-freeze N] [--max-noto N] <master400.ttf> <master700.ttf>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_qublack import DEFAULT_SOURCES  # noqa: E402
from cjk_masters import is_cjk  # noqa: E402

BLOCKS = [
    ("ascii", 0x20, 0x7E),
    ("latin-1", 0x80, 0xFF),
    ("latin-ext-a", 0x100, 0x17F),
    ("latin-ext-b", 0x180, 0x24F),
    ("ipa-spacing", 0x250, 0x2FF),
    ("greek", 0x370, 0x3FF),
    ("cyrillic", 0x400, 0x4FF),
    ("hebrew", 0x590, 0x5FF),
    ("arrows", 0x2190, 0x21FF),
    ("math", 0x2200, 0x22FF),
    ("tech", 0x2300, 0x23FF),
    ("box-block", 0x2500, 0x259F),
    ("geometric", 0x25A0, 0x25FF),
    ("misc-symbols", 0x2600, 0x27BF),
    ("braille", 0x2800, 0x28FF),
    ("kana", 0x3000, 0x30FF),
    ("hangul", 0xAC00, 0xD7A3),
    ("fullwidth", 0xFF00, 0xFFEF),
]


def signature(font: TTFont, name: str) -> tuple:
    """Everything varLib needs to agree on: contour count, point count, contour ends, on/off curve.

    The on/off-curve bits matter: two glyphs can share every count and still fail the merge when a
    point switches type, which is how U+4DB9 and a handful of Ext-B glyphs escaped the first pass.
    """
    glyph = font["glyf"][name]
    if glyph.isComposite():
        return ("composite", tuple((part.glyphName, part.x, part.y) for part in glyph.components))
    contours = getattr(glyph, "numberOfContours", 0)
    if contours <= 0:
        return ("empty",)
    flags = getattr(glyph, "flags", None)
    on_curve = tuple(int(value) & 1 for value in flags) if flags is not None else None
    return ("simple", contours, len(glyph.coordinates), tuple(glyph.endPtsOfContours), on_curve)


def block_for(codepoint: int) -> str:
    if is_cjk(codepoint):
        return "cjk"
    for name, low, high in BLOCKS:
        if low <= codepoint <= high:
            return name
    return "other"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("master400", type=Path)
    parser.add_argument("master700", type=Path)
    parser.add_argument("--noto", type=Path, default=DEFAULT_SOURCES / "NotoSansSC-VF.ttf")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--max-freeze", type=int, default=16_500)
    parser.add_argument("--max-noto", type=int, default=8)
    args = parser.parse_args()

    light = TTFont(str(args.master400))
    heavy = TTFont(str(args.master700))
    order_light, order_heavy = light.getGlyphOrder(), heavy.getGlyphOrder()
    cmap_light, cmap_heavy = light.getBestCmap(), heavy.getBestCmap()
    noto_cmap = TTFont(str(args.noto), lazy=True).getBestCmap() if args.noto.exists() else {}

    order_ok = order_light == order_heavy
    cmap_ok = set(cmap_light) == set(cmap_heavy)
    ascii_bad: list[int] = []
    noto_bad: list[int] = []
    buckets: dict[str, int] = {}
    for codepoint, name in cmap_light.items():
        other = cmap_heavy.get(codepoint)
        if other is None:
            noto_bad.append(codepoint)
            continue
        if signature(light, name) == signature(heavy, other):
            continue
        if 0x20 <= codepoint <= 0x7E:
            ascii_bad.append(codepoint)
        elif is_cjk(codepoint) and codepoint in noto_cmap:
            noto_bad.append(codepoint)
        else:
            key = block_for(codepoint)
            buckets[key] = buckets.get(key, 0) + 1

    freeze = sum(buckets.values())
    label = args.master400.stem.split("-")[0]
    status = "PASS"
    if not order_ok or not cmap_ok or ascii_bad or len(noto_bad) > args.max_noto or freeze > args.max_freeze:
        status = "FAIL"
    print(
        f"{status}  {label}: glyph order {'equal' if order_ok else 'DIFFERS'}, "
        f"ascii {len(ascii_bad)}, noto-covered {len(noto_bad)} of max {args.max_noto}, freeze {freeze}"
    )
    if args.report or status == "FAIL":
        for key, count in sorted(buckets.items(), key=lambda item: -item[1]):
            print(f"        freeze {key:14} {count}")
        if ascii_bad:
            print(f"        ascii mismatches: {''.join(chr(cp) for cp in ascii_bad)[:40]}")
        if noto_bad:
            print(f"        noto-covered mismatches: {' '.join(format(cp, '04X') for cp in noto_bad[:12])}")
    if args.report:
        print(f"        (cap {args.max_freeze}; freeze is the non-interpolatable tail frozen at wght 400)")
    return 1 if (args.check and status == "FAIL") else 0


if __name__ == "__main__":
    sys.exit(main())
