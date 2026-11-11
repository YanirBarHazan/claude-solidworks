# Verify every part and assembly - never report success without numbers

Run these after each part, print the results, and stop on any failure:
1. `rebuild_errors()` empty and exactly one solid body (unless intended).
2. Bounding box equals the design to 0.001 mm; volume equals a hand calculation (exact for prismatic
   parts; numpy grid integration for curved profiles).
3. **Edit test**: change a global variable, rebuild, check the geometry moved as expected, restore.
4. `save()` = save, close, reopen, rebuild → zero errors (catches session-only artefacts).
5. In assemblies: `check_interference(asm, expected)` with an explicit list of *designed* overlaps
   (press fits, crush ribs, detent preload, a plug tip in its socket). Anything else is a bug —
   and an absent expected overlap is also a bug (e.g. a snap hook not in its groove).
   Sweep moving parts through every position (`comp.Transform2`, rebuild, check).
6. Look at the pictures (`picture()`), and question what you see — the automatic checks once passed
   a leg joined to its wheel by a 1 mm sliver; only the side view showed it.

## Fully defined sketches (gate in `verify`, 2026-11-11)
`PartBuilder.verify` now fails when any sketch is not fully defined (`pb.open_sketches()` lists them; pass
`sketches=False` only for an imported / hand-made sketch you report to the user). An under-defined sketch is why a
model "explodes" when someone else changes a value. `scripts/audit.py` reports the same for any existing part.
