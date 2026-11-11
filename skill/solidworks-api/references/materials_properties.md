# Materials, mass and properties that follow the model

A text property "Material = S235" is not a material: SolidWorks has no density, so no mass, no weight in the BOM
and nothing for a simulation. Field baseline (`scripts/audit.py`): 76 of 76 parts had only the text.

## Recipe (`PartBuilder`, verified on SolidWorks 2019)
```python
pb.material("Plain Carbon Steel")            # exact name in the SOLIDWORKS Materials database; a wrong name raises
m, want = pb.check_mass(7800.0)              # mass = volume x the density YOU expect, +-0.5 % - else it raises
pb.save(path)
props = pb.link_properties()                 # Weight = "SW-Mass@<file>", Material = "SW-Material@<file>"
```
- `material(name, database="SOLIDWORKS Materials")` reads the name back; an unknown name leaves the part without
  material, so the read-back is the check. Company materials live in a custom database: pass its name.
- `check_mass` catches the two real mistakes: the wrong material, and a geometry / unit error (a 100 mm steel cube
  must weigh 7.8 kg).
- `link_properties` makes the title block, BOM and PDM card follow the model. The weight is evaluated in the
  DOCUMENT's mass unit: an MMGS template gives grams (7.8 kg reads "7800.00"). Decide the unit with the user
  (template units) rather than converting in text.
- Ask in the design brief (`dialogue.md` D) for the material names as they appear in the company's database; map
  the user's own names (S235, galvanised) to them in the parameter file with a source tag.
- Existing parts: applying a material is an in-place update (no feature changes) - never a reason to rebuild.

## Still to add (roadmap phase 5)
Company templates (units, title block) and feature folders. Done since: Hole Wizard, feature patterns and
mirror (`part_features.md`), the fully-defined-sketch gate (`verification.md`). Each needs its own live test before it is written here.
