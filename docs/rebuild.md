# Rebuilding Qu Black

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
| Latin weight axis     | `Recursive_VF_1.085.ttf`                            | `python3 tools/fetch_recursive_vf.py` — pinned Recursive VF (OFL 1.1)       |
| Hanzi weight axis     | `NotoSansSC-VF.ttf`                                 | `python3 tools/fetch_cjk_vf.py` — pinned Noto Sans SC VF (OFL 1.1)          |
| Emoji table           | `assets/emoji-data.txt`                             | vendored from the Unicode character database                                |

The toolchain needs `skia-pathops` next to `fonttools` (`requirements.txt`): the Latin instance is
reconciled to the static release with outline booleans, and the VF ink gate compares filled areas.

`--sources` defaults to `sources/upstream` (override with `QUBLACK_SOURCES`); any directory with the layout in
`tools/README.md` works. The one input that is scripted rather than hand-unpacked is the hanzi
weight axis: `python3 tools/fetch_cjk_vf.py` downloads `NotoSansSC-VF.ttf` from a pinned google/fonts
commit into that directory and verifies its SHA-256. Every face instances it (400 for Regular and
Italic, 700 for Bold and BoldItalic) and takes its hanzi outlines from that instance, which is what
makes Regular and Bold interpolatable; glyphs the VF lacks keep the Sarasa outline. Advances are
not copied from the donor, so grid metrics never depend on it.

## 2. Build the eight faces

Font binaries are never committed: `fonts/` is fully git-ignored, so a fresh clone must run the
build before any font gate. The release zip is the only distribution channel.

```sh
bash sources/build.sh                        # ~8 min: pinned sources/ -> fonts/ttf/
python3 tools/verify_family.py fonts/ttf/          # metrics against reference/baseline-v2.json
python3 tools/verify_family.py fonts/ttf/ --against reference/baseline-v1.json --grid-only
python3 tools/cjk_weight.py --check fonts/ttf/     # CJK weight ratios + Regular/Bold interpolability
python3 tools/name_audit.py --strict fonts/ttf/    # name table, OFL notice, cmap, 2:1 grid
bun run tools/font-probe.ts fonts/ttf/      # Chrome OTS load + canvas render, 8/8
```

The `--latin-vf` path does not draw the raw VF instances: `tools/latin_masters.py` reconciles every
ASCII slot against the matching ArrowType static first, because the statics bake the donor's feature
substitutions (`l.mono`, `f.mono`, `g.mono`, `i.mono`, `r.mono`; `l.sans` and `zero.sans_pnum` for the
proportional face). Without that step the variable faces render thin strokes 10-30% lighter than the
statics at small sizes. The eight static faces keep the static donors and are untouched.

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
GF_ALLOW="file_size has_license cjk_vertical_metrics" \
  bash tools/gf_gate.sh . fonts/ttf
```

The gate stages each family in an `ofl/<dirname>/` layout and runs fontspector's googlefonts
profile (the one Google Fonts' CI uses) plus fontbakery's `check-googlefonts`. `family_name_compliance`
passes since the family renamed to the two-word "Qu Black" form. Three checks are waived, each with
a reason that goes into the submission:
- `file_size` — CJK families exceed the 9 MB limit; Noto Sans SC is 17.7 MB in google/fonts.
- `has_license` — fontspector runs on files and cannot see the staged `OFL.txt`; the license ships
  in the release zip and in the google/fonts PR itself.
- `cjk_vertical_metrics` — GF wants a 1.15 em line box; Qu Black's 1.25 em line height is a design
  decision. Everything else in that check (BASE, win metrics, hhea/typo agreement, vmtx/vhea) is
  satisfied, so the waiver covers the two typo ascender/descender comparisons only.
  On the variable faces `googlefonts/font_names` is additionally waived: the `VF` marker in the
  PostScript name (`QuBlackMonoVF-Regular`) deliberately differs from family+style so the VF and the
  static Regular never collide in font managers.

`verify_family.py` compares metrics, never hashes: a rebuild differs in glyph order and name
records. `reference/shipped-v1.json` records the 2026-10-21 build that shipped as JunHei;
`reference/DRIFT.md` explains the two mono italics whose Latin ink differs by ~5%.

`baseline-v1.json` is the v1.0.4 build and stays the **grid** reference (`--grid-only`: upm,
advances, line height, glyph count, codepoint count — none of which a re-weight may move).
`baseline-v2.json` is the ink reference for the v1.1.0 VF-master build and
`baseline-v3.json` for v1.2.0 (identical ink: the statics keep the same donors). Re-record one with
`verify_family.py fonts/ttf/ --record reference/baseline-v3.json` only when an ink delta is expected and
reviewed. The weight and interpolability assertions, and the hanzi boundary the donor does not
cover, are described in `reference/CJK.md`.

## 2c. Build the variable faces

```sh
bun run fonts:vf                            # ~4 min: two masters per family, then the merge
python3 tools/vf_audit.py --check fonts/vf  # fvar/STAT/axis/glyph surface
bash tools/vf_gate.sh .                     # axis ends: grid, 44-symbol census, at.alt
bun run tools/font-probe.ts fonts/vf --vf
```

Output is `fonts/vf/QuBlackMono[wght].ttf` and `QuBlackSans[wght].ttf` (about 22 MB each), also
git-ignored. `reference/VF.md` explains the two-master model, the frozen glyphs that cannot
interpolate, the BASE exclusion and the sans layout fallback.

## 4. Package the release

```sh
python3 tools/pack_release.py --tag v1.0.4
# dist/QuBlack-family-1.0.4.zip, dist/SHA256SUMS
```

The zip is deterministic (sorted entries, fixed timestamps).

## 5. Publish from CI

Everything above also runs as one [release pipeline](../.github/workflows/release-pipeline.yml)
dispatch on an ubuntu runner: build the ten faces from the committed sources, gate them, pack,
create the release with its fifteen assets, then ask the `sites` repository to deploy.

| Input     | Meaning                                                                        |
| --------- | ------------------------------------------------------------------------------ |
| `version` | release version without the `v`; must equal `package.json` before a real run   |
| `notes`   | release body, markdown                                                         |
| `dry_run` | build, gate and pack for real, publish a **draft** release, print the dispatch |

The gates are `bun run fonts:gate` (`tools/ci-gate.sh`), the same twelve checks run by hand
below, and any red gate stops the run before a release exists. `fontbakery` is skipped there:
it needs minutes per family on these 57k-glyph faces, and fontspector's googlefonts profile —
the one Google Fonts' CI runs — is the submission surface. The waiver set is
`file_size has_license cjk_vertical_metrics` (reasons in §2b) plus, for the variable faces
only, `font_names`, because their PostScript name carries the `VF` marker on purpose; the
statics are gated without that waiver, and `name_audit --strict` pins their name ids anyway.

A dry run is honest about what it cannot prove: a draft release is not the latest published
release, so the site would still build from the previous one — that is why the dispatch is
printed and not sent.

The dispatch needs a fine-grained token with **Actions: read and write** on `gjuoun/sites`,
stored as the repository secret `SITES_DISPATCH_TOKEN`. Without it the run stays green up to
the deploy step and warns instead of failing: the release is already out, the deploy is not.

Locally the manual flow still works: `gh release create v1.0.4 dist/*`.

## Site

The specimen site lives in the `sites` monorepo (`apps/qublack`); its deploy fetches this
repo's release zip and cuts the web shards there. This repo is fonts-only.
