"""All dimensions in mm. Single source of truth for the case geometry."""

# ---------- Heights (Z = 0 at case bottom) ----------
# Floor is 1.8 mm thicker than the original 2.0 mm (BATTERY_POCKET_DEPTH) so a
# battery pocket can be recessed into it while leaving the original 2.0 mm of
# solid material beneath the pocket. Every Z above the floor is shifted up by
# the same 1.8 mm so all existing clearances (PCB seat, plate seat, rim) are
# unchanged relative to each other — only the floor gained thickness.
FLOOR_THICKNESS = 3.8
PCB_SEAT_Z      = 6.3
PLATE_SEAT_Z    = 10.9  # PCB_TOP_Z + 3.0 mm measured MX switch body clearance

PCB_TOP_Z       = 7.9   # PCB_SEAT_Z + 1.6 mm PCB thickness
PLATE_TOP_Z     = 12.5  # PLATE_SEAT_Z + 1.6 mm plate thickness

# Minimal short case: perimeter walls end flush with the plate's top surface —
# no proud lip above the plate. The MCU hill still rises above this (excluded).
MAIN_RIM_Z      = PLATE_TOP_Z  # 12.5

# Derived thicknesses — computed from the authoritative Z positions so that
# (TOP_Z - SEAT_Z == THICKNESS) holds exactly in floating-point arithmetic.
PCB_THICKNESS   = PCB_TOP_Z   - PCB_SEAT_Z    # ≈ 1.6 mm
PLATE_THICKNESS = PLATE_TOP_Z - PLATE_SEAT_Z  # = 1.5 mm

# ---------- Outer envelope ----------
# OUTER_WIDTH / OUTER_DEPTH are DERIVED from the PCB span + wall + clearance
# (see the PCB transform section below) so the footprint always tracks
# WALL_THICKNESS — thicken the wall and the envelope grows outward automatically
# while the PCB stays centred.
WALL_THICKNESS  = 4.75  # slim wall; grows the footprint outward (was 7.5)
# NOTE: CORNER_RADIUS is unused/dead — the visible outer corner radius is the
# Kind.ARC offset in tray._outer_extruded (= WALL_THICKNESS + PCB_XY_CLEARANCE),
# so the corner tracks the wall (≈5.25 at WALL=4.75). Kept only for reference.
CORNER_RADIUS   = 3.5
TOP_CHAMFER     = 0.8
BOTTOM_CHAMFER  = 0.5   # 45° counter-chamfer on outer bottom edge (elephant-foot pre-compensation)

# Outer-top bevel on the thick wall: a 45° chamfer that takes the outer top edge
# down toward the ground, so the chunky wall doesn't read as a hard block. Only
# the OUTER perimeter edge is bevelled — the inner cavity rim stays sharp (flush
# with the switch plate). 1.5 mm eats ~20% of the top wall thickness while leaving
# a 6.0 mm solid base. (OCC rejects an asymmetric chamfer on this edge set, so a
# clean symmetric 45° is used — the horizontal and vertical legs are equal.)
OUTER_TOP_CHAMFER = 1.9   # mm, 45° outer-top bevel leg (~40% of WALL_THICKNESS)

# ---------- Top cover (sandwich lid over the switch plate) ----------
# A thin printed layer the shape of the switch plate, sitting on the plate top
# (Z = MAIN_RIM_Z) and held by the same standoffs via taller M2 screws. Each
# 14 mm plate cutout is grown to a ~16.5 mm window so the switch's 15.6 mm top
# housing pokes through and the cover seats flat on the plate. Keycaps float
# entirely above it — skirt at full press ~14.0 mm > cover top 13.5 mm — so 1.0 mm
# is safe (1.5 mm would just kiss the skirt on a hard edge press). The plate's
# own inner notch leaves the MCU/OLED/slide/JST bay open for free.
MX_TOP_HOUSING_W        = 15.6   # mm; widest part of a Cherry MX switch (rests on plate) — drives the window size
COVER_THICKNESS         = 1.0    # mm; lid thickness, top at MAIN_RIM_Z + 1.0 = 13.5
COVER_WINDOW_OFFSET     = 1.25   # mm; grow each 14 mm plate cutout → 16.5 mm window (0.45 mm/side over the 15.6 housing)
COVER_SCREW_CLEARANCE_DIA = 2.4  # mm; M2 screw shaft clearance through the cover
# The plate-outline membrane sits ~0.3–0.7 mm inside the inner cavity wall, so on
# its own it floats free (a separate solid) inside the TOP part. Grow the membrane
# outline outward by this margin so it bites into the upper-wall material and fuses
# into one solid with the TOP walls. The bay notch shrinks by the same amount but
# stays wide open (the MCU/OLED/JST bay is ~20 mm across). Real overlap into wall
# material is used (not a coincident-face touch) because OCC's boolean union is
# unreliable on merely-coincident faces.
COVER_FUSE_MARGIN       = 1.0    # mm; membrane→upper-wall fusion overlap in the TOP part

