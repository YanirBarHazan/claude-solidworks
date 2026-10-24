"""Parametric SolidWorks part builder (pywin32 / early binding).

Every dimension is linked by an equation to a Global Variable, so the part can be
edited by hand in SolidWorks (Tools > Equations) and stays consistent.

Expressions are Python strings over the parameter names, e.g. "PCB_W/2 - HOLE_EDGE".
They are evaluated here for the initial geometry and written to SolidWorks with the
names quoted ("PCB_W"/2 - "HOLE_EDGE").
"""
import math
import os
import re

import pythoncom
from win32com.client import VARIANT

from sw_common import connect, new_doc, save_as, T, swconst

C = swconst.constants
MM = 1e-3

# User preferences that break scripted sketching (dimension pop-up, snapping to nearby
# geometry). They are switched off while a script runs and restored on exit.
_SCRIPT_TOGGLES = {"swInputDimValOnCreate": False, "swSketchAutomaticRelations": True,
                   "swSketchInference": False, "swSnapToPoints": False,
                   # centre rectangles get their centre point only with construction lines on
                   "swSketchAddConstToRectEntity": True}
_saved_toggles = {}


def _apply_script_prefs(sw):
    """Switch the toggles for scripting and restore the user's values on exit.
    The originals are also written to a backup file first: if a run is killed (no atexit), the next
    run restores from that file instead of mistaking the script values for the user's own."""
    if _saved_toggles:
        return
    import atexit
    import json
    import tempfile
    backup = os.path.join(tempfile.gettempdir(), "solidworks_api_prefs_backup.json")
    if os.path.exists(backup):                       # previous run did not restore
        _saved_toggles.update({int(k): v for k, v in json.load(open(backup)).items()})
        for name in _SCRIPT_TOGGLES:                 # toggles added since that backup was written
            _saved_toggles.setdefault(getattr(C, name), sw.GetUserPreferenceToggle(getattr(C, name)))
    else:
        for name in _SCRIPT_TOGGLES:
            k = getattr(C, name)
            _saved_toggles[k] = sw.GetUserPreferenceToggle(k)
        json.dump({str(k): v for k, v in _saved_toggles.items()}, open(backup, "w"))
    for name, val in _SCRIPT_TOGGLES.items():
        sw.SetUserPreferenceToggle(getattr(C, name), val)

    def restore():
        try:
            s = connect()
            for k, v in _saved_toggles.items():
                s.SetUserPreferenceToggle(k, v)
            os.remove(backup)
        except Exception:
            pass
    atexit.register(restore)


class SyncConflict(RuntimeError):
    """The existing part and the script disagree in a way that needs the user's decision."""


