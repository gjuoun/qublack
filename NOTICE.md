# Provenance

QuBlack is a derivative work. Every outline in it comes from an upstream project released under
the SIL Open Font License 1.1:

| Layer             | Upstream                                                                     | Version      | Licence     |
| ----------------- | ---------------------------------------------------------------------------- | ------------ | ----------- |
| Hanzi             | Sarasa Gothic / Sarasa Term (be5invis), outlines from Source Han Sans        | 1.0.42       | SIL OFL 1.1 |
| Hanzi weight axis | Noto Sans SC variable font (Google / Adobe, the same Source Han Sans design) | wght 100–900 | SIL OFL 1.1 |
| Latin             | Recursive **Linear** (ArrowType), Sans and Mono — statics up to v1.1.0, the variable source from v1.2.0 | 1.085 | SIL OFL 1.1 |

Derivation: the hanzi and the non-ASCII glyph set come from the Sarasa skeleton (Term SC for the
mono family, Gothic SC for the sans family), with one exception: from v1.1.0 the hanzi outlines are
instanced from the Noto Sans SC variable font (Regular/Italic at `wght` 400, Bold/BoldItalic at
`wght` 700) instead of copied from the two static Sarasa weights. Both are the Source Han Sans
design under the same licence; the move exists because Sarasa's Regular and Bold hanzi are
independently drawn and cannot be interpolated, while a single variable source can. Codepoints the
variable font does not carry (2,482 of them, mostly CJK Extension B) keep the Sarasa outline. The
From v1.2.0 the Latin outlines of every face are instanced from `Recursive_VF_1.085.ttf`
(`wght` 400 and 700, with `MONO`, `CASL`, `slnt`, `CRSV` pinned per style) instead of copied from
the four static faces, so the family has one interpolatable Latin master set like its hanzi. The
two variable donors are pinned and hash-checked by `tools/fetch_cjk_vf.py` and
`tools/fetch_recursive_vf.py`. ASCII is replaced with Recursive Linear outlines
(scaled into the mono cell for QuBlack Mono). Box drawing 0x2500–0x259F is copied from the Term
skeleton into the sans family so tables and code blocks keep half-width cells. `Emoji=Yes`
codepoints are removed from the cmap (keeping ASCII, © ® ™, arrows, box drawing, blocks,
geometric shapes, braille and PUA) so colour emoji fall through to the system font. Name tables
carry the OFL notice and this derivation statement.

QuBlack Mono ships Recursive's `at.alt` alternate for `@` (the target of its `ss12` lookup)
instead of the default `at` drawing; the outline is imported point for point through the same
500/600 cell transform as the rest of the ASCII set. QuBlack Sans keeps the default `@`.

QuBlack Mono harmonises every symbol in the 44-glyph census that sits against hanzi — the delta-8
brackets `" ' ( ) [ ] { } / \ |` plus the delta-10 marks `` ` * ! % & ? @ $ # < > ^ + : ; - = _`
(and a sub-percent nudge on `, . ~`) — by a
per-glyph vertical scale and translate that puts their ink boxes on the same top/height ratios as
the Sarasa Term skeleton (y only; the 500-unit advance is untouched). `tools/symbol_audit.py`
measures and asserts the result within two points. Deliberately left alone: curly quotes (already
flush), guillemets, `…`, `< >` and the CJK punctuation the skeleton brings.

QuBlack Mono uses the upm-833 technique: glyph coordinates stay untouched, `unitsPerEm` is 833,
so the Sarasa 1000-unit cell reads as 1.200em and the 500-unit ASCII cell as 0.600em — a measured
2:1 ratio.

The public family name deliberately differs from every upstream name; no Reserved Font Name from
Source Han Sans (`Source`), Sarasa or Recursive is used.

Build tooling originated in the private `lishu-mono` repository (tools @ `f210d1a`) and is
relicensed here under MIT (see `LICENSE-MIT`).