# ---------- Sandwich clamshell split (TOP / BOTTOM parts) ----------
# A single planar seam halves the shell into two printable parts screwed together
# through the standoffs. Total height rises to COVER_TOP_Z because the TOP part's
# rim carries the membrane ceiling above the 12.5 plate reference.
SEAM_Z       = MAIN_RIM_Z / 2            # 6.25 mm; the horizontal split plane
COVER_TOP_Z  = MAIN_RIM_Z + COVER_THICKNESS  # 13.5 mm; TOP part rim (membrane top)

# ---------- Encoder plateau (TOP part, around EC11 rotary encoder) ----------
# The EC11 body is a ~12 mm box that mounts through the plate's encoder cutout
# (~12.7 mm) and protrudes ~2 mm above the plate top. On the sandwich TOP part a
# single-body PLATEAU caps it: one low mound, hollow inside to clear the box, with
# a closed roof and a plain shaft hole. The plateau leaves the cover tangentially
# (concave ogee foot) and rounds over at the top edge — no hard step, no second
# tier. The box is hidden; the bushing + 6 mm shaft exit through the shaft hole.
ENCODER_BODY_PROUD     = 2.0   # mm; EC11 box top above the plate (measured)
ENCODER_BODY_TOP_Z     = PLATE_TOP_Z + ENCODER_BODY_PROUD   # 14.5; box top (cavity must clear this)
ENCODER_SHELL_WALL     = 1.5   # mm; plateau side-wall thickness (thin → smaller footprint)
ENCODER_SHELL_ROOF     = 1.5   # mm; closed top-face thickness
ENCODER_SHELL_CAVITY_CLEAR = 0.4  # mm/side; cavity grows past the window so the ring
                                  # overlaps solid cover material (robust fusion)
ENCODER_SHAFT_HOLE_DIA = 7.5   # mm; shaft hole: clears the 6 mm shaft + 7 mm bushing
ENCODER_PLATEAU_H      = 4.5   # mm; plateau height above the cover surface
ENCODER_SHELL_TOP_Z    = COVER_TOP_Z + ENCODER_PLATEAU_H            # 18.0; plateau top
ENCODER_CAVITY_TOP_Z   = ENCODER_SHELL_TOP_Z - ENCODER_SHELL_ROOF   # 16.5; roof underside (clears box)
# Tangent blends so the plateau reads as a mound, not a box:
ENCODER_BEZEL_FOOT_R   = 1.5   # mm; concave foot radius (plateau → cover)
ENCODER_BEZEL_TOP_R    = 1.5   # mm; convex round-over of the plateau top edge
# NB: PLATEAU_H MUST exceed FOOT_R + TOP_R or the two rolls collide and OCC aborts.

# ---------- Standoff geometry ----------
STANDOFF_OD_LOWER  = 5.5   # PCB-seat shoulder OD
STANDOFF_OD_UPPER  = 3.9   # passes through PCB Ø4.1 hole (~0.2 mm clearance); widened from 3.5 to thicken the M2 self-tap boss wall
STANDOFF_TAP_DIA   = 1.8   # M2 self-tap bore (sized for FDM tolerance)
STANDOFF_TAP_DEPTH = 4.0
STANDOFF_TAP_CHAMFER = 0.3  # 45° entry chamfer at bore top

# ---------- Clearances ----------
PCB_XY_CLEARANCE = 0.5
PCB_HOLE_DIA     = 4.1

# ---------- Optional perimeter PCB ledge (default off; see spec §3.4) ----------
PCB_LEDGE_ENABLED = False
PCB_LEDGE_WIDTH   = 1.0   # mm; ring width if enabled

