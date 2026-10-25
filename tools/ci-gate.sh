#!/usr/bin/env bash
# Every Qu Black gate, in one command, for a build already on disk.
#
#   bash tools/ci-gate.sh [fonts-dir] [vf-dir]     # defaults: fonts/ttf fonts/vf
#   bun run fonts:gate
#
# One line per gate; the full output of each lands in /tmp/jun/qublack-ci-gate/. Exit 0 only
# when every gate is green — the release pipeline runs exactly this script on the runner.
#
# fontspector and Chrome are hard requirements: if either is missing the run is red. Set
# GF_SKIP=1 to downgrade the fontspector gates to a named skip (never set on the runner), and
# CHROME_PATH to point the probe at a browser other than the macOS install.
set -uo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
ttf=${1:-$repo/fonts/ttf}
vfd=${2:-$repo/fonts/vf}
logs=${LOGS:-/tmp/jun/qublack-ci-gate}
cd "$repo" || exit 2
mkdir -p "$logs"

# The waiver set, documented in docs/rebuild.md: a CJK family exceeds the 9 MB file-size limit,
# fontspector checks files and cannot see the staged OFL.txt, the 1.25 em line height is a design
# decision, and the VF PostScript name carries a VF marker on purpose so it cannot collide with
# the static Regular. The statics run without the font_names waiver — their name table is pinned
# id by id by name_audit --strict, and fontspector should say so itself.
STATIC_ALLOW="file_size has_license cjk_vertical_metrics"
VF_ALLOW="$STATIC_ALLOW font_names"

pass=0
fail=0
skipped=0

gate() { # <name> <command...>
  name=$1 ; shift
  if "$@" > "$logs/$name.log" 2>&1; then
    printf 'GATE %-10s PASS\n' "$name"
    pass=$((pass + 1))
  else
    printf 'GATE %-10s FAIL\n' "$name"
    grep -E '^(FAIL|[0-9]+/[0-9]+.*fail|error)' "$logs/$name.log" | head -3 | sed 's/^/     /'
    tail -2 "$logs/$name.log" | sed 's/^/     /'
    fail=$((fail + 1))
  fi
}

skip() { # <name> <reason>
  printf 'GATE %-10s SKIP (%s)\n' "$1" "$2"
  skipped=$((skipped + 1))
}

if [ ! -d "$ttf" ] || [ -z "$(ls "$ttf"/*.ttf 2>/dev/null)" ]; then
  echo "no faces in $ttf — build them first (bash sources/build.sh && bun run fonts:vf)" >&2
  exit 2
fi

# 1-2. Metrics and grid against the recorded baselines.
gate metrics   python3 tools/verify_family.py "$ttf"
gate grid      python3 tools/verify_family.py "$ttf" --against reference/baseline-v1.json --grid-only

# 3-4. CJK weight interpolability, then the name/OFL/cmap surface.
gate weight    python3 tools/cjk_weight.py --check "$ttf"
gate names     python3 tools/name_audit.py --strict "$ttf"

# 5-6. The variable faces: table legality, then the same family at both axis ends.
gate vf        python3 tools/vf_audit.py --check "$vfd"
gate vfgate    bash tools/vf_gate.sh . "$vfd"

# 7-8. Symbol harmonisation and the @ source outline.
gate symbols   python3 tools/symbol_audit.py --check --fonts "$ttf" --donors sources/upstream
gate at        python3 tools/check_at.py --fonts "$ttf"

# 9-10. fontspector's googlefonts profile, once for the statics and once for the VF.
fontspector=$repo/.tools/fontspector
if [ -x "$fontspector" ]; then
  gate gf-statics env GF_SKIP_BAKERY=1 GF_ALLOW="$STATIC_ALLOW" bash tools/gf_gate.sh . "$ttf" "$logs/gf-statics"
  if [ -n "$(ls "$vfd"/*.ttf 2>/dev/null)" ]; then
    gate gf-vf      env GF_SKIP_BAKERY=1 GF_ALLOW="$VF_ALLOW" bash tools/gf_gate.sh . "$vfd" "$logs/gf-vf"
  else
    skip gf-vf "no variable faces in $vfd"
  fi
elif [ -n "${GF_SKIP:-}" ]; then
  skip gf-statics "GF_SKIP=1"
  skip gf-vf "GF_SKIP=1"
else
  echo 'GATE gf        FAIL (no .tools/fontspector — run bash tools/gf_setup.sh --fontspector-only)'
  fail=$((fail + 2))
fi

# 11-12. Chrome's OTS parser has to accept every face and draw something the fallback does not.
if [ -z "${CHROME_PATH:-}" ] && [ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
  CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
fi
if [ -z "${CHROME_PATH:-}" ] || [ ! -x "${CHROME_PATH:-/nonexistent}" ]; then
  echo 'GATE probe    FAIL (no Chrome: set CHROME_PATH)'
  fail=$((fail + 1))
else
  export CHROME_PATH
  gate probe     bun run tools/font-probe.ts "$ttf"
fi
if [ -n "$(ls "$vfd"/*.ttf 2>/dev/null)" ] && [ -n "${CHROME_PATH:-}" ] && [ -x "${CHROME_PATH:-/nonexistent}" ]; then
  gate probe-vf  bun run tools/font-probe.ts "$vfd" --vf
fi

total=$((pass + fail + skipped))
if [ "$fail" -eq 0 ] && [ "$skipped" -eq 0 ]; then
  printf 'PASS ci-gate: %d/%d gates green\n' "$pass" "$total"
  exit 0
fi
printf 'FAIL ci-gate: %d green, %d red, %d skipped of %d (logs: %s)\n' "$pass" "$fail" "$skipped" "$total" "$logs"
exit 1
