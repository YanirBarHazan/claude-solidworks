"""All dimensions (mm). Source of each value is noted: [M]=measured by Yanir, [D]=datasheet/listing,
[C]=calculated from other values, [A]=assumption - must be verified before final print.

Component frames used by the reference models:
  X right, Y up, Z toward the viewer (front). Display origin = PCB centre, PCB front face at Z=0.
"""

DISPLAY = dict(
    PCB_W=137.0,        # [M] [D] Guition 5" ESP32-S3 board
    PCB_H=84.0,         # [M] [D]
    PCB_T=1.5,          # [M]
    HOLE_D=3.2,         # [D] R1.6 on drawing; measured ~3 [M]
    HOLE_EDGE=3.5,      # [C] centre from edge: 2 mm edge-to-hole [M] + D/2; pitch 130 x 77 matches 127 min-min [M]
    GLASS_W=120.7,      # [D] standard 5" 800x480 panel outline; measured ~121 "a bit less" [M]
    GLASS_H=75.8,       # [D] measured ~76.5 "a bit less" [M]
    GLASS_T=5.0,        # [M] T1: glass face to PCB front face
    GLASS_TOP=4.35,     # [M] PCB top edge to glass top edge (bottom margin = 3.85 [C], to confirm)
    VA_SIDE=5.5,        # [M] black border left/right ("a bit more")
    VA_TOP=2.5,         # [M] black border top
    VA_BOT=6.0,         # [M] black border bottom
    BACK_T=5.0,         # [M] T2: PCB back face to tallest component
    BACK_MARGIN=8.0,    # [A] keep-out envelope for back components, inset from PCB edges
    USBC_W=8.94,        # [D] receptacle width (measured 9 [M])
    USBC_H=3.16,        # [D] receptacle height (measured "~3, a bit more" [M])
    USBC_L=7.35,        # [D] receptacle depth into the board
    USBC_TOP=37.32,     # [M] PCB top edge to receptacle edge; flush with the PCB edge
    USB_SIDE=-1,        # [M] receptacle on the LEFT edge seen from the screen side (+1 = right)
)

LED = dict(
    LED_PCB_W=50.3,     # [M]
    LED_PCB_H=10.0,     # [M]
    LED_PCB_T=1.6,      # [C] 3.15 total - 1.55 LED
    LED_SIZE=5.0,       # [D] WS2812B 5050 package
    LED_T=1.55,         # [D]
    LED_N=8,
    LED_SPAN=48.3,      # [M] outer edge to outer edge of end LEDs (centre-centre would overhang the PCB) -> pitch 6.19 [C]
    LED_ROW_TOP=3.9,    # [A] board top edge to LED top edge (LEDs must clear the holes)
    LED_HOLE_D=2.7,     # [C] from 11.2 + 22.5 + 11.2 + 2D = 50.3, assuming symmetric holes
    LED_HOLE_GAP=22.5,  # [M] hole edge to hole edge
    LED_HOLE_TOP=1.0,   # [M] board top edge to hole edge
)

RADAR = dict(
    RAD_W=22.0,         # [M] HLK-LD2410C
    RAD_H=16.0,         # [M]
    RAD_T=1.7,          # [M]
    RAD_PIN_TOTAL=11.2, # [M] board front to pin tips
    RAD_HDR_L=12.7,     # [D] 5 pins x 2.54
    RAD_HDR_W=2.54,     # [D]
    RAD_HDR_T=2.5,      # [D] header plastic
    RAD_HDR_EDGE=1.5,   # [A] long (top) edge to header centreline
    DUP_L=14.0,         # [D] Dupont female housing length
    DUP_BEND=6.0,       # [A] cable exit + bend allowance
)

ATOM = dict(
    ATOM_W=24.0,        # [D] M5Stack Atom Echo 24 x 24 x 17
    ATOM_H=24.0,        # [D]
    ATOM_D=17.0,        # [D]
)

PLUG = dict(
    PLUG_W=10.5,        # [M] USB-C cable overmold
    PLUG_T=6.5,         # [M]
    PLUG_L=25.0,        # [A] overmold length (not critical, keep-out only)
    PLUG_TIP_W=8.25,    # [D] USB-C plug shell
    PLUG_TIP_T=2.4,     # [D]
    PLUG_TIP_L=6.65,    # [D]
)

