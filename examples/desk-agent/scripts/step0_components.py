"""Step 0: parametric reference models of the purchased components (keep-out bodies).

Run:  python step0_components.py [display|led|radar|atom|plug|all]
Each part is verified: no rebuild errors, bounding box and volume against hand calculation,
and an edit test (change a global variable -> geometry follows -> restore).
"""
import math
import os
import sys

import encl as E
import params as PR
from sw_common import connect, close_out_docs, OUT
from swcad import PartBuilder

PI = math.pi


def check(pb, name, bbox_exp, vol_exp, edit=None):
    errs = pb.rebuild_errors()
    lo, hi = pb.bbox()
    vol = pb.volume()
    print(f"[{name}] bodies={len(pb.bodies())} errors={errs}")
    print(f"   bbox X[{lo[0]:.3f},{hi[0]:.3f}] Y[{lo[1]:.3f},{hi[1]:.3f}] Z[{lo[2]:.3f},{hi[2]:.3f}]")
    print(f"   volume {vol:.2f} mm3 (expected {vol_exp:.2f}), equations linked: {len(pb.links)}")
    assert not errs, errs
    for got, exp in zip(lo + hi, bbox_exp[0] + bbox_exp[1]):
        assert abs(got - exp) < 1e-3, f"bbox {lo}{hi} != {bbox_exp}"
    assert abs(vol - vol_exp) / vol_exp < 1e-4, "volume mismatch"
    if edit:
        var, new, axis, delta = edit
        old = pb.params[var]
        lo0, hi0 = pb.bbox()
        pb.set_param(var, new)
        lo1, hi1 = pb.bbox()
        d = (hi1[axis] - lo1[axis]) - (hi0[axis] - lo0[axis])
        pb.set_param(var, old)
        lo2, hi2 = pb.bbox()
        print(f"   edit test {var}: {old}->{new} changed size by {d:+.3f} (expected {delta:+.3f}); restored ok={abs(hi2[axis]-hi0[axis])<1e-6}")
        assert abs(d - delta) < 1e-3 and abs(hi2[axis] - hi0[axis]) < 1e-6 and not pb.rebuild_errors()


def display(sw):
    p = {**PR.DISPLAY}
    pb = PartBuilder(sw, p)
    he = "PCB_W/2 - HOLE_EDGE"
    ve = "PCB_H/2 - HOLE_EDGE"
    gcy = "PCB_H/2 - GLASS_TOP - GLASS_H/2"
    pb.plane("PL_PCB_BACK", "-PCB_T")
    pb.plane("PL_GLASS_FRONT", "GLASS_T")
    with pb.sketch("Front Plane", "SK_PCB") as s:
        s.rect(0, 0, "PCB_W", "PCB_H")
    pb.extrude("SK_PCB", "PCB_T", "PCB", reverse=True)
    with pb.sketch("Front Plane", "SK_GLASS") as s:
        s.rect(0, gcy, "GLASS_W", "GLASS_H")
    pb.extrude("SK_GLASS", "GLASS_T", "GLASS")
    with pb.sketch("PL_PCB_BACK", "SK_BACK") as s:
        s.rect(0, 0, "PCB_W - 2*BACK_MARGIN", "PCB_H - 2*BACK_MARGIN")
    pb.extrude("SK_BACK", "BACK_T", "BACK_KEEPOUT", reverse=True)
    with pb.sketch("PL_PCB_BACK", "SK_USBC") as s:
        s.rect(f"{E.USB_SGN}(PCB_W/2 - USBC_L/2)", "PCB_H/2 - USBC_TOP - USBC_W/2", "USBC_L", "USBC_W")
    pb.extrude("SK_USBC", "USBC_H", "USBC", reverse=True)
    with pb.sketch("Front Plane", "SK_HOLES") as s:
        for sx in (1, -1):
            for sy in (1, -1):
                s.circle(f"{sx}*({he})", f"{sy}*({ve})", "HOLE_D")
    pb.cut("SK_HOLES", "PCB_T", "HOLES", reverse=True)
    with pb.sketch("PL_GLASS_FRONT", "SK_VA") as s:
        s.rect(0, "PCB_H/2 - GLASS_TOP - VA_TOP - (GLASS_H - VA_TOP - VA_BOT)/2",
               "GLASS_W - 2*VA_SIDE", "GLASS_H - VA_TOP - VA_BOT")
    pb.cut("SK_VA", 0.1, "VISIBLE_AREA_MARK", reverse=True)

    v = PR.DISPLAY
    vol = (v["PCB_W"] * v["PCB_H"] * v["PCB_T"] - 4 * PI * (v["HOLE_D"] / 2) ** 2 * v["PCB_T"]
           + v["GLASS_W"] * v["GLASS_H"] * v["GLASS_T"]
           - (v["GLASS_W"] - 2 * v["VA_SIDE"]) * (v["GLASS_H"] - v["VA_TOP"] - v["VA_BOT"]) * 0.1
           + (v["PCB_W"] - 2 * v["BACK_MARGIN"]) * (v["PCB_H"] - 2 * v["BACK_MARGIN"]) * v["BACK_T"]
           + v["USBC_L"] * v["USBC_W"] * v["USBC_H"])
    zmin = -v["PCB_T"] - max(v["BACK_T"], v["USBC_H"])
    check(pb, "display", ([-v["PCB_W"] / 2, -v["PCB_H"] / 2, zmin], [v["PCB_W"] / 2, v["PCB_H"] / 2, v["GLASS_T"]]),
          vol, edit=("PCB_W", v["PCB_W"] + 10, 0, 10))
    return pb.save(os.path.join(OUT, "ref_display.sldprt"))


