#!/usr/bin/env python3
"""Google Fonts tables QuBlack's skeleton never carried: BASE, vmtx/vhea, win metrics.

The CJK geometry follows the rule fontspector's googlefonts/cjk_vertical_metrics check
uses (and which google/fonts applies to CJK families):

  * icfb / icft are the average ink bottom / top of the Han glyphs;
  * ideo / idtp are the ideographic em box, centred on that average ink box;
  * romn is the Roman baseline (0);
  * vertical baselines mirror the horizontal ones across the em box.

QuBlack keeps its own 1.25 em line height (a product decision, JG-143 Q5), so the typo
ascender/descender keep summing to the layout line height while hhea is made to agree.
"""

from __future__ import annotations

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import newTable
from fontTools.ttLib.tables import otTables as ot

HAN_RANGES = ((0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0x20000, 0x2A6DF))
VERT_ORIGIN_Y = 880  # Sarasa's ideographic vertical origin, in cell units


def han_bounds(font) -> list[tuple[int, int, int, int]]:
    """Ink bounds for every Han-mapped glyph, in font units."""
    cmap = font.getBestCmap()
    glyphs = {name for cp, name in cmap.items() if any(lo <= cp <= hi for lo, hi in HAN_RANGES)}
    bounds = []
    gs = font.getGlyphSet()
    for name in sorted(glyphs):
        pen = BoundsPen(gs)
        gs[name].draw(pen)
        if pen.bounds:
            bounds.append(tuple(round(v) for v in pen.bounds))
    if not bounds:
        raise SystemExit("no Han glyph bounds found")
    return bounds


def ideographic_metrics(font) -> dict[str, int]:
    upm = font["head"].unitsPerEm
    bounds = han_bounds(font)
    n = len(bounds)
    centre = sum((y1 + y0) / 2 for x0, y0, x1, y1 in bounds) / n
    cmap = font.getBestCmap()
    hmtx = font["hmtx"].metrics
    han_names = [
        name
        for cp, name in cmap.items()
        if any(lo <= cp <= hi for lo, hi in HAN_RANGES)
    ]
    return {
        "icfb": round(sum(y0 for _, y0, _, _ in bounds) / n),
        "icft": round(sum(y1 for _, _, _, y1 in bounds) / n),
        "ideo": round(centre - upm / 2),
        "idtp": round(centre + upm / 2),
        "romn": 0,
        # vertical baselines mirror the horizontal ink box across the em box
        "v_icfb": round(sum(x0 for x0, _, _, _ in bounds) / n),
        "v_icft": round(sum(x1 for _, _, x1, _ in bounds) / n),
        "v_ideo": 0,
        "v_romn": round(upm / 2 - centre),
        "v_idtp": round(sum(hmtx[name][0] for name in han_names) / len(han_names)),
    }


BASE_TAGS = ("icfb", "icft", "ideo", "romn", "idtp")


def _axis(tags: tuple[str, ...], records: list[tuple[str, int, list[int]]]) -> ot.Axis:
    axis = ot.Axis()
    axis.BaseTagList = ot.BaseTagList()
    axis.BaseTagList.BaselineTag = list(tags)
    axis.BaseScriptList = ot.BaseScriptList()
    axis.BaseScriptList.BaseScriptRecord = []
    for tag, default, values in records:
        record = ot.BaseScriptRecord()
        record.BaseScriptTag = tag
        record.BaseScript = ot.BaseScript()
        record.BaseScript.BaseValues = ot.BaseValues()
        record.BaseScript.BaseValues.DefaultIndex = default
        record.BaseScript.BaseValues.BaseCoord = []
        for value in values:
            coord = ot.BaseCoord()
            coord.Format = 1
            coord.Coordinate = int(value)
            record.BaseScript.BaseValues.BaseCoord.append(coord)
        axis.BaseScriptList.BaseScriptRecord.append(record)
    return axis


def write_base(font) -> dict[str, int]:
    """Add a BASE table built from the font's own Han ink box (no FEA compile: that
    would rewrite GSUB/GPOS, which this project inherits from its donors)."""
    metrics = ideographic_metrics(font)
    h_values = [metrics[k] for k in BASE_TAGS]
    v_values = [metrics[k] for k in ("v_icfb", "v_icft", "v_ideo", "v_romn", "v_idtp")]
    scripts = ["cyrl", "grek", "hani", "kana", "latn", "DFLT"]
    h_records, v_records = [], []
    for script in scripts:
        default = 2 if script in ("DFLT", "hani", "kana") else 3
        h_records.append((script, default, h_values))
        v_records.append((script, default, v_values))
    base = ot.BASE()
    base.Version = 0x00010000
    base.HorizAxis = _axis(BASE_TAGS, h_records)
    base.VertAxis = _axis(BASE_TAGS, v_records)
    table = newTable("BASE")
    table.table = base
    font["BASE"] = table
    return metrics


