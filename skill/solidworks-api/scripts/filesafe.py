"""Never overwrite human work silently - for ANY file a script writes (parts, assemblies, drawings, text).
The script records every file it writes (size + modified time) in <folder>/.swstate.json. Before writing over an
existing file:
  status(path) -> "new"      no file yet
                  "ours"     unchanged since the script last wrote it
                  "changed"  written by someone else since (a hand edit in SolidWorks, a copy, another tool)
                  "unknown"  exists but was never recorded (first run on an existing project)
  before_write(path)         "changed" / "unknown": copy the file to the backup folder first, then act by policy
  record(path)               call after every successful write
Policy (env SW_ON_HAND_EDIT): "backup" (default) keep a copy and continue; "stop" raise HandEdit so the caller asks
the user (keep mine / adopt / overwrite). Backups: env SW_BACKUP_DIR, else <parent of the file's folder>/_backup/
<YYYYMMDD-HHMMSS>/ - outside the CAD folder so Pack and Go / PDM do not pick them up. One copy per file per run.
`sw_common.save_as` calls before_write / record, so every library save is covered."""
import json
import os
import shutil
import time

STATE_NAME = ".swstate.json"
_STAMP = time.strftime("%Y%m%d-%H%M%S")
_backed = set()


class HandEdit(RuntimeError):
    """The file was changed by someone else since the script last wrote it (policy "stop")."""


def _state_path(path):
    return os.path.join(os.path.dirname(os.path.abspath(path)), STATE_NAME)


def _load(path):
    try:
        return json.load(open(_state_path(path), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _sig(path):
    st = os.stat(path)
    return {"size": st.st_size, "mtime": round(st.st_mtime, 3)}


def status(path):
    if not os.path.exists(path):
        return "new"
    rec = _load(path).get(os.path.basename(path).lower())
    if rec is None:
        return "unknown"
    now = _sig(path)
    return "ours" if (rec["size"] == now["size"] and abs(rec["mtime"] - now["mtime"]) < 0.002) else "changed"


def record(path):
    if not os.path.exists(path):
        return
    st = _load(path)
    st[os.path.basename(path).lower()] = dict(_sig(path), written=time.strftime("%Y-%m-%d %H:%M:%S"))
    json.dump(st, open(_state_path(path), "w", encoding="utf-8"), indent=1)


def backup_dir(path):
    root = os.environ.get("SW_BACKUP_DIR") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(path))),
                                                             "_backup")
    return os.path.join(root, _STAMP)


def backup(path):
    """Copy the file to the backup folder (once per run). Returns the copy's path, or None when already done."""
    key = os.path.abspath(path).lower()
    if key in _backed or not os.path.exists(path):
        return None
    d = backup_dir(path)
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, os.path.basename(path))
    shutil.copy2(path, dst)
    _backed.add(key)
    return dst


def before_write(path, policy=None):
    """Call before saving over `path`. Returns the status. "changed" / "unknown" files are backed up first."""
    st = status(path)
    if st in ("changed", "unknown"):
        copy = backup(path)
        policy = policy or os.environ.get("SW_ON_HAND_EDIT", "backup")
        if st == "changed":
            if policy == "stop":
                raise HandEdit(f"{os.path.basename(path)} was changed since the script wrote it; copy kept at {copy}")
            print(f"   note: {os.path.basename(path)} was changed by hand since the last script write - "
                  f"copy kept at {copy}", flush=True)
    return st


def self_test():
    import tempfile
    root = tempfile.mkdtemp()
    cad = os.path.join(root, "cad")
    os.makedirs(cad)
    f = os.path.join(cad, "a.sldprt")
    assert status(f) == "new"
    open(f, "w").write("v1")
    assert status(f) == "unknown" and before_write(f) == "unknown"
    assert os.path.exists(os.path.join(backup_dir(f), "a.sldprt"))
    record(f)
    assert status(f) == "ours" and before_write(f) == "ours"
    time.sleep(0.05)
    open(f, "w").write("hand edit!")
    assert status(f) == "changed"
    _backed.clear()
    try:
        before_write(f, policy="stop")
        raise AssertionError("no stop")
    except HandEdit:
        pass
    assert open(os.path.join(backup_dir(f), "a.sldprt")).read() == "hand edit!"
    record(f)
    assert status(f) == "ours"
    shutil.rmtree(root)
    print("FILESAFE TEST OK")


if __name__ == "__main__":
    self_test()
