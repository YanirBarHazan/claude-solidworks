# Example: a large repetitive structure in SolidWorks 2019 (738 components)

A real project (anonymised): a cable-braced steel structure of 90 poles, 104 ground anchors and ~450 cables, built
and verified entirely by scripts for a PDM on SolidWorks 2019. Full day log with measurements:
`skill/solidworks-api/references/field_log_2026-11-09.md`; the method: `references/update_in_place.md` and
`references/assemblies.md`.

## Architecture
```
params.py        every value with a source tag [M]/[D]/[C]/[A]
layout.py        pure-Python layout: positions, frames, attach points, cable files (one per exact length)
part_*.py        one script per part file (PartBuilder, all dimensions linked to globals, named planes)
part_runner.py   run_part(): fingerprint skip -> one-open update in place -> build only new files   (in this folder)
build_all.py     all parts in one Python process / one SolidWorks session, one line per part        (in this folder)
sa_build.py      one sub-assembly per variant, mates on named planes, transform check after solve
main_build.py    top level by computed transforms (asmtools.place_many, batches of 100, saved per batch)
verify_main.py   counts, positions, cable ends +-1 mm, lengths, rod axis vs cable resultant (from SolidWorks)
check_geometry.py  Python clearances on the rule set, BEFORE any CAD                                 (in this folder)
metrics_chart.py out/metrics.csv -> out/metrics.svg (cost per task)                                  (in this folder)
```
`part_runner.py` and `build_all.py` import the project module `nh_common` (paths, parameter dict, colours); they are
the reference implementation of ROADMAP 1/7/12 and will become a generic `scripts/runner.py`.

## Numbers
| | |
|---|---|
| Parts / sub-assemblies / top-level components | 70 / 6 / 738 |
| No-change run of all parts | 1 s (fingerprints) |
| A value change touching 36 parts | 0 rebuilt, ~15 min |
| Main assembly placement | 60 s |
| Cable ends vs attach points | 0.0000 mm worst of 856 |
