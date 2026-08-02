"""All dimensions in mm. Single source of truth for the case geometry."""

# ---------- Heights (Z = 0 at case bottom) ----------
# The whole Z ladder is DERIVED from FLOOR_THICKNESS via named gaps, so raising
# the floor cascades the PCB seat / plate seat / rim / cover / seam up by the same
# amount automatically. (Previously these were literals that silently did NOT track
# the floor.) The gap values below reproduce the original geometry EXACTLY at the
# historical FLOOR_THICKNESS = 3.8.
#
# FLOOR_THICKNESS raised 3.8 → 6.3 (+2.5 mm): the battery footprint sits under 12
# switches, so the hotswap sockets (~2 mm below the PCB) hang over it and cannot be
# dodged in Z. Lifting the whole stack 2.5 mm lifts the sockets clear so a real
# 4.5 mm 405070 cell fits in a deep pocket with 2.0 mm of solid floor beneath it.
FLOOR_THICKNESS = 6.3   # was 3.8

# Named vertical gaps (invariant — these reproduce the original stack at FLOOR=3.8):
STANDOFF_SHOULDER_H = 2.5   # PCB seat above the floor top (standoff lower shoulder)
PCB_THICKNESS       = 1.6   # main PCB thickness
MX_BODY_CLEAR       = 3.0   # measured MX switch-body gap: plate seat above PCB top
PLATE_THICKNESS     = 1.6   # switch-plate thickness (12.5 − 10.9 at the old floor)

PCB_SEAT_Z   = FLOOR_THICKNESS + STANDOFF_SHOULDER_H  # 8.8  (was 6.3 at FLOOR=3.8)
PCB_TOP_Z    = PCB_SEAT_Z + PCB_THICKNESS             # 10.4 (was 7.9)
PLATE_SEAT_Z = PCB_TOP_Z + MX_BODY_CLEAR              # 13.4 (was 10.9)
PLATE_TOP_Z  = PLATE_SEAT_Z + PLATE_THICKNESS         # 15.0 (was 12.5)

# Minimal short case: perimeter walls end flush with the plate's top surface —
# no proud lip above the plate. The MCU hill still rises above this (excluded).
MAIN_RIM_Z      = PLATE_TOP_Z

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
# 14 mm plate cutout is grown to a ~15.7 mm window (0.05 mm/side) that HUGS the
# switch's 15.6 mm top housing so the switch pokes through and the cover seats flat
# on the plate. The window is sized to hug the switch body (not oversized) so NO ring
# of the switch plate shows around each key — the case/plate can be different colours
# and the plate never peeks through (the 0.05 mm gap reads as a shadow line, not
# plate colour, and keeps the boolean/print non-degenerate). The window corners are
# mitered square (Kind.INTERSECTION), not rounded, so the switch box's square corners
# clear too. Keycaps float entirely above it — skirt at full
# press ~14.0 mm > cover top 16.0 mm — so 1.0 mm is safe (1.5 mm would just kiss the
# skirt on a hard edge press). The plate's own inner notch leaves the MCU/OLED/
# slide/JST bay open for free.
MX_TOP_HOUSING_W        = 15.6   # mm; widest part of a Cherry MX switch (rests on plate) — drives the window size
COVER_THICKNESS         = 1.0    # mm; lid thickness, top at MAIN_RIM_Z + 1.0 = 16.0
COVER_WINDOW_OFFSET     = 0.85   # mm; 14 mm cutout -> 15.7 mm window, 0.05 mm/side off the 15.6 housing (invisible shadow gap, plate hidden, non-degenerate)
COVER_SCREW_CLEARANCE_DIA = 2.4  # mm; M2 screw shaft clearance through the cover

