"""Drawing helpers: attach dimensions to model edges by geometry and verify their values.

    from drawtools import sheet_pt, view_box, Dimensioner
    D = Dimensioner(sw, doc, drw, part_box)            # part_box = ([xmin,ymin,zmin], [xmax,ymax,zmax]) mm
    D.add(view, "plate width", [(-18, -27, z), (18, -27, z)], "top", 36, "h", level=1)
    D.add(view, "hole dia", [(x + r*0.707, y + r*0.707, z)], ("leader", -16, 18), 4, tol=(0, 0.1),
          ctf=True, prefix="2X <MOD-DIAM>")
    for r in D.results: print(r)                       # (label, value, expected, status)

Points are model coordinates (mm) lying ON the edges to pick; where = top/bottom/left/right of the
view outline (+ level) or ("leader", dx, dy) mm from the first point.
Full recipe (views, section, notes, title block): references/drawings.md.
"""
import math

import pythoncom
from win32com.client import VARIANT

from sw_common import T, swconst

C = swconst.constants
MM = 1e-3


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


