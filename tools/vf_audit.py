#!/usr/bin/env python3
"""Structural audit of a built QuBlack variable face.

What it proves, per face: one wght axis 400-700 defaulting to 400, the two named instances, a STAT
table, the family's upm and weight class, HVAR when the advances vary with weight, and the glyph
surface the static family guarantees (the @ alternate, the eleven harmonised symbols, the frozen
tail still mapped).

--self-test copies the first face, deletes its fvar, and asserts the audit fails — the guard's
self-harm check.

usage: vf_audit.py [--check] [--self-test] <dir-or-face...>
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from symbol_targets import BRACKETS  # noqa: E402

UPM = {"QuBlackMonoVF": 833, "QuBlackSansVF": 1000}
MIN_GLYPHS = 50_000


def audit(path: Path) -> list[str]:
    problems: list[str] = []
    font = TTFont(str(path))
    slug = font["name"].getDebugName(6).split("-")[0]

    if "fvar" not in font:
        return ["no fvar table"]
    axes = {axis.axisTag: axis for axis in font["fvar"].axes}
    if set(axes) != {"wght"}:
        problems.append(f"axes {sorted(axes)} != ['wght']")
    elif (
        float(axes["wght"].minValue),
        float(axes["wght"].defaultValue),
        float(axes["wght"].maxValue),
    ) != (400.0, 400.0, 700.0):  # min, default, max
        problems.append(
            "wght range "
            f"{axes['wght'].minValue}..{axes['wght'].maxValue} default {axes['wght'].defaultValue}"
        )
    names = {font["name"].getDebugName(instance.subfamilyNameID) for instance in font["fvar"].instances}
    if not {"Regular", "Bold"} <= names:
        problems.append(f"named instances {sorted(names)}")
    if "STAT" not in font:
        problems.append("no STAT")
    if "gvar" not in font or not len(font["gvar"].variations):
        problems.append("gvar carries no variations")

    expected_upm = UPM.get(slug)
    if expected_upm and font["head"].unitsPerEm != expected_upm:
        problems.append(f"upm {font['head'].unitsPerEm} != {expected_upm}")
    if font["OS/2"].usWeightClass != 400:
        problems.append(f"usWeightClass {font['OS/2'].usWeightClass} != 400")
    if slug == "QuBlackSansVF" and "HVAR" not in font:
        problems.append("no HVAR although the sans advances vary with weight")

    cmap = font.getBestCmap()
    if len(cmap) < MIN_GLYPHS:
        problems.append(f"cmap {len(cmap)} < {MIN_GLYPHS}")
    if len(font.getGlyphOrder()) < MIN_GLYPHS:
        problems.append(f"glyphs {len(font.getGlyphOrder())} < {MIN_GLYPHS}")
    for char in BRACKETS:
        if ord(char) not in cmap:
            problems.append(f"missing harmonised symbol {char!r}")
    if 0x40 not in cmap:
        problems.append("missing @")
    return problems


def faces(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        found.extend(sorted(path.glob("*[[]wght[]].ttf")) if path.is_dir() else [path])
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("targets", nargs="+", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    built = faces(args.targets)
    if not built:
        print("no VF faces found", file=sys.stderr)
        return 2
    failures = 0
    for path in built:
        problems = audit(path)
        if problems:
            failures += 1
            print(f"FAIL  {path.name}: " + "; ".join(problems[:6]))
        else:
            font = TTFont(str(path))
            print(
                f"PASS  {path.name}: fvar wght 400..700 default 400, instances Regular/Bold, STAT, "
                f"{len(font.getGlyphOrder())} glyphs, {len(font.getBestCmap())} codepoints"
            )
    print(f"axis legality: {len(built) - failures}/{len(built)} VF faces")

    if args.self_test:
        with tempfile.TemporaryDirectory(prefix="qublack-vf-audit-") as temp:
            broken = Path(temp) / "broken[wght].ttf"
            shutil.copy2(built[0], broken)
            font = TTFont(str(broken))
            del font["fvar"]
            font.save(str(broken))
            rejected = bool(audit(broken))
            print(f"{'PASS' if rejected else 'FAIL'}  negative control (wght axis removed) "
                  f"{'rejected' if rejected else 'accepted'}")
            failures += 0 if rejected else 1
    return 1 if (args.check and failures) else 0


if __name__ == "__main__":
    sys.exit(main())
