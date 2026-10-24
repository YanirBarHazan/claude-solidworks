"""Step 8: production drawing of the hinge block (ISO A3, first-angle projection).

Views: front (contact face), side, top, isometric. Dimensions are attached to model edges found
by geometry (model point -> view transform -> sheet point -> select edge), and every dimension's
value is read back and compared with the design value. Title block fields come from the part's
custom properties (description, material, finish, weight) and the drawing's (drawn by, date, rev).
Outputs: parts/hinge_block.slddrw, drawings/hinge_block.pdf (+ png preview).
"""
import datetime
import math
import os

import pythoncom
from win32com.client import VARIANT

import encl as E
from encl import P, v
from sw_common import connect, close_out_docs, save_as, T, swconst, OUT, CREATED

C = swconst.constants
MM = 1e-3
PART = os.path.join(OUT, "hinge_block.sldprt")
DRW = os.path.join(OUT, "hinge_block.slddrw")
PDF_DIR = os.path.join(os.path.dirname(OUT), "drawings")
TEMPLATE = r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2025\templates\Drawing.DRWDOT"
FORMAT = r"C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2025\lang\english\sheetformat\a3 - iso.slddrt"
SCALE = 2

# ---- hinge block geometry in model coordinates (mm), from the shared parameters ----
ZC = v(E.Z_BACK_OUT)                 # contact face
ZO = v(E.HB_OUT_Z)                   # plate outer face
ZA = v(E.Z_AX)                       # hinge axis
HY = P["HINGE_Y"]
Y0, Y1 = v(E.HB_CY) - P["HB_L"] / 2, v(E.HB_CY) + P["HB_L"] / 2
X1 = P["HB_W"] / 2
KI, KO = P["MID_W"] / 2 + P["KN_GAP"], P["MID_W"] / 2 + P["KN_GAP"] + P["K_W"]   # knuckle inner/outer x
SX = P["HB_SCREW_X"]
RP = (P["PIN_D"] - P["PIN_PRESS"]) / 2
RI = P["INSERT_D"] / 2
AW = P["ARM_W"] / 2

PROPS_PART = {
    "Description": "STAND HINGE BLOCK",
    "Material": "PLA (Bambu PLA Basic)",
    "Finish": "AS PRINTED, 0.2 mm LAYERS",
}
PROPS_DRW = {
    "DrawnBy": "Claude", "DrawnDate": datetime.date.today().strftime("%d.%m.%y"),
    "CheckedBy": "", "EngineeringApproval": "", "Revision": "A",
    "COMPANYNAME": "DESK AGENT - personal project",
}

NOTES = [
    "NOTES (UNLESS OTHERWISE SPECIFIED):",
    "1. DIMENSIONS IN MM. GENERAL TOLERANCES (FDM): LINEAR +/-0.2, HOLES +/-0.15, ANGLES +/-1 DEG.",
    "2. DIMENSIONS MARKED * ARE CRITICAL TO FUNCTION - CHECK ON THE FIRST PART.",
    "3. PRINT CONTACT FACE (FRONT VIEW) ON THE BED. NO SUPPORT. LAYER 0.2, 3 WALLS, 20% INFILL.",
    "4. INSTALL 2x M3 HEAT INSERTS (D4.0 HOLES) FLUSH WITH THE CONTACT FACE.",
    "5. PRESS D5 HINGE PIN THROUGH BOTH FIXED KNUCKLES (D{:.2f} TEARDROP HOLE, ROOF UP WHEN PRINTING).".format(2 * RP),
    "6. ASSEMBLE TO BACK BODY WITH 2x M3x8 SCREWS FROM INSIDE.",
]


def sheet_pt(view, mu, p):
    """Model point (mm) -> sheet point (m) through the view's transform."""
    pt = T(mu.CreatePoint(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [c * MM for c in p])), "IMathPoint")
    pt = T(pt.MultiplyTransform(T(view.ModelToViewTransform, "IMathTransform")), "IMathPoint")
    a = pt.ArrayData
    return a[0], a[1]


