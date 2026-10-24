---
name: solidworks-api
description: Drive SolidWorks directly from Python (pywin32 COM) to build, check and export real parametric parts and assemblies - sketches with dimensions linked to global variables, features, mates, interference checks, Motion studies, STL export, print orientation, overhang/support checks and sliced Bambu Studio projects. Use this whenever the user wants SolidWorks files (.sldprt/.sldasm) made or changed, wants Claude to "work in SolidWorks", design an enclosure/bracket/mechanism/3D-printed part in SolidWorks, check fits or tolerances, run a SolidWorks Motion study, or prepare SolidWorks parts for printing - even if they don't mention the API, pywin32 or COM. Also use when a previous attempt to connect Claude to SolidWorks via plugins/macros failed.
---

# SolidWorks through the API

Claude runs Python on the same Windows machine as SolidWorks, talks to the running instance over COM,
builds the model, and **verifies every step itself** — the user never relays error messages.
What makes this work is less the API than the method: a small library that absorbs the API's
quirks, and a habit of never trusting geometry that hasn't been measured.

## 0. Setup (once per machine, ~2 min)
1. SolidWorks open, same Windows user, **not** "Run as administrator" (else COM can't see it).
2. `pip install pywin32` (numpy optional, for area checks).
3. Copy `scripts/*.py` from this skill into the project folder (they save parts to `./parts`,
   or set env `SW_OUT`). Then smoke-test: `python scripts/smoke_test.py` from the skill folder —
   it builds, edits, reopens, exports and checks a small part, and should print `SMOKE TEST OK`.
4. If several SolidWorks versions are installed, `sw_common` uses the folder of the running
   SLDWORKS.exe (override `SW_DIR`). Check add-ins you will need (e.g. Motion: `cmotionsw.dll`
   in that folder) *before* promising a feature — tell the user early if it's missing.

## 1. Engineering before modeling
Read `references/engineering.md` now: fits/wall table, snap-fit and detent formulas, PCB clamping,
stand geometry, standard component sizes for sanity checks, and the process that avoided rework.
- **Interrogate the measurements.** Cross-check what the user gives you (hole edge distance + diameter
  vs. hole pitch, sums of offsets vs. board size, "a bit less than 121" → the standard panel size).
  Odd non-round numbers often hide a standard part — look it up. Ask only for what you can't derive,
  and say exactly which dimension is missing and why it matters (e.g. "without the module thickness I
  can't set the enclosure depth").
- **One parameter file** (`params.py`): every value with a source tag `[M]` measured, `[D]` datasheet,
  `[C]` calculated, `[A]` assumption. Assumptions are listed back to the user. Keep printer fits
  (clearances, interference, wall thickness) as their own group — they change after test prints.
- **Derived geometry in one module** (expression strings over parameter names) so all parts agree.
- **Present a plan with drawings and get approval** for anything beyond a single part: parts list,
  joining method, tolerances table, print orientation of each part, and what you will verify.
- For fits you can't be sure of (snaps, press fits, hinges), propose **small test coupons** first.
  Size snap/flex arms by strain: ε = 1.5·t·y/L² (PLA ≲ 1 % for repeated use, ~2 % one-off), and
  orient flexing parts so they bend along the printed layers.

## 2. Build with the library (see references/api_cheatsheet.md)
- `PartBuilder` creates the doc (MMGS), switches off sketch snapping (restored on exit), and links
  **every** dimension to an equation, so the user can edit the part in Tools > Equations.
- Rules that keep parts editable: one outline per sketch (outer body, then cut the inner);
  rectangles/circles through the library (they get proper relations); polylines only for small
  profile details. Name every feature and sketch meaningfully.
- Raw API for anything the library doesn't cover — first read `references/pitfalls.md`; it lists
  47 traps with fixes (out-params, IDispatch args, selection marks, cut direction, mates...).

## 3. Verify every part — never report success without numbers
Run these after each part, print the results, and stop on any failure:
1. `rebuild_errors()` empty and exactly one solid body (unless intended).
2. Bounding box equals the design to 0.001 mm; volume equals a hand calculation (exact for prismatic
   parts; numpy grid integration for curved profiles).
3. **Edit test**: change a global variable, rebuild, check the geometry moved as expected, restore.
4. `save()` = save, close, reopen, rebuild → zero errors (catches session-only artefacts).
5. In assemblies: `check_interference(asm, expected)` with an explicit list of *designed* overlaps
   (press fits, crush ribs, detent preload, a plug tip in its socket). Anything else is a bug —
   and an absent expected overlap is also a bug (e.g. a snap hook not in its groove).
   Sweep moving parts through every position (`comp.Transform2`, rebuild, check).
6. Look at the pictures (`picture()`), and question what you see — the automatic checks once passed
   a leg joined to its wheel by a 1 mm sliver; only the side view showed it.

## 3b. Hand edits: never overwrite them silently
Users also edit the parts in SolidWorks. Every `PartBuilder.save()` writes `<part>.manifest.json`
(the script's feature definitions + the saved file's state). Before touching a part again:
```python
import partsync
mode = partsync.decide(sw, PATH, PARAMS_PY)      # "build" | "update", or exit 3 with a report
pb = PartBuilder(sw, P, path=PATH, mode=mode)
```
- No hand edits -> build as usual. Only added/suppressed features -> update in place automatically.
- Deleted features or changed globals/equations -> the script stops (exit 3) and prints what changed.
  **Ask the user**, then rerun with `--update` (keep hand edits), `--adopt` (hand-changed globals ->
  params.py) or `--rebuild` (discard; only with explicit consent).
- Update mode: features that exist with the same definition are skipped, new ones are appended at the end
  of the tree, a changed definition raises `SyncConflict` (needs a rebuild or replacing that feature).
  Prefer update mode for small additions (a teardrop, a chamfer, a slot): seconds instead of minutes,
  hand edits and drawing references survive. Add the feature to the build script too, so a future
  rebuild still has it.
- A shared equation file is protected the same way (`check_shared` + a `.last.json` snapshot).
- Parts built before manifests existed: run each build script once with `--update` (legacy mode trusts
  the existing names) to write a baseline manifest without changing geometry.
- Self test: `python scripts/sync_test.py` must print `SYNC TEST OK`.
- Update mode also changes existing features in place when only their dimension expressions changed
  (the equations are rewritten; polyline-only sketches are redrawn). Changed structure (feature kind,
  parent plane, cut direction, sign of a value) still needs a rebuild.
- `--no-link` keeps the globals inside each part instead of linking `shared_params.txt` (pitfall 41).
- Long builds: `SWCAD_TRACE=1` prints one timestamped line per feature - log it to a file and treat
  2-3 minutes without a new line as a hang (pitfall 42).

## 4. Drawings
For a production drawing read `references/drawings.md` and use `scripts/drawtools.py`; check every
dimension value AND look at the exported PNG (overlaps, empty sections).

## 5. Print pipeline (FDM)
1. `export_stl` → `orient_stl.py --rot flip_x|side_x|side_y|keep` (rest on Z=0).
2. `overhangs.py <folder>`: flat downward faces = bridges (OK when short), sloped/curved = needs
   support → prefer re-orienting or redesigning (constant profiles print on their side) over supports.
3. `bambu_project.py --name ... --outdir ... *.stl`: arranges, slices with the user's own Bambu presets
   (printer read from BambuStudio.conf), reports minutes, grams, `support_used` and warnings.
   One project per plate/colour; open the first with `bambu-studio.exe <file.3mf>`.

## 6. Working with the user
- **Intake before modeling** (each item cost a reprint once): a labelled photo of every board *from the
  side the user will look at* (directions given from the back mirror the whole design); every connector
  that will be used, with its plug and cable exit; how each loose component is held in all six
  directions (a part that can slide out of a window needs a stop); the fasteners/inserts the user has.
- **Model every interface as a keep-out body from day one** (plugs + wire bend room, cables, fingers on
  buttons) so the interference check covers it - an "open question" in a summary is not a check.
- **Tolerance-stack each joint along its axis**: preloads (crush ribs, detents) push parts apart, so a
  snap's play must exceed them, or the hook never reaches its groove.
- **Stop after two failed attempts at the same step** and tell the user what is known; never guess a cause
  to the user ("the screen is locked") without evidence.
- **Spend fewer credits:** value-only changes -> `set_param`/update mode or the user's own script, never a
  rebuild; scripts print one line per result and log details to a file (read only `tail`/`grep`);
  smoke-test a new SolidWorks session first; ask all intake questions in one message; keep status
  messages short.
- Long builds: run in the background (`python -u`), give a one-line status, keep working on the next script.
- Explain failures plainly ("each run starts clean on purpose; this one hit an API quirk, fixed once in
  the library") — users notice repeated restarts and open documents.
- Close only documents you created; restore any preference you change; never touch files outside
  the project folder.
- Deliver: SolidWorks files, a `build_all.py` that rebuilds everything in order, print files, a short
  assembly sequence, and the list of `[A]` assumptions still to measure.

## Files
- `scripts/sw_common.py` — connect, early binding, typed wrapper `T()`, templates, save, safe closing.
- `scripts/swcad.py` — `PartBuilder`: planes, sketches (rect/rrect/circle/polygon), extrude/cut,
  linked equations, checks, edit test, verified save.
- `scripts/asmtools.py` — place parts by transform, interference with expected overlaps, pictures, STL.
- `scripts/orient_stl.py`, `scripts/overhangs.py`, `scripts/bambu_project.py` — print pipeline.
- `scripts/drawtools.py` — drawing dimensions attached to model edges, placed off the view outline, verified.
- `scripts/smoke_test.py` — end-to-end self test of the above on the live SolidWorks.
- `scripts/partsync.py` — manifests, hand-edit drift report, build/update decision, adopt values.
- `scripts/sync_test.py` — self test of the hand-edit protection and update mode.
- `references/pitfalls.md` — read before writing raw API code.
- `references/api_cheatsheet.md` — library usage and raw call signatures that are known to work.
- `references/engineering.md` — design rules and formulas for printed enclosures and mechanisms.
- `references/drawings.md` — production drawings: recipe, pitfalls, what to put on the sheet.
- `references/tools_and_workflow.md` — reading component listings, approval drawings (incl. RTL
  labels), screen access, old STLs, Bambu Studio, and keeping token use low.
