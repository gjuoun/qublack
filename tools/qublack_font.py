"""Shared font helpers for the QuBlack build: loading, measuring, naming."""

from __future__ import annotations

import json
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

REPO = Path(__file__).resolve().parent.parent

VERTICAL_TABLES = ("vmtx", "vhea", "VORG")
CJK_SAMPLE = "汉国图一永口"
LATIN_SAMPLE = "axH"

# Google Fonts requires nameID 0 to be this exact shape (Copyright {year} The {family} Project
# Authors ({git_url})), with the upstream attribution living in nameID 7 / AUTHORS.txt instead.
COPYRIGHT = "Copyright 2026 The QuBlack Project Authors (https://github.com/gjuoun/qublack)"
DERIVATION = (
    "Derived from Sarasa Gothic and Recursive (SIL OFL 1.1); the hanzi weight axis comes from "
    "Noto Sans SC VF. Copyright holders are listed in AUTHORS.txt."
)
LICENSE = (
    "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
    "This license is available with a FAQ at: https://openfontlicense.org"
)


def open_font(path: str | Path, drop_vertical: bool = True) -> TTFont:
    """Load a face for reading; the vertical tables are dropped when present (broken in donors)."""
    font = TTFont(str(path), lazy=True)
    if drop_vertical:
        for tag in VERTICAL_TABLES:
            if tag in font:
                del font[tag]
    return font


def advance(font: TTFont, char: str) -> float | None:
    cmap = font.getBestCmap()
    name = cmap.get(ord(char))
    if name is None:
        return None
    return font["hmtx"].metrics[name][0] / font["head"].unitsPerEm


def ink(font: TTFont, char: str) -> dict[str, float] | None:
    cmap = font.getBestCmap()
    name = cmap.get(ord(char))
    if name is None:
        return None
    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    if not pen.bounds:
        return None
    upm = font["head"].unitsPerEm
    x0, y0, x1, y1 = (v / upm for v in pen.bounds)
    return {"w": round(x1 - x0, 4), "h": round(y1 - y0, 4), "x": round(x0, 4), "y": round(y0, 4)}


def measure(path: str | Path) -> dict:
    """Everything the release, the audit and the site quote about one face."""
    font = open_font(path)
    upm = font["head"].unitsPerEm
    cmap = font.getBestCmap()
    hhea = font["hhea"]
    return {
        "file": Path(path).name,
        "upm": upm,
        "glyphs": len(font.getGlyphOrder()),
        "family": font["name"].getDebugName(1),
        "postscript": font["name"].getDebugName(6),
        "advances": {
            ch: round(advance(font, ch), 4) if advance(font, ch) is not None else None
            for ch in "aHM汉一国図图永口│─。"
        },
        "ink": {ch: ink(font, ch) for ch in CJK_SAMPLE + LATIN_SAMPLE},
        "lineHeight": round((hhea.ascender - hhea.descender + hhea.lineGap) / upm, 4),
        "codepoints": len(cmap),
    }


ZH_PREFIX = {"QuBlack Mono": "黢黑等宽", "QuBlack Sans": "黢黑比例"}


def _release_version() -> str:
    return json.loads((REPO / "package.json").read_text(encoding="utf-8"))["version"]


def write_names(font: TTFont, display_family: str, slug: str, style: str) -> None:
    """Rebuild the whole name table: QuBlack names, OFL attribution, nothing inherited.

    The upstream Sarasa records (its 1.0.42 version string, the zh-CN localization saying
    "Sarasa Term SC", an empty nameID 11) were left behind by the earlier pass; a localized match
    could even collide with a real Sarasa install. The table is wiped and written from scratch:

      - ids 0 and 7 keep the OFL derivative attribution (copyright + derivation statement);
      - ids 1/4/16 carry the family, ids 2/17 the style, 6 the PostScript name;
      - id 3 is a real unique ID, id 5 the QuBlack version, 8/9 the manufacturer and designer;
      - the Windows zh-CN (0x804) records carry 黢黑等宽 QuBlack Mono / 黢黑比例 QuBlack Sans;
      - no empty records, and the Mac and Windows tables hold the same ids.
    """
    version = _release_version()
    zh_family = f"{ZH_PREFIX[display_family]} {display_family}"
    # GF style linking accepts only R/I/B/BI in IDs 2 and 17; the file and PostScript names keep
    # the compact "BoldItalic" form.
    style_display = style.replace("BoldItalic", "Bold Italic")
    full = f"{display_family} {style_display}"
    postscript = f"{slug}-{style}"
    zh_full = f"{zh_family} {style_display}"
    license_text = LICENSE

    common = [
        (0, COPYRIGHT),
        (1, display_family),
        (2, style_display),
        (3, f"{version}; gjuoun; {postscript}"),
        (4, full),
        (5, f"Version {version}"),
        (6, postscript),
        (7, DERIVATION),
        (8, "gjuoun"),
        (9, "Jun Guo"),
        (13, license_text),
        (14, "https://openfontlicense.org"),
        (16, display_family),
        (17, style_display),
    ]
    localized = [
        (0, COPYRIGHT),
        (1, zh_family),
        (2, style_display),
        (3, f"{version}; gjuoun; {postscript}"),
        (4, zh_full),
        (5, f"Version {version}"),
        (6, postscript),
        (7, DERIVATION),
        (8, "gjuoun"),
        (9, "Jun Guo"),
        (13, license_text),
        (14, "https://openfontlicense.org"),
        # GF compares ID 16 across platforms: keep it unlocalized, localize ID 1 only.
        (16, display_family),
        (17, style_display),
    ]

    # The OpenType version fields have to agree with nameID 5. fontbakery parses
    # "1.2.3" as 1.2, so a three-part version maps onto a two-part fontRevision.
    major, minor, _patch = version.split(".")
    font["head"].fontRevision = float(f"{major}.{minor}")
    font["OS/2"].achVendID = "JUNG"

    name = font["name"]
    name.names = []  # nothing from the upstream font survives
    for platform, records in [((3, 1, 0x409), common), ((1, 0, 0), common), ((3, 1, 0x804), localized)]:
        for nid, value in records:
            name.setName(value, nid, *platform)


def baseline_entry(path: str | Path) -> dict:

    data = measure(path)
    data.pop("file", None)
    return data


def write_json(path: str | Path, payload) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
