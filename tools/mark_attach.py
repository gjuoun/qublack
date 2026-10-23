#!/usr/bin/env python3
"""Give every base a mark anchor, so combining marks attach across the whole cmap.

The donors ship mark attachment for the Latin/Cyrillic/Greek bases they were designed
for; the extended bases inherited from Sarasa (African Latin, IPA, kana voicing marks,
the dotted circle) have no anchors, which is what GF's shape_languages check fails on.

This appends one MarkBasePos lookup built from glyph ink boxes:

  * above-marks anchor at (ink centre x, ink bottom) onto (advance/2, base yMax);
  * below-marks anchor at (ink centre x, ink top) onto (advance/2, base yMin).

Bases already covered by an inherited MarkBasePos subtable are left to those lookups,
so nothing that positions correctly today is displaced.
"""

from __future__ import annotations

import sys

from fontTools.otlLib.builder import buildAnchor, buildMarkBasePosSubtable
from fontTools.ttLib.tables import otTables as ot

ABOVE, BELOW = 0, 1
MARK_CLASS = 3
# Han/Hangul/Kana bases never take combining marks in real text, and they are half of
# the glyph set; skipping them keeps the generated lookup (and the build) reasonable.
CJK_RANGES = (
    (0x3040, 0x30FF),
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xAC00, 0xD7AF),
    (0xF900, 0xFAFF),
    (0x20000, 0x3FFFF),
)


def _markbase_subtables(gpos):
    for lookup in gpos.LookupList.Lookup:
        for subtable in lookup.SubTable:
            if lookup.LookupType == 9 and hasattr(subtable, "ExtSubTable"):
                subtable = subtable.ExtSubTable
            if getattr(subtable, "LookupType", lookup.LookupType) == 4 and hasattr(subtable, "BaseCoverage"):
                yield subtable


def covered_bases(gpos) -> set[str]:
    names: set[str] = set()
    for subtable in _markbase_subtables(gpos):
        names.update(subtable.BaseCoverage.glyphs)
    return names


def _bbox(glyf, name):
    glyph = glyf[name]
    glyph.recalcBounds(glyf)
    return getattr(glyph, "xMin", 0), getattr(glyph, "yMin", 0), getattr(glyph, "xMax", 0), getattr(glyph, "yMax", 0)


def attach(font) -> dict[str, int]:
    gpos = font["GPOS"].table
    gdef = font["GDEF"].table
    classes = gdef.GlyphClassDef.classDefs if gdef.GlyphClassDef else {}
    cmap = font.getBestCmap()
    hmtx = font["hmtx"].metrics
    glyf = font["glyf"]

    marks: dict[str, tuple[int, ot.Anchor]] = {}
    for cp, name in cmap.items():
        if classes.get(name) != MARK_CLASS or hmtx[name][0] != 0:
            continue
        x0, y0, x1, y1 = _bbox(glyf, name)
        centre = round((x0 + x1) / 2)
        if (y0 + y1) / 2 >= 0:
            marks[name] = (ABOVE, buildAnchor(centre, y0 - 1))
        else:
            marks[name] = (BELOW, buildAnchor(centre, y1 + 1))
    if not marks:
        return {"marks": 0, "bases": 0}

    # Every base gets anchors: the inherited lookups cover almost every glyph name but
    # leave whole mark classes unattached for the extended bases (that is exactly what
    # shape_languages fails on). This lookup is appended last, so precomposed forms still
    # compose through ccmp and never reach it.
    bases: dict[str, dict[int, ot.Anchor]] = {}
    # Bases are every glyph, not only cmap-mapped ones: HarfBuzz reaches some bases
    # (e.g. the ɨ in ɨ̃) through ccmp, so they never appear in the character map.
    han_cell = 1000 if font["head"].unitsPerEm == 833 else font["head"].unitsPerEm
    han_names = {
        name
        for cp, name in cmap.items()
        if any(lo <= cp <= hi for lo, hi in CJK_RANGES)
    }
    encoded = set(cmap.values())
    for name in font.getGlyphOrder():
        if name in marks or hmtx[name][0] == 0:
            continue
        if classes.get(name) == MARK_CLASS:
            continue
        if name in han_names:
            continue
        if name not in encoded and hmtx[name][0] == han_cell:
            continue  # an unencoded full-cell alternate (Han)
        x0, y0, x1, y1 = _bbox(glyf, name)
        if x0 == y0 == x1 == y1 == 0:
            continue
        # One unit of clearance: sarasa's marks are drawn for a nominal base top, so a
        # base whose ink already ends exactly there would produce a zero offset, which
        # shaperglot reports as an unattached mark. The unit is 0.0012 em at upm 833.
        # The mark is drawn after the base, so the base anchor is its centre; HarfBuzz then
        # shifts the mark back over the base (a negative x_offset of about one advance).
        # The 25-unit clearance keeps the offset non-zero when the mark's ink already
        # meets the base: shaperglot reads a (0, 0) offset as "unattached".
        bases[name] = {
            ABOVE: buildAnchor(round(hmtx[name][0] / 2) + 1, y1 + 1),
            BELOW: buildAnchor(round(hmtx[name][0] / 2) + 1, y0 - 1),
        }

    # Two 16-bit limits bite on a 57k-glyph face: the lookup-to-subtable offset and the
    # BaseArray-to-anchor offsets. Both are escaped by the Extension mechanism (lookup
    # type 9) plus chunking the bases, ~800 per subtable.
    reverse = font.getReverseGlyphMap()
    names = list(bases)
    chunk = 800
    subtables = []
    for start in range(0, len(names), chunk):
        part = {name: bases[name] for name in names[start : start + chunk]}
        subtable = buildMarkBasePosSubtable(marks, part, reverse)
        extension = ot.ExtensionPos()
        extension.Format = 1
        extension.ExtensionLookupType = 4
        extension.ExtSubTable = subtable
        subtables.append(extension)
    lookup = ot.Lookup()
    lookup.LookupType = 9
    lookup.LookupFlag = 0
    lookup.SubTable = subtables
    lookup.SubTableCount = len(subtables)
    gpos.LookupList.Lookup.append(lookup)
    gpos.LookupList.LookupCount = len(gpos.LookupList.Lookup)
    index = len(gpos.LookupList.Lookup) - 1
    for record in gpos.FeatureList.FeatureRecord:
        if record.FeatureTag == "mark":
            record.Feature.LookupListIndex.append(index)
            record.Feature.LookupCount = len(record.Feature.LookupListIndex)

    _attach_mark_to_mark(font, marks)
    return {"marks": len(marks), "bases": len(bases)}


