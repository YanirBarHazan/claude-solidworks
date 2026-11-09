# Version notes

The library was developed on SolidWorks 2025. Findings on other versions go here: symptom, cause, workaround.

## Version guard
Several versions on one PC are common (2019 + 2020 seen). A part saved by a newer version cannot be opened by an
older one, ever. `connect()` must refuse unless `RevisionNumber()` starts with the required major
(`SW_REQUIRE_REV`, e.g. `27.` = 2019, `28.` = 2020 ... `33.` = 2025). Tell the user to close the other version and
never to open project files by double-click while two versions are installed.

## SolidWorks 2019 (revision 27.x)
| # | Symptom | Cause | Workaround |
|---|---|---|---|
| 1 | `Equations` error 51 after save + reopen (2 of 3 runs) | `IEquationMgr.LinkToFile` to an external txt | do not link; globals live in each part (`--no-link`); a project text file + update script replaces the link |
| 2 | `GetPackAndGo()` → "Parameter not optional" / "Invalid number of parameters" | 2019 type library signature | Pack and Go by hand (or investigate the late-bound call) |
| 3 | Crash when opening the ~46th document in a row | each `OpenDoc6` opens a window | `sw.DocumentVisible(False, type)` while loading, restore in `finally` |
| 4 | `InterferenceDetectionManager` is None | assembly opened without a window is not active | open normally + `ActivateDoc3` |
| 5 | Interference on ~740 comps hangs / "object disconnected" | job size | see assemblies.md §5 |
| 6 | Next open hangs on a modal "file in use" dialog | `~$*.sld*` locks left by a crashed instance | before each run with no documents open: delete stale lock files of the project |
| 7 | Colour read back differs from the value set (0.05 → 0.047) | `MaterialPropertyValues` stored as 8-bit RGB | compare with 1/255 tolerance |
| 8 | COM blocked, no error | any modal dialog | lock-file hygiene; trace log + stall detector (pitfall 42) |
| 9 | Non-ASCII project path | worked for parts, assemblies and saves | set `PYTHONIOENCODING=utf-8`; avoid shell heredocs with non-ASCII text, write files with the file tool |