# ---------- Switch-puller access notches ----------
# The flush window hides the plate but also hugs the switch's 15.6 mm collar at the
# plate line (Z = MAIN_RIM_Z) — exactly where a switch puller must seat its claws to
# grip and lift a switch (the top housing tapers inward above the collar, so a claw
# on the proud upper body just cams off). Two small notches per MX switch, cut on the
# switch's local ±Y faces (the north/south faces a puller grabs), open the cover down
# to the plate on those two sides so the claws can descend beside the collar and pull
# a switch IN PLACE without removing the top shell. Verified against the Cherry MX
# datasheet drawing (top housing 6.6 mm above plate; 15.6 mm collar rests on plate).
#
# Geometry is a box per notch: NOTCH_W wide (tangential), spanning radius INNER_R→
# OUTER_R from the switch centre (INNER_R sits inside the ~7.85 mm window edge so the
# notch merges with the window; OUTER_R reaches ~1.2 mm past the 7.8 mm collar for
# claw room). OUTER_R is capped so two facing notches on 19.05 mm-pitch neighbours
# leave a ~1 mm cover bridge between them (cover stays one solid, plate barely shows).
COVER_PULLER_NOTCH        = False   # False → flush cover with no puller access (swap needs shell removal)
COVER_PULLER_NOTCH_W      = 4.0    # mm; notch width (tangential) — sized for a puller claw
COVER_PULLER_NOTCH_INNER_R = 7.0   # mm; radial inner edge (inside the window, so it merges)
COVER_PULLER_NOTCH_OUTER_R = 9.0   # mm; radial outer edge (~1.2 mm claw pocket past the 7.8 collar)
# The plate-outline membrane sits ~0.3–0.7 mm inside the inner cavity wall, so on
# its own it floats free (a separate solid) inside the TOP part. Grow the membrane
# outline outward by this margin so it bites into the upper-wall material and fuses
# into one solid with the TOP walls. The bay notch shrinks by the same amount but
# stays wide open (the MCU/OLED/JST bay is ~20 mm across). Real overlap into wall
# material is used (not a coincident-face touch) because OCC's boolean union is
# unreliable on merely-coincident faces.
COVER_FUSE_MARGIN       = 1.0    # mm; membrane→upper-wall fusion overlap in the TOP part

# ---------- Sandwich clamshell split (TOP tub / BOTTOM plate) ----------
# The shell is NOT split at a mid-wall butt seam (that showed a line on the outer
# face and mated poorly). Instead the TOP is a deep TUB that owns the full outer
# skin — the outer wall runs unbroken from COVER_TOP_Z all the way to the ground,
# so there is NO seam on any outer face. The BOTTOM is a thin INSET floor plate
# that tucks up behind the skin and joins via a RABBET (stepped lap): the plate's
# outer rim rises into a pocket in the tub's inner wall, hidden as a shadow line on
# the underside. See docs/spec deep-dive-sandwich-seam-modification.md.
COVER_TOP_Z  = MAIN_RIM_Z + COVER_THICKNESS  # 16.0 mm; TOP part rim (membrane top)

# Rabbet geometry (offsets are radial, from the PCB polygon outward):
#   skin (tub, → ground)  SEAM_SKIN | gap SEAM_FIT_CLEAR | plate rim SEAM_RIM_THK
# summing to WALL_THICKNESS across the wall. The plate rim seats inside the tub
# skirt; a small Z gap at the ledge lets the SCREWS (not the rabbet) set the clamp.
# Clearances follow the design-for-print mating-gap rule: 0.3 mm is the conservative
# FDM minimum (below that FDM tends to weld / bind). SEAM_FIT_CLEAR was tightened
# 0.3 → 0.2 after the feat/last-printed-case print proved this printer's calibration
# (PCB_XY_CLEARANCE 0.5 and the slide-switch slot both fit perfectly); 0.2 is as low
# as is safe on a ~150 mm irregular outline, where warping — not printer accuracy —
# becomes the binding risk. The fit stays intentionally loose because the screws
# clamp and the 5 standoffs — not the rabbet — set the precise XY registration.
SEAM_LEDGE_Z    = FLOOR_THICKNESS   # 6.3; rabbet ledge / plate-rim top / the split height
SEAM_SKIN       = 2.0    # mm; outer skin kept with the tub at the rabbet (descends to ground)
SEAM_FIT_CLEAR  = 0.2    # mm; per-side XY clearance, plate rim ↔ tub skirt pocket (was 0.3)
SEAM_LEDGE_CLEAR = 0.3   # mm; Z gap at the ledge so the screws clamp (no over-constraint)
SEAM_LEAD_IN    = 0.6    # mm; 45° lead-in chamfer on the plate rim's top-outer edge (plate-side starter)
SEAM_POCKET_LEAD_IN = 0.4  # mm; 45° starter chamfer on the tub pocket MOUTH (tub-side starter, so
#                            BOTH mating leading edges guide + the mouth can't elephant-foot-pinch).
#                            Kept small: it stacks with BOTTOM_CHAMFER on the opposite skirt corner,
#                            so 0.4 leaves ≥1.4 mm of skin at the ground-line first layer.
SEAM_RIM_THK    = WALL_THICKNESS - SEAM_SKIN - SEAM_FIT_CLEAR   # = 2.55; derived plate-rim thickness

