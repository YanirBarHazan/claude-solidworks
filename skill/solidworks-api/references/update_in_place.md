# Update in place: the runner pattern (measured)

Golden rule: **never rebuild an existing part to change it.** This page is the mechanism that makes it cheap.
Measured on a 70-part, 738-component structure in SolidWorks 2019 (revision 27.3).

## 1. Decision per part (in this order)

| Step | Test | Action | Cost |
|---|---|---|---|
| 1 | Fingerprint in the manifest == current, and the file's mtime == the mtime stored with it | **skip, do not open SolidWorks** | ~0.01 s |
| 2 | File exists with a manifest | open ONCE in update mode | 15-20 s if unchanged, 20-50 s if updated |
| 2a | `partsync.check_open(doc, path)` reports drift (hand edits) | stop, exit 3, ask: `--update` / `--adopt` / `--rebuild` | |
| 2b | dry build raises `SyncConflict` (a feature definition changed) | stop, exit 4, ask before rebuilding | |
| 2c | otherwise | append new features, `push_globals()`, props/colour only if different; if nothing changed: close, store fingerprint | |
| 2d | something changed | `save()` (save, close, reopen, 0 errors) -> `verify(expect)` -> store fingerprint | |
| 3 | No file | build from scratch, full checks incl. the edit test | 24-90 s |

`--rebuild` is the only way to rebuild an existing part and needs the user's explicit consent.

## 2. Fingerprint
`sha1(part script source + the shared geometry module(s) it imports + repr(sorted(values used)) + props + colour)`,
stored in `<part>.manifest.json` with the file's mtime after every save. If the user saves the file in SolidWorks
the mtime changes, so the runner opens it and `partsync` sees the hand edits.
Scope matters: hashing a shared module into every part's fingerprint made one edit in it reopen all 70 parts (13 min);
include it only for scripts that import it.
Seeding: right after a run that verified every file, `--seed-fp` stores the fingerprints without opening anything.

## 3. push_globals
For every global variable in the part whose name is in the script's values: compare `IEquationMgr.Value(i)` with the
new value **at 6 significant digits** (SolidWorks stores 2/3 as 0.666667 - an exact compare "changes" it on every run),
`SetEquationAndConfigurationOption`-free: plain `SetEquation(i, '"NAME" = value')`, one `EvaluateAll` + rebuild.

## 4. One session
All part scripts run in one Python process (`runpy.run_path`, `sys.argv` set per part, stdout captured to
`logs/<part>.log`, one summary line printed). Reset the parameter dict from the parameter file before each part.
On any failure close the documents the part opened, else the next part's `SaveAs` of a document with the same title
fails (error 1). Stop the batch on exit 3/4 (a user decision is needed).

## 5. Appending features in update mode
New features in the script (e.g. named reference planes for mates) are appended at the end of the tree of the
existing file; existing features are skipped; nothing is rebuilt. Seen: 8 parts got 1-7 planes each in place.

## 6. Measured (same model, same machine)

| Scenario | Before (rebuild everything affected) | After |
|---|---|---|
| Run with no change, 70 parts | ~19 min (every part rebuilt or opened) | **1 s** (fingerprints) |
| One value changed (hole position), 70 parts | 62 rebuilt, ~27 min | 0 rebuilt, 36 updated in place, 33 skipped, ~15 min |
| Same value restored | - | 0 rebuilt, 36 updated, ~14.5 min |
| Simple part (cable) | 24 s build | 19 s update, 0.01 s skip |
| Pole with 4-6 holes | 43 s build | 47 s update (3 opens; 1 open after the slim path) |
| Context tokens for the whole 70-part run | - | ~10 k (one summary line per part) |

## 7. Not worth it (yet)
A configuration per length driven by configuration-specific global values: see version_notes 2019 #12-15.


## Equation-only edits must be saved (bug found 2026-11-10)
When a script changes an EXPRESSION (not a value), update mode rewrites that equation in place. Count it as a
change: `PartBuilder.edited` lists the sketches / features whose equations or polylines were rewritten, and the
runner must save + verify when it is non-empty. Before the fix the part was closed unsaved with a new fingerprint,
and every assembly built on it was off (43 mm here) - the mate checks caught it, not the part check.

