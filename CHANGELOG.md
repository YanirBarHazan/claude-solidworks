# Changelog

Every "What's new" entry from the README, unchanged, newest first. [Back to README](README.md) · [Hebrew](CHANGELOG.he.md)

## 2026-11-11: version 2 foundation - models a human can open, understand and change
- **Design intent lives in SolidWorks.** A skeleton part, seeds mated to it, component patterns driven by assembly
  equations: change a number in Tools > Equations and the assembly follows; only the skeleton is fixed.
  [Recipe](skill/solidworks-api/references/assemblies.md) (section 13)
- **Hand and script together.** A value changed by hand in SolidWorks is pulled back into the parameter file,
  hand-added features are kept, and any file changed since the script wrote it is backed up before it is saved over.
  [Hand edits](skill/solidworks-api/references/hand_edits.md)
- **Real engineering data.** SolidWorks materials with a mass check, weight / material properties that follow the
  model, Hole Wizard holes, feature patterns and mirror with linked counts, a fully-defined-sketch gate.
  [Materials](skill/solidworks-api/references/materials_properties.md) |
  [Part features](skill/solidworks-api/references/part_features.md)
- **`audit.py`**: a health / editability score for any existing part or assembly (read-only).
- **A leaner skill.** SKILL.md is 60% shorter (the v1 text moved word for word into topic modules), plus a design
  brief and a one-page project card for the dialogue with the user.
  [Dialogue](skill/solidworks-api/references/dialogue.md)
- Every item was tested live on SolidWorks 2019 only; each reference lists what is not tested yet.
  [Roadmap](skill/solidworks-api/ROADMAP.md)

## 2026-11-10: configurations, one-command updates, and the bugs a real change exposed
- **Suppression configurations on a 770-component assembly in 35 s each** (was > 25 min): one tree walk, one
  `EditSuppress2`. The timing table that found the cause: [assemblies](skill/solidworks-api/references/assemblies.md)
- **One command for any value change:** parameters text file + `update.bat` -> checks, update in place, assemblies
  regenerated only for layout values, one PASS/FAIL line. 3.5 min for a part value, 17 min for a layout change.
  [Update in place](skill/solidworks-api/references/update_in_place.md)
- **Three traps found by the first layout change** (negative global under `^`, equation edits not saved, crash
  mid-batch) - each caught by a check, not by eye. [Version notes 25-31](skill/solidworks-api/references/version_notes.md) |
  [Field log](skill/solidworks-api/references/field_log_2026-11-10.md) | [Data](field-data/2026-11-10-large-structure/README.md)

## 2026-11-09: field results from a 738-component model in SolidWorks 2019
- **Update in place, never rebuild to change a value.** A run with no change over 70 parts: **1 s** (fingerprints,
  nothing opened) instead of ~19 min; a value change touching half the parts: **0 rebuilds**, ~15 min instead of 62
  rebuilds and ~27 min, with edge ids, mates and drawings kept. [How it works](skill/solidworks-api/references/update_in_place.md)
- **Big assemblies on 2019:** 738 components placed in 60 s; mates inside sub-assemblies on named planes, checked
  against the computed transform; interference by sub-assembly + cut-out + Python clearances. [Assemblies](skill/solidworks-api/references/assemblies.md)
- **20 SolidWorks 2019 traps** with cause and workaround (window limit crash, licence/VPN drops, configuration API
  crashes, 6-digit globals...). [Version notes](skill/solidworks-api/references/version_notes.md)
- **The whole day, measured:** timeline, method versions 1.0-1.4, time and tokens per task, what worked and what
  didn't. [Field log](skill/solidworks-api/references/field_log_2026-11-09.md) | [Example](examples/large-structure/README.md) | [Roadmap](skill/solidworks-api/ROADMAP.md)
- **Raw field data** (every run, every part, versions compared, errors, cost per task, as CSV): [field-data](field-data/README.md)
