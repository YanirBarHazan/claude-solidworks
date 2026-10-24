"""Step 1: print-test coupons. Run: python step1_coupons.py [A|B|C|all]

A  snap joint   : front-frame lip with two hooks (90 deg = permanent, 45 deg = releasable) + wall with grooves
B  PCB frame    : front plate with window, 4 standoffs + locating pins at the real hole pattern,
                  and the side wall with the USB-C plug opening, all in the display frame
C  hinge detent : base with knuckles and a flexing detent arm, leg stub with notched wheel, pin

Each part: no rebuild errors, volume = hand calculation, single body. Each coupon is also
assembled and interference-checked; then STL files are written for the printer.
"""
import math
import os
import sys

import params as PR
from asmtools import place, check_interference, picture, export_stl, stl_bbox, IDENT
from sw_common import connect, close_out_docs, OUT
from swcad import PartBuilder

PI = math.pi
F = PR.FIT
STL_DIR = os.path.join(os.path.dirname(OUT), "stl")
os.makedirs(STL_DIR, exist_ok=True)


def verify(pb, name, vol_exp, tol=1e-4):
    errs = pb.rebuild_errors()
    vol = pb.volume()
    nb = len(pb.bodies())
    print(f"[{name}] bodies={nb} errors={errs} volume {vol:.2f} (expected {vol_exp:.2f}) linked dims={len(pb.links)}")
    assert not errs and nb == 1, (errs, nb)
    assert abs(vol - vol_exp) / vol_exp < tol, "volume mismatch"


# ---------------------------------------------------------------- A: snap
A = dict(CPN_L=40.0, LIP_H=14.0, WALL_H=16.0, TOP_T=2.0, TOP_W=12.0, PLATE_W=12.0, HOOK_X=10.0)


