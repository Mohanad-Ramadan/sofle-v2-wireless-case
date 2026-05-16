"""All dimensions in mm. Single source of truth for the case geometry."""

# ---------- Heights (Z = 0 at case bottom) ----------
FLOOR_THICKNESS = 2.0
PCB_SEAT_Z      = 4.5
PLATE_SEAT_Z    = 9.1   # PCB_TOP_Z + 3.0 mm measured MX switch body clearance
MAIN_RIM_Z      = 14.0

PCB_TOP_Z       = 6.1   # PCB_SEAT_Z + 1.6 mm PCB thickness
PLATE_TOP_Z     = 10.7  # PLATE_SEAT_Z + 1.6 mm plate thickness

# Derived thicknesses — computed from the authoritative Z positions so that
# (TOP_Z - SEAT_Z == THICKNESS) holds exactly in floating-point arithmetic.
PCB_THICKNESS   = PCB_TOP_Z   - PCB_SEAT_Z    # ≈ 1.6 mm
PLATE_THICKNESS = PLATE_TOP_Z - PLATE_SEAT_Z  # = 1.5 mm

# ---------- Outer envelope ----------
OUTER_WIDTH     = 149.5
OUTER_DEPTH     = 121.5
WALL_THICKNESS  = 2.5
CORNER_RADIUS   = 3.5
TOP_CHAMFER     = 0.8

# ---------- Standoff geometry ----------
STANDOFF_OD_LOWER  = 5.5   # PCB-seat shoulder OD
STANDOFF_OD_UPPER  = 3.5   # passes through PCB Ø4.1 hole
STANDOFF_TAP_DIA   = 1.8   # M2 self-tap bore (sized for FDM tolerance)
STANDOFF_TAP_DEPTH = 4.0

# ---------- Clearances ----------
PCB_XY_CLEARANCE = 0.5
PCB_HOLE_DIA     = 4.1

# ---------- Optional perimeter PCB ledge (default off; see spec §3.4) ----------
PCB_LEDGE_ENABLED = False
PCB_LEDGE_WIDTH   = 1.0   # mm; ring width if enabled

# ---------- Cutouts (W = horizontal width along wall, H = vertical height) ----------
# USB-C slot in +Y wall: open-top (top edge punches past wall rim) so a single case
# STL fits both halves regardless of which MCU footprint is populated.
#   Z stack at MCU: main-PCB top 6.1, nice!nano PCB top 7.7, USB-C jack body 7.7→10.3.
#   Bottom Z 7.5 sits just below the jack lower lip; top punches past the rim.
#   USB_C_Y_DEPTH must reach the MCU's +Y edge (case Y ≈ 113.8) — there is ~2.5 mm of
#   solid case between the wall outer face (Y=116.5, USB_C_OUTER_Y) and the cavity edge,
#   so a 31 mm inward extrusion clears past the MCU into the empty cavity beyond.
USB_C_W = 9.0
USB_C_Z_RANGE: tuple[float, float] = (11, PCB_TOP_Z + 11.5)   # top = MCU_HILL_Z + 0.5; clears raised +Y wall
USB_C_Y_DEPTH = 31.0
USB_C_SIDE_BULGE = 1.5   # mm outward arc bulge at midpoint of each X-side

SLIDE_SWITCH_W     = 6.0
SLIDE_SWITCH_TOP_W = 14.0
SLIDE_SWITCH_Z_RANGE: tuple[float, float] = (10, MAIN_RIM_Z + 0.5)   # z_lo clears switch metal body top; z_hi punches past wall rim so slot is open
SLIDE_SWITCH_CORNER_R = 0.1   # fillet radius at slot-rim junction on outer wall face

# Spline tangent scalars passed to Spline(...) for the two side profiles.
# Each tuple is (start_scalar, end_scalar) following the spline's traversal direction.
#   Right spline traverses bottom → top: (bottom, top)
#   Left  (ramp) spline traverses top → bottom: (top, bottom)
# Larger scalar stretches the OCC interpolated tangent further → longer, more gradual
# arc with bigger outward sweep. The ramp's top scalar 44.1641 is empirically solved
# so the cutout's bb.min.Y lands exactly on Y=28.1806 — the case-Y of the tray
# cavity's min-X vertex (thumb-cluster innermost cavity wall). At that Y the ramp's
# outermost point fades into the cavity edge, hiding the slot's flare seam in print.
# Ramp spline now runs from z_hi down to PLATE_TOP_Z only (shortened); re-solve with
# binary search over slide_switch_cutout().bounding_box().min.Y against the cavity
# min-X vertex Y from tray._cavity_solid().vertices().
SLIDE_SWITCH_RAMP_TANGENT_SCALARS:  tuple[float, float] = (44.1641, 2.5)

