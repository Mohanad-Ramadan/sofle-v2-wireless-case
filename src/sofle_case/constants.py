"""All dimensions in mm. Single source of truth for the case geometry."""
import math
from typing import NamedTuple

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
# MX switch-body gap: plate UNDERSIDE above PCB top. This is a HARDWARE datum — the switch
# body bottoms on the PCB and the plate clips onto its shoulder, so nothing the case does can
# change it. Two independent derivations and one measurement disagree, and the spread is real:
#
#   Cherry datasheet, total height   0.60 in = 15.24 mm from PCB, no keycap
#                                    15.24 - PLATE_THICKNESS 1.6 - _UPPER_H 6.6 - _STEM_H 3.5
#                                                                              -> 3.54
#   ai03 wiki, plate TOP at 5.0      5.0 - PLATE_THICKNESS 1.6                 -> 3.40  <- CONFIRMED
#   measured on the real Sofle                                                 -> ~4.0  <- BAD TOOL
#
# Set to the DERIVED value, by decision: the plate-datum route is the only one that measures the
# surface this constant actually names (plate underside), and it agrees with the datasheet route
# to 0.14 mm. That decision was later vindicated by measurement — see below.
#
# The old value was 3.0 — below every one of the three — and it is what made the printed sandwich
# refuse to close: the standoff pins topped out 0.4-1.0 mm BELOW where the switches actually hold
# the plate, so the plate never touched them, the screws bowed it down, and the cover rode up off
# the tub's rim.
#
# RESOLVED 2026-08-16 BY MEASUREMENT. The risk above was real and is now closed: PCB top to plate
# TOP, measured on the assembled board with the switches fully seated, reads 5.00 mm — dead on
# MX_PLATE_TOP_ABOVE_PCB. The derivation was right and the ~4.0 caliper reading was the faulty
# instrument (the owner had two calipers and suspected one was ~1 mm out; this is the reading that
# convicts it). The datasheet route agreeing to 0.14 mm was the signal to trust.
#
# WHAT THAT MEASUREMENT DOES AND DOES NOT PIN. It pins the SUM, PCB top -> plate top = 5.00, and
# the sum is what closing depends on: PLATE_TOP_Z is MAIN_RIM_Z, so the tub's rim height is now
# measured, not derived. It does NOT pin how the 5.00 splits between MX_BODY_CLEAR and
# PLATE_THICKNESS. If the real plate is not 1.6, this constant is wrong by the difference while
# PLATE_TOP_Z stays right — harmless for the seam, but PLATE_SEAT_Z and STANDOFF_PIN_RECESS are
# built on the split, so measure plate thickness before trusting the pin-to-plate gap.
#
# The closing stack is FLOOR_THICKNESS + STANDOFF_SHOULDER_H + PCB_THICKNESS + MX_BODY_CLEAR +
# PLATE_THICKNESS, and SEAM_LEDGE_CLEAR (0.3) is the ONLY slack in all five. With the top two
# terms now measured, any remaining closure error lives BELOW the PCB top — in the 2.5 mm of air
# under the board, where the hotswap sockets already eat ~2.0.
PLATE_THICKNESS     = 1.6   # switch-plate thickness (12.5 − 10.9 at the old floor)
MX_PLATE_TOP_ABOVE_PCB = 5.0  # mm; THE datum: plate TOP surface above PCB top (ai03 wiki, MX std)
MX_BODY_CLEAR       = MX_PLATE_TOP_ABOVE_PCB - PLATE_THICKNESS  # 3.40 — derived, tracks the plate

PCB_SEAT_Z   = FLOOR_THICKNESS + STANDOFF_SHOULDER_H  # 8.8  (was 6.3 at FLOOR=3.8)
PCB_TOP_Z    = PCB_SEAT_Z + PCB_THICKNESS             # 10.4 (was 7.9)
PLATE_SEAT_Z = PCB_TOP_Z + MX_BODY_CLEAR              # 13.8 (was 13.4 at MX_BODY_CLEAR=3.0)
PLATE_TOP_Z  = PLATE_SEAT_Z + PLATE_THICKNESS         # 15.4 (was 15.0)

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
# 14 mm plate cutout is grown to a 16.1 mm window (0.25 mm/side) that CLEARS the
# switch's 15.6 mm top housing so the switch pokes through and the cover seats flat
# on the plate. The window corners are mitered square (Kind.INTERSECTION), not
# rounded, so the switch box's square corners clear too.
#
# THE 0.25 IS A PRINT/ASSEMBLY BUDGET, NOT A STYLE CHOICE, AND IT WAS LEARNED THE HARD
# WAY. This was 0.85 (a 15.70 mm window, 0.05 mm/side) chosen so NO ring of switch plate
# shows around any key. That window cannot be assembled: the membrane has to swallow all
# 29 collars at once in the last millimetre of travel, and the tolerance stack against it
# is at least ±0.2 mm — the plate floats ±0.1 on Ø3.9 pins in its Ø4.1 holes, and each
# switch floats ±0.1 in its own 14.0 mm cutout with a 13.8 mm lower housing — before any
# FDM error, and printed windows come out UNDERSIZE. Measured on the built TOP: at 0.85
# every one of the 29 windows binds on a collar oversized by only 0.10 mm. The printed
# case would not close over the keyboard while the empty shells mated fine.
# So the cover now shows a 0.25 mm ring of plate per key. That reads as a shadow line at
# any normal viewing distance, which is the price of a lid that goes on.
#
# KEYCAP HEADROOM. The previous version of this comment claimed "skirt at full press ~14.0 mm
# > cover top 16.0 mm — so 1.0 mm is safe" — that arithmetic was never true (14.0 is not
# greater than 16.0) and dates from before FLOOR_THICKNESS went 3.8 -> 6.3 and pushed
# MAIN_RIM_Z (hence cover top) up 15.0 -> 15.4. Nobody re-derived it when the stack moved.
#
# KEYCAP_SKIRT_CLEAR_AT_FULL_PRESS is NOT a Cherry spec — Cherry's switch datasheet has no
# keycap-skirt dimension at all, since keycaps are a third-party part with skirt length set
# by whichever vendor molded the cap. 1.5 mm is a community figure (a Cherry-keycap owner on
# geekhack reports ~2 mm nominal skirt-to-plate clearance, with a 1.5u key just touching the
# plate under a hard edge-press) that also matches this build's own printed-and-assembled
# result closely enough to trust as a working number — precise enough tooling (sub-0.1 mm) to
# measure the real skirt on this keycap set was not available, so 1.5 mm is adopted as the
# accepted working value rather than a lab measurement. Given that provenance, treat the
# 0.5 mm headroom in test_top_cover.test_keycap_headroom as tight, not comfortable — it is a
# community/field number, not a datasheet one, and this build already hit contact once.
KEYCAP_SKIRT_CLEAR_AT_FULL_PRESS = 1.5  # mm; skirt bottom above plate top at full press — see note above
MX_TOP_HOUSING_W        = 15.6   # mm; widest part of a Cherry MX switch (rests on plate) — drives the window size
COVER_THICKNESS         = 1.0    # mm; lid thickness, top at MAIN_RIM_Z + COVER_THICKNESS (= 16.4 at current MAIN_RIM_Z)
COVER_WINDOW_OFFSET     = 1.05   # mm; 14 mm cutout -> 16.1 mm window, 0.25 mm/side off the 15.6 housing (was 0.85 = 0.05/side, which would not assemble — see above)
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
COVER_PULLER_NOTCH        = True   # False → flush cover with no puller access (swap needs shell removal)
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

# Snap aids (assembly hold-shut): see the "Rabbet snap latch" block further down. It has
# to follow the seam-wave constants, because the wave — not SEAM_NORTH_RISE_Z as an older
# note here claimed — is what sets both the Z budget a barb fits into and the y beyond
# which a relief cut stops being hidden. Spec: .omc/specs/deep-dive-invisible-snap-latches.md

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

# ---------- Integrated tent wedge (BOTTOM case) ----------
# The keyboard is tented by the BOTTOM CASE growing into a wedge, the way the WOBKEY Crush 80
# does it: top case is a constant-section shell, bottom case is thick at the back and thin at
# the front, and the whole assembly tips forward on it. The parting line between them therefore
# runs parallel to the KEYS, not to the desk -- which is what reads as "tented" from the side.
#
# The wedge is ADDED, never cut. Cutting the bottom case is what would wreck the Z ladder: the
# floor is 6.3 mm and only 2.0 mm of it is free, because the battery pocket's floor spans
# Y 30.8-103.8 through the middle. At a north pivot, 1.0 deg already leaves 0.34 mm under that
# pocket and 1.5 deg breaches it. Growing downward instead leaves FLOOR_THICKNESS, PCB_SEAT_Z,
# PLATE_SEAT_Z, COVER_TOP_Z and the whole rabbet completely untouched -- the internals simply
# ride the wedge as a rigid body.
#
# Cost, stated plainly: the back gets taller. That is unavoidable. Tilting means the switch
# plate stops being parallel to the desk, and with the internals rigid that height comes from
# the front dropping (impossible -- the battery) or the back rising. There is no third option.
#
# TENT_WEDGE_MIN_H is the wedge's thickness at the SOUTH. It is not padding:
#   * a wedge tapering to zero is a feather edge -- the first ~6 mm would be under one layer
#     and simply would not print;
#   * the front foot seats are FOOT_DEPTH deep, and at y=22 a zero-min wedge is only 0.77 mm
#     thick, so a 0.6 mm seat would leave 0.17 mm of floor under the pad;
#   * the reference keeps a visible band of bottom case at the front too.
# 6 deg, inside the premium-board band and one degree back from the 7 that was tried first. The
# cost is stated above and it is real: TENT_RISE goes 6.60 -> 13.24, so the back of the assembly
# stands 40.94 mm tall instead of 34.58. Nothing above Z=0 moved to pay for it -- the wedge grew
# downward and the internals rode it, exactly as the "add, never cut" rule intends.
#
# It also roughly doubles the band of bottom case visible at the north, 7.6 -> 14.2 mm. THAT IS
# INTENDED: it reads as a tapered plinth under the north half. Do NOT "fix" it by lifting
# SEAM_NORTH_RISE_FRAC -- that dial is held at 0.0 for a reason of its own (see its block), and
# at this angle it would make the north look worse, not better.
TENT_ANGLE_DEG   = 6.0   # deg; typing angle the wedge stands the case at
TENT_WEDGE_MIN_H = 1.0   # mm; wedge thickness at the south (the thin end)

# ---- Where the two cases hand over: the visible parting line ----
# Like the reference, the TOP case does not stop at Z=0 all the way round. Over the southern
# stretch its skin carries on down to just above the desk, so the front of the keyboard reads
# as one piece over a reveal so narrow it looks like none (TENT_SKIRT_LIFT, below). It lifts
# away over the middle, where the bottom case shows at its widest, and comes back down below
# Z=0 over the REAR so the band closes again -- see SEAM_WAVE_KNOTS and SEAM_NORTH_RISE_FRAC.
#
# Seen from the side with the case standing, that gives the reference's profile exactly: flat
# along the desk at the front, a sweep up, then a long run that rises at the tilt angle. That
# last run needs no geometry -- it IS the Z=0 plane, which slopes at TENT_ANGLE_DEG once the
# case is standing on its wedge. Only the first two stretches are built.
#
# The handover costs NO height. The skin drops into space that already exists between Z=0 and
# the tent plane, so the envelope is unchanged.
#
# The two joins are swept, not kinked (TENT_SEAM_RAMP_FRAC controls how drawn-out): the profile
# leaves the desk-parallel run tangentially and arrives at Z=0 tangentially.
# TENT_SEAM_SOUTH_FRAC is THE dial for this: 0.0 = the skin comes down only at the very
# front edge, 1.0 = it would run the whole way. Both ends of that range are accepted
# in principle, but the usable ceiling is lower in practice -- the sweep has to finish before
# the +Y relief bump (see the TENT_SEAM_Y2 guard, which computes the ceiling and reports it).
TENT_SEAM_SOUTH_FRAC = 0.36   # fraction of depth where the top case rides the desk
TENT_SEAM_RAMP_FRAC  = 0.64   # fraction of depth the wave takes to climb and come back down

# How steeply the ramp is still falling when it reaches the back edge, as a MULTIPLE of the
# desk's own slope. Above 1.0 the line drops faster than the desk does, which is the condition
# for the visible band to still be narrowing at the very back.
#
# It exists because the ramp used to arrive horizontally onto a flat rear run. That looked
# harmless and was not: the desk keeps falling away under a level line, so the band re-opened
# over the last stretch and the wave turned back up right at the end -- the one thing the
# reference's sweep never does. It rises, peaks, and descends all the way out.
#
# NOT A FREE DIAL ANY MORE. Since the tail became a shoulder followed by a STRAIGHT run (see
# SEAM_WAVE_KNOTS), the end tangent has to be the straight run's own gradient or the spline
# curves out of the line it just spent 40 mm establishing. It is therefore derived:
#     m * (crest_z - SEAM_NORTH_RISE_Z) / ((1 - SEAM_WAVE_CREST_U) * OUTER_DEPTH) / tan(TENT_ANGLE_DEG)
# USED TO BE LEFT AS A LITERAL (2.27) because crest_z came from re-reading the built spline, which
# needed this value to exist first -- a circular recipe that could only run once. Re-anchoring the
# tail model on the crest KNOT instead of the spline (see the WAVE block below) breaks that
# circle, so this is now computed alongside SEAM_WAVE_KNOTS in the derived-seam block further
# down, from the same crest_z and fall. Both live there because both need TENT_RISE /
# TENT_WEDGE_MAX_H, which are not in scope yet at this point in the file.

