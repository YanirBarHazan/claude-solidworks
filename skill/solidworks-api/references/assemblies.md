# Assemblies: placement, sub-assemblies, mates, big models

Learned on a ~740-component steel frame structure in SolidWorks 2019. Read before building any
assembly with more than ~30 components, or any assembly the user will edit by hand.

## 1. Choose the placement method per level

| Level | Method | Why |
|---|---|---|
| Small sub-assembly (≤ ~30 comps: pole + fittings, bracket + bolts) | **Mates** | the user edits these by hand; fasteners belong concentric in their holes; the solver is fast at this size |
| Top level of a repetitive structure (grids of poles, arches, bays) | **Computed transforms, fixed** | 700+ comps placed in 60 s; exact and checkable; 2019 does not solve hundreds of mates across 700+ comps comfortably |
| Mechanism (hinge, slide) | Mates + limit mates | see pitfalls 30-31 |

Default for structures: **mates inside sub-assemblies, sub-assemblies placed by transform**. Tell the user this
trade-off up front: with transforms, dragging one component in SolidWorks moves nothing else.

Optional "skeleton" variant: a layout part with sketch points; each sub-assembly gets 2-3 mates to it, so editing
the sketch inside SolidWorks moves everything. Try it on a small cut-out region first (e.g. 3x3 bays) and measure
open/rebuild time before using it on the full model.

## 2. Mates that survive scripting
- **Mate on named reference geometry, never on faces picked by coordinates.** Give every part that will be mated
  named references when you build it: `AX_<name>` (axis of each hole/tube), `PL_<name>` (seat planes),
  `PT_<name>` (attach points). Select them as `"AX_HOLE1@PART-1@SA-NAME"` with type `"AXIS"` / `"PLANE"`.
  Face selection breaks on every rebuild that renews face ids.
- **Purchased parts you must not modify** (PDM files): find the entity by geometry (cylindrical face with radius r
  whose axis is closest to the target axis), mate it, and record which face was used in the manifest. Do not add
  references to a PDM part.
- Fastener recipe: Concentric (bolt axis to hole axis) + Coincident (head seat plane to the part face plane) +
  Lock rotation or Parallel if the user wants it fully defined. Nut: Concentric + Coincident to the far face.
- Fix exactly one component per sub-assembly (the base part); everything else is mated.
- **Verify mates numerically**: after `ForceRebuild3`, read each component's `Transform2` and compare with the
  transform the script expected (±0.01 mm, ±0.01°). A mate that solved to the flipped alignment passes the
  rebuild but fails this check. Also check every mate's error code (`GetErrorCode2`) and that the Mates folder has
  no warnings.
- Add mates with Solve deferred where possible, rebuild once at the end of the sub-assembly.

## 3. Sub-assemblies
- One sub-assembly per *variant* (standard pole, corner pole, pole with extra eye bolt...), not one per instance.
- A rigid sub-assembly can be tilted as a whole (leaning pole + foundation). It cannot when its members need
  different angles (anchor block level, rod along the cable resultant): place those members separately.
- Purchased fasteners live inside sub-assemblies, never as loose top-level components (keeps the top level small,
  the BOM still counts them). Give each sub-assembly a "simplified" configuration with fasteners suppressed.

## 4. Loading many components (2019)
- `sw.DocumentVisible(False, docType)` while opening parts, restore in `finally`. Opening ~46 visible documents
  in a row crashed SolidWorks 2019 (1.4 GB).
- Add components with `AddComponents3` in batches of ~100; save the assembly after each batch.
- The assembly itself must be opened with a window and activated (`ActivateDoc3`) before interference
  detection, otherwise `InterferenceDetectionManager` is None.

## 5. Interference on big assemblies
Interference over 700+ components hung or disconnected SolidWorks 2019. Instead:
1. Interference per sub-assembly, with the list of designed overlaps.
2. A cut-out check assembly built from the same layout code (one corner + one of each special region, ~200 comps).
3. A Python clearance check over the whole layout (segment/cylinder/box distances) with the allowed-overlap list.
   Run it **before** building any CAD: rule conflicts (two items at one point, members crossing, a cable
   through a cap) are visible here in seconds and cost an hour when found after the build.

## 6. Files vs configurations
- Separate files per size: simplest to script and verify; fine up to ~100 files.
- Items whose length follows the layout (cables, rods, purlins): **one part with a configuration per length**
  (or update the existing file in place). A file per exact length multiplies files after every rule change and
  forces rebuilds.

## 7. Checks that are not self-consistent
Layout-driven checks prove that SolidWorks stored what Python computed, not that the rule is right. Add checks from
first principles: counts derived independently of the layout code, minimum clearances, every cable end on an
attach feature, one lean vector per facade line, no two components at the same position.

## 8. Mate recipe that scripts well (2019, first use)
Plane-to-plane mates only, three per component, on named planes:
- **Our parts**: build them with named planes (`PL_<hole>` through every hole axis, `PL_TOP`, `PL_SEAT`, ...); for a
  coaxial part: Right/Top planes coincident with the base part's + one axial plane pair (coincident or distance).
