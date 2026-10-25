#!/usr/bin/env bash
# Build all eight Qu Black faces from the pinned sources committed in this directory.
#
#   bash sources/build.sh [out-dir]        # default: fonts/ttf
#
# One command, no network: the five-hundred-megabyte upstream archives are unpacked in
# sources/upstream and hash-checked by MANIFEST.sha256 (sources/check-sources.sh, which works on
# macOS and Linux). Requirements: python3 with tools/requirements.txt installed (fonttools,
# brotli, unicodedata2).
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
out=${1:-$repo/fonts/ttf}

bash "$repo/sources/check-sources.sh" "$repo/sources/upstream"

python3 tools/build_all.py --sources "$repo/sources/upstream" --out "$out"
