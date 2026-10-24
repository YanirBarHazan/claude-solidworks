"""Write print-ready STLs of the test coupons: rotated to their print orientation,
resting on Z=0, centred in X/Y. Input: stl/ (SolidWorks export). Output: print_tests/."""
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "stl")
DST = os.path.join(HERE, "print_tests")
os.makedirs(DST, exist_ok=True)

FLIP_X = ((1, 0, 0), (0, -1, 0), (0, 0, -1))      # upside down (180 deg about X)
SIDE = ((0, 0, 1), (0, 1, 0), (-1, 0, 0))         # X axis -> vertical (90 deg about Y)
KEEP = ((1, 0, 0), (0, 1, 0), (0, 0, 1))

ORIENT = {
    "test_A_lip": KEEP,       # plate on the bed, lip up
    "test_A_wall": FLIP_X,    # back plate on the bed
    "test_B_frame": FLIP_X,   # front face on the bed
    "test_C_base": KEEP,      # plate on the bed
    "test_C_leg": SIDE,       # wheel face on the bed
    "test_C_pin": SIDE,       # standing (use a brim)
}


def rot(m, v):
    return tuple(sum(m[i][j] * v[j] for j in range(3)) for i in range(3))


FINAL = {
    "front_frame": FLIP_X,    # front face on the bed
    "back_body": KEEP,        # back on the bed
    "diffuser": KEEP,         # flange on the bed (white / natural PLA)
    "hinge_block": FLIP_X,    # contact face on the bed
    "stand_leg": SIDE,        # on its side: flat profile, crisp detent notches, round pin hole
    "hinge_pin": SIDE,        # standing (use a brim)
}


def convert(name, m, dst=DST):
    b = open(os.path.join(SRC, name + ".stl"), "rb").read()
    n = struct.unpack("<I", b[80:84])[0]
    tris = []
    for i in range(n):
        f = struct.unpack("<12f", b[84 + 50 * i:84 + 50 * i + 48])
        tris.append([rot(m, f[k:k + 3]) for k in range(0, 12, 3)])
    pts = [p for t in tris for p in t[1:]]
    lo = [min(p[k] for p in pts) for k in range(3)]
    hi = [max(p[k] for p in pts) for k in range(3)]
    off = (-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2])
    out = bytearray(b"print-ready coupon".ljust(80, b" ")) + struct.pack("<I", n)
    for t in tris:
        nrm, *vs = t
        out += struct.pack("<3f", *nrm)
        for v in vs:
            out += struct.pack("<3f", *(v[k] + off[k] for k in range(3)))
        out += b"\0\0"
    os.makedirs(dst, exist_ok=True)
    path = os.path.join(dst, name + ".stl")
    open(path, "wb").write(out)
    size = [hi[k] - lo[k] for k in range(3)]
    return path, n, size


if __name__ == "__main__":
    import sys
    final = len(sys.argv) > 1 and sys.argv[1] == "final"
    table, dst = (FINAL, os.path.join(HERE, "print_final")) if final else (ORIENT, DST)
    for name, m in table.items():
        path, n, size = convert(name, m, dst)
        print(f"{name}: {n} triangles, {size[0]:.1f} x {size[1]:.1f} x {size[2]:.1f} mm (height last)")