def write_vertical(font) -> int:
    """Add vhea/vmtx: every glyph advances one ideographic cell vertically."""
    upm = font["head"].unitsPerEm
    cell = 1000 if upm == 833 else upm
    order = font.getGlyphOrder()
    glyf = font["glyf"]
    vmtx = newTable("vmtx")
    vmtx.metrics = {}
    for name in order:
        glyph = glyf[name]
        glyph.recalcBounds(glyf)
        top = getattr(glyph, "yMax", 0) or 0
        vmtx.metrics[name] = (cell, VERT_ORIGIN_Y - top)
    font["vmtx"] = vmtx

    vhea = newTable("vhea")
    vhea.tableVersion = 0x00011000
    vhea.ascent = cell // 2
    vhea.descent = -(cell // 2)
    vhea.lineGap = 0
    # The four aggregates below are recomputed from vmtx when the table compiles
    # (table__v_h_e_a.recalc), so only the required fields are set here.
    vhea.advanceHeightMax = cell
    vhea.minTopSideBearing = 0
    vhea.minBottomSideBearing = 0
    vhea.yMaxExtent = 0
    vhea.caretSlopeRise = 0
    vhea.caretSlopeRun = 1
    vhea.caretOffset = 0
    vhea.reserved1 = vhea.reserved2 = vhea.reserved3 = vhea.reserved4 = 0
    vhea.metricDataFormat = 0
    vhea.numberOfVMetrics = len(order)
    font["vhea"] = vhea
    return len(order)


def ink_extents(font) -> tuple[int, int]:
    """Ink bottom/top over the encoded glyphs (what the gate measures)."""
    glyf = font["glyf"]
    top = None
    bottom = None
    for name in set(font.getBestCmap().values()):
        glyph = glyf[name]
        if getattr(glyph, "numberOfContours", 0) == 0 and not glyph.isComposite():
            continue
        glyph.recalcBounds(glyf)
        y0 = getattr(glyph, "yMin", 0) or 0
        y1 = getattr(glyph, "yMax", 0) or 0
        top = y1 if top is None else max(top, y1)
        bottom = y0 if bottom is None else min(bottom, y0)
    return (bottom or 0), (top or 0)


def align_family_win_metrics(paths) -> tuple[int, int]:
    """Give every face of a family one win box big enough for the whole family.

    Italic faces reach past the upright ink; Google Fonts requires the win metrics to be
    identical across a family, so the widest extent wins and every face is rewritten.
    """
    from fontTools.ttLib import TTFont

    fonts = [TTFont(str(p)) for p in paths]
    boxes = [ink_extents(font) for font in fonts]
    bottom = min(b for b, _ in boxes)
    top = max(t for _, t in boxes)
    # Underline metrics must also agree across the family; keep the Regular's.
    underline = (fonts[0]["post"].underlinePosition, fonts[0]["post"].underlineThickness)
    for path, font in zip(paths, fonts):
        font["OS/2"].usWinAscent = max(0, top)
        font["OS/2"].usWinDescent = max(0, -bottom)
        font["post"].underlinePosition, font["post"].underlineThickness = underline
        font.save(str(path))
    return bottom, top


def write_win_metrics(font, line_height: float) -> dict[str, int]:
    """win metrics cover the ink; hhea and OS/2 typo agree on one line box.

    The line height is preserved: typoAscender - typoDescender stays equal to
    line_height * upm, so GF's CJK envelope is the only metric this cannot satisfy.
    """
    upm = font["head"].unitsPerEm
    bounds = han_bounds(font)
    ink_top = max(y1 for _, _, _, y1 in bounds)
    ink_bottom = min(y0 for _, y0, _, _ in bounds)
    os2, hhea = font["OS/2"], font["hhea"]
    # Largest ink extent over every *encoded* glyph (accents, brackets, ...); unmapped
    # glyphs are never rendered, and the gate measures the cmap-mapped set too.
    glyf = font["glyf"]
    cmap = font.getBestCmap()
    for name in set(cmap.values()):
        glyph = glyf[name]
        if glyph.numberOfContours == 0 and not glyph.isComposite():
            continue
        glyph.recalcBounds(glyf)
        ink_top = max(ink_top, getattr(glyph, "yMax", 0) or 0)
        ink_bottom = min(ink_bottom, getattr(glyph, "yMin", 0) or 0)
    os2.usWinAscent = max(0, ink_top)
    os2.usWinDescent = max(0, -ink_bottom)

    total = round(line_height * upm)
    descender = os2.sTypoDescender
    ascender = total + descender
    os2.sTypoAscender = ascender
    os2.sTypoLineGap = 0
    hhea.ascent = ascender
    hhea.descent = descender
    hhea.lineGap = 0
    return {"ascender": ascender, "descender": descender, "win_ascent": os2.usWinAscent, "win_descent": os2.usWinDescent}
