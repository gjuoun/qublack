# 黢黑 QuBlack

A bilingual typeface family built for code: **QuBlack Mono** holds a strict **2:1** grid (one
hanzi = two ASCII cells, measured at 2.000), **QuBlack Sans** is its proportional sibling for
documents, web and UI. Both carry Source Han Sans hanzi (via Sarasa Gothic) and Recursive Linear
Latin, so the whole family is redistributable under the SIL Open Font License 1.1.

Site: **https://qublack.qqntt.com/** — specimen, measurements and downloads.
Release: **[v1.0.4](https://github.com/gjuoun/qublack/releases/tag/v1.0.4)** · CI:
![CI](https://github.com/gjuoun/qublack/actions/workflows/ci.yml/badge.svg)

## Family

| Family       | Use                | upm  | Hanzi   | ASCII   |
| ------------ | ------------------ | ---- | ------- | ------- |
| QuBlack Mono | terminal, code     | 833  | 1.200em | 0.600em |
| QuBlack Sans | documents, web, UI | 1000 | 1.000em | 0.600em |

Four styles each: Regular, Italic, Bold, BoldItalic.

## Download

`v1.0.4` assets on the GitHub release page: eight TTFs plus `OFL.txt` and `README.txt`.
- **v1.0.4** — clean name tables (the zh-CN records now read 黢黑等宽 QuBlack Mono / 黢黑比例
  QuBlack Sans, no Sarasa version strings or empty records) and an OTS fix that lets Chrome load the
  TTFs directly.
- **v1.0.3** — the full 44-symbol census: every CJK-adjacent mark sits on Sarasa's ink ratios.
- **v1.0.2** — the bracket set harmonised.
- **v1.0.1** — the mono `@` swapped for Recursive's `at.alt` alternate.

### Formats

| Format    | Files                                    | Use it for                                                                                   |
| --------- | ---------------------------------------- | -------------------------------------------------------------------------------------------- |
| **TTF**   | `QuBlackMono-*.ttf`, `QuBlackSans-*.ttf` | system install — macOS `~/Library/Fonts`, Linux `~/.local/share/fonts`, Windows double-click |
| **TTC**   | `QuBlackMono.ttc`, `QuBlackSans.ttc`     | the smaller bundle: four faces per file, shared tables                                       |
| **WOFF2** | `QuBlack*-*.woff2`                       | `@font-face` self-hosting on the web — **WOFF2, not WOFF1**                                  |

No OTF: the outlines are `glyf`; a CFF conversion would only cost size and hinting.

## Build

```sh
bun install
python3 tools/build_all.py      # eight faces into fonts/ from the Sarasa + Recursive sources
bun run fonts:audit             # name table, OFL notice, cmap, metrics
bun run fonts:web               # woff2 shards + unicode-range CSS for the site
bun run check                   # lint, typecheck, tests, site build
```

## Licence

- Fonts and font derivatives: **SIL Open Font License 1.1** (see `LICENSE`).
- Site and tooling code: **MIT** (see `LICENSE-MIT`).
- Provenance and upstream licences: `NOTICE.md`.

## Credits

QuBlack is a derivative work, and it also borrows ideas. With thanks:

**Glyphs**
- [Sarasa Gothic](https://github.com/be5invis/Sarasa-Gothic) by Chen Qi's Sarasa contributors — the
  skeleton and CJK cells both families are built on (SIL OFL 1.1).
- [Source Han Sans](https://github.com/adobe-fonts/source-han-sans) by Adobe and Google — the hanzi
  ink Sarasa carries (SIL OFL 1.1).
- [Recursive](https://github.com/arrowtype/recursive) by ArrowType — every Latin outline, Mono and
  Sans (SIL OFL 1.1).

**Ideas and references**
- Sarasa's own Term/Mono split and its 2:1 alignment paradigm — why QuBlack Mono exists as a second
  family rather than another weight.
- The upm-833 optical trick (change `unitsPerEm`, leave every coordinate alone) that makes the mono
  cell read 1.200em against a 0.600em ASCII cell.
- Sarasa Term's symbol heights as the reference for the 44-symbol census
  (`tools/symbol_targets.py`).
- Recursive's `at.alt` alternate for the mono `@`.
- [commitmono.com](https://commitmono.com/) — the editable-specimen interaction this site's hero
  learns from.

No upstream Reserved Font Name is used; the family ships under new names with the OFL attribution
kept in name IDs 0 and 7.