def led(sw):
    v = PR.LED
    pb = PartBuilder(sw, v)
    with pb.sketch("Front Plane", "SK_BOARD") as s:
        s.rect(0, 0, "LED_PCB_W", "LED_PCB_H")
    pb.extrude("SK_BOARD", "LED_PCB_T", "BOARD", reverse=True)
    with pb.sketch("Front Plane", "SK_LEDS") as s:
        for i in range(v["LED_N"]):
            s.rect(f"({i} - (LED_N-1)/2)*(LED_SPAN-LED_SIZE)/(LED_N-1)",
                   "LED_PCB_H/2 - LED_ROW_TOP - LED_SIZE/2", "LED_SIZE", "LED_SIZE")
    pb.extrude("SK_LEDS", "LED_T", "LEDS")
    with pb.sketch("Front Plane", "SK_HOLES") as s:
        for sx in (1, -1):
            s.circle(f"{sx}*(LED_HOLE_GAP/2 + LED_HOLE_D/2)", "LED_PCB_H/2 - LED_HOLE_TOP - LED_HOLE_D/2", "LED_HOLE_D")
    pb.cut("SK_HOLES", "LED_PCB_T", "HOLES", reverse=True)
    # LEDs must not overlap the holes (checks the LED_ROW_TOP assumption)
    assert v["LED_ROW_TOP"] >= v["LED_HOLE_TOP"] + v["LED_HOLE_D"], "LED row overlaps mounting holes"
    vol = (v["LED_PCB_W"] * v["LED_PCB_H"] * v["LED_PCB_T"] - 2 * PI * (v["LED_HOLE_D"] / 2) ** 2 * v["LED_PCB_T"]
           + v["LED_N"] * v["LED_SIZE"] ** 2 * v["LED_T"])
    check(pb, "led", ([-v["LED_PCB_W"] / 2, -v["LED_PCB_H"] / 2, -v["LED_PCB_T"]],
                      [v["LED_PCB_W"] / 2, v["LED_PCB_H"] / 2, v["LED_T"]]),
          vol, edit=("LED_PCB_W", v["LED_PCB_W"] + 10, 0, 10))
    return pb.save(os.path.join(OUT, "ref_led_stick.sldprt"))


def radar(sw):
    """Antenna face at Z=0 (toward the viewer); header + Dupont plug keep-out go backwards."""
    v = PR.RADAR
    pb = PartBuilder(sw, v)
    pb.plane("PL_BACK", "-RAD_T")
    pb.plane("PL_HDR", "-(RAD_T + RAD_HDR_T)")
    with pb.sketch("Front Plane", "SK_BOARD") as s:
        s.rect(0, 0, "RAD_W", "RAD_H")
    pb.extrude("SK_BOARD", "RAD_T", "BOARD", reverse=True)
    with pb.sketch("PL_BACK", "SK_HDR") as s:
        s.rect(0, "RAD_H/2 - RAD_HDR_EDGE", "RAD_HDR_L", "RAD_HDR_W")
    pb.extrude("SK_HDR", "RAD_HDR_T", "HEADER", reverse=True)
    with pb.sketch("PL_HDR", "SK_PLUG") as s:
        s.rect(0, "RAD_H/2 - RAD_HDR_EDGE", "RAD_HDR_L", "RAD_HDR_W")
    pb.extrude("SK_PLUG", "DUP_L + DUP_BEND", "DUPONT_KEEPOUT", reverse=True)
    assert v["RAD_PIN_TOTAL"] - v["RAD_T"] - v["RAD_HDR_T"] < v["DUP_L"], "pins longer than the Dupont housing"
    vol = (v["RAD_W"] * v["RAD_H"] * v["RAD_T"]
           + v["RAD_HDR_L"] * v["RAD_HDR_W"] * (v["RAD_HDR_T"] + v["DUP_L"] + v["DUP_BEND"]))
    zmin = -(v["RAD_T"] + v["RAD_HDR_T"] + v["DUP_L"] + v["DUP_BEND"])
    check(pb, "radar", ([-v["RAD_W"] / 2, -v["RAD_H"] / 2, zmin], [v["RAD_W"] / 2, v["RAD_H"] / 2, 0]),
          vol, edit=("RAD_W", v["RAD_W"] + 4, 0, 4))
    return pb.save(os.path.join(OUT, "ref_radar.sldprt"))


