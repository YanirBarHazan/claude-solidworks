# Code changes pending

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
