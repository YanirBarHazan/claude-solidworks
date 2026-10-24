# SolidWorks API cheat sheet (verified with SolidWorks 2025 / pywin32)

All lengths in meters. `C = swconst.constants`. Wrap every returned object with `T(obj, "IInterface")`.

## Library (scripts/swcad.py) — preferred way to build parts
```python
from sw_common import connect, close_out_docs, OUT
from swcad import PartBuilder
sw = connect(); close_out_docs(sw)
pb = PartBuilder(sw, {"W": 40.0, "H": 30.0, "T": 3.0, "R": 2.0, "HOLE": 3.2})   # mm, become Global Variables
pb.plane("PL_TOP", "T")                                  # parallel to Front at Z = T (signed); base="Top Plane"/"Right Plane"
with pb.sketch("Front Plane", "SK_BODY") as s:
    s.rrect(0, 0, "W", "H", "R")                         # centre x, y, width, height, corner radius
pb.extrude("SK_BODY", "T", "BODY")                       # +normal; reverse=True for -normal; mode="mid"
with pb.sketch("PL_TOP", "SK_HOLES") as s:
    s.circle("W/2 - 5", "H/2 - 5", "HOLE")
    s.rect("-W/4", 0, 6, 2)                              # numbers or expressions; sketch coordinates
pb.cut("SK_HOLES", "T", "HOLES", reverse=True)           # reverse=True = toward -normal (into the plate)
with pb.sketch("Right Plane", "SK_PROFILE") as s:        # Right sketch: sx = -Z, sy = Y
    s.polygon([(0, 0), (-2, 0), (-2, 1)])                # closed polyline, not dimension-linked
assert not pb.rebuild_errors() and len(pb.bodies()) == 1
lo, hi = pb.bbox(); vol = pb.volume()                    # mm, mm3 — compare with a hand calculation
pb.set_param("W", 50.0)                                  # edit test, then restore
pb.save(OUT + r"\part.sldprt")                           # save + close + reopen + rebuild, raises on any error
```
Each sketch dimension and feature depth is linked to an equation over the global variables, so the
user can edit the part in Tools > Equations.

## Assemblies (scripts/asmtools.py)
```python
from asmtools import place, check_interference, picture, export_stl, stl_bbox, IDENT
doc, asm, comps = place(sw, [(path_a, IDENT, (0, 0, 0)), (path_b, ((0,1,0),(0,0,-1),(-1,0,0)), (x, y, z))], out_asm)
probs = check_interference(asm, {frozenset({"a", "b"}): 131.7,   # designed overlap, mm3 (5 % tolerance)
                                 frozenset({"c", "d"}): None})   # must exist, any volume
picture(doc, png_path, "*Isometric")                     # "*Front", "*Back", "*Right", ...
export_stl(sw, part_path, stl_path); lo, hi, n = stl_bbox(stl_path)
```
Components are fixed in place by transform (no mates) — right for layout/fit checks.
To sweep a mechanism, set `comp.Transform2` for each position, `ForceRebuild3`, check again.

## Raw calls that worked
| Task | Call |
|---|---|
| Version | `sw.RevisionNumber()` |
| New doc | `sw.NewDocument(template, 0, 0, 0)` |
| Open silently | `sw.OpenDoc6(path, C.swDocPART, C.swOpenDocOptions_Silent, "", 0, 0)` → `(doc, err, warn)` |
| Select by name | `doc.Extension.SelectByID2("Front Plane", "PLANE", 0,0,0, False, 0, None, 0)` |
| Revolve | `fm.FeatureRevolve2(True, True, False, False, False, False, 0, 0, 2*pi, 0, False, False, 0,0,0,0,0, True, True, True)` |
| Extrude | `fm.FeatureExtrusion3(True, False, rev, T1, 0, d, 0, F,F,F,F, 0,0, F,F,F,F, True, True, True, 0, 0, False)` |
| Cut | `fm.FeatureCut4(True, False, dir, T1, 0, d, 0, F,F,F,F, 0,0, F,F,F,F, False, True, True, True, True, False, 0, 0, False, False)` |
| Axis | select point + plane (or two planes), `doc.InsertAxis2(True)` |
| Ref plane | select refs, `fm.InsertRefPlane(C.swRefPlaneReferenceConstraint_Distance, d, 0,0,0,0)` |
| Mass | `T(doc.Extension.CreateMassProperty(), "IMassProperty").Mass` |
| Body volume | `T(body,"IBody2").GetMassProperties(density)[3]` |
| Feature errors | `code, is_warning = feat.GetErrorCode2()` |
| Mate (hinge) | `md = T(asm.CreateMateData(C.swMateHINGE), "IHingeMateFeatureData")`, `md.SetEntitiesToMate(C.swHingeMateEntityType_Concentric, arr)`, `asm.CreateMate(md)` |
| Limit angle | select 2 planes (mark 1), `asm.AddMate5(C.swMateANGLE, C.swMateAlignCLOSEST, False, 0,0,0,0,0, nom, nom+lim, nom-lim, False, False, 0)` |
| Coincident | `md = T(asm.CreateMateData(C.swMateCOINCIDENT), "ICoincidentMateFeatureData")`, `md.EntitiesToMate = arr` |
| Unfix | select comps, `asm.UnfixComponent()` |
| Interference | `T(asm.InterferenceDetectionManager, "IInterferenceDetectionMgr").GetInterferences()` |
| Preferences | `sw.GetUserPreferenceToggle(k)` / `SetUserPreferenceToggle(k, v)` — always restore |

Look up any other signature in the generated module:
`%TEMP%\gen_py\3.12\83A33D31-27C5-11CE-BFD4-00400513BB57x0x<ver>x0.py` (sldworks) and the
`4687F359-...` module (swconst enums): `grep -n "def MethodName(" -A3 <file>`.