# ---- The REVEAL: the two shells do not touch, and the gap is the design ----
# The reference's parting line is not one line, it is TWO -- the top case's lower edge and the
# bottom case's upper edge -- with a recessed shadow between them. Measured off the reference's
# own elevation, that gap holds ~22 px against a 434 px case height, i.e. about 5% of the case,
# and it is CONSTANT over the back two thirds. Near the front it appears to swallow the whole
# band, but that is not the gap growing: it is the bottom case running out, leaving nothing
# below the gap at all.
#
# So this is one number, measured straight down from the parting line, and the lens shape falls
# out of the geometry rather than being drawn: the bottom case exists exactly where the visible
# band is taller than the reveal, which starts partway up the ramp and runs to the back edge.
# That is what "the bottom matches the top from where the top leaves the ground to the north
# end" means in practice.
SEAM_REVEAL_H = 2.0   # mm; vertical gap from the parting line down to the bottom case's top edge

# ---- FLUSH, not flared, and there is no dial for it ----
# The old bottom sat SEAM_SKIN + SEAM_FIT_CLEAR (2.2 mm) INSIDE the skin -- the "skinny" look --
# so every bit of bottom case on show was a recess. The fix for that is to put the bottom on the
# TOP'S OWN SECTIONED OUTLINE (tub_outline_face) and extrude it straight down, which makes the
# two shells share one lateral surface exactly rather than approximately.
#
# A FLARE WAS TRIED HERE AND IS NOT COMING BACK. The bottom used to stand SEAM_FLARE_MAX (1.5 mm)
# proud of the skin, leaning out as it fell. Measured below the band's own top edge -- which
# follows the wave -- that makes the outer offset a function of BOTH Y and Z, and a concentric
# offset can only vary with Z. So the shell had to be stacked out of ~36 Y-slabs, every boundary
# a real edge: 304 faces on the band, ~7 visible vertical divisions down the east wall, and
# 7.1 s to build. Four separate attempts to loft it as one surface instead all failed on OCC
# (periodic splines refused; closed-but-not-periodic lofted to one face but self-intersected, so
# booleans against it returned 0 mm^3 and then 268019 mm^3 from an intersection).
#
# Flush costs nothing and removes the whole problem: the band is one prism cut by two tools,
# 29 faces, 0.23 s, and the entire swoosh is a SINGLE face. The reference this case is drawn
# from is flush too -- zoomed on its nose and its rear, the two shells' faces are coplanar and
# the swoosh is the reveal gap, not a proud lip.
#
# So: no SEAM_FLARE_* constants. If a proud base is ever wanted again, the only version that
# stays a single prism is a CONSTANT offset applied to the same outline -- never one keyed to
# depth below the parting line.

# ---- The WAVE: the shape the ramp takes between those two runs ----
# The ramp used to be a single spline hump -- two endpoints and two tangents, monotonic by
# construction, so the visible band of bottom case could only ever WIDEN going north. Against
# the reference that read as unfinished: a skirt that stops rather than a shape that resolves.
#
# The reference's bottom case is a LENS seen from the side. Pinched to nothing at the front,
# swelling to a crest around two-thirds back, then easing again. Reproducing that needs a curve
# family the two-point spline cannot express, so the ramp is now a through-fit spline over the
# knots below and the endpoints/tangents are unchanged around it. Everything else about the
# profile is as it was: one Y-Z sketch, extruded across X, a function of Y alone.
#
# WHERE THESE NUMBERS COME FROM, and how much to trust them. Digitised off a CAD side elevation
# of the reference board plus a photograph of the real product, then rescaled to this case's
# 126 mm depth. Two rounds: the first read the zero-reveal front as ending at u=0.19, which
# spliced across a V-notch in the drawing at x~1170 px. That notch is the reference's own front
# knife-edge, so the front runs to u=0.36 and the rise is compressed into ~35% of the depth
# rather than 53%. The crest's POSITION survived both reads and an independent re-extraction by
# a different method (scipy find_peaks vs. a dark-run threshold), and the crest is visible on
# the painted blue/white shell boundary in the photograph -- it is real geometry, not a shading
# artifact of the render.
#
# WHAT IS NOT MEASURED: nothing images the reference's rear 18%, so where the wave lands north
# of u=0.82 is this project's decision, not the reference's. It is held at SEAM_NORTH_RISE_Z
# (i.e. Z=0), which is what the north has been since the parting line was dropped back there.
#
# UNITS, and this is the part that matters. Each knot is (u, band), where u is a fraction of
# OUTER_DEPTH and `band` is the VISIBLE HEIGHT OF BOTTOM CASE there, as a fraction of
# TENT_WEDGE_MAX_H -- the bottom case's full height at the back. Not local Z, and not millimetres.
#
# Local Z was the obvious choice and it was wrong. The sketch is drawn in local Z, so storing it
# that way saves a conversion; but local Z bakes in the tent angle the numbers were measured at,
# and the desk is what the shape is measured FROM. Held in local Z at 6 deg, the table put the
# crest 2.55 mm through the desk when the angle was swept to 3 -- a table that only means what it
# says at one angle. Millimetres above the desk fail the other way: the band cannot be 13.6 mm
# tall on a 7.6 mm wedge, so at a shallow angle the crest is driven above SEAM_LEDGE_Z and eats
# the tub. As a fraction of the wedge's own height it is scale-free, which is what "the bottom
# case looks like a lens" actually means. The conversion back is one line in _seam_sweep_params.
#
# THE REAR HALF OF THIS TABLE IS NOT THE REFERENCE'S, it is this project's answer to a problem
# the reference solves off-camera. Nothing images the reference's rear 18%, and a wave that just
# stops leaves the band re-opening to the full wedge height at the back (14.24 mm), wider than
# the crest -- a ripple, not a lens. The knots from u=0.820 carry the line back DOWN through Z=0
# so the top case's skin descends again at the rear and the band keeps closing. See
# SEAM_NORTH_RISE_FRAC, which is negative for the same reason and sets where this lands.
#
#   u       band      -> at 6 deg: mm above desk   local Z    what it is
# (table below is at SEAM_WAVE_BAND_SCALE=1.02 -- the digitised bands are printed BEFORE that
#  dial's 1.02x, so they read as the ones actually traced off the reference; regenerate this
#  table, don't hand-edit it, if either the scale or the digitised base points move.)
#   0.360   (run)                   0.30           -5.47      end of the south run (computed)
#   0.406   0.0716                  1.04           -5.34      the front knife-edge opening up
#   0.485   0.2992                  4.35           -3.08
#   0.558   0.6159                  8.95           +0.56      crosses Z=0 -- eats pocket wall above
#   0.598   0.7690                 11.17           +2.25
#   0.670   0.9459                 13.74           +3.87      CREST in local Z (the digitised one)
#   0.700   (model)                14.07           +3.80      first tail knot, off the model
#   0.740   (model)                14.32           +3.52      easing; visible band still widening
#   0.780   (model)                14.33           +3.00      crest in the VISIBLE BAND, not local Z
#   0.820   (model)                14.11           +2.25
#   0.860   (model)                13.65           +1.27      still easing; about to re-cross Z=0
#   0.900   (model)                12.99           +0.07      rear skirt: nearly back below Z=0
#   0.950   (model)                12.10           -1.48
#   1.000   (end)                  (n/a)           -3.02      the BACK EDGE, and still falling
# THE TAIL KNOTS (u > 0.67) ARE NOT DIGITISED POINTS, they are a fitted curve, and that is a
# deliberate difference from the climb above them. The climb's knots are read off the reference
# directly. The tail's could not be: the reference's whole post-crest descent is 49 px in a
# 3186 px image, so tracing noise is ~1 px = 2% of the drop and the individual points are mush.
#
# What survives the noise is the CHARACTER, and it is not an arc. Traced column by column, the
# reference holds almost flat for the first third past the crest -- 12% of its total drop in the
# first 30% of the run -- and then descends on a near-constant gradient the rest of the way. A
# shoulder, then a straight. The old knots traced a symmetric arc instead: steepest in the
# middle, easing at both ends, already twice as far down as the reference by 30% of the run.
#
# So the tail is generated from a model fitted to the trace rather than from the trace:
#
#     drop(s) = m * s^2 / (2*s0)      for s <= s0        (gradient ramps linearly 0 -> m)
#     drop(s) = m * (s - s0/2)        for s >  s0        (gradient holds at m)
#     s = fraction of the run from the crest to the back edge, drop = fraction of the total fall
#     s0 = 0.65 (the shoulder), m = 1/(1 - s0/2) = 1.4815 (the straight-run gradient)
#
# Fitted at rms 0.028 of the drop against the trace, near its 0.020 noise floor. A power-law
# family fits marginally better (0.018) but describes a curve that steepens forever and is never
# straight, so it loses the one feature this change exists to reproduce -- and the difference is
# 0.07 mm on a 6.63 mm fall, well under the print. The shape was chosen, not the residual.
#
# Knots are placed ON that model at even u, then the through-fit spline is checked back against
# it: max error 0.076 mm, rms 0.056 mm. Move the model, regenerate the knots -- do not hand-edit
# them, or the spline and the law it came from will drift apart.
#
# THE CLIMB IS THE MEASURED BASE -- everything above this line describes it, and it never changes
# except by SEAM_WAVE_BAND_SCALE (see the derived-seam block, further down) multiplying all five
# band values by the same factor to raise the whole lens without touching their relative shape.
# u=0.670 IS the digitised crest; scaling it is what "raise it from the middle" means here.
SEAM_WAVE_CLIMB_KNOTS = (
    (0.406, 0.0716),
    (0.485, 0.2992),
    (0.558, 0.6159),
    (0.598, 0.7690),
    (0.670, 0.9459),
)
# THE TAIL IS NOT HERE ANY MORE. It used to be six more literal knots below this line, generated
# once from the model and pasted -- exactly the "do not hand-edit" trap, because a paste cannot
# regenerate itself when SEAM_WAVE_BAND_SCALE moves the crest it is anchored to. SEAM_WAVE_KNOTS
# (climb + tail together, what every consumer actually reads) is assembled in the derived-seam
# block near SEAM_WAVE_Y: the tail model needs TENT_RISE and TENT_WEDGE_MAX_H, which do not exist
# yet at this point in the file.

# ---- How far the skirt stops SHORT of the desk: the reveal ----
# TENT_SEAM_SOUTH_FRAC dials the skirt's LENGTH (how far north it reaches). This dials its
# DEPTH: the whole bottom edge lifts by TENT_SKIRT_LIFT, so instead of landing on the tent
# plane the skin floats above it and a band of bottom case shows underneath. That band IS
# this number at the south, widening northward as the sweep climbs away from the plane.
#
# It is not only cosmetic. At 0.0 the skirt's underside is COPLANAR with the wedge's ground
# face, so two separately-printed parts share the desk contact and whichever comes out proud
# decides how the keyboard sits. Lifting the skirt hands ground contact back to the wedge
# alone -- the part that ground_face() chamfers and that the foot seats are cut into.
#
# Costs no height either way: the skirt only ever fills space between Z=0 and the tent plane.
#
# The ceiling is TENT_WEDGE_MIN_H -- lift the skirt that far and its bottom edge reaches Z=0
# at the south, i.e. there is no skirt left there at all. TENT_SKIRT_LIFT_MAX backs off far
# enough to keep a real band of skin rather than a feather edge. To show MORE bottom case at
# the front than that allows, the wedge itself has to get thicker at the south
# (TENT_WEDGE_MIN_H), and that one does cost height, 1:1.
# 0.3 rather than the 0.5 it was, because the wave wants the front to read as ZERO reveal --
# the reference's bottom case is pinched to a knife edge there and the two shells look like one
# piece. Literal zero was on the table and was rejected: at 0.0 the skirt's underside is
# coplanar with the wedge's ground face and the two printed parts fight over how the case sits
# (see TENT_SKIRT_CLEAR_MIN). 0.3 is the smallest reveal that still leaves ground contact
# unambiguously with the wedge, and at arm's length it reads as none.
TENT_SKIRT_LIFT = 0.3   # mm; bottom case visible below the skin at the front

assert 0.0 <= TENT_SEAM_SOUTH_FRAC <= 1.0, (
    f"TENT_SEAM_SOUTH_FRAC must be a fraction of the depth, 0.0-1.0; got {TENT_SEAM_SOUTH_FRAC}")
assert TENT_SEAM_RAMP_FRAC > 0.0, "the sweep needs a non-zero run"

# ---- The floor under the reveal: ground contact belongs to the wedge, full stop ----
# TENT_SKIRT_LIFT is a STYLING dial -- how wide a band of bottom case shows. This is the
# PHYSICAL invariant underneath it, and the two are deliberately separate numbers.
#
# They were the same number once, and that was a defect. Every guard on "the skin never
# touches the desk" derived its threshold FROM the lift (worst > TENT_SKIRT_LIFT - 0.06), so
# turning the lift down turned the guard down with it and at 0.0 the assertion read
# worst > -0.06 -- it went trivially true at exactly the moment it should have fired. An
# assertion has to be anchored to the physical thing it protects, never to the dial that can
# violate it.
#
# 0.2 mm is the floor, not a target: two FDM parts printed to a nominal contact plane vary by
# about a layer, so anything under that and whichever comes out proud decides how the keyboard
# sits. The wedge must own the desk alone -- it is the part ground_face() chamfers and the part
# the foot seats are cut into.
TENT_SKIRT_CLEAR_MIN = 0.2   # mm; least the skin may ever come to the tent plane, at any dial

