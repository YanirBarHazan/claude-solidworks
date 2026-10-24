"""Self test of hand-edit protection (partsync + PartBuilder update mode). Writes only to a temp folder.

1. the script builds a plate (manifest written)
2. "the user" edits it by hand: adds a hole feature and changes a global variable
3. check() must report both; decide() must stop and ask (exit 3)
4. --adopt writes the changed value into the params file
5. update mode with one NEW script feature: existing features skipped, the new one appended,
   the hand-made hole kept
6. a changed definition of an existing feature must raise SyncConflict
"""
import os
import sys
import tempfile

OUT_DIR = tempfile.mkdtemp(prefix="sw_sync_")
os.environ["SW_OUT"] = OUT_DIR
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sw_common import connect, close_out_docs, T, swconst, save_as  # noqa: E402
from swcad import PartBuilder, SyncConflict  # noqa: E402
import partsync  # noqa: E402

C = swconst.constants
PATH = os.path.join(OUT_DIR, "sync_plate.sldprt")
PARAMS_PY = os.path.join(OUT_DIR, "params_test.py")


def script(sw, params, mode, with_slot=False, wide_window=False):
    pb = PartBuilder(sw, params, path=PATH, mode=mode)
    with pb.sketch("Front Plane", "SK_PLATE") as s:
        s.rrect(0, 0, "W", "H", "R")
    pb.extrude("SK_PLATE", "T", "PLATE")
    with pb.sketch("Front Plane", "SK_WINDOW") as s:
        s.rect(0, 0, "W/2 + 4" if wide_window else "W/2", "H/2")
    pb.cut("SK_WINDOW", "T", "WINDOW", reverse=False)
    if with_slot:                                   # the change the script brings later
        with pb.sketch("Front Plane", "SK_SLOT") as s:
            s.rect("W/2 - 5", 0, 2, "H/2")
        pb.cut("SK_SLOT", "T", "SLOT", reverse=False)
    return pb


def hand_edit(sw):
    """What a user might do in SolidWorks: a new hole, and W changed in Tools > Equations."""
    r = sw.OpenDoc6(PATH, C.swDocPART, C.swOpenDocOptions_Silent, "", 0, 0)
    doc = T(r[0], "IModelDoc2")
    sw.ActivateDoc3(doc.GetTitle(), False, 0, 0)
    part = T(doc, "IPartDoc")
    T(part.FeatureByName("Front Plane"), "IFeature").Select2(False, 0)
    doc.SketchManager.InsertSketch(True)
    doc.SketchManager.CreateCircleByRadius(-0.015, 0.008, 0, 0.002)
    doc.SketchManager.InsertSketch(True)
    T(doc.FeatureByPositionReverse(0), "IFeature").Name = "MY_HOLE_SKETCH"
    T(part.FeatureByName("MY_HOLE_SKETCH"), "IFeature").Select2(False, 0)
    f = doc.FeatureManager.FeatureCut4(True, False, True, 0, 0, 0.003, 0, False, False, False, False, 0, 0,
                                       False, False, False, False, False, True, True, True, True, False, 0, 0,
                                       False, False)
    T(f, "IFeature").Name = "MY_HOLE"
    eq = T(doc.GetEquationMgr(), "IEquationMgr")
    for i in range(eq.GetCount()):
        if eq.Equation(i).startswith('"W"'):
            eq.SetEquation(i, '"W" = 44')
    eq.EvaluateAll()
    doc.ForceRebuild3(False)
    save_as(doc, PATH)
    sw.CloseDoc(doc.GetTitle())


def main():
    sw = connect()
    close_out_docs(sw)
    params = {"W": 40.0, "H": 30.0, "T": 3.0, "R": 3.0}
    open(PARAMS_PY, "w").write("P = dict(W=40.0, H=30.0, T=3.0, R=3.0)\n")

    pb = script(sw, params, "build"); pb.save(PATH); sw.CloseDoc(pb.doc.GetTitle())
    rep = partsync.check(sw, PATH)
    print("1. fresh build ->", partsync.describe(rep).splitlines()[0])
    assert not rep["drift"]

    hand_edit(sw)
    rep = partsync.check(sw, PATH)
    print("2.", partsync.describe(rep))
    assert [n for n, _ in rep["added_features"]] == ["MY_HOLE_SKETCH", "MY_HOLE"]
    assert rep["globals_changed"] == {"W": [40.0, 44.0]}

    try:
        partsync.decide(sw, PATH, PARAMS_PY, argv=[])
        raise AssertionError("decide() should have stopped")
    except SystemExit as e:
        print("3. decide() stopped for the user, exit code", e.code)
        assert e.code == partsync.EXIT_NEEDS_USER

    mode = partsync.decide(sw, PATH, PARAMS_PY, argv=["--adopt"])
    adopted = open(PARAMS_PY).read()
    print("4. --adopt ->", adopted.strip(), "| mode:", mode)
    assert "W=44.0" in adopted and mode == "update"
    params["W"] = 44.0

    pb = script(sw, params, "update", with_slot=True)
    skipped = [n for n in pb.specs if n in pb.existing]
    added = [n for n in pb.specs if n not in pb.existing]
    pb.save(PATH)
    names = []
    f = pb.doc.FirstFeature()
    while f is not None:
        f = T(f, "IFeature"); names.append(f.Name); f = f.GetNextFeature()
    print(f"5. update: skipped {skipped}, appended {added}, hand-made kept: {'MY_HOLE' in names}, "
          f"errors {pb.rebuild_errors()}")
    assert added == ["SK_SLOT", "SLOT"] and "MY_HOLE" in names and not pb.rebuild_errors()
    assert names.index("SLOT") > names.index("MY_HOLE")
    sw.CloseDoc(pb.doc.GetTitle())
    rep = partsync.check(sw, PATH)
    assert not rep["drift"], "after the update the manifest must match the file"

    try:
        script(sw, params, "update", with_slot=True, wide_window=True)
        raise AssertionError("changed definition not detected")
    except SyncConflict as e:
        print("6. changed definition ->", str(e).splitlines()[0])
    close_out_docs(sw)
    print("SYNC TEST OK")


if __name__ == "__main__":
    main()