## One command for any value change (parameters text file + update.bat)
- `params.txt`: `NAME = value ; note`, groups as `[GROUP]` (the names are the SolidWorks globals - never rename),
  value sets as `[SET name]` overrides. `params.py` becomes a loader exposing the same dicts: no script changes.
  After the switch, compare every value with the old file (0 differences) before running anything.
- `update.py`: what changed (vs a snapshot written only after PASS) -> Python geometry checks (stop before CAD) ->
  parts in update mode -> if a layout value changed: sub-assemblies, main assembly, configurations regenerated ->
  verification -> one `UPDATE PASS / FAIL` line. Measured: no change 1.5 min, part-only value 3.5 min, layout
  value (pole lean 500 -> -500, 770 components) 17 min.
- Windows `.bat`: write it ASCII with CRLF line ends. A UTF-8 / LF file broke cmd parsing (`'d' is not recognized`).

## Build rules and the runner pattern (from SKILL.md v1)
- `PartBuilder` creates the doc (MMGS), switches off sketch snapping (restored on exit), and links
  **every** dimension to an equation, so the user can edit the part in Tools > Equations.
- Rules that keep parts editable: one outline per sketch (outer body, then cut the inner);
  rectangles/circles through the library (they get proper relations); polylines only for small
  profile details. Name every feature and sketch meaningfully.
- Raw API for anything the library doesn't cover — first read `references/pitfalls.md`; it lists
  47 traps with fixes (out-params, IDispatch args, selection marks, cut direction, mates...).
- **Update in place by default, rebuild only when the structure changes** (`references/update_in_place.md`).
  The runner pattern, measured on a 70-part model in SolidWorks 2019:
  1. **Fingerprint first** (hash of the part script + shared geometry module it imports + the values it uses +
     props + colour, stored in the manifest with the file's mtime). Same fingerprint and file not saved since
     -> skip without opening SolidWorks: **70 unchanged parts in 1 s instead of 19 min.**
  2. Otherwise **one open**: `PartBuilder(mode="update")` + `partsync.check_open` (hand edits -> stop, exit 3),
     dry build (existing features skipped, new ones appended - e.g. reference planes), `push_globals()`
     (value changes; compare at 6 significant digits), props/colour only if different, save + reopen, `verify()`.
     A changed feature definition raises `SyncConflict` -> stop (exit 4) and ask before any rebuild.
  3. New file -> build from scratch with the full checks.
  Result: a value change touching 36 of 70 parts = 0 rebuilds, ~15 min (before: 62 rebuilds, ~27 min, every
  edge id renewed). Rebuilding by habit also renews edge ids: mates and drawings dangle.
- **One SolidWorks session for a batch of parts** (`runpy` in one process, `reset_params()` before each part,
  one summary line per part, counts built/updated/unchanged at the end). Close the part's documents on any
  failure, or the next part's SaveAs fails (error 1).
- **Pre-run hygiene** (`scripts/hygiene.py`): with no documents open, delete stale `~$*` locks; heartbeat that
  prints `STALL <item>` after 3 min without progress (a modal dialog blocks COM without an error).
- Give every part that will be mated or attached to **named reference geometry** (`AX_*`, `PL_*`, `PT_*`):
  e.g. one plane per hole through its axis (`pb.plane("PL_HOLE_X", "L - 160")`), appended in update mode.
- **Configurations: by suppression** (the default holds every feature/component, each configuration suppresses
  all but its own). Configuration-specific global values (`SetEquationAndConfigurationOption`) crashed
  SolidWorks 2019 inside a batch build (version_notes 2019 #12-15) - don't use them on 2019.
- **Log every SolidWorks/API error in the project's version notes in the same turn** (date | symptom | cause |
  fixed / workaround / open). At the end of the conversation the log becomes skill changes.
- **Measure, don't estimate, cost per task**: in the Claude desktop app, the session usage tool gives the
  context size and the 5-hour plan percentage; log the delta per task with the wall time and the counts
  (built / updated / unchanged) to `out/metrics.csv` and chart it.