TENT_SKIRT_MIN_H = 0.3   # mm; skin that must survive at the south so the skirt is not a feather edge
TENT_SKIRT_LIFT_MAX = TENT_WEDGE_MIN_H - TENT_SKIRT_MIN_H
assert TENT_SKIRT_CLEAR_MIN <= TENT_SKIRT_LIFT <= TENT_SKIRT_LIFT_MAX, (
    f"TENT_SKIRT_LIFT={TENT_SKIRT_LIFT} is outside its band [{TENT_SKIRT_CLEAR_MIN:.2f}, "
    f"{TENT_SKIRT_LIFT_MAX:.2f}]. Below the floor the skin starts sharing desk contact with the "
    f"wedge; above the ceiling it leaves only "
    f"{TENT_WEDGE_MIN_H - TENT_SKIRT_LIFT:.2f} mm of skirt at the south, a feather edge. To show "
    f"MORE bottom case at the front, thicken the wedge's thin end (TENT_WEDGE_MIN_H), which costs "
    f"height 1:1")

# ---- How high the parting line rides NORTH of the sweep: the riser ----
# North of TENT_SEAM_Y2 the parting line has always sat flat at Z=0, so the visible band of
# bottom case there is exactly the wedge: 4.1 mm at the sweep, 7.6 mm at the back. This dial
# lifts that line off Z=0 and up the wall, so more of the bottom case shows at the north.
#
# ONLY THE TUB IS CUT BACK. The bottom part's XY is untouched — plate and wedge keep the rim
# profile they always had, inset SEAM_SKIN + SEAM_FIT_CLEAR (2.2 mm) behind the skin. So the
# band this exposes is a RECESS, not a flush face: a 2.2 mm deep shadow reveal running the
# north of the case, getting taller as the dial climbs. Growing the bottom out to meet the skin
# instead was tried and rejected — it makes the bottom chase the tub's real footprint (the +Y
# relief bump and its fillet), and it changes the bottom's outline, which is not wanted.
#
# Expressed as a FRACTION of the bottom case's own top (SEAM_LEDGE_Z, the plate-rim top),
# because that is the real travel: at 1.0 the parting line lands exactly on the ledge and there
# is no tub skin left below it on that stretch. Costs no height — the line moves up an existing
# wall, it does not make the wall taller.
#
#   frac   rise    recess at the sweep   at the back    rabbet lap left (north)
#   0.00   0.00           4.10 mm          7.60 mm            6.30 mm   (as before)
#   0.50   3.15           7.25 mm         10.75 mm            3.15 mm
#   1.00   6.30          10.40 mm         13.90 mm            0.00 mm
#
# THE TOP OF THE RANGE GIVES UP THE NORTHERN RABBET, DELIBERATELY. The tub's skin below the
# ledge is what the plate rim slots into; lift the line to the ledge and that pocket wall is
# gone everywhere north of the sweep, leaving the lap only over the southern stretch. The joint
# still locates — the 5 standoff screws set XY registration and the rabbet was never what
# clamped it — but the lap stops helping there. Chosen with that understood; the range is NOT
# capped short of it.
#
# The SOUTH is untouched by this dial. Over the southern run the skin still descends to
# TENT_SKIRT_LIFT above the desk and the bottom stays inset behind it — see that block above.
#
# ---- THE RANGE NOW GOES NEGATIVE, AND THAT IS WHERE IT IS SET ----
# Everything above describes lifting the line UP the wall, which was the only direction that
# made sense while the ramp was a monotonic sweep: the line arrived at the north from below and
# the dial decided how high. It was held at 0.0 because lifting it read as an unfinished skirt —
# the bottom stays inset 2.2 mm, so a lifted skin edge floats over a shadow slot with nothing
# flush behind it.
#
# The wave changed the question. Its band crests around u=SEAM_WAVE_CREST_U and eases, and for
# that to read as a lens rather than a ripple the band has to keep narrowing to the back. It
# cannot: the band at the back is at least the wedge's height there (14.24 mm) for any parting
# line at or above Z=0, which is wider than the crest's own 13.74 mm (at SEAM_WAVE_BAND_SCALE=
# 1.02; it moves with that dial). A crest tall enough to beat 14.24 mm needs local Z +4.37 there
# and leaves 1.91 mm of rabbet lap, still under the 2.0 floor. So the line has to go BELOW Z=0 at
# the back — the top case's skin descends again there, exactly as it does at the front, and the
# lens closes. Negative frac is that, as a fraction of the same SEAM_LEDGE_Z travel.
#
# THIS COSTS NO RABBET. Below Z=0 there is no pocket wall to give up; the lap is bounded by how
# high the line climbs, and going down does not touch it. What it costs instead is a second
# stretch of skirt band, at the rear, which is why skirt_extension had to stop being a polygon
# offset and start sectioning the tub — the +Y relief bump lives back there.
#
#   frac    line at the back    band at the back    what it reads as
#   +1.00   +6.30 mm            20.54 mm            plinth, rabbet gone north
#    0.00    0.00 mm            14.24 mm            the old flat line; band widest at the back
#   -0.29   -1.83 mm            12.41 mm            lens nearly closed
#   -0.37   -2.30 mm            11.94 mm            lens closed: back is narrower than the crest
SEAM_NORTH_RISE_FRAC = -0.48   # <0 = line drops below Z=0 (rear skirt), 1.0 = up to the ledge
SEAM_NORTH_RISE_Z    = SEAM_NORTH_RISE_FRAC * SEAM_LEDGE_Z   # derived; the actual height

# The ceiling is stated here; the FLOOR is a function of the tent (it is the desk, with the same
# clearance the front skirt keeps) and cannot be computed until TENT_WEDGE_MAX_H exists — see
# SEAM_NORTH_RISE_FRAC_MIN further down, beside the other derived seam numbers.
assert SEAM_NORTH_RISE_FRAC <= 1.0, (
    f"SEAM_NORTH_RISE_FRAC={SEAM_NORTH_RISE_FRAC} is a fraction of SEAM_LEDGE_Z={SEAM_LEDGE_Z}. "
    f"There is nothing sane above 1.0 — the line would pass the plate rim's own top and the "
    f"bottom case would have no material left to show")

# The ceiling here is a PRACTICAL band, not a derived limit, and it is worth saying so rather
# than implying a calculation that does not exist. The geometry has no hard stop: every part of
# the wedge path scales with tan(angle) and stays valid -- the tent plane never reaches Z=0
# inside the footprint (it starts at -TENT_WEDGE_MIN_H), and the seam cutter's southern guard
# branch is satisfied at every angle (it reduces to -TENT_SKIRT_LIFT < 0, which is why
# test_the_seam_cutter_never_reaches_above_z0 passes rather than merely happening to).
#
# What does bind is use, not maths. Rise is OUTER_DEPTH * tan, so each extra degree costs about
# 2.2 mm of back height at this depth: 7 deg puts the back at 43.45 mm, 10 deg at 51.2 mm, and
# past that the front lip and the north plinth stop being a keyboard and start being a doorstop.
# 10.0 is where that judgement lands. Raising it further is allowed but should come with a
# reason, the way this one does.
assert 0.0 < TENT_ANGLE_DEG <= 10.0, (
    f"TENT_ANGLE_DEG={TENT_ANGLE_DEG} is outside the practical 0-10 deg band; rise is "
    f"OUTER_DEPTH*tan(angle), so the back height grows ~2.2 mm per degree")
# The rest of the guards need OUTER_DEPTH and FOOT_DEPTH, both defined further down; they sit
# with the envelope. Search for TENT_RISE.

# ---------- Encoder plateau (TOP part, around EC11 rotary encoder) ----------
# The EC11 body is a ~12 mm box that mounts through the plate's encoder cutout
# (~12.7 mm). On the sandwich TOP part a single-body PLATEAU caps it: one low
# mound, hollow inside to clear the box, with a closed roof and a plain shaft
# hole. The plateau leaves the cover tangentially (concave ogee foot) and rounds
# over at the top edge — no hard step, no second tier. The box is hidden; the
# bushing + 6 mm shaft exit through the shaft hole.
#
# ENCODER_BODY_H is a PCB datum, not a plate one — the encoder is soldered to the
# PCB, so its height can't change when the plate does. It used to be the other
# way round (PLATE_TOP_Z + a measured "proud" offset), which meant every plate
# fix silently re-derived a different box height — 6.6 at MX_BODY_CLEAR=3.0, 7.0
# at 3.7, whatever the plate happened to be that week, independent of the actual
# hardware. Two independent sources for the real number (a vendor listing's own
# dimensioned photo — case top to the PCB-face color boundary, ≈5.9mm — and a
# second vendor's drawing giving 6.5mm for the same span) put it at 6.0–6.5mm.
# Held at 7.0 anyway, above both readings: the plateau's clearance over the box
# matters more than shaving the margin to match an estimate, and reading the
# case a little short costs nothing while reading it a little tall risks the
# same collision class as the encoder-plateau fix this datum already needed
# once (commit 7a54949).
ENCODER_BODY_H         = 7.0   # mm; PCB top -> EC11 box top. See note above.
ENCODER_BODY_TOP_Z     = PCB_TOP_Z + ENCODER_BODY_H          # box top (cavity must clear this)
ENCODER_BODY_PROUD     = ENCODER_BODY_TOP_Z - PLATE_TOP_Z    # derived, informational only: how far
                                                              # the box stands above the CURRENT plate
ENCODER_SHELL_WALL     = 1.5   # mm; plateau side-wall thickness (thin → smaller footprint)
ENCODER_SHELL_ROOF     = 1.5   # mm; closed top-face thickness
ENCODER_SHELL_CAVITY_CLEAR = 0.4  # mm/side; cavity grows past the plate cutout so the ring
                                  # overlaps solid cover material (robust fusion). ALSO the
                                  # membrane's encoder-window margin (top_cover.build_top_cover),
                                  # so the window and the cavity are ONE aperture: the window
                                  # used to be the exact cutout (12.72 mm), which left the
                                  # 12.4 mm EC11 body 0.07 mm/side on its −Y face and would
                                  # print interference-fit. The window is invisible under the
                                  # 16.5 mm plateau, so widening it costs nothing.
ENCODER_SHAFT_HOLE_DIA = 7.5   # mm; shaft hole: clears the 6 mm shaft + 7 mm bushing
ENCODER_PLATEAU_H      = 4.5   # mm; plateau height above the cover surface
ENCODER_SHELL_TOP_Z    = COVER_TOP_Z + ENCODER_PLATEAU_H            # derived; plateau top, tracks COVER_TOP_Z
ENCODER_CAVITY_TOP_Z   = ENCODER_SHELL_TOP_Z - ENCODER_SHELL_ROOF   # derived; roof underside (clears box) —
                                                                     # do not hardcode a number here, it has
                                                                     # already gone stale once (was "19.0")
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

# ---------- The pins are screw bosses, NOT a plate seat ----------
# The switch plate's height is set by the SWITCHES (PCB top + MX_BODY_CLEAR) — a hardware datum
# the case cannot argue with. The standoff pins used to top out at exactly PLATE_SEAT_Z, making
# them a SECOND datum for the same surface. Two datums for one face is an over-constraint, and
# it only resolves if MX_BODY_CLEAR is exact; it was out by 0.4-1.0 mm, so the pins and the
# switches fought and the case would not shut.
#
# The pins are now RECESSED below the plate. They carry the M2 thread and nothing else: the
# screw pulls the cover down onto the plate and the plate onto the switch shoulders, which is
# the load path that already existed in the hardware. Keypress force never runs through the
# plate (the switch body bottoms on the PCB), so the pins support nothing structural.
#
# Sized for the WORST case, which is MX_BODY_CLEAR being too HIGH: if the true gap is 3.4 the
# plate sits 0.3 below nominal and a flush pin would spear it. 0.6 covers that 0.3, plus ~0.3
# of FDM Z error on a printed pin — i.e. the case still assembles for any true gap from 3.1 up.
# There is no penalty at the other end: at a true gap of 4.0 the pin simply sits 0.9 clear.
# The tap bore follows the pin down, so thread engagement (STANDOFF_TAP_DEPTH) is unchanged;
# the screw crosses 0.6 mm more air, which is inside M2 head-to-thread slack.
STANDOFF_PIN_RECESS = 0.6  # mm; pin top below PLATE_SEAT_Z — the plate must never touch it

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
#                            nano board's +Y edge. The jack stops 0.57 mm short of the
#                            canopy north wall's inner face (BAY_NORTH_INNER_Y) — only the
#                            plug bridges the wall. (The pcb_phantom stub depth uses this.)

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
# Here the jack mouth sits 3.32 mm behind the canopy's outer face, so a straight shell-sized
# hole leaves 3.33 mm of engagement (50%) AND blocks the overmold outright — that port would
# not take a standard cable at all. The fix is a stepped bore: a wide outer POCKET that
# admits the overmold for part of the wall, then a narrow NECK sized for the shell.
# (That travel was 4.41 mm / 2.24 mm of engagement while the board's north face was anchored
# to the wrong pin. Correcting the anchor moved the jack 1.09 mm toward the wall, which is a
# problem for the CASE — see BAY_NORTH_INNER_Y — but a gift to the plug.)
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
# ---- SK12D07VG3 Z stack -----------------------------------------------------------
# Hoisted above the scoop block because the scoop's Z is derived from it. These three are
# the RULER every slide-switch clearance check is measured against, so a wrong value here
# does not make a test fail — it makes a real collision invisible.
#
# A caliper pass in Aug 2026 read 5.0 / 2.4 instead of 4.3 / 1.5 and was reverted at the
# owner's direction. That revert is now confirmed: the genuine SK12D07VG3 manufacturer spec
# sheet (ShenZhen ShouHan — the actual part, not a generic clone-envelope listing) gives a
# frame height of 4.0-4.7mm above the PCB (4.3 sits inside it) and a paddle thickness of
# exactly 2.0mm. The datasheet's paddle Z-band (~1.0-3.35mm, paddle centered at mid-body) is
# close to 1.5-3.5mm from NUB_BASE=1.5. The 5.0/2.4 caliper reading would put the paddle
# mostly above the frame top, which does not match a part whose paddle is drawn at mid-body
# height — that reading was the bad one. Datasheet also confirms this is a lateral paddle
# (protrudes sideways out of the frame, not upward off the top), matching why the model
# reaches it through a side-wall window rather than a top window.
SLIDE_ACTUATOR_BODY_H       = 4.3  # mm; datasheet-confirmed — frame height above PCB top (spec: 4.0-4.7)
SLIDE_ACTUATOR_NUB_BASE     = 1.5  # mm; datasheet-confirmed (close fit) — paddle underside above PCB top
SLIDE_ACTUATOR_NUB_H        = 2.0  # mm; datasheet-confirmed exact — paddle thickness. The paddle top
#                                    (PCB_TOP_Z + NUB_BASE + NUB_H) rides on this.

