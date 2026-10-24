# Production drawings through the API (verified: SOLIDWORKS 2025, ISO A3, first angle)

Worked example: the desk-agent project script `step8_drawing.py` (hinge block) - copy and adapt.

## Recipe
1. Part custom properties feed the title block (`$PRPSHEET:` fields): Description, Material, Finish, Weight.
   `cpm = T(part.Extension.CustomPropertyManager(""), "ICustomPropertyManager")`;
   `cpm.Add3(name, C.swCustomInfoText, value, C.swCustomPropertyReplaceValue)`. Drawing properties
   (`$PRP:` fields): DrawnBy, DrawnDate, CheckedBy, Revision, COMPANYNAME. DWG NO = file name.
2. `doc = sw.NewDocument(<templates>\Drawing.DRWDOT, C.swDwgPaperA3size, 0.42, 0.297)`;
   `drw.SetupSheet5(name, C.swDwgPaperA3size, C.swDwgTemplateCustom, scale1, scale2, True (first angle),
   <lang\english\sheetformat\a3 - iso.slddrt>, 0.42, 0.297, "Default", True)`.
3. Document style: `SetUserPreferenceInteger(swDetailingLinearDimPrecision, 0, 1)`,
   `swDetailingLinearTolPrecision` 2, `swDetailingDimTrailingZero` = `swDimRemoveTrailingZeroes`.
4. Views: `CreateDrawViewFromModelView3(part, "*Front", x, y, 0)`; select it
   (`SelectByID2(view.GetName2(), "DRAWINGVIEW", ...)`) then `CreateUnfoldedViewAt3(x, y, 0, False)`.
   First angle: put the RIGHT view on the LEFT, the TOP view BELOW. Iso: `"*Isometric"`, ScaleDecimal.
   Display: `view.SetDisplayMode3(False, C.swHIDDEN / swHIDDEN_GREYED / swSHADED_EDGES, False, True)`.
5. Section: activate the parent view, draw the cut line in the VIEW SKETCH space, select it,
   `drw.CreateSectionViewAt5(x, y, 0, "A", 0, None, 0)`. Check the result has hatching.
6. Centre marks: `view.AutoInsertCenterMarks2(swAutoInsertCenterMarkType_Hole, swCenterMark_ShowNoConnectLines,
   False, False, True, 0, 0, True, False, 0)`.
7. Dimensions: `drawtools.Dimensioner` (select edges through model points, place relative to the view
   outline, read the value back). Tolerances: `t = T(dim.Tolerance, "IDimensionTolerance")`;
   `t.Type = C.swTolBILAT`; `t.SetValues(min_m, max_m)`; read back `GetMinValue/GetMaxValue`.
8. Notes: `note = T(doc.InsertNote(text), "INote")`; `note.SetTextJustification(C.swTextJustificationLeft)`;
   `T(note.GetAnnotation(), "IAnnotation").SetPosition2(x, y, 0)` (upper-left of the box).
9. Export: `doc.Extension.SaveAs(".pdf" / ".png", 0, 1, None, 0, 0)`. LOOK at the PNG (crop/zoom with
   PIL): value checks cannot see overlapping text or a section that cut nothing.

## Pitfalls met
- A sketch in a drawing view uses the view space (model units about the view centre = sheet scaled by
  1/scale and shifted): convert sheet points with `view.GetSketch().ModelToSketchTransform`.
  Using sheet coordinates put the section line outside the part -> a "section" with no hatching.
- `IDimensionTolerance.SetValues2(..., swSetValue_InThisConfiguration, None)` silently did nothing in a
  drawing; `SetValues(min, max)` works.
- `SetText(swDimensionTextPrefix, "2X ")` replaces the default prefix and drops the diameter symbol:
  use `"2X <MOD-DIAM>"`.
- The default note justification put the text left of its anchor (off the sheet): set it left first.
- Place dimensions from the view outline (bbox corners through the view transform), not from the picked
  point, or they land inside the view.
- Edge picking: `SelectByID2("", "EDGE", sheet_x, sheet_y, ...)` at a model point mapped by
  `view.ModelToViewTransform` works; pick points away from other edges and from section arrows.

## Content that improves on a typical company sheet
Critical-to-function dims marked `*` with real tolerances (fits), general tolerances in the notes,
a section through the feature whose depth matters, an iso view, process notes (print orientation,
inserts, assembly), weight computed from the model, revision field filled.
