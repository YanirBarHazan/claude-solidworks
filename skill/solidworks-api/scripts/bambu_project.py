"""Build a sliced Bambu Studio project (.3mf) from print-oriented STLs, using the user's installed
system presets, and report Bambu's own result (time, grams, support used, warnings).

    python bambu_project.py --name plate1 --outdir bambu  a.stl b.stl ...
        [--printer "Bambu Lab A1 0.4 nozzle"] [--process "0.20mm Standard @BBL A1"]
        [--filament "Bambu PLA Basic @BBL A1"]
    python bambu_project.py --summary bambu/plate1.3mf

The printer the user has selected is in %APPDATA%/BambuStudio/BambuStudio.conf ("machine").
System presets use 'inherits' chains; the CLI needs complete settings, so they are flattened.
Notes: --export-3mf takes a bare file name (it is joined with --outdir); --orient 0 keeps the
orientation you chose; supports stay as the process preset sets them (off in "Standard").
"""
import argparse
import json
import os
import re
import subprocess
import zipfile

EXE = r"C:\Program Files\Bambu Studio\bambu-studio.exe"
SYS = os.path.join(os.environ.get("APPDATA", ""), "BambuStudio", "system", "BBL")


def flatten(kind, name, tmp):
    chain = []
    while name:
        d = json.load(open(os.path.join(SYS, kind, name + ".json"), encoding="utf-8"))
        chain.append(d)
        name = d.get("inherits", "")
    full = {}
    for d in reversed(chain):
        full.update(d)
    full.pop("inherits", None)
    full["from"] = "system"
    out = os.path.join(tmp, f"{kind}.json")
    json.dump(full, open(out, "w", encoding="utf-8"), indent=1)
    return out


def user_printer():
    try:
        conf = open(os.path.join(os.environ["APPDATA"], "BambuStudio", "BambuStudio.conf"), encoding="utf-8").read()
        m = re.search(r'"machine":\s*"([^"]+)"', conf)
        return m.group(1) if m else None
    except OSError:
        return None


def summary(path):
    si = zipfile.ZipFile(path).read("Metadata/slice_info.config").decode()
    rows = []
    for p in re.findall(r"<plate>(.*?)</plate>", si, re.S):
        g = lambda k: re.search(rf'key="{k}" value="([^"]*)"', p).group(1)
        rows.append(dict(plate=g("index"), minutes=int(g("prediction")) // 60, grams=float(g("weight")),
                         support=g("support_used"), outside=g("outside"),
                         warnings=re.findall(r'<warning[^>]*msg="([^"]+)"', p),
                         objects=[os.path.basename(o) for o in re.findall(r'<object[^>]*name="([^"]+)"', p)]))
    return rows


def build(name, outdir, stls, printer, process, filament):
    os.makedirs(outdir, exist_ok=True)
    tmp = os.path.join(outdir, "_profiles")
    os.makedirs(tmp, exist_ok=True)
    m, pr, fi = flatten("machine", printer, tmp), flatten("process", process, tmp), flatten("filament", filament, tmp)
    cmd = [EXE, "--load-settings", f"{pr};{m}", "--load-filaments", fi, "--arrange", "1", "--orient", "0",
           "--slice", "0", "--export-3mf", name + ".3mf", "--outputdir", os.path.abspath(outdir)] + \
          [os.path.abspath(s) for s in stls]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=outdir)
    open(os.path.join(tmp, name + ".log"), "w", encoding="utf-8").write(r.stdout + r.stderr)
    path = os.path.join(outdir, name + ".3mf")
    if r.returncode or not os.path.exists(path):
        raise SystemExit(f"Bambu CLI failed ({r.returncode}); see {tmp}\\{name}.log")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stls", nargs="*")
    ap.add_argument("--name")
    ap.add_argument("--outdir", default="bambu")
    ap.add_argument("--printer", default=None)
    ap.add_argument("--process", default=None)
    ap.add_argument("--filament", default=None)
    ap.add_argument("--summary")
    a = ap.parse_args()
    if a.summary:
        path = a.summary
    else:
        printer = a.printer or user_printer() or "Bambu Lab A1 0.4 nozzle"
        model = printer.replace("Bambu Lab ", "").split(" ")[0]          # e.g. A1, X1C, P1S
        process = a.process or f"0.20mm Standard @BBL {model}"
        filament = a.filament or f"Bambu PLA Basic @BBL {model}"
        path = build(a.name, a.outdir, a.stls, printer, process, filament)
        print(f"{path}  [{printer} | {process} | {filament}]")
    for row in summary(path):
        print(f"plate {row['plate']}: {row['minutes']} min, {row['grams']} g, support={row['support']}, "
              f"outside={row['outside']}, warnings={row['warnings']}\n    {row['objects']}")
