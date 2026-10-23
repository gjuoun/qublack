#!/usr/bin/env python3
"""Install CJK outlines from the pinned variable donor into a QuBlack skeleton.

Every face takes its hanzi from one weight-axis master set, so Regular and Bold come out of the
same interpolatable design instead of two independently drawn static weights:

    Regular / Italic      -> Noto Sans SC VF instanced at wght 400
    Bold / BoldItalic     -> Noto Sans SC VF instanced at wght 700

Instancing is expensive (~15 s for 31k glyphs), so the per-weight instances are cached under
`~/.cache/qublack/` keyed by donor size and weight. Only outlines are copied: `hmtx`, the cmap and
the glyph order stay exactly as the skeleton had them, which is what keeps the 2:1 grid and the
upm-833 trick independent of the donor.

Codepoints the donor does not carry (2,482 of Sarasa's CJK, mostly Extension B) keep the skeleton
outline, so they stay bold in the Bold faces; they are simply not interpolatable, and
`reference/CJK.md` records the boundary.

usage: cjk_masters.py <donor-vf> [--style Bold] [--report]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

CACHE = Path.home() / ".cache" / "qublack"
DEFAULT_DONOR = "NotoSansSC-VF.ttf"

# Sarasa's own italic CJK is a synthetic shear; fitted from SarasaTermSC Regular->Italic
# (x2 = x1 + k*y + c, 266 points, max residual 0.51 units) and confirmed on Bold->BoldItalic.
SHEAR_K = 0.16556
SHEAR_PIVOT = 333.16

STYLE_WEIGHT = {"Regular": 400, "Italic": 400, "Bold": 700, "BoldItalic": 700}
ITALIC_STYLES = ("Italic", "BoldItalic")

# Ranges whose outlines come from the donor. Everything else keeps the skeleton's drawing.
CJK_RANGES = (
    (0x3400, 0x4DBF),  # Extension A
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    (0xF900, 0xFAFF),  # CJK Compatibility Ideographs
    (0x20000, 0x2A6DF),  # Extension B
    (0x2A700, 0x2FA1F),  # Extensions C-F
)


def is_cjk(codepoint: int) -> bool:
    return any(low <= codepoint <= high for low, high in CJK_RANGES)


def style_weight(style: str) -> int:
    try:
        return STYLE_WEIGHT[style]
    except KeyError:
        raise SystemExit(f"unknown style {style!r}; expected one of {sorted(STYLE_WEIGHT)}") from None


def instance(donor: Path, wght: int, cache: Path = CACHE) -> TTFont:
    """Return the donor instanced at one weight, reusing the cached static when possible."""
    cache.mkdir(parents=True, exist_ok=True)
    cached = cache / f"{donor.stem}-{donor.stat().st_size}-w{wght}.ttf"
    if cached.exists():
        return TTFont(str(cached), lazy=True)
    print(f"[cjk] instancing {donor.name} at wght {wght}", flush=True)
    variable = TTFont(str(donor))
    static = instantiateVariableFont(variable, {"wght": wght}, inplace=True, updateFontNames=False)
    static.save(str(cached))
    return TTFont(str(cached), lazy=True)


def install(skeleton: TTFont, master: TTFont, style: str) -> int:
    """Replace CJK outlines in place. Returns how many glyphs were installed."""
    skeleton_cmap, master_cmap = skeleton.getBestCmap(), master.getBestCmap()
    master_glyphs = master.getGlyphSet()
    glyf = skeleton["glyf"]
    sheared = style in ITALIC_STYLES
    installed = 0

    for codepoint, skeleton_name in skeleton_cmap.items():
        if not is_cjk(codepoint):
            continue
        master_name = master_cmap.get(codepoint)
        if master_name is None:
            continue  # hybrid boundary: keep the skeleton outline
        if master_name not in master_glyphs:
            continue

        recorder = DecomposingRecordingPen(master_glyphs)
        master_glyphs[master_name].draw(recorder)
        pen = TTGlyphPen(None)
        for operation, args, *kwargs in recorder.value:
            getattr(pen, operation)(*args, **(kwargs[0] if kwargs and kwargs[0] else {}))
        glyph = pen.glyph()

        if sheared and hasattr(glyph, "coordinates"):
            coordinates = glyph.coordinates
            for index in range(len(coordinates)):
                x, y = coordinates[index]
                coordinates[index] = (round(x + SHEAR_K * (y - SHEAR_PIVOT)), y)

        glyph.recalcBounds(glyf)
        glyf[skeleton_name] = glyph
        installed += 1

    return installed


def donor_for(sources: Path) -> Path:
    return sources / DEFAULT_DONOR


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("donor", type=Path)
    parser.add_argument("--style", default=None, help="install into a skeleton style and report the count")
    parser.add_argument("--skeleton", type=Path, help="skeleton to patch, required with --style")
    parser.add_argument("--out", type=Path, help="where to save the patched skeleton")
    args = parser.parse_args()

    if args.style is None:
        print(f"donor {args.donor} cached instances in {CACHE}")
        return 0
    if args.skeleton is None or args.out is None:
        print("--style needs --skeleton and --out", file=sys.stderr)
        return 2

    skeleton = TTFont(str(args.skeleton))
    master = instance(args.donor, style_weight(args.style))
    count = install(skeleton, master, args.style)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    skeleton.save(str(args.out))
    print(f"cjk installed {count} (wght {style_weight(args.style)}) -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
