#!/usr/bin/env bash
# Build all eight Qu Black faces from the pinned sources committed in this directory.
#
#   bash sources/build.sh [out-dir]        # default: fonts/ttf
#
# One command, no network: the five-hundred-megabyte upstream archives are unpacked in
# sources/upstream and hash-checked by MANIFEST.sha256. Requirements: python3 with
# tools/requirements.txt installed (fonttools, brotli, unicodedata2).
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
out=${1:-$repo/fonts/ttf}

cd "$repo/sources/upstream"
shasum -a 256 -c MANIFEST.sha256 > /dev/null
cd "$repo"

python3 tools/build_all.py --sources "$repo/sources/upstream" --out "$out"
