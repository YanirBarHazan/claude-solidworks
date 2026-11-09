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


# ---------------------------------------------------------------------------------------------------------------
# ROADMAP 3: many components at the top level (2019-safe)
def place_many(sw, items, path, batch=100, new_doc_fn=None):
    """items: [(file path, (X', Y', Z'), origin mm[, configuration])]. Loads referenced files without windows
    (DocumentVisible False - opening ~46 visible documents crashed 2019), adds them with AddComponents3 in batches,
    fixes them, saves after every batch. Returns (doc, asm, comps)."""
    import time
    from sw_common import new_doc as _new
    files = sorted(set(i[0] for i in items))
    try:
        sw.DocumentVisible(False, C.swDocPART)
        sw.DocumentVisible(False, C.swDocASSEMBLY)
        for f in files:
            kind = C.swDocASSEMBLY if f.lower().endswith(".sldasm") else C.swDocPART
            if sw.OpenDoc6(f, kind, C.swOpenDocOptions_Silent, "", 0, 0)[0] is None:
                raise RuntimeError(f"cannot open {f}")
    finally:
        sw.DocumentVisible(True, C.swDocPART)
        sw.DocumentVisible(True, C.swDocASSEMBLY)
    doc = (new_doc_fn or _new)(sw, "asm")
    asm = T(doc, "IAssemblyDoc")
    sw.ActivateDoc3(doc.GetTitle(), False, 0, 0)
    doc.FeatureManager.EnableFeatureTree = False
    comps = []
    for s in range(0, len(items), batch):
        chunk = items[s:s + batch]
        xf = []
        for it in chunk:
            xf += [v for a in it[1] for v in a] + [v * MM for v in it[2]] + [1.0, 0.0, 0.0, 0.0]
        res = asm.AddComponents3(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, [it[0] for it in chunk]),
                                 VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, xf),
                                 VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, [""] * len(chunk)))
        got = [T(c, "IComponent2") for c in (res or ())]
        if len(got) != len(chunk):
            raise RuntimeError(f"AddComponents3 returned {len(got)} of {len(chunk)}")
        for c, it in zip(got, chunk):
            if len(it) > 3 and it[3]:
                c.ReferencedConfiguration = it[3]
        doc.ClearSelection2(True)
        for c in got:
            c.Select4(True, None, False)
        asm.FixComponent()
        doc.ClearSelection2(True)
        comps += got
        save_as(doc, path)
    doc.FeatureManager.EnableFeatureTree = True
    doc.ForceRebuild3(False)
    save_as(doc, path)
    return doc, asm, comps


# ---------------------------------------------------------------------------------------------------------------
# ROADMAP 2: mates on named reference geometry (sub-assemblies), checked against the expected transform
def _sel(doc, name, typ, append, mark):
    ok = doc.Extension.SelectByID2(name, typ, 0, 0, 0, append, mark, None, 0)
    if not ok:
        raise RuntimeError(f"select failed: {name} ({typ})")


def _mate(doc, kind, align, ents, flip=False, dist=0.0, lock=False):
    """ents: [(name, type)] selected with mark 1 (pitfall 18/31: marks matter for mates)."""
    asm = T(doc, "IAssemblyDoc")
    doc.ClearSelection2(True)
    for k, (n, t) in enumerate(ents):
        _sel(doc, n, t, k > 0, 1)
    r = asm.AddMate5(kind, align, flip, dist * MM, dist * MM, dist * MM, 0, 0, 0, 0, 0, False, lock, 0)
    mate, err = (r if isinstance(r, tuple) else (r, None))
    doc.ClearSelection2(True)
    if mate is None:
        raise RuntimeError(f"mate failed ({kind}) on {ents}: error {err}")
    return mate


def mate_concentric(doc, a, b, align=None, lock=True):
    """a, b: ('AX_HOLE1@NH-POLE-3IN-1@SA-PERIM', 'AXIS') or cylindrical faces ('...', 'FACE')."""
    return _mate(doc, C.swMateCONCENTRIC, C.swMateAlignALIGNED if align is None else align, [a, b], lock=lock)


def mate_coincident(doc, a, b, align=None, dist=0.0):
    kind = C.swMateCOINCIDENT if not dist else C.swMateDISTANCE
    return _mate(doc, kind, C.swMateAlignALIGNED if align is None else align, [a, b], dist=dist)


def mate_errors(doc):
    """Error codes of every mate in the assembly (the Mates folder must be clean)."""
    bad = []
    f = doc.FirstFeature()
    while f is not None:
        f = T(f, "IFeature")
        if f.GetTypeName2() == "MateGroup":
            m = f.GetFirstSubFeature()
            while m is not None:
                m = T(m, "IFeature")
                code, warn = m.GetErrorCode2()
                if code or warn:
                    bad.append((m.Name, code, warn))
                m = m.GetNextSubFeature()
        f = f.GetNextFeature()
    return bad


def transform_error(comp, axes, origin_mm):
    """Max deviation (mm, deg) of a component's solved transform from the expected one (flipped mates pass
    the rebuild but fail here)."""
    import math
    d = list(T(comp.Transform2, "IMathTransform").ArrayData)
    dpos = max(abs(d[9 + k] / MM - origin_mm[k]) for k in range(3))
    dang = 0.0
    for i in range(3):
        got = d[3 * i:3 * i + 3]
        dot = sum(g * e for g, e in zip(got, axes[i]))
        dang = max(dang, math.degrees(math.acos(max(-1.0, min(1.0, dot)))))
    return dpos, dang
