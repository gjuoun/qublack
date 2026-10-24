#!/usr/bin/env python3
"""Instance the pinned Recursive variable donor into the Latin master each style needs.

Recursive ships five axes (MONO, CASL, wght, slnt, CRSV). QuBlack Linear is one point in that
space; only wght and slnt move between faces:

    mono  MONO=1  CASL=0  CRSV=0
    sans  MONO=0  CASL=0  CRSV=0
    upright italics  slnt=0 / slnt=-15      wght 400 / 700

Instancing is cheap (1,304 glyphs, ~1 s) but repeated eight times per build, so the per-style
results are cached under ~/.cache/qublack keyed by donor size, mode, style and cache version.

RECONCILE — the loaded outlines are not the shipped ones. ArrowType's static releases bake the
donor's own feature substitutions, and drawing a glyph from the VF never applies them: the statics
carry l.mono / f.mono / g.mono / i.mono / r.mono and, for the proportional sans, l.sans and
zero.sans_pnum. Measured on the shipped statics, the untouched defaults differ by 14.6-29.7% of ink
area (i is 29.7% lighter), and the substituted ones by 0.4-0.6%. So after instancing, every
0x20-0x7E glyph is matched against the matching ArrowType static (same weight) and the default slot
is rewritten with the best of the default and its name.* alternates. The pick is proven by ink
area, not by feature name, and a residual above the tolerance aborts the build instead of shipping a
face whose strokes disagree with the statics.

usage: latin_masters.py <donor-vf> [--mode mono] [--style Regular] [--check] [--out face.ttf]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pathops
from fontTools.pens.pointPen import PointToSegmentPen
from fontTools.pens.recordingPen import DecomposingRecordingPointPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

REPO = Path(__file__).resolve().parent.parent
DEFAULT_SOURCES = Path(os.environ.get("QUBLACK_SOURCES") or REPO / "sources/upstream")
CACHE = Path.home() / ".cache" / "qublack"
DEFAULT_DONOR = "Recursive_VF_1.085.ttf"
# Bump when the cached instance changes shape. 2 = the rvrn/mono reconcile above.
CACHE_VERSION = 2
# Percent of the static glyph's ink area a reconciled glyph may still differ by.
TOLERANCE = 2.5
ASCII = range(0x20, 0x7F)

# Everything the Linear design pins, except the two axes a face is allowed to move along.
MODE_AXES = {
    "mono": {"MONO": 1.0, "CASL": 0.0, "CRSV": 0.0},
    "sans": {"MONO": 0.0, "CASL": 0.0, "CRSV": 0.0},
}
STYLE_AXES = {
    "Regular": {"wght": 400.0, "slnt": 0.0},
    "Bold": {"wght": 700.0, "slnt": 0.0},
    "Italic": {"wght": 400.0, "slnt": -15.0},
    "BoldItalic": {"wght": 700.0, "slnt": -15.0},
}
# Where the static release of each mode/style lives under --sources.
STATIC_DONORS = {
    "mono": ("rec_mono", "RecursiveMonoLnrSt-{style}.ttf"),
    "sans": (
        "ArrowType-Recursive-1.085/Recursive_Desktop/separate_statics/TTF",
        "RecursiveSansLnrSt-{style}.ttf",
    ),
}


def donor_for(sources: Path) -> Path:
    return sources / DEFAULT_DONOR


def static_donor(sources: Path, mode: str, style: str) -> Path:
    directory, pattern = STATIC_DONORS[mode]
    return sources / directory / pattern.format(style=style)


def location(mode: str, style: str) -> dict[str, float]:
    try:
        axes = dict(MODE_AXES[mode])
        axes.update(STYLE_AXES[style])
    except KeyError as error:
        raise SystemExit(f"unknown {error.args[0]!r}; expected {sorted(MODE_AXES)} / {sorted(STYLE_AXES)}") from None
    return axes


def path_of(font: TTFont, name: str) -> pathops.Path:
    glyph_set = font.getGlyphSet()
    path = pathops.Path()
    glyph_set[name].draw(path.getPen(glyphSet=glyph_set))
    return path


def ink_area(font: TTFont, name: str) -> float:
    """Area of the outline at this weight, counters excluded.

    Simplified first: on a glyph whose contour touches itself (bold O, Q) the raw path reports an
    area larger than its own ink. The simplified copy is read for its area only — feeding it into
    another PathOp makes Skia treat the two paths as disjoint.
    """
    path = path_of(font, name)
    resolved = pathops.Path()
    resolved.fillType = path.fillType
    resolved.addPath(path)
    resolved.simplify()
    return abs(resolved.area)


def difference_area(candidate: pathops.Path, reference: pathops.Path) -> float:
    """Ink the two outlines do not share. Kept for callers that want a shape delta."""
    overlap = abs(pathops.op(candidate, reference, pathops.PathOp.INTERSECTION).area)
    return max(0.0, abs(candidate.area) + abs(reference.area) - 2 * overlap)


def _decompose(instance: TTFont, name: str):
    """A simple glyph with every component flattened, exactly as build_qublack draws it."""
    glyph_set = instance.getGlyphSet()
    recorded = DecomposingRecordingPointPen(glyph_set)
    glyph_set[name].drawPoints(recorded)
    pen = TTGlyphPen(None)
    segment = PointToSegmentPen(pen)
    for operation, args, *kwargs in recorded.value:
        getattr(segment, operation)(*args, **(kwargs[0] if kwargs and kwargs[0] else {}))
    glyph = pen.glyph()
    glyph.recalcBounds(instance["glyf"])
    return glyph


def _bounds(font: TTFont, name: str) -> tuple[float, float, float, float]:
    return path_of(font, name).bounds


def _candidates(instance: TTFont, name: str) -> list[str]:
    return [candidate for candidate in instance.getGlyphOrder() if candidate.startswith(name + ".")]


def reconcile(instance: TTFont, reference: TTFont) -> tuple[list[str], float, str]:
    """Rewrite each ASCII slot with the donor glyph the static release actually shipped.

    Returns the substituted glyph names, the worst remaining ink-area delta in percent, and the
    character it belongs to.
    """
    cmap, ref_cmap = instance.getBestCmap(), reference.getBestCmap()
    glyf = instance["glyf"]
    picks: list[str] = []
    worst = (0.0, "?")
    for cp in ASCII:
        name, ref_name = cmap.get(cp), ref_cmap.get(cp)
        if not name or not ref_name:
            continue
        area = ink_area(reference, ref_name)
        if area <= 0:
            continue
        box = _bounds(reference, ref_name)
        # Measured on the shipped donors: the alternates the static release used sit within 0.5
        # units of its box, the rejected ones (italic, .case, .titl, .sans) at 5-20% of the em.
        box_tolerance = 0.01 * reference["head"].unitsPerEm

        def score(candidate: str) -> float | None:
            # The same drawing in another encoding has the same box and the same ink. A .case
            # alternate is the same drawing moved up (same area, different box), so the box filters
            # it out before the area is asked which form the static release used.
            if max(abs(a - b) for a, b in zip(_bounds(instance, candidate), box)) > box_tolerance:
                return None
            return abs(ink_area(instance, candidate) - area) / area * 100

        # An alternate has to be clearly better than the default, so a tie (the .case forms share
        # the default's area) never swaps in a shifted copy for nothing.
        margin = 0.1
        default_score = score(name)
        best = (default_score if default_score is not None else float("inf"), name)
        threshold = best[0] - margin
        for candidate in _candidates(instance, name):
            value = score(candidate)
            if value is not None and value < threshold:
                best, threshold = (value, candidate), value - margin

        if best[1] != name:
            # Fully decompose the alternate into the default slot. Some alternates are composites
            # over the very glyph being replaced (i.mono draws dotlessi.mono, which draws i), so a
            # component-preserving copy turns the slot into a cycle. The decomposition is checked
            # against the alternate's own ink, because a pen round-trip is where the shape is lost.
            before = ink_area(instance, best[1])
            glyf[name] = _decompose(instance, best[1])
            after = ink_area(instance, name)
            if before <= 0 or abs(after - before) / before > 0.005:
                raise SystemExit(
                    f"[latin] {name}: decomposed {best[1]} changed its ink ({before:.0f} -> {after:.0f} u^2)"
                )
            picks.append(best[1])
        value = best[0]

        if value > worst[0]:
            worst = (value, chr(cp))
    return sorted(picks), worst[0], worst[1]


def instance(donor: Path, mode: str, style: str, sources: Path = DEFAULT_SOURCES, cache: Path = CACHE) -> TTFont:
    """Return the donor instanced at one style, reconciled to the static release, cached."""
    cache.mkdir(parents=True, exist_ok=True)
    static = static_donor(Path(sources), mode, style)
    if not static.exists():
        raise SystemExit(f"missing static donor: {static} (needed to reconcile the Latin outlines)")
    key = f"{donor.stem}-{donor.stat().st_size}-{mode}-{style}-v{CACHE_VERSION}"
    cached = cache / f"{key}.ttf"
    if cached.exists():
        return TTFont(str(cached), lazy=True)
    print(f"[latin] instancing {donor.name} at {mode}/{style} {location(mode, style)}", flush=True)
    variable = TTFont(str(donor))
    static_font = TTFont(str(static))
    master = instantiateVariableFont(variable, location(mode, style), inplace=True, updateFontNames=False)
    picks, worst, worst_char = reconcile(master, static_font)
    if worst > TOLERANCE:
        raise SystemExit(
            f"[latin] {mode}/{style}: {worst_char!r} still differs from {static.name} by {worst:.2f}% "
            f"(tolerance {TOLERANCE}%); the donor and the static release disagree"
        )
    print(
        f"[latin] reconciled {len(picks)} alternates ({' '.join(picks) or 'none'}), "
        f"worst residual {worst:.2f}% ({worst_char})",
        flush=True,
    )
    master.save(str(cached))
    return TTFont(str(cached), lazy=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("donor", type=Path)
    parser.add_argument("--mode", choices=sorted(MODE_AXES), default="mono")
    parser.add_argument("--style", choices=sorted(STYLE_AXES), default="Regular")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--check", action="store_true", help="report the reconcile and fail above the tolerance")
    parser.add_argument("--out", type=Path, help="write the instance here")
    args = parser.parse_args()

    if args.check:
        static = static_donor(args.sources, args.mode, args.style)
        if not static.exists():
            print(f"FAIL  latin donor {args.mode}/{args.style}: missing static release {static}")
            return 1
        master = TTFont(str(args.donor))
        reference = TTFont(str(static))
        instantiateVariableFont(master, location(args.mode, args.style), inplace=True, updateFontNames=False)
        picks, worst, worst_char = reconcile(master, reference)
        status = "FAIL" if worst > TOLERANCE else "PASS"
        print(
            f"{status}  latin donor {args.mode}/{args.style}: {len(picks)} alternates "
            f"({' '.join(picks) or 'none'}), worst residual {worst:.2f}% ({worst_char})"
        )
        return 1 if status == "FAIL" else 0

    master = instance(args.donor, args.mode, args.style, args.sources)
    print(f"instance {args.mode}/{args.style} {location(args.mode, args.style)} glyphs {len(master.getGlyphOrder())}")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        master.save(str(args.out))
        print(f"saved {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
