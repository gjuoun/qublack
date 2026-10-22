#!/usr/bin/env python3
"""Strict audit of a built family: name table, OFL surface, cmap, grid.

Every fact the release and the site claim is checked here, so a wrong family name or a stray
emoji codepoint fails the build instead of shipping.

usage: name_audit.py --strict <dir-or-face...>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_qublack import emoji_codepoints, keep_codepoint  # noqa: E402
from qublack_font import open_font  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
EXPECTED = {
    "QuBlackMono": {"display": "QuBlack Mono", "slug": "QuBlackMono", "upm": 833, "han": 1200, "ascii": 600},
    "QuBlackSans": {"display": "QuBlack Sans", "slug": "QuBlackSans", "upm": 1000, "han": 1000, "ascii": 600},
}
RESERVED = ("Source", "Sarasa", "Recursive")


def faces(targets: list[Path]) -> list[Path]:
    out: list[Path] = []
    for target in targets:
        out.extend(sorted(target.glob("*.ttf")) if target.is_dir() else [target])
    return out


def audit(path: Path, emoji: set[int]) -> list[str]:
    font = open_font(path)
    upm = font["head"].unitsPerEm
    cmap = font.getBestCmap()
    hmtx = font["hmtx"].metrics
    name = font["name"]
    problems: list[str] = []

    family_slug, _, style = path.stem.partition("-")
    spec = EXPECTED.get(family_slug)
    if spec is None:
        return [f"unknown family slug {family_slug!r}"]

    display = name.getDebugName(1) or ""
    full = name.getDebugName(4) or ""
    postscript = name.getDebugName(6) or ""
    notice = " ".join(filter(None, [name.getDebugName(0), name.getDebugName(7), name.getDebugName(13)]))

    if display != spec["display"]:
        problems.append(f"name ID 1 {display!r} != {spec['display']!r}")
    if full != f"{spec['display']} {style}":
        problems.append(f"name ID 4 {full!r} != {spec['display']} {style!r}")
    if postscript != f"{spec['slug']}-{style}":
        problems.append(f"name ID 6 {postscript!r} != {spec['slug']}-{style}")
    if (name.getDebugName(16) or "") != spec["display"]:
        problems.append("name ID 16 (typographic family) missing")
    if (name.getDebugName(17) or "") != style:
        problems.append("name ID 17 (typographic subfamily) missing")
    for platform in [(3, 1, 0x409), (1, 0, 0)]:
        for nid in (1, 2, 4, 6):
            if not name.getName(nid, *platform):
                problems.append(f"missing name ID {nid} on platform {platform}")
    if "SIL Open Font License" not in notice:
        problems.append("OFL notice missing from the name table")
    if "Derived from Sarasa Gothic and Recursive" not in notice:
        problems.append("derivation statement missing from the name table")
    for reserved in RESERVED:
        if reserved.lower() in display.lower() or reserved.lower() in postscript.lower():
            problems.append(f"reserved upstream name {reserved!r} used in a family/PostScript name")

    if upm != spec["upm"]:
        problems.append(f"upm {upm} != {spec['upm']}")
    han = hmtx[cmap[0x6C49]][0] * 1000 / upm
    ascii_advance = hmtx[cmap[0x61]][0] * 1000 / upm
    if round(han) != spec["han"]:
        problems.append(f"汉 advance {han / 1000:.3f}em != {spec['han'] / 1000:.3f}em")
    if round(ascii_advance) != spec["ascii"]:
        problems.append(f"a advance {ascii_advance / 1000:.3f}em != {spec['ascii'] / 1000:.3f}em")
    if family_slug == "QuBlackMono" and round(han) / round(ascii_advance) != 2:
        problems.append("the 2:1 grid does not hold")

    stripped = sum(1 for cp in cmap if cp in emoji and not keep_codepoint(cp))
    if stripped:
        problems.append(f"{stripped} Emoji=Yes codepoints still in the cmap")
    # Box drawing must stay at half a hanzi cell in both families (0.600em mono, 0.500em sans).
    for cp in (0x2502, 0x2500):
        if cp not in cmap:
            problems.append(f"box drawing U+{cp:04X} missing from the cmap")
            continue
        width = hmtx[cmap[cp]][0] * 1000 / upm
        if abs(width - spec["han"] / 2) > 0.5:
            problems.append(
                f"box drawing U+{cp:04X} advances {width / 1000:.3f}em, not half a hanzi cell"
            )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("targets", nargs="+", type=Path)
    parser.add_argument("--strict", action="store_true", help="fail on any problem (the gate)")
    args = parser.parse_args()

    emoji = emoji_codepoints(REPO)
    built = faces(args.targets)
    failures = 0
    for path in built:
        problems = audit(path, emoji)
        if problems:
            failures += 1
            print(f"FAIL  {path.name}: " + "; ".join(problems[:6]))
        else:
            print(f"PASS  {path.name}: name/OFL/cmap ok")
    print(f"name/OFL/cmap ok ({len(built) - failures}/{len(built)} faces), emoji-free cmap checked")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
