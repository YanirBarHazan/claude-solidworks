"""Small live test of the hand + script flow (roadmap phase 3) and the sketch gate (phase 5):
1. the script builds a plate from a parameter text file (A = 100);
2. a "human" opens the part in SolidWorks, changes the global A to 120 in the equations, adds a hole of his own
   (feature USER_HOLE), saves;
3. the next script run: detects both, PULLS A = 120 into the parameter file (with a note), keeps USER_HOLE,
   and does not overwrite anything;
4. both sides changed (file 140, parameter file 150) -> conflict, nothing is written."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "skill", "solidworks-api", "scripts"))
CAD = os.path.join(HERE, "cad")
os.environ["SW_OUT"] = CAD
from sw_common import connect, close_out_docs, save_doc, T, swconst  # noqa: E402
from swcad import PartBuilder  # noqa: E402
from asmtools import set_equation  # noqa: E402
import partsync  # noqa: E402
import paramfile  # noqa: E402

C = swconst.constants
MM = 1e-3
path = os.path.join(CAD, "PLATE_2WAY.sldprt")
ptxt = os.path.join(HERE, "twoway_params.txt")
open(ptxt, "w", encoding="utf-8").write("[PLATE]\nA               = 100        ; [D] plate side\nT               = 10         ; [D] thickness\n")
for e in ("", ".manifest.json"):
    if os.path.exists(path + e):
        os.remove(path + e)


def build(pb):
    with pb.sketch("Front Plane", "SK_PLATE") as s:
        s.rect(0, 0, "A", "A")
    pb.extrude("SK_PLATE", "T", "PLATE_BODY")


def expect(p):
    return (p["A"], p["A"], p["T"]), p["A"] * p["A"] * p["T"]


sw = connect()
close_out_docs(sw)
# 1. script build
P = paramfile.values(ptxt)
pb = PartBuilder(sw, P)
build(pb)
pb.verify(expect)                                   # includes the fully-defined-sketch gate
print(f"OK   1 built from the parameter file, sketches not fully defined: {pb.open_sketches()}")
pb.save(path)
sw.CloseDoc(pb.doc.GetTitle())

# 2. the human: change A in the equations, add a hole, plain save
doc = T(sw.OpenDoc6(path, C.swDocPART, C.swOpenDocOptions_Silent, "", 0, 0)[0], "IModelDoc2")
sw.ActivateDoc3(doc.GetTitle(), False, 0, 0)
set_equation(doc, "A", "120")
doc.ForceRebuild3(False)
doc.Extension.SelectByID2("Front Plane", "PLANE", 0, 0, 0, False, 0, None, 0)
doc.SketchManager.InsertSketch(True)
doc.SketchManager.CreateCircleByRadius(0.02, 0.02, 0, 0.005)
doc.SketchManager.InsertSketch(True)
doc.Extension.SelectByID2("Sketch2", "SKETCH", 0, 0, 0, False, 0, None, 0)
hole = doc.FeatureManager.FeatureCut4(True, False, True, C.swEndCondThroughAll, 0, 0.01, 0.01, False, False, False, False,
                                      0, 0, False, False, False, False, False, True, True, True, True, False, 0, 0,
                                      False, False)
if hole is not None:
    T(hole, "IFeature").Name = "USER_HOLE"
doc.Save3(1, 0, 0)
sw.CloseDoc(doc.GetTitle())
print(f"OK   2 hand edit saved: A = 120 in the equations, hole {'USER_HOLE added' if hole is not None else 'NOT added'}")

# 3. next script run
P = paramfile.values(ptxt)
pb = PartBuilder(sw, P, path=path, mode="update")
rep = partsync.check_open(pb.doc, path)
pull, same, conflict = partsync.classify_values(rep["globals_changed"], P)
added = [n for n, _ in rep["added_features"]]
ok = pull == {"A": (100.0, 120.0)} and not conflict and partsync.additive_only(rep)
print(f"{'OK  ' if ok else 'FAIL'} 3 detected: pull {pull}, conflict {conflict}, hand features {added}, additive only "
      f"{partsync.additive_only(rep)}")
for k, (a, b) in pull.items():
    paramfile.set_value(ptxt, k, b, "from SolidWorks")
    P[k] = pb.params[k] = b
build(pb)                                            # update mode: existing features skipped
changed = pb.push_globals()
lo, hi = pb.bbox()
size = sorted(round(h - l, 3) for l, h in zip(lo, hi))
kept = any(n == "USER_HOLE" for n, _, _ in partsync.part_state(pb.doc)["features"]) if hole is not None else None
line = [l for l in open(ptxt, encoding="utf-8").read().split("\n") if l.startswith("A ")][0]
ok = paramfile.values(ptxt)["A"] == 120 and size == [10.0, 120.0, 120.0] and not changed and kept in (True, None)
print(f"{'OK  ' if ok else 'FAIL'} 3 pulled into the file: {line.strip()!r}; part bbox {size}; script pushed nothing "
      f"({changed}); USER_HOLE kept: {kept}")
pb.save(path)                                        # manifest now holds the accepted state
sw.CloseDoc(pb.doc.GetTitle())

# 4. both sides changed
pull, same, conflict = partsync.classify_values({"A": [120.0, 140.0]}, {"A": 150.0, "T": 10.0})
print(f"{'OK  ' if conflict == {'A': (120.0, 140.0, 150.0)} and not pull else 'FAIL'} 4 both sides changed -> conflict "
      f"{conflict}, pull {pull}")
pb = PartBuilder(sw, paramfile.values(ptxt), path=path, mode="update")
rep = partsync.check_open(pb.doc, path)
print(f"{'OK  ' if not rep['drift'] else 'FAIL'} 5 next run: no hand edits reported ({rep['drift']})")
sw.CloseDoc(pb.doc.GetTitle())
close_out_docs(sw)
