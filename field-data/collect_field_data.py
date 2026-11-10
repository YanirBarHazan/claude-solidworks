"""Collect the day's tracking data from logs/ into out/field_data/<date>/ (CSV + README), for the skill repository.
Re-runnable: run it at the end of every working day.
  runs.csv      one row per batch run: method version, parts, built / updated / unchanged / failed, wall time
  parts.csv     one row per part per run (new-method runs): action, seconds, change
  versions.csv  method versions and what changed between them, with the measured effect
  checks.csv    verification result lines (assembly / geometry checks)
  errors.csv    the SolidWorks error log (tools/SW2019_NOTES.md)
  metrics.csv   cost per task (context tokens, plan %, wall time) + metrics.svg
Anonymised: no file paths, people or purchased part numbers."""
import csv
import datetime
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS = os.path.join(ROOT, "logs")
DATE = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
OUT = os.path.join(ROOT, "out", "field_data", DATE)
os.makedirs(OUT, exist_ok=True)

# run log -> (method version, description); old-method runs have no per-part times (from timestamps)
RUNS = [
    ("step1_all", "1.0", "56 parts after a rule change (holes, eye bolts, colours)", 50 * 60),
    ("step12_parts", "1.0", "36 new/changed parts (own anchors, trellis, walk cable)", 15 * 60),
    ("step16_parts", "1.0", "62 changed parts (holes moved, rods, cables); crashed at 46", 19.7 * 60),
    ("run_all_1", "1.2", "all 70 parts, one session, update in place (first run)", None),
    ("seed_fp", "1.3", "store fingerprints after a verified run (no SolidWorks)", None),
    ("run_all_2", "1.3", "all 70 parts, no change, fingerprints", None),
    ("run_hole65", "1.3", "value change TOP_HOLE1 60->65 on the whole model", None),
    ("run_hole60", "1.3", "value restored 65->60", None),
    ("run_ancb1500", "1.3", "value change ANC_OFF_B 2000->1500", None),
    ("run_planes", "1.3", "named reference planes appended to 8 parts (mates)", None),
    ("run_eye15", "1.3", "measured eye-bolt ring (EYE_ID 30->15): cable lengths", None),
]
PARTS_RE = re.compile(r"^PARTS (\d+)/(\d+) OK - built (\d+), updated (\d+), unchanged (\d+), failed (\d+); (\d+) s")
OLD_RE = re.compile(r"^STEP1 parts: (\d+)/(\d+) OK")
LINE_RE = re.compile(r"^(OK|FAIL|STOP) (\S+)\s+(.*)$")


def sec(text):
    m = re.findall(r"([0-9]+\.?[0-9]*) s\)?\s*$", text)
    return float(m[-1]) if m else ""


runs, parts = [], []
for name, ver, desc, est in RUNS:
    path = os.path.join(LOGS, name + ".log")
    if not os.path.exists(path):
        continue
    lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    row = dict(run=name, method=ver, what=desc, parts="", ok="", built="", updated="", unchanged="", failed="",
               wall_s="", timing="")
    for l in lines:
        m = PARTS_RE.match(l)
        if m:
            ok, n, b, u, c, f, s = m.groups()
            row.update(parts=n, ok=ok, built=b, updated=u, unchanged=c, failed=f, wall_s=s, timing="measured")
        m = OLD_RE.match(l)
        if m:
            row.update(parts=m.group(2), ok=m.group(1), built=m.group(1), updated=0, unchanged=0,
                       failed=int(m.group(2)) - int(m.group(1)), wall_s=round(est), timing="from log timestamps")
    for l in lines:
        m = LINE_RE.match(l)
        if not m:
            continue
        status, part, rest = m.groups()
        if part.startswith(("9", "proto")):
            continue
        if "fingerprint" in rest:
            action = "skipped (fingerprint)"
        elif "unchanged" in rest:
            action = "unchanged (opened)"
        elif "UPDATED" in rest:
            action = "updated in place"
        elif "BUILT" in rest or (ver == "1.0" and status == "OK"):
            action = "built from scratch"
        else:
            action = status.lower()
        change = re.search(r"\((.*?)\)", rest)
        parts.append(dict(run=name, method=ver, part=part, status=status, action=action,
                          seconds=sec(rest) if ver != "1.0" else "",
                          change=change.group(1)[:120] if change and "UPDATED" in rest else ""))
    runs.append(row)


