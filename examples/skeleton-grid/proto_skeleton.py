"""v2 phase 2 experiment (generic): a 3x3-bay grid of posts + beams built with DESIGN INTENT:
  - SKEL part (fixed, the only fixed component): named planes driven by its globals (H, SPAN_X, SPAN_Z)
  - seeds (one post, one beam) MATED to the skeleton planes - nothing else is fixed
  - component linear patterns whose count / spacing are driven by ASSEMBLY equations (globals N_X, N_Z, SPAN_X, SPAN_Z)
Tests: T1 positions = expected; T2 change SPAN_X in the assembly equations -> everything moves; T3 change N_X ->
instance count changes; T4 change H in the skeleton -> the beams (mated to PL_TOP) move; T5 can an assembly
equation read a skeleton dimension (single source inside SolidWorks)?; T6 save / reopen / errors + timings.
  python proto_skeleton.py            the 3x3 model + tests
  python proto_skeleton.py stress N   N individually mated seeds (3 mates each): time to mate, rebuild, save, open"""
import collections
import os
import sys
import time

import pythoncom
from win32com.client import VARIANT

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "skill", "solidworks-api", "scripts"))
CAD = os.path.join(HERE, "cad")
os.makedirs(CAD, exist_ok=True)
os.environ["SW_OUT"] = CAD
from sw_common import connect, close_out_docs, T, swconst, new_doc, save_as  # noqa: E402
from swcad import PartBuilder  # noqa: E402
from asmtools import (_mate, mate_errors, linear_pattern, set_equation, drive_pattern, component_dim_ref,
                      edit_component_equation, fix_only, settle_distance_mates)  # noqa: E402

C = swconst.constants
MM = 1e-3
P = dict(SPAN_X=4200.0, SPAN_Z=3100.0, N_X=3.0, N_Z=2.0, H=2500.0, POST_D=80.0, BEAM_B=60.0)
COINC, DIST, CLOSEST = C.swMateCOINCIDENT, C.swMateDISTANCE, C.swMateAlignCLOSEST
R_POST = ((1, 0, 0), (0, 0, -1), (0, 1, 0))       # part +Z (build direction) -> assembly +Y
R_BEAM = ((0, 1, 0), (0, 0, 1), (1, 0, 0))        # part +Z -> assembly +X
T0 = time.time()


def lap(text):
    global T0
    print(f"{time.time() - T0:7.1f} s  {text}", flush=True)
    T0 = time.time()


def F(n):
    return os.path.join(CAD, n + ".sldprt")


def build_parts(sw):
    for f in ("SKEL", "POST", "BEAM"):
        for e in ("", ".manifest.json"):
            if os.path.exists(F(f) + e):
                os.remove(F(f) + e)
    pb = PartBuilder(sw, {k: P[k] for k in ("H", "SPAN_X", "SPAN_Z")})
    pb.plane("PL_TOP", "H", base="Top Plane")
    pb.plane("PL_X1", "SPAN_X", base="Right Plane")
    pb.plane("PL_Z1", "SPAN_Z", base="Front Plane")
    pb.save(F("SKEL"))
    sw.CloseDoc(pb.doc.GetTitle())
    pb = PartBuilder(sw, {k: P[k] for k in ("H", "POST_D")})
    with pb.sketch("Front Plane", "SK_POST") as s:
        s.circle(0, 0, "POST_D")
    pb.extrude("SK_POST", "H", "POST_BODY")
    pb.save(F("POST"))
    sw.CloseDoc(pb.doc.GetTitle())
    pb = PartBuilder(sw, {k: P[k] for k in ("SPAN_X", "BEAM_B")})
    with pb.sketch("Front Plane", "SK_BEAM") as s:
        s.rect(0, 0, "BEAM_B", "BEAM_B")
    pb.extrude("SK_BEAM", "SPAN_X", "BEAM_BODY")
    pb.save(F("BEAM"))
    sw.CloseDoc(pb.doc.GetTitle())
    lap("3 parts built (SKEL planes only, POST, BEAM)")


def make_axis(doc, a, b, name):
    doc.ClearSelection2(True)
    doc.Extension.SelectByID2(a, "PLANE", 0, 0, 0, False, 0, None, 0)
    doc.Extension.SelectByID2(b, "PLANE", 0, 0, 0, True, 0, None, 0)
    doc.InsertAxis2(True)
    last, f = None, doc.FirstFeature()
    while f is not None:
        f = T(f, "IFeature")
        if f.GetTypeName2() == "RefAxis":
            last = f
        f = f.GetNextFeature()
    last.Name = name
    doc.ClearSelection2(True)
    return last


