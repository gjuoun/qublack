#!/usr/bin/env python3
"""Render the QuBlack Mono vs Sarasa Term symbol-height sheet (PNG) for eyeballing.

Both faces are drawn at the same pixel size, so a hanzi is the same height in each column and the
symbol tops can be compared directly. A right-hand column prints the measured top-ratio delta.

usage: render_symbol_sheet.py [--out path.png] [--style Regular]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from symbol_audit import FIXED, reference, ratios  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DONORS = Path.home() / "code/gjuoun/lishu-mono/assets/work"
BG = (37, 41, 37)
FG = (217, 217, 212)
DIM = (140, 140, 136)
BLUE = (0, 176, 255)
LIME = (198, 255, 0)
SIZE = 46
ROW = 72


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("/tmp/jun/qublack/sym-sheet-v1.0.2.png"))
    parser.add_argument("--style", default="Regular")
    args = parser.parse_args()

    qublack = ImageFont.truetype(str(REPO / f"fonts/QuBlackMono-{args.style}.ttf"), SIZE)
    sarasa = ImageFont.truetype(str(DONORS / f"SarasaTermSC-{args.style}.ttf"), SIZE)
    mono = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", 15)
    heading = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", 28)

    built, _ = ratios(REPO / f"fonts/QuBlackMono-{args.style}.ttf", FIXED)
    target, _ = reference(args.style, DONORS)

    width = 1360
    top = 150
    height = top + ROW * len(FIXED) + 86
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)

    draw.text((48, 34), "QuBlack Mono  vs  Sarasa Term — symbol height harmony", font=heading, fill=FG)
    draw.text(
        (48, 76),
        "same pixel size · 汉 = 1.200em · ASCII advance untouched (0.600em) · v1.0.2",
        font=mono,
        fill=DIM,
    )

    col_q, col_s, col_d = 48, 560, 1110
    draw.text((col_q, 116), "QuBlack Mono", font=mono, fill=BLUE)
    draw.text((col_s, 116), "Sarasa Term SC", font=mono, fill=DIM)
    draw.text((col_d, 116), "Δ ink-top ratio", font=mono, fill=DIM)

    for index, char in enumerate(FIXED):
        y = top + index * ROW
        draw.text((col_q, y), f"汉 {char} 汉", font=qublack, fill=FG)
        draw.text((col_s, y), f"汉 {char} 汉", font=sarasa, fill=FG)
        delta = built[char]["topRatio"] - target[char]["topRatio"]
        colour = LIME if abs(delta) <= 0.02 else BLUE
        draw.text((col_d, y + 20), f"{delta * 100:+.1f} pts", font=mono, fill=colour)

    note = (
        "Fixed: quotes, brackets, braces, slash, backslash, bar. Unchanged by ruling: curly quotes, "
        "guillemets, < >, CJK punctuation."
    )
    draw.text((48, height - 46), note, font=mono, fill=DIM)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.out)
    print(f"wrote {args.out} ({width}x{height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
