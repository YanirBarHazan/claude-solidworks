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
| 10 | Every update run "changes" a value like 2/3 | global values are stored to ~6 significant digits (0.666667) | compare at 1e-6 relative (`push_globals`) |
| 11 | Documents from failed runs stay open; a later `SaveAs` of the same name returns error 1 | `close_out_docs` only closed documents directly in `SW_OUT` | close documents in any sub-folder of `SW_OUT` too; close the part's documents on every failure in a one-session batch |
| 12 | `AddConfiguration2` -> "Internal application error" | adding a configuration after a `ShowConfiguration2` | add all configurations first |
| 13 | `SetEquationAndConfigurationOption` -> "Internal application error" on a new part | first configuration-specific value set on a new configuration | set it first on the template's configuration (renamed after the others exist) |
| 14 | `SaveAs` ok=False err=1 although the file is written (configured part) | not isolated; unsaved test parts and the template `Part.prtdot` were open | open |
| 15 | On a clean restart, the configured-part code -> "Internal application error" twice, then a crash | configuration-specific equations in a batch (suspect `GetConfigurationNames()` on an unsaved part before `AddConfiguration2`) | **do not use**; configurations by suppression |
| 16 | "RPC failed" / "object disconnected" mid-build, SolidWorks closes by itself | suspected: VPN drop -> network licence (SolidNetWork) lost | keep the VPN up or borrow a licence; scripts save per file and can resume |
| 17 | `NewDocument` works, then throws "The server threw an exception" a minute later | instance in a bad state (template `Part.prtdot` was open as a document) | restart SolidWorks |
| 18 | Shell heredocs with long Python fail ("unexpected EOF") | quoting in the shell wrapper | write files with the file tool and run them |
| 19 | `ISldWorks.VersionHistoryFromFile` missing in the 2019 type library | API age | `IModelDoc2.VersionHistory()` after opening; a file that opens in 2019 was saved by <= 2019 |
| 20 | `InterferenceDetectionManager` on 738 comps: hang / disconnect | job size | per sub-assembly + ~190-comp cut-out assembly + Python clearances |

## How this table is kept
Every new failure gets a row in the same turn (symptom | cause found or suspected | status). Rows 10-20 come from one
day on a 738-component model; see `field_log_2026-11-09.md` for the context and the measured cost of each.