SCRUB = [(re.compile(r"\b(Yanir|Dotan|Hillel)\b|יניר|דותן|הלל"), "the user"), (re.compile(r"\b9\d{10}\b"), "<purchased part>"),
         (re.compile(r"[A-Za-z]:\\[^\s,\"]+"), "<path>"), (re.compile(r"Azrom|עזרום|Portugal|פורטוגל|avocado|אבוקדו", re.I), "<project>")]


def scrub(v):
    """Anonymise every value written to the public field data (people, purchased part numbers, paths, project)."""
    if not isinstance(v, str):
        return v
    for pat, rep in SCRUB:
        v = pat.sub(rep, v)
    return v


def write(name, rows, fields):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: scrub(r.get(k, "")) for k in fields})


write("runs.csv", runs, ["run", "method", "what", "parts", "ok", "built", "updated", "unchanged", "failed", "wall_s",
                         "timing"])
write("parts.csv", parts, ["run", "method", "part", "status", "action", "seconds", "change"])

VERSIONS = [
    ("1.0", "skill as installed", "one Python process per part, every part rebuilt from scratch on every change",
     "pole 43 s, rod 30 s, cable 24 s per build; a value change = 62 rebuilds, ~27 min; edge ids renewed"),
    ("1.1", "update in place", "PartBuilder update mode + push_globals + verify; stop on hand edits / structure change",
     "one pole: value change in place, 47 s, 0 rebuilds; holes measured 60->65->60"),
    ("1.1a", "6-digit compare", "SolidWorks stores globals to ~6 digits (2/3)",
     "no-change run stopped 'updating' V_LOW: unchanged pole 19.8 s, file untouched"),
    ("1.2-exp", "configuration per length", "configuration-specific global values",
     "isolated test OK; in batch: internal errors, 2 crashes, ~65 k context tokens -> abandoned"),
    ("1.2", "one session + hygiene + one open", "runpy batch, stale locks, stall heartbeat, partsync.check_open",
     "70 parts 19 min: 56 unchanged at 14.6 s, 4 updated, 10 new; 0 rebuilds of existing; ~10 k tokens"),
    ("1.3", "fingerprint skip", "hash(script + values + props + colour) + file mtime in the manifest",
     "no-change run of 70 parts: 1 s (was 19 min); value change: 0 rebuilt, 36 updated, ~15 min"),
    ("1.3a", "fingerprint scope", "shared module hashed only for scripts that import it",
     "before: one shared-module edit reopened all 70 parts (13 min)"),
    ("1.4", "mates on named planes", "planes appended in place; plane-to-plane mates; transform check after solve",
     "6 sub-assemblies, up to 12 comps / 33 mates each, 0 mate errors, solved = computed 0.0000; distance mates auto-flipped"),
    ("1.5", "seeds + component linear patterns", "patterns.plan + linear_pattern (marks 1 / 2 / 4, FeatureLinearPattern2)",
     "corner 194 comps: 95 placed + 48 patterns, exact, 55 s; main plan 770 -> 213 placed (117 patterns)"),
]
write("versions.csv", [dict(version=a, name=b, change=c, measured_effect=d) for a, b, c, d in VERSIONS],
      ["version", "name", "change", "measured_effect"])

checks = []
for f in ("step34_verify", "step12_verify", "step2", "step12_sa", "step3_build", "step12_main"):
    p = os.path.join(LOGS, f + ".log")
    if os.path.exists(p):
        for l in open(p, encoding="utf-8", errors="replace"):
            if re.match(r"^(OK|FAIL|STEP|3[a-e]|4[a-c]|saved|  added)", l):
                checks.append(dict(log=f, line=l.strip()[:220]))
write("checks.csv", checks, ["log", "line"])

errors = []
notes = os.path.join(ROOT, "tools", "SW2019_NOTES.md")
for l in open(notes, encoding="utf-8"):
    if l.startswith("| 09/11") or l.startswith("| 9/11"):
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if len(cells) >= 4:
            errors.append(dict(date="2026-11-09", symptom=cells[1], cause=cells[2], status=cells[3]))
    elif l.startswith("- ") and not errors:
        errors.append(dict(date="2026-11-09", symptom=l[2:].strip()[:300], cause="", status="see note"))
write("errors.csv", errors, ["date", "symptom", "cause", "status"])

for f in ("metrics.csv", "metrics.svg"):
    src = os.path.join(ROOT, "out", f)
    if os.path.exists(src):
        shutil.copy(src, os.path.join(OUT, f))
print(f"field data -> {OUT}: runs {len(runs)}, part rows {len(parts)}, versions {len(VERSIONS)}, checks {len(checks)}, "
      f"errors {len(errors)}")
