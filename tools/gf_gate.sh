#!/usr/bin/env bash
# Google Fonts gate for a Qu Black build.
# usage: [GF_ALLOW="check_id ..."] [GF_SKIP_BAKERY=1] [GF_VENV=...] [FONTSPECTOR=...] \
#          gf-gate.sh <repo-root> <fonts-dir> [<out-dir>]
#
# Stages each family in a google/fonts-shaped ofl/<dirname>/ (TTFs, plus OFL.txt,
# METADATA.pb and DESCRIPTION.en_us.html when google-fonts/ofl/<slug>/ exists) so
# the repo- and metadata-level checks see the real layout, then runs fontspector
# 1.9.0 (-p googlefonts, the profile GF CI runs) and fontbakery 1.1.0
# (check-googlefonts). fontspector runs for both families first so its report exists while
# fontbakery is still working.
#
# GF_ALLOW lists check ids excluded from both runs — documented exceptions only
# (e.g. GF_ALLOW="file_size cjk_vertical_metrics family_name_compliance").
#
# GF_SKIP_BAKERY=1 drops the fontbakery stage and says so per family. The CI runner uses it:
# fontbakery needs minutes per family on these 57k-glyph faces, and fontspector's googlefonts
# profile — the one Google Fonts' own CI runs — covers the submission surface.
#
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

# Faces of one family in a directory: the statics plus, when present, the variable face. The VF
# name carries a literal `[wght]`, so it is tested with -f instead of globbed — an escaped or
# quoted bracket pattern is not a pattern at all, and the literal path that the old version
# handed fontspector made the whole run error out instead of reporting a count.
collect() { # <dir> <family> -> FILES
  FILES=()
  shopt -s nullglob
  local found=("$1"/QuBlack"$2"-*.ttf)
  shopt -u nullglob
  local vf="$1/QuBlack$2[wght].ttf"
  [ -f "$vf" ] && found+=("$vf")
  local face
  for face in ${found[@]+"${found[@]}"}; do FILES+=("$face"); done
}

stage_family() {
  family=$1
  slug=qublack$(printf %s "$family" | tr '[:upper:]' '[:lower:]')
  stage="$out/stage/ofl/$slug"
  mkdir -p "$stage"
  collect "$fonts" "$family"
  if [ ${#FILES[@]} -eq 0 ]; then
    echo "FAIL  no Qu Black $family faces in $fonts"
    status=1
    return
  fi
  cp ${FILES[@]+"${FILES[@]}"} "$stage"/
  echo "stage  $slug: ${#FILES[@]} faces"
  for extra in OFL.txt METADATA.pb DESCRIPTION.en_us.html; do
    if [ -f "$repo/google-fonts/ofl/$slug/$extra" ]; then
      cp "$repo/google-fonts/ofl/$slug/$extra" "$stage"/
    fi
  done
}

# fontspector first — it is the profile GF's CI runs and it finishes in seconds.
for family in Mono Sans; do
  stage_family "$family"
  collect "$stage" "$family"   # gate the staged copy: the repo-level checks read its directory name
  [ ${#FILES[@]} -eq 0 ] && continue
  "$fontspector" -p googlefonts --skip-network --ghmarkdown "$out/fontspector-$family.md" --json "$out/fontspector-$family.json" \
    ${skip[@]+"${skip[@]}"} "${FILES[@]}" > "$out/fontspector-$family.log" 2>&1 || status=1
  fs_fail=$(grep -oE 'FAIL: [0-9]+' "$out/fontspector-$family.log" | tail -1 | grep -oE '[0-9]+')
  fs_fatal=$(grep -oE 'FATAL: [0-9]+' "$out/fontspector-$family.log" | tail -1 | grep -oE '[0-9]+')
  fs_warn=$(grep -oE 'WARN: [0-9]+' "$out/fontspector-$family.log" | tail -1 | grep -oE '[0-9]+')
  # A run that never produced a summary is red whatever its exit code says.
  if [ -z "${fs_fail:-}" ] || [ -z "${fs_fatal:-}" ]; then
    status=1
    echo "fontspector Qu Black $family: no summary in $out/fontspector-$family.log"
  fi
  echo "fontspector Qu Black $family: FAIL=${fs_fail:-?} FATAL=${fs_fatal:-?} WARN=${fs_warn:-?}"
  if [ "${fs_fail:-0}" != 0 ] || [ "${fs_fatal:-0}" != 0 ]; then status=1; fi
done

# fontbakery is minutes on 57k-glyph faces; --skip-network keeps it from hanging.
for family in Mono Sans; do
  if [ -n "${GF_SKIP_BAKERY:-}" ]; then
    echo "fontbakery  Qu Black $family: skipped (GF_SKIP_BAKERY=1)"
    continue
  fi
  slug=qublack$(printf %s "$family" | tr '[:upper:]' '[:lower:]')
  collect "$out/stage/ofl/$slug" "$family"
  if [ ${#FILES[@]} -eq 0 ]; then
    status=1
    continue
  fi
  "$venv/bin/fontbakery" check-googlefonts --skip-network \
    ${skip[@]+"${skip[@]}"} "${FILES[@]}" > "$out/fontbakery-$family.log" 2>&1 || status=1
  fb_fail=$(grep -c -E '^    Result: (FAIL|FATAL)' "$out/fontbakery-$family.log" || true)
  fb_warn=$(grep -c '^    Result: WARN' "$out/fontbakery-$family.log" || true)
  echo "fontbakery  Qu Black $family: FAIL=$fb_fail WARN=$fb_warn"
done

echo "allow: ${allow:-none}"
echo "reports: $out/fontspector-*.md $out/fontbakery-*.log"
exit $status