class PartBuilder:
    def __init__(self, sw, params, path=None, mode="build"):
        """mode="build": new part from scratch (overwrites `path` on save).
        mode="update": open the existing part at `path`; features the script declares that already
        exist with the same definition are skipped, new ones are appended at the end of the tree, a
        feature whose definition changed raises SyncConflict. Features the user added by hand stay."""
        self.sw = sw
        self.params = dict(params)
        self.mode, self.path = mode, path
        self.specs = {}               # feature name -> definition, in creation order (written to the manifest)
        self.existing, self.old_specs, self.legacy = set(), {}, False
        if mode == "update":
            import json
            r = sw.OpenDoc6(path, C.swDocPART, C.swOpenDocOptions_Silent, "", 0, 0)
            if r[0] is None:
                raise RuntimeError(f"cannot open {path} for update: {r[1:]}")
            self.doc = T(r[0], "IModelDoc2")
            sw.ActivateDoc3(self.doc.GetTitle(), False, 0, 0)
            f = self.doc.FirstFeature()
            while f is not None:
                f = T(f, "IFeature")
                self.existing.add(f.Name)
                f = f.GetNextFeature()
            mpath = path + ".manifest.json"
            if os.path.exists(mpath):
                self.old_specs = json.load(open(mpath, encoding="utf-8"))["specs"]
            else:
                self.legacy = True    # built before manifests existed: trust existing names
        else:
            self.doc = new_doc(sw, "part")
        self.part = T(self.doc, "IPartDoc")
        ext = self.doc.Extension
        ext.SetUserPreferenceInteger(C.swUnitSystem, 0, C.swUnitSystem_MMGS)
        _apply_script_prefs(sw)
        self.eq = T(self.doc.GetEquationMgr(), "IEquationMgr")
        self.globals = set()     # global variables written so far (only the ones actually used)
        if mode == "update":     # globals already in the part (own or from the linked shared file)
            if self.eq.LinkToFile:   # pull values and new names from the shared file (write it first)
                self.eq.UpdateValuesFromExternalEquationFile()
            for i in range(self.eq.GetCount()):
                if self.eq.GlobalVariable(i):
                    self.globals.add(self.eq.Equation(i).split("=")[0].strip().strip('"'))
        self.links = []          # (dimension full name, expression) for verification
        # speed: no feature-tree refresh while building (restored by save()).
        # Do NOT disable graphics updates (IModelView.EnableGraphicsUpdate = False): SolidWorks then
        # creates centre rectangles without their centre point and the sketch cannot be constrained.
        self.doc.FeatureManager.EnableFeatureTree = False

    # ---------- expressions ----------
    def val(self, expr):
        """mm value of a number or expression string."""
        if isinstance(expr, (int, float)):
            return float(expr)
        return float(eval(expr, {"math": math}, dict(self.params)))

    def sw_expr(self, expr):
        if isinstance(expr, (int, float)):
            return repr(float(expr))
        names = sorted(self.params, key=len, reverse=True)
        pat = r"\b(" + "|".join(map(re.escape, names)) + r")\b"
        return re.sub(pat, r'"\1"', expr)

    def _add_eq(self, text):
        # Solve=False: the geometry is already built at these values; solving after every
        # equation made SolidWorks rebuild the whole part each time (quadratic). solve() runs once.
        idx = self.eq.Add2(-1, text, False)
        if idx < 0:
            raise RuntimeError(f"equation rejected: {text}")
        return idx

    def _ensure_globals(self, expr):
        if isinstance(expr, (int, float)):
            return
        for name in sorted(self.params, key=len, reverse=True):
            if name not in self.globals and re.search(r"\b" + re.escape(name) + r"\b", expr):
                self._add_eq(f'"{name}" = {self.params[name]}')
                self.globals.add(name)

    def link_external(self, path):
        """Link the part's equations to a shared text file of global variables ("NAME" = value per line).
        The part keeps its own dimension equations; the globals then come from the file, so editing
        that one file (or Tools > Equations > link) updates every linked part on its next rebuild/open."""
        self.eq.FilePath = path
        self.eq.LinkToFile = True
        self.eq.UpdateValuesFromExternalEquationFile()
        self.solve()

    def solve(self):
        self.eq.EvaluateAll()
        self.doc.ForceRebuild3(False)

    def link(self, dim, expr, absval=False):
        """Link an IDimension to an expression (dimensions are unsigned -> abs if asked)."""
        d = T(dim, "IDimension")
        full = d.FullName              # e.g. D1@Sketch1@Part1.SLDPRT
        name = "@".join(full.split("@")[:2])
        self._ensure_globals(expr)
        e = self.sw_expr(expr)
        if absval and self.val(expr) < 0:
            e = f"-({e})"
        self._add_eq(f'"{name}" = {e}')
        self.links.append((name, expr))

    # ---------- features ----------
    def declare(self, name, spec):
        """Record a feature's definition. Returns True when it already exists unchanged (skip it)."""
        import json
        spec = json.loads(json.dumps(spec))          # normalise (tuples -> lists, floats)
        if os.environ.get("SWCAD_TRACE"):            # find the feature a hung build is stuck on
            import time
            print(f"   [{time.strftime('%H:%M:%S')}] {name}", flush=True)
        if name in self.specs:
            raise RuntimeError(f"feature name used twice: {name}")
        self.specs[name] = spec
        if self.mode != "update" or name not in self.existing:
            return False
        if self.legacy:
            return True
        old = self.old_specs.get(name)
        if old is None:
            raise SyncConflict(f"'{name}' exists in the part but was not made by the script "
                               f"(created or renamed by hand?)")
        if old != spec:
            self._retarget(name, old, spec)
        return True

    def _retarget(self, name, old, new):
        """In update mode: a feature whose definition changed only in dimension expressions keeps its
        geometry and gets its equations rewritten in place (same shapes, same planes, same signs).
        Anything structural raises SyncConflict before the part is touched."""
        def conflict(why):
            return SyncConflict(f"definition of '{name}' changed in the script ({why}):\n   was {old}\n"
                                f"   now {new}\n   -> needs a rebuild (or replacing this feature in place)")
        pairs = []

        def walk(a, b):
            if isinstance(a, list) and isinstance(b, list):
                if len(a) != len(b):
                    raise conflict("different number of shapes/arguments")
                for x, y in zip(a, b):
                    walk(x, y)
            elif a != b:
                if isinstance(a, (list, bool)) or isinstance(b, (list, bool)):
                    raise conflict("structure or direction changed")
                pairs.append((a, b))
        if old[:2] != new[:2]:
            raise conflict("feature kind or parent changed")
        redraw = []      # polylines carry no dimensions: redraw them inside the existing sketch
        if old[0] == "sketch" and len(old[2]) == len(new[2]):
            for i, (a, b) in enumerate(zip(old[2], new[2])):
                if a != b and a[0] == b[0] == "polygon":
                    redraw.append(b[1])
            if redraw:
                if any(c[0] != "polygon" for c in new[2]):
                    raise conflict("a polyline moved in a sketch that also has dimensioned shapes")
                old, new = old[:2], new[:2]
        walk(old, new)
        lhs_pat = re.compile(r'"D\d+@' + re.escape(name) + '"')
        eqs = [self.eq.Equation(i) for i in range(self.eq.GetCount())]
        writes = {}
        pairs = list(dict.fromkeys(pairs))       # the same change repeated in several shapes: once
        for a, b in pairs:
            try:
                va, vb = self.val(a), self.val(b)
            except Exception:
                raise conflict(f"{a!r} -> {b!r} is not a dimension")
            if (va < 0) != (vb < 0):
                raise conflict(f"{a!r} -> {b!r} changes sign")
            ea, eb = self.sw_expr(a), self.sw_expr(b)
            hits = 0
            for i, text in enumerate(eqs):
                lhs, _, rhs = text.partition("=")
                if not lhs_pat.fullmatch(lhs.strip()):
                    continue
                r = rhs.replace(" ", "")
                if r == ea.replace(" ", ""):
                    new_rhs = eb
                elif r == f"-({ea})".replace(" ", ""):
                    new_rhs = f"-({eb})"
                else:
                    continue
                text_new = f"{lhs.strip()} = {new_rhs}"
                if writes.get(i, text_new) != text_new:
                    raise conflict(f"two different changes for one equation ({lhs.strip()})")
                writes[i] = text_new
                hits += 1
            if not hits:
                raise conflict(f"no equation of {name} equals {a!r} (edited by hand?)")
        for _, b in pairs:
            self._ensure_globals(b)
        for i, text in writes.items():
            self.eq.SetEquation(i, text)          # returns nothing: read it back instead
            if self.eq.Equation(i).replace(" ", "") != text.replace(" ", ""):
                raise RuntimeError(f"equation rejected: {text}")
        if redraw:
            self._redraw_polylines(name, redraw)
        print(f"   updated in place: {name} ({len(writes)} equation(s)"
              f"{', polyline redrawn' if redraw else ''})")

    def _redraw_polylines(self, name, polys):
        """Replace the lines of an existing polyline-only sketch; the features built on it stay."""
        doc, sm = self.doc, self.doc.SketchManager
        doc.ClearSelection2(True)
        self.feat(name).Select2(False, 0)
        doc.EditSketch()
        sk = T(sm.ActiveSketch, "ISketch")
        doc.ClearSelection2(True)
        for seg in sk.GetSketchSegments() or ():
            T(seg, "ISketchSegment").Select4(True, None)
        doc.EditDelete()
        sm.AddToDB = True
        for pts in polys:
            for i in range(len(pts)):
                (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)]
                if sm.CreateLine(x1 * MM, y1 * MM, 0, x2 * MM, y2 * MM, 0) is None:
                    raise RuntimeError(f"line {i} failed in {name}")
        sm.AddToDB = False
        sm.InsertSketch(True)

    def feat(self, name):
        f = self.part.FeatureByName(name)
        if f is None:
            raise RuntimeError(f"no feature {name!r}")
        return T(f, "IFeature")

    def last_feat(self):
        return T(self.doc.FeatureByPositionReverse(0), "IFeature")

    def plane(self, name, z_expr, base="Front Plane"):
        """Reference plane parallel to `base` at signed offset z_expr (mm) along its normal.
        Normals: Front +Z, Top +Y, Right +X.
        Sketch axes: Front (X, Y); Top (X, -Z); Right (-Z, Y)."""
        if self.declare(name, ["plane", base, str(z_expr)]):
            return name
        z = self.val(z_expr)
        self.doc.ClearSelection2(True)
        self.feat(base).Select2(False, 0)
        opt = C.swRefPlaneReferenceConstraint_Distance
        if z < 0:
            opt |= C.swRefPlaneReferenceConstraint_OptionFlip
        pl = self.doc.FeatureManager.InsertRefPlane(opt, abs(z) * MM, 0, 0, 0, 0)
        if pl is None:
            raise RuntimeError(f"plane {name} failed")
        f = self.last_feat()
        f.Name = name
        self.link(self.own_dim(f), z_expr, absval=True)
        return name

    def sketch(self, plane, name):
        return _Sketch(self, plane, name)

    def _extrude(self, sketch, depth, reverse, cut, mode, name):
        if self.declare(name, ["cut" if cut else "extrude", sketch, str(depth), bool(reverse), mode]):
            return self.feat(name)
        self.doc.ClearSelection2(True)
        self.feat(sketch).Select2(False, 0)
        fm = self.doc.FeatureManager
        t1 = {"blind": C.swEndCondBlind, "mid": C.swEndCondMidPlane,
              "through": C.swEndCondThroughAll}[mode]
        d = self.val(depth) * MM if mode != "through" else 0.01
        if cut:
            # a cut's default direction is opposite the plane normal, so "reverse" (toward -normal) is the default
            f = fm.FeatureCut4(True, False, not reverse, t1, 0, d, 0, False, False, False, False,
                               0, 0, False, False, False, False, False, True, True, True, True,
                               False, 0, 0, False, False)
        else:
            f = fm.FeatureExtrusion3(True, False, reverse, t1, 0, d, 0, False, False, False, False,
                                     0, 0, False, False, False, False, True, True, True, 0, 0, False)
        if f is None:
            raise RuntimeError(f"{'cut' if cut else 'extrude'} {name} failed")
        f = T(f, "IFeature")
        f.Name = name
        if mode != "through":
            self.link(self.own_dim(f), depth)
        return f

    def own_dim(self, f, index=0):
        """index-th dimension that belongs to feature f itself (not to its sketch/plane)."""
        hits = []
        dd = f.GetFirstDisplayDimension()
        while dd is not None:
            dd = T(dd, "IDisplayDimension")
            d = T(dd.GetDimension2(0), "IDimension")
            if d.FullName.split("@")[1] == f.Name:
                hits.append(d)
            dd = f.GetNextDisplayDimension(dd)
        if len(hits) <= index:
            raise RuntimeError(f"feature {f.Name} has no own dimension #{index}")
        return hits[index]

    def extrude(self, sketch, depth, name, reverse=False, mode="blind"):
        return self._extrude(sketch, depth, reverse, False, mode, name)

    def cut(self, sketch, depth, name, reverse=False, mode="blind"):
        return self._extrude(sketch, depth, reverse, True, mode, name)

    # ---------- checks ----------
    def rebuild_errors(self, doc=None, skip_transient=True):
        """Feature errors. In a live session SolidWorks flags the Equations folder with error 51
        after equations are added by API; it is gone after save + reopen, which save() checks."""
        bad = []
        if doc is None:
            self.solve()
        f = (doc or self.doc).FirstFeature()
        while f is not None:
            f = T(f, "IFeature")
            code, warn = f.GetErrorCode2()
            if code != 0 and not (skip_transient and f.Name == "Equations" and code == 51):
                bad.append((f.Name, code, warn))
            f = f.GetNextFeature()
        return bad

    def bodies(self):
        return [T(b, "IBody2") for b in (self.part.GetBodies2(C.swSolidBody, True) or ())]

    def bbox(self):
        boxes = [b.GetBodyBox() for b in self.bodies()]
        lo = [min(b[i] for b in boxes) / MM for i in range(3)]
        hi = [max(b[i + 3] for b in boxes) / MM for i in range(3)]
        return lo, hi

    def volume(self):
        return sum(b.GetMassProperties(1000)[3] for b in self.bodies()) / MM ** 3

    def set_param(self, name, value):
        """Change a global variable (as a user would in the Equations dialog) and rebuild."""
        for i in range(self.eq.GetCount()):
            if self.eq.GlobalVariable(i) and self.eq.Equation(i).split("=")[0].strip() == f'"{name}"':
                self.eq.SetEquation(i, f'"{name}" = {value}')
                self.params[name] = value
                self.eq.EvaluateAll()
                self.doc.ForceRebuild3(False)
                return
        raise KeyError(f"{name} is not a global variable of this part")

    def save(self, path):
        """Save, close, reopen and rebuild: the part must come back with no errors at all."""
        self.solve()
        self.doc.FeatureManager.EnableFeatureTree = True
        save_as(self.doc, path)
        self.sw.CloseDoc(self.doc.GetTitle())
        r = self.sw.OpenDoc6(path, C.swDocPART, C.swOpenDocOptions_Silent, "", 0, 0)
        if r[0] is None:
            raise RuntimeError(f"reopen failed: {path} {r[1:]}")
        self.doc = T(r[0], "IModelDoc2")
        self.part = T(self.doc, "IPartDoc")
        self.doc.ForceRebuild3(False)
        errs = self.rebuild_errors(skip_transient=False)
        if errs:
            raise RuntimeError(f"{os.path.basename(path)} has errors after reopen: {errs}")
        import json
        from partsync import part_state
        specs = dict(self.old_specs) if self.mode == "update" else {}
        specs.update(self.specs)
        json.dump({"specs": specs, "state": part_state(self.doc)},
                  open(path + ".manifest.json", "w", encoding="utf-8"), indent=1)
        return path


