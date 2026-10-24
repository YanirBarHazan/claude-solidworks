"""Assembly helpers: place parts by transform, interference check, picture, STL export."""
import os

import pythoncom
from win32com.client import VARIANT

from sw_common import new_doc, save_as, T, swconst, OUT

C = swconst.constants
MM = 1e-3
IDENT = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def place(sw, items, path):
    """items: list of (part path, (axX, axY, axZ), origin_mm). Components are fixed in place."""
    mu = T(sw.GetMathUtility(), "IMathUtility")
    for f, _, _ in items:
        r = sw.OpenDoc6(f, C.swDocPART, C.swOpenDocOptions_Silent, "", 0, 0)
        assert r[0] is not None, f"cannot open {f}"
    doc = new_doc(sw, "asm")
    asm = T(doc, "IAssemblyDoc")
    sw.ActivateDoc3(doc.GetTitle(), False, 0, 0)
    comps = []
    for f, axes, o in items:
        c = T(asm.AddComponent5(f, 0, "", False, "", 0, 0, 0), "IComponent2")
        assert c is not None, f"AddComponent5 failed for {f}"
        xf = [v for a in axes for v in a] + [v * MM for v in o] + [1, 0, 0, 0]
        c.Transform2 = mu.CreateTransform(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, xf))
        comps.append(c)
    doc.ClearSelection2(True)
    for c in comps:
        c.Select4(True, None, False)
    asm.FixComponent()
    doc.ClearSelection2(True)
    doc.ForceRebuild3(False)
    save_as(doc, path)
    return doc, asm, comps


def interferences(asm):
    mgr = T(asm.InterferenceDetectionManager, "IInterferenceDetectionMgr")
    mgr.TreatCoincidenceAsInterference = False
    mgr.IncludeMultibodyPartInterferences = False
    found = []
    for itf in (mgr.GetInterferences() or ()):
        itf = T(itf, "IInterference")
        names = frozenset(T(c, "IComponent2").Name2.rsplit("-", 1)[0] for c in itf.Components)
        found.append((names, itf.Volume / MM ** 3))
    mgr.Done()
    return found


def check_interference(asm, expected):
    """expected: {frozenset(names): approx volume mm3 or None (any)}. Returns list of problems."""
    problems = []
    found = {}
    for names, vol in interferences(asm):         # one pair can touch in several places: sum them
        found[names] = found.get(names, 0.0) + vol
    found = list(found.items())
    for names, vol in found:
        exp = expected.get(names, "missing")
        ok = exp is None or (exp != "missing" and abs(vol - exp) <= max(0.5, 0.05 * exp))
        print(f"   interference {sorted(names)} {vol:.2f} mm3 -> {'expected' if ok else 'UNEXPECTED'}")
        if not ok:
            problems.append((names, vol))
    for names in expected:
        if not any(n == names for n, _ in found):
            problems.append((names, "expected interference not found"))
            print(f"   expected interference {sorted(names)} NOT found")
    if not found:
        print("   no interference")
    return problems


def picture(doc, path, view="*Isometric"):
    doc.ShowNamedView2(view, -1)
    doc.ViewZoomtofit2()
    doc.GraphicsRedraw2()
    ok, _, _ = doc.Extension.SaveAs(path, 0, 1, None, 0, 0)
    return ok and os.path.exists(path)


def export_stl(sw, part_path, stl_path):
    r = sw.OpenDoc6(part_path, C.swDocPART, C.swOpenDocOptions_Silent, "", 0, 0)
    d = T(r[0], "IModelDoc2")
    sw.ActivateDoc3(d.GetTitle(), False, 0, 0)       # STL export only works on the active document
    ok, _, _ = d.Extension.SaveAs(stl_path, 0, 1, None, 0, 0)
    return ok and os.path.exists(stl_path)


def stl_bbox(path):
    """Bounding box (mm) of a binary STL - confirms units and size of the exported file."""
    import struct
    b = open(path, "rb").read()
    n = struct.unpack("<I", b[80:84])[0]
    lo, hi = [1e9] * 3, [-1e9] * 3
    for i in range(n):
        v = struct.unpack("<12f", b[84 + 50 * i:84 + 50 * i + 48])[3:]
        for k in range(9):
            lo[k % 3] = min(lo[k % 3], v[k]); hi[k % 3] = max(hi[k % 3], v[k])
    return lo, hi, n
