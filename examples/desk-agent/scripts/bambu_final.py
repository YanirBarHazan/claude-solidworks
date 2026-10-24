"""One Bambu Studio project with every final part, arranged on as many A1 plates as needed and sliced.
The diffuser gets filament 2 (white) so the arranger keeps it on its own plate.
    python bambu_final.py            -> bambu/desk_agent_all_plates.3mf + summary
"""
import os
import subprocess

import bambu_projects as B

STLS = ["back_body.stl", "front_frame.stl", "hinge_block.stl", "stand_leg.stl", "hinge_pin.stl"]   # diffuser: own project (white)
FILAMENT_IDS = [1, 1, 1, 1, 1]
NAME = "desk_agent_all_plates"


def build():
    fil = B.FILAMENT
    cmd = [B.EXE, "--load-settings", f"{B.PROCESS};{B.MACHINE}", "--load-filaments", fil,
           "--load-filament-ids", ",".join(map(str, FILAMENT_IDS)),
           "--arrange", "1", "--orient", "0", "--slice", "0",
           "--export-3mf", NAME + ".3mf", "--outputdir", B.OUTDIR] + \
          [os.path.join(B.HERE, "print_final", f) for f in STLS]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=B.OUTDIR)
    open(os.path.join(B.TMP, NAME + ".log"), "w", encoding="utf-8").write(r.stdout + r.stderr)
    path = os.path.join(B.OUTDIR, NAME + ".3mf")
    assert r.returncode == 0 and os.path.exists(path), f"Bambu CLI failed ({r.returncode}), see {B.TMP}"
    return path


if __name__ == "__main__":
    p = build()
    import re
    import zipfile
    si = zipfile.ZipFile(p).read("Metadata/slice_info.config").decode()
    total_min = total_g = 0
    for pl in re.findall(r"<plate>(.*?)</plate>", si, re.S):
        g = lambda k: re.search(rf'key="{k}" value="([^"]*)"', pl).group(1)
        objs = [os.path.basename(o) for o in re.findall(r'<object[^>]*name="([^"]+)"', pl)]
        fils = re.findall(r'<filament id="(\d+)"', pl)
        warns = re.findall(r'<warning[^>]*msg="([^"]+)"', pl)
        total_min += int(g("prediction")) // 60
        total_g += float(g("weight"))
        print(f"plate {g('index')}: {int(g('prediction')) // 60} min, {g('weight')} g, filament {fils}, "
              f"support={g('support_used')}, outside={g('outside')}, warnings={warns}\n    {objs}")
    print(f"total {total_min // 60} h {total_min % 60} min, {total_g:.1f} g -> {p}")


