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

`MANIFEST.sha256` pins all 17 files. Build with:

```sh
python3 -m pip install -r tools/requirements.txt
bash sources/build.sh            # writes fonts/ttf/
```

These are the files the transformation pipeline consumes, not an authoring source: the
design is programmatic (grid maths, upm-833, symbol harmonisation, CJK instancing), so the
repository's source is the pipeline plus these pinned inputs. See NOTICE.md for provenance.
