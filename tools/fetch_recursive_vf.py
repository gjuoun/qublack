#!/usr/bin/env python3
"""Fetch the pinned Latin variable donor into the sources directory.

v1.2.0 swaps the Latin from Recursive's four static faces to one variable source, so the upright
family can grow a weight axis: the statics are independently drawn per weight (Regular and Bold
disagree on 51 of 95 ASCII glyphs in point structure), while a single `gvar` source is
interpolatable. The added axis cost is nothing — the file is 2.4 MB and already carries
`MONO`, `CASL`, `wght`, `slnt` and `CRSV`.

The download is pinned to the same google/fonts commit as `fetch_cjk_vf.py` and verified by size
and SHA-256 before it takes its real name, so a rebuild never depends on whatever `main` points
at today. The pinned bytes are identical to the `Recursive_VF_1.085.ttf` inside the v1.085
release archive the static donors came from.

usage: fetch_recursive_vf.py [--sources DIR] [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_qublack import DEFAULT_SOURCES  # noqa: E402

PIN = {
    "commit": "2894aab31764f10f29c421bdfd2340d3b382d384",
    "path": "ofl/recursive/Recursive%5BCASL,CRSV,MONO,slnt,wght%5D.ttf",
    "name": "Recursive_VF_1.085.ttf",
    "sha256": "653221ca467f4732fe6856ac493f6c409e9f56a7674abe36b2364acc89796f7c",
    "bytes": 2379132,
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
