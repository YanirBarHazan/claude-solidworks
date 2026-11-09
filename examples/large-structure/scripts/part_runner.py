"""Part runners (ROADMAP 1, 4, 10). Imported at the end of nh_common, so part scripts keep
`from nh_common import run_part`.
run_part        - update in place by default, ONE open per part, one verification after the save;
                  new file -> built from scratch with the full checks incl. the edit test.
run_config_part - one part, one configuration per value (cable / rod lengths): only differing configurations
                  are set, missing ones added, unused ones deleted; every touched configuration is measured.
Hand edits -> exit 3; changed feature structure -> exit 4. Never rebuild an existing part without consent
(`--rebuild` on the command line)."""
import os
import sys
import time
import traceback

import nh_common as NC
from swcad import PartBuilder, SyncConflict
import partsync

COUNTS = {"built": 0, "updated": 0, "unchanged": 0, "failed": 0}


def record(kind):
    COUNTS[kind] += 1


def reset_params():
    """Re-read params.py into P in place (one-session runs: every part script starts from the file values)."""
    import importlib
    importlib.reload(NC.params)
    NC.P.clear()
    for grp in (NC.params.GRID, NC.params.PERIM, NC.params.INT, NC.params.ANCHOR, NC.params.CABLE, NC.params.CAP,
                NC.params.HOLES, NC.params.ANC_EYE, NC.params.ANCHOR2, NC.params.ROOFCBL, NC.params.TRELLIS,
                NC.params.WALK):
        NC.P.update({k: float(v) for k, v in grp.items()})


def _props_colour(pb, name, props, color):
    changed = []
    cpm = NC.T(pb.doc.Extension.CustomPropertyManager(""), "ICustomPropertyManager")
    for k, v in {"PartNo": name, **props}.items():
        if cpm.Get6(k, False)[1] != v:
            cpm.Add3(k, NC.C.swCustomInfoText, v, NC.C.swCustomPropertyReplaceValue)
            changed.append(k)
    if color:
        got = list(pb.doc.MaterialPropertyValues or [])[:3]
        if len(got) < 3 or any(abs(a - b) > 1.0 / 255 for a, b in zip(got, NC.COLORS[color])):   # 8-bit, truncated
            NC.set_color(pb.doc, NC.COLORS[color])
            changed.append("colour")
    return changed


def _open_update(sw, name, path, p, build):
    """ONE open: PartBuilder in update mode, drift check on that document, dry build."""
    pb = PartBuilder(sw, p, path=path, mode="update")
    rep = partsync.check_open(pb.doc, path)
    if rep.get("drift"):
        print(partsync.describe(rep))
        sw.CloseDoc(pb.doc.GetTitle())
        print(f"STOP {name}: hand edits - decide --update / --adopt / --rebuild", flush=True)
        return None, 3
    try:
        build(pb)
    except SyncConflict as ex:
        sw.CloseDoc(pb.doc.GetTitle())
        print(f"STOP {name}: structure changed, needs a rebuild (ask first): {ex}", flush=True)
        return None, 4
    return pb, None


def _exists(path):
    return os.path.exists(path) and os.path.exists(path + ".manifest.json")


def fingerprint(build, p, props, color, extra=None):
    """What defines the part: the part script, the shared geometry modules, the values it uses, props, colour."""
    import hashlib
    import inspect
    h = hashlib.sha1()
    here = os.path.dirname(os.path.abspath(__file__))
    src = inspect.getsourcefile(build)
    files = [src, os.path.join(here, "nh_common.py")]
    if src and "pole_common" in open(src, encoding="utf-8").read():     # shared geometry only where it is used
        files.append(os.path.join(here, "pole_common.py"))
    for f in files:
        if f and os.path.exists(f):
            h.update(open(f, "rb").read())
    h.update(repr((sorted(p.items()), sorted(props.items()), color, extra)).encode("utf-8"))
    return h.hexdigest()


