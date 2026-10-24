"""End-to-end self test against the running SolidWorks: build a plate with a rounded outline, an inner
pocket, an offset hole and an off-centre boss; verify volume/bbox; edit parameters; save+reopen;
two-part assembly interference; STL export + orientation + overhang check. Prints SMOKE TEST OK.
Writes only to a temporary folder.
"""
import math
import os
import sys
import tempfile

OUT_DIR = tempfile.mkdtemp(prefix="sw_smoke_")
os.environ["SW_OUT"] = OUT_DIR
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sw_common import connect, close_out_docs  # noqa: E402
from swcad import PartBuilder  # noqa: E402
from asmtools import place, check_interference, export_stl, stl_bbox, IDENT  # noqa: E402
from orient_stl import orient, ROT  # noqa: E402
from overhangs import regions  # noqa: E402


def plate_volume(W, H, T, R, IW, IH, IR, PD, HD, BD, BH):
    rr = lambda w, h, r: w * h - (4 - math.pi) * r * r
    return (rr(W, H, R) - rr(IW, IH, IR)) * T - math.pi * (HD / 2) ** 2 * T + math.pi * (BD / 2) ** 2 * BH


def main():
    sw = connect()
    print("SolidWorks", sw.RevisionNumber(), "| output", OUT_DIR)
    close_out_docs(sw)
    p = dict(W=60.0, H=40.0, T=3.0, R=4.0, IW=30.0, IH=16.0, IR=1.0, OFF=0.25, HD=3.2, HX=22.0, BD=6.0, BH=5.0, BX=-20.0)
    pb = PartBuilder(sw, p)
    with pb.sketch("Front Plane", "SK_OUT") as s:
        s.rrect(0, "-OFF", "W", "H", "R")
    pb.extrude("SK_OUT", "T", "PLATE")
    with pb.sketch("Front Plane", "SK_IN") as s:
        s.rrect(0, "-OFF", "IW", "IH", "IR")
    pb.cut("SK_IN", "T", "WINDOW", reverse=False)
    with pb.sketch("Front Plane", "SK_HOLE") as s:
        s.circle("HX", "-OFF", "HD")
    pb.cut("SK_HOLE", "T", "HOLE", reverse=False)
    pb.plane("PL_TOP", "T")
    with pb.sketch("PL_TOP", "SK_BOSS") as s:
        s.circle("BX", 10, "BD")
    pb.extrude("SK_BOSS", "BH", "BOSS")

    vol = lambda: plate_volume(*(pb.params[k] for k in ("W", "H", "T", "R", "IW", "IH", "IR")), 0,
                               pb.params["HD"], pb.params["BD"], pb.params["BH"])
    errs = pb.rebuild_errors()
    lo, hi = pb.bbox()
    print(f"part: errors={errs} bodies={len(pb.bodies())} volume {pb.volume():.3f} (expected {vol():.3f}) "
          f"bbox Y[{lo[1]:.3f},{hi[1]:.3f}]")
    assert not errs and len(pb.bodies()) == 1
    assert abs(pb.volume() - vol()) < 1e-3 and abs(lo[1] + 20.25) < 1e-6 and abs(hi[1] - 19.75) < 1e-6
    for k, val in (("R", 6.0), ("W", 70.0), ("IR", 2.5), ("H", 46.0), ("OFF", 1.0)):
        pb.set_param(k, val)
        lo, hi = pb.bbox()
        ok = abs(pb.volume() - vol()) < 1e-3 and abs((lo[1] + hi[1]) / 2 + pb.params["OFF"]) < 1e-6 \
            and not pb.rebuild_errors()
        print(f"   edit {k}={val}: volume {pb.volume():.3f} vs {vol():.3f}, centred={ok}")
        assert ok, f"edit test failed for {k}"
    part = pb.save(os.path.join(OUT_DIR, "smoke_plate.sldprt"))

    pin = PartBuilder(sw, {"D": 5.9, "L": 4.0})
    pin.plane("PL", 3.0)
    with pin.sketch("PL", "SK") as s:
        s.circle(-20.0, 10.0, "D")
    pin.extrude("SK", "L", "PIN")
    pin_path = pin.save(os.path.join(OUT_DIR, "smoke_pin.sldprt"))
    doc, asm, _ = place(sw, [(part, IDENT, (0, 0, 0)), (pin_path, IDENT, (0, 0, 0))],
                        os.path.join(OUT_DIR, "smoke.sldasm"))
    exp = math.pi * (5.9 / 2) ** 2 * 4.0           # pin fully inside the boss = designed overlap
    assert not check_interference(asm, {frozenset({"smoke_plate", "smoke_pin"}): exp})

    stl = os.path.join(OUT_DIR, "smoke_plate.stl")
    assert export_stl(sw, part, stl)
    lo, hi, n = stl_bbox(stl)
    flipped = os.path.join(OUT_DIR, "smoke_plate_flipped.stl")
    orient(stl, flipped, ROT["flip_x"])
    up, down = regions(stl), regions(flipped)
    print(f"stl {n} triangles {hi[0]-lo[0]:.1f} x {hi[1]-lo[1]:.1f} x {hi[2]-lo[2]:.1f}; "
          f"overhang regions plate-down={len(up)}, flipped={len(down)}")
    assert len(up) == 0 and len(down) >= 1      # flipped, the plate hangs off the boss
    print("SMOKE TEST OK")


if __name__ == "__main__":
    main()
