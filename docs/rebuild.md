# Rebuilding QuBlack

Everything on https://qublack.qqntt.com/ and every asset in the release comes from the two scripts
below plus the upstream OFL sources. No step needs a network connection once the sources are
unpacked.

## 1. Inputs

| Layer                 | File                                                | Where                                                                       |
| --------------------- | --------------------------------------------------- | --------------------------------------------------------------------------- |
| Hanzi skeleton (mono) | `SarasaTermSC-{Regular,Italic,Bold,BoldItalic}.ttf` | Sarasa Gothic 1.0.42, `SarasaTermSC-TTF-1.0.42.7z`                          |
| Hanzi skeleton (sans) | `SarasaGothicSC-{…}.ttf`                            | Sarasa Gothic 1.0.42, `SarasaGothicSC-TTF-1.0.42.7z`                        |
| Latin (mono)          | `RecursiveMonoLnrSt-{…}.ttf`                        | `ArrowType-Recursive-1.085.zip` → `Recursive_Desktop/separate_statics/TTF/` |
| Latin (sans)          | `RecursiveSansLnrSt-{…}.ttf`                        | same zip                                                                    |
| Hanzi weight axis     | `NotoSansSC-VF.ttf`                                 | `python3 tools/fetch_cjk_vf.py` — pinned Noto Sans SC VF (OFL 1.1)          |
| Emoji table           | `assets/emoji-data.txt`                             | vendored from the Unicode character database                                |

`--sources` defaults to `~/code/gjuoun/lishu-mono/assets/work`; any directory with the layout in
`tools/README.md` works. The one input that is scripted rather than hand-unpacked is the hanzi
weight axis: `python3 tools/fetch_cjk_vf.py` downloads `NotoSansSC-VF.ttf` from a pinned google/fonts
commit into that directory and verifies its SHA-256. Every face instances it (400 for Regular and
Italic, 700 for Bold and BoldItalic) and takes its hanzi outlines from that instance, which is what
makes Regular and Bold interpolatable; glyphs the VF lacks keep the Sarasa outline. Advances are
not copied from the donor, so grid metrics never depend on it.

## 2. Build the eight faces

```sh
bash sources/build.sh                        # ~8 min: pinned sources/ -> fonts/ttf/
python3 tools/verify_family.py fonts/ttf/          # metrics against reference/baseline-v2.json
python3 tools/verify_family.py fonts/ttf/ --against reference/baseline-v1.json --grid-only
python3 tools/cjk_weight.py --check fonts/ttf/     # CJK weight ratios + Regular/Bold interpolability
python3 tools/name_audit.py --strict fonts/ttf/    # name table, OFL notice, cmap, 2:1 grid
bun run site/scripts/font-probe.ts fonts/ttf/      # Chrome OTS load + canvas render, 8/8
```

Each face is one `build_qublack.py` run. The mono pipeline applies the upm-833 trick after the
Latin swap, so `汉` = 1.200em and ASCII = 0.600em with the glyph coordinates untouched. The sans
pipeline copies `0x2500–0x259F` from the Term skeleton, so box drawing stays half-width, and
takes Term's full repertoire (Sarasa Gothic is ~4,900 codepoints narrower, mostly combining
marks). Both families then get the Google Fonts CJK surface: BASE, vmtx/vhea, win metrics that
agree across the family, GDEF mark classes and one appended MarkBasePos lookup for the marks the
donors left unattached.

## 2b. Google Fonts gate

```sh
bash tools/gf_setup.sh        # .venv-gf (gftools 0.10.4, fontbakery 1.1.0) + fontspector 1.9.0
GF_ALLOW="file_size family_name_compliance cjk_vertical_metrics" \
  bash tools/gf_gate.sh . fonts/ttf
```

The gate stages each family in an `ofl/<dirname>/` layout and runs fontspector's googlefonts
profile (the one Google Fonts' CI uses) plus fontbakery's `check-googlefonts`. Three checks are
waived, each with a reason that goes into the submission:
- `file_size` — CJK families exceed the 9 MB limit; Noto Sans SC is 17.7 MB in google/fonts.
- `family_name_compliance` — "QuBlack" is CamelCase; the submission requests an exception rather
  than renaming the family.
- `cjk_vertical_metrics` — GF wants a 1.15 em line box; QuBlack's 1.25 em line height is a design
  decision. Everything else in that check (BASE, win metrics, hhea/typo agreement, vmtx/vhea) is
  satisfied, so the waiver covers the two typo ascender/descender comparisons only.

`verify_family.py` compares metrics, never hashes: a rebuild differs in glyph order and name
records. `reference/shipped-v1.json` records the 2026-10-21 build that shipped as JunHei;
`reference/DRIFT.md` explains the two mono italics whose Latin ink differs by ~5%.

`baseline-v1.json` is the v1.0.4 build and stays the **grid** reference (`--grid-only`: upm,
advances, line height, glyph count, codepoint count — none of which a re-weight may move).
`baseline-v2.json` is the ink reference for the v1.1.0 VF-master build; re-record it with
`verify_family.py fonts/ttf/ --record reference/baseline-v2.json` only when an ink delta is expected and
reviewed. The weight and interpolability assertions, and the hanzi boundary the donor does not
cover, are described in `reference/CJK.md`.

## 3. Cut the web fonts

```sh
python3 tools/web_fonts.py --out site/public/fonts --css site/src/styles/qublack-fonts.css
python3 tools/web_fonts.py --check        # regenerate to /tmp and byte-compare
```

564 shards over eight faces (about 52 MB on disk, 46 KB for the first shard). Shard 0 holds every
codepoint the site's own source uses, so a first paint needs one small shard per face; the rest
follows the GB2312 level-1 order and then codepoint order. `head.modified`/`created` are pinned so
the output is byte-reproducible.

The shards are **not committed**. Cloudflare Pages downloads the release zip, cuts them, and
deploys the result; locally the same command writes into the git-ignored `site/public/fonts/ttf/`.

## 4. Package the release

```sh
python3 tools/pack_release.py --tag v1.0.4
# dist/QuBlack-family-1.0.4.zip, dist/SHA256SUMS
```

The zip is deterministic (sorted entries, fixed timestamps). Publish with
`gh release create v1.0.4 dist/QuBlack-family-1.0.4.zip dist/SHA256SUMS dist/README-release.txt`.

## 5. Site

```sh
bun install
bun run fonts:web        # once, after the faces exist
bun run site:dev         # http://localhost:4321
bun run check            # lint, typecheck, tests, site build
bun run site/scripts/smoke.ts http://localhost:4321
```

The smoke script drives the locally installed Chrome through puppeteer-core and asserts the
interactions (editable hero, B/M keys, arrow navigation), the content counts, the font payload
budget and CLS.
