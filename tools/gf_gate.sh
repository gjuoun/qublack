#!/usr/bin/env bash
# Google Fonts gate for a QuBlack build (the plan helper in
# ~/.notebook/project/gjuoun/qublack/plan/scripts/gf-gate.sh mirrors this file).
# usage: [GF_ALLOW="check_id ..."] [GF_VENV=...] [FONTSPECTOR=...] \
#          gf-gate.sh <repo-root> <fonts-dir> [<out-dir>]
#
# Stages each family in a google/fonts-shaped ofl/<dirname>/ (TTFs, plus OFL.txt,
# METADATA.pb and DESCRIPTION.en_us.html when google-fonts/ofl/<slug>/ exists) so
# the repo- and metadata-level checks see the real layout, then runs fontspector
# 1.9.0 (-p googlefonts, the profile GF CI runs) and fontbakery 1.1.0
# (check-googlefonts, the profile JG-143 names). fontspector runs for both
# families first so its report exists while fontbakery is still working.
#
# GF_ALLOW lists check ids excluded from both runs — documented exceptions only
# (e.g. GF_ALLOW="file_size cjk_vertical_metrics family_name_compliance").
# Exit 0 only when neither tool reports a FAIL or FATAL.
set -uo pipefail

repo=${1:?usage: gf-gate.sh <repo-root> <fonts-dir>}
fonts=${2:?usage: gf-gate.sh <repo-root> <fonts-dir>}
out=${3:-/tmp/jun/gf-gate}
venv=${GF_VENV:-$repo/.venv-gf}
fontspector=${FONTSPECTOR:-$repo/.tools/fontspector}
allow=${GF_ALLOW:-}

# gflanguages ships pre-3.20 protobuf stubs; both toolchains import them.
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

mkdir -p "$out"
status=0
rm -rf "$out/stage"
skip=()
for id in $allow; do skip+=(-x "$id"); done

stage_family() {
  family=$1
  slug=qublack$(printf %s "$family" | tr '[:upper:]' '[:lower:]')
  stage="$out/stage/ofl/$slug"
  mkdir -p "$stage"
  # Statics (v1.x) and the variable faces (QuBlackMono[wght].ttf) share the same gate.
  shopt -s nullglob
  for face in "$fonts"/QuBlack$family-*.ttf "$fonts/QuBlack$family[wght].ttf"; do
    cp "$face" "$stage"/
  done
  shopt -u nullglob
  for extra in OFL.txt METADATA.pb DESCRIPTION.en_us.html; do
    if [ -f "$repo/google-fonts/ofl/$slug/$extra" ]; then
      cp "$repo/google-fonts/ofl/$slug/$extra" "$stage"/
    fi
  done
}

# fontspector first — it is the profile GF's CI runs and it finishes in ~30 s.
for family in Mono Sans; do
  stage_family "$family"
  files=()
  shopt -s nullglob
  for face in "$out/stage/ofl/qublack$(printf %s "$family" | tr '[:upper:]' '[:lower:]')"/QuBlack$family-*.ttf \
              "$out/stage/ofl/qublack$(printf %s "$family" | tr '[:upper:]' '[:lower:]')/QuBlack$family[wght].ttf"; do
    files+=("$face")
  done
  shopt -u nullglob
  "$fontspector" -p googlefonts --skip-network --ghmarkdown "$out/fontspector-$family.md" --json "$out/fontspector-$family.json" \
    ${skip[@]+"${skip[@]}"} "${files[@]}" > "$out/fontspector-$family.log" 2>&1 || status=1
  fs_fail=$(grep -oE 'FAIL: [0-9]+' "$out/fontspector-$family.log" | tail -1 | grep -oE '[0-9]+')
  fs_fatal=$(grep -oE 'FATAL: [0-9]+' "$out/fontspector-$family.log" | tail -1 | grep -oE '[0-9]+')
  fs_warn=$(grep -oE 'WARN: [0-9]+' "$out/fontspector-$family.log" | tail -1 | grep -oE '[0-9]+')
  echo "fontspector QuBlack $family: FAIL=${fs_fail:-?} FATAL=${fs_fatal:-?} WARN=${fs_warn:-?}"
done

# fontbakery is minutes on 57k-glyph faces; --skip-network keeps it from hanging.
for family in Mono Sans; do
  files=()
  shopt -s nullglob
  for face in "$out/stage/ofl/qublack$(printf %s "$family" | tr '[:upper:]' '[:lower:]')"/QuBlack$family-*.ttf \
              "$out/stage/ofl/qublack$(printf %s "$family" | tr '[:upper:]' '[:lower:]')/QuBlack$family[wght].ttf"; do
    files+=("$face")
  done
  shopt -u nullglob
  "$venv/bin/fontbakery" check-googlefonts --skip-network \
    ${skip[@]+"${skip[@]}"} "${files[@]}" > "$out/fontbakery-$family.log" 2>&1 || status=1
  fb_fail=$(grep -c -E '^    Result: (FAIL|FATAL)' "$out/fontbakery-$family.log" || true)
  fb_warn=$(grep -c '^    Result: WARN' "$out/fontbakery-$family.log" || true)
  echo "fontbakery  QuBlack $family: FAIL=$fb_fail WARN=$fb_warn"
done

echo "allow: ${allow:-none}"
echo "reports: $out/fontspector-*.md $out/fontbakery-*.log"
exit $status
