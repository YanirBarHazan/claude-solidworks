# Intake: one question round before building

Every stop-and-ask round mid-build costs a context reload and often a rebuild. In the net house field test, five
rounds were caused by decisions nobody had made yet. Ask all of these in one message, before any CAD, and write
the answers into the plan file.

## For every part
1. Datum/origin, which dimension is the length rule (fixed, or derived from the layout).
2. What it sits on or inside: fit, embedment depth, clearance, which end is at ground level.
3. Which values are expected to change later (→ build so they update in place).

## For every connection
4. Which feature carries it (hole, eye bolt, loop, shackle), its height, its direction, the exact attach point.
5. What happens where two connections meet the same part (clashing holes, offsets).

## Topology
6. Corners, ends, T-junctions, symmetry lines: does the general rule apply, or is there a special rule?
7. Shared items (one anchor for two poles?) or one per instance?

## Checks
8. Allowed (designed) overlaps, minimum clearances.
9. Counts the user expects (to check against).

## Files and data
10. One file per size or configurations; naming (part numbers); custom properties the PDM card needs; template.
11. Purchased parts: file names, saved version, which simplified part each replaces, where each goes.
12. Target version of SolidWorks and other versions installed.

## Before CAD
Run the Python layout + clearance check on the rule set and show the user the counts and the closest pairs.
Rule conflicts are cheap here and expensive after a one-hour build.

## Plan file hygiene
The plan arrives in sections. Check the file's size/modified time and that the expected section exists before
reading it in full; if it is missing, say so in one line (the file may not have been saved yet).
