"""Build Bambu Studio projects (.3mf) for the A1: arranged plates, sliced by Bambu's own engine.

Profiles are the user's installed system presets (A1 0.4, 0.20mm Standard, Bambu PLA Basic),
flattened through their 'inherits' chain because the CLI needs complete settings.
Supports are OFF on purpose: every part was checked support-free (overhangs.py); the slice
log is then checked for floating-region / overhang warnings.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EXE = r"C:\Program Files\Bambu Studio\bambu-studio.exe"
SYS = os.path.join(os.environ["APPDATA"], "BambuStudio", "system", "BBL")
OUTDIR = os.path.join(HERE, "bambu")
TMP = os.path.join(OUTDIR, "_profiles")
os.makedirs(TMP, exist_ok=True)


def flatten(kind, name):
    folder = os.path.join(SYS, kind)
    chain = []
    while name:
        path = os.path.join(folder, name + ".json")
        d = json.load(open(path, encoding="utf-8"))
        chain.append(d)
        name = d.get("inherits", "")
    full = {}
    for d in reversed(chain):
        full.update(d)
    full.pop("inherits", None)
    full["from"] = "system"
    out = os.path.join(TMP, f"{kind}.json")
    json.dump(full, open(out, "w", encoding="utf-8"), indent=1)
    return out


MACHINE = flatten("machine", "Bambu Lab A1 0.4 nozzle")
PROCESS = flatten("process", "0.20mm Standard @BBL A1")
FILAMENT = flatten("filament", "Bambu PLA Basic @BBL A1")

PROJECTS = {
    "1_test_pieces": ["print_tests/" + f for f in ("test_A_lip.stl", "test_A_wall.stl", "test_B_frame.stl",
                                                   "test_C_base.stl", "test_C_leg.stl", "test_C_pin.stl")],
    "2_back_body": ["print_final/back_body.stl"],
    "3_front_frame_and_stand": ["print_final/" + f for f in ("front_frame.stl", "hinge_block.stl",
                                                             "stand_leg.stl", "hinge_pin.stl")],
    "4_diffuser_white_PLA": ["print_final/diffuser.stl"],
    "5_reprint_front_frame": ["print_final/front_frame.stl"],
}


def build(name, files):
    out3mf = os.path.join(OUTDIR, name + ".3mf")
    cmd = [EXE, "--load-settings", f"{PROCESS};{MACHINE}", "--load-filaments", FILAMENT,
           "--arrange", "1", "--orient", "0", "--slice", "0", "--export-3mf", name + ".3mf",
           "--outputdir", OUTDIR] + [os.path.join(HERE, f) for f in files]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=OUTDIR)
    log = r.stdout + r.stderr
    open(os.path.join(TMP, name + ".log"), "w", encoding="utf-8").write(log)
    return r.returncode, out3mf, log


if __name__ == "__main__" and sys.argv[1:] == ["summary"]:
    summary()
elif __name__ == "__main__":
    only = sys.argv[1:] or list(PROJECTS)
    for name in only:
        code, path, log = build(name, PROJECTS[name])
        warn = [l for l in log.splitlines() if any(k in l.lower() for k in ("floating", "overhang", "support", "warning", "error", "fail"))]
        print(f"{name}: exit {code}, 3mf {'OK' if os.path.exists(path) else 'MISSING'}")
        for l in warn[-12:]:
            print("   ", l[-200:])


def summary():
    import glob
    import re
    import zipfile
    for f in sorted(glob.glob(os.path.join(OUTDIR, "*.3mf"))):
        si = zipfile.ZipFile(f).read("Metadata/slice_info.config").decode()
        for p in re.findall(r"<plate>(.*?)</plate>", si, re.S):
            g = lambda k: re.search(rf'key="{k}" value="([^"]*)"', p).group(1)
            objs = [os.path.basename(o) for o in re.findall(r'<object[^>]*name="([^"]+)"', p)]
            warns = re.findall(r'<warning[^>]*msg="([^"]+)"', p)
            print(f"{os.path.basename(f)} plate {g('index')}: {int(g('prediction')) // 60} min, {g('weight')} g, "
                  f"support={g('support_used')}, outside={g('outside')}, warnings={warns}")
            print("    ", objs)
