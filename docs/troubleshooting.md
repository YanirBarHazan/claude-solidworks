# Troubleshooting

Start here, and if your problem isn't listed, look in the [full pitfalls list](../skill/solidworks-api/references/pitfalls.md).

| Symptom | Cause | Fix |
|---|---|---|
| `Operation unavailable` when connecting | SolidWorks isn't running, runs as administrator, or isn't registered yet | Start SolidWorks normally from the Start menu, wait until it has fully opened, and try again. |
| `'str' object is not callable` | Late binding: the type libraries weren't loaded | Use `sw_common.connect()`. Don't connect with `win32com.client.Dispatch` yourself. |
| `centre point not found in SK_...` | A fresh SolidWorks session drew a rectangle without its centre point | Fixed in `swcad.py`, which adds the point itself. Run `smoke_test.py` on each new session. |
| A build sits for minutes without progress | A COM call hung | Run with `set SWCAD_TRACE=1` to log each feature with a timestamp. Two minutes without a new line means a hang. |
| It hangs at "linking to the shared parameters file" | `LinkToFile` can hang SolidWorks (cause unknown) | Build with `--no-link`. The globals stay inside each part. |
| `SaveAs failed ... err=1` | Another open document has the same name | `close_out_docs(sw)` before saving. The drift check now closes what it opened. |
| A script stops with exit code 3 and a report | You changed the part by hand | Read the report, then rerun with `--update`, `--adopt` or `--rebuild`. |
| `OpenDoc6` returns None | Relative path | Always pass `os.path.abspath(path)`. |
| STL or picture export returns False | The document isn't the active one | `sw.ActivateDoc3(title, ...)` first. |
| "File in use" after a crash | Lock files `~$part.sldprt` left behind | Delete only the lock files of the instance that crashed. |
| SolidWorks preferences feel different after a crash | The script's sketch toggles weren't restored | The next run restores them from `%TEMP%\solidworks_api_prefs_backup.json`. |

## Self tests

```bash
python scripts\smoke_test.py     # builds, edits, reopens, exports a small part -> SMOKE TEST OK
python scripts\sync_test.py      # hand-edit protection and update mode        -> SYNC TEST OK
```

Run them from the skill folder with SolidWorks open. Run them after every SolidWorks update or restart before a long build.