def add(sw, asm, f, axes, o):
    mu = T(sw.GetMathUtility(), "IMathUtility")
    c = T(asm.AddComponent5(f, 0, "", False, "", 0, 0, 0), "IComponent2")
    xf = [v for a in axes for v in a] + [v * MM for v in o] + [1.0, 0.0, 0.0, 0.0]
    c.Transform2 = mu.CreateTransform(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, xf))
    return c


def origins(asm):
    out = collections.Counter()
    for c in asm.GetComponents(True) or []:
        c = T(c, "IComponent2")
        if c.GetSuppression2() == 0:
            continue
        d = list(T(c.Transform2, "IMathTransform").ArrayData)
        out[(os.path.splitext(os.path.basename(c.GetPathName()))[0],) + tuple(round(v / MM, 2) for v in d[9:12])] += 1
    return out


def expected(sx, sz, nx, nz, h):
    out = collections.Counter({("SKEL", 0.0, 0.0, 0.0): 1})
    for i in range(nx + 1):
        for j in range(nz + 1):
            out[("POST", round(i * sx, 2), 0.0, round(j * sz, 2))] += 1
    for i in range(nx):
        for j in range(nz + 1):
            out[("BEAM", round(i * sx, 2), round(h, 2), round(j * sz, 2))] += 1
    return out


def check(asm, tag, sx, sz, nx, nz, h):
    have, want = origins(asm), expected(sx, sz, nx, nz, h)
    miss, extra = want - have, have - want
    ok = not miss and not extra
    print(f"{'OK  ' if ok else 'FAIL'} {tag}: {sum(have.values())} components, missing {sum(miss.values())}, "
          f"extra {sum(extra.values())}" + ("" if ok else f"  e.g. want {list(miss)[:2]} have {list(extra)[:2]}"), flush=True)
    return ok


def dims_of(feat):
    out = []
    d = feat.GetFirstDisplayDimension()
    while d is not None:
        dd = T(T(d, "IDisplayDimension").GetDimension2(0), "IDimension")
        out.append((dd.FullName, dd.GetSystemValue3(C.swThisConfiguration, None)[0]
                    if isinstance(dd.GetSystemValue3(C.swThisConfiguration, None), tuple) else dd.SystemValue))
        d = feat.GetNextDisplayDimension(d)
    return out


def set_eq(eq, name, text):
    """Add or replace the equation whose left side is "name"."""
    for i in range(eq.GetCount()):
        if eq.Equation(i).split("=")[0].strip() == f'"{name}"':
            eq.SetEquation(i, f'"{name}" = {text}')
            return i
    r = eq.Add2(-1, f'"{name}" = {text}', True)
    if r < 0:
        raise RuntimeError(f'equation rejected: "{name}" = {text}')
    return r


def rebuild(doc):
    t = time.time()
    doc.ForceRebuild3(False)
    return time.time() - t


