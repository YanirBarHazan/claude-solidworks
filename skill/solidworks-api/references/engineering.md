# Engineering knowledge for printed enclosures & mechanisms

Read during planning. Numbers are starting points for PLA on a Bambu A1 (0.4 nozzle, 0.2 layer);
confirm with test coupons, then keep them in the parameter file's FIT group.

## Fits and walls (FDM, PLA)
| Item | Value | Note |
|---|---|---|
| Outer wall | 2.4 | 6 lines; stiff, no warping |
| Face plate printed face-down | 2.0 | good cosmetic face |
| Minimum wall | 1.2 | thinner breaks |
| Wall in front of a 24 GHz radar | 1.5 | plastic only, no paint/metal, keep 0.3 air gap |
| Part in a pocket | 0.2 / side | |
| Lip sliding in a wall | 0.15 / side | |
| PCB edge to wall | 0.3 / side | |
| Locating pin in PCB hole | hole − 0.4 | Ø3.2 hole → Ø2.8 pin |
| Rotating knuckle on pin | +0.3 diametral | |
| Pin pressed into fixed knuckles | −0.1 diametral | |
| Crush ribs | 3 × Ø1 per post, 0.2 interference | absorb the tolerance stack of a clamp |
| Cable plug opening | overmold + 0.2 / side | measure the user's cable overmold |
| Heat insert M3 | Ø4.0 × 5.7 (check the insert) | |

## Snap fits
- Cantilever strain ε = 1.5·t·y/L² (t thickness, y undercut, L length). PLA: ≤1 % for repeated use,
  ~2 % one-off. Example: t 1.6, y 0.6, L 12 → 1.0 %.
- Lead-in ramp 30° (height = y/tan30), flat land ~0.6, retaining face 90° (permanent) or 45°
  (releasable). Groove: depth y + 0.2, axial play 0.1, 0.3 above the tip.
- Printed vertical tongues bend across layers (weakest direction) — keep strain low, add a root
  fillet, or make the flexing member lie in the print plane.
- Hidden snaps: grooves inside the wall; give the bottom ones through-windows so a small screwdriver
  can release them.
- Hook flex direction must have free space (check against PCBs/cables near the lip).

## Clamping a PCB without screws (sandwich)
Front standoffs (to the PCB front face, exact height) + pins through the PCB holes; rear posts stop
0.3 short with crush ribs; the pin tip enters a clearance hole in the rear post. The glass/display
carries no load (0.2 gap to the front wall). Posts must clear the components on the back of the board.

## Detent hinge (adjustable stand)
- Fixed knuckles + rotating wheel with notches + a flexing arm with a bump.
  Strain of the arm = 1.5·t·(notch depth + preload)/L². Bump in a notch preloads ~0.1.
- Ridge between notches = 2·r_n·sin(step/2) − notch width; keep > 0.4 mm (grow the wheel radius,
  not the notch).
- Make the leg a constant profile (same width as the wheel) and print it on its side: notches crisp,
  hole round, no support. A wheel lying on the bed puts the notches in its bottom overhang.
- Stand geometry (device on its bottom-BACK edge + leg tip corner): with hinge height h above the
  bottom edge, axis offset d behind the back, leg length L, opening a, plate offset f:
  y = h - L*cos(a) - f*sin(a) (up the back), z = d + L*sin(a) - f*cos(a) (behind the back).
  atan(z/y) is the angle between the BACK and the DESK; screen tilt from vertical = 90 deg - atan(z/y).
  (Mixing these up once produced a stand that would have laid the device almost flat.) A desk-display
  range of 15-35 deg needs z/y = 1.4-3.7: a low hinge (about half height), leg about the hinge height,
  openings ~30-80 deg. Solve the opening per target tilt and put the notches there (non-uniform is fine).
- A front-heavy device cannot lean on a leg below atan(CoM offset in front of the back / CoM height)
  (~12 deg here): below that it stands upright on its own base - make "folded" an upright position.
- Verify with the real centre of mass: margins from the CoM to both contacts, and the push/pull at the
  top that tips it (push_back = W*(L - s)/h_top, pull_fwd = W*s/h_top).
- Stability: the centre of mass must stay well inside bottom-edge-to-leg-tip; check the most upright
  position (it tips forward first).

## Light, sensors, speakers in a front panel
- LED strip behind a diffuser: a bar through the wall (flush) + a flange behind it; LED tops rest on
  the flange (diffusion + fixed position); white/natural PLA ~2.8 mm.
- Radar (HLK-LD2410C etc.): antenna face toward the user, behind thin plastic, outside the display's
  metal footprint; Dupont headers add ~14 mm + bend → often sets the enclosure depth.
- A module whose own face is a button (M5Stack Atom): window = module + 0.2/side, face flush; support
  its back from the rear shell (0.2 gap); leave room for its plugs on the connector side.

## Measurement sanity checks (useful standards)
- 5" 800×480 TFT: outline 120.7 × 75.8, active area 108.0 × 64.8, visible area ≈ 110.8 × 67.6.
- USB-C receptacle 8.94 × 3.16 × 7.35; plug shell 8.25 × 2.4 × 6.65 (overmold: measure).
- WS2812B 5050 LED: 5 × 5 × 1.55; ~60 mA at full white → limit brightness in firmware.
- Dupont female housing: 2.54 pitch, ~14 mm long. JST-PH 2.0 / SH 1.0 / GH 1.25: plug + bend ~8–10 mm.
- Board hole given as "edge-to-edge" → centre = edge + Ø/2; check pitch = width − 2·centre offset.
- Typical ESP32 5" HMI board (Guition JC8048W550): 137 × 84 × 1.5, holes Ø3.2 at 3.5 from edges.

## Mechanism / Motion checks
- Before a Motion study, check the Motion add-in exists in the running install (`cmotionsw.dll`).
- Compute the expected answer by hand first (e.g. a pinned chain of N rigid segments with joint play ±φ
  sags at most like an arc: mid-span sag ≈ ((N² − 1)/8)·L·φ for odd N; 9 × 1000 mm, φ = 2.1/150 → 140 mm),
  then compare the simulation to it.
- Joint free play of a spigot (male in female tube): φ ≈ diametral clearance / insertion length.

## Process that avoided rework
1. Cross-check measurements → standard parts → list what's missing.
2. Plan + drawings (front view to scale, section through the joints, detail of each joint with its
   numbers) → user approval.
3. Reference models of purchased parts + layout assembly → interference check.
4. Test coupons for every uncertain fit → print → update FIT parameters.
5. Parts one by one, each fully verified; then the full assembly swept through every mechanism position.
6. Overhang check + slicer check per printed part; redesign rather than add supports where precision matters.
