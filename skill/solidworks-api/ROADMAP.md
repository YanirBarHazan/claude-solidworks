# Code changes pending (from the 2026-11-09 field report)

The guidance in SKILL.md and references/ is updated. These library changes exist as working, project-specific
code in the net house project (`tools/`, `scripts/nh_common.py`, `scripts/main_build.py`) and must be ported into
`scripts/` **and tested on a live SolidWorks** (smoke_test + sync_test must still pass) before they are claimed here.

| # | Change | Source in the project | Effort |
|---|---|---|---|
| 1 | Part scripts update in place by default (`partsync.decide` + `set_param` for value-only changes; props/colours as a separate pass) | new | M |
| 2 | `asmtools.place_many()`: hidden loading (`DocumentVisible`), `AddComponents3` batches of 100, save per batch | `main_build.py` | S |
| 3 | `swcad.verify_part()`: errors, bodies, bbox, volume, edit test, save/reopen, colour with 1/255 tolerance | `nh_common.run_part` | S |
| 4 | `swcad.val()` accepts SolidWorks syntax (`^`, `sqr`, `atn`, `sin`, `cos`) so one expression serves Python and the equation | `tools/swcad.py` | S |
| 5 | `sw_common.connect()` honours `SW_REQUIRE_REV` | `tools/sw_common.py` | S |
| 6 | Batch builds in one SolidWorks session (no per-part connect/close) | new | M |
| 7 | Pre-run hygiene: stale lock cleanup, "no docs open" check, stall detector on the trace log | partly in project | S |
| 8 | `clearance.py`: segment/cylinder/box distances with an allowed-overlap list, run before CAD | new | M |
| 9 | Mate helpers on named references (`mate_concentric`, `mate_coincident`, fastener recipe) + transform check after solve | new, see references/assemblies.md §2 | M |
| 10 | Layout-following parts as one part with a configuration per length (design table optional) | new | L |
| 11 | `volumes.py`: exact volumes for tube-with-holes, rod-in-disk, ring | `nh_common` | S |

After porting: rebuild `dist/solidworks-api.skill`.