SLIDE_SWITCH_W           = 6.0   # mm; slide actuator nominal width (reference)
SLIDE_NUB_Z              = PCB_TOP_Z + SLIDE_ACTUATOR_NUB_BASE + SLIDE_ACTUATOR_NUB_H / 2  # lever centre Z; tracks the PCB
SLIDE_SCOOP_W            = 10.0  # mm; scoop width in Y (wider than its Z depth)
# 1.4 below the lever centre: the window's lower edge sits under the lever so a fingernail can
# catch it. Derived rather than pinned, but note the coupling — it moves the moment the lever
# height does, which is a geometry change riding in on a measurement. If SLIDE_ACTUATOR_NUB_BASE
# is ever re-measured, size this floor deliberately instead of letting it follow.
SLIDE_SCOOP_FLOOR_Z      = SLIDE_NUB_Z - 1.4  # mm; scoop floor = 11.5
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
# underside so the 1.0 mm lid is NOT perforated.
#
# The cap is sized off the CAN, not off the rim — see SLIDE_ACTUATOR_TOP_Z below for why that
# distinction is the whole ballgame. (The old note here read "the can top is 12.2, leaving
# 0.3 mm of cover above it" — stale: 12.2 came from FLOOR_THICKNESS 3.8.)
#
# These are STRUCTURAL mirrors of the datasheet-derived can/nub dims. The pcb_phantom
# _SK12_* dims are marked "phantom-only, not structural" — do NOT import them here;
# structural geometry owns its own values. The placement (registration off SW31) is
# shared cleanly via pcb_geometry.slide_switch_placement / rotate_2d, so the cavity
# tracks the switch exactly without coupling structure to the phantom module.
SLIDE_ACTUATOR_BODY_W       = 4.4  # mm; metal can width (perp. to pin row, local Y)
SLIDE_ACTUATOR_BODY_L       = 4.0  # mm; metal can length (along pin row, local X)
SLIDE_ACTUATOR_NUB_L        = 3.5  # mm; actuator nub length along pin row (local X)
SLIDE_ACTUATOR_NUB_D        = 3.0  # mm; actuator protrusion beyond the can edge (local -Y)
SLIDE_ACTUATOR_PIN_CENTER_X = 2.0  # mm; can centre offset from footprint origin (local X)
# BODY_H / NUB_BASE / NUB_H are defined with the measured Z stack ABOVE — the scoop needs them
# first. They are the same OWNED structural values this block has always carried, only hoisted.
SLIDE_ACTUATOR_PAD          = 0.5  # mm; clearance grown on every X/Y face of the pocket
SLIDE_ACTUATOR_FLOOR_Z      = 0.0   # mm; pour depth for the drop-in channel (decoupled from the
#                                      seam — the tub is now open below this anyway; kept as a
#                                      registered clearance floor for the switch can/nub)
# Pocket cap. It tracked MAIN_RIM_Z − 0.5, which is a datum the CAN knows nothing about: the
# pocket is over the switch, not over the plate, so tying it to the plate stack made its
# clearance an accident of MX_BODY_CLEAR. That accident was 0.9 mm of INTERFERENCE at the old
# 4.3 mm can, and only ~0.15 mm of air at MX_BODY_CLEAR = 3.40. Now derived from the can it
# actually has to clear, and clamped so the lid keeps at least SLIDE_ACTUATOR_LID_MIN of solid.
SLIDE_ACTUATOR_CAP_CLEAR    = 0.3  # mm; air above the measured can — an FDM face lands ±0.2
SLIDE_ACTUATOR_LID_MIN      = 0.5  # mm; solid cover that must survive above the pocket
SLIDE_ACTUATOR_TOP_Z        = min(
    PCB_TOP_Z + SLIDE_ACTUATOR_BODY_H + SLIDE_ACTUATOR_CAP_CLEAR,  # clear the can
    COVER_TOP_Z - SLIDE_ACTUATOR_LID_MIN,                          # never perforate the lid
)

# ---------- Battery JST at J2 (S2B-XH-A-1, side entry) ----------
# THE PART THE MODEL COULD NOT SEE. This is the wireless build's battery connector, and until
# now it existed nowhere except a sentence: canopy.py's ramp-foot comment claims the slip
# "starts climbing early enough to clear the JST beneath it" — an explicit clearance promise
# with no constant, no phantom and no test behind it. Nothing ever checked it, and the case
# would not shut.
#
# It is invisible to the data too, and that is not the CPL's fault. data/raw/CPL-SofleKeyboard.csv
# is the shared Sofle v2 placement file (U1's ProMicro footprint is what a nice!nano drops into),
# and it lists J2 as a generic Conn_01x03_Female / PinSocket_1x03_P2.54mm_Vertical. The part
# actually soldered there is a 2-circuit JST XH. No footprint, no envelope, and above all no
# HEIGHT — so no data-driven check could have caught this. Only a datum can.
#
# HEIGHT: 6.5, MEASURED, and the datasheet agrees at (6.1). Read this before touching the number,
# because it was wrong once and the error is instructive.
#
# eXH.pdf's side-entry pages carry two figures side by side, and they are DIFFERENT VIEWS:
#   * LEFT is a plan view — "the PC board layout figure shown is viewed from the connector
#     mounting surface". Dimension (C) lives here, running from the pin-hole row to the "Side
#     edge of header on PCB". C is therefore a FOOTPRINT dimension in the plane of the board.
#     It is what distinguishes S2B-XH-A (C:9.2) from S2B-XH-A-1 (C:7.6);
#   * RIGHT is the side elevation. There (14.3), 4.5 and 7 run HORIZONTALLY, and the single
#     vertical dimension is (6.1). That is the height above the PCB.
#
# This constant was first set to 7.6 by reading C as a height — a plan-view footprint number used
# as an elevation. It survived because 7.6 was plausible and every check downstream was built on
# it, so the model was self-consistent and confidently wrong. The owner's calipers caught it: 6.5
# against the datasheet's 6.1, and the two agree. The vendor listing is wrong in the other
# direction — it advertises "assembled height 9.8 mm", which is the TOP-ENTRY (B2B) figure (header
# 7.0 plus a mated XHP-2 sitting on top of it), meaningless for an S-prefix side-entry part.
#
# The lesson is not "read more carefully". It is that a dimension letter is worthless without the
# view it was drawn in, and a datasheet that puts a plan and an elevation next to each other will
# hand you the wrong one without complaint.
#
# Above the PCB this fouled the cover no matter which figure was believed: the headroom at J2 is
# 6.70 mm and every candidate (6.1, 6.5, 7.6) needs more than that once JST_CLEAR is counted. That
# is what forced the move underneath, and it is why the wrong height did not change the decision.
#
# MOUNTED UNDER THE PCB, like the hotswap sockets. Standing on top it fouled the cover by
# 34.2 mm^3 (2.016 mm thick, Z 15.98..18.00) — the only hardware fouling either printed part. The
# fix is not to reshape the canopy around it but to move it out from under the canopy entirely,
# into a blind pocket in the floor. The fastback is then untouched, and the trough between the
# encoder plateau (underside 19.40, ends Y 59.80) and the ramp (19.20 by Y 69.0) stops mattering.
#
# WHICH WAY THE PLUG FACES IS A CLEARANCE DECISION, NOT A PREFERENCE. It enters from the NORTH so
# the wire run leaves north and turns east at case Y ~72. Routing south instead puts the wires
# 0.46 mm from the standoff at case (53.32, 58.79); north clears it by 10.46 mm.
#
# ALL THREE BODY DIMENSIONS ARE MEASURED on the installed connector (6.5 x 8.0 x 8.0). They
# replace a datasheet-derived set that was wrong in BOTH directions at once, which is the part
# worth remembering: the height ran 1.1 mm over and the length 1.5 mm over — harmless, they only
# spend floor — but the WIDTH ran 0.6 mm UNDER. At the earlier 7.4 the pocket came out 8.4 mm
# across for an 8.0 mm part: 0.2 mm a side, against an FDM face that lands +/-0.2. The pocket
# would very likely not have accepted the connector at all, and nothing in the model could have
# said so, because every check was built from the same wrong number.
#
# So: oversizing is NOT a substitute for measuring. Generous depth hid a tight width, and only a
# caliper on the real part separated them.
# PLACEMENT. JST_POS IS PIN 1, NOT THE BODY CENTRE — this footprint's CPL "Mid X/Y" is the origin
# pin, and SofleKeyboard-PTH.drl confirms a three-hole row running EAST from it at 2.54 pitch:
# case X 26.60 / 29.14 / 31.68, all at case Y 67.02. Centring the body on JST_POS (as this file
# first did) put it 2.5 mm west of the truth and short of its own third pin.
#
# The 2-circuit XH occupies two of the three holes. And it is a SIDE-ENTRY part: the pins leave
# the back of the shroud, so the body does not straddle the row — it runs off it, northward, which
# is the same direction the plug enters.
#
# EITHER PAIR WORKS, so the pocket must fit BOTH. The middle hole is B+ and both outer holes are
# GND, which makes the connector electrically reversible: it can sit on the west pair or the east
# pair and work the same. A pocket cut to whichever pair happened to be soldered first would turn
# a free choice into a permanent one, and the constraint is invisible from the geometry — nothing
# downstream could tell you the part was allowed to move. So the pocket spans the union of the two
# positions: 11.54 mm rather than 9.00, wider by exactly one pin pitch.
JST_POS       = (12.855, -48.735)  # PCB coords; the CPL's J2 row = PIN 1. Not the centre.
JST_PIN_PITCH = 2.54   # mm; the 1x03 footprint's pitch, read off the drill file
JST_MOUNT_W   = 0.5    # body centre for the WEST pair, in pitches from JST_POS (holes 1+2)
JST_MOUNT_E   = 1.5    # body centre for the EAST pair (holes 2+3)
#               No rotation constant: the CPL's 90 deg describes the 1x03 socket originally
#               footprinted at J2, not the XH re-soldered underneath. BODY_W/BODY_D below name
#               their case axes outright, so a stale placement angle has nothing to act on.
JST_BODY_H    = 6.5   # mm; MEASURED on the installed part. Datasheet corroborates: (6.1).
JST_BODY_W    = 8.0   # mm; MEASURED, across the circuits — lies along case X
JST_BODY_D    = 8.0   # mm; MEASURED, the mating axis — along case Y
JST_PLUG_RUN  = 6.3   # mm; how far the mated plug stands proud of the header. Datasheet-derived:
#                       side-entry ASSEMBLY length (14.3) minus the measured 8.0 body.
JST_WIRE_OD   = 1.9   # mm; JST's own max insulation OD. Two conductors run side by side.
JST_WIRE_BEND = 3.0   # mm; room past the plug for the leads to turn without being pinched
JST_CLEAR     = 0.5   # mm; air around the connector. Matches SLIDE_ACTUATOR_CAP_CLEAR's logic —
#                       an FDM face lands +/-0.2.
JST_BOTTOM_Z  = PCB_SEAT_Z - JST_BODY_H  # 1.20; PCB-anchored per the ENCODER_BODY_H fix (429adc9).
#                                          It hangs off the BOARD, so the floor that has to clear
#                                          it cannot be what defines its height.

# Pocket: a blind recess cut down from the floor's top face, exactly like the battery pocket.
JST_POCKET_PAD      = 0.5   # mm; per-side XY clearance around the connector envelope
JST_POCKET_FLOOR_Z  = JST_BOTTOM_Z - JST_CLEAR             # 0.70; pocket floor
JST_POCKET_DEPTH    = FLOOR_THICKNESS - JST_POCKET_FLOOR_Z  # 5.60; tracks the floor, as
#                                                             BATTERY_POCKET_DEPTH does
JST_POCKET_CORNER_R = 1.5   # mm; plan-corner fillet (battery uses 2.0; this pocket is smaller)

