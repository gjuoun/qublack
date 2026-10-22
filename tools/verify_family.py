#!/usr/bin/env python3
"""Compare built faces against the recorded baseline (the shipped JunHei family).

The baseline is metric-based on purpose: a rebuild differs in glyph order and name records, so
hashes can never be the pass condition. Any drift in upm, advances, ink, line height or glyph
count is a failure and names the face and the field.

usage: verify_family.py <dir-or-face...> [--against reference/baseline-v1.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from qublack_font import measure

REPO = Path(__file__).resolve().parent.parent


def flatten(data: dict, prefix: str = "") -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in data.items():
        if key in ("file", "family", "postscript"):
            continue
        if isinstance(value, dict):
            out.update(flatten(value, f"{prefix}{key}."))
        elif value is not None:
            out[f"{prefix}{key}"] = value
    return out


def faces(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found.extend(sorted(p for p in path.glob("*.ttf")))
        else:
            found.append(path)
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("targets", nargs="+", type=Path)
    parser.add_argument("--against", type=Path, default=REPO / "reference/baseline-v1.json")
    args = parser.parse_args()

    baseline = json.loads(args.against.read_text(encoding="utf-8"))
    built = faces(args.targets)
    if not built:
        print("no faces found", file=sys.stderr)
        return 2

    failures = 0
    for path in built:
        expected = baseline.get(path.stem) or baseline.get(path.name)
        if expected is None:
            print(f"FAIL  {path.name}: not in the baseline")
            failures += 1
            continue
        got = flatten(measure(path))
        want = flatten(expected)
        diffs = [f"{key}: {got.get(key)!r} != {want.get(key)!r}" for key in want if got.get(key) != want.get(key)]
        if diffs:
            failures += 1
            print(f"FAIL  {path.name}: " + "; ".join(diffs[:6]))
        else:
            print(
                f"PASS  {path.name}: metrics identical to baseline "
                f"(upm {want['upm']}, 汉 {want['advances.汉']:.3f}em, a {want['advances.a']:.3f}em, "
                f"{want['glyphs']} glyphs)"
            )

    print(f"{len(built) - failures}/{len(built)} faces matched {args.against.name}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
