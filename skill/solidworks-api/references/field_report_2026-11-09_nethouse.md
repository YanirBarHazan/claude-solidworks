# solidworks-api skill — field report, Azrom net house PT-8x8 (SolidWorks 2019), 2026-11-09

Scope: one working day (≈12:50–17:00). Parametric model of a 105 × 40 m avocado net house: 66 part files,
5 sub-assemblies, main assembly of 738 components, built and verified entirely by Python/pywin32 from
`params.py` + `PLAN.md`. Numbers below come from the logs and git history; "≈" = estimated from timestamps.

---

## 1. How the work was actually done: rebuild vs update

| | count |
|---|---|
| Part builds **from scratch** (PartBuilder build mode) | **≈ 200** (5 + 4 + 17 + 9 + 3 + 56 + 8 + 36 + 62) |
| Part **updates** (open existing part, change a global, rebuild, save) | **0** (only the in-script edit test, which is restored) |
| Sub-assembly builds from scratch | 17 (3 + 1 + 3 + 5 + 5) |
| Main-assembly builds from scratch | 5 (+2 that crashed) |

Per change today:

| Change | What was rebuilt | Why | Necessary? |
|---|---|---|---|
| PLAN 7–8 (stub, anchor, V cables) | 9 new parts + 4 SAs + main | new geometry | yes |
| PLAN 9/11 (holes, eye bolt, rod loop, colours, anchor resultant) | **all 56 parts** + 3 SAs + main | holes in poles, colours on every part, new cable lengths | **partly** — 18 parts only needed a colour (a property), not a rebuild |
| Colour-check tolerance bug | 8 parts rebuilt again | my check compared colour to 1e-3; SW stores 8-bit truncated | **no** — check bug, the files were correct |
| PLAN 12 (own anchors, roof cables, trellis, chamor, walk) | 36 new/changed (3 parts, 2 rods, 31 cables) | new parts; cable lengths all changed | mostly yes (cables are new length files) |
| PLAN 16 (holes 40→60, chamor embedded, anchors) | 62 (4 poles, chamor post, 4 rods, 53 cables) | one value (TOP_HOLE1) + new lengths | **poles: no** — a value-only change should be an update (set the global, rebuild, save) |

Avoidable rebuilds ≈ 30–35 % of part builds (colour-only, check-bug reruns, value-only hole moves).
How to avoid:
- Make `run_part` **idempotent**: if the file exists and its manifest specs equal the script specs → open, push
  changed global values (`set_param`), re-check, save. Rebuild only when a feature definition changes.
  `partsync` already has the drift logic; the part scripts did not use update mode.
- Colours / custom properties: a separate `props.py` pass that opens each part, sets properties, saves.
- Cable files: a cable is one extrude driven by `CBL_L`; when a length changes, **rename + update** the nearest
  existing file instead of building a new one.

## 2. Times

| Operation | Time | Notes |
|---|---|---|
| Simple part (cable/rod: 1 sketch + 1 extrude) incl. 4 checks + save/reopen | ≈ 25 s | 36 parts 16:10–16:25; 43 parts in ≈ 17 min |
| Pole with 4–6 holes | ≈ 60–90 s | each hole = sketch + cut + 2–3 linked dims; volume check numeric |
| Full part set (56) | ≈ 50 min | step1_all, 14:12–15:03 |
| Sub-assembly (2–8 comps) incl. interference + reopen | ≈ 15–25 s each | |
| Main assembly 558 / 738 comps (AddComponents3, batches of 100, save per batch) | **51 s / 60 s** | after the window fix |
| verify_main (reopen + transforms + checks) | ≈ 2–3 min | |
| Interference on 738 comps | never completed | crashed / disconnected; replaced by 16.4 a/b/c |

**Bottleneck: number of part files × per-file overhead.** Each part runs in its own Python process: connect,
create doc, build, 4 measure passes, save, close, reopen, rebuild, manifest. ≈ 60 % of a cable's 25 s is overhead,
not geometry. The second bottleneck was SolidWorks instability (two crashes, ≈ 40 min lost).

## 3. Tokens

Largest consumers (rough order):
1. **Reading tool output from long runs** — full logs printed back, traceback walls, `ls` of 40+ lock files.
2. **Re-reading PLAN.md / params.py** after every edit by Yanir (sections 7, 8, 11, 12, 16; two "section missing"
   rounds where the file had not been saved — ≈ 3 wasted rounds).