# Snap aids (assembly hold-shut) are DEFERRED: the 5 standoff screws are the real
# clamp and the rabbet self-locates, so the first print validates that fit alone.
# Adding barb/detent pairs needs robust placement on the irregular Sofle outline
# (a naive rectangular layout floats barbs off the curved wall spans) — a follow-up
# once the rabbet clearance is dialled in. See the spec's snap section.

# ---------- Drafted rim facet (outer-top treatment) ----------
# The tall (16 mm) flat wall read as an ugly slab from the sides. The old rim treatment
# was a shallow 1.9 mm 45° chamfer (OUTER_TOP_CHAMFER) — far too small to fight that.
# Instead a drafted FACET is shaved from the outer-top all round (RIM_*), and the
# palm-facing SOUTH (−Y) run gets a deeper, more aggressive facet (FRONT_*) so the front
# reads about half as tall — the trick premium alloy boards use on the hands' inner face.
#
# OUTER_TOP_CHAMFER stays defined (canopy.py reads it as a wall-inset offset) but its old
# rim-chamfer APPLICATION in build_tray is replaced by these facets. The facet is a wedge
# cut from the outer wall top: full wall thickness at the toe (Z = rim − DROP), sloping
# inward by RUN at the rim. Built as cutter solids because OCC rejects an asymmetric
# chamfer() on this arc-offset edge set (see the OUTER_TOP_CHAMFER note above).
RIM_FACET_DROP     = 4.0   # perimeter facet vertical extent (Z = rim → rim−4)
RIM_FACET_RUN      = 2.0   # perimeter inset at the rim (~27° from vertical); rim wall left = 2.75
FRONT_FACET_DROP   = 8.0   # south facet vertical extent (Z = rim → rim−8): a tall, dominant bevel
FRONT_FACET_RUN    = 3.0   # south inset at the rim (~21° from vertical); rim wall left = 1.75
# ---- Deep south facet: East '\' on ramp E4 + a DERIVED exact-twin West '/' under the thumb ----
# The deep facet covers the low front (thumb ramp → flat front → SE ramp E4). Its deep→shallow
# boundary shows as two creases that are exact mirror twins:
#   • EAST '\' — the flat cap y=FRONT_FACET_Y_MASK crossing the rising SE ramp E4 (pts[5]→pts[6]);
#     a long diagonal near the SE corner, kept exactly where it was. Its X-run/angle define the twin.
#   • WEST '/' — DERIVED, not tuned: the East crease's X-run mirrored (rim east of toe) and centred at
#     the midpoint of the two thumb switches (pcb_geometry.thumb_switch_midpoint_x), dropped onto the
#     straightened SW thumb ramp (pts[2]→pts[4]). Same run/angle as the East by construction, so the
#     two read as exact twins in front elevation. See tray._front_slash_crossings / _front_facet_mask.
# The OUTER wall + facet drop the barely-1 mm reflex kink pts[3] (tray._outer_poly_pts) so the SW ramp
# is one straight edge and the '/' is clean; the cavity/plate keep the sharp outline, so PCB fit is
# unchanged. (The West rides a lower/steeper wall, so its depth (Y) differs from the East — but the
# front-elevation profile you see is an exact mirror. No West tunables: it follows the East crease and
# the switch positions automatically.)
FRONT_FACET_Y_MASK = 24.0  # TOP cap; its crossing of ramp E4 IS the East '\' slash (E4 y 23.25→33.25)

