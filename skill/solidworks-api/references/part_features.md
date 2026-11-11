# Part features an engineer expects in the tree: Hole Wizard, patterns, mirror

A hole made as "circle + cut" works, but it tells the next engineer nothing: no standard, no size, no callout in
the drawing; ten holes as ten sketches hide that they are one row. Use the real features (verified on SolidWorks
2019, 2026-11-11, `examples/skeleton-grid/test_holes.py`).

```python
with pb.sketch("Front Plane", "SK_HOLE_POS") as s:
    s.point("EDGE", "ROW")                                   # the hole position, dimensioned to the origin
pb.hole_wizard("HOLE_M10", "SK_HOLE_POS", ("EDGE", "ROW", "T"), "M10", "HOLE_D", kind="clearance")
pb.pattern_linear("PAT_HOLES", ["HOLE_M10"], "Right Plane", "N_HOLES", "PITCH")
pb.plane("PL_MID", "W/2", base="Top Plane")
pb.mirror("MIR_ROW", ["HOLE_M10", "PAT_HOLES"], "PL_MID")
```
- `hole_wizard(name, pos_sketch, face_point, size, diameter, kind, depth=None)`: ISO standard; kind `clearance`
  (screw clearances), `drill`, `tap`; `depth=None` = through all. `face_point` is a point ON the face to drill
  (model coordinates). The wizard drops its own point where the face was picked; the library makes that point
  coincident with the library sketch point, so the position is driven by globals and the wizard's sketch is fully
  defined (the sketch gate in `verify` passes).
- `pattern_linear(name, features, direction, n, spacing)`: direction = a reference plane (its normal) or an axis.
  Count AND spacing are linked to expressions, so "5 holes" is a global variable the engineer changes in
  Tools > Equations. API: features selected with mark 4, direction with mark 1, `FeatureLinearPattern2`.
- `mirror(name, features, plane)`: plane mark 2, features mark 1, `InsertMirrorFeature2`.
- All three are recorded in the manifest like other features (update mode skips them when unchanged).

Proof in the test: plate volume = L x W x T minus 2 x N_HOLES holes of the given diameter (exact), no open sketch,
edit test on the count (5 -> 4) and on the pitch, save + reopen with 0 errors.
Not tested yet: blind and tapped holes, counterbore / countersink, a second pattern direction, circular patterns,
a hole on a non-planar face, and that moving the position point moves the hole (the volume cannot show it).
