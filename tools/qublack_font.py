"""Shared font helpers for the QuBlack build: loading, measuring, naming."""

from __future__ import annotations

import json
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

VERTICAL_TABLES = ("vmtx", "vhea", "VORG")
CJK_SAMPLE = "汉国图一永口"
LATIN_SAMPLE = "axH"

COPYRIGHT = (
    "Based on Sarasa Gothic by Chen Qi's Sarasa contributors and on Recursive by ArrowType. "
    "Both are licensed under the SIL Open Font License 1.1; this derivative is released under "
    "the same license with new family names."
)
DERIVATION = "Derived from Sarasa Gothic and Recursive (SIL OFL 1.1)"


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


def write_names(font: TTFont, display_family: str, slug: str, style: str) -> None:
    """Name table: new family, OFL notice, derivation statement — the OFL compliance surface."""
    name = font["name"]
    full = f"{display_family} {style}"
    postscript = f"{slug}-{style}"
    for plat in [(3, 1, 0x409), (1, 0, 0)]:
        for nid, val in [
            (0, COPYRIGHT),
            (1, display_family),
            (2, style),
            (3, "Jun"),
            (4, full),
            (6, postscript),
            (7, DERIVATION),
            (8, display_family),
            (9, "qublack build pipeline"),
            (11, ""),
            (13, "This font is licensed under the SIL Open Font License 1.1"),
            (14, "https://openfontlicense.org"),
            (16, display_family),
            (17, style),
        ]:
            name.setName(val, nid, *plat)


def baseline_entry(path: str | Path) -> dict:
    data = measure(path)
    data.pop("file", None)
    return data


def write_json(path: str | Path, payload) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
