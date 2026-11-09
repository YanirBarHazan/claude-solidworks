# Field data

Raw, anonymised tracking data from real projects built with the skill: every batch run, every part in every
run, method versions and their measured effect, verification results, the SolidWorks error log, and the cost per
task (context tokens, plan %, wall time). Open the CSV files in Excel or any spreadsheet. One folder per field day.

| Folder | Project | SolidWorks | Size |
|---|---|---|---|
| [2026-11-09-large-structure](2026-11-09-large-structure/) | cable-braced steel structure | 2019 | 70 parts, 6 sub-assemblies, 738 components |

## Files in each folder
| File | One row per | Columns |
|---|---|---|
| `runs.csv` | batch run | method version, parts, built / updated / unchanged / failed, wall time, how timed |
| `parts.csv` | part in a run | action (built from scratch / updated in place / unchanged opened / skipped by fingerprint), seconds, what changed |
| `versions.csv` | method version | change, measured effect |
| `checks.csv` | verification line | counts, positions, cable ends, clearances, interference |
| `errors.csv` | SolidWorks / API failure | symptom, cause, status (fixed / workaround / open) |
| `metrics.csv` + `metrics.svg` | task | context tokens (measured), 5-hour plan %, wall time, built / updated / unchanged |

## Headline comparison (2026-11-09)
| | Method 1.0 (rebuild every change) | Method 1.3 (update in place + fingerprint) |
|---|---|---|
| Run with no change, 70 parts | ~19 min | **1 s** |
| Value change touching half the parts | 62 rebuilt, ~27 min | **0 rebuilt**, 36 updated, ~15 min |
| Per part: cable / rod / pole | 24 / 30 / 43 s build | 0.0 s skip, ~9 s unchanged-opened, ~21 s updated |
| Context tokens for a 70-part run | - | ~10 k |

## Collect your own
`collect_field_data.py` builds a folder like these from a project's `logs/` and `out/metrics.csv` (run it at the end
of a working day). It anonymises people, purchased part numbers, paths and project names before writing.
Contributions are welcome as a pull request with a new folder; nothing is merged without review.
