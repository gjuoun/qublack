# Drift between the 2026-10-21 JunHei build and this reproducible Qu Black build

`shipped-v1.json` records the eight faces that shipped as the JunHei family on 2026-10-21
(`lishu-mono/out/pkg-jh/`). `baseline-v1.json` records this repository's reproducible build and
is what `tools/verify_family.py` compares against.

Six of the eight faces reproduce the shipped face metric-for-metric. The two mono italics do not,
and the reason is a gap in the old build's record rather than a regression here:

| Face                     | Field         | Shipped  | Rebuilt  |
| ------------------------ | ------------- | -------- | -------- |
| Qu Black Mono Italic     | `a` ink width | 0.4999em | 0.5273em |
| Qu Black Mono Italic     | `x` ink width | 0.5682em | 0.6038em |
| Qu Black Mono Italic     | `H` ink width | 0.5758em | 0.6253em |
| Qu Black Mono BoldItalic | `a` ink width | 0.5277em | 0.5554em |
| Qu Black Mono BoldItalic | `x` ink width | 0.5838em | 0.6185em |
| Qu Black Mono BoldItalic | `H` ink width | 0.5955em | 0.6445em |

Advances, upm, line height, glyph counts and every hanzi metric are identical; only the ASCII ink
of the two italic mono faces differs, by about 5% on the wide side. The 2026-10-21 run's italic
Latin donor was never written down, and none of the Recursive 1.085 statics reproduce those
widths: the Linear Italic donor gives the wider ink above, the Casual Italic gives a third set of
numbers. This build uses `RecursiveMonoLnrSt-{Italic,BoldItalic}` for both, consistently with the
family's stated Latin (Recursive Mono **Linear**), which is the reproducible choice.

No other face drifted, and nothing else in the family depends on the italic ASCII ink.
