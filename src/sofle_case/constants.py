"""All dimensions in mm. Single source of truth for the case geometry.

See docs/superpowers/specs/2026-04-25-sofle-v2-wireless-case-design.md.
"""

# ---------- Heights (Z = 0 at case bottom) ----------
FLOOR_THICKNESS = 2.0
PCB_SEAT_Z      = 4.5
PLATE_SEAT_Z    = 6.5
MAIN_RIM_Z      = 10.0
MCU_COVER_Z     = 17.0

PCB_TOP_Z       = 6.1   # PCB_SEAT_Z + 1.6 mm PCB thickness
PLATE_TOP_Z     = 8.0   # PLATE_SEAT_Z + 1.5 mm plate thickness

# Derived thicknesses — computed from the authoritative Z positions so that
# (TOP_Z - SEAT_Z == THICKNESS) holds exactly in floating-point arithmetic.
PCB_THICKNESS   = PCB_TOP_Z   - PCB_SEAT_Z    # ≈ 1.6 mm
PLATE_THICKNESS = PLATE_TOP_Z - PLATE_SEAT_Z  # = 1.5 mm

# ---------- Outer envelope ----------
OUTER_WIDTH     = 162.0
OUTER_DEPTH     = 131.0
WALL_THICKNESS  = 3.0
CORNER_RADIUS   = 3.5
TOP_CHAMFER     = 1.5

# ---------- Standoff geometry ----------
STANDOFF_OD_LOWER  = 5.5   # PCB-seat shoulder OD
STANDOFF_OD_UPPER  = 3.5   # passes through PCB Ø4.1 hole
STANDOFF_TAP_DIA   = 1.6   # M2 self-tap bore
STANDOFF_TAP_DEPTH = 4.0

# ---------- Clearances ----------
PCB_XY_CLEARANCE = 0.5
PCB_HOLE_DIA     = 4.1

# ---------- Optional perimeter PCB ledge (default off; see spec §3.4) ----------
PCB_LEDGE_ENABLED = False
PCB_LEDGE_WIDTH   = 1.0   # mm; ring width if enabled

# ---------- MCU cover ----------
MCU_COVER_W = 23.0
MCU_COVER_D = 40.0

# ---------- Cutouts (W = horizontal width along wall, H = vertical height) ----------
USB_C_W, USB_C_H = 9.0, 4.0
USB_C_Z_CENTER   = 14.0

SLIDE_SWITCH_W, SLIDE_SWITCH_H = 6.0, 3.5
SLIDE_SWITCH_Z_RANGE: tuple[float, float] = (1.0, 4.5)

RESET_PIN_DIA  = 2.0
RESET_Z_CENTER = 7.5

SLIDE_SWITCH_RECESS_W     = 10.0
SLIDE_SWITCH_RECESS_D     = 5.0
SLIDE_SWITCH_RECESS_DEPTH = 1.5

# ---------- Component positions (PCB coords, mm) ----------
MCU_POS        = (10.27, -16.16)
SW_SLIDE_POS   = (2.945, -43.23)
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


def pcb_to_case(x: float, y: float) -> tuple[float, float]:
    """Translate a PCB-coordinate point into case (outer-rect) coordinates."""
    return (x + PCB_OFFSET_X, y + PCB_OFFSET_Y)
