"""Step 6: full assembly, interference check (leg at every detent), pictures, print STLs.

Only designed interferences are allowed:
  USB-C plug tip inside the receptacle keep-out, crush ribs on the PCB back,
  pin press-fit in the fixed knuckles, detent bump preload in the active notch.
"""
import math
import os

import encl as E
from encl import P, v
from asmtools import place, check_interference, picture, export_stl, stl_bbox, IDENT
from sw_common import connect, close_out_docs, save_as, T, swconst, OUT

C = swconst.constants
MM = 1e-3
HERE = os.path.dirname(OUT)
STL_DIR = os.path.join(HERE, "stl")
PRINT_DIR = os.path.join(HERE, "print_final")
ASM = os.path.join(OUT, "desk_agent.sldasm")

PARTS = ["front_frame", "back_body", "diffuser", "hinge_block", "stand_leg", "hinge_pin"]
S = P["USB_SIDE"]
plug_o = (S * P["PCB_W"] / 2, v(E.USB_Y), v(E.USB_ZC))
COMPONENTS = [
    ("ref_display", IDENT, (0, 0, 0)),
    ("ref_led_stick", IDENT, (0, P["LED_Y"], v(E.LED_TOP_Z) - P["LED_T"])),
    ("ref_radar", IDENT, (P["RADAR_X"], v(E.RADAR_Y), v(E.RADAR_FACE_Z))),
    ("ref_atom_echo", IDENT, (P["ATOM_X"], v(E.ATOM_Y), v(E.ATOM_FACE_Z))),
    ("ref_usbc_plug", ((0, 1, 0), (0, 0, -S), (-S, 0, 0)), plug_o),     # tip points into the board
    ("ref_edge_plugs", IDENT, (0, 0, 0)),
]


def leg_pose(alpha_deg):
    """Leg rotation about the hinge axis (X through (HINGE_Y, Z_AX)); +alpha swings it away from the back."""
    a = math.radians(alpha_deg)
    c, s = math.cos(a), math.sin(a)
    hy, za = P["HINGE_Y"], v(E.Z_AX)
    axes = ((1, 0, 0), (0, c, s), (0, -s, c))
    o = (0, hy - (hy * c - za * s), za - (hy * s + za * c))
    return axes, o


def expected():
    crush = 12 * math.pi * (P["CRUSH_D"] / 2) ** 2 * P["CRUSH"]
    press = E.teardrop_press_area(P["PIN_D"], P["PIN_D"] - P["PIN_PRESS"]) * 2 * P["K_W"]   # teardrop hole
    tip = P["PLUG_TIP_W"] * P["PLUG_TIP_T"] * min(P["PLUG_TIP_L"], P["USBC_L"])
    return {frozenset({"ref_display", "ref_usbc_plug"}): tip,
            frozenset({"back_body", "ref_display"}): crush,
            frozenset({"hinge_block", "hinge_pin"}): press,
            frozenset({"hinge_block", "stand_leg"}): None}


def main():
    sw = connect()
    close_out_docs(sw)
    items = [(os.path.join(OUT, f"{n}.sldprt"), ax, o) for n, ax, o in COMPONENTS]
    items += [(os.path.join(OUT, f"{n}.sldprt"), IDENT, (0, 0, 0)) for n in PARTS]
    doc, asm, comps = place(sw, items, ASM)
    leg = next(c for c in comps if c.Name2.startswith("stand_leg"))
    mu = T(sw.GetMathUtility(), "IMathUtility")
    import pythoncom
    from win32com.client import VARIANT
    all_ok = True
    import params as PR
    for k, alpha in enumerate(PR.STAND_POSITIONS):
        axes, o = leg_pose(alpha)
        xf = [x for a in axes for x in a] + [x * MM for x in o] + [1, 0, 0, 0]
        leg.Transform2 = mu.CreateTransform(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, xf))
        doc.ForceRebuild3(False)
        print(f"-- leg at detent {k} ({alpha:.0f} deg)")
        probs = check_interference(asm, expected())
        all_ok &= not probs
    axes, o = leg_pose(PR.STAND_POSITIONS[3])
    xf = [x for a in axes for x in a] + [x * MM for x in o] + [1, 0, 0, 0]
    leg.Transform2 = mu.CreateTransform(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, xf))
    doc.ForceRebuild3(False)
    save_as(doc, ASM)
    for view in ("*Isometric", "*Front", "*Back", "*Right"):
        picture(doc, os.path.join(OUT, f"desk_agent_{view.strip('*').lower()}.png"), view)
    assert all_ok, "unexpected interference"
    print("ASSEMBLY OK")
    return sw


def export_all(sw):
    os.makedirs(STL_DIR, exist_ok=True)
    for n in PARTS:
        stl = os.path.join(STL_DIR, f"{n}.stl")
        assert export_stl(sw, os.path.join(OUT, f"{n}.sldprt"), stl), stl
        lo, hi, tri = stl_bbox(stl)
        print(f"   {n}.stl {tri} triangles, {hi[0]-lo[0]:.1f} x {hi[1]-lo[1]:.1f} x {hi[2]-lo[2]:.1f} mm")


if __name__ == "__main__":
    sw = main()
    export_all(sw)