# ---------- Component positions (PCB coords, mm) ----------
MCU_POS        = (10.27, -16.16)
SW_SLIDE_POS   = (2.945, -45.23)
SW_RESET_POS   = (7.72,  -45.35)
SW_ENCODER_POS = (9.47,  -65.95)
J_OLED_POS     = (5.22,  -33.69)

# ---------- PTH mounting holes (PCB coords, mm); from SofleKeyboard-PTH.drl T9 Ø4.1 ----------
MOUNTING_HOLES: tuple[tuple[float, float], ...] = (
    (14.07,  -80.26),
    (39.57,  -19.05),
    (39.57,  -56.96),
    (116.07, -25.66),
    (116.07, -63.96),
)

# ---------- PCB → case coordinate transform ----------
# PCB X range: -8.5 .. 135.0 (width 143.5); Y range: -110.5 .. 5.0 (depth 115.5).
# Case origin (0,0) is the case OUTER lower-left corner. PCB is centered in case.
PCB_X_MIN, PCB_X_MAX = -8.5, 135.0
PCB_Y_MIN, PCB_Y_MAX = -110.5, 5.0

PCB_OFFSET_X = (OUTER_WIDTH - (PCB_X_MAX - PCB_X_MIN)) / 2 - PCB_X_MIN
PCB_OFFSET_Y = (OUTER_DEPTH - (PCB_Y_MAX - PCB_Y_MIN)) / 2 - PCB_Y_MIN


# Outer wall face positions (polygon-derived; PCB top boundary at MCU X column = PCB Y=0)
USB_C_OUTER_Y = PCB_OFFSET_Y + WALL_THICKNESS + PCB_XY_CLEARANCE  # +Y outer face at MCU X = 116.5


def pcb_to_case(x: float, y: float) -> tuple[float, float]:
    """Translate a PCB-coordinate point into case (outer-rect) coordinates."""
    return (x + PCB_OFFSET_X, y + PCB_OFFSET_Y)


# ---------- Phantom (visual fit-check; default off) ----------
SHOW_PCB_PHANTOM    = True # True: adds PCB phantom to case.py __main__ viewer
SHOW_PLATE_PHANTOM  = True # True: adds switch plate phantom to case.py __main__ viewer
SHOW_SWITCH_PHANTOM = True # True: adds MX switch phantom to case.py __main__ viewer

# MCU vertical stack — structural heights that also drive the USB-C cutout design
MCU_PCB_TOP_Z    = 12    # nice!nano PCB top including socket height above main PCB
USB_C_BODY_TOP_Z = 18   # USB-C jack body top surface

# ---------- MCU wall cap on −X wall ----------
MCU_HILL_Z                              = PCB_TOP_Z + 11.0          # 17.1 mm — top of MCU + header legs
MCU_BODY_L                              = 33.0                       # MCU body length in Y (mm)
MCU_BODY_W                              = 18.0                       # MCU body width in X (mm)
MCU_HILL_DESCENT_SCALARS: tuple[float, float] = (1.5, 1.5)          # +Y wall spline descent tuning (larger = gentler curve)

# ---------- Integrated MCU hill covering −X and +Y walls at MCU corner ----------
# +X extent of the MCU hill on the +Y wall (case coords): MCU +X edge = MCU_POS + half width in PCB coords
MCU_HILL_PLUS_Y_REACH_X: float         = pcb_to_case(MCU_POS[0] + MCU_BODY_W / 2, 0)[0]  # ≈ 30.77 mm
# +Y wall linear ramp run (mm) from MCU +X edge down to MAIN_RIM_Z
MCU_HILL_PLUS_Y_RAMP_RUN: float        = 8.0
# L-corner XY mask bounds (case coords). Hill ring is kept where:
#   X ≤ MCU_HILL_NEG_X_INNER_BOUND_X (covers −X wall ring at MCU Y range)
#   Y ≥ MCU_HILL_PLUS_Y_INNER_BOUND_Y (covers +Y wall ring at MCU X column)
# Polygon at MCU column: outer −X face X=8.5, inner X=12.0; outer +Y face Y=116.5, inner Y=113.0.
MCU_HILL_NEG_X_INNER_BOUND_X: float    = 13.0
MCU_HILL_NEG_X_SOUTH_Y: float          = 75.0                       # hill −X strip south boundary (below spline's rim-Z crossing)
MCU_HILL_PLUS_Y_INNER_BOUND_Y: float   = OUTER_DEPTH - 9.0   # = 112.5

# ---------- S-curve ramp on −X wall ----------
S_CURVE_RAMP_Y_START: float             = 31.0                      # −Y ramp start Y in case coords

S_CURVE_RAMP_MINUS_Y_SCALARS: tuple[float, float] = (2.0, 0.3)     # −Y spline tangent scalars (start, end)
S_CURVE_RAMP_PLUS_Y_SCALARS: tuple[float, float] = (1.0, 1.0)      # +Y spline tangent scalars (start, end)