# Reflex outline corners (the outline turning the "wrong way": front idx3/idx4, the west jog,
# the east/back notches) leave sharp V-notches in a Kind.ARC offset — each one used to throw a
# spurious crease through the wall and facet. The outer wall + facet profiles are built from a
# polygon whose REFLEX corners are rounded by this radius (2-D, per-corner fallback), so the
# chamfer flows continuously around them. The CAVITY keeps the sharp polygon (PCB fit unchanged).
REFLEX_ROUND_R = 2.0   # mm; plan rounding of reflex outline corners (outer wall + facet only)

# Facet guards — the sandwich TOP is the binding case (rim = COVER_TOP_Z; the outer skin below
# SEAM_LEDGE_Z is only SEAM_SKIN thick; the membrane fuses into the inner COVER_FUSE_MARGIN of wall):
assert FRONT_FACET_RUN <= WALL_THICKNESS - 1.5, "front facet thins the rim wall below 1.5 mm"
assert RIM_FACET_RUN <= WALL_THICKNESS - 1.5, "perimeter facet thins the rim wall below 1.5 mm"
assert FRONT_FACET_RUN < WALL_THICKNESS - COVER_FUSE_MARGIN, "front facet reaches the membrane fuse band"
assert COVER_TOP_Z - FRONT_FACET_DROP >= SEAM_LEDGE_Z + 1.0, "front facet toe intrudes on the rabbet skin zone"

# ---------- Encoder plateau (TOP part, around EC11 rotary encoder) ----------
# The EC11 body is a ~12 mm box that mounts through the plate's encoder cutout
# (~12.7 mm) and protrudes ~2 mm above the plate top. On the sandwich TOP part a
# single-body PLATEAU caps it: one low mound, hollow inside to clear the box, with
# a closed roof and a plain shaft hole. The plateau leaves the cover tangentially
# (concave ogee foot) and rounds over at the top edge — no hard step, no second
# tier. The box is hidden; the bushing + 6 mm shaft exit through the shaft hole.
ENCODER_BODY_PROUD     = 2.0   # mm; EC11 box top above the plate (measured)
ENCODER_BODY_TOP_Z     = PLATE_TOP_Z + ENCODER_BODY_PROUD   # 17.0; box top (cavity must clear this)
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

# ---------- MCU physical stack (nice!nano v2 / SuperMini nRF52840) ----------
# Used by the PCB phantom (board/jack visuals), by the canopy roof derivation, and as a
# convenient over-tall bound for the slide-switch wall cutters. Declared HERE, ahead of the
# USB-C block, because the jack bands are derived from the nano's two board faces.
MCU_PCB_TOP_Z    = PCB_TOP_Z + 11.0   # measured nano board top, identical both orientations (was +5.9 — 5.1 mm short)
MCU_HILL_Z       = MCU_PCB_TOP_Z      # physical stack top excluding the jack; coincides with the board top by measurement
MCU_BODY_L       = 34.1    # SuperMini nRF52840 overall length in Y (Mechboards; the nice!nano
#                            it clones is 33.0). Consume via MCU_BODY_N_Y / MCU_BODY_S_Y below —
#                            the board is anchored at its pin array, not centred on MCU_POS.
MCU_BOARD_THK    = 1.6     # nano PCB thickness — CONFIRMED: Mechboards and Keebio both spec the
#                            SuperMini at a 1.6 mm PCB, same as the nice!nano v2 it clones.
#                            Positions the FLIPPED jack band (see USB_JACK_* below).
MCU_PCB_BOT_Z    = MCU_PCB_TOP_Z - MCU_BOARD_THK   # 19.8; nano board underside

