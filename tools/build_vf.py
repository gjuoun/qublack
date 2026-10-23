#!/usr/bin/env python3
"""Build the wght-axis variable faces from two masters per family.

Per family:

  1. build the 400 and the 700 master with the normal pipeline (same skeletons, same CJK donor,
     same Latin donor instanced at the matching weight), so the VF cannot drift from the statics;
  2. freeze every glyph whose point structure differs between the two (tools/vf_masters.py);
  3. merge them with fontTools.varLib into one face per family.

BASE is excluded from the merge and rebuilt from the finished VF: measured on the Noto donor, the
merger aborts with UnsupportedFormat on a baseline coordinate, and BASE has no variation model in
fontTools. GSUB/GPOS stay in the merge — their only weight-dependent content is anchor
coordinates, which is exactly what the axis should carry.

usage: build_vf.py [--sources DIR] [--out DIR] [--only mono|sans] [--keep-masters DIR]
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import time
from pathlib import Path

from fontTools import varLib
from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, SourceDescriptor
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_qublack import DEFAULT_SOURCES, DISPLAY, REPO, SLUGS, build, resolve_donor, resolve_latin_donor  # noqa: E402
from gf_tables import write_base  # noqa: E402
from vf_masters import freeze  # noqa: E402
from vf_tables import prepare, release_version  # noqa: E402

WEIGHTS = {400: "Regular", 700: "Bold"}


def designspace(light: Path, heavy: Path, target: Path) -> Path:
    doc = DesignSpaceDocument()
    axis = AxisDescriptor()
    axis.name = "Weight"
    axis.tag = "wght"
    axis.minimum, axis.default, axis.maximum = 400, 400, 700
    doc.addAxis(axis)
    for weight, path in ((400, light), (700, heavy)):
        source = SourceDescriptor()
        source.path = str(path)
        source.name = f"wght{weight}"
        source.location = {"Weight": weight}
        source.familyName = "QuBlack"
        source.styleName = WEIGHTS[weight]
        doc.addSource(source)
    doc.write(str(target))
    return target


def build_family(mode: str, sources: Path, outdir: Path, workdir: Path, latin_vf: Path, cjk_vf: Path) -> Path:
    slug, display = SLUGS[mode], DISPLAY[mode]
    masters: dict[int, Path] = {}
    for weight, style in WEIGHTS.items():
        masters[weight] = build(
            mode, style, sources, workdir / f"wght{weight}", REPO, cjk_vf=cjk_vf, latin_vf=latin_vf
        )

    light = TTFont(str(masters[400]))
    heavy = TTFont(str(masters[700]))
    buckets = freeze(light, heavy)
    frozen = sum(buckets.values())
    heavy.save(str(masters[700]))

    merged = varLib.build(str(designspace(masters[400], masters[700], workdir / f"{slug}.designspace")), exclude=["BASE"])[0]
    merged["name"].names = []
    prepare(merged, f"{display} VF", f"{slug}VF", release_version())
    write_base(merged)
    merged["maxp"].numGlyphs = len(merged.getGlyphOrder())

    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{slug}[wght].ttf"
    merged.save(str(out))

    codepoints = len(merged.getBestCmap())
    size = out.stat().st_size
    print(
        f"PASS  {out.name}: fvar wght 400..700 default 400, {len(merged.getGlyphOrder())} glyphs, "
        f"{codepoints} codepoints, {frozen} frozen, gvar 2 masters, {size:,} B",
        flush=True,
    )
    for key, count in sorted(buckets.items(), key=lambda item: -item[1]):
        print(f"        frozen {key:14} {count}", flush=True)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--out", type=Path, default=REPO / "fonts/vf")
    parser.add_argument("--only", choices=sorted(SLUGS), default=None)
    parser.add_argument("--keep-masters", type=Path, default=None, help="copy the two masters here")
    args = parser.parse_args()

    cjk_vf = resolve_donor(None, args.sources, False)
    latin_vf = resolve_latin_donor("auto", args.sources, False)
    if latin_vf is None:
        raise SystemExit("no Latin donor resolved; pass --latin-vf or fetch Recursive_VF_1.085.ttf")

    modes = [args.only] if args.only else ["mono", "sans"]
    started = time.time()
    built = []
    with tempfile.TemporaryDirectory(prefix="qublack-vf-") as temp:
        workdir = Path(temp)
        for mode in modes:
            built.append(build_family(mode, args.sources, args.out, workdir, latin_vf, cjk_vf))
        if args.keep_masters:
            args.keep_masters.mkdir(parents=True, exist_ok=True)
            for mode in modes:
                for weight, style in WEIGHTS.items():
                    source = workdir / f"wght{weight}" / f"{SLUGS[mode]}-{style}.ttf"
                    if source.exists():
                        shutil.copy2(source, args.keep_masters / source.name)
    print(f"built {len(built)} VF faces in {time.time() - started:.0f}s -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