# Wire channel: JST pocket -> battery pocket. NOT optional. Only STANDOFF_SHOULDER_H (2.5 mm) of
# air exists under the PCB and the hotswap sockets already eat ~2.0 of it, so a 1.9 mm lead has
# nowhere to cross the switch field without a channel cut into the floor.
JST_CHANNEL_W       = 2 * JST_WIRE_OD + 1.2   # 5.0; two conductors side by side, plus slack
# Floor MATCHES the JST pocket rather than being sized to the wire. The two pockets are NOT the
# same depth — battery 4.30 (floor Z 2.00, set by BATTERY_FLOOR_BASE) against JST 4.50 (floor
# Z 1.80, set by the measured connector) — so the channel takes the DEEPER of the two. A wire then
# only ever steps DOWN into the channel and never up, at either end; matching the shallower would
# leave a 0.20 lip at the JST mouth for a lead to catch on.
JST_CHANNEL_FLOOR_Z = JST_POCKET_FLOOR_Z                     # 1.80; flush with the JST pocket
JST_CHANNEL_DEPTH   = FLOOR_THICKNESS - JST_CHANNEL_FLOOR_Z  # 4.50; derived, tracks the floor
# The run is ORTHOGONAL and HOOKED, not diagonal: out of the JST pocket heading NORTH, east along
# the top, then a long leg SOUTH, and into the battery pocket near its south-west corner. ~94 mm
# against the 27 mm a straight east run took and the 64 mm a diagonal took. The length IS the
# feature — the leads get real slack and a route that stays out of the middle of the switch field,
# rather than the shortest line between two points.
#
# The southward leg's X is set by the standoff at case (53.32, 58.79), which is the only thing
# either turn comes near: 44.0 clears it by 4.07 mm, and every millimetre east of that is spent
# straight off the margin (46.0 leaves 2.07, 47.0 leaves 1.07).
JST_CHANNEL_TOP_Y     = 90.0   # case Y of the northern leg, clear of the JST pocket's mouth
JST_CHANNEL_MID_X     = 44.0   # case X of the long southward leg — see the standoff note above
# The entry leg's centreline offset from the battery pocket's south wall. HALF THE CHANNEL WIDTH,
# derived rather than dialled, so the channel's south face lands EXACTLY on the pocket's south
# face and the two read as one continuous wall. At a free 3.0 the channel sat 0.5 mm north of it
# and left a visible jog at the junction — small, but it is a step in a wall a wire is pressed
# against, and it moves the moment JST_CHANNEL_W does.
JST_CHANNEL_BAT_INSET = JST_CHANNEL_W / 2

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
# at 4 corners, so 8 mm self-adhesive rubber feet locate there and the keyboard grips
# the desk (doesn't slide while typing). NOT deep — a shallow locating seat; the foot
# sits mostly proud below and lifts the case off the desk.
#
# Positions are in CASE coords, chosen on solid plate material clear of the irregular
# Sofle outline edges (the bottom-right corner is cut by the thumb cluster) and clear of
# the battery pocket. Subtracted BEFORE the left-mirror, so they track to the mirrored
# outline on the left half.
#
# WAS 10.0, AND THE SEAT DIAMETER IS WHAT DECIDES WHERE THE SNAP ARMS CAN GO — not the
# seam. At Ø10 the seats clip four of the nine relief slots: the north-east arm's root
# relief collides outright (-0.24 mm), and the two east arms and the north-west arm graze
# by 0.05-0.37 mm. At Ø8 the worst clearance across all nine is 4.94 mm, and the
# north-east arm reaches its intended barb position (x 128.90, between SW5 and SW6)
# instead of retreating 10 mm west. Moving a foot was tried on wip/snap-latches and did
# not survive; shrinking the seat is the cheaper fix and 8 mm feet are as common as 10.
FOOT_DIA   = 8.0    # mm, rubber-foot diameter → seat diameter
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

# How far the tent wedge climbs from its thin (south) end to its thick (north) end, and the
# total thickness of the bottom case at the back. Defined here because it needs OUTER_DEPTH.
TENT_RISE     = OUTER_DEPTH * math.tan(math.radians(TENT_ANGLE_DEG))   # 4.40 at 2 deg
TENT_WEDGE_MAX_H = TENT_WEDGE_MIN_H + TENT_RISE                        # 5.40 -> the case grows by this
assert TENT_WEDGE_MIN_H >= FOOT_DEPTH + 0.3, (
    "wedge too thin at the south to host a foot seat -- raise TENT_WEDGE_MIN_H")

# Where the top case leaves the desk, and where its skin gets back to Z=0.
TENT_SEAM_Y1 = TENT_SEAM_SOUTH_FRAC * OUTER_DEPTH                        # 63.0 at 0.50
TENT_SEAM_Y2 = TENT_SEAM_Y1 + TENT_SEAM_RAMP_FRAC * OUTER_DEPTH          # 85.7 at 0.50

# The ramp used to have to finish south of the +Y relief bump at y = OUTER_DEPTH - 20. That was
# never about the ramp: it was about the SKIRT the ramp drags below Z=0. The bump stands proud of
# the nominal outline offset and carries a corner fillet, and skirt_extension built its band from
# a polygon offset, so a band reaching the bump would have sat INSIDE the wall above it and left a
# step at Z=0 along the whole bump face. The limit fenced the skirt off from that region instead
# of solving it.
#
# skirt_extension now sections the TUB at Z=0 and projects that outline down, so the band IS
# whatever the wall above it is -- bump, fillet and all. The limit is therefore retired, which is
# what lets the wave carry a rear skirt at all. What remains is only that the ramp has to fit in
# the case.
TENT_SEAM_FRAC_MAX = 1.0 - TENT_SEAM_RAMP_FRAC
assert TENT_SEAM_Y2 <= OUTER_DEPTH, (
    f"TENT_SEAM_SOUTH_FRAC={TENT_SEAM_SOUTH_FRAC} puts the ramp's end at y={TENT_SEAM_Y2:.1f}, "
    f"past the back of the case at {OUTER_DEPTH:.1f}. With TENT_SEAM_RAMP_FRAC="
    f"{TENT_SEAM_RAMP_FRAC} the ceiling is {TENT_SEAM_FRAC_MAX:.2f} — lower the south fraction "
    f"or shorten the ramp")

# The rear parting line's floor: the desk, less the clearance the skin must always keep from it.
# Stated here rather than beside the dial because it needs the tent's own numbers.
SEAM_NORTH_RISE_FRAC_MIN = -(TENT_WEDGE_MAX_H - TENT_SKIRT_CLEAR_MIN) / SEAM_LEDGE_Z
assert SEAM_NORTH_RISE_FRAC >= SEAM_NORTH_RISE_FRAC_MIN, (
    f"SEAM_NORTH_RISE_FRAC={SEAM_NORTH_RISE_FRAC} puts the rear parting line at "
    f"{SEAM_NORTH_RISE_Z:.2f}, which is through the desk at the back ({-TENT_WEDGE_MAX_H:.2f}) or "
    f"inside TENT_SKIRT_CLEAR_MIN={TENT_SKIRT_CLEAR_MIN} of it. The floor at this tent angle is "
    f"{SEAM_NORTH_RISE_FRAC_MIN:.3f}")

# ---- Raising the wave: one dial, and the tail regenerated around it ----
# SEAM_WAVE_BAND_SCALE multiplies SEAM_WAVE_CLIMB_KNOTS' band values -- the whole of "raise the
# wave from the middle" is this one number, because the crest sits at the climb's own last knot
# (u=SEAM_WAVE_CREST_U). Scaling rather than adding an offset keeps the front knife-edge pinched
# (u=0.406 moves 0.0716 -> 0.0730 at 1.02x, i.e. +0.03 mm) and cannot introduce a second hump on
# its own, since it preserves the climb's monotone shape exactly.
#
# 1.02, NOT HIGHER. The lap-left floor (below) alone would allow up to ~1.052x (crest 4.30, lap
# exactly 2.0). Two other things bind first and are tighter:
#   * tests/test_case.py's rear-skirt probe window shrinks as the crest rises (the shoulder holds
#     the line high for longer, and the window it needs to probe the mouth chamfer through sits
#     right where that shoulder now reaches). It needs > 0.6 mm and is already down to 0.71 mm at
#     1.02x; at 1.03x it is 0.48 mm and the probe no longer fits without relocating it.
#   * TENT_ANGLE_MAX (below) is the angle past which SEAM_WAVE_LAP_LEFT can no longer clear its
#     own floor. It falls from 7.14 deg at 1.0x to 6.63 deg at 1.02x; the design runs at 6.0 deg,
#     so 1.02x is the point past which there is barely any angle headroom left to spend, not the
#     point past which the crest itself is illegal.
# 1.02x was picked to leave both of those with real margin rather than shave either to its edge.
SEAM_WAVE_CREST_U = SEAM_WAVE_CLIMB_KNOTS[-1][0]   # 0.670; the digitised crest, unchanged by scale
SEAM_WAVE_BAND_SCALE = 1.02   # THE dial; multiplies every digitised climb band-fraction

_SEAM_WAVE_TAIL_U = (0.700, 0.740, 0.780, 0.820, 0.860, 0.900, 0.950)   # even u past the crest
_SEAM_WAVE_TAIL_S0 = 0.65                                    # the shoulder, as a fraction of the run
_SEAM_WAVE_TAIL_M = 1.0 / (1.0 - _SEAM_WAVE_TAIL_S0 / 2.0)   # 1.4815...; the straight-run gradient


def _seam_wave_ground(u: float) -> float:
    """tent_ground_z(u * OUTER_DEPTH), written out. case.py has the real function; constants.py
    cannot import it, and this has to run at import time (see SEAM_WAVE_KNOTS below)."""
    return -(TENT_WEDGE_MIN_H + TENT_RISE * u)


def _seam_wave_drop(s: float) -> float:
    """The tail's fitted model: gradient ramps 0 -> m over the shoulder, then holds at m. See the
    WAVE block above SEAM_WAVE_CLIMB_KNOTS for where this comes from and why it is not an arc."""
    if s <= _SEAM_WAVE_TAIL_S0:
        return _SEAM_WAVE_TAIL_M * s * s / (2.0 * _SEAM_WAVE_TAIL_S0)
    return _SEAM_WAVE_TAIL_M * (s - _SEAM_WAVE_TAIL_S0 / 2.0)


_SEAM_WAVE_CLIMB = tuple((u, SEAM_WAVE_BAND_SCALE * band) for u, band in SEAM_WAVE_CLIMB_KNOTS)
# RE-ANCHORED ON THE CREST KNOT, not on a re-read of the built spline. The recipe this replaced
# read crest_y/crest_z off the SPLINE it was about to regenerate -- a pass that could only run
# once, because regenerating from its own output moves the crest a little further every time
# (verified: re-running it as a fixed point at k=1 alone drifts the crest +0.03 mm and the barb
# dead zone +2.3 mm). Anchoring on the knot instead is a closed form: the same inputs always
# produce the same table, and it reproduces the original shipped tail to 0.041 mm -- inside the
# 0.076 mm residual the model was already accepted at.
_seam_wave_crest_z = _SEAM_WAVE_CLIMB[-1][1] * TENT_WEDGE_MAX_H + _seam_wave_ground(SEAM_WAVE_CREST_U)
_seam_wave_fall = _seam_wave_crest_z - SEAM_NORTH_RISE_Z   # total drop from crest to the back edge


def _seam_wave_tail_band(u: float) -> float:
    s = (u - SEAM_WAVE_CREST_U) / (1.0 - SEAM_WAVE_CREST_U)
    z = _seam_wave_crest_z - _seam_wave_fall * _seam_wave_drop(s)
    return (z - _seam_wave_ground(u)) / TENT_WEDGE_MAX_H


# SEAM_WAVE_KNOTS -- climb (measured, scaled) + tail (modelled, regenerated). Every consumer
# (case.py's _seam_sweep_params, the guards below) reads this, not the climb/tail pieces alone.
SEAM_WAVE_KNOTS = _SEAM_WAVE_CLIMB + tuple(
    (u, _seam_wave_tail_band(u)) for u in _SEAM_WAVE_TAIL_U)

# SEAM_TAIL_SLOPE, derived from the same crest_z/fall -- see the note above its old literal
# definition for why this circle only closes now that the anchor is the knot, not the spline.
SEAM_TAIL_SLOPE = (_SEAM_WAVE_TAIL_M * _seam_wave_fall
                   / ((1.0 - SEAM_WAVE_CREST_U) * OUTER_DEPTH)
                   / math.tan(math.radians(TENT_ANGLE_DEG)))

# ---- The wave's knots, checked against the geometry they have to live inside ----
#   local Z = (band above the desk) + (Z of the desk there)
#           = band * TENT_WEDGE_MAX_H  -  (TENT_WEDGE_MIN_H + TENT_RISE * u)
# The second term is tent_ground_z() written out in terms of u; case.py has the function, but
# constants cannot import it, and the guards below have to run at import time.
SEAM_WAVE_Y = tuple((u * OUTER_DEPTH,
                     band * TENT_WEDGE_MAX_H - (TENT_WEDGE_MIN_H + TENT_RISE * u))
                    for u, band in SEAM_WAVE_KNOTS)
assert all(TENT_SEAM_Y1 < y < TENT_SEAM_Y2 for y, _z in SEAM_WAVE_Y), (
    f"a wave knot sits outside the ramp it shapes (y must be strictly inside "
    f"{TENT_SEAM_Y1:.2f}..{TENT_SEAM_Y2:.2f}); the runs either side own those ends")
assert all(a[0] < b[0] for a, b in zip(SEAM_WAVE_Y, SEAM_WAVE_Y[1:])), (
    "wave knots must be strictly increasing in y — a through-fit spline cannot double back")

# The ceiling is the rabbet ledge, and for exactly the reason SEAM_NORTH_RISE_FRAC's own ceiling
# of 1.0 exists: below SEAM_LEDGE_Z the tub is ONLY its outer skin, because _plate_pocket has
# already taken the floor and inner wall out from behind it, so the cutter eats skin and nothing
# else. Above the ledge it starts eating the tub proper. The crest is the same question asked at
# a different Y, and it costs the same thing -- rabbet lap, 1 mm for 1 mm.
SEAM_WAVE_LAP_MIN = 2.0       # mm; floor on the rabbet lap left once the crest has eaten into it
SEAM_WAVE_SPLINE_SLOP = 0.02  # mm; the BUILT spline overshoots its highest knot (measured ~0.016
#                                mm at 6 deg -- OCC's through-fit curve bows slightly past the
#                                point that is nominally its maximum). Folded into the lap guard
#                                so it protects the curve that actually gets cut, not just the
#                                knot table that approximates it.
SEAM_WAVE_CREST_Z = max(z for _y, z in SEAM_WAVE_Y)
SEAM_WAVE_LAP_LEFT = (SEAM_LEDGE_Z - max(SEAM_WAVE_CREST_Z, SEAM_NORTH_RISE_Z)
                      - SEAM_WAVE_SPLINE_SLOP)   # 2.41 at crest 3.87 (SEAM_WAVE_BAND_SCALE=1.02)
