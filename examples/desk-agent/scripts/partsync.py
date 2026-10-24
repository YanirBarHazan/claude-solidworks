"""Keep scripts and hand edits from colliding.

Every PartBuilder.save() writes <part>.manifest.json: the script's feature definitions ("specs") and the
state of the saved file ("state": features, suppression, equations, global values). Before a script
touches a part again, check() compares the file on disk with that state and reports what changed by hand.

    python partsync.py <part.sldprt> [...]           # report drift for parts (SolidWorks must be open)

In a build script:
    from partsync import decide
    mode = decide(sw, PATH)       # "build" | "update"; exits with a report (code 3) when a human must choose
Command-line flags a build script then honours (see decide):
    --update   keep hand edits: open the part and append/skip features (default when drift is only added
               or suppressed features)
    --rebuild  rebuild from scratch even though hand edits will be lost (explicit user consent)
    --adopt    copy hand-changed global variable values into params.py, then continue
"""
import json
import os
import re
import sys

from sw_common import T, swconst

C = swconst.constants
EXIT_NEEDS_USER = 3


def part_state(doc):
    """Comparable snapshot of a part: features (name, type, suppressed), equations, global values."""
    feats = []
    f = doc.FirstFeature()
    while f is not None:
        f = T(f, "IFeature")
        sup = f.IsSuppressed2(C.swThisConfiguration, None)
        feats.append([f.Name, f.GetTypeName2(), bool(sup[0]) if sup else False])
        f = f.GetNextFeature()
    eq = T(doc.GetEquationMgr(), "IEquationMgr")
    eqs, glob = [], {}
    for i in range(eq.GetCount()):
        text = eq.Equation(i)
        if eq.GlobalVariable(i):
            glob[text.split("=")[0].strip().strip('"')] = round(eq.Value(i), 6)
        else:
            eqs.append(text.replace(" ", ""))
    return {"features": feats, "equations": sorted(eqs), "globals": glob,
            "linked_file": eq.FilePath if eq.LinkToFile else ""}


def check(sw, path):
    """Drift report between the file on disk and its manifest (what was changed by hand)."""
    path = os.path.abspath(path)                     # SolidWorks cannot open relative paths
    mpath = path + ".manifest.json"
    rep = {"part": os.path.basename(path), "exists": os.path.exists(path), "manifest": os.path.exists(mpath)}
    if not rep["exists"] or not rep["manifest"]:
        rep["drift"] = False
        return rep
    old = json.load(open(mpath, encoding="utf-8"))["state"]
    was_open = sw.GetOpenDocumentByName(path) is not None
    r = sw.OpenDoc6(path, C.swDocPART, C.swOpenDocOptions_Silent, "", 0, 0)
    doc = T(r[0], "IModelDoc2")
    doc.ForceRebuild3(False)
    now = part_state(doc)
    if not was_open:          # left open, it blocks a rebuild from saving under the same name
        sw.CloseDoc(doc.GetTitle())
    of = {n: (t, s) for n, t, s in old["features"]}
    nf = {n: (t, s) for n, t, s in now["features"]}
    rep["added_features"] = [[n, nf[n][0]] for n in nf if n not in of]
    rep["deleted_features"] = [n for n in of if n not in nf]
    rep["suppression_changed"] = [n for n in nf if n in of and nf[n][1] != of[n][1]]
    rep["equations_changed"] = sorted(set(old["equations"]) ^ set(now["equations"]))
    rep["globals_changed"] = {k: [old["globals"].get(k), v] for k, v in now["globals"].items()
                              if k in old["globals"] and abs(v - old["globals"][k]) > 1e-6}
    # globals that now equal what the scripts last wrote to the linked shared file came from that file
    snap = (now["linked_file"] + ".last.json") if now["linked_file"] else ""
    if snap and os.path.exists(snap):
        written = json.load(open(snap, encoding="utf-8"))
        rep["globals_changed"] = {k: ab for k, ab in rep["globals_changed"].items()
                                  if k not in written or abs(written[k] - ab[1]) > 1e-6}
    rep["drift"] = any(rep[k] for k in ("added_features", "deleted_features", "suppression_changed",
                                        "equations_changed", "globals_changed"))
    return rep


def describe(rep):
    lines = [f"== {rep['part']}: " + ("hand edits found" if rep.get("drift") else "no hand edits")]
    for n, t in rep.get("added_features", []):
        lines.append(f"   + feature added by hand: {n} ({t})")
    for n in rep.get("deleted_features", []):
        lines.append(f"   - feature deleted by hand: {n}")
    for n in rep.get("suppression_changed", []):
        lines.append(f"   ~ suppression changed: {n}")
    for k, (a, b) in rep.get("globals_changed", {}).items():
        lines.append(f"   ~ global variable {k}: {a} -> {b}")
    for e in rep.get("equations_changed", [])[:10]:
        lines.append(f"   ~ equation added/removed/edited: {e}")
    return "\n".join(lines)


def adopt_globals(params_py, changes):
    """Write hand-changed global values back into params.py (NAME=value entries)."""
    s = open(params_py, encoding="utf-8").read()
    for name, (_, new) in changes.items():
        s, n = re.subn(rf"(\b{re.escape(name)}=)(-?[0-9.]+)", rf"\g<1>{new}", s, count=1)
        if not n:
            raise KeyError(f"{name} not found in {params_py}")
    open(params_py, "w", encoding="utf-8").write(s)


def decide(sw, path, params_py=None, argv=None):
    """Choose build vs update for one part from its drift and the command-line flags.
    Exits with EXIT_NEEDS_USER and a report when the choice must come from the user."""
    argv = sys.argv if argv is None else argv
    rep = check(sw, path)
    if not rep.get("drift"):
        return "update" if "--update" in argv and rep["exists"] else "build"
    print(describe(rep))
    if rep["globals_changed"] and "--adopt" in argv:
        if not params_py:
            raise SystemExit("--adopt needs the params.py path")
        adopt_globals(params_py, rep["globals_changed"])
        print("   adopted the hand-changed values into params.py")
        rep["globals_changed"] = {}
    if "--rebuild" in argv:
        print("   --rebuild: hand edits in this part will be overwritten (user consent given)")
        return "build"
    only_additive = not (rep["deleted_features"] or rep["equations_changed"] or rep["globals_changed"])
    if "--update" in argv or only_additive:
        print("   -> updating in place: hand-added features are kept")
        return "update"
    print(f"\nNEEDS A DECISION for {rep['part']}: rerun with --update (keep hand edits), "
          f"--adopt (take hand-changed values into params.py) or --rebuild (discard hand edits).")
    raise SystemExit(EXIT_NEEDS_USER)


def check_shared(txt_path, params):
    """Hand edits in the shared equation file since the scripts last wrote it.
    Returns {name: [last_written, file_now, params_py]} for values that differ from what was written."""
    snap = txt_path + ".last.json"
    if not (os.path.exists(txt_path) and os.path.exists(snap)):
        return {}
    last = json.load(open(snap, encoding="utf-8"))
    now = {}
    for line in open(txt_path, encoding="utf-8"):
        m = re.match(r'\s*"([^"]+)"\s*=\s*(-?[0-9.eE+]+)', line)
        if m:
            now[m.group(1)] = float(m.group(2))
    return {k: [last.get(k), v, params.get(k)] for k, v in now.items()
            if k in last and abs(v - last[k]) > 1e-9}


if __name__ == "__main__":
    from sw_common import connect
    sw = connect()
    for p in sys.argv[1:]:
        print(describe(check(sw, p)))