def fp_unchanged(path, fp):
    """True when the manifest has this fingerprint AND the file was not saved since (no hand edit possible)."""
    import json
    try:
        m = json.load(open(path + ".manifest.json", encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return m.get("fingerprint") == fp and abs(m.get("mtime", -1) - os.path.getmtime(path)) < 1e-3


def fp_store(path, fp):
    import json
    mp = path + ".manifest.json"
    m = json.load(open(mp, encoding="utf-8"))
    m["fingerprint"], m["mtime"] = fp, os.path.getmtime(path)
    json.dump(m, open(mp, "w", encoding="utf-8"), indent=1)


def run_part(name, keys, build, expect, edit, props, color=None, folder=None):
    t0 = time.time()
    path = os.path.join(NC.CAD, *([folder] if folder else []), name + ".sldprt")
    p = {k: NC.P[k] for k in keys}
    fp = fingerprint(build, p, props, color)
    if "--seed-fp" in sys.argv:          # one-off, ONLY right after a run that verified every file (no SolidWorks)
        if _exists(path):
            fp_store(path, fp)
            print(f"OK {name}  fingerprint stored", flush=True)
            return 0
        print(f"FAIL {name}: no file to fingerprint", flush=True)
        return 1
    if _exists(path) and "--rebuild" not in sys.argv and "--check" not in sys.argv and fp_unchanged(path, fp):
        print(f"OK {name}  unchanged (fingerprint, not opened, {time.time() - t0:.2f} s)", flush=True)
        record("unchanged")
        return 0
    try:
        sw = NC.connect()
        if _exists(path) and "--rebuild" not in sys.argv:
            pb, code = _open_update(sw, name, path, p, build)
            if pb is None:
                return code
            added = [n for n in pb.specs if n not in pb.existing]
            changed = pb.push_globals()
            other = _props_colour(pb, name, props, color)
            if not (added or changed or other):
                sw.CloseDoc(pb.doc.GetTitle())
                fp_store(path, fp)
                print(f"OK {name}  unchanged (opened, {time.time() - t0:.1f} s)", flush=True)
                record("unchanged")
                return 0
            pb.save(path)                       # save, close, reopen, rebuild: 0 errors or raises
            res = pb.verify(expect)
            sw.CloseDoc(pb.doc.GetTitle())
            fp_store(path, fp)
            what = ", ".join([f"{k} {o:g}->{n:g}" for k, o, n in changed] + [f"+{a}" for a in added] + other)
            print(f"OK {name}  UPDATED in place ({what}) bbox={[round(s, 1) for s in res['bbox']]} "
                  f"vol={res['volume'] / 1e6:.4f} dm3, {time.time() - t0:.1f} s", flush=True)
            record("updated")
            return 0
        NC.close_out_docs(sw)
        pb = PartBuilder(sw, p)
        build(pb)
        _props_colour(pb, name, props, color)
        pb.verify(expect, edit=edit)
        pb.save(path)
        res = pb.verify(expect)
        sw.CloseDoc(pb.doc.GetTitle())
        fp_store(path, fp)
        print(f"OK {name}  BUILT new bbox={[round(s, 1) for s in res['bbox']]} vol={res['volume'] / 1e6:.4f} dm3 "
              f"links={len(pb.links)} edit {edit[0]} ok, {time.time() - t0:.1f} s", flush=True)
        record("built")
        return 0
    except Exception as ex:
        traceback.print_exc()
        print(f"FAIL {name}: {ex}", flush=True)
        record("failed")
        try:                                     # one session: never leave this part's documents open
            NC.close_out_docs(NC.connect())
        except Exception:
            pass
        return 1


def run_config_part(name, keys, build, cfg_param, configs, expect_cfg, props, color=None):
    """configs: {configuration name: value of cfg_param}. expect_cfg(p, value) -> (bbox, volume)."""
    t0 = time.time()
    path = os.path.join(NC.CAD, name + ".sldprt")
    exists = _exists(path) and "--rebuild" not in sys.argv
    try:
        sw = NC.connect()
        first = next(iter(configs))
        p = {k: NC.P[k] for k in keys}
        p[cfg_param] = configs[first]
        if exists:
            pb, code = _open_update(sw, name, path, p, build)
            if pb is None:
                return code
            pb.params.pop(cfg_param, None)       # configuration-specific: never pushed as one global value
            changed = [f"{k} {o:g}->{n:g}" for k, o, n in pb.push_globals()]
        else:
            NC.close_out_docs(sw)
            pb = PartBuilder(sw, p)
            build(pb)
            changed = []
        added, setv, gone = [], [], []
        # 2019 order that works (prototype): add ALL missing configurations first (adding after a
        # ShowConfiguration2 failed), and on a new part rename the template configuration to the first one
        # AFTER the others exist, so the first configuration-specific value is set on the original configuration.
        names = list(configs)
        if not exists:
            default = pb.config_names()[0]
            for cfg in names[1:]:
                pb.ensure_config(cfg)
            NC.T(pb.doc.GetConfigurationByName(default), "IConfiguration").Name = names[0]
            added = names[:]
        else:
            for cfg in names:
                if pb.ensure_config(cfg):
                    added.append(cfg)
        for cfg, v in configs.items():
            if cfg in added or abs(pb.cfg_value(cfg_param, cfg) - v) > 1e-6 * max(1.0, abs(v)):
                pb.set_cfg_value(cfg_param, cfg, v)
                setv.append(cfg)
        for cfg in pb.config_names():
            if cfg not in configs:
                pb.delete_config(cfg)            # also the template's default configuration of a new part
                if exists:
                    gone.append(cfg)
        other = _props_colour(pb, name, props, color)
        if exists and not (changed or added or setv or gone or other):
            sw.CloseDoc(pb.doc.GetTitle())
            print(f"OK {name}  unchanged, {len(configs)} configurations ({time.time() - t0:.1f} s)", flush=True)
            record("unchanged")
            return 0
        pb.doc.ShowConfiguration2(first)
        pb.save(path)
        pb.eq = NC.T(pb.doc.GetEquationMgr(), "IEquationMgr")
        touched = list(configs) if not exists else list(dict.fromkeys(setv + added))
        for cfg in touched:
            pb.doc.ShowConfiguration2(cfg)
            pb.doc.ForceRebuild3(False)
            v = configs[cfg]
            pb.verify(lambda pp, v=v: expect_cfg(pp, v), params={**p, cfg_param: v})
        pb.doc.ShowConfiguration2(first)
        pb.doc.Save3(1, 0, 0)
        sw.CloseDoc(pb.doc.GetTitle())
        tag = "UPDATED in place" if exists else "BUILT new"
        extra = ", ".join(changed + other)
        print(f"OK {name}  {tag}: {len(configs)} configurations (set {len(setv)}, added {len(added)}, "
              f"deleted {len(gone)}){', ' + extra if extra and exists else ''}; measured {len(touched)}, "
              f"{time.time() - t0:.1f} s", flush=True)
        record("updated" if exists else "built")
        return 0
    except Exception as ex:
        traceback.print_exc()
        print(f"FAIL {name}: {ex}", flush=True)
        record("failed")
        try:                                     # one session: never leave this part's documents open
            NC.close_out_docs(NC.connect())
        except Exception:
            pass
        return 1
