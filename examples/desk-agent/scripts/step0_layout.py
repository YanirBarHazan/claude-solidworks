"""Step 0b: reference layout assembly of the purchased components (positions from the agreed plan).

Assembly frame = display frame: X right, Y up, Z toward the viewer, origin at PCB centre / PCB front face.
Verifies: all components placed, no unexpected interference (the USB-C plug tip inside the
receptacle keep-out is the only expected one), and writes a picture.
"""
import os

import pythoncom
from win32com.client import VARIANT

import params as PR
from sw_common import connect, close_out_docs, new_doc, save_as, T, swconst, OUT

C = swconst.constants
MM = 1e-3

# ---- layout parameters (mm) ----
FRONT_OUTER_Z = PR.DISPLAY["GLASS_T"] + 0.2 + 2.0      # glass + gap + front wall
LED_Y = -48.5            # LED stick centre, top edge 1.5 below the PCB
LED_TOP_Z = FRONT_OUTER_Z - 2.0 - 0.6                   # LED tops 0.6 behind the wall inner face
RADAR_XY = (-50.0, -57.0)
RADAR_FACE_Z = FRONT_OUTER_Z - 1.5 - 0.3                # 1.5 mm window wall + 0.3 gap
ATOM_XY = (50.0, -57.0)
ATOM_FACE_Z = FRONT_OUTER_Z                             # Atom face flush with the front
# ---------------------------------

D = PR.DISPLAY
USB_Y = D["PCB_H"] / 2 - D["USBC_TOP"] - D["USBC_W"] / 2
USB_Z = -D["PCB_T"] - D["USBC_H"] / 2

PLACEMENT = {
    # file: (local X axis, local Y axis, local Z axis, origin)
    "ref_display.sldprt": ((1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, 0)),
    "ref_led_stick.sldprt": ((1, 0, 0), (0, 1, 0), (0, 0, 1), (0, LED_Y, LED_TOP_Z - PR.LED["LED_T"])),
    "ref_radar.sldprt": ((1, 0, 0), (0, 1, 0), (0, 0, 1), (*RADAR_XY, RADAR_FACE_Z)),
    "ref_atom_echo.sldprt": ((1, 0, 0), (0, 1, 0), (0, 0, 1), (*ATOM_XY, ATOM_FACE_Z)),
    # plug tip points -X into the receptacle, width along Y; overmold face at the PCB edge
    "ref_usbc_plug.sldprt": ((0, 1, 0), (0, 0, -1), (-1, 0, 0), (D["PCB_W"] / 2, USB_Y, USB_Z)),
}
EXPECTED_INTERFERENCE = {frozenset({"ref_display", "ref_usbc_plug"}):
                         PR.PLUG["PLUG_TIP_W"] * PR.PLUG["PLUG_TIP_T"] * min(PR.PLUG["PLUG_TIP_L"], D["USBC_L"])}


def build(sw):
    mu = T(sw.GetMathUtility(), "IMathUtility")
    for f in PLACEMENT:
        r = sw.OpenDoc6(os.path.join(OUT, f), C.swDocPART, C.swOpenDocOptions_Silent, "", 0, 0)
        assert r[0] is not None, f"cannot open {f}"
    doc = new_doc(sw, "asm")
    asm = T(doc, "IAssemblyDoc")
    sw.ActivateDoc3(doc.GetTitle(), False, 0, 0)
    comps = {}
    for f, (ax, ay, az, o) in PLACEMENT.items():
        c = T(asm.AddComponent5(os.path.join(OUT, f), 0, "", False, "", 0, 0, 0), "IComponent2")
        assert c is not None, f"AddComponent5 failed for {f}"
        xf = list(ax) + list(ay) + list(az) + [v * MM for v in o] + [1, 0, 0, 0]
        c.Transform2 = mu.CreateTransform(VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, xf))
        comps[f.split(".")[0]] = c
    doc.ClearSelection2(True)
    for c in comps.values():
        c.Select4(True, None, False)
    asm.FixComponent()
    doc.ClearSelection2(True)
    doc.ForceRebuild3(False)
    return doc, asm, comps


def interferences(asm):
    mgr = T(asm.InterferenceDetectionManager, "IInterferenceDetectionMgr")
    mgr.TreatCoincidenceAsInterference = False
    mgr.IncludeMultibodyPartInterferences = False
    found = []
    for itf in (mgr.GetInterferences() or ()):
        itf = T(itf, "IInterference")
        names = frozenset(T(c, "IComponent2").Name2.rsplit("-", 1)[0] for c in itf.Components)
        found.append((names, itf.Volume / MM ** 3))
    mgr.Done()
    return found


def picture(doc, path):
    doc.ShowNamedView2("*Isometric", 7)
    doc.ViewZoomtofit2()
    doc.GraphicsRedraw2()
    ok, errs, warns = doc.Extension.SaveAs(path, 0, 1, None, 0, 0)
    return ok and os.path.exists(path)


if __name__ == "__main__":
    sw = connect()
    close_out_docs(sw)
    doc, asm, comps = build(sw)
    print("components:", sorted(comps))
    for n, c in comps.items():
        box = c.GetBox(False, False)
        print(f"  {n:15s} X[{box[0]/MM:7.2f},{box[3]/MM:7.2f}] Y[{box[1]/MM:7.2f},{box[4]/MM:7.2f}] Z[{box[2]/MM:7.2f},{box[5]/MM:7.2f}]")
    found = interferences(asm)
    bad = []
    for names, vol in found:
        exp = EXPECTED_INTERFERENCE.get(names)
        tag = "expected" if exp is not None and abs(vol - exp) < 0.5 else "UNEXPECTED"
        print(f"  interference {sorted(names)} {vol:.1f} mm3 -> {tag}" + (f" (expected {exp:.1f})" if exp else ""))
        if tag != "expected":
            bad.append(names)
    assert len(comps) == len(PLACEMENT)
    assert not bad, f"unexpected interference: {bad}"
    assert any(n in EXPECTED_INTERFERENCE for n, _ in found), "plug is not inserted in the receptacle"
    print("saved", save_as(doc, os.path.join(OUT, "ref_layout.sldasm")))
    png = os.path.join(OUT, "ref_layout.png")
    print("picture", picture(doc, png), png)
    print("STEP 0 LAYOUT OK")
