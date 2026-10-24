"""Step 4: LED diffuser (white/natural PLA, prints flange-down).

A bar that fills the slot in the front wall (flush with the front face) plus a flange behind
the wall that keeps it in place; the LED tops rest on the flange back face.
"""
import os
import sys

import encl as E
from encl import P, v
from sw_common import connect, close_out_docs, OUT
from swcad import PartBuilder

PATH = os.path.join(OUT, "diffuser.sldprt")


def build(sw, mode="build"):
    pb = PartBuilder(sw, P, path=PATH, mode=mode)
    pb.plane("PL_IN", E.Z_IN)
    with pb.sketch("PL_IN", "SK_BAR") as s:
        s.rect(0, E.DIFF_CY, "DIFF_W", "DIFF_H")
    pb.extrude("SK_BAR", "BEZ_T", "BAR")
    with pb.sketch("PL_IN", "SK_FLANGE") as s:
        s.rect(0, E.DIFF_FL_CY, E.DIFF_FL_W, E.DIFF_FL_H)
    pb.extrude("SK_FLANGE", "DIFF_FL_T", "FLANGE", reverse=True)
    return pb


def verify(pb):
    errs = pb.rebuild_errors()
    vol = pb.volume()
    exp = P["DIFF_W"] * P["DIFF_H"] * P["BEZ_T"] + v(E.DIFF_FL_W) * v(E.DIFF_FL_H) * P["DIFF_FL_T"]
    print(f"[diffuser] bodies={len(pb.bodies())} errors={errs} volume {vol:.2f} (expected {exp:.2f})")
    # flange must clear the LED locating pins
    pin_bottom = v(E.LED_HOLE_Y) - (P["LED_HOLE_D"] - 2 * P["PIN_CLR"]) / 2
    fl_top = v(E.DIFF_FL_CY) + v(E.DIFF_FL_H) / 2
    print(f"   flange top {fl_top:.2f}, LED pin bottom {pin_bottom:.2f} -> clearance {pin_bottom - fl_top:.2f} mm")
    assert not errs and len(pb.bodies()) == 1 and abs(vol - exp) / exp < 1e-4 and pin_bottom - fl_top > 0.2


if __name__ == "__main__":
    sw = connect()
    close_out_docs(sw)
    import partsync
    mode = partsync.decide(sw, PATH, os.path.join(os.path.dirname(os.path.abspath(__file__)), "params.py"))
    print('mode:', mode)
    shared = E.write_shared()          # before build: update mode pulls new names from it
    pb = build(sw, mode)
    verify(pb)
    if "--no-link" not in sys.argv:   # linking hung SolidWorks on 24/10 - parts keep their own globals
        pb.link_external(shared)
    print("saved", pb.save(PATH))
    print("STEP 4 OK")
