# Setup (once per machine, ~2 min)

1. SolidWorks open, same Windows user, **not** "Run as administrator" (else COM can't see it).
2. `pip install pywin32` (numpy optional, for area checks).
3. Copy `scripts/*.py` from this skill into the project folder (they save parts to `./parts`,
   or set env `SW_OUT`). Then smoke-test: `python scripts/smoke_test.py` from the skill folder —
   it builds, edits, reopens, exports and checks a small part, and should print `SMOKE TEST OK`.
4. If several SolidWorks versions are installed, `sw_common` uses the folder of the running
   SLDWORKS.exe (override `SW_DIR`). Check add-ins you will need (e.g. Motion: `cmotionsw.dll`
   in that folder) *before* promising a feature — tell the user early if it's missing.
5. **Version guard.** If the project targets an older SolidWorks (files go to a PDM/team on that version),
   set `SW_REQUIRE_REV` (e.g. `27.` for 2019) and refuse to work on any other running version: a newer save
   can never be reopened by the older one. Read `references/version_notes.md` for known version issues.
6. For a project (not a one-off part), the smoke test can be replaced by a one-minute project check:
   one parametric part, edit test, save/reopen, small assembly, and whatever the project needs at the end
   (e.g. Pack and Go), all in the project folder and path.
