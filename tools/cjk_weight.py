#!/usr/bin/env python3
"""Report and assert the CJK weight of a built family, plus whether its weights can interpolate.

Two things are measured, both from outlines only (no rasteriser, no new dependency):

  weight  — the CJK horizontal stroke (`一` ink height), the CJK vertical stem (`丨` ink width),
            the Latin stem (`|` ink width) and the ratio between the last two. `一` and `丨` are
            plain bars, so their ink box *is* the stroke; `十` is not used because its ink box is
            the width of the crossbar.
  masters — the contour/point signature (numberOfContours, points) of a deterministic 500-glyph
            URO/ExtA sample, compared between the Regular and Bold face of the same family. Two
            masters can only be interpolated when those signatures agree; a mismatch means the
            family cannot grow a weight axis from its own outlines.

`--report` prints the numbers and exits 0. `--check` asserts the thresholds and exits non-zero:

  - Bold/Regular `一` stroke >= 1.45x        (the Bold face really is a bold)
  - Bold CJK/Latin stroke ratio within +-0.20 of 1.0 (CJK and Latin strokes match; the band is
    wider than one number because QuBlack Mono shrinks the em to 833, which raises every stroke
    relative to the em, while QuBlack Sans keeps upm 1000)
  - interpolable mismatch count == 0          (Regular and Bold share a point structure)

usage: cjk_weight.py --report <dir-or-face...> [--against <dir-or-face>]
       cjk_weight.py --check  <dir-or-face...>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fontTools.pens.areaPen import AreaPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

AREA_SAMPLE = "汉国图一永口黑白你好的们"
# Deterministic master-compatibility sample: sorted CJK Unified Ideographs + Extension A.
SAMPLE_RANGES = ((0x4E00, 0x9FFF),)
SAMPLE_SIZE = 500

STROKE_MIN = 1.45
RATIO_TOLERANCE = 0.20
FAMILIES = {"QuBlackMono": ("Regular", "Bold"), "QuBlackSans": ("Regular", "Bold")}


def faces(targets: list[Path]) -> list[Path]:
    found: list[Path] = []
    for path in targets:
        found.extend(sorted(path.glob("*.ttf")) if path.is_dir() else [path])
    return found


def centroid(path: Path) -> tuple[str, str]:
    """('QuBlackMono', 'Bold') from a QuBlack face filename."""
    family, _, style = path.stem.partition("-")
    return family, style


def ink_box(font: TTFont, char: str) -> tuple[float, float, float, float] | None:
    name = font.getBestCmap().get(ord(char))
    if name is None:
        return None
    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    if not pen.bounds:
        return None
    upm = font["head"].unitsPerEm
    return tuple(value / upm for value in pen.bounds)  # type: ignore[return-value]


def ink_area(font: TTFont, char: str) -> float | None:
    name = font.getBestCmap().get(ord(char))
    if name is None:
        return None
    pen = AreaPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    return abs(pen.value) / font["head"].unitsPerEm**2


def weight(path: Path) -> dict[str, float | None]:
    font = TTFont(str(path), lazy=True)
    box_yi, box_shu, box_bar = ink_box(font, "一"), ink_box(font, "丨"), ink_box(font, "|")
    cjk_h = box_yi[3] - box_yi[1] if box_yi else None
    cjk_v = box_shu[2] - box_shu[0] if box_shu else None
    latin = box_bar[2] - box_bar[0] if box_bar else None
    areas = [area for area in (ink_area(font, ch) for ch in AREA_SAMPLE) if area is not None]
    return {
        "一": round(cjk_h, 4) if cjk_h is not None else None,
        "丨": round(cjk_v, 4) if cjk_v is not None else None,
        "|": round(latin, 4) if latin is not None else None,
        "cjk_latin": round(cjk_v / latin, 3) if cjk_v and latin else None,
        "cjk_area": round(sum(areas) / len(areas), 4) if areas else None,
    }


def signatures(path: Path) -> dict[int, tuple[int, int]]:
    """Contour count + point count for the deterministic sample, keyed by codepoint."""
    font = TTFont(str(path), lazy=True)
    cmap = font.getBestCmap()
    glyf = font["glyf"]
    out: dict[int, tuple[int, int]] = {}
    for codepoint in sample_codepoints():
        name = cmap.get(codepoint)
        if name is None:
            continue
        glyph = glyf[name]
        points = len(glyph.coordinates) if hasattr(glyph, "coordinates") else 0
        out[codepoint] = (glyph.numberOfContours, points)
    return out


def sample_codepoints() -> list[int]:
    return [cp for low, high in SAMPLE_RANGES for cp in range(low, high + 1)]


def mismatch(regular: dict[int, tuple[int, int]], bold: dict[int, tuple[int, int]]) -> tuple[int, int, str]:
    shared = sorted(set(regular) & set(bold))[:SAMPLE_SIZE]
    differing = [codepoint for codepoint in shared if regular[codepoint] != bold[codepoint]]
    example = ""
    if differing:
        codepoint = differing[0]
        example = f" (e.g. {chr(codepoint)} {regular[codepoint]} vs {bold[codepoint]})"
    return len(differing), len(shared), example


def fmt(value: float | None, digits: int = 4) -> str:
    return "n/a" if value is None else f"{value:.{digits}f}"


def report(paths: list[Path], against: Path | None) -> int:
    reference = faces([against])[0] if against else None
    reference_weight = weight(reference) if reference else None
    for path in paths:
        data = weight(path)
        print(f"{path.name}")
        print(f"  一 {fmt(data['一'])}  (CJK horizontal stroke, em)")
        print(f"  丨 {fmt(data['丨'])}  (CJK vertical stem, em)")
        print(f"  | {fmt(data['|'])}  (Latin stem, em)")
        print(f"  cjk_latin {fmt(data['cjk_latin'], 3)}  cjk_area {fmt(data['cjk_area'])} em2")
        if reference_weight is not None:
            deltas = [
                abs(float(data[key]) - float(reference_weight[key]))
                for key in ("一", "丨", "|")
                if data[key] is not None and reference_weight[key] is not None
            ]
            print(f"  ±{max(deltas):.4f} vs {reference}")
    return 0


def check(paths: list[Path]) -> int:
    by_name = {path.name: path for path in paths}
    failures = 0
    measured = {path.name: weight(path) for path in paths}
    for family in sorted({centroid(path)[0] for path in paths}):
        regular_name, bold_name = (f"{family}-{style}.ttf" for style in FAMILIES.get(family, ("Regular", "Bold")))
        if regular_name not in by_name or bold_name not in by_name:
            print(f"SKIP {family}: needs both {regular_name} and {bold_name}")
            continue
        regular, bold = measured[regular_name], measured[bold_name]
        stroke = (bold["一"] or 0) / (regular["一"] or 1)
        status = "PASS" if stroke >= STROKE_MIN else "FAIL"
        failures += int(status == "FAIL")
        print(f"{status} {family} Bold/Regular 一 stroke {stroke:.2f}x (>= {STROKE_MIN:.2f}x)")
        ratio = bold["cjk_latin"] or 0
        inside = abs(ratio - 1.0) <= RATIO_TOLERANCE
        status = "PASS" if inside else "FAIL"
        failures += int(status == "FAIL")
        print(f"{status} {family} Bold CJK/Latin {ratio:.2f} (within {RATIO_TOLERANCE:.2f} of 1.00)")
        differing, shared, example = mismatch(signatures(by_name[regular_name]), signatures(by_name[bold_name]))
        status = "PASS" if differing == 0 else "FAIL"
        failures += int(status == "FAIL")
        print(f"{status} interpolable: {differing}/{shared} URO glyphs differ ({family}){example}")
    print(f"{failures} failure(s)")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--report", action="store_true", help="print the numbers (default)")
    mode.add_argument("--check", action="store_true", help="assert the thresholds")
    parser.add_argument("targets", nargs="+", type=Path)
    parser.add_argument("--against", type=Path, help="report the delta against this face or dir")
    args = parser.parse_args()

    paths = faces(args.targets)
    if not paths:
        print("no faces found", file=sys.stderr)
        return 2
    if args.check:
        return check(paths)
    return report(paths, args.against)


if __name__ == "__main__":
    sys.exit(main())