assert SEAM_WAVE_CREST_Z < SEAM_LEDGE_Z, (
    f"the wave crests at Z={SEAM_WAVE_CREST_Z:.2f}, at or above the rabbet ledge "
    f"SEAM_LEDGE_Z={SEAM_LEDGE_Z:.2f} — past there the seam cutter eats the tub itself, not its "
    f"skin. Lower the crest, or raise the ledge (which is FLOOR_THICKNESS and costs height)")
assert SEAM_WAVE_LAP_LEFT >= SEAM_WAVE_LAP_MIN, (
    f"the crest at Z={SEAM_WAVE_CREST_Z:.2f} leaves only {SEAM_WAVE_LAP_LEFT:.2f} mm of rabbet "
    f"lap to locate the two halves against each other; {SEAM_WAVE_LAP_MIN} is the floor")

# TENT_ANGLE_MAX -- the angle past which SEAM_WAVE_LAP_LEFT can no longer clear SEAM_WAVE_LAP_MIN,
# for THIS crest design (SEAM_WAVE_BAND_SCALE fixed). Band-fraction knots are angle-free, so the
# crest in mm is TENT_WEDGE_MIN_H*(k*b_c - 1) + TENT_RISE*(k*b_c - u_c), linear in TENT_RISE, which
# is what makes this solvable in closed form rather than swept numerically. Existed as a silent
# gap before this change (see tests/test_seam.py's angle sweep): raising the crest just makes the
# gap wide enough that it can no longer go unnoticed, so it is now an explicit, enforced ceiling
# instead of one guard being quietly weaker than another guard on the same physical quantity.
_seam_wave_kbc = SEAM_WAVE_BAND_SCALE * SEAM_WAVE_CLIMB_KNOTS[-1][1]
_seam_wave_rise_max = (
    (SEAM_LEDGE_Z - SEAM_WAVE_LAP_MIN - SEAM_WAVE_SPLINE_SLOP
     - TENT_WEDGE_MIN_H * (_seam_wave_kbc - 1.0))
    / (_seam_wave_kbc - SEAM_WAVE_CREST_U))
TENT_ANGLE_MAX = math.degrees(math.atan(_seam_wave_rise_max / OUTER_DEPTH))
assert TENT_ANGLE_DEG <= TENT_ANGLE_MAX, (
    f"TENT_ANGLE_DEG={TENT_ANGLE_DEG} exceeds TENT_ANGLE_MAX={TENT_ANGLE_MAX:.2f} for "
    f"SEAM_WAVE_BAND_SCALE={SEAM_WAVE_BAND_SCALE} — past this angle the wave's crest needs more "
    f"than SEAM_WAVE_LAP_MIN of rabbet lap to stay under SEAM_LEDGE_Z. Lower "
    f"SEAM_WAVE_BAND_SCALE, or raise SEAM_LEDGE_Z (costs height)")

# ---------- Rabbet snap latch ----------
# Hold-shut for the case ends the 5 screws cannot reach: they span case-Y 35.5-96.7 of a 126 mm
# case, so both ends are unclamped cantilevers held only by SEAM_FIT_CLEAR of rabbet friction.
# These are NOT a second clamp — the screws remain the only precision Z reference, and a
# fatigued latch degrades this joint back to friction-only rather than letting the case open.
# Full derivation: .omc/specs/deep-dive-invisible-snap-latches.md
#
# EVERY FLEXING PART IS ON THE BOTTOM PLATE'S RIM, AND THAT IS A PRINT-ORIENTATION DECISION.
# An FDM arm must bend PARALLEL to the layer lines. A strip of the bottom's rim, freed by a slot
# and pushed inward, bends about a VERTICAL axis, so the stretched material runs along the
# extrusions. An arm hanging off the tub's ledge would bend about a HORIZONTAL axis and peel its
# layers apart — and the tub prints rim-down, so that is squarely across them.
#
# The arm must be a CANTILEVER, not a fixed-fixed strip. Freeing it with the inboard slot alone
# leaves it built in at both ends, and fixed-fixed strain is 12*d*h/L^2 against a cantilever's
# 3*d*h/(2L^2) — 8x worse, 2.84% at L=22, which fractures PLA. Hence the outboard leg.
SNAP_TAB_L        = 22.0   # mm; default arm length. Per-arm; N2 is shorter, see SNAP_ARMS
SNAP_TAB_SLOT_W   = 0.9    # mm; relief slot width. IT IS ALSO WHAT YOU SEE: the same slot is
#                            the release port on the underside and, on the arms whose cut is
#                            north of the reveal line, the slit in the shadow recess. Narrowing
#                            1.2 -> 0.9 shrinks both by 25% (port ~26 -> ~20 mm² per arm) and
#                            costs nothing mechanically — the arm only deflects SNAP_DEFLECT,
#                            0.32 mm, so 0.9 is still 2.8x the gap it has to swing through, and
#                            every run margin GAINS 0.30 mm because cut_u and the slot's far
#                            edge both scale with this. The slot cannot be hidden altogether:
#                            it has to reach the ground face or the arm stops being a
#                            vertical-axis cantilever (see the print-orientation note below).
#                            WATCH THIS ON THE FIRST PRINT — 0.9 mm is a little over two 0.4 mm
#                            extrusions, so it may partially bridge where 1.2 would not.
SNAP_BARB_PROUD   = 0.52   # mm; barb protrusion from the rim's outer face (guide: 0.5-1.2)
# PINNED, not tuned further — printed via a print-shop service with no coupon to calibrate
# against, so raising this to chase a firmer click is not an option: the 28 N cap in
# test_closing_force_stays_hand_assemblable already allows proud up to only ~0.552 before the
# test itself fails, i.e. 0.52 already sits at ~94% of the force/strain budget. The 90 deg
# SNAP_RETURN_DEG is what actually guarantees "not loose" — a pure undercut cannot pull straight
# out regardless of barb depth — so there is no tightness upside to a deeper barb, only strain
# risk. See "Open questions and risks" -> SNAP_BARB_PROUD in the deep-dive doc.
SNAP_LEAD_IN_DEG  = 30.0   # deg from the insertion axis, barb's TOP face (guide: 25-35)
SNAP_RETURN_DEG   = 90.0   # deg from the insertion axis, barb's BOTTOM face. SELF-LOCKING —
#                            see the force note below; a flat face costs no Z at all.
SNAP_BARB_X_LEN   = 8.0    # mm; barb length along the wall, near the arm's free end
SNAP_BARB_EMBED   = 0.15   # mm; how far the barb's backing slab sinks INTO the rim. Not a
#                            shape dimension — it lies inside material that is already there,
#                            so it moves no face and adds no volume. It exists because a fuse
#                            across a single tangent plane is unreliable: with the barb standing
#                            exactly on v=0 OCC handed back the SE and SW diagonal barbs as
#                            separate solids, their run coordinates landing within 0.02 mm of
#                            the rim face rather than exactly on it. See snaps._barb_local.
SNAP_ROOT_FILLET  = 1.0    # mm; drilled root relief, >= 0.5 * SEAM_RIM_THK
SNAP_Z_PLAY       = 0.25   # mm; catch pocket taller than the barb, ALL of it below the barb
SNAP_SKIRT_BELOW  = 0.3    # mm; skirt kept below the catch pocket
SNAP_SKIRT_ABOVE_MIN = 1.0 # mm; skirt that must survive above the catch pocket
# PLA is rated POOR for snaps (low strain tolerance, creep-prone). Staying on PLA is deliberate
# and survivable ONLY because the screws are the load path. Budget set accordingly.
SNAP_PLA_STRAIN_MAX = 0.005

SNAP_DEFLECT = SNAP_BARB_PROUD - SEAM_FIT_CLEAR   # 0.32; the arm's working deflection

# SNAP_Z_PLAY IS THE DEAD TRAVEL, and that is what a closed case feels like: the tub lifts by
# exactly this much before any barb bites. It was 0.5, which reads as a loose case no matter how
# strong the latches are. It cannot go much below 0.25 either — the closure Z is a five-link
# chain (FLOOR + SHOULDER + PCB + MX_BODY_CLEAR + PLATE) whose error is ONE-DIRECTIONAL: the
# standoff pin tops are a hard floor under the switch plate, so the tub can only ever sit at or
# ABOVE nominal, never below. A high tub carries the pocket UP relative to the barb, so the
# barb needs its clearance BELOW it, and the pocket FLOOR is therefore the retention face.
# Too little play and the barb bottoms out on that floor and becomes the Z datum instead of the
# standoffs — two datums for one face, which is the bug STANDOFF_PIN_RECESS exists to avoid.


def snap_barb_h(barb_proud: float = SNAP_BARB_PROUD) -> float:
    """Total Z height of a barb of this depth: lead-in ramp + return face.

    Both ramps are measured from the insertion axis (Z), so each costs proud/tan(angle) of
    height — the barb's Z extent is DERIVED from its depth, never guessed, and it therefore
    GROWS with the barb. At SNAP_RETURN_DEG = 90 the return face is flat and costs nothing,
    which is why the self-locking barb is also the SHORTEST one."""
    per_mm = 1.0 / math.tan(math.radians(SNAP_LEAD_IN_DEG))
    if SNAP_RETURN_DEG < 90.0:
        per_mm += 1.0 / math.tan(math.radians(SNAP_RETURN_DEG))
    return barb_proud * per_mm


SNAP_BARB_H = snap_barb_h()                                   # 0.9007
SNAP_Z_BUDGET = SNAP_BARB_H + SNAP_Z_PLAY + SNAP_SKIRT_ABOVE_MIN   # 2.1507
# The hidden band a barb must fit into is (SEAM_LEDGE_Z - SEAM_LEAD_IN) - max(seam_z, mouth),
# and the wave crests at SEAM_WAVE_CREST_Z, leaving less than the budget over part of the
# ramp. That excluded stretch is the BARB DEAD ZONE — measured at y 81.04..92.79 for this
# budget and SEAM_WAVE_BAND_SCALE (it widened from 83.25..88.50 when the crest was raised). It
# moves when SNAP_Z_PLAY or the crest move, so tests compute it; nothing hard-codes it.
SNAP_BAND_CEIL = SEAM_LEDGE_Z - SEAM_LEAD_IN                  # 5.70; below the rim's chamfer
SNAP_BAND_FLOOR = SEAM_POCKET_LEAD_IN                         # 0.40; above the pocket mouth


def snap_strain(thickness: float, tab_l: float = SNAP_TAB_L,
                deflect: float = SNAP_DEFLECT) -> float:
    """Peak root strain of a straight rim arm: e = 3*h*y / (2*L^2), the standard tip-loaded
    cantilever result (Covestro publish it as d_max = e_perm*L^2 / (1.5*h), rearranged).

    ``thickness`` is the radial bending thickness h. It is PER ARM and <= SEAM_RIM_THK: the
    inboard slot can be widened to leave a thinner arm, which is the main tuning knob because
    force goes as h^3 while strain only goes as h."""
    return 3.0 * thickness * deflect / (2.0 * tab_l ** 2)


def snap_force(thickness: float, arm_h: float, tab_l: float = SNAP_TAB_L,
               deflect: float = SNAP_DEFLECT, e_mod: float = 3500.0) -> float:
    """Deflection force of one straight arm, in N: P = E*b*h^3*y / (4*L^3).

    ``arm_h`` is the beam WIDTH b — the LOCAL WALL HEIGHT, not SEAM_LEDGE_Z. The arm is freed
    from the wedge's ground face up to the ledge, so b is 9.4 mm at the south front and ~20 mm
    at the north where the wedge is deep. A single global thickness would therefore put half
    the closing force in the north arms: uniform h=2.0 totals 49.9 N against 24.7 N tuned.
    b cancels out of the strain entirely."""
    return e_mod * arm_h * thickness ** 3 * deflect / (4.0 * tab_l ** 3)


def snap_insertion_force(deflect_force: float, mu: float) -> float:
    """Push-on force from the deflection force: W = P*(mu + tan a)/(1 - mu*tan a).

    ASSEMBLY FORCE IS NOT DEFLECTION FORCE, and printed PLA on PLA is grippy — measured 0.4-0.7
    static at 100% infill, not the 0.3 a smooth-plastic guide would suggest. Over that range
    this multiplies P by 1.27 to 2.14, which is the largest single uncertainty in the numbers.

    The same expression run at SNAP_RETURN_DEG gives the pull-off force, and it goes SINGULAR
    at mu*tan(a) = 1 — i.e. self-locking above atan(1/mu), which is 68.2 deg at mu=0.4 and
    55.0 deg at mu=0.7. The old 60 deg return sat inside that band only for mu >= 0.55, so its
    behaviour depended on print quality. 90 deg is a pure undercut: it cannot cam out at all,
    and the case comes apart by prying the shells, deliberately.

    DESIGN POINT: mu=0.7 (this file's grippy end). Parts come from a print-shop service, so
    there is no printer to calibrate against and no coupon to measure the real value — planning
    for the pessimistic end costs nothing here, since a higher mu only ever predicts a HARDER
    push, never a looser hold (retention is the 90 deg undercut's job, not friction's). At
    mu=0.7 the worst-case insertion is 54.5 N, already accepted as the deliberate firm-press
    target rather than an accident of the friction range."""
    t = math.tan(math.radians(SNAP_LEAD_IN_DEG))
    return deflect_force * (mu + t) / (1.0 - mu * t)