def _attach_mark_to_mark(font, marks: dict) -> None:
    """Stack marks (mkmk): a second above-mark sits on the first mark's top."""
    from fontTools.otlLib.builder import MarkMarkPosBuilder

    gpos = font["GPOS"].table
    glyf = font["glyf"]
    mark1 = {}
    mark2 = {}
    for name, (cls, anchor) in marks.items():
        x0, y0, x1, y1 = _bbox(glyf, name)
        centre = round((x0 + x1) / 2)
        if cls == ABOVE:
            mark1[name] = (ABOVE, buildAnchor(centre, y0))
            mark2[name] = {ABOVE: buildAnchor(centre, y1), BELOW: buildAnchor(centre, y0)}
        else:
            mark1[name] = (BELOW, buildAnchor(centre, y1))
            mark2[name] = {ABOVE: buildAnchor(centre, y1), BELOW: buildAnchor(centre, y0)}
    builder = MarkMarkPosBuilder(font, None)
    builder.marks = mark1
    builder.baseMarks = mark2
    lookup = builder.build()
    gpos.LookupList.Lookup.append(lookup)
    gpos.LookupList.LookupCount = len(gpos.LookupList.Lookup)
    index = len(gpos.LookupList.Lookup) - 1
    for record in gpos.FeatureList.FeatureRecord:
        if record.FeatureTag == "mkmk":
            record.Feature.LookupListIndex.append(index)
            record.Feature.LookupCount = len(record.Feature.LookupListIndex)


def check(font) -> tuple[bool, str]:
    """Shape a known-broken pair; fall back to structural coverage without uharfbuzz."""
    cmap = font.getBestCmap()
    base, mark = cmap.get(0x025B), cmap.get(0x0303)
    if not base or not mark:
        return False, "sample glyphs missing"
    try:
        import uharfbuzz as hb
    except ImportError:
        gpos = font["GPOS"].table
        covered = any(
            base in s.BaseCoverage.glyphs and mark in s.MarkCoverage.glyphs
            for s in _markbase_subtables(gpos)
        )
        return covered, "structural"
    with open(font.reader.file.name if hasattr(font, "reader") else "/dev/null", "rb") as fh:
        face = hb.Face(fh.read())
    font_hb = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str("\u025b\u0303")
    buf.guess_segment_properties()
    hb.shape(font_hb, buf)
    positions = buf.glyph_positions
    if len(positions) < 2:
        return False, "no mark glyph in the shaping run"
    return positions[1].y_offset != 0 or positions[1].x_offset != 0, f"dy={positions[1].y_offset} dx={positions[1].x_offset}"


def main(argv: list[str]) -> int:
    from pathlib import Path

    from fontTools.ttLib import TTFont

    args = [a for a in argv[1:] if a != "--check"]
    targets = [Path(a) for a in args]
    faces = []
    for target in targets:
        faces.extend(sorted(target.glob("*.ttf")) if target.is_dir() else [target])
    ok = 0
    for path in faces:
        font = TTFont(str(path))
        passed, detail = check(font)
        ok += passed
        print(("PASS " if passed else "FAIL ") + path.name + ": " + detail)
    print(f"{ok}/{len(faces)} faces: mark attachment " + ("ok" if ok == len(faces) else "incomplete"))
    return 0 if ok == len(faces) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
