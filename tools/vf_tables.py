#!/usr/bin/env python3
"""Name table, fvar and STAT for a QuBlack variable face.

The VF is its own family ("QuBlack Mono VF"), not a second file sharing "QuBlack Mono": the
static Regular already owns the PostScript name QuBlackMono-Regular, and two installed fonts with
one PostScript name collide in every font manager. The file name keeps the Google Fonts variable
convention (QuBlackMono[wght].ttf); only the family string carries the VF marker.

usage (from build_vf.py): prepare(font, display, slug, version)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fontTools.otlLib.builder import buildStatTable
from fontTools.ttLib import newTable
from fontTools.ttLib.tables._f_v_a_r import Axis, NamedInstance

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qublack_font import COPYRIGHT, DERIVATION, LICENSE, REPO, ZH_PREFIX  # noqa: E402

# Google Fonts expects the standard weight ladder on a 400-700 axis, with PostScript names on
# every instance and Regular linked to the bold end.
INSTANCES = {400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}
WEIGHTS = {400: "Regular", 700: "Bold"}


def release_version() -> str:
    return json.loads((REPO / "package.json").read_text(encoding="utf-8"))["version"]


def _add(font, name_id: int, value: str) -> None:
    for platform in ((3, 1, 0x409), (1, 0, 0)):
        font["name"].setName(value, name_id, *platform)


def prepare(font, display: str, slug: str, version: str, default_weight: int = 400) -> dict:
    """Write the whole name surface plus fvar and STAT. Returns the axis summary."""
    style = WEIGHTS[default_weight]
    postscript = f"{slug}-{style}"
    zh_family = f"{ZH_PREFIX[display]} {display}"

    font["name"].names = []  # nothing from the donors survives
    common = [
        (0, COPYRIGHT),
        (1, display),
        (2, style),
        (3, f"{version}; gjuoun; {postscript}"),
        (4, f"{display} {style}"),
        (5, f"Version {version}"),
        (6, postscript),
        (7, DERIVATION),
        (8, "gjuoun"),
        (9, "Jun Guo"),
        (13, LICENSE),
        (14, "https://openfontlicense.org"),
        (16, display),
        (17, style),
    ]
    for name_id, value in common:
        _add(font, name_id, value)
    # zh-CN mirrors the static faces, with the VF marker in the family string.
    for platform in ((3, 1, 0x804),):
        for name_id, value in common:
            if name_id == 1:
                value = zh_family
            elif name_id == 4:
                value = f"{zh_family} {style}"
            font["name"].setName(value, name_id, *platform)

    major, minor, _patch = version.split(".")
    font["head"].fontRevision = float(f"{major}.{minor}")
    font["head"].macStyle = 0
    font["OS/2"].achVendID = "JUNG"
    font["OS/2"].usWeightClass = default_weight
    font["OS/2"].fsSelection = (font["OS/2"].fsSelection & ~0b100000) | 0b1000000  # REGULAR, not BOLD

    # fvar: one weight axis and the four instances GF's profile requires, each with the style name
    # and a PostScript name (0xFFFF is rejected by fvar_instance_ps_names).
    fvar = newTable("fvar")
    axis = Axis()
    axis.axisTag = "wght"
    axis.minValue = 400.0
    axis.defaultValue = float(default_weight)
    axis.maxValue = 700.0
    axis.flags = 0
    axis.axisNameID = font["name"].addName("Weight")
    fvar.axes = [axis]
    fvar.instances = []
    for weight, style_name in INSTANCES.items():
        instance = NamedInstance()
        instance.coordinates = {"wght": float(weight)}
        instance.subfamilyNameID = font["name"].addName(style_name)
        instance.postscriptNameID = font["name"].addName(f"{slug}-{style_name}")
        instance.flags = 0
        fvar.instances.append(instance)
    fvar.axisCount = 1
    fvar.instanceCount = len(fvar.instances)
    fvar.offsetToData = 0
    font["fvar"] = fvar

    buildStatTable(
        font,
        [
            {
                "tag": "wght",
                "name": "Weight",
                "ordering": 0,
                "values": [
                    {"value": 400, "name": "Regular", "flags": 0x2, "nominalValue": 400, "linkedValue": 700},
                    {"value": 500, "name": "Medium", "flags": 0x0, "nominalValue": 500},
                    {"value": 600, "name": "SemiBold", "flags": 0x0, "nominalValue": 600},
                    {"value": 700, "name": "Bold", "flags": 0x0, "nominalValue": 700},
                ],
            }
        ],
    )
    return {
        "family": display,
        "postscript": postscript,
        "axes": [("wght", axis.minValue, axis.defaultValue, axis.maxValue)],
        "instances": [WEIGHTS[weight] for weight in WEIGHTS],
    }
