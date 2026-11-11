# Roadmap

## Version 2 plan (2026-11-10): from "a correct model" to "a model a human can open, understand and change"
Findings behind it (measured on the 770-component field model, SolidWorks 2019; baseline from `scripts/audit.py`):
- Top assembly: 213 placed components, **all fixed, 0 mates** (audit score 50/100); 11 sub-assemblies fully mated
  (score 100). Assemblies are regenerated from zero on any layout value (10 of 17 minutes); hand edits are lost.
- Parts: 76 of 76 with **no SolidWorks material** (so no mass); 0 default feature names; 119 of 119 sketches fully
  defined.
- All geometry knowledge lived in project Python (3,500 lines, ~1,330 of them generic infrastructure written in
  the conversation). SKILL.md loaded 2,671 words on every use, ~40% about 3D printing.

| # | Phase | Content | Proof |
|---|---|---|---|
| 1 | **Foundation + measurement** - done 2026-11-10 | lean SKILL.md (1,012 words, -63%) + module map; dialogue module + project card; `audit.py` | baseline above |
| 2 | **Design-intent assemblies** | skeleton part (grid, named planes / axes, driven by globals); seeds mated to it instead of fixed; pattern spacing / count linked to assembly equations; **update assemblies in place** | 3x3 cut-out: a value changed inside SolidWorks moves everything; open / rebuild time measured before the full model; audit score |
| 3 | **Hand + script together** | change detection on every file + automatic backup before any write; two-way value sync (3-way compare); `USER_` features left alone | scenarios: hand value edit, hand feature, both sides edited - nothing lost |
| 4 | **Project scaffold** | one command creates a project: parameter text file, generic runner, one-command update, verify, cleanup, guide PDF, file-name prefix | field project migrated with an identical result |
| 5 | **Real engineering data** | SolidWorks materials, mass vs hand calculation, linked properties (mass, material), company templates, Hole Wizard, feature patterns / mirror, fully-defined-sketch gate, tree folders | per part: material, mass check, 0 open sketches |
| 6 | **Drawings + BOM** | views, sections, model-linked dimensions, BOM + balloons, title block from properties, PDF / DXF | every dimension vs the model; BOM counts = layout counts |
| 7 | **Sheet metal** | base / edge flange, cuts, flat pattern, bend table / K-factor, DXF | flat pattern size vs hand calculation |
| 8 | **Simulation** | add-in + licence check; static study (material, fixtures, loads, mesh, run, factor of safety); documented hand calculation when no licence | a case with a known analytic answer |
| 9 | **Benchmark, other versions, release** | fixed benchmark tasks measured in time and tokens per skill version; run on SolidWorks 2025; "tested on" table; v2 release | v1 vs v2 table |

Progress 2026-11-11 (SolidWorks 2019, one live test each): phase 2 recipe in the library (`assemblies.md` 13); phase 3: `filesafe` backup / change detection, two-way value pull, hand features kept; phase 5: material, mass check, linked properties, fully-defined-sketch gate. Open in 3: a generic runner that does the pull automatically (phase 4). Open in 5: templates, Hole Wizard, feature patterns / mirror, tree folders.

Cost levers (each measured or to be measured): lean core; one session per phase with a hand-over file; tools that
run without Claude; scaffold instead of rewriting infrastructure; tested recipe catalogue + API probe script;
one status file per run; preflight before a run; built-in step timer; save after each unit + resume list.

---

## Version 1 code changes (history)

The guidance in SKILL.md and references/ is updated. These library changes have been prototyped in real use and
must be added to `scripts/` **and tested on a live SolidWorks** (smoke_test + sync_test must still pass) before
they are claimed in SKILL.md.

| # | Change | Effort | Status (2026-11-09, SolidWorks 2019 field use) |
|---|---|---|---|
| 1 | **Update in place by default** (top priority): part scripts call `partsync.decide`; value-only changes go through `set_param`; colours and custom properties as a separate pass; a run that changes only values must build 0 parts from scratch | M | **done** (swcad.push_globals, partsync.check_open/compare, example runner): 0 rebuilds on a value change; + fingerprint skip (70 parts in 1 s) |
| 2 | Mate helpers on named references (`mate_concentric`, `mate_coincident`, fastener recipe) + transform check after solve, for sub-assemblies (references/assemblies.md §2) | M | **done, first use** (asmtools._mate / mate_errors / transform_error, plane-to-plane recipe) |
| 3 | `asmtools.place_many()`: hidden loading (`DocumentVisible`), `AddComponents3` batches of ~100, save per batch | S | **done** (asmtools.place_many): 738 comps in 60 s |
| 4 | `swcad.verify_part()`: errors, bodies, bbox, volume, edit test, save/reopen, colour with 1/255 tolerance | S | **done** (PartBuilder.verify) |
| 5 | `swcad.val()` accepts SolidWorks syntax (`^`, `sqr`, `atn`, `sin`, `cos`) so one expression serves Python and the equation | S | **done** |
| 6 | `sw_common.connect()` honours `SW_REQUIRE_REV` | S | **done** (default off; set e.g. 27.) |
| 7 | Batch builds in one SolidWorks session (no per-part connect/close) | M | **done in the example** (build_all.py, runpy in one process) |
| 8 | Pre-run hygiene: stale lock cleanup, "no docs open" check, stall detector on the trace log | S | **done** (scripts/hygiene.py) |
| 9 | `clearance.py`: segment/cylinder/box distances with an allowed-overlap list, run before CAD | M | **done in the example** (check_geometry.py); move to scripts/clearance.py |
| 10 | Layout-following parts as one part with a configuration per length (design table optional) | L | **changed**: configuration-specific equations crashed 2019 -> use suppression-based configurations; file per length updated in place works |
| 11 | `volumes.py`: exact volumes for tube-with-holes, rod-in-disk, ring | S | **done in the example** (hole_in_tube, rod_in_disk in nh_common); move to scripts/volumes.py |
After adding: rebuild `dist/solidworks-api.skill`.

## Next (from the 2026-11-09 field log)
| # | Change | Effort |
|---|---|---|
| 12 | Generic `scripts/runner.py` (fingerprint + one-open update + one session) instead of the example's project runner | M |
| 13 | Fingerprint scope: include a shared module only for scripts that import it (one change reopened 70 parts) | S |
| 14 | Suppression-based configuration helper for parts and assemblies, tested on 2019 | M |
| 15 | Resume list for long batches (a crash mid-batch restarts at the failed item) | S |
| 16 | Hole helper that also creates the named plane (`PL_<hole>`) - every mated part needs it | S |
| 17 | **done** Component linear pattern + modify in place (`asmtools.linear_pattern`, `modify_pattern`) and pattern planner (`scripts/patterns.py`) | - |
| 18 | Mirror halves in the planner (`MirrorComponents3`), then patterns of sub-assemblies with internal patterns (e.g. an anchor set with N anchors) | M |
| 19 | Lock check before saving over shared files (second SolidWorks instance) in `save_as` | S |
