"""Step 5: adjustable stand = hinge block (screwed to the back from inside) + leg + pin.

Same mechanism as coupon C: a flexing arm in the block presses a bump into notches on the
leg wheel; N_NOTCH positions every NOTCH_STEP degrees. At position 0 the leg points down
along the back; it swings away from the back as it opens.
Print: hinge block on its side (X face down: round pin hole, arm bends along the layers),
leg on its side (wheel face down), pin standing.
"""
import math
import os

import encl as E
from encl import P, v
from sw_common import connect, close_out_docs, OUT
from swcad import PartBuilder

PATHS = {k: os.path.join(OUT, f"{k}.sldprt") for k in ("hinge_block", "stand_leg", "hinge_pin")}
KX_OUT = "(MID_W/2 + KN_GAP + K_W)"     # outer face of the fixed knuckles
KX_IN = "(MID_W/2 + KN_GAP)"


def notch_angles():
    """Wheel notch directions (deg, in the Y-Z plane from +Y toward +Z) at leg position 0.
    The bump points +Z from the axis (90 deg); opening the leg by a rotates the wheel by +a."""
    import params as PR
    return [90 - a for a in PR.STAND_POSITIONS]


def hinge_block(sw, mode="build"):
    pb = PartBuilder(sw, P, path=PATHS["hinge_block"], mode=mode)
    pb.plane("PL_CONTACT", E.Z_BACK_OUT)
    with pb.sketch("PL_CONTACT", "SK_PLATE") as s:
        s.rect(0, E.HB_CY, "HB_W", "HB_L")
    pb.extrude("SK_PLATE", "HB_T", "PLATE", reverse=True)
    # detent arm: U-slot through the plate, then thinned from the contact side (relief)
    root = "(HINGE_Y + ARM_TIP - ARM_L)"
    with pb.sketch("PL_CONTACT", "SK_SIDE_SLOTS") as s:
        for sx in (1, -1):
            s.rect(f"{sx}*(ARM_W/2 + SLOT_W/2)", f"({root} + HINGE_Y + ARM_TIP + SLOT_W)/2", "SLOT_W", "ARM_L + SLOT_W")
    pb.cut("SK_SIDE_SLOTS", "HB_T", "ARM_SIDE_SLOTS", reverse=True)
    with pb.sketch("PL_CONTACT", "SK_TIP_SLOT") as s:
        s.rect(0, "HINGE_Y + ARM_TIP + SLOT_W/2", "ARM_W", "SLOT_W")
    pb.cut("SK_TIP_SLOT", "HB_T", "ARM_TIP_SLOT", reverse=True)
    # arm thinned from the OUTER side, so the block prints flat on its contact face with no support
    pb.plane("PL_HB_OUT", E.HB_OUT_Z)
    with pb.sketch("PL_HB_OUT", "SK_RELIEF") as s:
        s.rect(0, f"({root} + HINGE_Y + ARM_TIP)/2", "ARM_W", "ARM_L")
    pb.cut("SK_RELIEF", "HB_T - ARM_T", "ARM_RELIEF", reverse=False)
    # bump on a neck rising from the thinned arm, under the axis (Right-plane sketch: sx = -Z, sy = Y)
    arm_out = f"({E.Z_BACK_OUT} - ARM_T)"
    bump_c = f"({E.HB_OUT_Z} - BUMP_H + BUMP_R)"
    pb.plane("PL_ARM", "-ARM_W/2", base="Right Plane")
    with pb.sketch("PL_ARM", "SK_BUMP_NECK") as s:
        s.rect(f"-({arm_out} + {bump_c})/2", "HINGE_Y", f"{arm_out} - {bump_c}", "2*BUMP_R")
    pb.extrude("SK_BUMP_NECK", "ARM_W", "DETENT_NECK")
    with pb.sketch("PL_ARM", "SK_BUMP") as s:
        s.circle(f"-({E.HB_OUT_Z} - BUMP_H + BUMP_R)", "HINGE_Y", "2*BUMP_R")
    pb.extrude("SK_BUMP", "ARM_W", "DETENT_BUMP")
    # fixed knuckles
    for side, x0 in (("L", f"-{KX_OUT}"), ("R", KX_IN)):
        pb.plane(f"PL_K{side}", x0, base="Right Plane")
        with pb.sketch(f"PL_K{side}", f"SK_K{side}_POST") as s:
            s.rect(f"-({E.HB_OUT_Z} + {E.Z_AX})/2", "HINGE_Y", f"{E.HB_OUT_Z} - {E.Z_AX}", "2*K_R")
        pb.extrude(f"SK_K{side}_POST", "K_W", f"KNUCKLE_{side}_POST")
        with pb.sketch(f"PL_K{side}", f"SK_K{side}_EYE") as s:
            s.circle(f"-{E.Z_AX}", "HINGE_Y", "2*K_R")
        pb.extrude(f"SK_K{side}_EYE", "K_W", f"KNUCKLE_{side}_EYE")
    with pb.sketch("Right Plane", "SK_PIN_HOLE") as s:
        s.circle(f"-{E.Z_AX}", "HINGE_Y", "PIN_D - PIN_PRESS")
    pb.cut("SK_PIN_HOLE", 60, "PIN_HOLE", mode="mid")
    # teardrop: 45 deg roof over the horizontal pin hole so the printed top does not sag and pinch the pin.
    # Print-up = model -Z = +sx in the Right-plane sketch (sx = -Z, sy = Y).
    rp, cx, cy = (P["PIN_D"] - P["PIN_PRESS"]) / 2, -v(E.Z_AX), P["HINGE_Y"]
    with pb.sketch("Right Plane", "SK_PIN_TEARDROP") as s:
        s.polygon([(cx + 0.70711 * rp, cy - 0.70711 * rp), (cx + 0.70711 * rp, cy + 0.70711 * rp),
                   (cx + 1.41421 * rp, cy)])
    pb.cut("SK_PIN_TEARDROP", 60, "PIN_HOLE_TEARDROP", mode="mid")
    # heat-insert holes from the contact face into the knuckle posts
    with pb.sketch("PL_CONTACT", "SK_INSERTS") as s:
        for hx in ("HB_SCREW_X", "-HB_SCREW_X"):
            s.circle(hx, "HINGE_Y", "INSERT_D")
    pb.cut("SK_INSERTS", "INSERT_L", "INSERT_HOLES", reverse=True)
    return pb