def coupon_a(sw):
    p = {**F, **A}
    v = p
    # frame: X along the joint, Y outward (+Y = outside), Z into the enclosure, front face at Z=0
    lip = PartBuilder(sw, p)
    lip.plane("PL_BEZ", "BEZ_T")
    lip.plane("PL_LIPTOP", "BEZ_T + LIP_H")
    with lip.sketch("Front Plane", "SK_PLATE") as s:
        s.rect(0, "-PLATE_W/2", "CPN_L", "PLATE_W")
    lip.extrude("SK_PLATE", "BEZ_T", "PLATE")
    lip_cy = "-(WALL_T + LIP_CLR + LIP_T/2)"
    with lip.sketch("PL_BEZ", "SK_LIP") as s:
        s.rect(0, lip_cy, "CPN_L", "LIP_T")
    lip.extrude("SK_LIP", "LIP_H", "LIP")
    with lip.sketch("PL_LIPTOP", "SK_SLITS") as s:
        for hx in ("HOOK_X", "-HOOK_X"):
            for side in (1, -1):
                s.rect(f"{hx} + {side}*(SNAP_W/2 + SLIT_W/2)", lip_cy, "SLIT_W", "LIP_T + 1")
    lip.cut("SK_SLITS", "SNAP_L", "SLITS", reverse=True)
    # hook profiles in the Y-Z plane (Right-plane sketch: sx = -Z, sy = Y)
    y_hi = -(v["WALL_T"] + v["LIP_CLR"])
    top = v["BEZ_T"] + v["LIP_H"]
    U, RH, LAND = v["SNAP_U"], v["RAMP_H"], v["SNAP_LAND"]
    z_ret = top - RH - LAND
    prof = {
        "H90": [(y_hi - 0.2, top), (y_hi, top), (y_hi + U, top - RH), (y_hi + U, z_ret), (y_hi - 0.2, z_ret)],
        "H45": [(y_hi - 0.2, top), (y_hi, top), (y_hi + U, top - RH), (y_hi + U, z_ret), (y_hi, z_ret - U),
                (y_hi - 0.2, z_ret - U)],
    }
    for name, x0 in (("H90", "HOOK_X - SNAP_W/2"), ("H45", "-HOOK_X - SNAP_W/2")):
        lip.plane(f"PL_{name}", x0, base="Right Plane")
        with lip.sketch(f"PL_{name}", f"SK_{name}") as s:
            s.polygon([(-z, y) for y, z in prof[name]])
        lip.extrude(f"SK_{name}", "SNAP_W", f"HOOK_{name}")
    hook_area90 = U * RH / 2 + U * LAND
    hook_area45 = hook_area90 + U * U / 2
    vol = (v["CPN_L"] * v["PLATE_W"] * v["BEZ_T"] + v["CPN_L"] * v["LIP_T"] * v["LIP_H"]
           - 4 * v["SLIT_W"] * v["LIP_T"] * v["SNAP_L"] + (hook_area90 + hook_area45) * v["SNAP_W"])
    verify(lip, "A_lip", vol)
    p_lip = lip.save(os.path.join(OUT, "test_A_lip.sldprt"))

    wall = PartBuilder(sw, p)
    wall.plane("PL_BEZ", "BEZ_T")
    wall.plane("PL_TOP", "BEZ_T + WALL_H")
    wall.plane("PL_G90", "BEZ_T + LIP_H - RAMP_H - SNAP_LAND - GROOVE_PLAY")
    wall.plane("PL_G45", "BEZ_T + LIP_H - RAMP_H - SNAP_LAND - SNAP_U - GROOVE_PLAY")
    with wall.sketch("PL_BEZ", "SK_WALL") as s:
        s.rect(0, "-WALL_T/2", "CPN_L", "WALL_T")
    wall.extrude("SK_WALL", "WALL_H", "WALL")
    with wall.sketch("PL_TOP", "SK_TOP") as s:
        s.rect(0, "-TOP_W/2", "CPN_L", "TOP_W")
    wall.extrude("SK_TOP", "TOP_T", "BACK")
    gcy = "-WALL_T + (SNAP_U + GROOVE_CLR)/2 - 0.25"
    for name, hx, depth in (("G90", "HOOK_X", "RAMP_H + SNAP_LAND + GROOVE_PLAY + GROOVE_TOP"),
                            ("G45", "-HOOK_X", "RAMP_H + SNAP_LAND + SNAP_U + GROOVE_PLAY + GROOVE_TOP")):
        with wall.sketch(f"PL_{name}", f"SK_{name}") as s:
            s.rect(hx, gcy, "SNAP_W + 1", "SNAP_U + GROOVE_CLR + 0.5")
        wall.cut(f"SK_{name}", depth, f"GROOVE_{name}")
    gd = v["SNAP_U"] + v["GROOVE_CLR"]
    d90 = RH + LAND + v["GROOVE_PLAY"] + v["GROOVE_TOP"]
    d45 = d90 + U
    vol = (v["CPN_L"] * v["WALL_T"] * v["WALL_H"] + v["CPN_L"] * v["TOP_W"] * v["TOP_T"]
           - (v["SNAP_W"] + 1) * gd * (d90 + d45))
    verify(wall, "A_wall", vol)
    p_wall = wall.save(os.path.join(OUT, "test_A_wall.sldprt"))

    strain = 1.5 * v["LIP_T"] * U / v["SNAP_L"] ** 2 * 100
    print(f"   snap strain {strain:.2f} % (PLA limit ~2 %, repeated use ~1 %)")
    doc, asm, _ = place(sw, [(p_lip, IDENT, (0, 0, 0)), (p_wall, IDENT, (0, 0, 0))],
                        os.path.join(OUT, "test_A_assembly.sldasm"))
    probs = check_interference(asm, {})
    picture(doc, os.path.join(OUT, "test_A.png"))
    assert not probs, probs
    return [p_lip, p_wall]


# ---------------------------------------------------------------- B: PCB frame + USB-C wall
B = dict(FR_MARGIN=3.0, USB_WALL_L=22.0, USB_WALL_D=15.0, PIN_EXTRA=1.0)


