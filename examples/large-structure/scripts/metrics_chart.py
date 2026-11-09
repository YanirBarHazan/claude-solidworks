"""out/metrics.csv -> out/metrics.svg: per task, context tokens spent (delta of the measured context size) and
wall time of the SolidWorks work, so the improvement of the method is visible over the day. No external libraries."""
import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = list(csv.DictReader(open(os.path.join(ROOT, "out", "metrics.csv"), encoding="utf-8")))
tasks = []
prev = None
for r in rows:
    ctx = int(r["ctx_tokens"]) if r["ctx_tokens"] else None
    if prev is not None and ctx is not None:
        tasks.append(dict(name=r["task"], tok=(ctx - prev) / 1000.0, wall=float(r["wall_s"] or 0) / 60.0,
                          built=r["built"], upd=r["updated"], unch=r["unchanged"], time=r["time"]))
    if ctx is not None:
        prev = ctx

W, H, PAD, BAR = 900, 420, 70, 0.36
n = max(len(tasks), 1)
step = (W - 2 * PAD) / n
tmax = max([t["tok"] for t in tasks] + [1])
wmax = max([t["wall"] for t in tasks] + [1])
plot_h = H - 2 * PAD - 40
out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H + 120}" font-family="Segoe UI, Arial" font-size="12">',
       '<rect width="100%" height="100%" fill="#ffffff"/>',
       f'<text x="{PAD}" y="28" font-size="16" font-weight="bold">Cost per task (measured)</text>',
       f'<text x="{PAD}" y="46" fill="#555">blue: context tokens spent (k) | orange: SolidWorks wall time (min)</text>']
base = H - PAD
for i, t in enumerate(tasks):
    x0 = PAD + i * step + step * 0.1
    bw = step * BAR
    h1 = plot_h * t["tok"] / tmax
    h2 = plot_h * t["wall"] / wmax
    out.append(f'<rect x="{x0:.1f}" y="{base - h1:.1f}" width="{bw:.1f}" height="{h1:.1f}" fill="#2f6fd6"/>')
    out.append(f'<text x="{x0 + bw / 2:.1f}" y="{base - h1 - 4:.1f}" text-anchor="middle">{t["tok"]:.0f}k</text>')
    out.append(f'<rect x="{x0 + bw:.1f}" y="{base - h2:.1f}" width="{bw:.1f}" height="{h2:.1f}" fill="#e8892b"/>')
    if t["wall"]:
        out.append(f'<text x="{x0 + 1.5 * bw:.1f}" y="{base - h2 - 4:.1f}" text-anchor="middle">{t["wall"]:.1f}m</text>')
    label = t["name"][:34]
    out.append(f'<text transform="translate({x0 + bw:.1f},{base + 14}) rotate(28)" fill="#222">{t["time"]} {label}</text>')
    if t["built"] or t["upd"] or t["unch"]:
        out.append(f'<text transform="translate({x0 + bw:.1f},{base + 28}) rotate(28)" fill="#666">'
                   f'built {t["built"] or 0} / upd {t["upd"] or 0} / same {t["unch"] or 0}</text>')
out.append(f'<line x1="{PAD}" y1="{base}" x2="{W - PAD}" y2="{base}" stroke="#333"/>')
out.append("</svg>")
path = os.path.join(ROOT, "out", "metrics.svg")
open(path, "w", encoding="utf-8").write("\n".join(out))
print(f"metrics chart: {len(tasks)} tasks -> {path}")
