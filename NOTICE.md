# Provenance

QuBlack is a derivative work. Every outline in it comes from an upstream project released under
the SIL Open Font License 1.1:

| Layer | Upstream                                                              | Version | Licence     |
| ----- | --------------------------------------------------------------------- | ------- | ----------- |
| Hanzi | Sarasa Gothic / Sarasa Term (be5invis), outlines from Source Han Sans | 1.0.42  | SIL OFL 1.1 |
| Latin | Recursive **Linear** statics (ArrowType), Sans and Mono               | 1.085   | SIL OFL 1.1 |

Derivation: the hanzi and the non-ASCII glyph set come from the Sarasa skeleton (Term SC for the
mono family, Gothic SC for the sans family). ASCII is replaced with Recursive Linear outlines
(scaled into the mono cell for QuBlack Mono). Box drawing 0x2500–0x259F is copied from the Term
skeleton into the sans family so tables and code blocks keep half-width cells. `Emoji=Yes`
codepoints are removed from the cmap (keeping ASCII, © ® ™, arrows, box drawing, blocks,
geometric shapes, braille and PUA) so colour emoji fall through to the system font. Name tables
carry the OFL notice and this derivation statement.

QuBlack Mono ships Recursive's `at.alt` alternate for `@` (the target of its `ss12` lookup)
instead of the default `at` drawing; the outline is imported point for point through the same
500/600 cell transform as the rest of the ASCII set. QuBlack Sans keeps the default `@`.

QuBlack Mono uses the upm-833 technique: glyph coordinates stay untouched, `unitsPerEm` is 833,
so the Sarasa 1000-unit cell reads as 1.200em and the 500-unit ASCII cell as 0.600em — a measured
2:1 ratio.

The public family name deliberately differs from every upstream name; no Reserved Font Name from
Source Han Sans (`Source`), Sarasa or Recursive is used.

Build tooling originated in the private `lishu-mono` repository (tools @ `f210d1a`) and is
relicensed here under MIT (see `LICENSE-MIT`).
