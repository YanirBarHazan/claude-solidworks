"""PLAN 16.2-16.4c: whole-model clearances in Python, from the layout geometry (no SolidWorks).
  rods / blocks: minimum distance between any two (rod-rod, block-block, rod-other block) >= 300
  cable - pole:  centreline distance - radii; designed contacts: cable alongside a pole (0, tangent),
                 cable end in its chamor hole; anything below -0.01 mm otherwise is a bug
  cable - cap:   roof / facade cables >= 10 mm clear of every cap (16.3); other cables >= 0
Prints one line per check and 'GEOMETRY OK' / 'GEOMETRY FAIL'."""
import math
import sys

from nh_common import P
import layout as LY


def seg_seg(p1, q1, p2, q2):
    """Minimum distance between segments p1q1 and p2q2."""
    d1, d2, r = LY.sub(q1, p1), LY.sub(q2, p2), LY.sub(p1, p2)
    a, e, f = LY.dot(d1, d1), LY.dot(d2, d2), LY.dot(d2, r)
    if a <= 1e-12 and e <= 1e-12:
        return LY.norm(r)
    if a <= 1e-12:
        s, t = 0.0, min(max(f / e, 0.0), 1.0)
    else:
        c = LY.dot(d1, r)
        if e <= 1e-12:
            t, s = 0.0, min(max(-c / a, 0.0), 1.0)
        else:
            b = LY.dot(d1, d2)
            den = a * e - b * b
            s = min(max((b * f - c * e) / den, 0.0), 1.0) if den > 1e-12 else 0.0
            t = (b * s + f) / e
            if t < 0:
                t, s = 0.0, min(max(-c / a, 0.0), 1.0)
            elif t > 1:
                t, s = 1.0, min(max((b - c) / a, 0.0), 1.0)
    return LY.norm(LY.sub(LY.add(p1, LY.mul(d1, s)), LY.add(p2, LY.mul(d2, t))))


def seg_cyl(p, q, c0, c1, R, step=0.5):
    """Clearance between segment pq (centreline) and a FLAT-ended solid cylinder c0-c1 of radius R, sampled every
    `step` mm along pq near its closest approach (a capsule test would add false round ends)."""
    ax = LY.sub(c1, c0)
    h = LY.norm(ax)
    ax = LY.mul(ax, 1 / h)
    d = LY.sub(q, p)
    Lq = LY.norm(d)
    u = LY.mul(d, 1 / Lq)
    # closest approach of the line to the cylinder centre, then sample +-400 mm around it
    mid = LY.mul(LY.add(c0, c1), 0.5)
    t0 = min(max(LY.dot(LY.sub(mid, p), u), 0.0), Lq)
    best = 1e9
    t = max(0.0, t0 - 400)
    while t <= min(Lq, t0 + 400):
        x = LY.add(p, LY.mul(u, t))
        w = LY.sub(x, c0)
        a = LY.dot(w, ax)
        rho = LY.norm(LY.sub(w, LY.mul(ax, a)))
        da = -a if a < 0 else (a - h if a > h else 0.0)
        dr = max(rho - R, 0.0)
        dist = math.hypot(da, dr) if (da > 0 or dr > 0) else -min(R - rho, a, h - a)
        best = min(best, dist)
        t += step
    return best


def box_dist(c1, c2, h):
    """Distance between two axis-aligned cubes of half size h."""
    return math.sqrt(sum(max(0.0, abs(a - b) - 2 * h) ** 2 for a, b in zip(c1, c2)))


def pt_box(pt, c, h):
    return math.sqrt(sum(max(0.0, abs(a - b) - h) ** 2 for a, b in zip(pt, c)))


