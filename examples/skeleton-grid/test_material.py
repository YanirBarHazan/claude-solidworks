"""Small live test: real material + mass check + linked properties (PartBuilder), and filesafe on a SolidWorks save.
A 100 mm steel cube must weigh 7.8 kg; the Weight / Material properties must follow the model; a file touched after
the script wrote it must be backed up before the next save."""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "skill", "solidworks-api", "scripts"))
CAD = os.path.join(HERE, "cad")
os.environ["SW_OUT"] = CAD
from sw_common import connect, close_out_docs, save_as  # noqa: E402
from swcad import PartBuilder  # noqa: E402
import filesafe  # noqa: E402

path = os.path.join(CAD, "CUBE_STEEL.sldprt")
for e in ("", ".manifest.json"):
    if os.path.exists(path + e):
        os.remove(path + e)
sw = connect()
close_out_docs(sw)
pb = PartBuilder(sw, {"A": 100.0})
with pb.sketch("Front Plane", "SK_CUBE") as s:
    s.rect(0, 0, "A", "A")
pb.extrude("SK_CUBE", "A", "CUBE_BODY")
try:
    pb.material("No Such Steel")
    print("FAIL a wrong material name was accepted")
except RuntimeError as ex:
    print(f"OK   wrong material name rejected ({str(ex)[:60]})")
pb.material("Plain Carbon Steel")
m, want = pb.check_mass(7800.0)
print(f"OK   material Plain Carbon Steel: mass {m:.4f} kg = volume x 7800 = {want:.4f} kg")
try:
    pb.check_mass(2700.0)
    print("FAIL mass check passed with the wrong density")
except RuntimeError:
    print("OK   mass check fails for a wrong expected density (2700)")
pb.save(path)
props = pb.link_properties()
ok = abs(float(str(props["Weight"]).replace(",", ".")) - m * 1000) < 1      # MMGS document: grams and props["Material"] == "Plain Carbon Steel"
print(f"{'OK  ' if ok else 'FAIL'} linked properties: {props}")
print(f"{'OK  ' if filesafe.status(path) == 'ours' else 'FAIL'} filesafe after the script's save: {filesafe.status(path)}")
os.utime(path, (time.time() + 5, time.time() + 5))            # someone else touched the file
st = filesafe.status(path)
save_as(pb.doc, path)
copy = os.path.join(filesafe.backup_dir(path), os.path.basename(path))
print(f"{'OK  ' if st == 'changed' and os.path.exists(copy) and filesafe.status(path) == 'ours' else 'FAIL'} "
      f"touched file: status {st}, backed up before the next save: {os.path.exists(copy)}, then {filesafe.status(path)}")
sw.CloseDoc(pb.doc.GetTitle())
close_out_docs(sw)
