# sources

The design sources QuBlack is built from, in the layout `tools/build_qublack.py --sources`
expects. Everything here is upstream, SIL OFL 1.1, and hash-pinned:

| Layer | Files |
|---|---|
| Hanzi skeleton | `SarasaTermSC-{Regular,Italic,Bold,BoldItalic}.ttf` (QuBlack Mono) |
| Hanzi skeleton | `SarasaGothicSC-{…}.ttf` (QuBlack Sans) |
| Hanzi weight axis | `NotoSansSC-VF.ttf` (Google/Adobe, wght 100–900) |
| Latin (mono) | `rec_mono/RecursiveMonoLnrSt-{…}.ttf` (ArrowType Recursive 1.085) |
| Latin (sans) | `ArrowType-Recursive-1.085/…/RecursiveSansLnrSt-{…}.ttf` |
| Latin weight axis | `Recursive_VF_1.085.ttf` (the same release, variable source; `MONO`/`CASL`/`wght`/`slnt`/`CRSV` axes) |

From v1.2.0 the Latin outlines of every face come from `Recursive_VF_1.085.ttf`, instanced per
style instead of copied from the four statics: the statics are independently drawn per weight and
cannot be interpolated. `python3 tools/fetch_recursive_vf.py` writes it (2,379,132 bytes, SHA-256
`653221ca…f7c`); the four statics stay in the tree because the symbol census and the `at.alt`
guard still reference them.

`MANIFEST.sha256` pins all 17 files. Build with:

```sh
python3 -m pip install -r tools/requirements.txt
bash sources/build.sh            # writes fonts/ttf/
```

These are the files the transformation pipeline consumes, not an authoring source: the
design is programmatic (grid maths, upm-833, symbol harmonisation, CJK instancing), so the
repository's source is the pipeline plus these pinned inputs. See NOTICE.md for provenance.
