"""Turn a placement list into seeds + component linear patterns (no SolidWorks here).
Items with the same file, configuration and orientation whose origins form an equally spaced row along assembly X
(or Z), and rows that repeat equally along the other axis, become ONE pattern: a seed placed by transform + a
1- or 2-direction linear pattern. Anything else stays an individual placement. The result reproduces every origin
exactly (checked in plan()).
Pattern dict: seed item, n1, s1 (mm along +X), n2, s2 (mm along +Z), members (item indices)."""
import collections

TOL = 0.01


def _key(it):
    f, axes, o = it[0], it[1], it[2]
    cfg = it[3] if len(it) > 3 else ""
    return (f, cfg, tuple(round(v, 6) for a in axes for v in a))


def _runs(vals, min_len):
    """Split sorted values into maximal arithmetic runs (equal step) of at least min_len."""
    out, i = [], 0
    while i < len(vals):
        j = i + 1
        if j < len(vals):
            step = vals[j] - vals[i]
            while j + 1 < len(vals) and abs((vals[j + 1] - vals[j]) - step) < TOL:
                j += 1
        if j - i + 1 >= min_len and j < len(vals) and step > TOL:
            out.append((i, j, step))
            i = j + 1
        else:
            out.append((i, i, 0.0))
            i += 1
    return out


def plan(items, min_len=2):
    """-> (patterns, singles). Every item is in exactly one pattern or in singles."""
    groups = collections.defaultdict(list)
    for k, it in enumerate(items):
        groups[_key(it)].append(k)
    patterns, singles = [], []
    for _, idx in groups.items():
        rows = collections.defaultdict(list)                       # same y, z -> row along X
        for k in idx:
            o = items[k][2]
            rows[(round(o[1], 3), round(o[2], 3))].append(k)
        row_runs = []                                              # (x0, step, n, z, y, members sorted by x)
        for (y, z), ks in rows.items():
            ks.sort(key=lambda k: items[k][2][0])
            xs = [items[k][2][0] for k in ks]
            for i, j, step in _runs(xs, min_len):
                row_runs.append((round(xs[i], 3), round(step, 3), j - i + 1, z, y, ks[i:j + 1]))
        # stack equal runs along Z into 2-direction patterns
        stacks = collections.defaultdict(list)
        for r in row_runs:
            stacks[(r[0], r[1], r[2], r[4])].append(r)
        for (x0, step, n, y), rs in stacks.items():
            rs.sort(key=lambda r: r[3])
            zs = [r[3] for r in rs]
            for i, j, zstep in _runs(zs, 2):
                block = rs[i:j + 1]
                members = [k for r in block for k in r[5]]
                if len(members) == 1:
                    singles.append(members[0])
                    continue
                if n == 1:                                         # a column along Z only
                    patterns.append(dict(seed=block[0][5][0], n1=1, s1=0.0, n2=len(block), s2=zstep, members=members))
                else:
                    patterns.append(dict(seed=block[0][5][0], n1=n, s1=step, n2=len(block) if j > i else 1,
                                         s2=zstep if j > i else 0.0, members=members))
    # check: every member origin = seed origin + a*s1*X + b*s2*Z
    for p in patterns:
        s = items[p["seed"]][2]
        want = sorted((round(s[0] + a * p["s1"], 2), round(s[1], 2), round(s[2] + b * p["s2"], 2))
                      for a in range(p["n1"]) for b in range(p["n2"]))
        got = sorted(tuple(round(v, 2) for v in items[k][2]) for k in p["members"])
        if want != got:
            raise AssertionError(f"pattern does not reproduce its members: {items[p['seed']][0]}")
    covered = {k for p in patterns for k in p["members"]}
    singles = sorted(set(range(len(items))) - covered)
    return patterns, singles
