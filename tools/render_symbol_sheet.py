#!/usr/bin/env python3
"""Render the QuBlack Mono vs Sarasa Term symbol sheet (PNG) for eyeballing.

Both faces are drawn at the same pixel size, so a hanzi is the same height in each column and the
symbol tops compare directly. The right-hand column prints the glyph's offset from the blended
target (in font units), so a regression is visible as a non-zero number.

usage: render_symbol_sheet.py [--out path.png] [--style Regular]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from symbol_targets import FIXED_SYMBOLS, QUOTE_BLEND, SYMBOL_BLEND, target  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
from build_qublack import DEFAULT_SOURCES  # noqa: E402

DONORS = DEFAULT_SOURCES
BG = (37, 41, 37)
FG = (217, 217, 212)
DIM = (140, 140, 136)
BLUE = (0, 176, 255)
LIME = (198, 255, 0)
SIZE = 46
ROW = 72


def ink(font: TTFont, char: str):
    name = font.getBestCmap().get(ord(char))
    if not name:
        return None
    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    return pen.bounds


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("/tmp/jun/qublack/sym-sheet-v1.0.2.png"))
    parser.add_argument("--style", default="Regular")
    args = parser.parse_args()

    face = REPO / f"fonts/QuBlackMono-{args.style}.ttf"
    qublack = ImageFont.truetype(str(face), SIZE)
    sarasa = ImageFont.truetype(str(DONORS / f"SarasaTermSC-{args.style}.ttf"), SIZE)
    mono = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", 15)
    heading = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", 28)

    built_font = TTFont(str(face))
    reference = TTFont(str(DONORS / f"SarasaTermSC-{args.style}.ttf"))
    upm = built_font["head"].unitsPerEm

    width = 1360
    top = 150
    height = top + ROW * len(FIXED_SYMBOLS) + 86
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)

    draw.text((48, 34), "QuBlack Mono  vs  Sarasa Term — symbol harmony", font=heading, fill=FG)
    draw.text(
        (48, 76),
        f"same pixel size · 汉 = 1.200em · ASCII advance untouched (0.600em) · blend "
        f"quotes {QUOTE_BLEND:.2f} / delimiters {SYMBOL_BLEND:.2f}",
        font=mono,
        fill=DIM,
    )

    col_q, col_s, col_d = 48, 560, 1080
    draw.text((col_q, 116), "QuBlack Mono", font=mono, fill=BLUE)
    draw.text((col_s, 116), "Sarasa Term SC", font=mono, fill=DIM)
    draw.text((col_d, 116), "Δ from target (units)", font=mono, fill=DIM)

    worst = 0.0
    for index, char in enumerate(FIXED_SYMBOLS):
        y = top + index * ROW
        draw.text((col_q, y), f"汉 {char} 汉", font=qublack, fill=FG)
        draw.text((col_s, y), f"汉 {char} 汉", font=sarasa, fill=FG)
        box = ink(built_font, char)
        expected = target(built_font, reference, char)
        delta = 0.0
        if box and expected:
            delta = max(abs(box[3] - expected[0]), abs((box[3] - box[1]) - expected[1]))
        worst = max(worst, delta)
        colour = LIME if delta <= 1.5 else BLUE
        draw.text((col_d, y + 20), f"{delta:+.1f}", font=mono, fill=colour)

    draw.text(
        (48, height - 46),
        f"worst offset {worst:.1f} units (tolerance 1.5) · fixed: quotes, brackets, braces, slash, backslash, bar",
        font=mono,
        fill=DIM,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.out)
    print(f"wrote {args.out} ({width}x{height}) worst={worst:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
