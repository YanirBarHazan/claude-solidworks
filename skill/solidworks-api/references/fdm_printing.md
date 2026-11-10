# 3D-printed parts (FDM): design process and print pipeline

Design rules and formulas: `engineering.md`. This file: the process around them.

## Print pipeline
1. `export_stl` → `orient_stl.py --rot flip_x|side_x|side_y|keep` (rest on Z=0).
2. `overhangs.py <folder>`: flat downward faces = bridges (OK when short), sloped/curved = needs
   support → prefer re-orienting or redesigning (constant profiles print on their side) over supports.
3. `bambu_project.py --name ... --outdir ... *.stl`: arranges, slices with the user's own Bambu presets
   (printer read from BambuStudio.conf), reports minutes, grams, `support_used` and warnings.
   One project per plate/colour; open the first with `bambu-studio.exe <file.3mf>`.

## Engineering before modeling (printed parts, enclosures, mechanisms)
**Ask the whole intake in one round** (`references/intake.md`): datums, attach features, corners/ends/
T-junctions, shared items, allowed overlaps, files vs configurations, PDM properties, purchased parts.
For layout-driven models, run the Python layout + clearance check on the rules before any CAD.
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