- **Eye bolt / bolt in a hole** (PDM part, its planes renamed Plane1/2/3): ring/plate plane coincident with the base
  plane that contains the hole axis and the base axis; the plane that contains the shank axis coincident with the
  hole plane `PL_<hole>`; the plane square to the shank distance-mated to the base plane square to the hole.
  Nut: the same with its own planes, bearing face on the far side.
- Insert each component at its computed transform first, fix only the base part, add the mates with
  `swMateAlignCLOSEST`, rebuild once, then `mate_errors(doc)` must be empty and `transform_error(comp, axes,
  origin)` <= 0.01 mm / 0.01 deg for every component.
- An off-axis hole on a round post: a flat nut face touches the curved surface only along a line on the hole axis;
  move the nut out until its footprint clears the surface (or model a washer) - otherwise interference.
- A fitting that must point the other way (left/right end posts) is another sub-assembly variant, not a flipped mate.

## 9. Configurations by suppression (user rule, confirmed by 2019 crashes of the alternative)
The default configuration holds every feature / component; each configuration suppresses all but its own.
Assemblies: one configuration per variant set (with/without a cable family, terrace width ...), components
suppressed per configuration. Do not drive lengths with configuration-specific global values on 2019.

## 10. Patterns and mirrors instead of hundreds of placed components (2019, verified)
- Component linear pattern: `asmtools.linear_pattern(doc, seeds, axis1, n1, s1, axis2, n2, s2, flip1, flip2)`.
  Selection marks are the whole trick: seeds **mark 1**, direction-1 axis **mark 2**, direction-2 axis **mark 4**,
  then `FeatureLinearPattern2`. Directions: assembly reference axes (e.g. Top x Front = X).
- Change count or spacing later without rebuilding anything: `modify_pattern(doc, feat, n1=4, s1_mm=1500)`.
  Tested: 3x2 -> 4x2, spacing 1000 -> 1500, identical after reopen.
- Symmetric halves: `MirrorComponents3` about a named plane (same component, no mirrored file).
- Plan: seed + pattern per repeated family; members whose geometry differs (corners, staggered lines) stay
  placed by transform. Verify with the same position checks - a pattern that shifts anything fails them.

## 11. From hundreds of placements to seeds + patterns (measured, 2019)
`scripts/patterns.py` `plan(items)` takes the same placement list the transform build uses
(`(file, axes, origin[, configuration])`) and groups items with the same file, configuration and orientation whose
origins form equally spaced rows along X, and rows that repeat equally along Z, into one seed + a 1- or 2-direction
linear pattern. It asserts that every pattern reproduces its members exactly; the rest stay single placements.
Build: place seeds + singles (`AddComponents3`, hidden loading, fixed), assembly axes `AX_X` (Top x Front) and
`AX_Z` (Top x Right), `linear_pattern()` per pattern. The direction sign of each axis is learned on the first
pattern (flip and re-check). Final check: the multiset of (file, rotation, origin) of every component in the
file == the layout's - 0 missing, 0 extra, or it fails.

| Assembly | Components | Placed by transform | Patterns | Build time |
|---|---|---|---|---|
| Corner check assembly | 194 | 95 | 48 (covering 99 instances) | 55 s, exact |
| Main assembly (plan) | 770 | 213 | 117 (covering 674) | - |

What it does not cover yet: items whose geometry differs at corners, T-junctions or staggered lines (they stay
singles) and mirror halves (`MirrorComponents3` works; next step).

## 12. Before mating a purchased part, check it against the layout rule
Measure the purchased file first (bbox, cylinders, tori, planes) and check that the rule that places the cable /
bolt agrees with it. Example: a rectangular cable shackle holds the cable in an end curl 13 mm from the bolt axis
with the bolt axis square to the cable, while the layout rule put the cable 36-50 mm from a bolt parallel to it -
caught in Python before any mate, sent to the user as a design question instead of being forced.


## Configurations by suppression on a big assembly (measured 2026-11-10, 2019, 770 components)
Default configuration holds everything; each other configuration suppresses one family. Recipe:
```python
feats = {}                                   # walk the tree ONCE (55 s here) - never per lookup
f = doc.FirstFeature()
while f is not None:
    f = T(f, "IFeature"); feats[f.Name] = f; f = f.GetNextFeature()
doc.AddConfiguration3(name, "", "", 0); doc.ShowConfiguration2(name)
doc.ClearSelection2(True)
for pat in patterns_of_family: feats[pat].Select2(True, 0)          # the pattern feature
for c in seeds_and_singles_of_family: c.Select4(True, None, False)   # not c.IsPatternInstance()
doc.EditSuppress2(); doc.ForceRebuild3(False); doc.Save3(1, 0, 0)  # save after each configuration
```
Check per configuration: resolved components (`GetSuppression2() != 0`) per file = expected. Time: 35 s per
configuration (was > 25 min per component, 15 min with a per-pattern tree walk). If the assembly is regenerated
by a script, create the configurations by script too, after it - hand-made ones would be lost.
Value variants (span, terrace) are NOT configurations: they change part lengths and file counts - keep them as value
sets in the parameters file and update the one model in place.