def main():
    sw = connect()
    close_out_docs(sw)
    build_parts(sw)
    sx, sz, nx, nz, h = P["SPAN_X"], P["SPAN_Z"], int(P["N_X"]), int(P["N_Z"]), P["H"]
    path = os.path.join(CAD, "GRID.sldasm")
    if os.path.exists(path):
        os.remove(path)
    for f in ("SKEL", "POST", "BEAM"):
        sw.OpenDoc6(F(f), C.swDocPART, C.swOpenDocOptions_Silent, "", 0, 0)
    doc = new_doc(sw, "asm")
    asm = T(doc, "IAssemblyDoc")
    sw.ActivateDoc3(doc.GetTitle(), False, 0, 0)
    skel = add(sw, asm, F("SKEL"), ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (0, 0, 0))
    doc.ClearSelection2(True)
    skel.Select4(False, None, False)
    asm.FixComponent()                                    # the ONLY fixed component
    post = add(sw, asm, F("POST"), R_POST, (0, 0, 0))
    beam = add(sw, asm, F("BEAM"), R_BEAM, (0, h, 0))
    save_as(doc, path)
    A = "GRID"
    sk, po, be = skel.Name2, post.Name2, beam.Name2
    for a, b in ((f"Front Plane@{po}@{A}", f"Top Plane@{sk}@{A}"), (f"Right Plane@{po}@{A}", f"Right Plane@{sk}@{A}"),
                 (f"Top Plane@{po}@{A}", f"Front Plane@{sk}@{A}"),
                 (f"Front Plane@{be}@{A}", f"Right Plane@{sk}@{A}"), (f"Top Plane@{be}@{A}", f"Front Plane@{sk}@{A}"),
                 (f"Right Plane@{be}@{A}", f"PL_TOP@{sk}@{A}")):
        _mate(doc, COINC, CLOSEST, [(a, "PLANE"), (b, "PLANE")])
    ax_x = make_axis(doc, "Top Plane", "Front Plane", "AX_X")
    ax_z = make_axis(doc, "Top Plane", "Right Plane", "AX_Z")
    pp = linear_pattern(doc, [post], ax_x, nx + 1, sx, ax_z, nz + 1, sz, flip1=True, flip2=False, name="PAT_POSTS")
    pbm = linear_pattern(doc, [beam], ax_x, nx, sx, ax_z, nz + 1, sz, flip1=True, flip2=False, name="PAT_BEAMS")
    doc.ForceRebuild3(False)
    lap("assembly: skeleton fixed, 2 seeds with 6 mates, 2 patterns")
    ok = check(asm, "T1 positions after build", sx, sz, nx, nz, h)
    errs = mate_errors(doc)
    print(f"{'OK  ' if not errs else 'FAIL'} T1 mate errors {errs}", flush=True)

    # ---- pattern dimensions -> assembly equations
    pd, bd = dims_of(pp), dims_of(pbm)
    print("   PAT_POSTS dims:", [(n, round(v, 4)) for n, v in pd], flush=True)
    eq = T(doc.GetEquationMgr(), "IEquationMgr")
    for k, v in (("SPAN_X", sx), ("SPAN_Z", sz), ("N_X", nx), ("N_Z", nz)):
        set_eq(eq, k, f"{v:g}")

    drive_pattern(doc, pp, n1='"N_X" + 1', s1='"SPAN_X"', n2='"N_Z" + 1', s2='"SPAN_Z"')
    drive_pattern(doc, pbm, n1='"N_X"', s1='"SPAN_X"', n2='"N_Z" + 1', s2='"SPAN_Z"')
    m1 = m2 = "library drive_pattern"
    print(f"   equations: posts {m1}; beams {m2}", flush=True)
    eq.EvaluateAll()
    t = rebuild(doc)
    ok = check(asm, f"T1b positions with equations (rebuild {t:.1f} s)", sx, sz, nx, nz, h) and ok

    cur = dict(sx=sx, sz=sz, nx=nx, nz=nz, h=h)

    def trial(tag, key, new, apply):
        old = cur[key]
        apply(new)
        t = rebuild(doc)
        exp = dict(cur, **{key: new})
        good = check(asm, f"{tag} (rebuild {t:.1f} s)", exp["sx"], exp["sz"], exp["nx"], exp["nz"], exp["h"])
        if good:
            cur[key] = new
        else:
            apply(old)
            rebuild(doc)
        return good

    def asm_eq(name):
        def f(v):
            set_eq(eq, name, f"{v:g}")
            eq.EvaluateAll()
        return f
    t2 = trial("T2 SPAN_X 4200 -> 5000 in the assembly equations", "sx", 5000.0, asm_eq("SPAN_X"))
    t3 = trial("T3 N_X 3 -> 5 in the assembly equations (instance count)", "nx", 5, asm_eq("N_X"))
    sdoc = T(skel.GetModelDoc2(), "IModelDoc2")
    seq = T(sdoc.GetEquationMgr(), "IEquationMgr")

    def plane_dim(name):
        f = sdoc.FirstFeature()
        while f is not None:
            f = T(f, "IFeature")
            if f.Name == name:
                return dims_of(f)[0]
            f = f.GetNextFeature()

    def skel_eq(name):
        def f(v):
            edit_component_equation(sw, doc, skel, name, f"{v:g}")
        return f
    t4 = trial("T4 H 2500 -> 3000 in the SKELETON part (beams mated to PL_TOP)", "h", 3000.0, skel_eq("H"))
    print(f"   skeleton PL_TOP dimension now {plane_dim('PL_TOP')}", flush=True)
    # ---- T5: assembly equation reading a skeleton dimension (single source inside SolidWorks)
    ref = component_dim_ref(skel, "PL_Z1")
    set_equation(doc, "SPAN_Z", ref)
    t5 = trial(f"T5 SPAN_Z 3100 -> 3600 in the SKELETON, assembly reads {ref}", "sz", 3600.0, skel_eq("SPAN_Z"))
    if not t5:
        set_eq(eq, "SPAN_Z", f"{cur['sz']:g}")
        eq.EvaluateAll()
        rebuild(doc)
    # ---- T6: save, reopen, errors, timings
    t = time.time()
    save_as(doc, path)
    ts = time.time() - t
    sdoc.Save3(1, 0, 0)
    sw.CloseDoc(doc.GetTitle())
    close_out_docs(sw)
    t = time.time()
    r = sw.OpenDoc6(path, C.swDocASSEMBLY, C.swOpenDocOptions_Silent, "", 0, 0)
    d2 = T(r[0], "IModelDoc2")
    to = time.time() - t
    tr = rebuild(d2)
    e2 = mate_errors(d2)
    t6 = check(T(d2, "IAssemblyDoc"), f"T6 after save {ts:.1f} s / reopen {to:.1f} s / rebuild {tr:.1f} s, mate errors {e2}",
               cur["sx"], cur["sz"], cur["nx"], cur["nz"], cur["h"]) and not e2
    sw.CloseDoc(d2.GetTitle())
    close_out_docs(sw)
    res = dict(T1=ok, T2=t2, T3=t3, T4=t4, T5=t5, T6=t6)
    print(f"PROTO {'OK' if all(v for k, v in res.items() if k != 'T5') else 'FAIL'} {res}", flush=True)


