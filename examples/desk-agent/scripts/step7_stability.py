"""Step 7: does the device stand, at every stand position?

Centre of mass (CoM): printed parts = Bambu sliced grams (real infill) at their SolidWorks volume
centroid; purchased parts = MASS below at their reference-model centroid, placed as in step 6.
The leg is placed at each detent. Contacts on the desk: the bottom-back edge of the body and the
outer corner of the leg tip (2-D side view, the device is symmetric enough in X).

Reported per position: screen tilt, where the CoM falls between the two contacts, and the push at
the top of the front face (horizontal, toward the back) / pull (toward the viewer) that tips it.
"""
import math
import os

import encl as E
from encl import P, v
from sw_common import connect, T, swconst, OUT
from step6_assembly import COMPONENTS, leg_pose

C = swconst.constants
MM = 1e-3
G = 9.81

# grams. Printed parts: Bambu slice (0.20 Standard, PLA Basic). Purchased: [A] estimates - weigh them!
MASS = {
    "back_body": 73.80, "front_frame": 37.0, "hinge_block": 3.6, "stand_leg": 4.67, "hinge_pin": 0.6,
    "diffuser": 0.89,
    "ref_display": 95.0,     # [A] 5" IPS module + ESP32-S3 board
    "ref_atom_echo": 5.0,    # [A]
    "ref_radar": 2.0,        # [A]
    "ref_led_stick": 2.0,    # [A]
}


def centroid(sw, name):
    r = sw.OpenDoc6(os.path.join(OUT, name + ".sldprt"), C.swDocPART, C.swOpenDocOptions_Silent, "", 0, 0)
    d = T(r[0], "IModelDoc2")
    mp = T(d.Extension.CreateMassProperty(), "IMassProperty")
    return [x / MM for x in mp.CenterOfMass]


def apply(axes, o, p):
    return [o[i] + sum(axes[k][i] * p[k] for k in range(3)) for i in range(3)]


def main():
    sw = connect()
    place = {n: (ax, o) for n, ax, o in COMPONENTS}
    ident = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    cen = {n: centroid(sw, n) for n in MASS}
    y_bot, z_back = v(E.OUT_BOT), v(E.Z_BACK_OUT)
    y_top, z_front = y_bot + v(E.OUT_H), v(E.Z_OUT)
    m_tot = sum(MASS.values())
    print(f"total mass {m_tot:.0f} g  (printed {sum(MASS[k] for k in MASS if not k.startswith('ref_')):.0f} g)")
    print(" pos  tilt   CoM behind back-edge  CoM before leg tip  push-back to tip  pull-forward to tip")
    import params as PR
    for k, a in enumerate(PR.STAND_POSITIONS):
        lax, lo = leg_pose(a)
        com = [0.0, 0.0, 0.0]
        for n, m in MASS.items():
            if n == "stand_leg":
                p = apply(lax, lo, cen[n])
            elif n in place:
                p = apply(*place[n], cen[n])
            else:
                p = apply(ident, (0, 0, 0), cen[n])
            com = [com[i] + m * p[i] for i in range(3)]
        com = [c / m_tot for c in com]
        # leg tip outer corner (device frame): tip end of the plate face nearest the back
        f = P["R_W"] - P["LEG_T"]
        ar = math.radians(a)
        tip = (P["HINGE_Y"] - P["LEG_L"] * math.cos(ar) - f * math.sin(ar),
               v(E.Z_AX) - P["LEG_L"] * math.sin(ar) + f * math.cos(ar))
        # desk line through the back-bottom edge E and the tip; tilt = angle of the back from vertical
        ey, ez = y_bot, z_back
        dy, dz = tip[0] - ey, tip[1] - ez
        L = math.hypot(dy, dz)
        ux, uz = dy / L, dz / L                       # along the desk (device frame), from E toward the tip
        tilt = 90 - math.degrees(math.atan2(-dz, dy))  # back face from vertical
        s_com = (com[1] - ey) * ux + (com[2] - ez) * uz          # CoM position along the desk from E
        h_com = abs((com[1] - ey) * (-uz) + (com[2] - ez) * ux)  # CoM height above the desk
        # top-front corner height above the desk (where a finger pushes)
        tx, tz = y_top - ey, z_front - ez
        h_top = abs(tx * (-uz) + tz * ux)
        W = m_tot / 1000 * G
        push = W * (L - s_com) / h_top if 0 < s_com < L else 0.0     # tips over the leg
        pull = W * s_com / h_top if 0 < s_com < L else 0.0           # tips forward over E
        if a == 0:   # folded: the device stands on its bottom face; CoM must be inside the base depth
            depth = z_front - z_back
            fwd = com[2] - z_back
            print(f"  {k}   folded: stands upright on its base; CoM {fwd:.1f} mm in front of the back edge, "
                  f"{depth - fwd:.1f} mm behind the front edge (base {depth:.1f} mm)")
            continue
        state = "OK" if 0 < s_com < L else ("falls back" if s_com >= L else "stands upright on its base, leg idle")
        print(f"  {k}   {tilt:4.1f}°   {s_com:6.1f} mm             {L - s_com:6.1f} mm"
              f"          {push:5.2f} N          {pull:5.2f} N   {state}")
    print(f"CoM (pos 2): y={com[1]:.1f} z={com[2]:.1f} mm in the device frame; contact span {L:.1f} mm")


if __name__ == "__main__":
    main()