def stand_leg(sw, mode="build"):
    pb = PartBuilder(sw, P, path=PATHS["stand_leg"], mode=mode)
    # leg plate tangent to the wheel on the device side: prints plate-down with no support,
    # and keeps the leg close to the back (lower minimum tilt)
    pb.plane("PL_MID", "-MID_W/2", base="Right Plane")
    pb.plane("PL_LEG", f"{E.Z_AX} + R_W")
    with pb.sketch("PL_MID", "SK_WHEEL") as s:
        s.circle(f"-{E.Z_AX}", "HINGE_Y", "2*R_W")
    pb.extrude("SK_WHEEL", "MID_W", "WHEEL")
    # neck: joins the plate to the wheel over the full wheel width; stops LEG_NECK_GAP short of
    # the axis line so it never reaches the detent bump (it swings away from it as the leg opens)
    with pb.sketch("PL_MID", "SK_NECK") as s:
        s.rect(f"-({E.Z_AX} + R_W - LEG_T/2)", "HINGE_Y - (LEG_NECK_GAP + LEG_START + 1)/2",
               "LEG_T", "LEG_START + 1 - LEG_NECK_GAP")
    pb.extrude("SK_NECK", "MID_W", "NECK")
    with pb.sketch("PL_LEG", "SK_LEG") as s:
        s.rect(0, "HINGE_Y - (LEG_START + LEG_L)/2", "LEG_W", "LEG_L - LEG_START")
    pb.extrude("SK_LEG", "LEG_T", "LEG", reverse=True)
    with pb.sketch("Right Plane", "SK_LEG_HOLE") as s:
        s.circle(f"-{E.Z_AX}", "HINGE_Y", "PIN_D + HINGE_CLR")
    pb.cut("SK_LEG_HOLE", 60, "PIN_HOLE", mode="mid")
    rn = "(R_W - NOTCH_D + NOTCH_R)"
    with pb.sketch("Right Plane", "SK_NOTCHES") as s:
        for a in notch_angles():
            c, sn = math.cos(math.radians(a)), math.sin(math.radians(a))
            s.circle(f"-({E.Z_AX} + {rn}*({sn:.9f}))", f"HINGE_Y + {rn}*({c:.9f})", "2*NOTCH_R")
    pb.cut("SK_NOTCHES", 30, "DETENT_NOTCHES", mode="mid")
    return pb


