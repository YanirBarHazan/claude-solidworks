"""PLAN_PATTERNS step 1-2: build an assembly as seeds + component linear patterns (+ single placements) from the same
placements as main_build.py, then check that EVERY component in the file sits exactly where the layout puts it.
  python pattern_build.py corner   -> cad/NH-CHECK-CORNER.sldasm   (prototype)
  python pattern_build.py main     -> cad/NH-PT-8x8.sldasm         (previous one kept as NH-PT-8x8_transforms.sldasm)
Pattern recipe (2019): asmtools.linear_pattern - seeds mark 1, X axis mark 2, Z axis mark 4, FeatureLinearPattern2.
Directions: assembly axes AX_X (Top x Front) and AX_Z (Top x Right); the flip of each is found on the first pattern
and checked on every one (a wrong instance position fails the final check anyway)."""
import collections
import os
import shutil
import sys
import time

import pythoncom
from win32com.client import VARIANT

from nh_common import CAD, connect, close_out_docs, T, C
from sw_common import new_doc, save_as
from asmtools import linear_pattern, modify_pattern
import main_build as MB
import patterns as PT

MM = 1e-3


def make_axis(doc, a, b, name):
    doc.ClearSelection2(True)
    doc.Extension.SelectByID2(a, "PLANE", 0, 0, 0, False, 0, None, 0)
    doc.Extension.SelectByID2(b, "PLANE", 0, 0, 0, True, 0, None, 0)
    doc.InsertAxis2(True)
    last = None
    f = doc.FirstFeature()
    while f is not None:
        f = T(f, "IFeature")
        if f.GetTypeName2() == "RefAxis":
            last = f
        f = f.GetNextFeature()
    last.Name = name
    doc.ClearSelection2(True)
    return last


def comp_state(c):
    d = list(T(c.Transform2, "IMathTransform").ArrayData)
    return (os.path.basename(c.GetPathName()).lower(),
            tuple(round(v, 4) for v in d[:9]), tuple(round(d[9 + k] / MM, 2) for k in range(3)))


def item_state(it):
    return (os.path.basename(it[0]).lower(), tuple(round(v, 4) for a in it[1] for v in a),
            tuple(round(v, 2) for v in it[2]))


def build(items, path, batch=100):
    t0 = time.time()
    pats, singles = PT.plan(items)
    sw = connect()
    close_out_docs(sw)
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
    doc = new_doc(sw, "asm")
    asm = T(doc, "IAssemblyDoc")
    sw.ActivateDoc3(doc.GetTitle(), False, 0, 0)
    ax_x = make_axis(doc, "Top Plane", "Front Plane", "AX_X")
    ax_z = make_axis(doc, "Top Plane", "Right Plane", "AX_Z")
    doc.FeatureManager.EnableFeatureTree = False
    placed = [p["seed"] for p in pats] + singles
    comp_of = {}
    for s in range(0, len(placed), batch):
        chunk = placed[s:s + batch]
        xf = []
        for k in chunk:
            f, axes, o = items[k][:3]
            xf += [v for a in axes for v in a] + [v * MM for v in o] + [1.0, 0.0, 0.0, 0.0]
        res = asm.AddComponents3(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, [items[k][0] for k in chunk]),
                                 VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, xf),
                                 VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, [""] * len(chunk)))
        got = [T(c, "IComponent2") for c in (res or ())]
        if len(got) != len(chunk):
            raise RuntimeError(f"AddComponents3 returned {len(got)} of {len(chunk)}")
        doc.ClearSelection2(True)
        for c, k in zip(got, chunk):
            comp_of[k] = c
            c.Select4(True, None, False)
        asm.FixComponent()
        doc.ClearSelection2(True)
        save_as(doc, path)
    print(f"  placed {len(placed)} seeds/singles ({time.time() - t0:.0f} s)", flush=True)
    flip = {"x": True, "z": False}                      # from the 2019 prototype; re-checked below
    made = 0
    for n, p in enumerate(pats):
        seed = comp_of[p["seed"]]
        if p["n1"] > 1:
            f = linear_pattern(doc, [seed], ax_x, p["n1"], p["s1"], ax_z if p["n2"] > 1 else None,
                               p["n2"], p["s2"], flip1=flip["x"], flip2=flip["z"], name=f"PAT_{n + 1:03d}")
        else:
            f = linear_pattern(doc, [seed], ax_z, p["n2"], p["s2"], flip1=flip["z"], name=f"PAT_{n + 1:03d}")
        made += 1
        if made == 1:                                   # learn the direction signs once, on the first pattern
            doc.ForceRebuild3(False)
            states = collections.Counter(comp_state(T(c, "IComponent2")) for c in asm.GetComponents(True))
            want = [item_state(items[k]) for k in p["members"]]
            if not all(states[w] for w in want):
                d1 = "x" if p["n1"] > 1 else "z"
                flip[d1] = not flip[d1]
                data = T(f.GetDefinition(), "ILocalLinearPatternFeatureData")
                data.AccessSelections(doc, None)
                data.D1ReverseDirection = not data.D1ReverseDirection
                f.ModifyDefinition(data, doc, None)
                print(f"  direction {d1} reversed after the first pattern", flush=True)
        if made % 25 == 0:
            save_as(doc, path)
    doc.FeatureManager.EnableFeatureTree = True
    doc.ForceRebuild3(False)
    save_as(doc, path)
    print(f"  patterns {made} ({time.time() - t0:.0f} s)", flush=True)
    # final check: the file holds exactly the layout's components
    have = collections.Counter(comp_state(T(c, "IComponent2")) for c in asm.GetComponents(True))
    want = collections.Counter(item_state(it) for it in items)
    missing, extra = want - have, have - want
    sw.CloseDoc(doc.GetTitle())
    close_out_docs(sw)
    ok = not missing and not extra
    print(f"{'OK  ' if ok else 'FAIL'} {os.path.basename(path)}: {sum(have.values())} components "
          f"({len(placed)} placed + {sum(have.values()) - len(placed)} from {made} patterns), "
          f"missing {sum(missing.values())}, extra {sum(extra.values())}, {time.time() - t0:.0f} s", flush=True)
    if missing:
        print("   missing e.g.", list(missing)[:2], flush=True)
    if extra:
        print("   extra e.g.", list(extra)[:2], flush=True)
    return ok


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "corner"
    if which == "corner":
        import check_corner as CC
        ok = build(CC.items(), CC.PATH)
    else:
        if os.path.exists(MB.MAIN):
            shutil.copy(MB.MAIN, MB.MAIN.replace(".sldasm", "_transforms.sldasm"))
        ok = build(MB.placements(), MB.MAIN)
    sys.exit(0 if ok else 1)
