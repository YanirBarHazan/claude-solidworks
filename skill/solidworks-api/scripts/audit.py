"""Model health / editability audit of ANY existing SolidWorks part or assembly. Read-only: nothing is saved.
  python audit.py <file.sldprt|.sldasm> [more files] [--props PartNo,Description] [--out folder]
One summary line per file + <out>/<name>.audit.json. The score (0-100) is a heuristic, not a standard:
it turns "is this model easy for a human to understand and change" into numbers that can be compared before / after.

Part:      default-named features (Boss-Extrude1, Sketch7), sketches not fully defined, rebuild errors / warnings,
           material + mass, missing custom properties, global variables / equations.
Assembly:  top-level components: fixed, floating (not fixed, no mates, not a pattern instance), pattern instances,
           suppressed, missing files; mates and mate errors; patterns; configurations.
Documents already open are left open; documents opened here are closed without saving."""
import collections
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sw_common import connect, T, swconst  # noqa: E402

C = swconst.constants
DEFAULT_NAME = re.compile(
    r"^(Boss-Extrude|Cut-Extrude|Extrude-Thin|Cut-Extrude-Thin|Extrude|Sketch|3DSketch|Plane|Axis|Point|Fillet|"
    r"Chamfer|Revolve|Cut-Revolve|Sweep|Cut-Sweep|Loft|Cut-Loft|Shell|Rib|Draft|Dome|Mirror|LPattern|CirPattern|"
    r"Curve Driven Pattern|Sketch-Driven Pattern|Hole|Wrap|Flex|Combine|Split|Scale|Move/Copy|Base-Flange|"
    r"Edge-Flange|Miter Flange|Hem|Jog|Sketched Bend|Unfold|Fold|Structural Member|Trim/Extend|Gusset|End cap|"
    r"Weld Bead|LocalLPattern|LocalCirPattern|DerivedLPattern|DerivedCirPattern)\d+$")
SKETCH_TYPES = ("ProfileFeature", "3DProfileFeature")
# system / container nodes that are not modelling decisions
SKIP_TYPES = {"HistoryFolder", "SensorFolder", "DetailCabinet", "SurfaceBodyFolder", "SolidBodyFolder", "CommentsFolder",
              "FavoriteFolder", "SelectionSetFolder", "EnvFolder", "InkMarkupFolder", "EqnFolder", "MaterialFolder",
              "OriginProfileFeature", "DocsFolder", "TableFolder", "CutListFolder", "SubWeldFolder", "MateGroup",
              "FtrFolder", "BlockFolder", "NotesAreaFtrFolder", "LiveSectionFolder", "MarkupCommentFolder"}
SKIP_TYPES |= {"AmbientLight", "DirectionLight", "PointLight", "SpotLight", "CameraFeature"}
STD_NAMES = {"Front Plane", "Top Plane", "Right Plane", "Origin"}
COMP_PATTERNS = {"LocalLPattern", "LocalCirPattern", "LocalSketchPattern", "LocalCurvePattern", "DerivedLPattern",
                 "DerivedCirPattern", "LocalChainPattern", "MirrorComponent"}
CONSTRAINED = {1: "unknown", 2: "under", 3: "full", 4: "over", 5: "no solution", 6: "invalid", 7: "autosolve off"}


def walk(doc):
    """Every feature once: top level + sub-features (absorbed sketches live there). ONE pass (COM is the cost)."""
    seen, out = set(), []

    def visit(f, depth):
        while f is not None:
            f = T(f, "IFeature")
            key = (f.Name, f.GetTypeName2())
            if key not in seen:
                seen.add(key)
                out.append(f)
                if depth < 3:
                    visit(f.GetFirstSubFeature(), depth + 1)
            f = f.GetNextSubFeature() if depth else f.GetNextFeature()
    visit(doc.FirstFeature(), 0)
    return out


def errors_of(f):
    try:
        r = f.GetErrorCode2()
        code, warn = (r[0], r[1]) if isinstance(r, tuple) else (r, False)
        return code, bool(warn)
    except Exception:
        return 0, False


def common(doc, feats, props):
    out = {}
    errs = [(f.Name, errors_of(f)) for f in feats]
    out["rebuild_errors"] = [n for n, (c, w) in errs if c and not w]
    out["rebuild_warnings"] = [n for n, (c, w) in errs if c and w]
    cpm = T(doc.Extension.CustomPropertyManager(""), "ICustomPropertyManager")
    names = list(cpm.GetNames() or [])
    out["properties"] = names
    out["missing_properties"] = [p for p in props if p not in names]
    eq = T(doc.GetEquationMgr(), "IEquationMgr")
    n = eq.GetCount()
    out["equations"] = n
    out["global_variables"] = sum(1 for i in range(n) if eq.GlobalVariable(i))
    out["configurations"] = doc.GetConfigurationCount()
    return out