def view_box(view, mu, part_box):
    """Sheet-space outline (m) of the part in a view: the 8 bbox corners through the view transform."""
    lo, hi = part_box
    pts = [sheet_pt(view, mu, (x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


class Dimensioner:
    GAP, STEP = 8.0, 7.0      # mm on the sheet: first dimension line from the outline, then each level

    def __init__(self, sw, doc, drw, part_box):
        self.sw, self.doc, self.drw, self.box = sw, doc, drw, part_box
        self.mu = T(sw.GetMathUtility(), "IMathUtility")
        self.results = []

    def add(self, view, label, pts, where, expect, kind="free", tol=None, ctf=False, prefix=None, level=0):
        """Select edges through model points `pts`; place the dimension `where` = top/bottom/left/right
        (at `level`) of the view outline, or ("leader", dx, dy) from the first point; compare with `expect`."""
        doc = self.doc
        self.drw.ActivateView(view.GetName2())
        doc.ClearSelection2(True)
        ok = True
        sp = [sheet_pt(view, self.mu, p) for p in pts]
        for i, (x, y) in enumerate(sp):
            ok &= bool(doc.Extension.SelectByID2("", "EDGE", x, y, 0, i > 0, 0, None, 0))
        x0, y0, x1, y1 = view_box(view, self.mu, self.box)
        mx, my = sum(p[0] for p in sp) / len(sp), sum(p[1] for p in sp) / len(sp)
        d = (self.GAP + self.STEP * level) * MM
        if isinstance(where, tuple):
            loc = (sp[0][0] + where[1] * MM, sp[0][1] + where[2] * MM)
        else:
            loc = {"top": (mx, y1 + d), "bottom": (mx, y0 - d), "left": (x0 - d, my), "right": (x1 + d, my)}[where]
        fn = {"free": doc.AddDimension2, "h": doc.AddHorizontalDimension2, "v": doc.AddVerticalDimension2}[kind]
        dd = fn(loc[0], loc[1], 0) if ok else None
        doc.ClearSelection2(True)
        if dd is None:
            self.results.append((label, None, expect, "NOT PLACED (edge selection failed)" if not ok else "NOT PLACED"))
            return
        dd = T(dd, "IDisplayDimension")
        dim = T(dd.GetDimension2(0), "IDimension")
        val = dim.SystemValue / MM
        status = "OK" if abs(val - expect) < 1e-3 else "WRONG VALUE"
        if tol:
            t = T(dim.Tolerance, "IDimensionTolerance")
            t.Type = C.swTolBILAT
            t.SetValues(tol[0] * MM, tol[1] * MM)
            got = (t.GetMinValue() / MM, t.GetMaxValue() / MM)
            if max(abs(got[0] - tol[0]), abs(got[1] - tol[1])) > 1e-6:
                status = f"TOLERANCE NOT SET {got}"
        if prefix:
            dd.SetText(C.swDimensionTextPrefix, prefix)
        if ctf:
            dd.SetText(C.swDimensionTextSuffix, " *")
        self.results.append((label, val, expect, status))


def main():
    sw = connect()
    close_out_docs(sw)
    os.makedirs(PDF_DIR, exist_ok=True)
    # part properties -> title block
    r = sw.OpenDoc6(PART, C.swDocPART, C.swOpenDocOptions_Silent, "", 0, 0)
    part = T(r[0], "IModelDoc2")
    vol = sum(T(b, "IBody2").GetMassProperties(1000)[3] for b in T(part, "IPartDoc").GetBodies2(C.swSolidBody, True)) / MM ** 3
    cpm = T(part.Extension.CustomPropertyManager(""), "ICustomPropertyManager")
    for k, val in {**PROPS_PART, "Weight": f"{vol * 1.24e-3:.1f} g solid / ~3.6 g printed"}.items():
        cpm.Add3(k, C.swCustomInfoText, val, C.swCustomPropertyReplaceValue)
    part.ForceRebuild3(False)
    save_as(part, PART)

    doc = T(sw.NewDocument(TEMPLATE, C.swDwgPaperA3size, 0.42, 0.297), "IModelDoc2")
    CREATED.add(doc.GetTitle())
    drw = T(doc, "IDrawingDoc")
    sheet = T(drw.GetCurrentSheet(), "ISheet")
    assert drw.SetupSheet5(sheet.GetName(), C.swDwgPaperA3size, C.swDwgTemplateCustom, SCALE, 1, True,
                           FORMAT, 0.42, 0.297, "Default", True), "sheet setup failed"
    ext = doc.Extension
    ext.SetUserPreferenceInteger(C.swDetailingLinearDimPrecision, 0, 1)      # 13.3, not 13.30
    ext.SetUserPreferenceInteger(C.swDetailingLinearTolPrecision, 0, 2)      # +0.05
    ext.SetUserPreferenceInteger(C.swDetailingDimTrailingZero, 0, C.swDimRemoveTrailingZeroes)   # 36, not 36.0
    cpd = T(doc.Extension.CustomPropertyManager(""), "ICustomPropertyManager")
    for k, val in PROPS_DRW.items():
        cpd.Add3(k, C.swCustomInfoText, val, C.swCustomPropertyReplaceValue)

    # views (sheet coordinates in m; A3 = 0.420 x 0.297; title block bottom-right)
    front = T(drw.CreateDrawViewFromModelView3(PART, "*Front", 0.165, 0.185, 0), "IView")
    assert front is not None, "front view failed"
    doc.ClearSelection2(True)
    front_feat = T(drw.FeatureByName(front.GetName2()), "IFeature") if hasattr(drw, "FeatureByName") else None
    doc.Extension.SelectByID2(front.GetName2(), "DRAWINGVIEW", 0, 0, 0, False, 0, None, 0)
    side = T(drw.CreateUnfoldedViewAt3(0.060, 0.185, 0, False), "IView")      # first angle: right view on the left
    doc.ClearSelection2(True)
    doc.Extension.SelectByID2(front.GetName2(), "DRAWINGVIEW", 0, 0, 0, False, 0, None, 0)
    top = T(drw.CreateUnfoldedViewAt3(0.165, 0.085, 0, False), "IView")       # first angle: top view below
    doc.ClearSelection2(True)
    iso = T(drw.CreateDrawViewFromModelView3(PART, "*Isometric", 0.345, 0.215, 0), "IView")
    for vw in (side, top, iso):
        assert vw is not None, "view creation failed"
    front.SetDisplayMode3(False, C.swHIDDEN, False, True)
    top.SetDisplayMode3(False, C.swHIDDEN, False, True)
    side.SetDisplayMode3(False, C.swHIDDEN_GREYED, False, True)
    iso.SetDisplayMode3(False, C.swSHADED_EDGES, False, True)
    iso.ScaleDecimal = 1.5
    doc.ForceRebuild3(False)

    # section A-A: vertical cut through the right insert hole, drawn in the front view
    mu = T(sw.GetMathUtility(), "IMathUtility")
    drw.ActivateView(front.GetName2())
    a = sheet_pt(front, mu, (SX, Y1 + 4, ZC))
    b = sheet_pt(front, mu, (SX, Y0 - 4, ZC))
    doc.ClearSelection2(True)
    vsk = T(front.GetSketch(), "ISketch")
    to_sk = T(vsk.ModelToSketchTransform, "IMathTransform")    # sheet -> view sketch (scaled, shifted)

    def sk_pt(q):
        m = T(mu.CreatePoint(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [q[0], q[1], 0.0])), "IMathPoint")
        return T(m.MultiplyTransform(to_sk), "IMathPoint").ArrayData
    a, b = sk_pt(a), sk_pt(b)
    line = doc.SketchManager.CreateLine(a[0], a[1], 0, b[0], b[1], 0)
    section = None
    if line is not None:
        T(line, "ISketchSegment").Select4(False, None)
        section = drw.CreateSectionViewAt5(0.255, 0.185, 0, "A", 0, None, 0)
    section = T(section, "IView") if section is not None else None
    print("section view:", "OK" if section is not None else "FAILED")
    doc.ClearSelection2(True)
    for vw in (front, side):
        vw.AutoInsertCenterMarks2(C.swAutoInsertCenterMarkType_Hole, C.swCenterMark_ShowNoConnectLines,
                                  False, False, True, 0, 0, True, False, 0)
    doc.ForceRebuild3(False)

    pb = T(T(part, "IPartDoc").GetBodies2(C.swSolidBody, True)[0], "IBody2").GetBodyBox()
    part_box = ([c / MM for c in pb[:3]], [c / MM for c in pb[3:]])
    D = Dimensioner(sw, doc, drw, part_box)
    # front view (X right, Y up): plate, insert holes, detent arm
    D.add(front, "insert hole pitch", [(SX + RI, HY, ZC), (-SX + RI, HY, ZC)], "top", 2 * SX, "h", ctf=True)
    D.add(front, "plate width", [(-X1, Y1 - 3, ZC), (X1, Y1 - 3, ZC)], "top", 2 * X1, "h", level=1)
    D.add(front, "insert hole height", [(-SX - RI, HY, ZC), (-X1 + 3, Y0, ZC)], "left", HY - Y0, "v")
    D.add(front, "plate height", [(-X1 + 3, Y1, ZC), (-X1 + 3, Y0, ZC)], "left", Y1 - Y0, "v", level=1)
    D.add(front, "insert hole dia", [(-SX - RI * 0.7071, HY + RI * 0.7071, ZC)], ("leader", -16, 18), 2 * RI,
          tol=(0, 0.1), ctf=True, prefix="2X <MOD-DIAM>")
    D.add(front, "detent arm width", [(-AW, HY - 6, ZC), (AW, HY - 6, ZC)], "bottom", 2 * AW, "h")
    # side view (Z horizontal, Y up): plate thickness, axis position, knuckle eye, pin hole
    D.add(side, "plate thickness", [(X1, Y0 + 1, ZC), (X1, Y0 + 1, ZO)], "bottom", ZC - ZO, "h")
    D.add(side, "axis from contact face", [(KO, HY + RP, ZA), (X1, Y0 + 1, ZC)], "top", ZC - ZA, "h",
          tol=(-0.1, 0.1), ctf=True)
    D.add(side, "axis height", [(KO, HY + RP, ZA), (X1, Y0, ZC - 1)], "left", HY - Y0, "v")
    D.add(side, "pin hole dia", [(KO, HY + RP * 0.7071, ZA + RP * 0.7071)], ("leader", 16, 20), 2 * RP,
          tol=(0, 0.05), ctf=True)
    D.add(side, "knuckle radius", [(KO, HY - P["K_R"] * 0.5, ZA - P["K_R"] * 0.866)], ("leader", 14, -14), P["K_R"])
    # top view: knuckle widths and the gap for the 16.4 mm leg wheel
    zk = (ZO + ZA) / 2
    D.add(top, "knuckle width", [(KI, HY, zk), (KO, HY, zk)], "bottom", P["K_W"], "h")
    D.add(top, "wheel gap", [(-KI, HY, zk), (KI, HY, zk)], "bottom", 2 * KI, "h", tol=(0, 0.2), ctf=True, level=1)
    D.add(top, "knuckle span", [(-KO, HY, zk), (KO, HY, zk)], "bottom", 2 * KO, "h", level=2)
    if section is not None:
        D.add(section, "insert depth", [(SX, HY + RI + 1.5, ZC), (SX, HY, ZC - P["INSERT_L"])], "top",
              P["INSERT_L"], "h")

    # notes (bottom left)
    doc.ClearSelection2(True)
    drw.ActivateSheet(sheet.GetName())
    note = T(doc.InsertNote("\n".join(NOTES)), "INote")
    if note is not None:
        note.SetTextJustification(C.swTextJustificationLeft)
        ann = T(note.GetAnnotation(), "IAnnotation")
        ann.SetPosition2(0.022, 0.283, 0)            # upper-left of the note box
    doc.ForceRebuild3(False)

    print("dimension                    value      design   status")
    bad = 0
    for label, val, exp, status in D.results:
        print(f"  {label:24s} {('%.3f' % val) if val is not None else '   -   ':>9s}  {exp:8.3f}   {status}")
        bad += status != "OK"
    save_as(doc, DRW)
    pdf = os.path.join(PDF_DIR, "hinge_block.pdf")
    ok_pdf = doc.Extension.SaveAs(pdf, 0, 1, None, 0, 0)[0]
    png = os.path.join(PDF_DIR, "hinge_block.png")
    ok_png = doc.Extension.SaveAs(png, 0, 1, None, 0, 0)[0]
    print("saved", DRW, "| pdf", ok_pdf, "| png", ok_png)
    print("DRAWING OK" if bad == 0 else f"DRAWING HAS {bad} PROBLEM DIMENSIONS")


if __name__ == "__main__":
    main()