## Summary rules (from SKILL.md v1)
- Small sub-assemblies (a pole with its fittings, a bracket with bolts): **mates** on named references,
  fasteners concentric in their holes, verified against the expected transforms. Recipe that scripts well:
  **plane-to-plane mates only** (`asmtools._mate`, `mate_errors`, `transform_error`): insert each component at its
  computed transform, fix only the base part, add 3 plane mates per component, rebuild, then every solved
  transform must equal the computed one (a flipped mate passes the rebuild and fails here). Purchased (PDM)
  parts get no added references: use their own planes (often renamed `Plane1/2/3`; identify by normal).
- Top level of repetitive structures: sub-assemblies placed by **computed transforms**,
  `asmtools.place_many()` (hidden loading, `AddComponents3` batches of ~100, save per batch; 738 comps in 60 s).
  Say the trade-off to the user (no drag-editing).
- **Repeated families as seeds + patterns, not hundreds of placements** (assemblies.md 10-11): `patterns.plan()` on
  the placement list, then `asmtools.linear_pattern` (2019 recipe: seeds mark 1, axes mark 2 / 4,
  `FeatureLinearPattern2`); count/spacing changed later with `modify_pattern` - "4 anchors instead of 2" is one value.
  Measured: 194 -> 95 placed components, exact. Mirrors with `MirrorComponents3`.
- One sub-assembly per variant; a variant that needs a mirrored fitting (eye bolt left/right) is its own
  sub-assembly. Use Linear Pattern / Mirror inside a sub-assembly instead of loose repeated components.
- Purchased fasteners inside sub-assemblies, never loose at the top level; a "simplified" configuration
  (by suppression) without them.
- Interference on big assemblies: per sub-assembly + a cut-out check assembly + Python clearances
  (run the clearances on the rule set BEFORE any CAD - three rule conflicts were found there in seconds).
- Layout-following items (cables, rods, purlins): a file per exact length updated in place works and is simple;
  one part with a configuration per length only by suppression (see above), never configuration-specific
  equations on 2019.

## 13. Design-intent top level: skeleton + mated seeds + equation-driven patterns (2019, verified 2026-11-10)
**Use this for any assembly a human will open and change.** It replaces "everything fixed by computed transform"
(section 1), which stays only as a fallback for very large top levels after measuring.
Audit of the two styles (`scripts/audit.py`): fixed-by-transform top level 50/100, this recipe 100/100.

1. **Skeleton part** (`SKEL`): reference planes / axes with names (`PL_TOP`, `PL_X1` ...), each dimension linked to
   a global variable of the part (heights, spans). No solid body needed. It is the ONLY fixed component
   (`asmtools.fix_only`).
2. **Seeds are mated to the skeleton**, 3 plane mates each, never fixed. Insert each seed at its computed transform
   first (the solver then picks the right side), check solved = computed, and settle distance mates
   (`asmtools.settle_distance_mates`: a distance mate has two solutions; in a 100-seed test all 100 solved on the
   wrong side before the flip pass).
3. **Repeats are component patterns driven by assembly equations**: assembly globals (`"N_X"`, `"SPAN_X"`) and
   `asmtools.drive_pattern(doc, pattern, n1='"N_X" + 1', s1='"SPAN_X"', n2=..., s2=...)`.
   2019 dimension names of a component linear pattern: D1 = count dir 1, D3 = spacing dir 1, D2 = count dir 2,
   D4 = spacing dir 2. Changing `"N_X"` in Tools > Equations adds / removes instances; changing `"SPAN_X"` moves them.
4. **One source inside SolidWorks**: an assembly global can read a skeleton dimension -
   `set_equation(doc, "SPAN_Z", component_dim_ref(skel, "PL_Z1"))` gives `"SPAN_Z" = "D1@PL_Z1@SKEL<1>.Part"`.
   The engineer edits the skeleton; the assembly follows.
5. **Editing a component's equations from a script**: activate the component document first
   (`asmtools.edit_component_equation`); without activation the change is silently ignored on 2019.
6. **Update in place**: a value change = `set_equation` + rebuild (0.1 s on the test model). No regeneration, so
   hand-made mates, components and configurations in the assembly survive.

Measured (2019): 3x3-bay grid (34 components, 6 mates, 2 patterns): every edit rebuilds in 0.1 s; save / reopen
0 mate errors. Solver load: 100 individually mated seeds = 300 mates: 0.31 s per mate to create, rebuild 0.7 s,
open 1.5 s. Not measured yet: 200+ seeds, and a real 700-component structure. Example: `examples/skeleton-grid/`.
Part lengths that must follow the same value (a beam as long as the span) live in the part's own globals: push
the value to the part as well (`update_in_place.md`), or accept that the part is edited separately.