def coupon_b(sw):
    """Display frame: X right, Y up, Z toward the viewer, PCB front face at Z=0 (same as ref_display)."""
    p = {**PR.DISPLAY, **PR.PLUG, **F, **B}
    v = p
    pb = PartBuilder(sw, p)
    pb.plane("PL_INNER", "GLASS_T + GLASS_GAP")
    with pb.sketch("PL_INNER", "SK_PLATE") as s:
        s.rect(0, 0, "PCB_W + 2*FR_MARGIN", "PCB_H + 2*FR_MARGIN")
    pb.extrude("SK_PLATE", "BEZ_T", "PLATE")
    va_cy = "PCB_H/2 - GLASS_TOP - VA_TOP - (GLASS_H - VA_TOP - VA_BOT)/2"
    win_w, win_h = "GLASS_W - 2*VA_SIDE - 2*WIN_MARGIN", "GLASS_H - VA_TOP - VA_BOT - 2*WIN_MARGIN"
    with pb.sketch("PL_INNER", "SK_WINDOW") as s:
        s.rect(0, va_cy, win_w, win_h)
    pb.cut("SK_WINDOW", "BEZ_T", "WINDOW", reverse=False)
    hx, hy = "PCB_W/2 - HOLE_EDGE", "PCB_H/2 - HOLE_EDGE"
    with pb.sketch("PL_INNER", "SK_STANDOFFS") as s:
        for sx in (1, -1):
            for sy in (1, -1):
                s.circle(f"{sx}*({hx})", f"{sy}*({hy})", "STAND_D")
    pb.extrude("SK_STANDOFFS", "GLASS_T + GLASS_GAP", "STANDOFFS", reverse=True)
    with pb.sketch("Front Plane", "SK_PINS") as s:
        for sx in (1, -1):
            for sy in (1, -1):
                s.circle(f"{sx}*({hx})", f"{sy}*({hy})", "HOLE_D - 2*PIN_CLR")
    pb.extrude("SK_PINS", "PCB_T + PIN_EXTRA", "PINS", reverse=True)
    usb_y = "PCB_H/2 - USBC_TOP - USBC_W/2"
    with pb.sketch("PL_INNER", "SK_USB_WALL") as s:
        s.rect("PCB_W/2 + PCB_CLR + WALL_T/2", usb_y, "WALL_T", "USB_WALL_L")
    pb.extrude("SK_USB_WALL", "USB_WALL_D", "USB_WALL", reverse=True)
    pb.plane("PL_USB_OUT", "PCB_W/2 + PCB_CLR + WALL_T", base="Right Plane")
    with pb.sketch("PL_USB_OUT", "SK_USB_HOLE") as s:          # Right sketch: sx = -Z, sy = Y
        s.rect("PCB_T + USBC_H/2", usb_y, "PLUG_T + 2*PLUG_CLR", "PLUG_W + 2*PLUG_CLR")
    pb.cut("SK_USB_HOLE", "WALL_T + 1", "USB_OPENING", reverse=True)

    ww = v["GLASS_W"] - 2 * v["VA_SIDE"] - 2 * v["WIN_MARGIN"]
    wh = v["GLASS_H"] - v["VA_TOP"] - v["VA_BOT"] - 2 * v["WIN_MARGIN"]
    vol = ((v["PCB_W"] + 2 * v["FR_MARGIN"]) * (v["PCB_H"] + 2 * v["FR_MARGIN"]) - ww * wh) * v["BEZ_T"] \
        + 4 * PI * (v["STAND_D"] / 2) ** 2 * (v["GLASS_T"] + v["GLASS_GAP"]) \
        + 4 * PI * ((v["HOLE_D"] - 2 * v["PIN_CLR"]) / 2) ** 2 * (v["PCB_T"] + v["PIN_EXTRA"]) \
        + v["WALL_T"] * v["USB_WALL_L"] * v["USB_WALL_D"] \
        - v["WALL_T"] * (v["PLUG_T"] + 2 * v["PLUG_CLR"]) * (v["PLUG_W"] + 2 * v["PLUG_CLR"])
    verify(pb, "B_frame", vol)
    print(f"   window {ww:.2f} x {wh:.2f} mm, pins d{v['HOLE_D'] - 2 * v['PIN_CLR']:.2f} in d{v['HOLE_D']} holes")
    p_frame = pb.save(os.path.join(OUT, "test_B_frame.sldprt"))

    # fit check with the real components: display on the pins, cable plug through the wall
    from step0_layout import PLACEMENT
    plug_ax = PLACEMENT["ref_usbc_plug.sldprt"]
    items = [(p_frame, IDENT, (0, 0, 0)),
             (os.path.join(OUT, "ref_display.sldprt"), IDENT, (0, 0, 0)),
             (os.path.join(OUT, "ref_usbc_plug.sldprt"), plug_ax[:3], plug_ax[3])]
    doc, asm, _ = place(sw, items, os.path.join(OUT, "test_B_assembly.sldasm"))
    tip = PR.PLUG["PLUG_TIP_W"] * PR.PLUG["PLUG_TIP_T"] * min(PR.PLUG["PLUG_TIP_L"], v["USBC_L"])
    probs = check_interference(asm, {frozenset({"ref_display", "ref_usbc_plug"}): tip})
    picture(doc, os.path.join(OUT, "test_B.png"))
    assert not probs, probs
    return [p_frame]


