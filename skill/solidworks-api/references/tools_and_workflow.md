# Other tools that helped (and how)

## Reading component listings (AliExpress etc.) — built-in browser
- `get_page_text` often returns only the shell; product data is in images.
- Collect gallery/description images with JS: regex the page HTML for
  `https?://[a-z0-9.-]*(alicdn|aliexpress-media)\.com/kf/[A-Za-z0-9_]+\.(jpg|png)`; skip tiny icons.
- Open each image URL and screenshot; dimension drawings need `zoom` on the dimension text.
  Low-res drawings: read what you can, label it "to confirm", and cross-check with standards.
- Description iframes may hit a captcha — don't try to bypass; ask the user for the numbers.

## Drawings for approval — inline SVG widget (visualize)
- Front view to scale (e.g. 3 px/mm), a schematic section through the joints, and a detail panel per
  joint with its numbers. Mark unknowns as "? (needed)".
- Hebrew labels: `direction="rtl"` with `text-anchor="start"` anchored at the right end of the label
  column. Keep the user's language in drawings too.

## Looking at the user's screen — computer-use
- Request access to "SOLIDWORKS 2025"; the window may be on another monitor (`switch_display`).
- `open_application` on a running SolidWorks can start a *second* instance — prefer COM.
- Screenshots are expensive in tokens; use them only when COM can't tell you (modal dialogs).

## Old STL from a previous attempt
- Parse binary STL (numpy) → bbox, volume, coordinate levels per axis; render views with matplotlib
  (Poly3DCollection) to understand it; slice with plane intersections to measure openings and walls.

## Bambu Studio
- User's printer: `%APPDATA%\BambuStudio\BambuStudio.conf` → "machine".
- `bambu_project.py` builds and slices a project per plate; open it with
  `bambu-studio.exe <file.3mf>` (opens a new window when single_instance is false).
- Keep different filament colours on different plates/projects.

## Token economy
- One Python script per part (dozens of API calls in one run, compact printed checks) is far cheaper
  than one tool round-trip per feature.
- Print only verification lines (`Select-String` the important ones); long builds in the background.
- Grep the generated gen_py module for signatures instead of reading it.
- Avoid screenshots/images unless needed; read STL/part data numerically.
