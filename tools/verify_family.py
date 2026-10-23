#!/usr/bin/env python3
"""Compare built faces against a recorded baseline. Metrics only, never hashes.

a rebuild differs in glyph order and name records, so a hash can never be the pass condition. Any
drift in upm, advances, ink, line height or glyph count is a failure and names the face and field.

usage:
  verify_family.py <dir-or-face...>                          # full diff against baseline-v2.json
  verify_family.py <dir-or-face...> --against <baseline.json>
  verify_family.py <dir-or-face...> --against reference/baseline-v1.json --grid-only
  verify_family.py <dir-or-face...> --record reference/baseline-v2.json

`--grid-only` keeps only the fields a re-weighting is not allowed to move: upm, glyph count,
codepoint count, line height and every advance. Ink is deliberately excluded there, which lets
`reference/baseline-v1.json` (the v1.0.4 build) stay the grid reference while
`reference/baseline-v2.json` records the ink of the VF-master build.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from qublack_font import baseline_entry, measure, write_json

REPO = Path(__file__).resolve().parent.parent
GRID_PREFIXES = ("upm", "glyphs", "codepoints", "lineHeight", "advances.")


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


def grid_only(fields: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in fields.items() if key.startswith(GRID_PREFIXES)}


def faces(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found.extend(sorted(p for p in path.glob("*.ttf")))
        else:
            found.append(path)
    return found


def record(paths: list[Path], target: Path) -> int:
    payload = {path.stem: baseline_entry(path) for path in paths}
    write_json(target, payload)
    print(f"recorded {len(payload)} faces -> {target}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("targets", nargs="+", type=Path)
    parser.add_argument("--against", type=Path, default=REPO / "reference/baseline-v2.json")
    parser.add_argument("--grid-only", action="store_true", help="compare grid invariants only")
    parser.add_argument("--record", type=Path, help="write the baseline from these faces and exit")
    args = parser.parse_args()

    built = faces(args.targets)
    if not built:
        print("no faces found", file=sys.stderr)
        return 2
    if args.record:
        return record(built, args.record)

    baseline = json.loads(args.against.read_text(encoding="utf-8"))
    label = "grid" if args.grid_only else "metrics"
    failures = 0
    for path in built:
        expected = baseline.get(path.stem) or baseline.get(path.name)
        if expected is None:
            print(f"FAIL  {path.name}: not in the baseline")
            failures += 1
            continue
        got = flatten(measure(path))
        want = flatten(expected)
        if args.grid_only:
            got, want = grid_only(got), grid_only(want)
        diffs = [f"{key}: {got.get(key)!r} != {want.get(key)!r}" for key in want if got.get(key) != want.get(key)]
        if diffs:
            failures += 1
            print(f"FAIL  {path.name}: " + "; ".join(diffs[:6]))
        elif args.grid_only:
            print(f"PASS  {path.name}: grid identical (upm {want['upm']}, 汉 {want['advances.汉']:.4f}em, a {want['advances.a']:.4f}em, {want['glyphs']} glyphs)")
        else:
            print(
                f"PASS  {path.name}: metrics identical to baseline "
                f"(upm {want['upm']}, 汉 {want['advances.汉']:.3f}em, a {want['advances.a']:.3f}em, "
                f"{want['glyphs']} glyphs)"
            )

    print(f"{len(built) - failures}/{len(built)} faces matched {args.against.name} ({label})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
