# Assemblies: placement, sub-assemblies, mates, big models

Learned on a 738-component net house in SolidWorks 2019 (field report 2026-11-09). Read before building any
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
   Run it **before** building any CAD: three rule conflicts in the field test (anchors coinciding, rods crossing
   under ground, a cable through a cap) were visible here in seconds.

## 6. Files vs configurations
- Separate files per size: simplest to script and verify; fine up to ~100 files.
- Items whose length follows the layout (cables, rods, purlins): **one part with a configuration per length**
  (or update the existing file in place). A file per exact length went from 31 to 53 files after one rule change,
  and every change forced rebuilds.

## 7. Checks that are not self-consistent
Layout-driven checks prove that SolidWorks stored what Python computed, not that the rule is right. Add checks from
first principles: counts derived independently of the layout code, minimum clearances, every cable end on an
attach feature, one lean vector per facade line, no two components at the same position.
