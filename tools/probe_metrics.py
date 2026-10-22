#!/usr/bin/env python3
"""Print the measurements that decide whether a face is acceptable. usage: probe_metrics.py <face...>"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qublack_font import CJK_SAMPLE, LATIN_SAMPLE, ink, open_font  # noqa: E402


def probe(path: str) -> None:
    font = open_font(path)
    upm = font["head"].unitsPerEm
    hhea = font["hhea"]
    os2 = font["OS/2"] if "OS/2" in font else None
    cmap = font.getBestCmap()
    hmtx = font["hmtx"].metrics
    print(f"\n== {Path(path).name}  upm={upm}")
    print(
        f"   hhea asc/desc/gap = {hhea.ascender / upm:.3f}/{hhea.descender / upm:.3f}/"
        f"{hhea.lineGap / upm:.3f}   (line = {(hhea.ascender - hhea.descender + hhea.lineGap) / upm:.3f}em)"
    )
    if os2 is not None:
        print(
            f"   typo asc/desc/gap = {os2.sTypoAscender / upm:.3f}/{os2.sTypoDescender / upm:.3f}/"
            f"{os2.sTypoLineGap / upm:.3f}  win={os2.usWinAscent / upm:.3f}/{-os2.usWinDescent / upm:.3f}"
        )
    for ch in CJK_SAMPLE:
        name = cmap.get(ord(ch))
        if name is None:
            print(f"   {ch}: MISSING")
            continue
        box = ink(font, ch)
        advance = hmtx[name][0] / upm
        if box is None:
            print(f"   {ch}: no outline")
            continue
        print(
            f"   {ch} adv={advance:.3f}em  ink w={box['w']:.3f} h={box['h']:.3f}  "
            f"x[{box['x']:+.3f},{box['x'] + box['w']:+.3f}] y[{box['y']:+.3f},{box['y'] + box['h']:+.3f}]  "
            f"bearing/side={(advance - box['w']) / 2:+.3f}"
        )
    for ch in LATIN_SAMPLE:
        box = ink(font, ch)
        name = cmap.get(ord(ch))
        if box is None or name is None:
            continue
        print(
            f"   [{ch}] adv={hmtx[name][0] / upm:.3f} ink h={box['h']:.3f} "
            f"y[{box['y']:+.3f},{box['y'] + box['h']:+.3f}]"
        )


for argument in sys.argv[1:]:
    probe(argument)
