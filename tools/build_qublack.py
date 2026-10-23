#!/usr/bin/env python3
"""Build one QuBlack face from the Sarasa skeleton + Recursive Linear Latin donor.

The pipeline is the one that produced the shipped JunHei family, made explicit per mode:

  mono: SarasaTermSC skeleton, ASCII replaced with Recursive **Mono** Linear scaled into the
        500-unit cell, emoji stripped from the cmap, then the upm-833 trick (coordinates
        untouched, unitsPerEm 1000 -> 833) so 汉 = 1.200em and ASCII = 0.600em — a measured 2:1.
        `@` takes Recursive's `at.alt` alternate (the ss12 lookup target, a single-storey narrow
        design) instead of the default `at`; the sans family keeps the default.
  sans: SarasaGothicSC skeleton, ASCII replaced with Recursive **Sans** Linear at the donor's own
        advances, emoji stripped, then 0x2500-0x259F copied from the Term skeleton so box drawing
        stays half-width in a proportional face.

usage: build_qublack.py --mode mono|sans --style Regular|Italic|Bold|BoldItalic [options]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from fontTools.misc.transform import Transform
from fontTools.pens.pointPen import PointToSegmentPen
from fontTools.pens.recordingPen import DecomposingRecordingPointPen
from fontTools.pens.transformPen import TransformPointPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

import cjk_masters
from qublack_font import VERTICAL_TABLES, write_names

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SOURCES = Path.home() / "code/gjuoun/lishu-mono/assets/work"
# CJK outlines come from the variable donor so Regular and Bold share one master design. The
# donor is looked up as <sources>/NotoSansSC-VF.ttf unless --cjk-vf points somewhere else.
USE_CJK_DONOR = False
SLUGS = {"mono": "QuBlackMono", "sans": "QuBlackSans"}
DISPLAY = {"mono": "QuBlack Mono", "sans": "QuBlack Sans"}
# Symbols that sit against hanzi: Recursive draws them at Latin cap height, which after the
# upm-833 move leaves them ~23-24% of the em below the hanzi top. Sarasa keeps them nearly flush.
FIXED_SYMBOLS = ['"', "'", "(", ")", "[", "]", "{", "}", "/", "\\", "|"]

KEEP_RANGES = (
    (0x2190, 0x21FF),
    (0x2500, 0x257F),
    (0x2580, 0x259F),
    (0x25A0, 0x25FF),
    (0x2800, 0x28FF),
    (0xE000, 0xF8FF),
)


def drop_vertical(font: TTFont) -> None:
    for tag in VERTICAL_TABLES:
        if tag in font:
            del font[tag]


def emoji_codepoints(repo: Path) -> set[int]:
    table: set[int] = set()
    data = repo / "assets" / "emoji-data.txt"
    for line in data.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = re.match(r"^([0-9A-F.]+)\s*;\s*Emoji\s*#", line)
        if not match:
            continue
        span = match.group(1).split("..")
        table.update(range(int(span[0], 16), int(span[-1], 16) + 1))
    return table


def keep_codepoint(cp: int) -> bool:
    if cp <= 0x7F or cp in (0xA9, 0xAE, 0x2122):
        return True
    return any(lo <= cp <= hi for lo, hi in KEEP_RANGES)


def swap_latin(skeleton: TTFont, latin: TTFont, mode: str) -> int:
    """Replace ASCII outlines with the Recursive Linear donor. Never touches punctuation."""

    st_cmap, rc_cmap = skeleton.getBestCmap(), latin.getBestCmap()
    glyf, hmtx = skeleton["glyf"], skeleton["hmtx"]
    cell = latin["hmtx"].metrics[rc_cmap[0x4D]][0] if mode == "mono" else None
    swapped = 0
    donor_glyphs = set(latin.getGlyphOrder())
    for cp in range(0x20, 0x7F):
        source_name, target_name = st_cmap.get(cp), rc_cmap.get(cp)
        if not (source_name and target_name):
            continue
        # Mono ships the at.alt alternate: Recursive's GSUB maps `at` -> `at.alt` under ss12.
        if mode == "mono" and cp == 0x40 and "at.alt" in donor_glyphs:
            target_name = "at.alt"
        if mode == "mono":
            scale = 500.0 / cell
            width = 500
        else:
            scale = skeleton["head"].unitsPerEm / latin["head"].unitsPerEm
            width = int(round(latin["hmtx"].metrics[target_name][0] * scale))
        recorder = DecomposingRecordingPointPen(latin.getGlyphSet())
        latin.getGlyphSet()[target_name].drawPoints(TransformPointPen(recorder, Transform().scale(scale)))
        pen = TTGlyphPen(None)
        segment = PointToSegmentPen(pen)
        for op, args, *kwargs in recorder.value:
            getattr(segment, op)(*args, **(kwargs[0] if kwargs and kwargs[0] else {}))
        glyph = pen.glyph()
        glyph.recalcBounds(glyf)
        glyf[source_name] = glyph
        hmtx.metrics[source_name] = (width, glyph.xMin)
        swapped += 1
    return swapped


def strip_emoji(skeleton: TTFont, emoji: set[int]) -> int:
    removed = 0
    for table in skeleton["cmap"].tables:
        for cp in list(table.cmap):
            if cp in emoji and not keep_codepoint(cp):
                del table.cmap[cp]
                removed += 1
    return removed


def copy_range(source: TTFont, target: TTFont, lo: int, hi: int) -> int:
    source_cmap, target_cmap = source.getBestCmap(), target.getBestCmap()
    copied = 0
    for cp in range(lo, hi + 1):
        from_name, to_name = source_cmap.get(cp), target_cmap.get(cp)
        if not (from_name and to_name):
            continue
        target["glyf"][to_name] = source["glyf"][from_name]
        target["hmtx"].metrics[to_name] = source["hmtx"].metrics[from_name]
        copied += 1
    return copied


def apply_upm_trick(font: TTFont, new_upm: int = 833) -> None:
    old = font["head"].unitsPerEm
    scale = new_upm / float(old)
    font["head"].unitsPerEm = new_upm
    hhea = font["hhea"]
    hhea.ascender = round(hhea.ascender * scale)
    hhea.descender = round(hhea.descender * scale)
    hhea.lineGap = round(hhea.lineGap * scale)
    os2 = font["OS/2"]
    os2.usWinAscent = round(os2.usWinAscent * scale)
    os2.usWinDescent = round(os2.usWinDescent * scale)
    os2.sTypoAscender = round(os2.sTypoAscender * scale)
    os2.sTypoDescender = round(os2.sTypoDescender * scale)
    os2.sTypoLineGap = round(os2.sTypoLineGap * scale)


def strip_overlap_flags(font: TTFont) -> int:
    """Drop OVERLAP_SIMPLE (0x40) from every simple glyph.

    Chrome's OTS rejects a glyph whose flag stream carries bit 6 on any point but the first
    ("Bad glyph flag (115), bit 6 must be set to zero for flag 1"), which is exactly what the
    transplanted/decomposed outlines end up with. The flag is only a rasteriser hint, so clearing
    it costs nothing and makes the whole family loadable in Chrome.
    """
    cleared = 0
    for name in font.getGlyphOrder():
        glyph = font["glyf"][name]
        if getattr(glyph, "numberOfContours", 0) <= 0:
            continue
        if getattr(glyph, "overlap", False):
            glyph.overlap = False
            cleared += 1
        flags = getattr(glyph, "flags", None)
        if flags is None:
            continue
        for index in range(len(flags)):
            if int(flags[index]) & 0x40:
                flags[index] = int(flags[index]) & ~0x40
    return cleared


def _ink_units(glyph) -> tuple[float, float, float]:
    """(top, bottom, height) in font units for a simple glyph."""
    top, bottom = float(glyph.yMax), float(glyph.yMin)
    return top, bottom, top - bottom


# Blends live in tools/symbol_targets.py so the build and the audit cannot drift apart.
from symbol_targets import FIXED_SYMBOLS, target as symbol_target  # noqa: E402


def harmonize_symbols(font: TTFont, reference_path: Path) -> int:
    """Scale+translate (y only) the hanzi-adjacent symbols onto Sarasa's ink ratios.

    Recursive draws its ASCII punctuation around the Latin cap height; Sarasa Term keeps the same
    symbols nearly flush with the hanzi top. For each symbol we take Sarasa's two ratios — ink top
    below the hanzi top, and ink height — relative to its own hanzi ink box, then apply a vertical
    affine transform so QuBlack Mono reproduces them. Advance widths are untouched, so the 500-unit
    (0.600em) cell survives.
    """
    reference = TTFont(str(reference_path))
    if "汉" not in [chr(cp) for cp in reference.getBestCmap()]:
        return 0

    moved = 0
    for char in FIXED_SYMBOLS:
        name = font.getBestCmap().get(ord(char))
        if name is None:
            continue
        glyph = font["glyf"][name]
        if getattr(glyph, "numberOfContours", 0) <= 0:
            # Composites (percent, dollar, …) are flattened before scaling; hmtx keeps the advance.
            pen = TTGlyphPen(font.getGlyphSet())
            font.getGlyphSet()[name].draw(pen)
            glyph = pen.glyph()
            font["glyf"][name] = glyph
        if not hasattr(glyph, "coordinates"):
            continue
        glyph.recalcBounds(font["glyf"])
        target = symbol_target(font, reference, char)
        if target is None:
            continue
        target_top, target_height = target

        current_top, _, current_height = _ink_units(glyph)
        if current_height <= 0:
            continue
        scale = target_height / current_height
        shift = target_top - scale * current_top

        coordinates = glyph.coordinates
        for index in range(len(coordinates)):
            x, y = coordinates[index]
            coordinates[index] = (x, round(scale * y + shift))
        glyph.recalcBounds(font["glyf"])
        moved += 1
    return moved


def resolve_donor(value: str | None, sources: Path, disabled: bool) -> Path | None:
    """Turn the --cjk-vf flag into a donor path (None = keep the skeleton CJK)."""
    if disabled:
        return None
    donor = Path(value) if value and value != "auto" else cjk_masters.donor_for(sources)
    if not (value or USE_CJK_DONOR):
        return None
    if not donor.exists():
        raise SystemExit(f"missing CJK donor: {donor} (run python3 tools/fetch_cjk_vf.py)")
    return donor


def donor_paths(mode: str, style: str, sources: Path) -> tuple[Path, Path]:
    if mode == "mono":
        skeleton = sources / f"SarasaTermSC-{style}.ttf"
        latin = sources / "rec_mono" / f"RecursiveMonoLnrSt-{style}.ttf"
    else:
        skeleton = sources / f"SarasaGothicSC-{style}.ttf"
        latin = (
            sources
            / "ArrowType-Recursive-1.085/Recursive_Desktop/separate_statics/TTF"
            / f"RecursiveSansLnrSt-{style}.ttf"
        )
    return skeleton, latin


def build(mode: str, style: str, sources: Path, outdir: Path, repo: Path, cjk_vf: Path | None = None) -> Path:
    skeleton_path, latin_path = donor_paths(mode, style, sources)
    for path in (skeleton_path, latin_path):
        if not path.exists():
            raise SystemExit(f"missing donor: {path}")

    skeleton = TTFont(str(skeleton_path))
    latin = TTFont(str(latin_path))
    for font in (skeleton, latin):
        drop_vertical(font)
    assert skeleton["head"].unitsPerEm == 1000 and latin["head"].unitsPerEm == 1000

    slug, display = SLUGS[mode], DISPLAY[mode]
    print(f"[{slug}-{style}] latin swapped {swap_latin(skeleton, latin, mode)}", flush=True)
    print(f"[{slug}-{style}] emoji cmap entries removed {strip_emoji(skeleton, emoji_codepoints(repo))}", flush=True)

    if cjk_vf is not None:
        weight = cjk_masters.style_weight(style)
        master = cjk_masters.instance(cjk_vf, weight)
        installed = cjk_masters.install(skeleton, master, style)
        print(f"[{slug}-{style}] cjk installed {installed} (wght {weight})", flush=True)

    if mode == "sans":
        term = TTFont(str(sources / f"SarasaTermSC-{style}.ttf"))
        for font in (term,):
            drop_vertical(font)
        print(f"[{slug}-{style}] box drawing copied {copy_range(term, skeleton, 0x2500, 0x259F)}", flush=True)

    if mode == "mono":
        apply_upm_trick(skeleton, 833)
        print(
            f"[{slug}-{style}] symbols harmonised {harmonize_symbols(skeleton, skeleton_path)}",
            flush=True,
        )

    print(f"[{slug}-{style}] overlap flags cleared {strip_overlap_flags(skeleton)}", flush=True)
    write_names(skeleton, display, slug, style)
    skeleton["maxp"].numGlyphs = len(skeleton.getGlyphOrder())

    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{slug}-{style}.ttf"
    skeleton.save(str(out))
    print(f"[{slug}-{style}] saved {out}", flush=True)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=sorted(SLUGS), required=True)
    parser.add_argument("--style", choices=["Regular", "Italic", "Bold", "BoldItalic"], required=True)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--out", type=Path, default=REPO / "fonts")
    parser.add_argument(
        "--cjk-vf",
        nargs="?",
        const="auto",
        default=None,
        metavar="PATH",
        help="install CJK outlines from this variable donor (no value = <sources>/NotoSansSC-VF.ttf)",
    )
    parser.add_argument("--no-cjk-vf", action="store_true", help="keep the skeleton CJK outlines")
    args = parser.parse_args()
    donor = resolve_donor(args.cjk_vf, args.sources, args.no_cjk_vf)
    build(args.mode, args.style, args.sources, args.out, REPO, cjk_vf=donor)
    return 0


if __name__ == "__main__":
    sys.exit(main())
