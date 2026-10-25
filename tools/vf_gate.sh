#!/usr/bin/env bash
# tools/vf_gate.sh [repo] [vf-dir] — prove a wght-axis VF is the same family as the shipped statics.
#
# 1. Instances every VF at wght 400 and 700 into /tmp/jun/qublack-vf/axis/{400,700} under the
#    static face names, so the existing guards run unmodified.
# 2. Grid invariants: verify_family --grid-only against reference/baseline-v1.json (upm,
#    advances, line height, glyph count) for both axis ends.
# 3. Symbol harmonisation + at.alt at both axis ends (44-symbol census, 4/4 at.alt).
# 4. Axis legality: fvar wght 400..700, default 400, two named instances, STAT present.
#
# usage: bash tools/vf_gate.sh [repo] [vf-dir]        # defaults: . fonts/vf
set -uo pipefail

repo="${1:-.}"
vfd="${2:-fonts/vf}"
work=/tmp/jun/qublack-vf/axis
fail=0
pass() { printf 'PASS  %s\n' "$*"; }
bad()  { printf 'FAIL  %s\n' "$*"; fail=1; }

cd "$repo" || exit 2
rm -rf "$work"; mkdir -p "$work/400" "$work/700"

python3 - "$vfd" "$work" <<'PY'
import sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

vfd, work = Path(sys.argv[1]), Path(sys.argv[2])
styles = {400: "Regular", 700: "Bold"}
seen = 0
for path in sorted(vfd.glob("*[[]wght[]].ttf")):
    slug = path.stem.split("[")[0]
    for weight, style in styles.items():
        font = TTFont(str(path))
        instantiateVariableFont(font, {"wght": weight}, inplace=True, updateFontNames=False)
        out = work / str(weight) / f"{slug}-{style}.ttf"
        font.save(str(out))
        print(f"instanced {path.name} @{weight} -> {out}")
        seen += 1
print(f"instanced {seen} faces")
PY
[ $? -eq 0 ] || bad "instancing the VF axis ends"

python3 - "$vfd" <<'PY' || exit 1
import sys
from pathlib import Path
from fontTools.ttLib import TTFont

failures = 0
for path in sorted(Path(sys.argv[1]).glob("*[[]wght[]].ttf")):
    font = TTFont(str(path))
    fvar = font["fvar"]
    axes = {axis.axisTag: axis for axis in fvar.axes}
    problems = []
    if set(axes) != {"wght"}:
        problems.append(f"axes {sorted(axes)} != ['wght']")
    else:
        axis = axes["wght"]
        if (axis.minValue, axis.maxValue, axis.defaultValue) != (400, 700, 400):
            problems.append(f"range {axis.minValue}..{axis.maxValue} default {axis.defaultValue}")
    names = {font["name"].getDebugName(inst.subfamilyNameID) for inst in fvar.instances}
    if not {"Regular", "Bold"} <= names:
        problems.append(f"named instances {sorted(names)}")
    if "STAT" not in font:
        problems.append("no STAT")
    if problems:
        print("FAIL  " + path.name + ": " + "; ".join(problems))
        failures += 1
    else:
        print(f"PASS  {path.name}: fvar wght 400..700 default 400, instances Regular/Bold, STAT present")
print(f"axis legality: {len(list(Path(sys.argv[1]).glob('*[[]wght[]].ttf'))) - failures}/"
      f"{len(list(Path(sys.argv[1]).glob('*[[]wght[]].ttf')))} VF faces")
sys.exit(1 if failures else 0)
PY
[ $? -eq 0 ] || bad "VF axis table legality"

python3 tools/verify_family.py "$work/400" "$work/700" \
  --against reference/baseline-v1.json --grid-only || bad "grid invariants at the axis ends"

python3 tools/symbol_audit.py --check --fonts "$work/400" --donors sources/upstream --style Regular \
  || bad "44-symbol census at wght 400"
python3 tools/symbol_audit.py --check --fonts "$work/700" --donors sources/upstream --style Bold \
  || bad "44-symbol census at wght 700"

python3 tools/check_at.py --fonts "$work/400" --style Regular \
  --latin-vf sources/upstream/Recursive_VF_1.085.ttf || bad "at.alt at wght 400"
python3 tools/check_at.py --fonts "$work/700" --style Bold \
  --latin-vf sources/upstream/Recursive_VF_1.085.ttf || bad "at.alt at wght 700"

[ "$fail" -eq 0 ] && echo "PASS vf-gate: axis ends, grid, census and at.alt all green"
[ "$fail" -eq 0 ] || echo "FAIL vf-gate: see the FAIL lines above"
exit "$fail"
