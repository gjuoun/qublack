#!/usr/bin/env python3
"""Strict audit of a built family: name table, OFL surface, cmap, 2:1 grid.

Delta 12 cleared the upstream name records, so the audit now also holds the cleanliness line:
no upstream strings outside the OFL attribution ids (0 and 7), no empty records, Mac and Windows
carrying the same ids, a zh-CN localization naming the Qu Black families, and a version string that
matches package.json.

usage: name_audit.py --strict <dir-or-face...>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_qublack import emoji_codepoints, keep_codepoint  # noqa: E402
from qublack_font import COPYRIGHT, LICENSE, open_font  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
EXPECTED = {
    "QuBlackMono": {"display": "Qu Black Mono", "zh": "黢黑等宽", "upm": 833, "han": 1200, "ascii": 600},
    "QuBlackSans": {"display": "Qu Black Sans", "zh": "黢黑比例", "upm": 1000, "han": 1000, "ascii": 600},
}
RESERVED = ("Source", "Sarasa", "Recursive", "ttfautohint", "1.0.42")
# Only the derivation record (7) may name upstream projects; id 0 is the GF copyright line now.
ATTRIBUTION_IDS = (7,)
NAME_IDS = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 14, 16, 17}


def faces(targets: list[Path]) -> list[Path]:
    out: list[Path] = []
    for target in targets:
        out.extend(sorted(target.glob("*.ttf")) if target.is_dir() else [target])
    return out


def name_map(font) -> dict[tuple[int, int, int], dict[int, str]]:
    table: dict[tuple[int, int, int], dict[int, str]] = {}
    for record in font["name"].names:
        table.setdefault((record.platformID, record.platEncID, record.langID), {})[record.nameID] = (
            record.toUnicode()
        )
    return table


def audit_names(path: Path, spec: dict, version: str) -> list[str]:
    font = open_font(path)
    table = name_map(font)
    problems: list[str] = []

    mac = table.get((1, 0, 0), {})
    win = table.get((3, 1, 0x409), {})
    zh = table.get((3, 1, 0x804), {})
    if not mac or not win:
        return ["name table missing the Mac or Windows English platform"]

    for label, platform in (("mac", mac), ("win", win), ("zh-CN", zh)):
        if set(platform) != NAME_IDS:
            problems.append(label + " name ids " + str(sorted(set(platform))) + " != " + str(sorted(NAME_IDS)))

    for label, platform in (("mac", mac), ("win", win), ("zh-CN", zh)):
        for nid, value in platform.items():
            if value == "":
                problems.append(label + " name id " + str(nid) + " is empty")
            if nid in ATTRIBUTION_IDS:
                continue
            for reserved in RESERVED:
                if reserved.lower() in value.lower():
                    problems.append(label + " id " + str(nid) + " still mentions " + reserved + ": " + repr(value))

    style = path.stem.split("-")[1]
    style_display = style.replace("BoldItalic", "Bold Italic")
    display = spec["display"]
    expected = {
        1: display,
        2: style_display,
        4: display + " " + style_display,
        6: path.stem,
        16: display,
        17: style_display,
    }
    for label, platform in (("mac", mac), ("win", win)):
        for nid, want in expected.items():
            if platform.get(nid) != want:
                problems.append(label + " id " + str(nid) + " = " + repr(platform.get(nid)) + ", expected " + repr(want))

    zh_family = spec["zh"] + " " + display
    if zh.get(1) != zh_family:
        problems.append("zh-CN family " + repr(zh.get(1)) + " != " + repr(zh_family))
    if zh.get(16) != display:
        problems.append("zh-CN typographic family " + repr(zh.get(16)) + " != " + repr(display) + " (GF compares it across platforms)")

    version_string = "Version " + version
    if win.get(5) != version_string:
        problems.append("version string " + repr(win.get(5)) + " != " + repr(version_string))
    unique = str(win.get(3, "")).strip().lower()
    if unique in ("jun", ""):
        problems.append("unique ID is the old leftover: " + repr(win.get(3)))

    if win.get(0) != COPYRIGHT:
        problems.append("copyright " + repr(win.get(0)) + " != " + repr(COPYRIGHT))
    if win.get(13) != LICENSE:
        problems.append("license " + repr(win.get(13)) + " != the GF fixed string")
    notice = " ".join([win.get(7, ""), win.get(13, "")])
    if "SIL Open Font License" not in notice:
        problems.append("OFL attribution missing from the name table")
    # The family name is two words now: a one-word regression in the naming ids has to fail the
    # audit, not survive as a cleanup note. IDs 3/6 keep the no-space PostScript slug on purpose.
    for label, platform in (("mac", mac), ("win", win), ("zh-CN", zh)):
        stale = [nid for nid in (1, 4, 16) if "QuBlack" in platform.get(nid, "")]
        if stale:
            problems.append(label + " naming ids " + str(stale) + " still carry the one-word family")

    return problems


def audit(path: Path, emoji: set[int], version: str) -> list[str]:
    font = open_font(path)
    upm = font["head"].unitsPerEm
    cmap = font.getBestCmap()
    hmtx = font["hmtx"].metrics
    family_slug = path.stem.partition("-")[0]
    spec = EXPECTED.get(family_slug)
    if spec is None:
        return ["unknown family slug " + repr(family_slug)]

    problems = audit_names(path, spec, version)
    if upm != spec["upm"]:
        problems.append("upm " + str(upm) + " != " + str(spec["upm"]))
    han = hmtx[cmap[0x6C49]][0] * 1000 / upm
    ascii_advance = hmtx[cmap[0x61]][0] * 1000 / upm
    if round(han) != spec["han"]:
        problems.append("han advance " + str(round(han)) + " != " + str(spec["han"]))
    if round(ascii_advance) != spec["ascii"]:
        problems.append("a advance " + str(round(ascii_advance)) + " != " + str(spec["ascii"]))
    if family_slug == "QuBlackMono" and round(han) / round(ascii_advance) != 2:
        problems.append("the 2:1 grid does not hold")

    stripped = sum(1 for cp in cmap if cp in emoji and not keep_codepoint(cp))
    if stripped:
        problems.append(str(stripped) + " Emoji=Yes codepoints still in the cmap")
    for cp in (0x2502, 0x2500):
        if cp not in cmap:
            problems.append("box drawing U+" + format(cp, "04X") + " missing from the cmap")
            continue
        width = hmtx[cmap[cp]][0] * 1000 / upm
        if abs(width - spec["han"] / 2) > 0.5:
            problems.append("box drawing U+" + format(cp, "04X") + " is not half a hanzi cell")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("targets", nargs="+", type=Path)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    version = json.loads((REPO / "package.json").read_text(encoding="utf-8"))["version"]
    emoji = emoji_codepoints(REPO)
    built = faces(args.targets)
    failures = 0
    for path in built:
        problems = audit(path, emoji, version)
        if problems:
            failures += 1
            print("FAIL  " + path.name + ": " + "; ".join(problems[:6]))
        else:
            print("PASS  " + path.name + ": name/OFL/cmap ok")
    print("name/OFL/cmap ok (" + str(len(built) - failures) + "/" + str(len(built)) + " faces), emoji-free cmap checked")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
