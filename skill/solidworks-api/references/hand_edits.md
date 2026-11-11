# Hand edits: never overwrite them silently

Users also edit the parts in SolidWorks. Every `PartBuilder.save()` writes `<part>.manifest.json`
(the script's feature definitions + the saved file's state). Before touching a part again:
```python
import partsync
mode = partsync.decide(sw, PATH, PARAMS_PY)      # "build" | "update", or exit 3 with a report
pb = PartBuilder(sw, P, path=PATH, mode=mode)
```
- No hand edits -> build as usual. Only added/suppressed features -> update in place automatically.
- Deleted features or changed globals/equations -> the script stops (exit 3) and prints what changed.
  **Ask the user**, then rerun with `--update` (keep hand edits), `--adopt` (hand-changed globals ->
  params.py) or `--rebuild` (discard; only with explicit consent).
- Update mode: features that exist with the same definition are skipped, new ones are appended at the end
  of the tree, a changed definition raises `SyncConflict` (needs a rebuild or replacing that feature).
  Prefer update mode for small additions (a teardrop, a chamfer, a slot): seconds instead of minutes,
  hand edits and drawing references survive. Add the feature to the build script too, so a future
  rebuild still has it.
- A shared equation file is protected the same way (`check_shared` + a `.last.json` snapshot).
- Parts built before manifests existed: run each build script once with `--update` (legacy mode trusts
  the existing names) to write a baseline manifest without changing geometry.
- Self test: `python scripts/sync_test.py` must print `SYNC TEST OK`.
- Update mode also changes existing features in place when only their dimension expressions changed
  (the equations are rewritten; polyline-only sketches are redrawn). Changed structure (feature kind,
  parent plane, cut direction, sign of a value) still needs a rebuild.
- `--no-link` keeps the globals inside each part instead of linking `shared_params.txt` (pitfall 41).
- Long builds: `SWCAD_TRACE=1` prints one timestamped line per feature - log it to a file and treat
  2-3 minutes without a new line as a hang (pitfall 42).

## Any file, not only parts: `scripts/filesafe.py` (verified 2026-11-11)
Assemblies, drawings and text files have no manifest. `filesafe` records every file the library writes (size +
modified time, `<folder>/.swstate.json`) and `sw_common.save_as` / `save_doc` use it:
- before saving over a file that changed since the script wrote it (or that it never wrote): the file is copied
  to `<parent of the CAD folder>/_backup/<timestamp>/` (outside the CAD folder: Pack and Go / PDM do not see it);
- policy `SW_ON_HAND_EDIT=backup` (default): keep the copy, print one note line, continue;
  `SW_ON_HAND_EDIT=stop`: raise `filesafe.HandEdit` - ask the user (keep mine / adopt / overwrite).
- Save documents through `save_as` / `save_doc`, not a raw `Save3`: an unrecorded save looks like a hand edit next
  time (harmless - one extra backup and a note - but misleading).
Self test without SolidWorks: `python scripts/filesafe.py` -> `FILESAFE TEST OK`.

## Two-way values: a value changed in SolidWorks flows back to the parameter file (verified 2026-11-11)
The engineer may change a global in Tools > Equations instead of the parameter file. On the next run:
```python
P = paramfile.values(PARAMS_TXT)
pb = PartBuilder(sw, P, path=PATH, mode="update")
rep = partsync.check_open(pb.doc, PATH)                       # what changed by hand since the last script write
pull, same, conflict = partsync.classify_values(rep["globals_changed"], P)
if conflict or not partsync.additive_only(rep):
    ...stop and ask (print partsync.describe(rep))            # both sides changed, or something was deleted
for name, (old, new) in pull.items():
    paramfile.set_value(PARAMS_TXT, name, new, "from SolidWorks")   # note kept: '... | from SolidWorks <date>: 100 -> 120'
    P[name] = pb.params[name] = new
build(pb); pb.push_globals(); pb.save(PATH)                   # nothing is pushed back over the human's value
```
Three-way rule (last written by the script / in the file now / in the parameter file):
only the file changed -> **pull** (the human wins, the parameter file is updated, then rerun so every other part
that uses the value follows); parameter file already equal -> nothing; both changed or not a parameter ->
**conflict**, stop and ask. `paramfile.py` is the generic text format (`NAME = value ; note`, `[GROUP]`,
`[SET name]`), with `set_value` rewriting one line in place.

## Hand-added features are kept
Update mode skips features that exist and appends new ones; features a human added stay (test: a hand-made hole
survived the next script run, and the run after it reported no drift). Ask people to prefix their own features
(`USER_...`) so the tree shows who owns what. The geometry check (`verify`: bbox / volume against the hand
calculation) no longer describes a part with hand features - say so in the report instead of failing or hiding it.
Deleted features, edited equations and changed suppression are NOT additive: stop and ask.
