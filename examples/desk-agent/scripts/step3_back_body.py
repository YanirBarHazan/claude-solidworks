"""Step 3: back body (prints back-down, no supports).

Walls + back, snap grooves (top: blind grooves, bottom: through windows = release access),
USB-C openings (display, Atom), PCB clamp posts with crush ribs and pin-tip holes,
Atom back support, vents, screw holes for the stand hinge block.
"""
import math
import os
import sys

import encl as E
from encl import P, v
from sw_common import connect, close_out_docs, OUT
from swcad import PartBuilder

PATH = os.path.join(OUT, "back_body.sldprt")


def build(sw, mode="build"):
    pb = PartBuilder(sw, P, path=PATH, mode=mode)
    pb.plane("PL_RIM", E.Z_IN)
    pb.plane("PL_BACK_IN", E.Z_BACK_IN)
    pb.plane("PL_POST_TOP", E.POST_TOP_Z)

    with pb.sketch("PL_RIM", "SK_OUTER") as s:
        s.rrect(0, E.CAV_CY, E.OUT_W, E.OUT_H, E.OUT_R)
    pb.extrude("SK_OUTER", f"{E.Z_IN} - {E.Z_BACK_OUT}", "BODY", reverse=True)
    with pb.sketch("PL_RIM", "SK_CAVITY") as s:
        s.rrect(0, E.CAV_CY, E.WALL_IN_W, E.WALL_IN_H, E.WALL_IN_R)
    pb.cut("SK_CAVITY", f"{E.Z_IN} - {E.Z_BACK_IN}", "CAVITY", reverse=True)

    # snap grooves: hook retaining face at zr; groove from zr+PLAY back to tip-GROOVE_TOP
    zt = v(E.LIP_TIP)
    zr = zt + P["RAMP_H"] + P["SNAP_LAND"]
    pb.plane("PL_GROOVE", f"{E.LIP_TIP} + RAMP_H + SNAP_LAND + GROOVE_PLAY")
    gdepth = "RAMP_H + SNAP_LAND + GROOVE_PLAY + GROOVE_TOP"
    with pb.sketch("PL_GROOVE", "SK_GROOVES_TOP") as s:
        for hx in ("SNAP_X_TOP", "-SNAP_X_TOP"):
            s.rect(hx, f"{E.WALL_IN_TOP} + (SNAP_U + GROOVE_CLR)/2 - 0.25", "SNAP_W + 1", "SNAP_U + GROOVE_CLR + 0.5")
    pb.cut("SK_GROOVES_TOP", gdepth, "SNAP_GROOVES_TOP", reverse=True)
    with pb.sketch("PL_GROOVE", "SK_WINDOWS_BOT") as s:      # through the bottom wall: release access
        for hx in ("SNAP_X_BOT", "-SNAP_X_BOT"):
            s.rect(hx, f"{E.WALL_IN_BOT} - WALL_T/2", "SNAP_W + 1", "WALL_T + 1")
    pb.cut("SK_WINDOWS_BOT", gdepth, "SNAP_WINDOWS_BOT", reverse=True)

    # USB-C openings
    pb.plane("PL_USB_WALL", f"{E.USB_SGN}({E.WALL_IN_W} + {E.OUT_W})/4", base="Right Plane")   # wall mid-plane
    with pb.sketch("PL_USB_WALL", "SK_USB") as s:                # Right-parallel sketch: sx = -Z, sy = Y
        s.rect(f"-{E.USB_ZC}", E.USB_Y, "PLUG_T + 2*PLUG_CLR", "PLUG_W + 2*PLUG_CLR")
    pb.cut("SK_USB", "WALL_T + 1", "USB_OPENING", mode="mid")
    pb.plane("PL_BOTTOM_OUT", E.OUT_BOT, base="Top Plane")
    with pb.sketch("PL_BOTTOM_OUT", "SK_ATOM_USB") as s:         # Top sketch: sx = X, sy = -Z
        s.rect("ATOM_X + ATOM_USB_DX", f"-{E.ATOM_USB_Z}", "ATOM_OPEN_W", "PLUG_T + 2*PLUG_CLR")
    pb.cut("SK_ATOM_USB", "WALL_T + 0.5", "ATOM_USB_OPENING", reverse=False)

    # PCB clamp posts (stop POST_GAP short; 3 crush ribs close the gap with CRUSH interference)
    with pb.sketch("PL_BACK_IN", "SK_POSTS") as s:
        for sx in (1, -1):
            for sy in (1, -1):
                s.circle(f"{sx}*{E.HOLE_X}", f"{sy}*{E.HOLE_Y}", "STAND_D")
    pb.extrude("SK_POSTS", f"{E.POST_TOP_Z} - {E.Z_BACK_IN}", "PCB_POSTS")
    with pb.sketch("PL_POST_TOP", "SK_POST_HOLES") as s:
        for sx in (1, -1):
            for sy in (1, -1):
                s.circle(f"{sx}*{E.HOLE_X}", f"{sy}*{E.HOLE_Y}", "HOLE_D - 2*PIN_CLR + 2*POST_HOLE_CLR")
    pb.cut("SK_POST_HOLES", "PIN_EXTRA + 1.5", "POST_PIN_HOLES", reverse=True)
    rr = "(STAND_D/4 + (HOLE_D - 2*PIN_CLR + 2*POST_HOLE_CLR)/4)"     # rib circle radius: mid-wall
    with pb.sketch("PL_POST_TOP", "SK_CRUSH") as s:
        for sx in (1, -1):
            for sy in (1, -1):
                for a in (90, 210, 330):
                    c, sn = math.cos(math.radians(a)), math.sin(math.radians(a))
                    s.circle(f"{sx}*{E.HOLE_X} + {rr}*({c:.9f})", f"{sy}*{E.HOLE_Y} + {rr}*({sn:.9f})", "CRUSH_D")
    pb.extrude("SK_CRUSH", "POST_GAP + CRUSH", "CRUSH_RIBS")

    # Atom back support
    with pb.sketch("PL_BACK_IN", "SK_ATOM_POST") as s:
        s.circle("ATOM_X", E.ATOM_Y, "ATOM_POST_D")
    pb.extrude("SK_ATOM_POST", f"{E.ATOM_BACK_Z} - ATOM_BACK_GAP - {E.Z_BACK_IN}", "ATOM_POST")

    # vents and hinge-block screw holes (cut through the back from inside)
    with pb.sketch("PL_BACK_IN", "SK_VENTS") as s:
        for xs in ("VENT_X1", "VENT_X2", "VENT_X3"):
            for hx in (xs, f"-{xs}"):
                s.rect(hx, "VENT_CY", "VENT_W", "VENT_L")
    pb.cut("SK_VENTS", "SHELL_BACK_T + 0.5", "VENTS", reverse=True)
    with pb.sketch("PL_BACK_IN", "SK_SCREWS") as s:
        for hx in ("HB_SCREW_X", "-HB_SCREW_X"):
            s.circle(hx, "HINGE_Y", "SCREW_HOLE_D")
    pb.cut("SK_SCREWS", "SHELL_BACK_T + 0.5", "HINGE_SCREW_HOLES", reverse=True)
    return pb


