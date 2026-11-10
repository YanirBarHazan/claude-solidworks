# Dialogue with the user: brief, project card, gates, cost

The most expensive rules of the first field project (never rebuild a part to change a value, mates inside
sub-assemblies, configurations by suppression, no pictures) were learned in the middle of the work. Ask for them
at the start. Talk in the user's language; keep part and parameter names exactly as the user writes them.

## 1. Design brief - ONE round, before any CAD
Ask all of it in one message; skip what the user already said. Give your recommendation with each choice.

**A. Outcome**
- What is being made, for whom, and what "done" means (files only? drawings? BOM? print files? PDM check-in?).
- Which existing files must be used as they are (purchased parts, company library).

**B. Who changes it later, and how** - this decides how the model is built
- By values (a parameter file + one command), by hand in SolidWorks, or both?
- Their SolidWorks level; one engineer or a team; local folder, shared drive or PDM.
- If people will edit by hand: the model must explain itself in the tree (mates, named references, a skeleton),
  and the scripts must never overwrite hand work silently (`hand_edits.md`).

**C. What is expected to change**
- Every expected change becomes a parameter; say which changes are cheap (a part value) and which are expensive
  (layout). On/off options -> configurations by suppression. Size variants -> files or value sets.
- "Move this one item a bit" requests: ask now whether single items need their own offsets.

**D. Standards**
- SolidWorks version that must open the files, and other versions installed (version guard).
- Templates, units, materials (real SolidWorks materials, not text), part numbering, custom properties the PDM /
  title block needs, colours.

**E. Engineering intake** - `intake.md` (datums, connections, topology, allowed overlaps, expected counts).

**F. How to work together**
- Approval gates (section 3), how often to report, pictures or numbers only.
- Sensitivity to credits and time: say that long SolidWorks runs cost time but almost no credits.

## 2. Project card - one page, approved before building
Write `PROJECT_CARD.md` in the project (template: `templates/PROJECT_CARD.md`): goal, who edits and how, model
structure (what is the skeleton, what is mated, what is patterned, what is a file vs a configuration), decisions,
assumptions, open questions, checks that will prove it.
- Every decision has a status and a date: `CONFIRMED` (the user decided), `ASSUMED` (your default, listed back to
  the user), `OPEN` (blocks the work that depends on it - ask, never guess).
- A new session reads the card first and does not ask again.

## 3. Gates - stop for approval
One sample part (built, verified, edit-tested) -> one sub-assembly -> the whole model. At each gate give numbers
(and a picture only if the user wants pictures). Do not continue past a gate on your own.

## 4. Before any long task
Say what will run, the expected wall time (from a measurement, or say it is a guess) and that it runs in the
background. After it: one line with the result and the numbers. Never set a timeout shorter than a measured run on
a step that saves only at the end; save after each unit.

## 5. Missing or conflicting information
- One focused question with your recommendation; never invent a dimension. Say which value is missing and what
  it blocks.
- Rule conflicts found by the Python checks (clearances, counts) go to the user with the numbers and 2-3 options.
- After two failed attempts at the same step: stop and report what is known. Never state a cause without evidence.

## 6. Reporting style
Short status lines; numbers, not adjectives; failures explained plainly (what broke, what caught it, what changed).
Report what was NOT verified. Log every SolidWorks / API error in the project's notes file in the same turn.

## 7. Keep sessions short (cost)
A long conversation re-reads itself every turn. At the end of a phase write a hand-over file (state, decisions,
next steps, how to verify) + keep `PROJECT_CARD.md` current, and continue in a new session that reads those two
files. Anything the user will repeat (update after a value change, cleanup, export) becomes a double-click tool
that runs without Claude.

## 8. Working with the user - field rules (from SKILL.md v1)
- **Intake before modeling** (each item cost a reprint once): a labelled photo of every board *from the
  side the user will look at* (directions given from the back mirror the whole design); every connector
  that will be used, with its plug and cable exit; how each loose component is held in all six
  directions (a part that can slide out of a window needs a stop); the fasteners/inserts the user has.
- **Model every interface as a keep-out body from day one** (plugs + wire bend room, cables, fingers on
  buttons) so the interference check covers it - an "open question" in a summary is not a check.
- **Tolerance-stack each joint along its axis**: preloads (crush ribs, detents) push parts apart, so a
  snap's play must exceed them, or the hook never reaches its groove.
- **Stop after two failed attempts at the same step** and tell the user what is known; never guess a cause
  to the user ("the screen is locked") without evidence.
- **Spend fewer credits:** never print long logs or tracebacks to the conversation (one summary line per
  item, details in `logs/`, last 10 lines only on failure); never `ls` a CAD folder (count instead); value-only changes -> `set_param`/update mode or the user's own script, never a
  rebuild; scripts print one line per result and log details to a file (read only `tail`/`grep`);
  smoke-test a new SolidWorks session first; ask all intake questions in one message; keep status
  messages short.
- Long builds: run in the background (`python -u`), give a one-line status, keep working on the next script.
- Explain failures plainly ("each run starts clean on purpose; this one hit an API quirk, fixed once in
  the library") — users notice repeated restarts and open documents.
- Close only documents you created; restore any preference you change; never touch files outside
  the project folder.
- Deliver: SolidWorks files, a `build_all.py` that rebuilds everything in order, print files, a short
  assembly sequence, and the list of `[A]` assumptions still to measure.
