# CJK weight and the variable-font masters

From v1.1.0 every face takes its hanzi outlines from **Noto Sans SC VF** (google/fonts, SIL OFL
1.1, `wght` 100–900), instanced at `wght` 400 for Regular/Italic and `wght` 700 for
Bold/BoldItalic. Advances, cmap and glyph order still come from the Sarasa skeleton, so the grid
never depends on the donor.

## Why the donor changed

v1.0.4 already shipped a real bold: the Bold skeletons were `SarasaTermSC-Bold` /
`SarasaGothicSC-Bold`, whose hanzi is Source Han Sans Bold. What it could not do is interpolate —
Sarasa's Regular and Bold hanzi are independently drawn, so their outlines have different point
structures and no weight axis can be built from them:

| pair                              | URO glyphs compared | contour/point signature mismatch |
| --------------------------------- | ------------------- | -------------------------------- |
| `SarasaTermSC-Regular` vs `-Bold` | 500                 | 410 (82%)                        |
| `NotoSansSC-VF` @400 vs @700      | 500                 | 0                                |

`tools/cjk_weight.py --check` asserts exactly that: `interpolable` must reach 0 mismatches, and the
Bold face must stay a bold. It runs against `fonts/` after a build and is not part of `bun run
check` (it needs the built faces).

## Measured weight (built faces, em units, outlines only)

| metric                                  | Regular                  | Bold   | ratio  |
| --------------------------------------- | ------------------------ | ------ | ------ |
| `一` ink height (CJK horizontal stroke) | 0.0984                   | 0.1573 | 1.60x  |
| `丨` ink width (CJK vertical stem)      | 0.0972                   | 0.1573 | 1.62x  |
| `                                       | ` ink width (Latin stem) | 0.0960 | 0.1441 | 1.50x |
| CJK / Latin stroke (mono)               | 1.01                     | 1.09   | —      |
| CJK / Latin stroke (sans, upm 1000)     | 0.84                     | 0.91   | —      |

The sans ratio is lower because Qu Black Sans keeps upm 1000 while Qu Black Mono shrinks the em to
833, which raises every stroke relative to the em. `cjk_weight.py --check` therefore asserts a band
(`|ratio - 1| <= 0.20`), not one number. Heavy (`wght` 900) was measured and rejected: it pushes the
mono ratio to ~1.40, i.e. hanzi visibly heavier than the Recursive Bold Latin.

## Ink delta against v1.0.4

`reference/baseline-v1.json` records the v1.0.4 build; `reference/baseline-v2.json` records this
one. The grid (`--grid-only`: upm, advances, line height, glyph count, codepoint count) is
identical for 8/8 faces; the ink boxes move only where the donor's outline differs from Sarasa's:

| family                  | glyphs whose ink box moved           | fields        | worst delta       |
| ----------------------- | ------------------------------------ | ------------- | ----------------- |
| Qu Black Mono (4 faces) | `国` `永` `口`                       | `w`, `h`, `y` | `永` h −0.0024 em |
| Qu Black Sans (4 faces) | `国` `永` `口`                       | `w`, `h`, `y` | `永` h −0.0020 em |
| both                    | `汉` `图` `一` `黑` `白` `a` `x` `H` | —             | 0.0000            |

46 of the 72 compared ink fields moved, none by more than 0.0024 em; the full per-face list is the
`ink` diff between `baseline-v1.json` and `baseline-v2.json`.

Worst case 0.0024 em (two font units at upm 833). Anything above 0.003 em fails the build rather
than being absorbed into the baseline.

## The 2,482-codepoint boundary

The donor covers 27,897 of Sarasa's 30,379 CJK codepoints. The remaining 2,482 keep their Sarasa
outline: Extension B 2,055, Compatibility Ideographs 244, Extensions C–F 93, Extension A 10, URO
16. They stay bold in the Bold faces — they are simply not interpolatable, so a future variable
font would pin them at their static weight. Closing that gap means the full Source Han Sans VF
(CFF2, needs a cu2qu pass) rather than the SC subset, which is a separate card.

## Italic

Sarasa's italic CJK is a synthetic shear, and the donor is sheared the same way rather than
re-invented: `x' = x + 0.16556 * (y - 333.16)`, fitted on 266 points from SarasaTermSC
Regular→Italic with a 0.51-unit maximum residual (the Same fit on Bold→BoldItalic gives 0.16556 and
the same pivot). A uniform affine transform preserves interpolability, so the italic masters stay
compatible with the upright ones.
