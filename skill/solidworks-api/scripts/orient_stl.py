"""Rotate a binary STL to its print orientation, rest it on Z=0 and centre it in X/Y.

    python orient_stl.py in.stl out.stl --rot flip_x     # upside down (e.g. a front face onto the bed)
    python orient_stl.py in.stl out.stl --rot side_x     # model X axis becomes vertical (part on its X face)
    python orient_stl.py in.stl out.stl --rot side_y     # model Y axis becomes vertical
    python orient_stl.py in.stl out.stl --rot keep

SolidWorks exports in model coordinates; pick the rotation that puts the intended face on the bed,
then confirm with overhangs.py.
"""
import argparse
import struct

ROT = {
    "keep": ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
    "flip_x": ((1, 0, 0), (0, -1, 0), (0, 0, -1)),   # 180 deg about X
    "flip_y": ((-1, 0, 0), (0, 1, 0), (0, 0, -1)),   # 180 deg about Y
    "side_x": ((0, 0, 1), (0, 1, 0), (-1, 0, 0)),    # 90 deg about Y: +X face goes down
    "side_y": ((1, 0, 0), (0, 0, 1), (0, -1, 0)),    # 90 deg about X: +Y face goes down
}


def rot(m, v):
    return tuple(sum(m[i][j] * v[j] for j in range(3)) for i in range(3))


def orient(src, dst, m):
    b = open(src, "rb").read()
    n = struct.unpack("<I", b[80:84])[0]
    tris = []
    for i in range(n):
        f = struct.unpack("<12f", b[84 + 50 * i:84 + 50 * i + 48])
        tris.append([rot(m, f[k:k + 3]) for k in range(0, 12, 3)])
    pts = [p for t in tris for p in t[1:]]
    lo = [min(p[k] for p in pts) for k in range(3)]
    hi = [max(p[k] for p in pts) for k in range(3)]
    off = (-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2])
    out = bytearray(b"print-oriented".ljust(80, b" ")) + struct.pack("<I", n)
    for nrm, *vs in tris:
        out += struct.pack("<3f", *nrm)
        for v in vs:
            out += struct.pack("<3f", *(v[k] + off[k] for k in range(3)))
        out += b"\0\0"
    open(dst, "wb").write(out)
    return n, [hi[k] - lo[k] for k in range(3)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--rot", choices=sorted(ROT), default="keep")
    a = ap.parse_args()
    n, size = orient(a.src, a.dst, ROT[a.rot])
    print(f"{a.dst}: {n} triangles, {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm (height last)")
