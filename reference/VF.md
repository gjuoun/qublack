# Variable faces (v1.2.0)

v1.2.0 adds two weight-axis variable fonts to the eight static faces. They are **build outputs, not
committed files**: `fonts/` is fully git-ignored, the binaries are produced locally by
`bun run fonts:vf`, and they ship inside the release zip only.

| family          | file                             | name ID 1       | PostScript              | glyphs | size         |
| --------------- | -------------------------------- | --------------- | ----------------------- | ------ | ------------ |
| QuBlack Mono VF | `fonts/vf/QuBlackMono[wght].ttf` | QuBlack Mono VF | `QuBlackMonoVF-Regular` | 57,129 | 22,573,948 B |
| QuBlack Sans VF | `fonts/vf/QuBlackSans[wght].ttf` | QuBlack Sans VF | `QuBlackSansVF-Regular` | 53,716 | 22,166,280 B |

The family string carries the `VF` marker on purpose: the static `QuBlack Mono` already owns
`QuBlackMono-Regular`, and two installed fonts with one PostScript name collide in every font
manager. The file name keeps the Google Fonts convention.

## Masters

Two masters per family, both built by the normal pipeline (`build_qublack.build`), so the VF and
the statics cannot drift:

| layer | wght 400                                                                             | wght 700          |
| ----- | ------------------------------------------------------------------------------------ | ----------------- |
| CJK   | `NotoSansSC-VF.ttf` instanced at 400                                                 | same donor at 700 |
| Latin | `Recursive_VF_1.085.ttf` at `MONO` 1 (mono) / 0 (sans), `CASL` 0, `CRSV` 0, `slnt` 0 | same at 700       |

**The static faces do not use the instanced donor.** Measured: at wght 400 the instance's `l` is
4 units narrower than the static `l` (68..532 vs 72..534) and carries the overlap contours the
statics had removed — a pixel on a thin stem at 24 ppem, 12–15% rasterised coverage on that glyph.
Rebuilding the statics from the instance would therefore move the shipped faces, which the card
forbids. The statics keep the Recursive statics (`USE_LATIN_VF = False`, byte-identical to
v1.1.0); only the VF masters take the instance, where the requirement is interpolability. The VF
and the static Regular differ by that sub-pixel amount on a handful of Latin glyphs — documented
here rather than hidden.

## The freeze

A weight axis only interpolates glyphs that share a point structure. Everything still copied from
Sarasa's independently drawn Regular/Bold cannot, so the 700 master takes the 400 outline and
`gvar` stores no delta: the glyph keeps its cell and coverage but does not embolden inside the
variable file. The static Bold faces are unaffected.

| block                        | mono    | sans    |     | block                                         | mono | sans |
| ---------------------------- | ------- | ------- | --- | --------------------------------------------- | ---- | ---- |
| Hangul                       | 8,513   | 8,513   |     | fullwidth                                     | 108  | 108  |
| other (symbol donors)        | 2,246   | 2,670   |     | math                                          | 78   | 68   |
| CJK not in Noto Sans SC      | 2,329   | 2,329   |     | latin-ext-b                                   | 69   | 192  |
| _unencoded (never rendered)_ | _2,066_ | _1,808_ |     | misc/cyrillic/ipa/tech/greek/arrows/geometric | ~270 | ~530 |
| kana                         | 183     | 183     |     | latin-1 / latin-ext-a                         | 37   | 191  |

Totals: **15,940 of 51,138 mono codepoints** (13,874 reachable) and **16,515** (14,707 reachable).
The count grew from the first estimate (13,459) because the audit compares on/off-curve bits, not
just contour and point counts — varLib rejects a glyph whose point types change even when every
count matches, so those glyphs were silently skipped before.

Two of 27,897 CJK glyphs (U+5605, U+7A4A) are frozen for a different reason: `TTGlyphPen` drops a
coincident duplicate point that only appears at wght 700. `tools/vf_compat.py` caps that class at
8 so a real CJK regression (thousands of glyphs) still fails the gate.

## Merge findings

- **BASE is excluded and rewritten.** varLib aborts merging BASE (`UnsupportedFormat` on a
  baseline coordinate, reproduced on the Noto donor); `gf_tables.write_base` rebuilds it on the
  finished VF from the default master's Han ink box.
- **The sans layout tables do not vary.** A GPOS PairPos subtable orders its glyphs differently in
  the two masters (`InconsistentGlyphOrder`) and varLib cannot canonicalise it. The layout tables
  are stripped from the masters for the merge and re-attached from wght 400, so kerning and
  mark anchors are correct at every weight but static. The mono pair merges normally.
- **Hinting is discarded** (`Masters have incompatible fpgm tables`): a warning, not an error. The
  family has never shipped instructions.
- No `MVAR`-driven variation of the win metrics beyond what varLib derives; the two masters are
  produced by the same pipeline, so the default instance matches the static Regular.

## Italic

**Ruled A (2026-10-23): no italic VF in v1.2.0.** The four static faces keep the synthetic CJK
shear. Measured on the shipped italics: CJK stems sit at 9.40° (`k = 0.16556`) while the Latin
italics read 11.48° (`|`) to 13.70° (`H` stem), and the shear thins perpendicular stems by 1.34%.
A true-italic CJK donor would need two more masters per family and an `ital` axis (≈ +7 MB of
`gvar` each), and it re-baselines every italic hanzi.

## Verification

```sh
bun run fonts:vf                        # build both VFs (local, git-ignored)
python3 tools/vf_audit.py --check fonts/vf
bash ../../scripts/vf-gate.sh "$PWD"    # axis ends: grid, census, at.alt
bun run site/scripts/font-probe.ts fonts/vf --vf
```
