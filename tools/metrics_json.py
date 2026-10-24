#!/usr/bin/env python3
"""Emit the numbers the site prints, straight from the built faces.

usage: metrics_json.py --out site/src/data/metrics.generated.json fonts/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qublack_font import measure  # noqa: E402

FAMILIES = {"QuBlackMono": "Qu Black Mono", "QuBlackSans": "Qu Black Sans"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    faces = {}
    for path in sorted(args.target.glob("*.ttf")):
        data = measure(path)
        faces[path.stem] = data

    payload = {"faces": faces, "families": {}}
    for slug, display in FAMILIES.items():
        regular = faces.get(f"{slug}-Regular")
        if regular is None:
            continue
        han = regular["advances"]["汉"]
        ascii_advance = regular["advances"]["a"]
        payload["families"][slug] = {
            "display": display,
            "upm": regular["upm"],
            "glyphs": regular["glyphs"],
            "han": han,
            "ascii": ascii_advance,
            "ratio": round(han / ascii_advance, 3),
            "lineHeight": regular["lineHeight"],
            "styles": sorted(name.split("-", 1)[1] for name in faces if name.startswith(slug)),
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for slug, data in payload["families"].items():
        print(f"{slug}: upm {data['upm']}, 汉 {data['han']:.3f}em, a {data['ascii']:.3f}em, ratio {data['ratio']:.3f}, glyphs {data['glyphs']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