# ---------- USB-C jack (MID-MOUNT; derived from the nano board faces) ----------
# The SuperMini nRF52840 (like the nice!nano v2 it clones) carries a MID-MOUNT USB-C: the
# shell straddles a routed slot in the nano board instead of sitting on top of it. GCT's
# Type-C selection guide lists 16-pin mid-mount parts at a 3.16 mm profile with sink offsets
# of 0.80 / 1.00 / 1.60 / 2.10 mm; this board is the 1.00 mm sink — caliper-confirmed
# (~3 mm shell, ~1 mm buried in the board, ~2 mm proud of the component face).
#
# So the shell hangs USB_JACK_SINK below the board's COMPONENT face and USB_JACK_PROUD
# above it. Flipping the nano flips which physical face that is — the whole reason the two
# halves need different bands:
#     flipped (components down, jack under the board)   17.64 -> 20.80
#     neutral (components up,   jack on top)            20.40 -> 23.56
# They now OVERLAP through 20.40 -> 20.80 (they used to abut exactly at 20.4, an artifact of
# the old guessed 4.0 mm body). The halves are built with DIFFERENT orientations, so the TOP
# part is not mirror-identical — only the canopy window band differs, the silhouette stays
# common (see canopy.canopy_usb_z and CANOPY_RIDGE_TOP_Z).
USB_C_W       = 9.0
USB_JACK_H    = 3.16   # mm; mid-mount shell height (was 4.0 — a guess, 0.84 mm too tall)
USB_JACK_SINK = 1.00   # mm; shell depth BELOW the board's component-side face
USB_JACK_PROUD = USB_JACK_H - USB_JACK_SINK   # 2.16; shell height above that face
USB_JACK_Y_PROTRUDE = 1.0   # mm; measured: the jack's +Y face sits this far past the
#                            nano board's +Y edge. The jack stops ~0.4 mm short of the
#                            canopy north wall's inner face — only the plug bridges the
#                            wall. (The pcb_phantom stub depth uses this.)

# Port-mouth DESIGN MARGINS around the jack body (NOT measurements — the values above are
# the hardware; these are the slack the printed port adds). The canopy port cutter is the
# jack band grown by these clears. They also cover the residual disagreement between the
# two hardware readings: a plate-top → jack-top caliper reading of 9.0 mm implies a jack top
# of 24.0, while the board-face derivation below gives 23.56 — 0.44 mm apart. The derivation
# wins (it is datasheet-anchored), and 0.7 mm of ceiling clear absorbs the difference either way.
USB_PORT_CLEAR_LO = 0.8   # mm; port floor below the jack body
USB_PORT_CLEAR_HI = 0.7   # mm; port ceiling above the jack body
USB_PORT_W_CLEAR  = 2.0   # mm; port width = USB_C_W + this (jack + plug clearance)

# ---------- USB-C PLUG (the cable end) — drives the port's STEPPED bore ----------
# The receptacle never swallows the whole plug shell. On any real device part of the shell
# stays outside and the case wall hides it, so it only LOOKS fully seated. What matters is
# ENGAGEMENT — how much shell is inside the jack — not seating:
#
#     engagement = USB_PLUG_SHELL_L − (wall outer face → jack mouth)
#
# Here the jack mouth sits 4.41 mm behind the canopy's outer face, so a straight shell-sized
# hole leaves 2.24 mm of engagement (34%) AND blocks the overmold outright — that port would
# not take a standard cable at all. The fix is a stepped bore: a wide outer POCKET that
# admits the overmold for part of the wall, then a narrow NECK sized for the shell.
USB_PLUG_SHELL_L = 6.65   # mm; USB-IF plug shell insertion depth (shell itself 8.34 × 2.56)
USB_OVERMOLD_W   = 12.35  # mm; USB-IF MAXIMUM plug overmold width.  Overmolds are NOT
USB_OVERMOLD_H   = 6.50   # mm; USB-IF MAXIMUM plug overmold height. standardised, so sizing
#                           to the published max is what makes ANY compliant cable fit.
USB_OVERMOLD_CLEAR = 0.5  # mm; total (not per-side) slop added to the pocket cross-section
USB_PORT_ENGAGE_TARGET = 5.0  # mm of shell inside the jack (75%). NOT a spec figure — the
#                           USB-IF documents publish no minimum. Anchored on shipping
#                           hardware, which runs 0.8–2.0 mm of wall in front of the
#                           receptacle, i.e. 4.6–5.8 mm of engagement.

