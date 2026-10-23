#!/usr/bin/env python3
"""Render the full 44-symbol census sheet for QuBlack Mono (PNG).

Two columns of 22 rows: the glyph in QuBlack Mono, the deviation from Sarasa hanzi-relative ratio
(the metric the census was triggered by) and, for harmonised glyphs, the offset from the blended
target. Green means inside tolerance.

usage: render_census_sheet.py [--out path.png] [--style Regular]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from symbol_targets import CENSUS, FIXED_SYMBOLS, boxes, target  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
from build_qublack import DEFAULT_SOURCES  # noqa: E402

DONORS = DEFAULT_SOURCES
BG = (37, 41, 37)
FG = (217, 217, 212)
DIM = (140, 140, 136)
LIME = (198, 255, 0)
BLUE = (0, 176, 255)
SIZE = 40
ROW = 62


def ink(font: TTFont, char: str):
    name = font.getBestCmap().get(ord(char))
    if not name:
        return None
    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    return pen.bounds


def ratio(font: TTFont, char: str):
    box = ink(font, char)
    han = ink(font, "汉")
    if box is None or han is None:
        return None
    han_h = han[3] - han[1]
    return (han[3] - box[3]) / han_h, (box[3] - box[1]) / han_h


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("/tmp/jun/qublack/census-sheet-v1.0.3.png"))
    parser.add_argument("--style", default="Regular")
    args = parser.parse_args()

    face = REPO / f"fonts/QuBlackMono-{args.style}.ttf"
    font = TTFont(str(face))
    reference = TTFont(str(DONORS / f"SarasaTermSC-{args.style}.ttf"))
    han_top, han_h, cap_top, cap_h = boxes(font)
    upm = font["head"].unitsPerEm

    image_font = ImageFont.truetype(str(face), SIZE)
    mono = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", 13)
    heading = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", 26)

    columns = 2
    rows = (len(CENSUS) + columns - 1) // columns
    width = 1420
    top = 128
    height = top + rows * ROW + 60
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)

    draw.text((40, 28), "QuBlack Mono — 44-symbol census", font=heading, fill=FG)
    draw.text(
        (40, 68),
        "deviation from Sarasa hanzi-relative ratio · harmonised glyphs also show target offset · v1.0.3",
        font=mono,
        fill=DIM,
    )
    draw.text((40, 96), "harmonised: 32   untouched skeleton glyphs: 12", font=mono, fill=DIM)

    for index, char in enumerate(CENSUS):
        column = index // rows
        row = index % rows
        x = 40 + column * 700
        y = top + row * ROW
        draw.text((x, y), char, font=image_font, fill=FG)
        ours = ratio(font, char)
        theirs = ratio(reference, char)
        if ours is None or theirs is None:
            continue
        deviation = (ours[0] - theirs[0]) * 100
        if char in FIXED_SYMBOLS:
            expected = target(font, reference, char)
            delta = 0.0
            if expected is not None:
                delta = max(
                    abs((han_top - expected[0]) / han_h - ours[0]),
                    abs(expected[1] / han_h - ours[1]),
                ) * 100
            note = f"dev {deviation:+5.1f} pts · target {delta:4.1f}"
            colour = LIME if delta <= 2 else BLUE
        else:
            note = f"dev {deviation:+5.1f} pts · skeleton"
            colour = LIME if abs(deviation) <= 6 else BLUE
        draw.text((x + 52, y + 12), note, font=mono, fill=colour)

    draw.text(
        (40, height - 40),
        "harmonised = delta 8 brackets + delta 10 marks; skeleton glyphs (Latin-1, arrows) are never touched",
        font=mono,
        fill=DIM,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.out)
    print(f"wrote {args.out} ({width}x{height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
