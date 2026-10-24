# Variable faces (v1.2.0)

v1.2.0 adds two weight-axis variable fonts to the eight static faces. They are **build outputs, not
committed files**: `fonts/` is fully git-ignored, the binaries are produced locally by
`bun run fonts:vf`, and they ship inside the release zip only.

| family       | file                             | PostScript              | instances                                          | glyphs | size              |
| ------------ | -------------------------------- | ----------------------- | -------------------------------------------------- | ------ | ----------------- |
| QuBlack Mono | `fonts/vf/QuBlackMono[wght].ttf` | `QuBlackMonoVF-Regular` | Regular 400 · Medium 500 · SemiBold 600 · Bold 700 | 57,129 | 22,574,360 B      |
| QuBlack Sans | `fonts/vf/QuBlackSans[wght].ttf` | `QuBlackSansVF-Regular` | same ladder                                        | 53,716 | see the build log |

The family string is the unmarked name — Google Fonts rejects `VF` as an illegal particle — while
the PostScript name keeps the marker. That marker is deliberate: the static faces already own
`QuBlackMono-Regular`, and two installed fonts with one PostScript name collide in every font
manager. The cost is one waived Google Fonts check (`font_names` expects family + style); the
alternative is a name collision or dropping the statics from the release.

## Google Fonts profile

```sh
.tools/fontspector -p googlefonts --skip-network \
  -x family_name_compliance -x cjk_vertical_metrics -x file_size -x font_names \
  'fonts/vf/QuBlackMono[wght].ttf'
```

Result: **FAIL 0 / FATAL 0** for both families (WARN-only). The four waivers are the three the
static gate already carries — `QuBlack` is CamelCase, the 1.25 em line box is a design decision,
CJK families exceed the 9 MB file-size limit — plus `font_names` for the PostScript marker above.

## Masters

Two masters per family, both built by the normal pipeline (`build_qublack.build`), so the VF and
the statics cannot drift:

| layer | wght 400                                                                             | wght 700          |
| ----- | ------------------------------------------------------------------------------------ | ----------------- |
| CJK   | `NotoSansSC-VF.ttf` instanced at 400                                                 | same donor at 700 |
| Latin | `Recursive_VF_1.085.ttf` at `MONO` 1 (mono) / 0 (sans), `CASL` 0, `CRSV` 0, `slnt` 0 | same at 700       |

**The static faces do not use the instanced donor.** Their Latin comes from the Recursive statics
(`USE_LATIN_VF = False`, byte-identical to v1.1.0); only the VF masters take the variable instance.
That instance is reconciled to the static release before it is drawn (next section), so the two
agree on ink: measured per glyph, the axis ends are within 0.7% of the shipped statics.

## Latin ink

The variable donor is not the drawing ArrowType shipped in its statics. Its static releases bake the
donor's own alternates, and drawing a glyph out of a variable font never applies them, so the raw
instance loses 15–30% of the ink area on the affected glyphs (mono `i` 28.0%, `r` 25.4%, `f` 19.2%,
`l` 14.9%, `g` 1.6%; sans `0` 15.3%, `l` 8.2%). The v1.2.0 variable faces shipped that way, which
is why thin stems rendered visibly lighter than the statics at small sizes.

`tools/latin_masters.py` now reconciles every `0x20–0x7E` slot against the matching ArrowType static
of the same weight: among the default glyph and its `name.*` alternates it keeps the one with the
static's box and ink, decomposes it into the slot, and reports the pick. The picks are the ones the
statics use — `f.mono g.mono i.mono l.mono r.mono` for the mono family, `l.sans zero.sans_pnum` for
the proportional one — and the build aborts above 2.5% drift instead of shipping a face whose
strokes disagree.

| per glyph, against the shipped statics | ink area       | rasterised ink, 24/48 ppem |
| -------------------------------------- | -------------- | -------------------------- |
| before (v1.2.0)                        | −28.0% (`i`)   | −87.5 px² (`i`)            |
| after                                  | **0.7%** (`\`) | **2.8 px²** (`Q`)          |

The pair still interpolates (`vf_compat`: `ascii 0`); the reconciliation rewrites five glyph slots
per mono family and two per sans family, and adds no geometry. `python3 tools/latin_masters.py
sources/upstream/Recursive_VF_1.085.ttf --mode mono --style Regular --check` prints the picks and
the residual (0.76% for mono Regular, 0.54% for sans Regular).

**Ruled out — `removeOverlaps()` and stem compensation.** Applying
`fontTools.ttLib.removeOverlaps` to each instance breaks the point structure of 35 of 95 ASCII
glyphs (`#` 88 vs 72 points, `x` 51 vs 56, `1` 43/43 with a different on/off bit pattern), so the
pair can no longer be merged, and it changes rendered ink by 0.0–0.9% (`l` 1.16 → 1.16 px² at
12 px). The gap was the missing alternates, not the overlaps.

**`maxp` limits change how an instance rasterises.** varLib zeroes the merged `maxp` instruction
limits (`maxZones` 1, no twilight/storage/stack), and FreeType then renders the same outline 8.8%
heavier on `@` than the static face does. `build_vf.py` restores the six limits from the wght 400
master, which is what the statics carry.

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
python3 tools/latin_masters.py sources/upstream/Recursive_VF_1.085.ttf --mode mono --style Regular --check
bash ../../scripts/vf-gate.sh "$PWD"    # axis ends: grid, census, at.alt
python3 ../../scripts/vf-ink.py --vf fonts/vf   # per-glyph ink of the axis ends vs fonts/ttf
bun run site/scripts/font-probe.ts fonts/vf --vf
```
