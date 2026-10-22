# 黢黑 QuBlack

A bilingual typeface family built for code: **QuBlack Mono** holds a strict **2:1** grid (one
hanzi = two ASCII cells, measured at 2.000), **QuBlack Sans** is its proportional sibling for
documents, web and UI. Both carry Source Han Sans hanzi (via Sarasa Gothic) and Recursive Linear
Latin, so the whole family is redistributable under the SIL Open Font License 1.1.

Site: **https://qublack.qqntt.com/** — specimen, measurements and downloads.
Release: **[v1.0.1](https://github.com/gjuoun/qublack/releases/tag/v1.0.1)** · CI:
![CI](https://github.com/gjuoun/qublack/actions/workflows/ci.yml/badge.svg)

## Family

| Family       | Use                | upm  | Hanzi   | ASCII   |
| ------------ | ------------------ | ---- | ------- | ------- |
| QuBlack Mono | terminal, code     | 833  | 1.200em | 0.600em |
| QuBlack Sans | documents, web, UI | 1000 | 1.000em | 0.600em |

Four styles each: Regular, Italic, Bold, BoldItalic.

## Download

`v1.0.1` assets on the GitHub release page: eight TTFs plus `OFL.txt` and `README.txt`.
v1.0.1 swaps the mono `@` for Recursive's `at.alt` alternate; everything else is unchanged.

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
