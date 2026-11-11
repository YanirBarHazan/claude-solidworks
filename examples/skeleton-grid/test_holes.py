"""Small live test: Hole Wizard hole + feature linear pattern + mirror in a part, all driven by globals.
Plate L x W x T; one ISO M10 clearance hole (d 11, through) at (EDGE, ROW); patterned N_HOLES times along X at PITCH;
hole + pattern mirrored about the mid plane -> 2 rows. Proof: volume = plate - 2 * N_HOLES holes, every sketch
fully defined, edit test on the COUNT (N_HOLES 5 -> 4) and on PITCH."""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "skill", "solidworks-api", "scripts"))
CAD = os.path.join(HERE, "cad")
os.environ["SW_OUT"] = CAD
from sw_common import connect, close_out_docs  # noqa: E402
from swcad import PartBuilder  # noqa: E402

P = dict(L=200.0, W=100.0, T=10.0, EDGE=20.0, ROW=25.0, HOLE_D=11.0, N_HOLES=5.0, PITCH=35.0)
path = os.path.join(CAD, "PLATE_HOLES.sldprt")
for e in ("", ".manifest.json"):
    if os.path.exists(path + e):
        os.remove(path + e)


def expect(p):
    holes = 2 * round(p["N_HOLES"]) * math.pi * (p["HOLE_D"] / 2) ** 2 * p["T"]
    return (p["L"], p["W"], p["T"]), p["L"] * p["W"] * p["T"] - holes


sw = connect()
close_out_docs(sw)
pb = PartBuilder(sw, P)
with pb.sketch("Front Plane", "SK_PLATE") as s:
    s.rect("L/2", "W/2", "L", "W")
pb.extrude("SK_PLATE", "T", "PLATE_BODY")
with pb.sketch("Front Plane", "SK_HOLE_POS") as s:
    s.point("EDGE", "ROW")
pb.plane("PL_MID", "W/2", base="Top Plane")
step = "hole wizard"
try:
    pb.hole_wizard("HOLE_M10", "SK_HOLE_POS", ("EDGE", "ROW", "T"), "M10", "HOLE_D", kind="clearance")
    print("OK   Hole Wizard hole created and tied to the position sketch")
    step = "pattern"
    pb.pattern_linear("PAT_HOLES", ["HOLE_M10"], "Right Plane", "N_HOLES", "PITCH")
    print("OK   linear pattern created, count and spacing linked")
    step = "mirror"
    pb.mirror("MIR_ROW", ["HOLE_M10", "PAT_HOLES"], "PL_MID")
    print("OK   mirror created")
    step = "verify"
    res = pb.verify(expect, edit=("N_HOLES", 4.0))
    print(f"OK   verify: bbox {[round(v, 3) for v in res['bbox']]}, volume {res['volume']:.1f} = plate - 10 holes "
          f"({expect(P)[1]:.1f}); edit N_HOLES 5 -> 4 ok; open sketches {pb.open_sketches()}")
    pb.verify(expect, edit=("PITCH", 30.0))
    print("OK   edit PITCH 35 -> 30 ok")
    step = "save"
    pb.save(path)
    print("OK   saved, reopened, 0 errors")
except Exception as ex:
    print(f"FAIL at {step}: {str(ex)[:300]}")
    try:
        print(f"     state: errors {pb.rebuild_errors()}, volume {pb.volume():.1f} (plate {P['L'] * P['W'] * P['T']:.1f}), "
              f"open sketches {pb.open_sketches()}")
    except Exception as ex2:
        print("     (state unavailable)", str(ex2)[:100])
sw.CloseDoc(pb.doc.GetTitle())
close_out_docs(sw)
