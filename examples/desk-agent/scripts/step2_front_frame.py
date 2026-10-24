"""Step 2: front frame (prints face down).

Front plate with screen window, diffuser slot, Atom window and thinned radar window;
lip that slides into the back body with 4 snap hooks; PCB standoffs + locating pins;
LED stick locating pins; radar pocket ribs; Atom cradle ribs; USB-C openings in the lip.
"""
import os
import sys

import encl as E
from encl import P, v
from sw_common import connect, close_out_docs, OUT
from swcad import PartBuilder

PATH = os.path.join(OUT, "front_frame.sldprt")


def build(sw, mode="build"):
    pb = PartBuilder(sw, P, path=PATH, mode=mode)
    pb.plane("PL_IN", E.Z_IN)
    pb.plane("PL_TIP", E.LIP_TIP)

    # plate
    with pb.sketch("PL_IN", "SK_PLATE") as s:
        s.rrect(0, E.CAV_CY, E.OUT_W, E.OUT_H, E.OUT_R)
    pb.extrude("SK_PLATE", "BEZ_T", "FRONT_PLATE")
    with pb.sketch("PL_IN", "SK_WINDOW") as s:
        s.rect(0, E.VA_CY, E.WIN_W, E.WIN_H)
    pb.cut("SK_WINDOW", "BEZ_T", "SCREEN_WINDOW", reverse=False)
    with pb.sketch("PL_IN", "SK_ATOM_WIN") as s:
        s.rect("ATOM_X", E.ATOM_Y, "ATOM_W + 2*ATOM_CLR", "ATOM_H + 2*ATOM_CLR")
    pb.cut("SK_ATOM_WIN", "BEZ_T", "ATOM_WINDOW", reverse=False)
    with pb.sketch("PL_IN", "SK_DIFF_SLOT") as s:
        s.rect(0, E.DIFF_CY, "DIFF_W + 2*DIFF_CLR", "DIFF_H + 2*DIFF_CLR")
    pb.cut("SK_DIFF_SLOT", "BEZ_T", "DIFFUSER_SLOT", reverse=False)
    with pb.sketch("PL_IN", "SK_RADAR_POCKET") as s:
        s.rect("RADAR_X", E.RADAR_Y, "RAD_W + 2*RAD_CLR", "RAD_H + 2*RAD_CLR")
    pb.cut("SK_RADAR_POCKET", "BEZ_T - RAD_WIN_T", "RADAR_THIN_WALL", reverse=False)

    # lip: outer body, then hollow it (separate sketches -> no merged corner points)
    with pb.sketch("PL_IN", "SK_LIP_OUT") as s:
        s.rrect(0, E.CAV_CY, E.LIP_OUT_W, E.LIP_OUT_H, E.LIP_OUT_R)
    pb.extrude("SK_LIP_OUT", "LIP_H", "LIP", reverse=True)
    with pb.sketch("PL_IN", "SK_LIP_IN") as s:
        s.rrect(0, E.CAV_CY, E.CAV_W, E.CAV_H, "LIP_IN_R")
    pb.cut("SK_LIP_IN", "LIP_H", "LIP_HOLLOW", reverse=True)

    # PCB standoffs + locating pins
    with pb.sketch("PL_IN", "SK_STANDOFFS") as s:
        for sx in (1, -1):
            for sy in (1, -1):
                s.circle(f"{sx}*{E.HOLE_X}", f"{sy}*{E.HOLE_Y}", "STAND_D")
    pb.extrude("SK_STANDOFFS", E.Z_IN, "PCB_STANDOFFS", reverse=True)
    with pb.sketch("Front Plane", "SK_PCB_PINS") as s:
        for sx in (1, -1):
            for sy in (1, -1):
                s.circle(f"{sx}*{E.HOLE_X}", f"{sy}*{E.HOLE_Y}", "HOLE_D - 2*PIN_CLR")
    pb.extrude("SK_PCB_PINS", "PCB_T + PIN_EXTRA", "PCB_PINS", reverse=True)

    # LED stick locating pins (LED tops rest on the diffuser flange)
    with pb.sketch("PL_IN", "SK_LED_PINS") as s:
        for sx in (1, -1):
            s.circle(f"{sx}*{E.LED_HOLE_X}", E.LED_HOLE_Y, "LED_HOLE_D - 2*PIN_CLR")
    pb.extrude("SK_LED_PINS", "DIFF_FL_T + LED_T + LED_PCB_T + LEDPIN_EXTRA", "LED_PINS", reverse=True)

    # radar pocket ribs (ring)
    with pb.sketch("PL_IN", "SK_RADAR_RIB_OUT") as s:
        s.rect("RADAR_X", E.RADAR_Y, "RAD_W + 2*RAD_CLR + 2*RIB_T", "RAD_H + 2*RAD_CLR + 2*RIB_T")
    pb.extrude("SK_RADAR_RIB_OUT", "RAD_RIB_H", "RADAR_RIBS", reverse=True)
    with pb.sketch("PL_IN", "SK_RADAR_RIB_IN") as s:
        s.rect("RADAR_X", E.RADAR_Y, "RAD_W + 2*RAD_CLR", "RAD_H + 2*RAD_CLR")
    pb.cut("SK_RADAR_RIB_IN", "RAD_RIB_H", "RADAR_RIBS_HOLLOW", reverse=True)

    # Atom cradle: side ribs only (the PCB edge is right above it, its plugs are below it)
    with pb.sketch("PL_IN", "SK_ATOM_RIBS") as s:
        for sx in (1, -1):
            s.rect(f"ATOM_X + {sx}*(ATOM_W/2 + ATOM_CLR + RIB_T/2)", E.ATOM_Y, "RIB_T", "ATOM_H + 2*ATOM_CLR")
    pb.extrude("SK_ATOM_RIBS", "ATOM_RIB_D", "ATOM_RIBS", reverse=True)

    # snap tongues: slits from the lip tip
    with pb.sketch("PL_TIP", "SK_SLITS") as s:
        for xs, yc in (("SNAP_X_TOP", f"{E.CAV_TOP} + LIP_T/2"), ("SNAP_X_BOT", f"{E.CAV_BOT} - LIP_T/2")):
            for hx in (xs, f"-{xs}"):
                for side in (1, -1):
                    s.rect(f"{hx} + {side}*(SNAP_W/2 + SLIT_W/2)", yc, "SLIT_W", "LIP_T + 1")
    pb.cut("SK_SLITS", "SNAP_L", "SNAP_SLITS", reverse=False)
    # hooks (profile in the Y-Z plane; Right-plane sketch: sx = -Z, sy = Y)
    zt = v(E.LIP_TIP)
    for top, xs in ((True, "SNAP_X_TOP"), (False, "SNAP_X_BOT")):
        prof, _ = E.hook_profile(top, P["SNAP_U"], P["RAMP_H"], P["SNAP_LAND"], zt)
        for sgn in (1, -1):
            tag = f"{'TOP' if top else 'BOT'}{'R' if sgn > 0 else 'L'}"
            pb.plane(f"PL_HOOK_{tag}", f"{sgn}*{xs} - SNAP_W/2", base="Right Plane")
            with pb.sketch(f"PL_HOOK_{tag}", f"SK_HOOK_{tag}") as s:
                s.polygon([(-z, y) for y, z in prof])
            pb.extrude(f"SK_HOOK_{tag}", "SNAP_W", f"HOOK_{tag}")

    # USB-C opening in the right lip (display plug)
    pb.plane("PL_USB", f"{E.USB_SGN}({E.CAV_HW} + LIP_T/2)", base="Right Plane")   # lip mid-plane, USB side
    with pb.sketch("PL_USB", "SK_USB") as s:
        s.rect(f"-{E.USB_ZC}", E.USB_Y, "PLUG_T + 2*PLUG_CLR", "PLUG_W + 2*PLUG_CLR")
    pb.cut("SK_USB", "LIP_T + 1", "USB_OPENING_LIP", mode="mid")
    # Atom USB-C opening in the bottom lip (Top-plane sketch: sx = X, sy = -Z)
    pb.plane("PL_BOT_LIP", f"{E.CAV_BOT} - LIP_T", base="Top Plane")
    with pb.sketch("PL_BOT_LIP", "SK_ATOM_USB") as s:
        s.rect("ATOM_X + ATOM_USB_DX", f"-{E.ATOM_USB_Z}", "ATOM_OPEN_W", "PLUG_T + 2*PLUG_CLR")
    pb.cut("SK_ATOM_USB", "LIP_T + 0.5", "ATOM_USB_OPENING_LIP", reverse=False)

    # Atom front stop: a thin rim inside the window, over the edge of the Atom face
    pb.plane("PL_ATOM_FACE", E.ATOM_FACE_Z)
    with pb.sketch("PL_ATOM_FACE", "SK_ATOM_STOP") as s:
        s.rect("ATOM_X", E.ATOM_Y, "ATOM_W + 2*ATOM_CLR", "ATOM_H + 2*ATOM_CLR")
    pb.extrude("SK_ATOM_STOP", "ATOM_LIP_T", "ATOM_STOP")
    with pb.sketch("PL_ATOM_FACE", "SK_ATOM_STOP_IN") as s:
        s.rect("ATOM_X", E.ATOM_Y, "ATOM_W - 2*ATOM_LIP", "ATOM_H - 2*ATOM_LIP")
    pb.cut("SK_ATOM_STOP_IN", "ATOM_LIP_T", "ATOM_STOP_OPENING", reverse=False)

    # notch in the USB-side lip for the P1 wires (P2/P4 plugs exit into the chin, no notch needed)
    with pb.sketch("PL_TIP", "SK_CABLE_P1") as s:
        s.rect(f"{E.USB_SGN}({E.CAV_HW} + LIP_T/2)", "P1_Y", "LIP_T + 1", "P1_NW")
    pb.cut("SK_CABLE_P1", f"-(PCB_T - CBL_FRONT) - {E.LIP_TIP}", "CABLE_NOTCH_P1", reverse=False)
    return pb


def verify(pb):
    errs = pb.rebuild_errors()
    nb = len(pb.bodies())
    lo, hi = pb.bbox()
    exp_lo = [-v(E.OUT_W) / 2, v(E.CAV_CY) - v(E.OUT_H) / 2, v(E.LIP_TIP)]
    exp_hi = [v(E.OUT_W) / 2, v(E.CAV_CY) + v(E.OUT_H) / 2, v(E.Z_OUT)]
    print(f"[front_frame] bodies={nb} errors={errs} links={len(pb.links)}")
    print(f"   bbox X[{lo[0]:.3f},{hi[0]:.3f}] Y[{lo[1]:.3f},{hi[1]:.3f}] Z[{lo[2]:.3f},{hi[2]:.3f}]")
    print(f"   volume {pb.volume() / 1000:.1f} cm3, PLA mass ~{pb.volume() * 1.24e-3:.0f} g")
    assert not errs and nb == 1
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
    print("STEP 2 OK")