# ---------------------------------------------------------------- C: hinge with detents
Cp = dict(BASE_T=1.6, BASE_W=30.0, BASE_L=34.0, BASE_CY=-7.0, K_W=6.0, K_R=6.0, KN_GAP=0.3, MID_W=16.4,
          R_W=12.0, NOTCH_D=0.9, NOTCH_R=0.9, DET_PRE=0.1, BUMP_H=1.3, BUMP_R=0.9,
          ARM_W=12.0, ARM_L=16.0, ARM_TIP=1.5, SLOT_W=1.0, PIN_D=5.0, STUB_L=35.0, STUB_T=5.0,
          N_NOTCH=6, NOTCH_STEP=12.0)
AXZ = "(BASE_T + BUMP_H + R_W - NOTCH_D - DET_PRE)"      # hinge axis height


def area_grid(inside, x0, x1, y0, y1, h=0.01):
    import numpy as np
    xs = np.arange(x0 + h / 2, x1, h)
    ys = np.arange(y0 + h / 2, y1, h)
    X, Y = np.meshgrid(xs, ys)
    return float(inside(X, Y).sum()) * h * h


def coupon_c(sw):
    """Frame: hinge axis along X, Z up (base plate on the bed), leg stub along +Y at the first detent."""
    p = {**F, **Cp}
    v = p
    axz = eval(AXZ, {}, p)
    base = PartBuilder(sw, p)
    with base.sketch("Front Plane", "SK_PLATE") as s:
        s.rect(0, "BASE_CY", "BASE_W", "BASE_L")
    base.extrude("SK_PLATE", "BASE_T", "PLATE")
    root = "ARM_TIP - ARM_L"
    with base.sketch("Front Plane", "SK_SIDE_SLOTS") as s:
        for sx in (1, -1):
            s.rect(f"{sx}*(ARM_W/2 + SLOT_W/2)", f"({root} + ARM_TIP + SLOT_W)/2", "SLOT_W", "ARM_L + SLOT_W")
    base.cut("SK_SIDE_SLOTS", "BASE_T", "SIDE_SLOTS", reverse=False)
    with base.sketch("Front Plane", "SK_TIP_SLOT") as s:
        s.rect(0, "ARM_TIP + SLOT_W/2", "ARM_W", "SLOT_W")
    base.cut("SK_TIP_SLOT", "BASE_T", "TIP_SLOT", reverse=False)
    base.plane("PL_ARM", "-ARM_W/2", base="Right Plane")
    with base.sketch("PL_ARM", "SK_BUMP_NECK") as s:           # Right sketch: sx = -Z, sy = Y
        s.rect("-(BASE_T + (BUMP_H - BUMP_R)/2)", 0, "BUMP_H - BUMP_R", "2*BUMP_R")
    base.extrude("SK_BUMP_NECK", "ARM_W", "DETENT_NECK")
    with base.sketch("PL_ARM", "SK_BUMP") as s:
        s.circle("-(BASE_T + BUMP_H - BUMP_R)", 0, "2*BUMP_R")
    base.extrude("SK_BUMP", "ARM_W", "DETENT_BUMP")
    for side, x0 in (("L", "-(MID_W/2 + KN_GAP + K_W)"), ("R", "MID_W/2 + KN_GAP")):
        base.plane(f"PL_K{side}", x0, base="Right Plane")
        with base.sketch(f"PL_K{side}", f"SK_K{side}_POST") as s:
            s.rect(f"-(BASE_T + {AXZ})/2", 0, f"{AXZ} - BASE_T", "2*K_R")
        base.extrude(f"SK_K{side}_POST", "K_W", f"KNUCKLE_{side}_POST")
        with base.sketch(f"PL_K{side}", f"SK_K{side}_EYE") as s:
            s.circle(f"-{AXZ}", 0, "2*K_R")
        base.extrude(f"SK_K{side}_EYE", "K_W", f"KNUCKLE_{side}_EYE")
    with base.sketch("Right Plane", "SK_PIN_HOLE") as s:
        s.circle(f"-{AXZ}", 0, "PIN_D - PIN_PRESS")
    base.cut("SK_PIN_HOLE", 40, "PIN_HOLE", mode="mid")
    rp0, cx0 = (v["PIN_D"] - v["PIN_PRESS"]) / 2, -axz       # teardrop roof toward +Z (print-up) = -sx
    with base.sketch("Right Plane", "SK_PIN_TEARDROP") as s:
        s.polygon([(cx0 - 0.70711 * rp0, -0.70711 * rp0), (cx0 - 0.70711 * rp0, 0.70711 * rp0), (cx0 - 1.41421 * rp0, 0)])
    base.cut("SK_PIN_TEARDROP", 40, "PIN_HOLE_TEARDROP", mode="mid")

    import numpy as np
    slots = (2 * v["SLOT_W"] * (v["ARM_L"] + v["SLOT_W"]) + v["ARM_W"] * v["SLOT_W"]) * v["BASE_T"]
    br, bh = v["BUMP_R"], v["BUMP_H"]
    bump_area = area_grid(lambda Y, Z: (Z > v["BASE_T"]) & ((Y ** 2 + (Z - (v["BASE_T"] + bh - br)) ** 2 < br ** 2)
                                                          | ((abs(Y) < br) & (Z < v["BASE_T"] + bh - br))),
                          -br, br, v["BASE_T"], v["BASE_T"] + bh)
    kr, rh = v["K_R"], (v["PIN_D"] - v["PIN_PRESS"]) / 2
    tri = rh * rh * (1 - PI / 4)        # teardrop roof area outside the circle (kite minus quarter circle)
    kn_area = (axz - v["BASE_T"]) * 2 * kr + PI * kr ** 2 / 2 - PI * rh ** 2 - tri
    vol = v["BASE_W"] * v["BASE_L"] * v["BASE_T"] - slots + bump_area * v["ARM_W"] + 2 * kn_area * v["K_W"]
    verify(base, "C_base", vol, tol=2e-3)
    p_base = base.save(os.path.join(OUT, "test_C_base.sldprt"))

    leg = PartBuilder(sw, p)
    leg.plane("PL_MID", "-MID_W/2", base="Right Plane")
    with leg.sketch("PL_MID", "SK_WHEEL") as s:
        s.circle(f"-{AXZ}", 0, "2*R_W")
    leg.extrude("SK_WHEEL", "MID_W", "WHEEL")
    with leg.sketch("PL_MID", "SK_STUB") as s:
        s.rect(f"-{AXZ}", "STUB_L/2", "STUB_T", "STUB_L")
    leg.extrude("SK_STUB", "MID_W", "STUB")
    with leg.sketch("Right Plane", "SK_LEG_HOLE") as s:
        s.circle(f"-{AXZ}", 0, "PIN_D + HINGE_CLR")
    leg.cut("SK_LEG_HOLE", 40, "PIN_HOLE", mode="mid")
    rn = "(R_W - NOTCH_D + NOTCH_R)"
    angles = [-90 - k * v["NOTCH_STEP"] for k in range(v["N_NOTCH"])]
    with leg.sketch("Right Plane", "SK_NOTCHES") as s:
        for a in angles:
            c, sn = math.cos(math.radians(a)), math.sin(math.radians(a))
            s.circle(f"-({AXZ} + {rn}*({sn:.9f}))", f"{rn}*({c:.9f})", "2*NOTCH_R")
    leg.cut("SK_NOTCHES", 40, "DETENT_NOTCHES", mode="mid")

    R, st, sl, rr = v["R_W"], v["STUB_T"], v["STUB_L"], (v["PIN_D"] + v["HINGE_CLR"]) / 2
    rnv = R - v["NOTCH_D"] + v["NOTCH_R"]
    ncs = [(rnv * math.cos(math.radians(a)), rnv * math.sin(math.radians(a))) for a in angles]

    def inside(Y, Z):
        m = (Y ** 2 + Z ** 2 < R ** 2) | ((Y > 0) & (Y < sl) & (abs(Z) < st / 2))
        m &= Y ** 2 + Z ** 2 > rr ** 2
        for cy, cz in ncs:
            m &= (Y - cy) ** 2 + (Z - cz) ** 2 > v["NOTCH_R"] ** 2
        return m
    leg_area = area_grid(inside, -R, sl, -R, R, h=0.01)
    verify(leg, "C_leg", leg_area * v["MID_W"], tol=2e-3)
    web = 2 * rnv * math.sin(math.radians(v["NOTCH_STEP"] / 2)) - 2 * v["NOTCH_R"]
    defl = v["NOTCH_D"] + v["DET_PRE"]
    print(f"   detent: {v['N_NOTCH']} positions every {v['NOTCH_STEP']:.0f} deg, ridge between notches {web:.2f} mm, "
          f"arm deflection {defl:.2f} -> strain {1.5 * v['BASE_T'] * defl / v['ARM_L'] ** 2 * 100:.2f} %")
    assert web > 0.4, "notch ridge too thin"
    p_leg = leg.save(os.path.join(OUT, "test_C_leg.sldprt"))

    pin = PartBuilder(sw, p)
    pin.plane("PL_PIN", "-(MID_W/2 + KN_GAP + K_W)", base="Right Plane")
    with pin.sketch("PL_PIN", "SK_PIN") as s:
        s.circle(f"-{AXZ}", 0, "PIN_D")
    pin.extrude("SK_PIN", "2*(MID_W/2 + KN_GAP + K_W)", "PIN")
    verify(pin, "C_pin", PI * (v["PIN_D"] / 2) ** 2 * 2 * (v["MID_W"] / 2 + v["KN_GAP"] + v["K_W"]))
    p_pin = pin.save(os.path.join(OUT, "test_C_pin.sldprt"))

    doc, asm, _ = place(sw, [(p_base, IDENT, (0, 0, 0)), (p_leg, IDENT, (0, 0, 0)), (p_pin, IDENT, (0, 0, 0))],
                        os.path.join(OUT, "test_C_assembly.sldasm"))
    from encl import teardrop_press_area
    press = teardrop_press_area(v["PIN_D"], v["PIN_D"] - v["PIN_PRESS"]) * 2 * v["K_W"]   # teardrop: no press under the roof
    probs = check_interference(asm, {frozenset({"test_C_base", "test_C_pin"}): press,   # press fit in the fixed knuckles
                                     frozenset({"test_C_base", "test_C_leg"}): None})   # detent preload in notch 1
    picture(doc, os.path.join(OUT, "test_C.png"))
    assert not probs, probs
    return [p_base, p_leg, p_pin]


COUPONS = {"A": coupon_a, "B": coupon_b, "C": coupon_c}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    sw = connect()
    close_out_docs(sw)
    for k, fn in COUPONS.items():
        if which in (k, "all"):
            for part in fn(sw):
                stl = os.path.join(STL_DIR, os.path.basename(part).replace(".sldprt", ".stl"))
                assert export_stl(sw, part, stl), f"STL export failed: {stl}"
                lo, hi, n = stl_bbox(stl)
                print(f"   stl {os.path.basename(stl)}: {n} triangles, size {hi[0]-lo[0]:.2f} x {hi[1]-lo[1]:.2f} x {hi[2]-lo[2]:.2f} mm")
            print(f"COUPON {k} OK")