class SnapArm(NamedTuple):
    """One latch. ``root`` is on the rim's OUTER face; ``out`` is that wall's outward normal.

    ``sense`` multiplies snaps.arm_direction(out) = (out_y, -out_x). The old code derived the
    direction from the normal alone so that "local +Y is outward" held without a second sign to
    keep in step — but that fixes each wall's arm direction, and the free-end cut has to land
    where the tub's skin still covers the rim. On the west wall and on the south front's west
    arm the derived sense points the cut into the reveal, so it is now explicit."""
    name: str
    root: tuple[float, float]
    out: tuple[float, float]
    sense: float
    length: float
    thickness: float
    barb_lo_z: float
    hidden_cut: bool


# ---- The measured rim runs the arms sit on ----
# Endpoints read off a section of the BUILT plate rim at z=3.0 (25 edges, 495.26 mm total), NOT
# off the PCB polygon: the rim is that polygon offset outward by PCB_XY_CLEARANCE + SEAM_RIM_THK
# and _plate_envelope offsets with ARCS, so every convex corner is an R3.05 fillet and the
# straight runs come out SHORTER than the polygon edges (south front 55.84 not 56.50; north-east
# 34.95 not 38.00). A straight prism laid across one of those arcs floats off the wall and
# produces disjoint solids — the failure that sank the first attempt at this.
#
# Arms on these runs DERIVE their root and outward normal from the endpoints instead of carrying
# hand-typed literals. On the two diagonals and in the gulf the normal is not axis-aligned, and
# a mistyped fourth decimal there tilts the barb into the skirt without tripping any assert.
_Run = tuple[tuple[float, float], tuple[float, float]]
SNAP_RUN_SE_DIAG: _Run = ((149.53, 30.30), (111.53, 20.30))   # 39.29 mm
SNAP_RUN_SOUTH:   _Run = ((110.75, 20.20), (54.91, 20.20))    # 55.84 mm, east -> west
SNAP_RUN_GULF_A:  _Run = ((54.91, 20.20), (38.16, 12.54))     # 18.42 mm, thumb gulf, east leg
SNAP_RUN_GULF_B:  _Run = ((38.16, 12.54), (21.30, 2.62))      # 19.56 mm, thumb gulf, west leg
SNAP_RUN_SW_DIAG: _Run = ((17.11, 3.72), (2.61, 28.72))       # 28.90 mm
SNAP_RUN_EAST:    _Run = ((151.80, 109.25), (151.80, 33.25))  # 76.00 mm, north -> south
SNAP_RUN_WEST:    _Run = ((10.70, 36.98), (10.70, 115.75))    # 78.77 mm, south -> north
SNAP_RUN_CANOPY_N: _Run = ((13.75, 118.80), (51.75, 118.80))  # 38.00 mm, west -> east
SNAP_RUN_NE:      _Run = ((113.80, 112.30), (148.75, 112.30))  # 34.95 mm, west -> east
# Each pair is oriented so snap_run_outward() returns the OUTWARD normal: east -> (1,0),
# west -> (-1,0), both north runs -> (0,1). Reverse a pair and every barb on it moves to the
# inside of the rim, which builds without complaint and latches nothing.


def snap_run_dir(run: _Run) -> tuple[tuple[float, float], float]:
    """Unit vector along a rim run, plus its length."""
    (x0, y0), (x1, y1) = run
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    return (dx / length, dy / length), length


def snap_run_outward(run: _Run) -> tuple[float, float]:
    """The run's OUTWARD normal, derived rather than typed.

    These endpoint pairs walk the outline CLOCKWISE in case coords — the south front runs east
    to west — so outward is ``(-dy, dx)``: on the south front that returns (0, -1), which does
    point away from the case. The opposite convention would put every barb inside the rim."""
    (dx, dy), _ = snap_run_dir(run)
    return (-dy, dx)


def snap_run_point(run: _Run, s: float) -> tuple[float, float]:
    """Point at arc-length ``s`` measured from the run's start."""
    (dx, dy), _ = snap_run_dir(run)
    (x0, y0), _ = run
    return (x0 + dx * s, y0 + dy * s)


# ---- Where the arms go ----
# EVERY ARM IS SPACED BY ARC LENGTH AROUND THE WHOLE RIM, NOT PER WALL. The outline is 495.26 mm
# and the eleven barbs divide it into steps of 43.75-46.37 mm against an ideal of 45.02 — a
# spread of 2.62 mm, where the previous layout ran 32.32 to 56.95 (spread 24.63) because only
# the southern stretch had been evened out and the north and east had never been touched.
#
# ELEVEN IS THE RIGHT COUNT, and this was measured rather than assumed, because the obvious move
# is to delete an arm and it makes the case WORSE. Best achievable max gap by count, with N2
# anchored on the lobe:
#
#     9 arms  58.33   (perfectly even 55.03)
#    10 arms  55.28   (49.53) — and the optimum drops an EAST arm, not a southern one
#    11 arms  45.63   (45.02) — near perfect
#    12 arms  45.58   (41.27) — no better than 11, the constraint binds
#
# Only 54% of the rim can carry a barb at all: corner arcs are unbuildable (a prism laid across
# one floats off the wall and comes back as a disjoint solid), the north runs are too short, and
# the barb dead zone at y 83.47-88.32 rules out a stretch of both side walls. So 2.62 mm of
# spread is close to the floor, not a first attempt.
#
# EVERY CUT KEEPS >= 1.8 mm OF RIM BEYOND IT. The cut is a through-slot SNAP_TAB_SLOT_W wide, so
# 1.8 leaves a 1.2 mm sliver — three perimeters at a 0.4 mm nozzle. An earlier solve of this
# layout left N3 with 0.60 mm and T1 with 0.45 mm of feather against a run end, which prints as
# a fin. Tightening the margin to 2.5 everywhere was tried and cost 9.00 mm of spread; the split
# below (2.5 at the root, where the arm is actually anchored, and 1.8 past the cut, where only
# printability is at stake) holds the spread at 2.62.
#
# ONLY THE FREE-END CUT HAS TO BE HIDDEN. The inboard slot opens on the cavity and the ground
# face, and the barb sits above seam_z at every station used, so both are invisible everywhere.
# The cut severs the rim's outer face, and that face is bare wherever the reveal exposes it:
# exposure crosses zero at y = 54.87 (moves with SEAM_WAVE_BAND_SCALE), so cuts south of
# TENT_SEAM_Y1 are covered by the skin
# with a constant +0.200 mm margin (BOTTOM_CHAMFER 0.5 - TENT_SKIRT_LIFT 0.3), and cuts north
# of it show a 1.2 mm slit in a 2.2 mm deep shadow recess.
#
# HIDDEN CUTS FELL FROM SIX TO FOUR, and that is the price of evenness rather than an oversight.
# E1 and W1 used to cut at y=39.60, under the skin; even spacing carries their barbs north to
# y=53.50 and 55.71, and a cut sits 5.0 mm beyond its own barb, so neither can reach back under
# the line in either sense. They join the five arms that already show a slit by decision.
#
# barb_lo_z IS ONE SHARED NUMBER, 3.95, AND THE LADDER IT REPLACED WAS DOING NOTHING. That ladder
# ran 1.40 to 4.40 in 0.30 steps on the claim that a shared datum "makes all eleven peak in the
# same instant" and staggering "turns a single 60 N wall into eleven small ones". Simulating the
# actual closure — the barb's profile against the skirt's inner face, with the catch pocket
# travelling up with the tub — the peak is 26.57 N either way, 100% of the total, because the
# pocket has cleared its own barb by about 1.15 mm above seated. Past that point every arm is
# bearing on solid skirt at once no matter what height it sits at, so there is no instant to
# stagger. The claim was never measured; it is now.
#
# What the ladder did cost was uniformity where it actually matters. Skirt left above the catch
# pocket is (SEAM_LEDGE_Z + SEAM_LEDGE_CLEAR) - (barb_lo_z + SNAP_BARB_H), and across the ladder
# that ran 1.30 mm on N2 to 4.30 mm on SW1 — the thin end being the place the skirt would split.
# One height gives every arm 1.749 mm.
#
# 3.95, AND NOT HIGH ENOUGH TO RETIRE THE DEAD ZONE OUTRIGHT ANY MORE — that claim held at the
# original crest (3.60) and stopped holding once SEAM_WAVE_BAND_SCALE raised it: the worst floor
# anywhere on the rim, max(seam_z, ...) + SNAP_SKIRT_BELOW at the crest itself, is now
# SEAM_WAVE_CREST_Z + SNAP_SKIRT_BELOW = 4.17, ABOVE 3.95. Barb height alone no longer says
# "nowhere on the rim is excluded" — see test_every_barb_sits_at_one_height, which used to assert
# exactly that and now asserts the fact underneath it instead.
#
# WHAT ACTUALLY BOUNDS WHERE AN ARM MAY GO is the BAND check (SNAP_BAND_CEIL - SNAP_Z_BUDGET =
# 3.5493), asked at each arm's OWN barb y — not this barb-height check, worst-case-anywhere. The
# band check has always been the tighter of the two (3.5493 < SNAP_SKIRT_BELOW's own 3.65 floor),
# so nothing that ever cleared it was saved by the barb-height margin below; the barb-height check
# was a REDUNDANT, weaker guarantee that happened to read as a stronger one. Per arm, only E2
# (floor 2.75) and W2 (floor 2.85) sit anywhere near the crest — everywhere else floors at
# SNAP_BAND_FLOOR (0.40) — and both clear 3.95 with margin (1.20 / 1.10 mm) once measured against
# the BAND ceiling that actually governs (see test_every_barb_fits_its_hidden_band). The ceiling
# is unchanged by the crest either way, 4.799 (band) / 5.699 (skirt), because it comes from
# barb_lo_z and SNAP_BARB_H alone. (E2's floor moved with its own reposition to the run's ceiling,
# below — it was 3.36 / margin 0.59 at its original arc-length.)
#
# THICKNESS IS PER ARM AND FALLS OUT OF THE FORCE BUDGET, not the geometry. Each arm is sized to
# carry about 2.4 N so the set totals 26.4 N against the 28 N cap in
# test_closing_force_stays_hand_assemblable. Force goes as b*h^3 while strain goes as h, and the
# beam width b runs 8.2 mm in the gulf to 19.8 mm on the canopy north, so a single global h would
# put half the closing force in the northern arms.
SNAP_ARMS: tuple[SnapArm, ...] = (
    #        name              root                                      out                                 sense  L     h     barb  hidden
    SnapArm("SW1-sw-diag",   snap_run_point(SNAP_RUN_SW_DIAG, 3.19),   snap_run_outward(SNAP_RUN_SW_DIAG),  +1.0, 16.0, 1.55, 3.95, True),
    SnapArm("T1-thumb-gulf", snap_run_point(SNAP_RUN_GULF_A, 2.96),    snap_run_outward(SNAP_RUN_GULF_A),   +1.0, 13.0, 1.30, 3.95, True),
    SnapArm("S1-south-C",    snap_run_point(SNAP_RUN_SOUTH, 6.06),     snap_run_outward(SNAP_RUN_SOUTH),    +1.0, 22.0, 2.15, 3.95, True),
    SnapArm("SE1-se-diag",   snap_run_point(SNAP_RUN_SE_DIAG, 4.14),   snap_run_outward(SNAP_RUN_SE_DIAG),  +1.0, 20.0, 1.90, 3.95, True),
    SnapArm("E1-east-S",     snap_run_point(SNAP_RUN_EAST, 35.81),     snap_run_outward(SNAP_RUN_EAST),     +1.0, 22.0, 1.90, 3.95, False),
    SnapArm("N1-canopy-N",   snap_run_point(SNAP_RUN_CANOPY_N, 8.82),  snap_run_outward(SNAP_RUN_CANOPY_N), +1.0, 22.0, 1.65, 3.95, False),
    SnapArm("W1-west-S",     snap_run_point(SNAP_RUN_WEST, 36.33),     snap_run_outward(SNAP_RUN_WEST),     -1.0, 22.0, 1.90, 3.95, False),
    SnapArm("N3-north-east", snap_run_point(SNAP_RUN_NE, 24.70),       snap_run_outward(SNAP_RUN_NE),       -1.0, 22.0, 1.70, 3.95, False),
    SnapArm("W2-west-N",     snap_run_point(SNAP_RUN_WEST, 46.90),     snap_run_outward(SNAP_RUN_WEST),     +1.0, 22.0, 1.70, 3.95, False),
    SnapArm("E2-east-N",     snap_run_point(SNAP_RUN_EAST, 24.75),     snap_run_outward(SNAP_RUN_EAST),     -1.0, 22.0, 1.75, 3.95, False),
)
# T1 IS THE ONE SHORT ARM, and it is short because even spacing pins its barb at arc-length
# 73.0, which falls on gulf-A — an 18.42 mm run. Rooting it 2.96 mm in and cutting at 17.16
# leaves 1.26 mm before the gulf's mitre, which caps the arm at L=13. Running it longer means
# spanning that mitre, and although the kink is only 5.90 deg, a straight prism laid across it
# deviates 1.24 mm over this arm's span — half the rim's thickness, so the arm would float off
# the wall. Spanning it properly needs N2's concentric-band builder generalised to trim bounds
# that are not axis-aligned; L=13 at h=1.30 gives 0.369% strain, inside the PLA budget, and
# keeps every entry above an ordinary straight arm. The band is the fallback if strain ever has
# to come down.
# N2 sits on the 18.00 mm SW3 lobe, the only run too short for L=22. As a straight arm it has to
# stay thin — h=1.20 gives 0.294% strain and 3.58 N, and it cannot be stiffened to match the
# other north arms (h=1.75 on L=14 is 11.11 N, four times the set's average). Wrapping the R3
# corner onto the 16.00 mm lobe-west run gives L_eff 25.4 mm, 0.082% strain and 1.86 N at
# h=1.75 — but that needs a swept builder, so the straight arm above is the shipped fallback.