# Neutral: components UP, so the component face is the board TOP.
USB_JACK_NEUTRAL_LO_Z = MCU_PCB_TOP_Z - USB_JACK_SINK    # 20.40
USB_JACK_NEUTRAL_HI_Z = MCU_PCB_TOP_Z + USB_JACK_PROUD   # 23.56
# Flipped: components DOWN, so the component face is the board UNDERSIDE — the proud side of
# the shell now points down and the sunk side pokes up through the board.
USB_JACK_FLIPPED_LO_Z = MCU_PCB_BOT_Z - USB_JACK_PROUD   # 17.64
USB_JACK_FLIPPED_HI_Z = MCU_PCB_BOT_Z + USB_JACK_SINK    # 20.80

# Which way the nice!nano faces on each half. Assembly-time fact, not derivable from
# the PCB (which is reversible) — flipping a build means flipping this mapping.
MCU_ORIENTATION = {"left": "flipped", "right": "neutral"}


def usb_jack_z(side: str) -> tuple[float, float]:
    """(lo, hi) Z of the USB-C jack body for a half, per its MCU orientation."""
    if side not in MCU_ORIENTATION:
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")
    if MCU_ORIENTATION[side] == "flipped":
        return USB_JACK_FLIPPED_LO_Z, USB_JACK_FLIPPED_HI_Z
    return USB_JACK_NEUTRAL_LO_Z, USB_JACK_NEUTRAL_HI_Z


def usb_port_z(side: str) -> tuple[float, float]:
    """(lo, hi) Z of the north-wall USB PORT for a half: the measured jack band
    (``usb_jack_z``) grown by the USB_PORT_CLEAR_LO/HI design margins."""
    lo, hi = usb_jack_z(side)
    return lo - USB_PORT_CLEAR_LO, hi + USB_PORT_CLEAR_HI

# ---------- Slide-switch finger access (−X wall + canopy) ----------
# A wide, top-open "decrement" scoop lowers the −X wall AND the canopy over the SK12D07VG3 slide
# actuator (nub at case ≈ (13, 70.5), at the inner wall face, travelling along Y). It is a
# rounded valley WIDER in Y than tall in Z, cut from a floor just below the nub UP through the
# upper wall and the whole canopy — roof included — so it is open from the top and the −X side
# and a finger/nail reaches the nub. Cut in build_top_part AFTER the canopy is fused, so it
# lowers both the wall and the cover in one op. It is a TOP-only feature (the BOTTOM is a separate
# inset plate below the rabbet ledge); access is from the top/side, not from below, so the plate
# never blocks. See docs and the plan slide-scoop-decrement.md.
SLIDE_SWITCH_W           = 6.0   # mm; slide actuator nominal width (reference)
SLIDE_NUB_Z              = PCB_TOP_Z + 2.5   # actuator nub centre Z (finger-access height); tracks the PCB
SLIDE_SCOOP_W            = 10.0  # mm; scoop width in Y (wider than its Z depth)
SLIDE_SCOOP_FLOOR_Z      = SLIDE_NUB_Z - 1.4  # mm; scoop floor just below the nub; tracks the PCB (was literal 9.0)
SLIDE_SCOOP_INNER_MARGIN = 0.25  # mm; reach past the inner wall face to bare the nub (no PCB)
SLIDE_SCOOP_FLOOR_R      = 2.0   # mm; floor rounding (reads as a valley, not a box)
SLIDE_SCOOP_SIDE_R       = 2.5   # mm; plan-corner rounding at the scoop ends
SLIDE_SCOOP_X_SHIFT      = 0.4   # mm; slide the WHOLE cutter toward −X (out the wall). Pulls the
#                                  inner reach (x1) back from the cavity and moves the floor-fillet
#                                  shelf outboard, away from the nub — experiment knob (0 = original).

