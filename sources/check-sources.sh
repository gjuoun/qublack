#!/usr/bin/env bash
# Verify the committed upstream sources against their recorded hashes.
#
#   bash sources/check-sources.sh [dir]      # default: sources/upstream
#
# `shasum` is a macOS habit — ubuntu 24.04 and the GitHub runner image ship coreutils'
# `sha256sum` and no Digest::SHA wrapper, so the check picks whichever is present. Both read the
# same `<hash>  <path>` manifest format.
set -euo pipefail

dir=$(cd "${1:-$(dirname "$0")/upstream}" && pwd)
[ -f "$dir/MANIFEST.sha256" ] || { echo "no manifest at $dir/MANIFEST.sha256" >&2; exit 2; }

cd "$dir"
if command -v shasum >/dev/null 2>&1; then
  shasum -a 256 -c MANIFEST.sha256 > /dev/null
else
  sha256sum -c MANIFEST.sha256 > /dev/null
fi
printf 'sources: %s files ok\n' "$(wc -l < MANIFEST.sha256 | tr -d ' ')"
