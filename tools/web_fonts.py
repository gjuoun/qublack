#!/usr/bin/env python3
"""Cut the built faces into woff2 shards with unicode-range CSS for the specimen site.

A 25 MB CJK TTF cannot be a web font. Each face is split into ~700-codepoint shards (about
120 KB of woff2), each exposed through its own @font-face + unicode-range, so a page downloads
only the shards whose codepoints it actually renders. Tiers are ordered so the first shards are
the ones a first paint needs: ASCII/punctuation/box drawing, then GB2312 level-1 hanzi, then the
rest of the BMP.

Deterministic on purpose: sorted file names, fixed head timestamps, no CSS comments carrying
counts — so `--check` can regenerate into a temp dir and byte-compare.

usage:
  web_fonts.py --out site/public/fonts --css site/src/styles/qublack-fonts.css
  web_fonts.py --check --out site/public/fonts --css site/src/styles/qublack-fonts.css
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

REPO = Path(__file__).resolve().parent.parent
FACES = [
    ("QuBlackMono", "QuBlack Mono", "Regular", 400, "normal"),
    ("QuBlackMono", "QuBlack Mono", "Bold", 700, "normal"),
    ("QuBlackMono", "QuBlack Mono", "Italic", 400, "italic"),
    ("QuBlackMono", "QuBlack Mono", "BoldItalic", 700, "italic"),
    ("QuBlackSans", "QuBlack Sans", "Regular", 400, "normal"),
    ("QuBlackSans", "QuBlack Sans", "Bold", 700, "normal"),
    ("QuBlackSans", "QuBlack Sans", "Italic", 400, "italic"),
    ("QuBlackSans", "QuBlack Sans", "BoldItalic", 700, "italic"),
]
TIER_LATIN = [(0x20, 0x7E), (0xA0, 0xFF), (0x2000, 0x206F), (0x2190, 0x21FF), (0x2500, 0x25FF),
              (0x2800, 0x28FF), (0x3000, 0x303F), (0xFF00, 0xFFEF)]
TIER_GB2312_LEVEL1 = (0xB0A1, 0xD7F9)
# Seconds since 1904-01-01, fixed so every shard is reproducible.
FIXED_EPOCH = 3800000000


def page_codepoints(site_dir: Path) -> set[int]:
    """Every character the site's own copy uses, so the first shard covers a first paint."""

    chars: set[int] = set()
    for path in site_dir.rglob("*"):
        if path.suffix not in {".astro", ".ts", ".tsx", ".json", ".css", ".md"}:
            continue
        if "node_modules" in path.parts or path.name.endswith("qublack-fonts.css"):
            continue
        chars.update(ord(char) for char in path.read_text(encoding="utf-8", errors="ignore"))
    return chars


def ordered_codepoints(cmap: dict[int, str], priority: set[int]) -> list[int]:
    """Tier 0: the site's own text. Tier 1: latin/punctuation/box drawing. Tier 2: GB2312 level-1.
    Tier 3: the rest, in codepoint order."""

    seen: set[int] = set()
    ordered: list[int] = []

    def take(cp: int) -> None:
        if cp in cmap and cp not in seen:
            seen.add(cp)
            ordered.append(cp)

    for cp in sorted(priority):
        take(cp)

    for lo, hi in TIER_LATIN:
        for cp in range(lo, hi + 1):
            take(cp)

    gb: list[int] = []
    for row in range(0xB0, 0xD8):
        for cell in range(0xA1, 0xFF):
            try:
                char = bytes([row, cell]).decode("gb2312")
            except UnicodeDecodeError:
                continue
            gb.append(ord(char))
    for cp in gb:
        take(cp)

    for cp in sorted(cmap):
        take(cp)
    return ordered


def subset_shard(job: tuple[str, list[int], str]) -> tuple[str, int]:
    source, codepoints, out = job
    font = TTFont(source)
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14]
    options.hinting = False
    options.recalc_timestamp = False
    options.drop_tables += ["DSIG"]
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=codepoints)
    subsetter.subset(font)
    # A fixed head.modified/created is what makes the shards byte-identical across runs:
    # the field keeps its length but changes the brotli stream, so `--check` can diff bytes.
    font.recalcTimestamp = False
    font["head"].modified = FIXED_EPOCH
    font["head"].created = FIXED_EPOCH
    font.flavor = "woff2"
    font.save(out)
    return Path(out).name, Path(out).stat().st_size


