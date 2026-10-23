#!/usr/bin/env python3
"""Build all eight QuBlack faces in family order. usage: build_all.py [--out fonts] [--only mono|sans]"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_qublack import DEFAULT_SOURCES, build, resolve_donor  # noqa: E402
from gf_tables import align_family_win_metrics  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
STYLES = ["Regular", "Bold", "Italic", "BoldItalic"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=REPO / "fonts/ttf")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--only", choices=["mono", "sans"], default=None)
    parser.add_argument(
        "--cjk-vf",
        nargs="?",
        const="auto",
        default=None,
        metavar="PATH",
        help="install CJK outlines from this variable donor (no value = <sources>/NotoSansSC-VF.ttf)",
    )
    parser.add_argument("--no-cjk-vf", action="store_true", help="keep the skeleton CJK outlines")
    args = parser.parse_args()
    donor = resolve_donor(args.cjk_vf, args.sources, args.no_cjk_vf)

    modes = [args.only] if args.only else ["mono", "sans"]
    started = time.time()
    built: list[Path] = []
    for mode in modes:
        family = []
        for style in STYLES:
            family.append(build(mode, style, args.sources, args.out, REPO, cjk_vf=donor))
        bottom, top = align_family_win_metrics(family)
        print(f"[{mode}] family win box {bottom}..{top} written to 4 faces", flush=True)
        built.extend(family)
    print(f"built {len(built)} faces in {time.time() - started:.0f}s -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
