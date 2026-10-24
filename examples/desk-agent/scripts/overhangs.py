"""Overhang check of print-oriented STLs (Z up, part resting on Z=0).

A face needs support when it points downward more than OVERHANG_DEG from vertical and is not
on the bed. Nearly horizontal downward faces are bridges: fine when short and supported at
both ends. Each downward region is grouped (connected faces) and reported with its size.
"""
import math
import os
import struct
import sys
from collections import defaultdict

OVERHANG_DEG = 45.0
BED_EPS = 0.25          # faces below this height are on the bed (first layer)


def load(path):
    b = open(path, "rb").read()
    n = struct.unpack("<I", b[80:84])[0]
    tris = []
    for i in range(n):
        f = struct.unpack("<12f", b[84 + 50 * i:84 + 50 * i + 48])
        tris.append((f[3:6], f[6:9], f[9:12]))
    return tris


def normal_area(t):
    a, b, c = t
    u = [b[i] - a[i] for i in range(3)]
    w = [c[i] - a[i] for i in range(3)]
    n = (u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0])
    L = math.sqrt(sum(x * x for x in n)) or 1e-12
    return tuple(x / L for x in n), L / 2


def regions(path):
    tris = load(path)
    lim = -math.cos(math.radians(90 - OVERHANG_DEG))     # nz below this = steeper than 45 deg overhang
    sel = []
    for t in tris:
        n, area = normal_area(t)
        zmin = min(p[2] for p in t)
        if n[2] < lim and zmin > BED_EPS and area > 1e-6:
            sel.append((t, n, area))
    # group by shared vertices
    key = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
    vmap = defaultdict(list)
    for i, (t, _, _) in enumerate(sel):
        for p in t:
            vmap[key(p)].append(i)
    seen, groups = set(), []
    for i in range(len(sel)):
        if i in seen:
            continue
        stack, g = [i], []
        seen.add(i)
        while stack:
            j = stack.pop()
            g.append(j)
            for p in sel[j][0]:
                for k in vmap[key(p)]:
                    if k not in seen:
                        seen.add(k)
                        stack.append(k)
        pts = [p for j in g for p in sel[j][0]]
        lo = [min(p[k] for p in pts) for k in range(3)]
        hi = [max(p[k] for p in pts) for k in range(3)]
        area = sum(sel[j][2] for j in g)
        flat = all(sel[j][1][2] < -0.999 for j in g)
        groups.append(dict(area=area, lo=lo, hi=hi, flat=flat,
                           span=min(hi[0] - lo[0], hi[1] - lo[1]), length=max(hi[0] - lo[0], hi[1] - lo[1])))
    return sorted(groups, key=lambda g: -g["area"])


if __name__ == "__main__":
    folder = sys.argv[1]
    for f in sorted(os.listdir(folder)):
        if not f.lower().endswith(".stl"):
            continue
        gs = regions(os.path.join(folder, f))
        print(f"{f}: {len(gs)} downward regions" + ("" if gs else " -> no overhangs, no support"))
        for g in gs[:8]:
            kind = "flat (bridge/ceiling)" if g["flat"] else "sloped/curved"
            print(f"   {kind:22s} area {g['area']:7.1f} mm2  size {g['hi'][0]-g['lo'][0]:6.2f} x {g['hi'][1]-g['lo'][1]:6.2f} "
                  f"at z {g['lo'][2]:5.2f}..{g['hi'][2]:5.2f}")