# ---- enclosure construction & printer fits (PLA, Bambu A1, 0.4 nozzle) ----
FIT = dict(
    BEZ_T=2.0,          # front wall thickness
    WALL_T=2.4,         # side walls (6 lines)
    LIP_T=1.65,         # front-frame lip that slides inside the back body
    LIP_CLR=0.1,        # lip to wall clearance, per side (0.15 rattled a little - snug now)
    PCB_CLR=0.3,        # PCB edge to wall, per side
    GLASS_GAP=0.2,      # glass face to front wall inner face
    PIN_CLR=0.2,        # radial clearance, locating pin in PCB hole (3.2 -> 2.8)
    STAND_D=6.0,        # standoff diameter around the PCB holes
    PLUG_CLR=0.2,       # USB-C overmold to opening, per side
    WIN_MARGIN=0.3,     # window edge inside the visible area, per side
    SNAP_L=12.0,        # snap tongue length (strain = 1.5*LIP_T*0.7/SNAP_L^2 = 1.2 % at the 0.7 deflection)
    SNAP_W=8.0,         # snap tongue width
    SLIT_W=1.0,         # slit beside the tongue
    SNAP_U=0.8,         # undercut (0.6 held but too weak) - engagement in the groove = SNAP_U - LIP_CLR = 0.7
    RAMP_H=1.39,        # lead-in ramp height = SNAP_U / tan(30 deg)
    SNAP_LAND=0.6,      # flat land at the hook tip
    GROOVE_CLR=0.2,     # extra groove depth behind the hook
    GROOVE_PLAY=0.35,   # hook reach past the groove edge: > CRUSH (PCB ribs push the frame out) + bridge sag (0.1 did not reach)
    GROOVE_TOP=0.3,     # groove clearance above the hook tip
    HINGE_CLR=0.3,      # pin to rotating knuckle, diametral
    PIN_PRESS=0.05,     # pin to fixed knuckle, diametral interference (0.1 printed too tight - coupon C)
)

# ---- enclosure layout (mm) ----
ENCL = dict(
    CHIN_GAP=0.8,       # PCB bottom edge to Atom top
    ATOM_CABLE=13.0,    # [A] room below the Atom for its USB-C / Grove plugs (shrink once its connector layout is measured)
    ATOM_X=50.0,        # Atom centre X (right side of the chin)
    ATOM_CLR=0.2,       # Atom in its front window, per side
    ATOM_RIB_D=8.0,     # depth of the side ribs that cradle the Atom
    ATOM_LIP=0.6,       # front stop: rim over the Atom face edge, per side (keeps it from falling out)
    ATOM_LIP_T=0.6,     # rim thickness (3 layers, printed on the bed); the Atom face sits this far back
    ATOM_USB_DX=0.0,    # [A] Atom USB-C centre, X offset from Atom centre (on its bottom face)
    ATOM_USB_FROM_FACE=8.5,  # [A] Atom USB-C centre, distance behind the Atom front face
    ATOM_OPEN_W=13.0,   # [M] Atom cable opening width along X (Yanir: room for a USB or a Grove power lead)
    RADAR_X=-50.0,      # radar centre X (left side of the chin), same height as the Atom
    RAD_CLR=0.2,        # radar in its pocket, per side
    RAD_WIN_T=1.5,      # front wall thickness in front of the radar antenna
    RAD_GAP=0.3,        # antenna face to that wall
    RAD_RIB_H=1.5,      # pocket rib height
    RIB_T=1.2,          # rib thickness
    LED_Y=-48.5,        # LED stick centre Y (top edge 1.5 below the PCB)
    DIFF_W=48.2,        # diffuser bar visible width (slot 48.5 [M] Yanir, after print)
    DIFF_H=4.7,         # diffuser bar visible height (slot 5.0 [M] Yanir, grown downward)
    DIFF_TOP=1.9,       # bar top edge above the LED row centre (kept from the 3.8 bar)
    DIFF_CLR=0.15,      # diffuser bar in its slot, per side
    DIFF_FL_T=0.8,      # diffuser flange behind the front wall (LED tops rest on it)
    DIFF_FL_EXT=2.0,    # flange beyond the bar, left/right
    DIFF_FL_UP=0.6,     # flange above the bar (limited by the LED locating pins)
    DIFF_FL_DN=3.0,     # flange below the bar
    LEDPIN_EXTRA=1.0,   # LED locating pins beyond the LED board
    LIP_IN_R=0.5,       # inner corner radius of the lip (<= 1.0 so the PCB corners clear it)
    LIP_H=14.0,         # lip depth behind the front wall
    PIN_EXTRA=1.0,      # PCB locating pins beyond the PCB back
    SNAP_X_TOP=40.0,    # snap tongues on the top lip at +/- this X
    SNAP_X_BOT=30.0,    # snap tongues on the bottom lip at +/- this X
    BACK_GAP=0.5,       # deepest component (radar plug) to back wall
    # plugs in the PCB edge connectors (seen from the screen side; positions from the photo, +/-2 [A])
    P2_X=-4.2,          # P2 radar data (IO11/IO12), bottom edge, centre X
    P4_X=-35.8,         # P4 LEDs (3.3V/GND/IO17), bottom edge, centre X
    P1_Y=-16.0,         # P1 radar 5V/GND, USB edge, centre Y
    CONN_W=11.0,        # [A] plug + wires width along the edge
    CONN_ON_PCB=5.0,    # [A] plug length on the board, from its edge
    CONN_H=4.5,         # [A] plug height behind the board
    WIRE_ROOM=2.0,      # [M] wires bend back within this beyond the board edge
    P1_NW=13.5,         # lip notch for the P1 wires (USB-side lip)
    CBL_FRONT=0.5,      # notch reaches this far in front of the PCB back face
    SHELL_BACK_T=2.0,   # back wall thickness
)

