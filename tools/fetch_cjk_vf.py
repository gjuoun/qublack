#!/usr/bin/env python3
"""Fetch the pinned CJK variable donor into the sources directory.

The hanzi outlines of every QuBlack face come from one weight-axis master set, so the family can
grow a variable font later: Sarasa's Regular and Bold CJK are independently drawn (410 of 500 URO
glyphs differ in contour/point structure), while Noto Sans SC VF is a single interpolatable source
(same Source Han Sans design Sarasa embeds, SIL OFL 1.1, axis wght 100-900).

The download is pinned to one google/fonts commit and verified by size and SHA-256 before it is
moved into place, so a rebuild never depends on whatever `main` points at today.

usage: fetch_cjk_vf.py [--sources DIR] [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_qublack import DEFAULT_SOURCES  # noqa: E402

PIN = {
    "commit": "2894aab31764f10f29c421bdfd2340d3b382d384",
    "path": "ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf",
    "name": "NotoSansSC-VF.ttf",
    "sha256": "a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da",
    "bytes": 17772300,
}
URL = f"https://raw.githubusercontent.com/google/fonts/{PIN['commit']}/{PIN['path']}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(dest: Path) -> None:
    """Stream the donor to <dest>.part, then verify before it takes the real name."""
    partial = dest.with_suffix(dest.suffix + ".part")
    digest = hashlib.sha256()
    size = 0
    print(f"GET {URL}", flush=True)
    with urllib.request.urlopen(URL, timeout=120) as response, partial.open("wb") as handle:
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            handle.write(chunk)
            digest.update(chunk)
            size += len(chunk)
    got = digest.hexdigest()
    if size != PIN["bytes"] or got != PIN["sha256"]:
        partial.unlink(missing_ok=True)
        raise SystemExit(f"FAIL sha256 {got} ({size} bytes) != {PIN['sha256']} ({PIN['bytes']} bytes)")
    partial.replace(dest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--force", action="store_true", help="re-download even when the cached copy verifies")
    args = parser.parse_args()

    dest = args.sources / PIN["name"]
    if dest.exists() and not args.force:
        got = sha256(dest)
        if got == PIN["sha256"]:
            print(f"cached {dest}")
            return 0

    args.sources.mkdir(parents=True, exist_ok=True)
    download(dest)
    print(f"PASS sha256 {PIN['sha256']}")
    print(f"{dest.name} {dest.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
