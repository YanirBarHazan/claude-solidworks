# Project card - <project name>

> One page. Approved by the user before building. A new session reads this first.
> Status of every line: `CONFIRMED` (user decided, date) / `ASSUMED` (default, to confirm) / `OPEN` (ask - do not guess).

## 1. Goal
- What is made, for whom:
- Deliverables (files / drawings / BOM / print files / PDM):
- "Done" means:

## 2. Who changes it later, and how
- By values / by hand in SolidWorks / both:
- Who (level, how many), where the files live (local / shared drive / PDM):
- Expected changes (each becomes a parameter): 
- Options on/off (configurations by suppression):
- Size variants (files / value sets):

## 3. Standards
- SolidWorks version that must open the files:            Other versions installed:
- Templates / units:
- Materials (SolidWorks material names):
- Part numbering / file-name prefix:
- Custom properties (PDM card, title block):
- Purchased / library parts (file, used as is?):

## 4. Model structure (design intent)
| Level | What drives it | Placement | Human-editable how |
|---|---|---|---|
| Skeleton / layout |  |  |  |
| Parts |  |  |  |
| Sub-assemblies |  |  |  |
| Top assembly |  |  |  |

## 5. Decisions
| # | Decision | Status | Date | Source |
|---|---|---|---|---|

## 6. Open questions (each blocks: ...)
| # | Question | Blocks | Recommendation |
|---|---|---|---|

## 7. Checks that will prove it
- Parts: bbox / volume vs hand calculation, edit test, save + reopen
- Assemblies: solved = computed, interference list, counts
- Audit score before / after (`scripts/audit.py`)

## 8. Gates
- [ ] Sample part approved   - [ ] Sample sub-assembly approved   - [ ] Full model approved