# ---------- USB-C jack (physical) ----------
# The nice!nano USB-C jack sits above the flat rim (jack ~MCU_PCB_TOP_Z 13.8 >
# MAIN_RIM_Z 12.5), so with no hill the port is open to air over the +Y wall —
# no case cutout is needed. USB_C_W is kept for the PCB phantom's jack stub.
USB_C_W = 9.0

# ---------- Slide-switch finger access (−X wall + canopy) ----------
# A wide, top-open "decrement" scoop lowers the −X wall AND the canopy over the SK12D07VG3 slide
# actuator (nub at case ≈ (13, 70.5), at the inner wall face, travelling along Y). It is a
# rounded valley WIDER in Y than tall in Z, cut from a floor just below the nub UP through the
# upper wall and the whole canopy — roof included — so it is open from the top and the −X side
# and a finger/nail reaches the nub. Cut in build_top_part AFTER the canopy is fused, so it
# lowers both the wall and the cover in one op. Its floor is above SEAM_Z (6.25), so the scoop
# lives entirely in the TOP part — the BOTTOM is untouched (access is from the top/side, not from
# below, so the lower wall never blocks). See docs and the plan slide-scoop-decrement.md.
SLIDE_SWITCH_W           = 6.0   # mm; slide actuator nominal width (reference)
SLIDE_NUB_Z              = PCB_TOP_Z + 2.5   # 10.4; actuator nub centre Z (finger-access height)
SLIDE_SCOOP_W            = 10.0  # mm; scoop width in Y (wider than its Z depth)
SLIDE_SCOOP_FLOOR_Z      = 9.0   # mm; scoop floor — just below the nub; solid wall remains below
SLIDE_SCOOP_INNER_MARGIN = 0.25  # mm; reach past the inner wall face to bare the nub (no PCB)
SLIDE_SCOOP_FLOOR_R      = 2.0   # mm; floor rounding (reads as a valley, not a box)
SLIDE_SCOOP_SIDE_R       = 2.5   # mm; plan-corner rounding at the scoop ends
SLIDE_SCOOP_X_SHIFT      = 0.4   # mm; slide the WHOLE cutter toward −X (out the wall). Pulls the
#                                  inner reach (x1) back from the cavity and moves the floor-fillet
#                                  shelf outboard, away from the nub — experiment knob (0 = original).

# ---------- Battery pocket (405070 LiPo cell: 4.0mm thick, 50x70mm footprint) ----------
# Recessed into the floor's added 1.8 mm thickness (see FLOOR_THICKNESS above),
# so 2.0 mm of solid floor remains beneath the pocket, matching the case floor
# everywhere else. Position verified against data/pcb_outline.json + the 5
# standoff posts (MOUNTING_HOLES): centered in the open main key well, clear of
# every standoff and every bottom-mounted component (those all cluster near
# the MCU/thumb-cluster column, far from this footprint).
BATTERY_POCKET_POS   = (69.5, -48.5)  # PCB coords, pocket footprint center
BATTERY_W            = 50.0   # mm, X extent
BATTERY_L            = 70.0   # mm, Y extent
BATTERY_THICKNESS    = 4.0    # mm, nominal 405070 cell thickness
BATTERY_XY_CLEARANCE = 0.4    # mm, per-side insertion clearance
BATTERY_Z_CLEARANCE  = 0.3    # mm, extra clear height above nominal thickness
BATTERY_POCKET_DEPTH = 1.8    # mm, = new FLOOR_THICKNESS(3.8) − original(2.0)
BATTERY_POCKET_CORNER_R = 2.0  # mm, pocket corner fillet radius

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

# Outer envelope = PCB span + a full wall + clearance on every side. Derived so
# the footprint tracks WALL_THICKNESS automatically and the PCB stays centred.
OUTER_WIDTH  = (PCB_X_MAX - PCB_X_MIN) + 2 * (WALL_THICKNESS + PCB_XY_CLEARANCE)  # = 154.0
OUTER_DEPTH  = (PCB_Y_MAX - PCB_Y_MIN) + 2 * (WALL_THICKNESS + PCB_XY_CLEARANCE)  # = 126.0

