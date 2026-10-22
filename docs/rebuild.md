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
| Emoji table           | `assets/emoji-data.txt`                             | vendored from the Unicode character database                                |

`--sources` defaults to `~/code/gjuoun/lishu-mono/assets/work`; any directory with the layout in
`tools/README.md` works.

## 2. Build the eight faces

```sh
python3 tools/build_all.py --out fonts
python3 tools/verify_family.py fonts/          # metrics against reference/baseline-v1.json
python3 tools/name_audit.py --strict fonts/    # name table, OFL notice, cmap, 2:1 grid
```

Each face is one `build_qublack.py` run (~10 s). The mono pipeline applies the upm-833 trick after
the Latin swap, so `汉` = 1.200em and ASCII = 0.600em with the glyph coordinates untouched. The
sans pipeline copies `0x2500–0x259F` from the Term skeleton, so box drawing stays half-width.

`verify_family.py` compares metrics, never hashes: a rebuild differs in glyph order and name
records. `reference/shipped-v1.json` records the 2026-10-21 build that shipped as JunHei;
`reference/DRIFT.md` explains the two mono italics whose Latin ink differs by ~5%.

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
deploys the result; locally the same command writes into the git-ignored `site/public/fonts/`.

## 4. Package the release

```sh
python3 tools/pack_release.py --tag v1.0.1
# dist/QuBlack-family-1.0.1.zip, dist/SHA256SUMS
```

The zip is deterministic (sorted entries, fixed timestamps). Publish with
`gh release create v1.0.1 dist/QuBlack-family-1.0.1.zip dist/SHA256SUMS dist/README-release.txt`.

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