def audit_part(doc, feats, props):
    r = common(doc, feats, props)
    model = [f for f in feats if f.GetTypeName2() not in SKIP_TYPES and f.Name not in STD_NAMES]
    r["features"] = len(model)
    r["default_named"] = [f.Name for f in model if DEFAULT_NAME.match(f.Name)]
    sk = [f for f in model if f.GetTypeName2() in SKETCH_TYPES]
    status = collections.Counter()
    not_full = []
    for f in sk:
        try:
            st = T(f.GetSpecificFeature2(), "ISketch").GetConstrainedStatus()
        except Exception:
            st = 1
        status[CONSTRAINED.get(st, str(st))] += 1
        if st != 3:
            not_full.append(f"{f.Name} ({CONSTRAINED.get(st, st)})")
    r["sketches"] = len(sk)
    r["sketch_status"] = dict(status)
    r["sketches_not_fully_defined"] = not_full
    mat = T(doc, "IPartDoc").GetMaterialPropertyName2("", "")
    name = mat[0] if isinstance(mat, tuple) else mat
    r["material"] = name or None
    try:
        mp = doc.Extension.CreateMassProperty()
        r["mass_kg"] = round(mp.Mass, 4) if (mp is not None and name) else None      # no material = default density
    except Exception:
        r["mass_kg"] = None
    n = max(1, r["features"])
    score = 100.0
    score -= 30.0 * len(r["default_named"]) / n
    score -= 30.0 * len(not_full) / max(1, len(sk))
    score -= 15.0 if not r["material"] else 0.0
    score -= 10.0 * len(r["missing_properties"]) / max(1, len(props))
    score -= 15.0 if r["rebuild_errors"] else (5.0 if r["rebuild_warnings"] else 0.0)
    r["score"] = round(max(0.0, score))
    r["line"] = (f"features {r['features']} (default names {len(r['default_named'])}), sketches {len(sk)} "
                 f"(not fully defined {len(not_full)}), material {r['material'] or 'NONE'}, mass "
                 f"{str(r['mass_kg']) + ' kg' if r['mass_kg'] is not None else 'n/a (no material)'}, globals {r['global_variables']}, missing props {r['missing_properties'] or 0}, "
                 f"errors {len(r['rebuild_errors'])}")
    return r


def audit_assembly(doc, feats, props):
    r = common(doc, feats, props)
    asm = T(doc, "IAssemblyDoc")
    comps = [T(c, "IComponent2") for c in (asm.GetComponents(True) or [])]
    fixed = floating = inst = supp = 0
    missing, files = [], collections.Counter()
    for c in comps:
        path = c.GetPathName()
        files[os.path.basename(path)] += 1
        if not os.path.exists(path):
            missing.append(os.path.basename(path))
        if c.GetSuppression2() == 0:
            supp += 1
            continue
        if c.IsPatternInstance():
            inst += 1
        elif c.IsFixed():
            fixed += 1
        elif not c.GetMates():
            floating += 1
    mates, mate_errs = 0, []
    patterns = 0
    for f in feats:
        t = f.GetTypeName2()
        if t.startswith("Mate") and t != "MateGroup":
            mates += 1
            code, warn = errors_of(f)
            if code:
                mate_errs.append(f.Name)
        elif t in COMP_PATTERNS:
            patterns += 1
    placed = len(comps) - inst - supp
    mated = placed - fixed - floating
    r.update(components=len(comps), distinct_files=len(files), placed=placed, fixed=fixed, mated=mated,
             floating=floating, pattern_instances=inst, suppressed=supp, missing_files=sorted(set(missing)),
             mates=mates, mate_errors=mate_errs, patterns=patterns)
    score = 100.0
    if placed > 1:
        score -= 50.0 * max(0, fixed - 1) / (placed - 1)      # one fixed base component is good practice
        score -= 20.0 * floating / placed
    score -= 20.0 if mate_errs else 0.0
    score -= 10.0 if missing else 0.0
    score -= 10.0 if r["rebuild_errors"] else 0.0
    r["score"] = round(max(0.0, score))
    r["line"] = (f"components {len(comps)} ({len(files)} files): placed {placed} = fixed {fixed} + mated {mated} + "
                 f"floating {floating}; pattern instances {inst} from {patterns} patterns; suppressed {supp}; "
                 f"mates {mates} (errors {len(mate_errs)}); configurations {r['configurations']}; "
                 f"missing files {len(set(missing))}")
    return r


def audit(sw, path, props):
    t0 = time.time()
    path = os.path.abspath(path)
    is_asm = path.lower().endswith(".sldasm")
    was_open = sw.GetOpenDocumentByName(path) is not None
    if was_open:
        doc = T(sw.GetOpenDocumentByName(path), "IModelDoc2")
    else:
        r = sw.OpenDoc6(path, C.swDocASSEMBLY if is_asm else C.swDocPART,
                        C.swOpenDocOptions_Silent | C.swOpenDocOptions_ReadOnly, "", 0, 0)
        doc = T(r[0], "IModelDoc2") if r[0] is not None else None
    if doc is None:
        return dict(file=os.path.basename(path), ok=False, line="cannot open", score=None)
    try:
        feats = walk(doc)
        res = (audit_assembly if is_asm else audit_part)(doc, feats, props)
    finally:
        if not was_open:
            sw.CloseDoc(doc.GetTitle())
    res.update(file=os.path.basename(path), kind="assembly" if is_asm else "part", ok=True,
               seconds=round(time.time() - t0, 1))
    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "") for a in sys.argv[1:] if a.startswith("--"))
    for k in ("props", "out"):
        if k in opt and not opt[k]:
            i = sys.argv.index("--" + k)
            opt[k] = sys.argv[i + 1]
            args.remove(opt[k])
    props = [p for p in opt.get("props", "PartNo,Description").split(",") if p]
    out = opt.get("out", os.path.join(os.getcwd(), "audit"))
    if not args:
        print(__doc__)
        return 2
    os.makedirs(out, exist_ok=True)
    sw = connect()
    scores = []
    for path in args:
        res = audit(sw, path, props)
        name = os.path.splitext(res["file"])[0]
        json.dump(res, open(os.path.join(out, name + ".audit.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"AUDIT {res['file']}  score {res['score']}/100  {res['line']}  ({res.get('seconds', 0)} s)", flush=True)
        if res["score"] is not None:
            scores.append(res["score"])
    if len(scores) > 1:
        print(f"AUDIT {len(scores)} files: mean score {sum(scores) / len(scores):.0f}, lowest {min(scores)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