def atom(sw):
    """Front (button / speaker) face at Z=0."""
    v = PR.ATOM
    pb = PartBuilder(sw, v)
    with pb.sketch("Front Plane", "SK_BODY") as s:
        s.rect(0, 0, "ATOM_W", "ATOM_H")
    pb.extrude("SK_BODY", "ATOM_D", "BODY", reverse=True)
    check(pb, "atom", ([-12, -12, -v["ATOM_D"]], [12, 12, 0]), v["ATOM_W"] * v["ATOM_H"] * v["ATOM_D"],
          edit=("ATOM_D", v["ATOM_D"] + 3, 2, 3))
    return pb.save(os.path.join(OUT, "ref_atom_echo.sldprt"))


def plug(sw):
    """USB-C cable plug. Z=0 at the overmold face; metal tip toward +Z, overmold/cable toward -Z."""
    v = PR.PLUG
    pb = PartBuilder(sw, v)
    with pb.sketch("Front Plane", "SK_MOLD") as s:
        s.rect(0, 0, "PLUG_W", "PLUG_T")
    pb.extrude("SK_MOLD", "PLUG_L", "OVERMOLD", reverse=True)
    with pb.sketch("Front Plane", "SK_TIP") as s:
        s.rect(0, 0, "PLUG_TIP_W", "PLUG_TIP_T")
    pb.extrude("SK_TIP", "PLUG_TIP_L", "TIP")
    vol = v["PLUG_W"] * v["PLUG_T"] * v["PLUG_L"] + v["PLUG_TIP_W"] * v["PLUG_TIP_T"] * v["PLUG_TIP_L"]
    check(pb, "plug", ([-v["PLUG_W"] / 2, -v["PLUG_T"] / 2, -v["PLUG_L"]], [v["PLUG_W"] / 2, v["PLUG_T"] / 2, v["PLUG_TIP_L"]]),
          vol, edit=("PLUG_L", v["PLUG_L"] + 5, 2, 5))
    return pb.save(os.path.join(OUT, "ref_usbc_plug.sldprt"))


def edge_plugs(sw):
    """Plugs in the PCB edge connectors P2, P4 (bottom edge) and P1 (USB edge) with the room their wires
    need to bend back. Placed in the global frame (PCB front face Z=0)."""
    import encl as E
    pb = PartBuilder(sw, E.P)
    pb.plane("PL_PCB_BACK", "-PCB_T")
    yb = "-PCB_H/2 + (CONN_ON_PCB - WIRE_ROOM)/2"
    with pb.sketch("PL_PCB_BACK", "SK_BOTTOM") as s:
        for x in ("P2_X", "P4_X"):
            s.rect(x, yb, "CONN_W", "CONN_ON_PCB + WIRE_ROOM")
    pb.extrude("SK_BOTTOM", "CONN_H", "PLUGS_BOTTOM", reverse=True)
    with pb.sketch("PL_PCB_BACK", "SK_P1") as s:
        s.rect(f"{E.USB_SGN}(PCB_W/2 + (WIRE_ROOM - CONN_ON_PCB)/2)", "P1_Y", "CONN_ON_PCB + WIRE_ROOM", "CONN_W")
    pb.extrude("SK_P1", "CONN_H", "PLUG_P1", reverse=True)
    v = E.P
    box = v["CONN_W"] * (v["CONN_ON_PCB"] + v["WIRE_ROOM"]) * v["CONN_H"]
    errs = pb.rebuild_errors()
    print(f"[edge_plugs] bodies={len(pb.bodies())} errors={errs} volume {pb.volume():.1f} (expected {3 * box:.1f})")
    assert not errs and len(pb.bodies()) == 3 and abs(pb.volume() - 3 * box) < 0.01
    return pb.save(os.path.join(OUT, "ref_edge_plugs.sldprt"))


PARTS = {"display": display, "led": led, "radar": radar, "atom": atom, "plug": plug, "edge_plugs": edge_plugs}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    sw = connect()
    close_out_docs(sw)
    for k, fn in PARTS.items():
        if which in (k, "all"):
            print("saved", fn(sw))