def hinge_pin(sw, mode="build"):
    pb = PartBuilder(sw, P, path=PATHS["hinge_pin"], mode=mode)
    pb.plane("PL_PIN", f"-{KX_OUT}", base="Right Plane")
    with pb.sketch("PL_PIN", "SK_PIN") as s:
        s.circle(f"-{E.Z_AX}", "HINGE_Y", "PIN_D")
    pb.extrude("SK_PIN", f"2*{KX_OUT}", "PIN")
    return pb


def tilt_table():
    """Screen tilt FROM VERTICAL at each detent: the device rests on its bottom-back edge and on the
    outer corner of the leg tip; the desk is the line through both."""
    import params as PR
    h = P["HINGE_Y"] - v(E.OUT_BOT)                 # hinge above the bottom edge, along the back
    d = v(E.Z_BACK_OUT) - v(E.Z_AX)                 # axis behind the back surface
    f = P["R_W"] - P["LEG_T"]                       # outer face of the leg plate, toward the back from the axis
    out = []
    for a_deg in PR.STAND_POSITIONS:
        a = math.radians(a_deg)
        ty = h - P["LEG_L"] * math.cos(a) - f * math.sin(a)
        tz = d + P["LEG_L"] * math.sin(a) - f * math.cos(a)
        out.append((a_deg, 90 - math.degrees(math.atan2(tz, ty))))
    return out


if __name__ == "__main__":
    sw = connect()
    close_out_docs(sw)
    shared = E.write_shared()          # before build: update mode pulls new names from it
    for name, fn in (("hinge_block", hinge_block), ("stand_leg", stand_leg), ("hinge_pin", hinge_pin)):
        import partsync
        mode = partsync.decide(sw, PATHS[name], os.path.join(os.path.dirname(os.path.abspath(__file__)), "params.py"))
        print(f'   {name} mode: {mode}')
        pb = fn(sw, mode)
        errs = pb.rebuild_errors()
        lo, hi = pb.bbox()
        print(f"[{name}] bodies={len(pb.bodies())} errors={errs} links={len(pb.links)} "
              f"size {hi[0]-lo[0]:.2f} x {hi[1]-lo[1]:.2f} x {hi[2]-lo[2]:.2f} vol {pb.volume()/1000:.2f} cm3")
        assert not errs and len(pb.bodies()) == 1
        pb.link_external(shared)
        print("   saved", pb.save(PATHS[name]))
    import params as PR
    rn = P["R_W"] - P["NOTCH_D"] + P["NOTCH_R"]
    step = min(b - a for a, b in zip(PR.STAND_POSITIONS, PR.STAND_POSITIONS[1:]))
    web = 2 * rn * math.sin(math.radians(step / 2)) - 2 * P["NOTCH_R"]
    assert web > 0.4, f"notch ridge {web:.2f} mm too thin"
    strain = 1.5 * P["ARM_T"] * (P["NOTCH_D"] + P["DET_PRE"]) / P["ARM_L"] ** 2 * 100
    print(f"   detent ridge {web:.2f} mm, arm strain {strain:.2f} %")
    for a, t in tilt_table():
        if a == 0:
            print("   leg folded       -> device stands upright on its own base (leg off the desk)")
        else:
            print(f"   leg open {a:4.0f} deg -> screen tilt {t:5.1f} deg from vertical")
    print("STEP 5 OK")
