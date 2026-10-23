#!/usr/bin/env bash
# Install the pinned Google Fonts toolchain used by the GF readiness gate.
#
#   .venv-gf/        gftools + fontbakery + the glyphsets/shaperglot data they need
#   .tools/fontspector  pinned release binary (the profile GF's CI runs)
#
# Re-running is cheap: the venv is reused and the tarball is only downloaded when
# the pinned sha256 does not match.
set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
venv="$repo/.venv-gf"
tools="$repo/.tools"
version=1.9.0
asset="fontspector-${version}-aarch64-apple-darwin.tar.gz"
sha256=0d34d5f85ac7a2efe57157c31f454e56a759edf888879b53af50b76bb1d6b617
url="https://github.com/fonttools/fontspector/releases/download/fontspector-v${version}/${asset}"

# gflanguages ships pre-3.20 protobuf stubs; gftools and fontbakery both import
# them, and fail with "Descriptors cannot be created directly" without this.
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

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

mkdir -p "$tools"
if [ ! -x "$tools/fontspector" ] || [ "$(shasum -a 256 "$tools/$asset" 2>/dev/null | cut -d' ' -f1)" != "$sha256" ]; then
  curl -fsSL -o "$tools/$asset" "$url"
  echo "$sha256  $tools/$asset" | shasum -a 256 -c -
  tar xzf "$tools/$asset" -C "$tools"
  mv "$tools/fontspector-${version}-aarch64-apple-darwin/fontspector" "$tools/fontspector"
  rm -rf "$tools/fontspector-${version}-aarch64-apple-darwin" "$tools/$asset"
  chmod +x "$tools/fontspector"
fi

"$venv/bin/fontbakery" --version
"$venv/bin/gftools" --version 2>&1 | head -3 | tail -1
"$tools/fontspector" --version | head -1
