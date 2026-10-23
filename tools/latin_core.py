#!/usr/bin/env python3
"""GF Latin Core coverage, and the case-swapping pairs the gate also expects.

Google Fonts requires every face to cover GF Latin Core (319 codepoints; the list is
vendored in assets/gf-latin-core.txt so the build needs no glyphsets dependency).
Sarasa Term carries the whole set; Sarasa Gothic is missing a few codepoints, which the
sans faces inherit — U+030B is the current one. Powerline/symbol donors are never
touched; only the missing codepoints are imported, with their donor advance.

usage: latin_core.py --check <face|dir>...   print coverage per face, exit 1 on a gap
       latin_core.py --fix <term-donor.ttf> <face>...
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import unicodedata2 as unicodedata
except ImportError:  # pragma: no cover
    import unicodedata

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

REPO = Path(__file__).resolve().parent.parent
CORE = [int(line, 16) for line in (REPO / "assets" / "gf-latin-core.txt").read_text().split()]
# (present, missing counterpart) — fontbakery's case-swapping check.
CASE_PAIRS = ((0x01C6, 0x01C4), (0x023A, 0x2C65), (0x023E, 0x2C66), (0x0265, 0xA78D))


def missing_codepoints(font) -> list[int]:
    cmap = font.getBestCmap()
    return [cp for cp in CORE if cp not in cmap]


def missing_pairs(font) -> list[int]:
    cmap = font.getBestCmap()
    return [missing for present, missing in CASE_PAIRS if present in cmap and missing not in cmap]


def _add_glyph(target: TTFont, donor: TTFont, cp: int) -> str | None:
    donor_name = donor.getBestCmap().get(cp)
    if donor_name is None:
        return None
    order = target.getGlyphOrder()
    if donor_name in order:
        # The donor's glyph is already in the face but unencoded (U+030B on the sans
        # faces): map the codepoint to it instead of appending a duplicate name.
        for table in target["cmap"].tables:
            if table.isUnicode() and not (table.format == 4 and cp > 0xFFFF):
                table.cmap[cp] = donor_name
        return donor_name
    name = donor_name
    recorded = DecomposingRecordingPen(donor.getGlyphSet())
    donor.getGlyphSet()[donor_name].draw(recorded)
    pen = TTGlyphPen(None)
    for operation, args, *kwargs in recorded.value:
        getattr(pen, operation)(*args, **(kwargs[0] if kwargs else {}))
    glyph = pen.glyph()
    # glyf.__setitem__ appends the name to the glyf glyph order; mirror that into the
    # font-level order instead of appending a second time.
    target["glyf"][name] = glyph
    target["hmtx"].metrics[name] = donor["hmtx"].metrics[donor_name]
    target.setGlyphOrder(target["glyf"].glyphOrder)
    for table in target["cmap"].tables:
        if not table.isUnicode():
            continue
        if table.format == 4 and cp > 0xFFFF:
            continue
        table.cmap[cp] = name
    return name


def ensure_repertoire(font, donor_path) -> int:
    """Copy every assigned codepoint the donor carries and this face lacks.

    Sarasa Gothic is 4,900 codepoints narrower than Sarasa Term (combining marks,
    IPA, Latin/Cyrillic extended). Google Fonts' shape_languages check turns those gaps
    into failures for languages the family otherwise covers, so the sans faces take
    Term's repertoire; both families are the same design and the copy is outline-only.
    """
    donor = TTFont(str(donor_path))
    donor_cmap = donor.getBestCmap()
    missing = sorted(set(donor_cmap) - set(font.getBestCmap()))
    added = 0
    for cp in missing:
        if unicodedata.category(chr(cp)) in ("Cc", "Cf", "Zs", "Zl", "Zp", "Cn"):
            continue
        if _add_glyph(font, donor, cp):
            added += 1
    return added


def ensure(font, donor_path) -> list[str]:
    wanted = missing_codepoints(font) + missing_pairs(font)
    if not wanted:
        return []
    donor = TTFont(str(donor_path))
    added = []
    for cp in sorted(set(wanted)):
        name = _add_glyph(font, donor, cp)
        if name:
            added.append(f"U+{cp:04X}->{name}")
    return added


def faces(targets: list[str]) -> list[Path]:
    out: list[Path] = []
    for target in targets:
        path = Path(target)
        out.extend(sorted(path.glob("*.ttf")) if path.is_dir() else [path])
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    mode, rest = argv[1], argv[2:]
    if mode == "--fix":
        donor, targets = rest[0], rest[1:]
        for path in faces(targets):
            font = TTFont(path)
            added = ensure(font, donor)
            font.save(path)
            print(f"{path.name}: added {len(added)} " + " ".join(added))
        return 0
    if mode != "--check":
        print(__doc__)
        return 2
    ok = 0
    paths = faces(rest)
    for path in paths:
        font = TTFont(path)
        gaps = missing_codepoints(font)
        pairs = missing_pairs(font)
        if gaps or pairs:
            print(
                f"FAIL {path.name}: GF_Latin_Core {len(CORE) - len(gaps)}/{len(CORE)}"
                + (" missing " + " ".join(f"U+{cp:04X}" for cp in gaps) if gaps else "")
                + (" pairs " + " ".join(f"U+{cp:04X}" for cp in pairs) if pairs else "")
            )
        else:
            ok += 1
            print(f"PASS {path.name}: GF_Latin_Core {len(CORE)}/{len(CORE)}")
    print(f"{ok}/{len(paths)} faces, GF_Latin_Core {len(CORE)}/" + str(len(CORE)))
    return 0 if ok == len(paths) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
