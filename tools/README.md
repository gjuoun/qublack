# tools

The build and verification toolchain behind the QuBlack release. Python 3.9+ with
`fonttools` and `brotli` (`python3 -m pip install fonttools brotli`).

| Script             | What it does                                                                                              |
| ------------------ | --------------------------------------------------------------------------------------------------------- |
| `fetch_cjk_vf.py`  | download the pinned CJK variable donor (`NotoSansSC-VF.ttf`) into `--sources`, verify size + SHA-256      |
| `build_qublack.py` | build one face: `--mode mono\|sans --style …` (Latin swap, emoji strip, names, then the mode's post step) |
| `build_all.py`     | build all eight faces into `fonts/` (`python3 tools/build_all.py`)                                        |
| `verify_family.py` | compare a build against `reference/baseline-v1.json` (metrics, never hashes)                              |
| `name_audit.py`    | strict gate: name table, OFL notice, derivation, reserved names, cmap, 2:1 grid                           |
| `cjk_weight.py`    | report/assert CJK weight ratios and whether Regular and Bold CJK share a point structure                  |
| `probe_metrics.py` | print the per-glyph measurements that decide whether a face is acceptable                                 |
| `cell_geometry.py` | running-text ink/advance comparison across faces                                                          |
| `metrics_json.py`  | emit the numbers the site prints, straight from the faces                                                 |
| `web_fonts.py`     | woff2 shards + `unicode-range` CSS for the site                                                           |
| `pack_release.py`  | deterministic release zip + `SHA256SUMS`                                                                  |
| `strip_emoji.py`   | manual repair: strip Emoji=Yes codepoints from a face (keeps `.bak-emoji`)                                |

`qublack_font.py` holds the shared loading/measuring/naming helpers.

Inputs are the upstream OFL sources (Sarasa Gothic / Sarasa Term 1.0.42, Recursive 1.085
Linear statics, and Noto Sans SC VF as the hanzi weight axis). `--sources` defaults to `~/code/gjuoun/lishu-mono/assets/work`; pass
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