# ---- back body & stand ----
SHELL = dict(
    POST_GAP=0.3,       # PCB back face to clamp-post top
    CRUSH=0.2,          # crush-rib interference on the PCB back
    CRUSH_D=1.0,        # crush rib diameter (3 per post)
    POST_HOLE_CLR=0.3,  # radial clearance of the locating-pin tip inside the post
    ATOM_BACK_GAP=0.2,  # Atom back face to its support post
    ATOM_POST_D=8.0,
    VENT_W=3.0,         # back vents
    VENT_L=50.0,
    VENT_CY=5.0,
    VENT_X1=22.0, VENT_X2=32.0, VENT_X3=42.0,
    HINGE_Y=-14.0,      # stand hinge axis height on the back (70 above the bottom edge; see step7_stability)
    HB_W=36.0,          # hinge block plate
    HB_L=30.0,          # longer plate for the 16 mm detent arm
    HB_T=3.0,
    HB_SCREW_X=11.5,    # M3 screws from inside the back body into heat inserts in the hinge knuckles
    SCREW_HOLE_D=3.4,
    INSERT_D=4.0,       # [A] M3 heat insert hole (check the insert you have)
    INSERT_L=5.7,
)
STAND = dict(
    K_W=6.0, K_R=6.0, KN_GAP=0.3, MID_W=16.4,          # knuckles (as tested in coupon C)
    R_W=12.0, NOTCH_D=0.9, NOTCH_R=0.9, DET_PRE=0.1,   # detent wheel (bigger teeth: holding torque ~0.13 N*m, SF ~4)
    BUMP_H=1.3, BUMP_R=0.9, ARM_W=12.0, ARM_L=16.0, ARM_TIP=1.5, ARM_T=1.6, SLOT_W=1.0,   # k ~10.5 N/mm, strain 0.94 %
    PIN_D=5.0,
    N_NOTCH=6, NOTCH_STEP=10.0,                        # N_NOTCH = len(STAND_POSITIONS); STEP unused
    LEG_W=16.4, LEG_T=5.0, LEG_L=64.0, LEG_NECK_GAP=3.0, LEG_START=7.5,
)

# leg opening angles (deg) of the detent notches: 0 = folded (device stands upright on its base),
# then screen tilts of 15/20/25/30/35 deg from vertical (solved in step7_stability.py, min 11 deg apart)
STAND_POSITIONS = [0.0, 29.9, 46.1, 59.0, 70.9, 82.3]