class _Sketch:
    def __init__(self, pb, plane, name):
        self.pb, self.plane, self.name = pb, plane, name
        self.pending = []   # (callable -> IDimension, expr, absval)
        self.fillets = []   # radius expressions of sketch fillets (their dimensions are created by SW)
        self.used = []      # sketch points already constrained as a shape centre

    def __enter__(self):
        pb = self.pb
        self.calls = []
        self.dry = pb.mode == "update" and self.name in pb.existing
        if self.dry:
            return self
        pb.doc.ClearSelection2(True)
        pb.feat(self.plane).Select2(False, 0)
        pb.doc.SketchManager.InsertSketch(True)
        # AddToDB stays False: the rectangle tool then adds its own horizontal/vertical/midpoint
        # relations; inference/snapping is off so nothing attaches to other geometry
        pb.doc.SketchManager.AddToDB = False
        self.sk = T(pb.doc.SketchManager.ActiveSketch, "ISketch")
        return self

    def __exit__(self, et, ev, tb):
        pb = self.pb
        if self.dry:
            if not et:
                pb.declare(self.name, ["sketch", self.plane, self.calls])
            return False
        if not et:
            pb.declare(self.name, ["sketch", self.plane, self.calls])
        pb.doc.SketchManager.AddToDB = False
        pb.doc.SketchManager.InsertSketch(True)
        if et:
            return False
        f = pb.last_feat()
        f.Name = self.name
        for dim, expr, absval in self.pending:
            pb.link(dim, expr, absval)
        if self.fillets:
            linked = {T(d, "IDimension").FullName for d, _, _ in self.pending}
            todo = list(self.fillets)
            dd = f.GetFirstDisplayDimension()
            while dd is not None and todo:
                dd = T(dd, "IDisplayDimension")
                d = T(dd.GetDimension2(0), "IDimension")
                if d.FullName not in linked:
                    val = d.SystemValue / MM
                    hit = next((r for r in todo if abs(pb.val(r) - val) < 1e-6), None)
                    if hit is not None:
                        pb.link(d, hit)
                        todo.remove(hit)
                dd = f.GetNextDisplayDimension(dd)
            if todo:
                raise RuntimeError(f"fillet dimensions not found in {self.name}: {todo}")
        return False

    # -- helpers
    def _dim(self, sel, x, y, kind="free"):
        doc = self.pb.doc
        doc.ClearSelection2(True)
        for i, s in enumerate(sel):
            s(i > 0)
        fn = {"free": doc.AddDimension2, "h": doc.AddHorizontalDimension2,
              "v": doc.AddVerticalDimension2}[kind]
        nsel = T(doc.SelectionManager, "ISelectionMgr").GetSelectedObjectCount2(-1)
        dd = fn(x * MM, y * MM, 0)
        doc.ClearSelection2(True)
        if dd is None:
            raise RuntimeError(f"dimension failed in {self.name} (kind={kind}, selected={nsel}/{len(sel)}, at {x:.2f},{y:.2f})")
        return T(dd, "IDisplayDimension").GetDimension2(0)

    def _sel_seg(self, seg):
        return lambda app: T(seg, "ISketchSegment").Select4(app, None)

    def _sel_pt(self, pt):
        return lambda app: T(pt, "ISketchPoint").Select4(app, None)

    def _sel_origin(self):
        doc = self.pb.doc
        return lambda app: doc.Extension.SelectByID2("Point1@Origin", "EXTSKETCHPOINT", 0, 0, 0, app, 0, None, 0)

    def _place(self, pt, cx, cy):
        """Dimension a sketch point to the origin, or align it when the offset is zero."""
        doc = self.pb.doc
        x, y = self.pb.val(cx), self.pb.val(cy)
        for val, expr, kind, rel in ((x, cx, "h", "sgVERTICALPOINTS2D"), (y, cy, "v", "sgHORIZONTALPOINTS2D")):
            if abs(val) < 1e-9:
                doc.ClearSelection2(True)
                self._sel_pt(pt)(False)
                self._sel_origin()(True)
                doc.SketchAddConstraints(rel)
                doc.ClearSelection2(True)
            else:
                lx, ly = (x / 2, y + 6) if kind == "h" else (x + 6, y / 2)
                self.pending.append((self._dim([self._sel_pt(pt), self._sel_origin()], lx, ly, kind), expr, True))

    def rect(self, cx, cy, w, h):
        self.calls.append(["rect", str(cx), str(cy), str(w), str(h)])
        if self.dry:
            return []
        return self._rect(cx, cy, w, h)

    def _rect(self, cx, cy, w, h):
        pb = self.pb
        x, y, W, H = pb.val(cx), pb.val(cy), pb.val(w), pb.val(h)
        segs = pb.doc.SketchManager.CreateCenterRectangle(x * MM, y * MM, 0, (x + W / 2) * MM, (y + H / 2) * MM, 0)
        lines = [T(s, "ISketchLine") for s in segs if T(s, "ISketchSegment").ConstructionGeometry is False]
        def mid(l):
            a, b = T(l.GetStartPoint2(), "ISketchPoint"), T(l.GetEndPoint2(), "ISketchPoint")
            return (a.X + b.X) / 2 / MM, (a.Y + b.Y) / 2 / MM, abs(a.Y - b.Y) < 1e-9
        top = max((l for l in lines if mid(l)[2]), key=lambda l: mid(l)[1])
        right = max((l for l in lines if not mid(l)[2]), key=lambda l: mid(l)[0])
        self.pending.append((self._dim([self._sel_seg(top)], x, y + H / 2 + 4), w, False))
        self.pending.append((self._dim([self._sel_seg(right)], x + W / 2 + 4, y), h, False))
        # centre point of the centre-rectangle
        pts = [T(p, "ISketchPoint") for p in self.sk.GetSketchPoints2()]
        # centre point of this rectangle: closest point not already used by an earlier shape
        free = [p for p in pts if not any(p._oleobj_ == u for u in self.used)]
        c = min(free, key=lambda p: math.hypot(p.X / MM - x, p.Y / MM - y))
        if math.hypot(c.X / MM - x, c.Y / MM - y) > 1e-6:
            # some sessions draw the construction diagonals but no centre point: add it at a diagonal's midpoint
            diag = next(T(s, "ISketchSegment") for s in segs if T(s, "ISketchSegment").ConstructionGeometry)
            c = T(pb.doc.SketchManager.CreatePoint(x * MM, y * MM, 0), "ISketchPoint")
            pb.doc.ClearSelection2(True)
            c.Select4(False, None)
            diag.Select4(True, None)
            pb.doc.SketchAddConstraints("sgATMIDDLE")
            pb.doc.ClearSelection2(True)
        assert math.hypot(c.X / MM - x, c.Y / MM - y) < 1e-6, f"centre point not found in {self.name}"
        self.used.append(c._oleobj_)
        self._place(c, cx, cy)
        corners = {}
        for l in lines:
            for p in (T(l.GetStartPoint2(), "ISketchPoint"), T(l.GetEndPoint2(), "ISketchPoint")):
                corners.setdefault((round(p.X / MM, 6), round(p.Y / MM, 6)), p)
        return list(corners.values())

    def rrect(self, cx, cy, w, h, r):
        """Centre rectangle with all four corners filleted to radius r (linked to an expression)."""
        pb = self.pb
        self.calls.append(["rrect", str(cx), str(cy), str(w), str(h), str(r)])
        if self.dry:
            return
        corners = self._rect(cx, cy, w, h)
        if len(corners) != 4:
            raise RuntimeError(f"rrect: found {len(corners)} corners in {self.name}")
        pb.doc.ClearSelection2(True)
        for i, p in enumerate(corners):
            p.Select4(i > 0, None)
        pb.doc.SketchFillet2(pb.val(r) * MM, C.swConstrainedCornerKeepGeometry)
        pb.doc.ClearSelection2(True)
        self.fillets.append(r)

    def polygon(self, pts):
        """Closed polyline in sketch coordinates (mm). Not dimension-linked: used only for
        small profile details whose values come from the parameters at build time."""
        self.calls.append(["polygon", [[round(x, 6), round(y, 6)] for x, y in pts]])
        if self.dry:
            return
        sm = self.pb.doc.SketchManager
        sm.AddToDB = True          # direct mode merges coincident endpoints into a closed loop
        n = len(pts)
        for i in range(n):
            (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % n]
            if sm.CreateLine(x1 * MM, y1 * MM, 0, x2 * MM, y2 * MM, 0) is None:
                raise RuntimeError(f"line {i} failed in {self.name}")
        sm.AddToDB = False

    def circle(self, cx, cy, d):
        self.calls.append(["circle", str(cx), str(cy), str(d)])
        if self.dry:
            return
        pb = self.pb
        x, y, D = pb.val(cx), pb.val(cy), pb.val(d)
        seg = pb.doc.SketchManager.CreateCircleByRadius(x * MM, y * MM, 0, D / 2 * MM)
        self.pending.append((self._dim([self._sel_seg(seg)], x + D, y + D), d, False))
        ctr = T(T(seg, "ISketchArc").GetCenterPoint2(), "ISketchPoint")
        self._place(ctr, cx, cy)