# ---- E2 MOVED TO ITS RUN'S CEILING, AND THE NE CORNER'S EVENNESS IS THE DELIBERATE PRICE ----
# Raising the crest (SEAM_WAVE_BAND_SCALE) thinned the TOP part's ambient rim wall in the stretch
# between E2's root and its own catch pocket — not the pocket/barb interface itself, which stays
# clear at every position tried, but the plain wall the arm's inboard relief leg sits against.
# Checked on the built solid, not just the band-margin formula: at the ORIGINAL root (arc-length
# 29.11) that wall was already thinned by up to ~0.55 mm just south of the pocket, a pre-existing
# condition (baseline, before any crest raise, thinned by ~0.5 mm there too) that the raise made
# a little worse.
#
# MOVING E2 FURTHER NORTH ON ITS OWN RUN CANNOT FULLY CLEAR IT. SNAP_RUN_EAST simply runs out —
# past arc-length ~24.7 (root y=84.55) the outboard relief cut's own far edge is inside
# SNAP_TAB_SLOT_W + 1.8 mm of the run's north end, the same "floats off the wall" failure T1 and
# N2 exist to dodge. Even at that ceiling the residual thinning does not reach zero (~0.20 mm).
#
# E2 SITS AT THAT CEILING (arc-length 24.75, root y=84.55) — the most this run can give — because
# a snap that feels wrong on one specific arm was judged worse than an uneven rim. That is a
# deliberate reversal of test_every_barb_is_evenly_spaced_around_the_whole_rim's usual priority,
# not an oversight: the whole point of that test is normally that spacing wins over local
# convenience, and here it does not. E1-east-S (38.15 -> 35.81) and N3-north-east (24.61 -> 24.70)
# are pushed to the positions that do the LEAST damage to the rest of the rim for E2 sitting at
# its ceiling, not to hit any spacing target of their own.
#
# THE DAMAGE IS SCOPED TO EXACTLY THREE ARMS' WORTH OF GAPS. The other eight (everything from
# SE1-se-diag round through N3-north-east's OWN far side back to E1-east-S) still divide their
# stretch of the rim to a 2.39 mm spread — tighter than the original all-eleven 2.62 mm, because
# they were re-solved around E2's fixed new position rather than left where a uniform solve put
# them. Only the four gaps touching E1/E2/N3 carry the cost: SE1-E1 and E1-E2 open to 46.31 mm
# each, E2-N3 compresses to 39.70 mm, and N3-N2 opens to 46.22 mm — a local bulge-then-pinch around
# the NE corner, not a rim-wide drift. See the same test for the explicit exemption and why the
# other eight still get the strict check.
#
# THE RESIDUAL IS ACCEPTED, NOT HIDDEN, on both fronts. The ~0.20 mm of ambient-wall thinning is
# on the wall next to the relief leg, not on the barb/pocket interface that actually carries load.
# Closing it to zero needs either less crest (SEAM_WAVE_BAND_SCALE back down) or a wrapped/banded
# builder for E2 like N2's; closing the NE corner's spacing back up needs the same, since it is
# the run running out that forces both trade-offs at once.

# ---- N2, the one arm that wraps a corner ----
# The SW3 lobe is the northernmost run on the case (y=123.80, over SW3 at x=82.52) and it is
# 18.00 mm long — too short for L=22, and a straight L=14 there has to stay at h=1.20 to survive
# (0.294% strain, 3.58 N) and cannot be stiffened with the rest: h=1.75 on L=14 is 11.11 N, four
# times the set's average. So this arm runs past the end of the lobe.
#
# WHAT IT WRAPS IS A JOG, NOT AN ELBOW, and that distinction is the whole sizing argument. The
# lobe is flanked at BOTH ends by a 4.24 mm arc dropping to a run at y=121.30 — measured on a
# section of the built plate, where the 2.5 mm of west-facing wall between them is consumed
# entirely by the two R3.05 offsets and never appears as a straight edge. Both runs therefore
# face NORTH; the wall does not turn a corner, it steps sideways.
#
# An earlier pass modelled this as a 90 deg L-arm and got L_eff = (Lb^3 + 3*Lb^2*La)^(1/3) =
# 25.4 mm. That formula is for perpendicular legs, where the load is axial to the root leg and
# it carries a constant moment. Here the load is perpendicular to BOTH legs, so the thing
# behaves as a nearly straight cantilever of 18.00 + 4.24 + 16.00 = 38.24 mm of continuous rim
# with a 2.5 mm lateral offset partway along. Sized as a straight beam accordingly.
SNAP_CORNER_LOBE = ((91.75, 123.80), (73.75, 123.80))   # measured rim run, east -> west
SNAP_CORNER_ARC = 4.24                                  # the blend to the next run
SNAP_CORNER_WEST = ((70.75, 121.30), (54.75, 121.30))   # measured rim run past the arc
SNAP_CORNER_L = 26.0     # of the 38.24 available. Full length would be 0.545 N — too soft to
#                          matter; 26 at h=2.0 lands on 2.59 N and 0.142%, in line with the rest
SNAP_CORNER_CUT_S = 2.0  # arc-length from the lobe's east end to the cut's outboard face
SNAP_CORNER_THK = 2.0
SNAP_CORNER_BARB_LO_Z = 3.95   # the same shared height as every straight arm; see the note
#                                above SNAP_ARMS for why there is no longer a ladder

assert len({a.name for a in SNAP_ARMS}) == len(SNAP_ARMS), "duplicate SNAP_ARMS name"
_corner_run = ((SNAP_CORNER_LOBE[0][0] - SNAP_CORNER_LOBE[1][0]) + SNAP_CORNER_ARC
               + (SNAP_CORNER_WEST[0][0] - SNAP_CORNER_WEST[1][0]))
_corner_need = SNAP_CORNER_CUT_S + SNAP_TAB_SLOT_W + SNAP_CORNER_L + 2.0
assert _corner_need <= _corner_run, (
    f"the corner arm needs {_corner_need:.2f} mm of rim (cut + slot + arm + root) but the lobe "
    f"stretch is only {_corner_run:.2f} mm")
assert SNAP_CORNER_THK <= SEAM_RIM_THK, "corner arm is thicker than the rim it is cut from"
assert SNAP_TAB_SLOT_W < SEAM_RIM_THK, "relief slot is wider than the rim it relieves"
for _a in SNAP_ARMS:
    assert _a.thickness <= SEAM_RIM_THK, (
        f"{_a.name}: arm thickness {_a.thickness} exceeds the rim it is cut from "
        f"({SEAM_RIM_THK}) — there is nothing to make it out of")
    assert _a.length / _a.thickness >= 8.0, (
        f"{_a.name}: L/t is {_a.length / _a.thickness:.1f}:1; rigid filaments want >= 8:1 or "
        f"the root over-strains")
    _e = snap_strain(_a.thickness, _a.length)
    assert _e <= SNAP_PLA_STRAIN_MAX, (
        f"{_a.name}: root strain {_e * 100:.3f}% exceeds the {SNAP_PLA_STRAIN_MAX * 100:.1f}% "
        f"PLA budget — lengthen the arm (strain falls as L^2), thin it, or shrink "
        f"SNAP_BARB_PROUD")
    assert _a.length >= SNAP_BARB_X_LEN + 2.0, (
        f"{_a.name}: an arm {_a.length} mm long cannot carry a {SNAP_BARB_X_LEN} mm barb and "
        f"still have root material — the barb would run off one end or the other")
    assert SNAP_BAND_FLOOR < _a.barb_lo_z and _a.barb_lo_z + SNAP_BARB_H <= SNAP_BAND_CEIL, (
        f"{_a.name}: barb band {_a.barb_lo_z:.2f}..{_a.barb_lo_z + SNAP_BARB_H:.2f} is outside "
        f"the rim's usable face ({SNAP_BAND_FLOOR:.2f}..{SNAP_BAND_CEIL:.2f}) — below the floor "
        f"it lands on the pocket's mouth chamfer, above the ceiling on the rim's lead-in")
    assert (SEAM_LEDGE_Z + SEAM_LEDGE_CLEAR) - (_a.barb_lo_z + SNAP_BARB_H) >= SNAP_SKIRT_ABOVE_MIN, (
        f"{_a.name}: only "
        f"{(SEAM_LEDGE_Z + SEAM_LEDGE_CLEAR) - (_a.barb_lo_z + SNAP_BARB_H):.2f} mm of skirt "
        f"survives above its catch pocket, under SNAP_SKIRT_ABOVE_MIN={SNAP_SKIRT_ABOVE_MIN}")
assert sum(1 for a in SNAP_ARMS if a.hidden_cut) == 4, (
    "four arms are meant to have hidden cuts (SW1, T1, S1, SE1 — the southern stretch, which "
    "cuts at y <= 24.0, south of the line where the reveal starts to open); the rest show a "
    "slit by decision. This was SIX before the whole rim was evenly spaced: E1 and W1 used to "
    "cut under the skin at y=39.60, and even spacing carries their barbs north far enough that "
    "no sense of the arm can reach back. If that count changed, the visibility test's exemption "
    "list changed with it")

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

# ---------- MCU board Y extent (anchored to the SOUTH pin, NOT centred on the array) ----------
# The nano is located by its 24 pin holes, so the board's Y faces must be derived from a PIN —
# never from ``MCU_POS ± MCU_BODY_L/2``. That centred form happened to give the right answer
# only while MCU_BODY_L was the nice!nano's 33.0, which IS centred on the pins; at any other
# length it drifts, and it drifts on the end that matters. That trap is still live — see
# tests/test_constants.py.
#
# WHICH pin is the anchor is the second half of the question, and it was answered wrong. This
# used to derive the USB-end face from the NORTHMOST pin, which spends the SuperMini's extra
# 1.1 mm (34.1 vs the nice!nano's 33.0) at the far/south end. Backwards. A Pro-Micro-footprint
# board is 33.02 mm = the 27.94 mm pin span plus 2.54 mm of edge at EACH end, so it is the far
# edge that the pin row pins down; a board longer than 33.0 grows NORTH, out over the USB end.
# That is exactly why a SuperMini fouls a case cut for a nice!nano — the north face (board and
# the jack overhanging it) lands in the canopy's north wall, and the case will not close over
# it. Anchor south, let the length run north, and the collision is visible instead of invented
# somewhere it is harmless.
MCU_PIN_SPAN_Y        = 27.94   # mm; 11 × 2.54 between the outer pins — from the drill file
MCU_PIN_TO_SOUTH_EDGE = 2.54    # mm; southmost pin centre → the board's FAR (non-USB) edge.
#                                 Stock Pro Micro footprint: 27.94 + 2 × 2.54 = 33.02 ⇒ the
#                                 33.0 mm board. This end is the datum; MCU_BODY_L sets the other.
MCU_BODY_S_Y = pcb_to_case(*MCU_POS)[1] - MCU_PIN_SPAN_Y / 2 - MCU_PIN_TO_SOUTH_EDGE  # 83.08
MCU_BODY_N_Y = MCU_BODY_S_Y + MCU_BODY_L                                              # 117.18
# For reference: the PCB's own north edge at this column is 115.75, so the board overhangs
# it by 1.43 mm — that overhang is the unsupported B+/B- pad end (see the relief below).

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

# ---------- The north bay's inner face — ONE plane, tray floor to canopy roof ----------
# The tray cavity, the ceiling band above the plate top, and the canopy's north wall all bound
# the same bay on the same side, and each used to pick its own Y: 118.75, 116.09 and 117.50.
# Three faces on one wall means two steps, and a step in the bay is a ledge the MCU has to be
# threaded past on the way in. The middle one was the worst of them — bounding the ceiling band
# at MCU_BODY_N_Y put its face on exactly the board's north face, zero air by construction, and
# left a 1 mm-tall lip running the full width of the bay under the USB funnel.
#
# So they all land here instead. Anything that bounds the bay on the north consumes this and
# nothing steps inboard of anything else; the MCU slides past one flat wall. Derived from the
# relief target, so raising MCU_Y_RELIEF_TARGET_Y moves the wall, the cavity and the canopy
# together (that is the escape hatch if the board ever measures longer than MCU_BODY_L).
BAY_NORTH_INNER_Y = pcb_to_case(0, MCU_Y_RELIEF_TARGET_Y)[1] + PCB_XY_CLEARANCE   # 118.75
assert BAY_NORTH_INNER_Y - (MCU_BODY_N_Y + USB_JACK_Y_PROTRUDE) >= 0.3, (
    f"the north bay leaves {BAY_NORTH_INNER_Y - (MCU_BODY_N_Y + USB_JACK_Y_PROTRUDE):.2f} mm "
    f"in front of the USB jack — the MCU will not go in")

# ---------- Slide-switch slot X reach (−X wall) ----------
# Inner-X bound the slide-switch slot cutter extrudes to. Derived from the −X wall
# corner (pcb_to_case(0,0)[0]) + a 1.5 mm margin so it tracks the PCB re-centring
# when WALL_THICKNESS changes (15.25 at WALL=4.75).
MCU_HILL_NEG_X_INNER_BOUND_X: float    = pcb_to_case(0, 0)[0] + 1.5