def css_ranges(codepoints: list[int]) -> str:
    parts: list[str] = []
    start = prev = codepoints[0]
    for cp in codepoints[1:]:
        if cp == prev + 1:
            prev = cp
            continue
        parts.append(f"U+{start:X}-{prev:X}" if start != prev else f"U+{start:X}")
        start = prev = cp
    parts.append(f"U+{start:X}-{prev:X}" if start != prev else f"U+{start:X}")
    return ",".join(parts)


def build(fonts_dir: Path, out_dir: Path, css_path: Path, chunk: int, workers: int,
          site_dir: Path | None = None) -> int:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs: list[tuple[str, list[int], str]] = []
    plan: list[tuple[str, str, str, int, str, list[tuple[str, list[int]]]]] = []
    for slug, display, style, weight, font_style in FACES:
        source = fonts_dir / f"{slug}-{style}.ttf"
        if not source.exists():
            raise SystemExit(f"missing face: {source} — run tools/build_all.py first")
        cmap = TTFont(str(source)).getBestCmap()
        priority = page_codepoints(site_dir) if site_dir else set()
        ordered = ordered_codepoints(cmap, priority)
        shards: list[tuple[str, list[int]]] = []
        for index in range(0, len(ordered), chunk):
            codepoints = ordered[index : index + chunk]
            name = f"{slug}-{style}.{index // chunk}.woff2"
            jobs.append((str(source), codepoints, str(out_dir / name)))
            shards.append((name, codepoints))
        plan.append((slug, display, style, weight, font_style, shards))

    with ProcessPoolExecutor(max_workers=workers) as pool:
        sizes = dict(pool.map(subset_shard, jobs))

    lines = [
        "/* Generated by tools/web_fonts.py — do not edit. One @font-face per woff2 shard. */",
    ]
    for slug, display, style, weight, font_style, shards in plan:
        for name, codepoints in shards:
            lines.append(
                "@font-face{"
                f'font-family:"{display}";'
                f'font-style:{font_style};font-weight:{weight};font-display:swap;'
                f'src:url("/fonts/{name}") format("woff2");'
                f"unicode-range:{css_ranges(codepoints)}}}"
            )
    css_path.parent.mkdir(parents=True, exist_ok=True)
    css_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    total = sum(sizes.values())
    first = sizes[plan[0][5][0][0]]
    print(f"web fonts: {len(jobs)} shards, {total / 1e6:.1f} MB total, first shard {first / 1024:.0f} KB")
    return 0


def check(out_dir: Path, css_path: Path, chunk: int, workers: int, fonts_dir: Path,
          site_dir: Path | None = None) -> int:
    temp = Path("/tmp/jun/qublack-webfonts-check")
    if temp.exists():
        shutil.rmtree(temp)
    code = build(fonts_dir, temp / "fonts", temp / "fonts.css", chunk, workers, site_dir)
    if code:
        return code
    left = sorted(p.name for p in (temp / "fonts").glob("*.woff2"))
    right = sorted(p.name for p in out_dir.glob("*.woff2"))
    if left != right:
        print(f"FAIL  shard set differs: {len(left)} generated vs {len(right)} on disk")
        return 1
    mismatch = [name for name in left if not filecmp.cmp(temp / "fonts" / name, out_dir / name, shallow=False)]
    css_differs = (temp / "fonts.css").read_text() != css_path.read_text()
    if mismatch or css_differs:
        print(
            f"FAIL  regeneration differs ({len(mismatch)} shards byte-differ, "
            f"css {'differs' if css_differs else 'identical'})"
        )
        return 1
    print(f"PASS  deterministic: {len(left)} shards and the CSS regenerate byte-identically")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fonts", type=Path, default=REPO / "fonts")
    parser.add_argument("--out", type=Path, default=REPO / "site/public/fonts")
    parser.add_argument("--css", type=Path, default=REPO / "site/src/styles/qublack-fonts.css")
    parser.add_argument("--chunk", type=int, default=700)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--site", type=Path, default=REPO / "site/src")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        return check(args.out, args.css, args.chunk, args.workers, args.fonts, args.site)
    return build(args.fonts, args.out, args.css, args.chunk, args.workers, args.site)


if __name__ == "__main__":
    sys.exit(main())
