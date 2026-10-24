# tools

The build and verification toolchain behind the QuBlack release. Python 3.9+ with
`fonttools` and `brotli` (`python3 -m pip install fonttools brotli`).

| Script                  | What it does                                                                                                                                                         |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fetch_cjk_vf.py`       | download the pinned CJK variable donor (`NotoSansSC-VF.ttf`) into `--sources`, verify size + SHA-256                                                                 |
| `fetch_recursive_vf.py` | download the pinned Latin variable donor (`Recursive_VF_1.085.ttf`), verify size + SHA-256                                                                           |
| `build_qublack.py`      | build one face: `--mode mono\|sans --style …` (Latin swap, emoji strip, names, then the mode's post step)                                                            |
| `build_all.py`          | build all eight faces into `fonts/ttf/` (`python3 tools/build_all.py`)                                                                                               |
| `verify_family.py`      | compare a build against `reference/baseline-v1.json` (metrics, never hashes)                                                                                         |
| `name_audit.py`         | strict gate: name table, OFL notice, derivation, reserved names, cmap, 2:1 grid                                                                                      |
| `cjk_weight.py`         | report/assert CJK weight ratios and whether Regular and Bold CJK share a point structure                                                                             |
| `latin_masters.py`      | instance the Recursive VF per style (`MONO`/`CASL`/`CRSV`/`slnt` pinned), reconcile to the static release, cache under ~/.cache/qublack (`--check` reports the pick) |
| `vf_compat.py`          | compare two masters glyph by glyph: ascii / noto-covered / freeze, the tail a weight axis cannot interpolate                                                         |
| `vf_masters.py`         | freeze the non-interpolatable glyphs at the wght 400 outline so varLib can merge                                                                                     |
| `build_vf.py`           | build `fonts/vf/QuBlack{Mono,Sans}[wght].ttf` from the two masters (`bun run fonts:vf`)                                                                              |
| `vf_tables.py`          | name table, fvar and STAT for a variable face                                                                                                                        |
| `vf_audit.py`           | assert the axis, instances, STAT, HVAR and glyph surface of a built VF                                                                                               |
| `probe_metrics.py`      | print the per-glyph measurements that decide whether a face is acceptable                                                                                            |
| `cell_geometry.py`      | running-text ink/advance comparison across faces                                                                                                                     |
| `metrics_json.py`       | emit the numbers the site prints, straight from the faces                                                                                                            |
| `web_fonts.py`          | woff2 shards + `unicode-range` CSS for the site                                                                                                                      |
| `pack_release.py`       | deterministic release zip + `SHA256SUMS`                                                                                                                             |
| `strip_emoji.py`        | manual repair: strip Emoji=Yes codepoints from a face (keeps `.bak-emoji`)                                                                                           |

`qublack_font.py` holds the shared loading/measuring/naming helpers.

The Latin instance is not the raw VF drawing: ArrowType's static releases bake the donor's own
feature substitutions, so `latin_masters.py` rewrites each ASCII slot with whichever of the default
glyph and its `name.*` alternates has the same ink as the static of that weight (mono:
`f.mono g.mono i.mono l.mono r.mono`; sans: `l.sans zero.sans_pnum`). The pick is proven per glyph
by ink area and the build aborts above 2.5% drift; `python3 tools/latin_masters.py
sources/upstream/Recursive_VF_1.085.ttf --mode mono --style Regular --check` prints it.

Inputs are the upstream OFL sources (Sarasa Gothic / Sarasa Term 1.0.42, Recursive 1.085
Linear statics, the Recursive VF as the Latin weight axis, and Noto Sans SC VF as the hanzi weight
axis). `--sources` defaults to `sources/upstream` (`QUBLACK_SOURCES` overrides it); pass
`--sources <dir>` to point at your own copy. The layout it expects:

```
<SarasaTermSC|SarasaGothicSC>-{Regular,Italic,Bold,BoldItalic}.ttf
NotoSansSC-VF.ttf                       # python3 tools/fetch_cjk_vf.py runs this one in
rec_mono/RecursiveMonoLnrSt-{…}.ttf
ArrowType-Recursive-1.085/Recursive_Desktop/separate_statics/TTF/RecursiveSansLnrSt-{…}.ttf
```

Every face takes its hanzi outlines from `NotoSansSC-VF.ttf`, instanced at `wght` 400 for
Regular/Italic and 700 for Bold/BoldItalic, so the two weights share a point structure and can be
interpolated later. Glyphs the VF does not carry keep the Sarasa outline. Advances are never
touched, so the 2:1 grid and the upm-833 move are independent of the donor.
