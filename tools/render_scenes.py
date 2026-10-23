#!/usr/bin/env python3
"""Render the three-scenario symbol sheet: pure English, pure Chinese, mixed.

Each scene carries all of the fixed symbols and draws QuBlack Mono beside Sarasa Term at the same
pixel size, so the assessor can compare like with like. Output is one PNG per scene.

usage: render_scenes.py [--outdir /tmp/jun/qublack/scenes] [--style Regular]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

REPO = Path(__file__).resolve().parent.parent
from build_qublack import DEFAULT_SOURCES  # noqa: E402

DONORS = DEFAULT_SOURCES
BG = (37, 41, 37)
FG = (217, 217, 212)
DIM = (140, 140, 136)
BLUE = (0, 176, 255)

SCENES = {
    "en": [
        'const URL = "HTTPS://X.Y"; if (A[B] == C) { D(); }',
        "let S = 'it\\'s'; f(A / B) | g(C); // \"X\" [Y] {Z} \\ end",
        'const t = `${n} ms`; a = b + c * d % e ^ f; // #tag @me ~ x? ! _ = -',
    ],
    "cn": [
        "他说 \"引号\" 与 '单引号'，然后 (圆括号) [方括号] {大括号} 都要对齐。",
        "路径是 a/b\\\\c，或者用 | 表示“或者”，中文里也常见。",
        "价格 $5、折扣 10%、标签 #1 与 @ 提及，问号 ? 感叹 ! 加号 + 星号 * 也要齐。",
    ],
    "mixed": [
        'const 名字 = "汉字" + (值 / 2) | {键: [1, 2]};',
        '函数 f(x) { return 值 / 2 | 3; }  // 注释 \\ 结束',
        '`点了 ${count.value} 次` — a_b + c*d % e ^ f @ home #1 ; 问号? 感叹!',
    ],
}

SIZE = 34
LINE = 56


def ink_top(font: TTFont, char: str) -> float | None:
    name = font.getBestCmap().get(ord(char))
    if not name:
        return None
    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    if not pen.bounds:
        return None
    return pen.bounds[3] / font["head"].unitsPerEm


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, default=Path("/tmp/jun/qublack/scenes"))
    parser.add_argument("--style", default="Regular")
    parser.add_argument("--face", type=Path, default=None, help="QuBlack face to render (defaults to fonts/)")
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    face = args.face or (REPO / f"fonts/QuBlackMono-{args.style}.ttf")
    qublack = ImageFont.truetype(str(face), SIZE)
    sarasa = ImageFont.truetype(str(DONORS / f"SarasaTermSC-{args.style}.ttf"), SIZE)
    mono = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", 14)
    heading = ImageFont.truetype("/System/Library/Fonts/SFNS.ttf", 24)

    for scene, lines in SCENES.items():
        width = 1560
        height = 90 + len(lines) * LINE * 2 + 40
        image = Image.new("RGB", (width, height), BG)
        draw = ImageDraw.Draw(image)
        draw.text((32, 24), f"QuBlack Mono vs Sarasa Term — {scene.upper()} scene", font=heading, fill=FG)
        draw.text((32, 56), "top: QuBlack Mono (2:1 cell)   bottom: Sarasa Term SC (1:1 cell)", font=mono, fill=DIM)
        y = 96
        for line in lines:
            draw.text((32, y), line, font=qublack, fill=FG)
            draw.text((32, y + LINE), line, font=sarasa, fill=DIM)
            y += LINE * 2
        draw.text(
            (32, height - 32),
            'fixed glyphs: " \' ( ) [ ] { } / \\ |   — the same string in both faces',
            font=mono,
            fill=BLUE,
        )
        path = args.outdir / f"scene-{scene}.png"
        image.save(path)
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
