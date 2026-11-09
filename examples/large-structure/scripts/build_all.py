"""Run part scripts in ONE Python process and ONE SolidWorks session (ROADMAP 7), update in place by default.
One summary line per part; details of each part go to logs/<name>.log. Ends with counts and the wall time.
Usage: python build_all.py [script [arg] ...]      (no arguments = every part of the model)
       python build_all.py --rebuild ...          (only with the user's consent: rebuilds existing parts)"""
import contextlib
import io
import os
import runpy
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LOGS = os.path.join(os.path.dirname(HERE), "logs")
import nh_common as NC  # noqa: E402
import layout  # noqa: E402
import hygiene  # noqa: E402


def parts():
    LY = layout.build(NC.P)
    return (["part_pole_3in", "part_pole_3in_w", "part_pole_3in_c", "part_pole_2in", "part_cap_3in", "part_cap_2in",
             "part_plate_int", "part_stub_3in", "part_fdn_perim", "part_anc_block", "part_eyebolt",
             "part_chamor_post", "part_chamor_fdn"] +
            ["part_anc_rod " + n for n in sorted(LY["rods"])] + ["part_cbl " + n for n in sorted(LY["cfiles"])])


def run(todo, extra_argv=()):
    t0 = time.time()
    sw = NC.connect()
    hygiene.prerun(sw, NC.CAD)
    stall = hygiene.Stall(os.path.join(LOGS, "build_all.trace"), seconds=180)
    fails = 0
    for s in todo:
        script, *args = s.split()
        NC.reset_params()
        log = os.path.join(LOGS, (args[0] if args else script) + ".log")
        buf = io.StringIO()
        old_argv = sys.argv
        sys.argv = [script + ".py", *args, *extra_argv]
        stall.beat(s)
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                runpy.run_path(os.path.join(HERE, script + ".py"), run_name="__main__")
            rc = 0
        except SystemExit as ex:
            rc = ex.code or 0
        finally:
            sys.argv = old_argv
        text = buf.getvalue()
        open(log, "w", encoding="utf-8").write(text)
        last = [l for l in text.splitlines() if l.startswith(("OK ", "FAIL ", "STOP "))]
        print(last[-1] if last else f"FAIL {s}: no summary (see {log})", flush=True)
        fails += rc != 0
        if rc in (3, 4):                     # a decision for the user: stop the batch here
            print("batch stopped: a part needs your decision", flush=True)
            break
    stall.stop()
    c = NC.COUNTS
    print(f"PARTS {len(todo) - fails}/{len(todo)} OK - built {c['built']}, updated {c['updated']}, "
          f"unchanged {c['unchanged']}, failed {c['failed']}; {time.time() - t0:.0f} s", flush=True)
    return 1 if fails else 0


if __name__ == "__main__":
    extra = [a for a in sys.argv[1:] if a.startswith("--")]
    todo = [a for a in sys.argv[1:] if not a.startswith("--")] or parts()
    sys.exit(run(todo, extra))
