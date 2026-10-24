# SolidWorks API pitfalls (pywin32) — symptom → cause → fix

Every item below cost a failed run once. `swcad.py` / `sw_common.py` already handle the ones
marked ✅; the rest you handle in your own code.

## Connecting
1. **`'str' object is not callable` / methods behave like properties** — late binding.
   ✅ Load early-bound wrappers from the install's `.tlb` files (`load_tlb("sldworks.tlb")`,
   `swconst.tlb`, `swmotionstudy.tlb`). `gencache.EnsureDispatch("SldWorks.Application")` fails
   ("cannot automate the makepy process") — SolidWorks does not expose its type info.
2. **`CastTo` → "object has no attribute Invoke"**. ✅ Wrap with the generated class instead:
   `T(obj, "IModelDoc2")` = `swmod.IModelDoc2(ole.QueryInterface(IID_IDispatch))`.
   Every object a method returns is an untyped IDispatch — wrap it before use.
3. **`GetActiveObject` → "Operation unavailable"** although SLDWORKS.exe runs: that instance is not
   in the Running Object Table (different privilege level, or a stale session). Start SolidWorks
   normally (not as admin, same user). Launching it again creates a second instance — fine,
   but leave the user's own instance alone.
4. **Several installs** (`SOLIDWORKS`, `SOLIDWORKS (2)`, ...) may coexist with different add-ins.
   ✅ `SW_DIR` = folder of the *running* SLDWORKS.exe (WMI), override with env `SW_DIR`.

## Arguments
5. **"Python instance can not be converted to a COM object"** for an IDispatch parameter
   (e.g. `SelectByID2(..., Callout)`): with early binding pass `None`, not `VARIANT(VT_DISPATCH, None)`.
6. **ByRef / out params** (`SaveAs` errors/warnings, `AddMate5` error status, `GetErrorCode2`):
   pass plain ints, the results come back as a tuple: `ok, errs, warns = ext.SaveAs(path, 0, 1, None, 0, 0)`.
7. **Arrays of objects** (mate entities): `VARIANT(VT_ARRAY | VT_DISPATCH, [o._oleobj_ for o in objs])`.
   Transforms: `mu.CreateTransform(VARIANT(VT_ARRAY | VT_R8, [16 doubles]))` — rows 0-2 are the
   images of local X, Y, Z axes, then translation (m), scale, 3 zeros.

## Documents
8. **`NewDocument` returns None**: the default-template preference can be a bare name like
   `~BLANK_ASSY_TEMPLATE.asmdot`. ✅ Fall back to `C:\ProgramData\SOLIDWORKS\SOLIDWORKS <year>\templates`.
9. **SaveAs error 1** while another open doc has that file name. ✅ `close_out_docs()` first.
   Never close documents you did not create: a blank `Part1` may be the user's.
10. **Unsaved scratch docs pile up** after failed runs (the user sees "10 assemblies open").
    ✅ An atexit hook closes unsaved docs created by the process.
11. **`AddComponent5` returns None**: the part must be opened (silently) first with `OpenDoc6`,
    then re-activate the assembly with `ActivateDoc3`.
12. **STL / image `SaveAs` returns False**: the document must be the active one (`ActivateDoc3`).
13. **Units**: set MMGS on every new doc (`swUnitSystem` = `swUnitSystem_MMGS`); the API itself is
    always in meters.

## Selection & features
14. **`FeatureByName` missing on IModelDoc2** — it lives on `IPartDoc` / `IAssemblyDoc` / `IComponent2`.
15. **In an assembly, `FeatureByPositionReverse(0)` is the *Mates* folder**, not your new feature.
    Walk `FirstFeature()/GetNextFeature()` and take the last feature of the wanted type.
16. **`SelectByID2("GND_Z","AXIS")` fails in an assembly** (needs `@AsmName`). Select feature
    objects with `feat.Select2(append, mark)` instead.
17. **A failed `SelectByID2(..., append=True)` clears the whole selection.**
18. **`InsertRefPlane` returns None**: marks matter — first reference mark 0, second mark 1
    (e.g. axis mark 0 + plane mark 1 with Angle constraint). Feature `GetFirstDisplayDimension`
    can return the *parent plane's* dimension: ✅ `own_dim()` filters by `FullName.split("@")[1] == feature name`.
19. **Cut direction is opposite to extrude**: from a sketch plane a cut goes to −normal by default.
    ✅ `cut(reverse=True)` means "toward −normal".
20. **A sketch with overlapping contours** (circle over rectangle) will not extrude. Use two features.
21. **Sketch axes on base planes**: Front (X, Y), normal +Z · Top (X, −Z), normal +Y · Right (−Z, Y), normal +X.

## Sketch relations (the subtle ones)
22. **Point snaps to the origin when the offset is small (0.25 mm)** → dimension is refused.
    ✅ Script turns off `swSketchInference` and `swSnapToPoints` and restores them on exit.
23. **`AddToDB = True` creates rectangles with NO relations** (sides not H/V, centre unbound):
    geometry is right but deforms when a dimension is edited.
    ✅ Rectangles are created with AddToDB False and `swSketchAutomaticRelations` True
    (inference still off). Polylines use AddToDB True so endpoints merge into a closed loop.
24. **Two shapes with the same centre**: the nearest-point search grabs the first shape's centre.
    ✅ Track used points (COM identity `p._oleobj_ == q._oleobj_` works).