3. **Question rounds** — 5 stop-and-ask rounds (missing dims, corner, tech anchors, eye bolts, file counts).
4. **Retries**: color check (8 parts), heredoc with Hebrew failing in bash (rewrote with Write), main-build crash
   diagnosis (screenshot attempt, process probing).
5. Writing scripts (necessary).

Changes that would save:
- Every script prints **one summary line per item** and writes details to `logs/`; never print tracebacks to
  stdout unless the run failed (then the last 10 lines).
- `PLAN.md` changes arrive as a **diff section with a version stamp**; the skill should check the stamp/size before
  reading and say "section N not found" in one line (it happened twice).
- A pre-flight **question template** (section 7) would have removed ≈ 4 of the 5 question rounds.
- Never `ls` a CAD folder; use counts (`ls | wc -l`, lock-file count).
- Avoid bash heredocs for files with Hebrew; use the file-write tool directly.

## 4. SolidWorks 2019 bugs and limits found

| # | Symptom | Cause | Fix / workaround | In library? |
|---|---|---|---|---|
| 1 | `Equations` error 51 after save + reopen (2 of 3 runs) | `IEquationMgr.LinkToFile` + external txt on 2019 | don't link; globals live in each part | noted in `tools/SW2019_NOTES.md`, step0 changed |
| 2 | `GetPackAndGo()` → "Parameter not optional" / "Invalid number of parameters" | 2019 typelib signature mismatch | not fixed (Pack and Go done by hand) | noted |
| 3 | SolidWorks crashed opening the 46th file in a row (1.4 GB) | `OpenDoc6` opens a window per document | `sw.DocumentVisible(False, type)` while loading, restore in `finally` → 50 files OK | fixed in `main_build.py` |
| 4 | `InterferenceDetectionManager` returns None | document opened without a window (fix #3) is not "active" | open the assembly normally + `ActivateDoc3` (components load without windows anyway) | fixed in `interference.py` |
| 5 | Interference on 738 comps: hang / "object disconnected" | size of the job on 2019 | per-SA interference + a cut-out check assembly (≈190 comps) + Python clearances | process change (PLAN 16.4) |
| 6 | Stale `~$*.sldprt` locks after a crash; next open hangs on a dialog | killed instance | delete locks when SW has no docs open | noted |
| 7 | Colour read back ≠ set (0.05 → 0.047) | `MaterialPropertyValues` stored as truncated 8-bit RGB | compare with 1/255 tolerance | fixed in `nh_common.py` |
| 8 | Dialog during unattended build blocks COM with no error | modal dialog (file in use) | lock-file cleanup before runs; screenshot is masked for `sldworks.exe` (grant the exe name) | process |

## 5. Changes made in `tools/` vs the original skill

| File | Change | Why | Upstream? |
|---|---|---|---|
| `swcad.py` `val()` | accept SolidWorks syntax `^`, `sqr()`, `atn()`, `sin`, `cos` in expressions | one expression string for Python and the SW equation (e.g. pole length `sqr(TOP_H^2+LEAN^2)`) | **yes** |
| `sw_common.py` `connect()` | refuse unless `RevisionNumber()` starts with `SW_REQUIRE_REV` (default `27.`) | 2019 + 2020 on one PC; a 2020 save is unreadable in 2019 | **yes** (generic env var) |
| `SW2019_NOTES.md` | new | version-specific findings | yes, as `references/version_notes.md` |
| project `nh_common.run_part` | build + 4 checks (errors, bodies, bbox, volume, edit, save/reopen, colour) in one call | every part script is 15 lines | **yes** as `swcad.verify_part()` |
| project `nh_common` | `hole_in_tube()`, `rod_in_disk()` numeric volumes | exact expected volume with holes/rings | yes (`volumes.py`) |
| project `main_build` | `AddComponents3` in batches of 100 + save per batch + hidden loading | speed (738 comps in 60 s) and crash safety | **yes** into `asmtools.place_many()` |

## 6. Methods — what worked

- **Placement by computed transforms (no mates): worked very well.** One pure-Python layout (`layout.py`) drives
  the build *and* the checks; 738 components placed in 60 s; every check exact (cable ends 0.0000 mm). Layout
  change = rerun in minutes. Weakness: checks partly self-consistent — they prove SW stored what Python computed,
  not that the rule is right; add independent physical checks (clearances, counts from first principles).
- **Sub-assemblies per pole variant** (SA-PERIM / -W / -C / SA-INT / SA-CHAMOR): good; keeps the main assembly
  at 738 top-level comps. Tilting a rigid SA as a whole worked for poles; it **failed for anchors** (each rod has
  its own angle, the block stays level) → block + rod placed separately.
- **Separate files vs configurations** (PLAN decision): simple and robust for scripting; cost = file count (53
  cable files, 4 rods). Fine up to ~100 files; beyond that configurations of one part + a design table would scale
  better, at the cost of harder per-file verification.
- **Cable file per exact length**: correct geometry (ends meet ±0.0000) but explodes with every rule change
  (31 → 53 files) and forces rebuilds. Recommendation: one cable part with a configuration per length, or keep
  lengths and update in place (see §1).
- **Large greenhouse assemblies with mates (future)**: use mates only inside small SAs (pole + fittings, where the
  user edits by hand); place SAs in the main assembly by transform, fixed. 2019 will not solve hundreds of mates
  across 700+ components comfortably; also mate-driven positions are hard to verify numerically.

## 7. Working with Yanir: missing decisions that caused stops

Stops caused by missing decisions (5 rounds) and by checks finding rule conflicts (3):
- dimensions not given: stub OD/wall, foundation pocket, anchor rod length/orientation/depth reference, cap fit,
  eye-bolt height, corner eye-bolt clash, chamor embedment;
- topology not defined: corner pole lean, shared anchors at the technical row, roof cable on facade lines,
  T-junction vs corner;
- rule conflicts found only after building: anchors coincide (TECH_W = 2·TERR), rods crossing under the strip,
  roof cable through the cap, ANC_OFF_B=2000 crossing rods within line B.

**Question template to ask before building** (one round instead of five):
1. For every part: datum / origin, length rule, what it sits on or inside (fit, embedment, clearance).
2. For every connection: which feature (hole, eye, loop), its height, its direction, the attach point.
3. Corners, ends, T-junctions, symmetry lines: does the general rule apply? shared items?
4. Allowed overlaps list (designed interferences) and minimum clearances.
5. One file per size or configurations; naming; which values are expected to change (→ update mode).
6. Purchased parts: file names, version, which replace which simplified part.
And: run a **Python clearance check on the rule set before any CAD** — 3 of today's conflicts were visible there.

## 8. Ten improvements to the skill (priority order)

| # | Change | Benefit | Effort |
|---|---|---|---|
| 1 | Idempotent part scripts: manifest compare → update values in place, rebuild only on feature change | −30–60 % build time, keeps edge ids for drawings | M |
| 2 | `asmtools.place_many()`: hidden loading (`DocumentVisible`), `AddComponents3` batches, save per batch | no crashes, 60 s for 700+ comps | S |
| 3 | `verify_part()` in swcad (errors, bodies, bbox, volume, edit, save/reopen, colour with 1/255) | 15-line part scripts, uniform checks | S |
| 4 | Python geometry-clearance module (segment/cylinder/box distances, allowed-overlap list) run **before** CAD | finds rule conflicts in seconds, not after a 1-h build | M |
| 5 | Version guard + `references/version_notes.md` (2019: equation link, PackAndGo, interference mgr, windows) | avoids the same stalls next time | S |
| 6 | Batch part builds in **one** SW session/process (no per-part connect/close) | ≈ 2× faster for small parts | M |
| 7 | Pre-run hygiene: kill-safe lock cleanup, "no docs open" check, stall detector on trace log | no silent dialog hangs | S |
| 8 | Interference strategy for big assemblies: per-SA + cut-out region assembly + Python, documented | check 5 actually runs on 2019 | S |
| 9 | Question template + PLAN section stamp check in SKILL.md | fewer stop rounds, no "section missing" rounds | S |
| 10 | Cable/rod "one part, configuration per length" option with design table | file count stays flat when rules change | L |

---
Report: `out/SKILL_REPORT_2026-11-09.md` (committed).
