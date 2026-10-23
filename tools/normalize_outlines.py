#!/usr/bin/env python3
"""Outline hygiene for the Google Fonts gate.

Three defects are inherited from the Sarasa/Recursive donors and are fixed here, on the
built face, without touching glyph order, cmap size or any metric:

  * nested components (components whose base is itself a composite) — flattened once;
  * zero-advance base glyphs — every cmap-mapped glyph that is not a combining mark and
    has no advance gets one cell, so it is a usable spacing glyph instead of a
    zero-width "base" the gate rejects;
  * GDEF mark class drift — Unicode mark characters enter class 3, non-marks leave it.
"""

from __future__ import annotations

import sys

try:  # the stdlib table on the build interpreter can be several Unicode versions behind
    import unicodedata2 as unicodedata
except ImportError:  # pragma: no cover - fallback keeps the build runnable
    import unicodedata

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

MARK = 3
BASE = 1
# Control/format/space characters are legitimately zero-width and are not "bases".
ZERO_OK = {"Cc", "Cf", "Zl", "Zp", "Zs"}


def flatten_nested(font) -> int:
    glyf = font["glyf"]
    gs = font.getGlyphSet()
    changed = 0
    for name in font.getGlyphOrder():
        glyph = glyf[name]
        if not glyph.isComposite():
            continue
        if not any(glyf[c.glyphName].isComposite() for c in glyph.components):
            continue
        recorded = DecomposingRecordingPen(gs)
        gs[name].draw(recorded)
        pen = TTGlyphPen(None)
        for operation, args, *kwargs in recorded.value:
            getattr(pen, operation)(*args, **(kwargs[0] if kwargs else {}))
        glyf[name] = pen.glyph()
        changed += 1
    return changed


def fix_mark_classes(font) -> tuple[int, int]:
    gdef = font["GDEF"].table
    if gdef.GlyphClassDef is None:
        return 0, 0
    classes = gdef.GlyphClassDef.classDefs
    cmap = font.getBestCmap()
    added = removed = 0
    for cp, name in cmap.items():
        category = unicodedata.category(chr(cp))
        current = classes.get(name)
        if category.startswith("M"):
            if current != MARK:
                classes[name] = MARK
                added += 1
        elif current == MARK and category != "Cn":
            # Unassigned codepoints carry planned combining marks in the donor; leave
            # them alone rather than churn on Unicode-version skew.
            classes[name] = BASE
            removed += 1
    return added, removed


def space_zero_width_bases(font) -> int:
    cmap = font.getBestCmap()
    hmtx = font["hmtx"].metrics
    glyf = font["glyf"]
    gdef = font["GDEF"].table
    classes = gdef.GlyphClassDef.classDefs if gdef.GlyphClassDef else {}
    upm = font["head"].unitsPerEm
    cell = 1000 if upm == 833 else upm
    changed = 0
    for cp, name in cmap.items():
        if classes.get(name) == MARK:
            # Combining marks are zero-width by definition; Sarasa's spacing variants
            # (U+0323) would otherwise be skipped by the mark-attachment builder.
            if hmtx[name][0] != 0:
                hmtx[name] = (0, hmtx[name][1])
                changed += 1
            continue
        if hmtx[name][0] != 0:
            continue  # spacing glyphs keep their advance
        if unicodedata.category(chr(cp)) in ZERO_OK:
            continue
        glyph = glyf[name]
        glyph.recalcBounds(glyf)
        if getattr(glyph, "numberOfContours", 0) == 0 and not glyph.isComposite():
            continue  # blank placeholders (CGJ, ZWSP) stay zero-width
        hmtx[name] = (cell, hmtx[name][1])
        changed += 1
    return changed


def fix_space_widths(font) -> int:
    """NBSP must have the same advance as the space."""
    cmap = font.getBestCmap()
    space, nbsp = cmap.get(0x20), cmap.get(0xA0)
    if not space or not nbsp:
        return 0
    hmtx = font["hmtx"].metrics
    width = hmtx[space][0]
    if hmtx[nbsp][0] == width:
        return 0
    hmtx[nbsp] = (width, hmtx[nbsp][1])
    return 1


def drop_outlier_orphans(font) -> int:
    """Remove unencoded glyphs whose ink escapes the em box by more than half of it.

    Two nameless donor glyphs (gid 3484/3485) carry 1.3-1.8 em ink and are unreachable
    from the cmap; they only inflate the win metrics and break the family ink box.
    """
    upm = font["head"].unitsPerEm
    glyf = font["glyf"]
    encoded = set(font.getBestCmap().values())
    limit = upm * 1.5
    doomed = []
    for name in font.getGlyphOrder():
        if name in encoded:
            continue
        glyph = glyf[name]
        if getattr(glyph, "numberOfContours", 0) == 0 and not glyph.isComposite():
            continue
        glyph.recalcBounds(glyf)
        if (getattr(glyph, "yMax", 0) or 0) > limit or (getattr(glyph, "yMin", 0) or 0) < -limit:
            doomed.append(name)
    for name in doomed:
        del glyf[name]
        font["hmtx"].metrics.pop(name, None)
    if doomed:
        font.setGlyphOrder([n for n in font.getGlyphOrder() if n not in set(doomed)])
    return len(doomed)


def drop_vert_feature(font) -> int:
    """Remove the 'vert' GSUB feature; 'vrt2' is its superset and the spec forbids both."""
    gsub = font["GSUB"].table
    features = gsub.FeatureList.FeatureRecord
    keep = [i for i, record in enumerate(features) if record.FeatureTag != "vert"]
    if len(keep) == len(features):
        return 0
    removed = len(features) - len(keep)
    gsub.FeatureList.FeatureRecord = [features[i] for i in keep]
    gsub.FeatureList.FeatureCount = len(gsub.FeatureList.FeatureRecord)
    remap = {old: new for new, old in enumerate(keep)}
    for script in gsub.ScriptList.ScriptRecord:
        systems = [script.Script.DefaultLangSys] if script.Script.DefaultLangSys else []
        systems += [record.LangSys for record in script.Script.LangSysRecord]
        for langsys in systems:
            if not langsys:
                continue
            langsys.FeatureIndex = [remap[i] for i in langsys.FeatureIndex if i in remap]
            langsys.FeatureCount = len(langsys.FeatureIndex)
    return removed


def normalize(font) -> dict[str, int]:
    nested = flatten_nested(font)
    added, removed = fix_mark_classes(font)
    spaced = space_zero_width_bases(font)
    vert = drop_vert_feature(font)
    spaces = fix_space_widths(font)
    dropped = drop_outlier_orphans(font)
    return {
        "space_widths_fixed": spaces,
        "outlier_glyphs_dropped": dropped,
        "nested_flattened": nested,
        "marks_added": added,
        "marks_removed": removed,
        "bases_spaced": spaced,
        "vert_features_dropped": vert,
    }


def main(argv: list[str]) -> int:
    from fontTools.ttLib import TTFont

    for path in argv[1:]:
        font = TTFont(path)
        counts = normalize(font)
        font.save(path)
        print(path, counts)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
