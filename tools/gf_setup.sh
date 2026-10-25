#!/usr/bin/env bash
# Install the pinned Google Fonts toolchain used by the GF readiness gate.
#
#   .venv-gf/           gftools + fontbakery + the glyphsets/shaperglot data they need
#   .tools/fontspector  pinned release binary (the profile GF's CI runs)
#
# usage:
#   bash tools/gf_setup.sh                      # venv + fontspector
#   bash tools/gf_setup.sh --fontspector-only    # just the binary (CI runs no fontbakery)
#   bash tools/gf_setup.sh --print-plan [--platform <triple>|all]   # resolve, download nothing
#
# Re-running is cheap: the venv is reused and the tarball is only downloaded when the pinned
# sha256 does not match.
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
venv="$repo/.venv-gf"
tools="$repo/.tools"
version=1.9.0

# fontspector publishes one tarball per target triple. x86_64-unknown-linux-gnu is what the
# GitHub runner needs; there is no aarch64 Linux build, so an arm64 box must run the gate under
# emulation or on another machine.
plan_for() {
  case "$1" in
    aarch64-apple-darwin)      echo 0d34d5f85ac7a2efe57157c31f454e56a759edf888879b53af50b76bb1d6b617 ;;
    x86_64-apple-darwin)       echo 5819e6d61466a4eddbc3cd40d6241790f50bd8ea3e7176e72f546f9f014f4f3b ;;
    x86_64-unknown-linux-gnu)  echo 0d4a7fbc577f7f99a084dec2a7acc13f64f923cbe44c0e3c5e3d76469786b8e2 ;;
    *) return 1 ;;
  esac
}
PINS=(aarch64-apple-darwin x86_64-apple-darwin x86_64-unknown-linux-gnu)

detect() {
  case "$(uname -s):$(uname -m)" in
    Darwin:arm64)  echo aarch64-apple-darwin ;;
    Darwin:x86_64) echo x86_64-apple-darwin ;;
    Linux:x86_64)  echo x86_64-unknown-linux-gnu ;;
    *) echo "no pinned fontspector build for $(uname -s) $(uname -m)" >&2 ; return 1 ;;
  esac
}

digest() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
  else sha256sum "$1" | cut -d' ' -f1; fi
}
check_file() { # <file> <sha256>
  if command -v shasum >/dev/null 2>&1; then echo "$2  $1" | shasum -a 256 -c - >/dev/null
  else echo "$2  $1" | sha256sum -c - >/dev/null; fi
}
asset_url() { echo "https://github.com/fonttools/fontspector/releases/download/fontspector-v${version}/fontspector-${version}-$1.tar.gz"; }

print_plan() { # <triple|all>
  if [ "$1" = all ]; then set -- "${PINS[@]}"; fi
  for triple in "$@"; do
    sha=$(plan_for "$triple") || { echo "no pinned fontspector build for $triple" >&2 ; exit 2; }
    printf 'fontspector %s %-24s sha256 %s\n' "$version" "$triple" "$sha"
    printf 'url %s\n' "$(asset_url "$triple")"
  done
  printf 'target %s\n' "$tools/fontspector"
}

platform=$(detect) || exit 2
fontspector_only=0
while [ $# -gt 0 ]; do
  case "$1" in
    --fontspector-only) fontspector_only=1 ; shift ;;
    --print-plan) mode=print ; shift ;;
    --platform) platform=${2:?--platform needs a triple or 'all'} ; shift 2 ;;
    *) echo "unknown argument: $1" >&2 ; exit 2 ;;
  esac
done
[ "${mode:-}" = print ] && { print_plan "$platform" ; exit 0; }

sha256=$(plan_for "$platform") || { echo "no pinned fontspector build for $platform" >&2 ; exit 2; }
asset="fontspector-${version}-${platform}.tar.gz"

# gflanguages ships pre-3.20 protobuf stubs; gftools and fontbakery both import
# them, and fail with "Descriptors cannot be created directly" without this.
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

if [ "$fontspector_only" -eq 0 ]; then
  if [ ! -x "$venv/bin/python" ]; then
    if command -v uv >/dev/null 2>&1; then
      uv venv --python 3.12 "$venv"
    else
      python3.12 -m venv "$venv"
    fi
  fi
  if command -v uv >/dev/null 2>&1; then
    uv pip install --python "$venv/bin/python" -r "$repo/requirements-gf.txt"
  else
    "$venv/bin/pip" install -r "$repo/requirements-gf.txt"
  fi
else
  echo "fontspector: skipping .venv-gf (--fontspector-only)"
fi

mkdir -p "$tools"
if [ ! -x "$tools/fontspector" ] || [ "$(digest "$tools/$asset" 2>/dev/null || true)" != "$sha256" ]; then
  curl -fsSL -o "$tools/$asset" "$(asset_url "$platform")"
  check_file "$tools/$asset" "$sha256"
  tar xzf "$tools/$asset" -C "$tools"
  mv "$tools/fontspector-${version}-${platform}/fontspector" "$tools/fontspector"
  rm -rf "$tools/fontspector-${version}-${platform}" "$tools/$asset"
  chmod +x "$tools/fontspector"
fi

if [ "$fontspector_only" -eq 0 ]; then
  "$venv/bin/fontbakery" --version
  "$venv/bin/gftools" --version 2>&1 | head -3 | tail -1
fi
"$tools/fontspector" --version | head -1
