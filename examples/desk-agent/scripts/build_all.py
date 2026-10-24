"""Rebuild the whole project in order (SolidWorks must be open). Edit params.py first.

    python build_all.py            # everything
    python build_all.py enclosure  # only steps 2-6 (front frame ... final print STLs)
    flags: --update (keep hand edits, append new features) --adopt (hand-changed globals -> params.py)
           --rebuild (discard hand edits) --adopt-shared / --overwrite-shared (shared_params.txt edits)
"""
import subprocess
import sys

STEPS = {
    "components": [["step0_components.py", "all"], ["step0_layout.py"]],
    "coupons": [["step1_coupons.py", "all"], ["make_print_stls.py"]],
    "enclosure": [["step2_front_frame.py"], ["step3_back_body.py"], ["step4_diffuser.py"],
                  ["step5_stand.py"], ["step6_assembly.py"], ["make_print_stls.py", "final"]],
}

if __name__ == "__main__":
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    groups = [a for a in sys.argv[1:] if not a.startswith("--")] or list(STEPS)
    for g in groups:
        for cmd in STEPS[g]:
            print(f"==> {' '.join(cmd)}", flush=True)
            r = subprocess.run([sys.executable, "-u", *cmd, *flags])
            if r.returncode == 3:
                sys.exit(f"STOPPED at {' '.join(cmd)}: hand edits need a decision (see the report above)")
            if r.returncode:
                sys.exit(f"FAILED: {' '.join(cmd)}")
    print("ALL OK")