def stress(n):
    """n posts, each mated to the skeleton with 1 coincident + 2 distance mates (no patterns): solver load."""
    sw = connect()
    close_out_docs(sw)
    if not os.path.exists(F("POST")):
        build_parts(sw)
    path = os.path.join(CAD, f"STRESS_{n}.sldasm")
    if os.path.exists(path):
        os.remove(path)
    for f in ("SKEL", "POST"):
        sw.OpenDoc6(F(f), C.swDocPART, C.swOpenDocOptions_Silent, "", 0, 0)
    doc = new_doc(sw, "asm")
    asm = T(doc, "IAssemblyDoc")
    sw.ActivateDoc3(doc.GetTitle(), False, 0, 0)
    skel = add(sw, asm, F("SKEL"), ((1, 0, 0), (0, 1, 0), (0, 0, 1)), (0, 0, 0))
    skel.Select4(False, None, False)
    asm.FixComponent()
    side = int(n ** 0.5 + 0.999)
    want, comps = [], []
    for k in range(n):
        o = (1000.0 * (1 + k % side), 0.0, 1000.0 * (1 + k // side))
        comps.append(add(sw, asm, F("POST"), R_POST, o))
        want.append(o)
    save_as(doc, path)
    A, sk = f"STRESS_{n}", skel.Name2
    lap(f"stress {n}: components added")
    doc.FeatureManager.EnableFeatureTree = False
    t = time.time()
    for c, o in zip(comps, want):
        po = c.Name2
        _mate(doc, COINC, CLOSEST, [(f"Front Plane@{po}@{A}", "PLANE"), (f"Top Plane@{sk}@{A}", "PLANE")])
        _mate(doc, DIST, CLOSEST, [(f"Right Plane@{po}@{A}", "PLANE"), (f"Right Plane@{sk}@{A}", "PLANE")], dist=o[0])
        _mate(doc, DIST, CLOSEST, [(f"Top Plane@{po}@{A}", "PLANE"), (f"Front Plane@{sk}@{A}", "PLANE")], dist=o[2])
    doc.FeatureManager.EnableFeatureTree = True
    tm = time.time() - t
    tr = rebuild(doc)
    off = 0
    for c, o in zip(comps, want):
        d = list(T(c.Transform2, "IMathTransform").ArrayData)
        off += max(abs(d[9 + i] / MM - o[i]) for i in range(3)) > 0.01
    t = time.time()
    save_as(doc, path)
    ts = time.time() - t
    sw.CloseDoc(doc.GetTitle())
    close_out_docs(sw)
    t = time.time()
    d2 = T(sw.OpenDoc6(path, C.swDocASSEMBLY, C.swOpenDocOptions_Silent, "", 0, 0)[0], "IModelDoc2")
    to = time.time() - t
    tr2 = rebuild(d2)
    errs = mate_errors(d2)
    sw.CloseDoc(d2.GetTitle())
    close_out_docs(sw)
    print(f"STRESS {n} mated seeds, {3 * n} mates: mating {tm:.0f} s ({tm / (3 * n):.2f} s/mate), rebuild {tr:.1f} s, "
          f"save {ts:.1f} s, open {to:.1f} s, rebuild after open {tr2:.1f} s, wrong side {off}, mate errors {len(errs)}",
          flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "stress":
        stress(int(sys.argv[2]))
    else:
        main()