# ---------- Slide-switch actuator container (drop-in pocket, TOP part) ----------
# A registered clearance pocket shaped to the physical SK12D07VG3 (metal can body +
# actuator nub), grown 0.5 mm on every X/Y face and poured from SLIDE_ACTUATOR_FLOOR_Z
# UP to the cover underside, so the switch has a switch-shaped clearance channel as the
# tub lowers over the PCB+switch assembly. Subtracted in build_top_part AFTER the scoop;
# it is a TOP-only feature (the BOTTOM is a separate inset plate below the rabbet ledge —
# untouched). No retaining lip: a plain clearance pocket. The top is capped at the cover
# underside so the 1.0 mm lid is NOT
# perforated (the can top is 12.2, leaving 0.3 mm of cover above it).
#
# These are STRUCTURAL mirrors of the datasheet-derived can/nub dims. The pcb_phantom
# _SK12_* dims are marked "phantom-only, not structural" — do NOT import them here;
# structural geometry owns its own values. The placement (registration off SW31) is
# shared cleanly via pcb_geometry.slide_switch_placement / rotate_2d, so the cavity
# tracks the switch exactly without coupling structure to the phantom module.
SLIDE_ACTUATOR_BODY_W       = 4.4  # mm; metal can width (perp. to pin row, local Y)
SLIDE_ACTUATOR_BODY_L       = 4.0  # mm; metal can length (along pin row, local X)
SLIDE_ACTUATOR_BODY_H       = 4.3  # mm; metal can height above the PCB (reference)
SLIDE_ACTUATOR_NUB_L        = 3.5  # mm; actuator nub length along pin row (local X)
SLIDE_ACTUATOR_NUB_D        = 3.0  # mm; actuator protrusion beyond the can edge (local -Y)
SLIDE_ACTUATOR_NUB_H        = 2.0  # mm; actuator height above the can top (reference)
SLIDE_ACTUATOR_PIN_CENTER_X = 2.0  # mm; can centre offset from footprint origin (local X)
SLIDE_ACTUATOR_PAD          = 0.5  # mm; clearance grown on every X/Y face of the pocket
SLIDE_ACTUATOR_FLOOR_Z      = 0.0   # mm; pour depth for the drop-in channel (decoupled from the
#                                      seam — the tub is now open below this anyway; kept as a
#                                      registered clearance floor for the switch can/nub)
SLIDE_ACTUATOR_TOP_Z        = MAIN_RIM_Z - 0.5   # mm; cover underside — do NOT perforate the lid (tracks the rim; was literal 12)

# ---------- Battery pocket (405070 LiPo cell: 50x70mm footprint) ----------
# The footprint sits UNDER 12 switches, so the hotswap sockets (~2 mm below the PCB)
# hang over it. The pocket is now a DEEP recess in the thickened floor: it holds a
# real 4.5 mm cell with BATTERY_FLOOR_BASE (2.0 mm) of solid floor beneath, and the
# raised stack (FLOOR_THICKNESS 6.3) lifts the sockets clear of the cell top.
# Pocket depth is DERIVED from the floor so it tracks any future floor change.
#
# XY: grown east-biased. The two WEST standoffs (PCB X≈39.6) are the only tight
# neighbours (~1.7 mm from the pocket wall); east/north/south have 17–27 mm free.
# BATTERY_POCKET_SHIFT_X moves the pocket +X so a larger clearance grows the roomy
# sides while the west edge (and its standoff gap) barely moves.
BATTERY_POCKET_POS   = (69.5, -48.5)  # PCB coords, pocket footprint center
BATTERY_W            = 50.0   # mm, X extent (nominal cell)
BATTERY_L            = 70.0   # mm, Y extent (nominal cell)
BATTERY_THICKNESS    = 4.5    # mm, design thickness (real 405070 incl. wrapper/swell)
BATTERY_XY_CLEARANCE = 1.5    # mm, per-side insertion clearance (was 0.4)
BATTERY_POCKET_SHIFT_X = 1.0  # mm, shift pocket center +X (east) to keep west standoffs clear
BATTERY_Z_CLEARANCE  = 0.3    # mm, extra clear height above design thickness
BATTERY_FLOOR_BASE   = 2.0    # mm, solid floor kept beneath the pocket
BATTERY_POCKET_DEPTH = FLOOR_THICKNESS - BATTERY_FLOOR_BASE   # = 4.3; tracks the floor
BATTERY_POCKET_CORNER_R = 2.0  # mm, pocket corner fillet radius