def verify(pb):
    errs = pb.rebuild_errors()
    nb = len(pb.bodies())
    lo, hi = pb.bbox()
    exp_lo = [-v(E.OUT_W) / 2, v(E.OUT_BOT), v(E.Z_BACK_OUT)]
    exp_hi = [v(E.OUT_W) / 2, v(E.OUT_BOT) + v(E.OUT_H), v(E.Z_IN)]
    print(f"[back_body] bodies={nb} errors={errs} links={len(pb.links)}")
    print(f"   bbox X[{lo[0]:.3f},{hi[0]:.3f}] Y[{lo[1]:.3f},{hi[1]:.3f}] Z[{lo[2]:.3f},{hi[2]:.3f}]")
    print(f"   volume {pb.volume() / 1000:.1f} cm3, PLA mass ~{pb.volume() * 1.24e-3:.0f} g")
    # the vents must stay clear of the hinge block footprint
    gap = P["VENT_X1"] - P["VENT_W"] / 2 - P["HB_W"] / 2
    print(f"   vent to hinge-block clearance {gap:.2f} mm")
    assert not errs and nb == 1 and gap > 0.5
    for a, b in zip(lo + hi, exp_lo + exp_hi):
        assert abs(a - b) < 1e-3, f"bbox {lo}{hi} != {exp_lo}{exp_hi}"


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
    print("STEP 3 OK")
