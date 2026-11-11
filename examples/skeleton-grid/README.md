# skeleton-grid

Small experiments behind the version 2 foundation (see [CHANGELOG](../../CHANGELOG.md), 2026-11-11). Each script is self-contained and needs SolidWorks running on Windows with `pywin32`.

| Script | What it tests |
|---|---|
| `proto_skeleton.py` | A 3x3-bay grid of posts and beams driven by a skeleton part, mated seeds and assembly equations. `python proto_skeleton.py stress N` times N individually mated seeds. |
| `test_holes.py` | Hole Wizard hole, feature linear pattern and mirror, all driven by globals; volume check and edit test on count and pitch. |
| `test_material.py` | Real material with a mass check (100 mm steel cube = 7.8 kg), linked properties, and backup of a file touched by hand before the next save. |
| `test_twoway.py` | Hand and script together: a global changed by hand is pulled back into the parameter file, a hand-added feature is kept, nothing is overwritten. |

Method and traps: [assemblies](../../skill/solidworks-api/references/assemblies.md), [hand edits](../../skill/solidworks-api/references/hand_edits.md), [materials](../../skill/solidworks-api/references/materials_properties.md). Everything here was tested on SolidWorks 2019 only.