PCB_OFFSET_X = (OUTER_WIDTH - (PCB_X_MAX - PCB_X_MIN)) / 2 - PCB_X_MIN
PCB_OFFSET_Y = (OUTER_DEPTH - (PCB_Y_MAX - PCB_Y_MIN)) / 2 - PCB_Y_MIN


def pcb_to_case(x: float, y: float) -> tuple[float, float]:
    """Translate a PCB-coordinate point into case (outer-rect) coordinates."""
    return (x + PCB_OFFSET_X, y + PCB_OFFSET_Y)


# ---------- Phantom (visual fit-check; default off) ----------
SHOW_PCB_PHANTOM    = True # True: adds PCB phantom to case.py __main__ viewer
SHOW_PLATE_PHANTOM  = True # True: adds switch plate phantom to case.py __main__ viewer
SHOW_SWITCH_PHANTOM = True # True: adds MX switch phantom to case.py __main__ viewer
SHOW_TOP_COVER      = True # True: adds the sandwich top cover to case.py __main__ viewer

# MCU physical stack heights — used by the PCB phantom (jack/header visuals) and
# as a convenient over-tall bound for the slide-switch wall cutters.
MCU_PCB_TOP_Z    = 13.8    # nice!nano PCB top including socket height above main PCB
USB_C_BODY_TOP_Z = 19.8    # USB-C jack body top surface
MCU_HILL_Z       = PCB_TOP_Z + 11.0   # top of MCU + header legs (physical stack top)
MCU_BODY_L       = 33.0    # MCU body length in Y (mm)

# ---------- MCU +Y cover relief (B+/B- clearance) ----------
# The nice!nano's B+/B- pads (unsoldered — meant for direct battery wire, no leg
# through the main PCB) sit near the USB-C end and overhang past the +Y case
# wall, which at the MCU's own X column sits at the tight PCB edge (PCB Y=0.0) —
# only PCB_XY_CLEARANCE (0.5mm) of clearance. The index-finger switch column next
# to the MCU (SW2, X≈49.77) has its PCB edge 2.5mm further +Y (polygon step from
# Y=0.0 to Y=2.5 in data/pcb_outline.json). This relief pushes the +Y wall face
# out to that same index-column line — ONLY the +Y wall; the −X wall is left
# exactly as-is. The wall shifts outward (thickness preserved), it does not thin.
MCU_Y_RELIEF_TARGET_Y  = 2.5   # mm, PCB coords — target +Y edge (matches index column's stagger)
# The relief must reach all the way to where the polygon itself naturally arrives
# at MCU_Y_RELIEF_TARGET_Y (PCB X=41, the same flat-segment boundary) — stopping
# short leaves an unrelieved gap that reads as a dip back to the tight line.
MCU_Y_RELIEF_X_HI      = 41.0  # mm, PCB coords — polygon's own Y=0.0→2.5 step point
# The outer shell's wall face is an arc-based polygon offset (Kind.ARC), not a raw
# flat plane, so a bump box that merely touches it can fail to fuse (OCC
# coincident-face union is unreliable). Overlapping 1mm into solid wall material
# (well within WALL_THICKNESS), and starting the box at Z=0 so it overlaps
# the floor slab, guarantees a real fuse once the cavity is widened behind it.
MCU_Y_RELIEF_OVERLAP   = 1.0   # mm, fusion overlap into existing wall material
# The +Y relief widens the cavity for the nice!nano + B+/B- wires. In the sandwich
# TOP part the walls run past the plate top, so the band above MAIN_RIM_Z becomes
# the printed ceiling. Only the MCU bay (PCB X ≤ this) may stay hollow up there —
# the switch column to the east must keep its ceiling or the top shell is open to
# air. 20.0 (case X≈36.5) is the plate's own switch/bay boundary and sits ~1.5 mm
# clear of the nice!nano's right edge (case X≈35).
MCU_Y_RELIEF_CEILING_X = 20.0  # mm, PCB coords — east limit of the ceiling-band cavity

# ---------- Slide-switch slot X reach (−X wall) ----------
# Inner-X bound the slide-switch slot cutter extrudes to. Derived from the −X wall
# corner (pcb_to_case(0,0)[0]) + a 1.5 mm margin so it tracks the PCB re-centring
# when WALL_THICKNESS changes (15.25 at WALL=4.75).
MCU_HILL_NEG_X_INNER_BOUND_X: float    = pcb_to_case(0, 0)[0] + 1.5