def main():
    p = P
    L = LY.build(p)
    fails = []
    an = L["anchors"]
    hb = p["ANC_BLOCK"] / 2
    rr = p["ANC_ROD"] / 2
    centres = [LY.add(a["top_c"], (0.0, -hb, 0.0)) for a in an]

    # rods and blocks
    rod_min, blk_min, rb_min = (1e9, None), (1e9, None), (1e9, None)
    for i, a in enumerate(an):
        for j in range(i + 1, len(an)):
            b = an[j]
            if LY.norm(LY.sub(a["ground"], b["ground"])) > 8000:
                continue
            d = seg_seg(a["top_c"], a["tip"], b["top_c"], b["tip"]) - 2 * rr
            rod_min = min(rod_min, (d, (a["ground"], b["ground"])), key=lambda x: x[0])
            d = box_dist(centres[i], centres[j], hb)
            blk_min = min(blk_min, (d, (a["ground"], b["ground"])), key=lambda x: x[0])
    for i, a in enumerate(an):                       # rod of one anchor vs the block of another (sampled)
        for j, b in enumerate(an):
            if i == j or LY.norm(LY.sub(a["ground"], b["ground"])) > 8000:
                continue
            d = min(pt_box(LY.add(a["top_c"], LY.mul(LY.sub(a["tip"], a["top_c"]), k / 200)), centres[j], hb)
                    for k in range(201)) - rr
            rb_min = min(rb_min, (d, (a["ground"], b["ground"])), key=lambda x: x[0])
    worst = min(rod_min, blk_min, rb_min, key=lambda x: x[0])
    ok = worst[0] >= 300
    print(f"{'OK  ' if ok else 'FAIL'} rods/blocks ({len(an)} anchors): min clear rod-rod {rod_min[0]:.0f}, "
          f"block-block {blk_min[0]:.0f}, rod-other block {rb_min[0]:.0f} mm (need >= 300); worst pair at ground "
          f"({worst[1][0][0]:.0f}, {worst[1][0][2]:.0f}) / ({worst[1][1][0]:.0f}, {worst[1][1][2]:.0f})", flush=True)
    if not ok:
        fails.append("rods/blocks")

    # poles (axis from the ground to the top) and chamor posts
    sticks = []
    for q in L["poles"].values():
        sticks.append(dict(name=f"pole {q['pk']}", a=q["base"], b=q["top"], r=q["od"] / 2, top=q["top"], q=q))
    for c in L["chamors"]:
        pos = c["pos"]
        sticks.append(dict(name="chamor", a=LY.add(pos, (0, -p["CHAMOR_EMB"], 0)), b=LY.add(pos, (0, p["CHAMOR_H"], 0)),
                           r=p["P3_OD"] / 2, top=None, q=None))
    dia = {"C_ROOF": p["C_ROOF"], "C_PERIM": p["C_PERIM"], "C_ANCHOR": p["C_ANCHOR"], "C_TR": p["C_TR"], "C_WALK": p["C_WALK"]}
    tol = 0.01
    contacts, bugs, cap_min, cap_min_roof = 0, [], (1e9, ""), (1e9, "")
    for c in L["cables"]:
        rc = dia[c["dia"]] / 2
        mid = LY.mul(LY.add(c["a"], c["b"]), 0.5)
        reach = LY.norm(LY.sub(c["b"], c["a"])) / 2 + 200
        for s in sticks:
            if abs(mid[0] - s["b"][0]) > reach + 1000 or abs(mid[2] - s["b"][2]) > reach + 1000:
                continue
            clr = seg_seg(c["a"], c["b"], s["a"], s["b"]) - rc - s["r"]
            if clr < tol:
                in_hole = s["name"] == "chamor" and c["file"].startswith("CBL-TR")
                if abs(clr) <= tol:
                    contacts += 1
                elif not in_hole:
                    bugs.append((clr, c["file"], s["name"]))
            if s["top"] is not None:                 # cap: sleeve CAP_SKIRT down from the top, CAP_T thick
                ax = LY.unit(LY.sub(s["b"], s["a"]))
                c0, c1 = LY.sub(s["top"], LY.mul(ax, p["CAP_SKIRT"])), LY.add(s["top"], LY.mul(ax, p["CAP_T"]))
                if seg_seg(c["a"], c["b"], c0, c1) - rc - (s["r"] + p["CAP_T"]) > 60:
                    continue                                 # far away: skip the exact test
                cclr = seg_cyl(c["a"], c["b"], c0, c1, s["r"] + p["CAP_T"]) - rc
                cap_min = min(cap_min, (cclr, c["file"]), key=lambda x: x[0])
                if c["file"].startswith(("CBL-ROOF", "CBL-PERIM")):
                    cap_min_roof = min(cap_min_roof, (cclr, c["file"]), key=lambda x: x[0])
    ok = not bugs
    print(f"{'OK  ' if ok else 'FAIL'} cable-pole ({len(L['cables'])} cables x {len(sticks)} poles/posts): designed contacts "
          f"(alongside, tangent within {tol} mm) {contacts}, overlaps {len(bugs)}"
          + (f", worst {min(bugs)[0]:.2f} mm {min(bugs)[1]} / {min(bugs)[2]}" if bugs else ""), flush=True)
    if not ok:
        fails.append("cable-pole")
    ok = cap_min_roof[0] >= 10 and cap_min[0] >= 0
    print(f"{'OK  ' if ok else 'FAIL'} cable-cap: roof/facade cables min clearance {cap_min_roof[0]:.2f} mm "
          f"({cap_min_roof[1]}, need >= 10), all cables min {cap_min[0]:.2f} mm ({cap_min[1]})", flush=True)
    if not ok:
        fails.append("cable-cap")
    print("GEOMETRY OK" if not fails else f"GEOMETRY FAIL: {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