# ---------- Anti-slip rubber feet (external, underside of the bottom plate) ----------
# Shallow Ø10 seats recessed into the OUTER bottom face (Z=0) of the inset floor plate
# at 4 corners, so 10 mm self-adhesive rubber feet locate there and the keyboard grips
# the desk (doesn't slide while typing). NOT deep — a shallow locating seat; the foot
# sits mostly proud below and lifts the case off the desk.
#
# Positions are in CASE coords, chosen on solid plate material clear of the irregular
# Sofle outline edges (the bottom-right corner is cut by the thumb cluster) and clear of
# the battery pocket. Subtracted BEFORE the left-mirror, so they track to the mirrored
# outline on the left half.
FOOT_DIA   = 10.0   # mm, rubber-foot diameter → seat diameter
FOOT_DEPTH = 0.6    # mm, shallow locating-seat depth
FOOT_POSITIONS: tuple[tuple[float, float], ...] = (
    (20.0, 110.0),   # top-left
    (143.0, 104.0),  # top-right (pulled in off the cut corner)
    (20.0, 22.0),    # bottom-left
    (143.0, 38.0),   # bottom-right (thumb-cluster side is cut away lower)
)

# ---------- Component positions (PCB coords, mm) ----------
# MCU_POS is the centre of the nano's 24-hole PIN ARRAY, not the centre of its board —
# verified against data/raw/SofleKeyboard-PTH.drl: 12 Ø1.092 holes per row, 2.540 pitch,
# 27.940 span, rows 15.240 apart (0.600" — stock Pro Micro), array centre (10.269, -16.157).
# (The 0.457 X stagger inside each row is the Sofle's reversible dual footprint.)
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

# MCU physical stack heights (MCU_PCB_TOP_Z / MCU_HILL_Z / MCU_BODY_L / MCU_BOARD_THK)
# moved UP to the "MCU physical stack" block above the USB-C section: the jack bands are
# now derived from the nano's board faces, so they must be declared before that block.

# ---------- MCU board Y extent (anchored to the pin array, NOT centred on it) ----------
# The nano is located by its 24 pin holes, so the board's Y faces must be derived from the
# northmost pin — never from ``MCU_POS ± MCU_BODY_L/2``. That centred form happened to give
# the right answer only while MCU_BODY_L was the nice!nano's 33.0, which IS centred on the
# pins; at the SuperMini's 34.1 it silently walks the USB end 0.55 mm north and manufactures
# a collision with the canopy wall. The extra 1.1 mm is at the FAR end (the SuperMini's extra
# breakout pads): the footprint here is stock Pro Micro (0.600" rows, 2.54 pitch, 27.94 span,
# see MCU_POS), and the board would not be Pro-Micro-drop-in if its USB end had moved.
MCU_PIN_SPAN_Y      = 27.94   # mm; 11 × 2.54 between the outer pins — from the drill file
MCU_PIN_TO_USB_EDGE = 2.53    # mm; northmost pin centre → the board's USB-end edge
#                               (33.0 nice!nano centred on a 27.94 span ⇒ (33.0 − 27.94)/2)
MCU_BODY_N_Y = pcb_to_case(*MCU_POS)[1] + MCU_PIN_SPAN_Y / 2 + MCU_PIN_TO_USB_EDGE  # 116.09
MCU_BODY_S_Y = MCU_BODY_N_Y - MCU_BODY_L                                            # 81.99
# For reference: the PCB's own north edge at this column is 115.75, so the board overhangs
# it by 0.34 mm — that overhang is the unsupported B+/B- pad end (see the relief below).

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