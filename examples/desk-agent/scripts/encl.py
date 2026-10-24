"""Shared enclosure geometry: one parameter set and derived expressions used by every part,
so the front frame, back body, diffuser and stand always agree.

Global frame (same as ref_display / ref_layout): X right, Y up, Z toward the viewer,
origin at the PCB centre, PCB front face at Z = 0.
"""
import params as PR

P = {**PR.DISPLAY, **PR.LED, **PR.RADAR, **PR.ATOM, **PR.PLUG, **PR.FIT, **PR.ENCL, **PR.SHELL, **PR.STAND}

# ---- derived expressions (strings over parameter names) ----
Z_IN = "(GLASS_T + GLASS_GAP)"                         # front wall inner face
Z_OUT = "(GLASS_T + GLASS_GAP + BEZ_T)"                # front face
CAV_HW = "(PCB_W/2 + PCB_CLR)"                         # lip inner half width
CAV_TOP = "(PCB_H/2 + PCB_CLR)"                        # lip inner top
CAV_BOT = "(-(PCB_H/2 + CHIN_GAP + ATOM_H + ATOM_CABLE))"
CAV_CY = f"(({CAV_TOP} + {CAV_BOT})/2)"
CAV_H = f"({CAV_TOP} - {CAV_BOT})"
CAV_W = f"(2*{CAV_HW})"
SHELL_OFF = "(LIP_T + LIP_CLR + WALL_T)"
OUT_W = f"({CAV_W} + 2*{SHELL_OFF})"
OUT_H = f"({CAV_H} + 2*{SHELL_OFF})"
OUT_R = f"(LIP_IN_R + {SHELL_OFF})"
LIP_OUT_W = f"({CAV_W} + 2*LIP_T)"
LIP_OUT_H = f"({CAV_H} + 2*LIP_T)"
LIP_OUT_R = "(LIP_IN_R + LIP_T)"
WALL_IN_W = f"({LIP_OUT_W} + 2*LIP_CLR)"
WALL_IN_H = f"({LIP_OUT_H} + 2*LIP_CLR)"
WALL_IN_R = f"({LIP_OUT_R} + LIP_CLR)"
LIP_TIP = f"({Z_IN} - LIP_H)"

VA_CY = "(PCB_H/2 - GLASS_TOP - VA_TOP - (GLASS_H - VA_TOP - VA_BOT)/2)"
WIN_W = "(GLASS_W - 2*VA_SIDE - 2*WIN_MARGIN)"
WIN_H = "(GLASS_H - VA_TOP - VA_BOT - 2*WIN_MARGIN)"
HOLE_X = "(PCB_W/2 - HOLE_EDGE)"
HOLE_Y = "(PCB_H/2 - HOLE_EDGE)"
USB_Y = "(PCB_H/2 - USBC_TOP - USBC_W/2)"
USB_ZC = "(-(PCB_T + USBC_H/2))"
USB_SGN = "-" if P["USB_SIDE"] < 0 else ""              # side as a literal sign: a SW global used as a
                                                       # multiplier hung SolidWorks when linking the shared file                       # receptacle centre Z

ATOM_Y = "(-(PCB_H/2 + CHIN_GAP + ATOM_H/2))"
RADAR_Y = ATOM_Y
RADAR_FACE_Z = f"({Z_OUT} - RAD_WIN_T - RAD_GAP)"
ATOM_FACE_Z = f"({Z_OUT} - ATOM_LIP_T)"               # Atom face, behind the front stop rim
ATOM_USB_Z = f"({ATOM_FACE_Z} - ATOM_USB_FROM_FACE)"
LED_ROW_Y = "(LED_Y + LED_PCB_H/2 - LED_ROW_TOP - LED_SIZE/2)"
LED_HOLE_X = "(LED_HOLE_GAP/2 + LED_HOLE_D/2)"
LED_HOLE_Y = "(LED_Y + LED_PCB_H/2 - LED_HOLE_TOP - LED_HOLE_D/2)"
LED_TOP_Z = f"({Z_IN} - DIFF_FL_T)"                    # LED tops rest on the diffuser flange
LED_BACK_Z = f"({LED_TOP_Z} - LED_T - LED_PCB_T)"
DIFF_FL_W = "(DIFF_W + 2*DIFF_FL_EXT)"
DIFF_FL_H = "(DIFF_H + DIFF_FL_UP + DIFF_FL_DN)"
DIFF_CY = f"({LED_ROW_Y} + DIFF_TOP - DIFF_H/2)"        # bar centre (top edge fixed)
DIFF_FL_CY = f"({DIFF_CY} + (DIFF_FL_UP - DIFF_FL_DN)/2)"

