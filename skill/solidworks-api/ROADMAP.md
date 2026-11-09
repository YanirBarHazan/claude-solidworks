# Code changes pending

The guidance in SKILL.md and references/ is updated. These library changes have been prototyped in real use and
must be added to `scripts/` **and tested on a live SolidWorks** (smoke_test + sync_test must still pass) before
they are claimed in SKILL.md.

| # | Change | Effort |
|---|---|---|
| 1 | **Update in place by default** (top priority): part scripts call `partsync.decide`; value-only changes go through `set_param`; colours and custom properties as a separate pass; a run that changes only values must build 0 parts from scratch | M |
| 2 | Mate helpers on named references (`mate_concentric`, `mate_coincident`, fastener recipe) + transform check after solve, for sub-assemblies (references/assemblies.md §2) | M |
| 3 | `asmtools.place_many()`: hidden loading (`DocumentVisible`), `AddComponents3` batches of ~100, save per batch | S |
| 4 | `swcad.verify_part()`: errors, bodies, bbox, volume, edit test, save/reopen, colour with 1/255 tolerance | S |
| 5 | `swcad.val()` accepts SolidWorks syntax (`^`, `sqr`, `atn`, `sin`, `cos`) so one expression serves Python and the equation | S |
| 6 | `sw_common.connect()` honours `SW_REQUIRE_REV` | S |
| 7 | Batch builds in one SolidWorks session (no per-part connect/close) | M |
| 8 | Pre-run hygiene: stale lock cleanup, "no docs open" check, stall detector on the trace log | S |
| 9 | `clearance.py`: segment/cylinder/box distances with an allowed-overlap list, run before CAD | M |
| 10 | Layout-following parts as one part with a configuration per length (design table optional) | L |
| 11 | `volumes.py`: exact volumes for tube-with-holes, rod-in-disk, ring | S |

After adding: rebuild `dist/solidworks-api.skill`.