25. **Concentric outlines in one sketch merge coincident points** (outer arc centre = inner corner)
    and then fight each other. ✅ Never put two outlines in one sketch: extrude the outer, cut the inner.
26. **Sketch fillet (`SketchFillet2`) creates one radius dimension by itself**; find it after the
    sketch closes (unlinked dimension with that value) and link it.
27. **Always run an edit test**: change a global variable, rebuild, check the bounding box/volume,
    restore. Geometry that is right at build time can still be wrongly constrained.

36. **`IModelView.EnableGraphicsUpdate = False` breaks sketching**: centre rectangles are created
    without their centre point (the sketch can no longer be centred/constrained). Only disable the
    feature tree (`FeatureManager.EnableFeatureTree = False`) for speed.
37. **Preferences left changed after a killed run** (atexit never ran). ✅ Originals are written to
    `%TEMP%/solidworks_api_prefs_backup.json` first; the next run restores from it.

38. **`OpenDoc6` returns None for a relative path** — always pass `os.path.abspath(path)`.
39. **Rebuilding a part from scratch discards the user's hand edits** and renews every edge id (drawing
    dimensions dangle). Check drift first (`partsync.decide`) and prefer update mode for additions.

## Equations
28. **`EquationMgr.Add2(..., Solve=True)` per equation makes builds quadratic** (minutes).
    ✅ Add with Solve=False, `EvaluateAll()` + `ForceRebuild3` once (`PartBuilder.solve()`).
    Add only the global variables an expression uses.
29. **"Equations" feature shows error 51 during the session** after API-added equations, whatever
    their text. It disappears after save + reopen. ✅ `save()` closes, reopens, rebuilds and requires
    zero errors — that is the real check.

## Mates
30. **Hinge mate with its own angle limit** (`IHingeMateFeatureData.AngleSelection/MaxVal/MinVal`)
    → error 51. Use a plain hinge + separate `AddMate5(swMateANGLE, ..., angle, upper, lower)` limit mate
    (plane-to-plane at a 90° nominal avoids the sign ambiguity at 0°).
31. **`GetConstrainedStatus()` says "fully" for any component with a limit mate.** Test mobility
    instead: add a temporary angle mate inside the limit (must solve) and beyond it (must fail), delete it.
32. Interference results come per contact patch — sum per component pair before comparing.

## Motion Study
33. API: `doc.Extension.GetMotionStudyManager()` → `IMotionStudy` (swmotionstudy.tlb):
    `StudyType = swMotionStudyTypeCosmosMotion`, `CreateDefinition(swFmAEMGravity)` →
    `ISimulationGravityFeatureData`, `CreateFeature`, `Calculate`, `GetResults` → `GetCMPosition(t, comp)`.
    `GetSupportedStudyTypes` can list Motion Analysis even when the **SOLIDWORKS Motion add-in is
    not installed** (no `cmotionsw.dll` in the install folder) — then setting StudyType silently
    does nothing. Check the DLL and tell the user before building a study.

## Printing pipeline
34. Overhang check on the print-oriented STL (`overhangs.py`): flat downward faces are bridges
    (fine when short); sloped/curved downward faces above the bed need support or a new orientation.
    A horizontal cylinder resting on the bed overhangs in its bottom ~0.3R — never put precision
    features (detent notches) there; make the part a constant profile and print it on its side.
35. Bambu CLI: `--export-3mf` wants a bare file name (joined with `--outdir`); system presets need
    flattening; the result's `Metadata/slice_info.config` holds time, grams, `support_used`, warnings.

## Session health (each cost a long stall on 24/10/2026)
40. **A fresh SolidWorks instance can draw centre rectangles without their centre point** (the two
    diagonals exist, the point does not), regardless of `swSketchAddConstToRectEntity`. The script
    then fails at `centre point not found`. ✅ `_rect` adds the point itself at a diagonal's midpoint
    (`sgATMIDDLE`). **Run `smoke_test.py` on every new SolidWorks instance before a real build** - it
    catches this class of problem in one minute instead of after a five-minute build.
41. **`IEquationMgr.LinkToFile = True` can hang SolidWorks forever** (100 % CPU, no error) on a part with
    ~150 equations; cause not found (not the values' format, not a negative-global multiplier). Every
    feature had built fine. Build with `--no-link` and keep the globals in the part; never retry the
    same hanging call - after one hang, switch strategy and investigate on a scratch copy.
42. **A hung COM call blocks the script with no output.** Run builds with `SWCAD_TRACE=1` (one timestamped
    line per feature) into a log file and watch it with a stall detector (no new line for 2-3 min = hung).
    `| tail -N` in the pipeline hides all progress until the end - write to a file instead.
43. **`partsync.check` must close the part it opened** (✅ now): left open, a rebuild cannot `SaveAs`
    under the same name (error 1). Only shows in build mode - test build mode after `decide`.
44. `IEquationMgr.SetEquation` returns nothing via pywin32 - verify by reading `Equation(i)` back.
45. A new SolidWorks started by script may have no window: set `sw.Visible = True` (✅ `connect()`).
46. Killing SolidWorks leaves `~$<part>.sldprt` lock files next to the parts; delete them (only those of
    the killed instance) or the next open reports the file as in use.
47. Toolchains (ESP32 gcc) break on non-ASCII project paths: a `-D` macro holding the path fails, and a
    junction does not help (PlatformIO resolves it). Use `LV_CONF_INCLUDE_SIMPLE` + `-I include` and put
    `build_dir` on an ASCII path outside OneDrive.