RADAR_BACK_Z = f"({RADAR_FACE_Z} - (RAD_T + RAD_HDR_T + DUP_L + DUP_BEND))"
Z_BACK_IN = f"({RADAR_BACK_Z} - BACK_GAP)"
Z_BACK_OUT = f"({Z_BACK_IN} - SHELL_BACK_T)"


POST_TOP_Z = "(-(PCB_T + POST_GAP))"
ATOM_BACK_Z = f"({ATOM_FACE_Z} - ATOM_D)"
OUT_BOT = f"({CAV_CY} - {OUT_H}/2)"
WALL_IN_TOP = f"({CAV_TOP} + LIP_T + LIP_CLR)"
WALL_IN_BOT = f"({CAV_BOT} - LIP_T - LIP_CLR)"
# stand
HB_OUT_Z = f"({Z_BACK_OUT} - HB_T)"                    # hinge block outer face
Z_AX = f"({HB_OUT_Z} - BUMP_H - R_W + NOTCH_D + DET_PRE)"   # hinge axis Z
HB_CY = "(HINGE_Y - 5)"      # plate from HINGE_Y-20 to HINGE_Y+10


def write_shared():
    """shared_params.txt next to the scripts: every enclosure global variable, linked into each part.
    If the file was edited by hand since the scripts last wrote it, stop and ask (exit 3), unless
    --adopt-shared (take the hand values into params.py) or --overwrite-shared is on the command line."""
    import json
    import os
    import sys
    import partsync
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "shared_params.txt")
    edits = partsync.check_shared(path, P)
    if edits:
        print("== shared_params.txt was edited by hand:")
        for k, (last, now, pp) in edits.items():
            print(f"   ~ {k}: scripts wrote {last}, file now {now}, params.py {pp}")
        if "--adopt-shared" in sys.argv:
            partsync.adopt_globals(os.path.join(here, "params.py"), {k: [a, b] for k, (a, b, _) in edits.items()})
            for k, (_, now, _) in edits.items():
                P[k] = now
            print("   adopted into params.py (rebuild the other parts so they agree)")
        elif "--overwrite-shared" not in sys.argv:
            print("NEEDS A DECISION: rerun with --adopt-shared (keep the hand values) "
                  "or --overwrite-shared (go back to params.py).")
            raise SystemExit(partsync.EXIT_NEEDS_USER)
    with open(path, "w", encoding="utf-8") as f:
        for k, val in P.items():
            f.write(f'"{k}" = {float(val)}' + chr(10))      # floats only: '= -1' hung the link
    json.dump({k: float(val) for k, val in P.items()}, open(path + ".last.json", "w", encoding="utf-8"))
    return path


def v(expr):
    """Numeric value (mm) of an expression."""
    import math
    return float(eval(expr, {"math": math}, dict(P)))


def hook_profile(top, U, RH, LAND, zt):
    """Hook cross-section (Y, Z) on a lip outer face. top=True: top lip (hook toward +Y)."""
    yo = v(f"{CAV_TOP} + LIP_T") if top else v(f"{CAV_BOT} - LIP_T")
    s = 1 if top else -1
    zr = zt + RH + LAND
    return [(yo - s * 0.2, zt), (yo, zt), (yo + s * U, zt + RH), (yo + s * U, zr), (yo - s * 0.2, zr)], zr


def teardrop_press_area(pin_d, hole_d, h=0.002):
    """Cross-section area (mm2) where a pin of pin_d overlaps a teardrop hole of hole_d
    (circle + 45 deg roof). Numeric grid; used for the expected press-fit interference volume."""
    import numpy as np
    R, r = pin_d / 2, hole_d / 2
    xs = np.arange(-R, R, h) + h / 2
    X, Y = np.meshgrid(xs, xs)                       # Y = roof direction
    in_pin = X ** 2 + Y ** 2 < R ** 2
    in_circle = X ** 2 + Y ** 2 < r ** 2
    in_roof = (Y > 0.70711 * r) & (abs(X) < (1.41421 * r - Y))
    return float((in_pin & ~(in_circle | in_roof)).sum()) * h * h
