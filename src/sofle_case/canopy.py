"""Fastback canopy over the MCU / JST / slide-switch bay — FUSED into the TOP cover.

``case.build_top_part`` adds this onto the TOP, so the MCU hood is integral to the cover, not
a separate part. Its ``CANOPY_*`` parameters are self-contained here (not in constants.py) and
depend only on base geometry constants. Cross-section is a Y–Z roofline swept along the bay's
X width (case Y, south → north):

  • Foot   — the ramp merges tangentially DOWN into the cover surface (``CANOPY_FOOT_Z``) —
             NO raised tongue — and lands ON the encoder plateau's north face so the bay strip
             in front of the plateau is CLOSED (no open gap). The body base drops to
             ``CANOPY_FUSE_BASE_Z`` (one cover thickness below) so it overlaps the cover/walls
             (and the plateau stub) for a clean OCC union.
  • Ramp   — a tangent S-curve (exact single cubic ``Bezier`` — the analytic
             3t²−2t³ with horizontal tangents, 0 deviation, minimal curvature) up to the
             flat roof. Reaches full height ``CANOPY_RAMP_TOP_OLED_GAP`` before the OLED
             pins; the whole south bay is empty (PCB-level) so the low foot clears.
  • Roof   — FLAT at ``CANOPY_RIDGE_TOP_Z`` over the MCU (clears the USB-C stack).
  • North / West / East — VERTICAL walls landing at the chamfer FIRST point (chamfer
             EXPOSED); BOTH north corners (NW + NE) are ROUNDED to the case's own corner radius
             (``_round_nw_corner`` / ``_round_ne_corner``). Both top shoulders carry a drafted
             facet cut by a swept boolean, NOT a 3-D edge chamfer (``_chamfer_west_top`` /
             ``_chamfer_east_top`` — an edge chamfer cannot survive the ramp spline's density).
             The USB-C port is cut through the north wall (required — the plug must pass; the jack
             itself stops 0.57 mm short of the wall's inner face, see C.USB_JACK_Y_PROTRUDE). The
             wall's thickness is DERIVED, not chosen — see CANOPY_NORTH_WALL. The lower east
             wall remains the plain vertical switch-column boundary below its chamfered shoulder.

There is deliberately NO reset poke-hole. The roof over RSW1 is unbroken: a bore there could not
be relocated into the BOTTOM part (it would end at the PCB underside, Z=PCB_SEAT_Z, not at the
button), so the feature was dropped rather than moved. Reset means opening the case, or the
nice!nano's double-tap over the USB-C port.

Tangent curves are 2-D profile Beziers/fillets on the swept cross-section (robust), not
fragile 3-D solid fillets. The slide finger-bowl (over on the −X wall) is handled in ``tray``
and split cleanly into the TOP part by ``case``'s local seam step-down."""
from __future__ import annotations
import math
from typing import Callable, Sequence, cast

from build123d import (
    Part, Face, Pos, Line, Polyline, Spline, Bezier, make_face, extrude, fillet, chamfer, loft, Solid,
    Plane, BuildPart, BuildSketch, BuildLine,
)
from OCP.Standard import Standard_Failure
from . import constants as C
from . import canopy_puzzle as PZ
from .canopy_puzzle import Stroke

# A sketch plane whose local axes map cleanly onto global (Y, Z) with the extrude normal along
# +X: local-x = +Y, local-y = +Z. Built-in ``Plane.YZ`` negates/swaps these, so define it here.
_YZ = Plane(origin=(0, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))

# ---------------------------------------------------------------------------
# Canopy parameters (self-contained; depend only on base geometry constants). The canopy is
# FUSED into the TOP cover (``case.build_top_part`` adds it): the ramp grows out of the cover
# surface and merges tangentially into it — no separate part, no standing tongue. Its body
# base drops one cover thickness so it OVERLAPS the cover/walls for a clean OCC union.
# ---------------------------------------------------------------------------
CANOPY_ROOF_WALL    = 1.5                       # roof + east-wall shell thickness
CANOPY_WEST_WALL    = 4.0                       # W wall thickness (case-like; thinned from 4.75
                                               #   so the west cavity clears the nice!nano's west edge)
CANOPY_ROOF_CLEAR   = 0.6                       # headroom over the USB-C body top
# N/W walls land FLUSH on the drafted rim facet's top line (outer wall face pulled IN by the
# facet's rim inset RIM_FACET_RUN): the wall's facet rises from its toe and meets the canopy
# face exactly at the rim, so wall → facet → canopy face reads as one continuous surface stack.
CANOPY_WEST_OUTER_X = (C.pcb_to_case(0, 0)[0] - C.WALL_THICKNESS - C.PCB_XY_CLEARANCE
                       + C.RIM_FACET_RUN)                                                   # ≈ 10.5
CANOPY_NORTH_OUTER_Y = (C.pcb_to_case(0, C.MCU_Y_RELIEF_TARGET_Y)[1]
                        + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE - C.RIM_FACET_RUN)           # ≈ 121.5
# The north wall is NOT free to pick its own thickness: its inner face is the bay's one north
# face (C.BAY_NORTH_INNER_Y), so the canopy continues the tray wall upward instead of stepping
# inboard of it. It used to share the west wall's 4.0, which put this face 1.25 mm proud of the
# tray's and drove the wall into the USB jack. Thickness is what falls out — 2.75 — not what is
# chosen. Still thicker than CANOPY_ROOF_WALL, and the overmold pocket is checked against it
# below (CANOPY_USB_OM_DEPTH) so the port cannot bore through into the bay.
CANOPY_NORTH_WALL   = CANOPY_NORTH_OUTER_Y - C.BAY_NORTH_INNER_Y                             # 2.75
assert CANOPY_NORTH_OUTER_Y - CANOPY_NORTH_WALL \
       - (C.MCU_BODY_N_Y + C.USB_JACK_Y_PROTRUDE) >= 0.5, "the jack is back in the wall"
CANOPY_EAST_X       = 34.6                       # switch-column boundary (bay east edge)
# Ramp foot: the slip merges DOWN into the cover surface (tangent, no raised tongue) AND lands
# on the encoder plateau's north face, so the open bay strip in front of the plateau is CLOSED
# (the "tongue gap" that reappeared when the canopy was fused) and the slip starts climbing
# early enough to clear the JST beneath it. The foot overlaps the plateau's flat stub by
# CANOPY_ENCODER_OVERLAP for a clean fuse (both are added to the TOP, so overlap just merges).
CANOPY_ENCODER_HALF    = 10.0   # encoder centre → plateau north face (measured)
CANOPY_ENCODER_OVERLAP = 1.0    # foot overlaps the plateau stub so the two fuse with no open strip
CANOPY_RAMP_FOOT_Y  = (C.pcb_to_case(*C.SW_ENCODER_POS)[1]
                       + CANOPY_ENCODER_HALF - CANOPY_ENCODER_OVERLAP)                       # ≈ 58.8
CANOPY_RAMP_TOP_OLED_GAP = 0.5
CANOPY_RAMP_TOP_Y   = C.pcb_to_case(*C.J_OLED_POS)[1] - CANOPY_RAMP_TOP_OLED_GAP            # ≈ 81.6
# The ramp is the cubic smoothstep 3t²−2t³ with horizontal tangents at both
# ends — an exact single cubic Bezier, not an interpolating Spline through samples.
# Its 4 control points are P0=(y0,z0), P1=(y0+L/3,z0), P2=(y1−L/3,z1), P3=(y1,z1)
# (Y is linear in the Bezier parameter, Z carries the smoothstep). That curve is
# used directly for the swept roofline (Bezier in _yz_prism / _west_chamfer_section),
# so there is NO ringing, NO deviation to tune, and minimal curvature for OCC's
# angular mesher.
#
# CANOPY_RAMP_SAMPLES survives only as a DEPRECATED alias for import compatibility
# and for _roofline's dense analytic sampling (used by _offset_roofline / puzzle
# depth queries). It no longer drives geometry — the ramp is one exact Bezier
# regardless. The old interpolating Spline rang 0.14 mm at 9 samples and still
# 0.032 mm at 25; densifying damped ~4× per 2× samples but OCC meshes by curvature,
# not deviation, and a denser interpolating spline traded deviation for high-frequency
# curvature wiggle. Measured on the bare prism, right half:
#
#     samples    9        15       25       41        51
#     deviation  0.143mm  0.073mm  0.032mm  —         0.0086mm
#     triangles  28,482   26,988   39,150   216,264   396,620
#     right STL  2.5 MB   —        3.9 MB   —         39.9 MB
#
# Past ~25 the mesh detonated for invisible gain (0.023 mm for 10× STL at 51).
# The exact Bezier has 0 deviation by construction and the lowest achievable
# curvature, so it does not detonate at any export tolerance. Do not reintroduce
# an interpolating Spline to chase flatness — re-measure the RIGHT half (shorter
# left never blew up, 2.76 mm lower) if touching this.
#
# NOTE: this number used to be load-bearing for the west top shoulder's facet — OCC's 3-D
# chamfer on that run silently stopped working above ~9 samples. That coupling is gone;
# _chamfer_west_top/_chamfer_east_top are booleans. Keep it that way.
CANOPY_RAMP_SAMPLES = 25  # deprecated: geometry is now an exact Bezier, not a sampled Spline
CANOPY_NORTH_ROUND_R = 1.0
# The north-top facet's DROP is that same number, and the equality is structural rather than tidy:
# CANOPY_NORTH_ROUND_R is what ``canopy_ridge_top_z`` budgets for the top edge eating into the north
# wall above the USB overmold pocket, so the treatment that actually eats it must not exceed it.
# (The name is historical — that edge was a round before it was a drafted facet.)
CANOPY_NORTH_FACET_DROP = CANOPY_NORTH_ROUND_R
# Lead-in of the west top shoulder's drafted facet: the cutter's vertical leg fades to 0 at the
# ramp foot, where the west wall is only (COVER_TOP_Z − MAIN_RIM_Z) = 1 mm tall, so the facet
# can never bite into the fuse overlap. Full depth is reached ~7 mm up the ramp (case-Y ≈ 65.7
# on the right half, 66.9 on the left — the shorter left ramp climbs slower per mm of Y).
# Heights. The ramp foot merges at the cover surface; the body base drops one cover thickness
# (to MAIN_RIM_Z) so it overlaps the cover/walls for a clean fuse into the TOP.
CANOPY_FOOT_Z       = C.COVER_TOP_Z                                # ramp foot = cover surface
CANOPY_FUSE_BASE_Z  = C.MAIN_RIM_Z                                 # base overlaps the cover for the fuse
# ---------------------------------------------------------------------------
# USB port STEPPED bore: overmold pocket (outer) → shell neck (inner).
# See constants.USB_PLUG_SHELL_L for why: the jack mouth sits well behind the outer face, so
# a straight shell-sized hole both blocks the overmold and starves the shell of engagement.
# ---------------------------------------------------------------------------
CANOPY_USB_OM_W = C.USB_OVERMOLD_W + C.USB_OVERMOLD_CLEAR      # 12.85; pocket width
CANOPY_USB_OM_H = C.USB_OVERMOLD_H + C.USB_OVERMOLD_CLEAR      # 7.00;  pocket height
# How far the plug must travel from the outer face before it reaches the jack, and how deep
# the pocket must therefore be so USB_PORT_ENGAGE_TARGET of shell ends up inside the jack.
CANOPY_USB_TRAVEL    = CANOPY_NORTH_OUTER_Y - (C.MCU_BODY_N_Y + C.USB_JACK_Y_PROTRUDE)       # 3.32
CANOPY_USB_OM_DEPTH  = C.USB_PORT_ENGAGE_TARGET - (C.USB_PLUG_SHELL_L - CANOPY_USB_TRAVEL)   # 1.67
# Minimum solid wall left above the pocket, measured where the north wall's top round-over
# starts eating material (at CANOPY_RIDGE_TOP_Z − CANOPY_NORTH_ROUND_R). Without this term
# a 7 mm-tall pocket breaks out through the rounded top shoulder and the port stops being a
# closed hole.
CANOPY_USB_OM_ROOF_MIN = 0.5
# The pocket is cut inward from the outer face, so it has to stop inside the wall — otherwise it
# breaks through into the bay and the "stepped bore" is just a hole. Free while the wall was 4.0;
# an assert now that the wall's thickness is derived rather than chosen.
assert CANOPY_USB_OM_DEPTH < CANOPY_NORTH_WALL, (
    f"the overmold pocket ({CANOPY_USB_OM_DEPTH:.2f}) bores through a "
    f"{CANOPY_NORTH_WALL:.2f} mm north wall")


def canopy_usb_om_z(side: str) -> tuple[float, float]:
    """(lo, hi) Z of the overmold POCKET for a half.

    Centred on the jack band: the plug's overmold is centred on its shell, and the shell is
    centred in the receptacle, so the pocket cannot be biased away from the jack centre."""
    lo, hi = C.usb_jack_z(side)
    mid = (lo + hi) / 2
    return mid - CANOPY_USB_OM_H / 2, mid + CANOPY_USB_OM_H / 2


# Roof height is derived PER HALF, so each half carries only as much material above its own
# port as the port needs — a common ridge left the flipped half with 2.76 mm of dead air above
# its (lower) port. Two independent constraints per half, whichever is taller:
#   1. the physical stack — on the FLIPPED half the nano board (21.4) stands taller than its
#      own jack (20.8), so a jack-only derivation would sink the roof underside into the board;
#   2. the overmold pocket — it must stay buried in solid wall, including under the top
#      round-over, or the plug's pocket opens into the roof shoulder.
def canopy_ridge_top_z(side: str) -> float:
    """Canopy roof height for a half — the taller of the physical-stack and overmold-pocket
    constraints, both evaluated against THIS half's own jack/pocket Z (see module comment)."""
    ridge_from_stack = (max(C.usb_jack_z(side)[1], C.MCU_PCB_TOP_Z)
                        + CANOPY_ROOF_CLEAR + CANOPY_ROOF_WALL)
    ridge_from_pocket = (canopy_usb_om_z(side)[1]
                         + CANOPY_NORTH_ROUND_R + CANOPY_USB_OM_ROOF_MIN)
    return max(ridge_from_stack, ridge_from_pocket)


# Kept as the tallest half's ridge: case.py's _slide_scoop uses it purely as a cut CEILING
# (removes only air above the roof), so over-reaching on the shorter half is harmless. This is
# the one place the two halves still share a number, and only because nothing downstream cares
# which half it came from.
CANOPY_RIDGE_TOP_Z = max(canopy_ridge_top_z(s) for s in ("left", "right"))   # 26.98
# NW corner radius = the case's own rounded corner AT the facet's rim line.
CANOPY_CORNER_R     = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE - C.RIM_FACET_RUN                # ≈ 3.25
# USB-C port through the north wall — REQUIRED: the plug must pass the wall (the jack itself
# stops 0.57 mm short of the inner face — C.USB_JACK_Y_PROTRUDE; it used to sit open over the
# +Y wall). Centred on the MCU X column. The BAND is per-half: the two MCU orientations put
# the jack at different Z, so left and right are NOT mirror images here (left 16.84→21.5,
# right 19.6→24.26; they overlap through 19.6→21.5). The design margins live in constants.py
# (USB_PORT_CLEAR_LO/HI, USB_PORT_W_CLEAR) — single source of truth, like the other CLEARs.
CANOPY_USB_W        = C.USB_C_W + C.USB_PORT_W_CLEAR               # 11.0; port width (jack + plug clearance)
# Port mouth corner radius. The opening is a ROUNDED rectangle, not a sharp one: it matches
# the plug overmold's own profile, kills four stress risers in a thin wall, and prints better
# — the arc at the top of the hole self-supports where a square corner needs a hard bridge.
# Clamped below half the port's short side (5.5 / 2) so the fillet can always be built; at the
# clamp the mouth degenerates to a stadium, which is still valid.
CANOPY_USB_R        = 1.5
# ---------------------------------------------------------------------------
# Roof PUZZLE strokes — two CURVES drawn across the ASSEMBLED pair, each crossing both canopies. The
# plan geometry (which curve, at what angle, in whose frame) belongs to ``canopy_puzzle``, which
# fitted the baseline from the design sketch; this half of the job is cutting the resulting
# POLYLINES into a surface that is flat for 40 mm and then tips over to 35.9°. Polylines, not
# segments: everything here reads a stroke as a sequence of points, so the shape of the mark and the
# plumbing that carries it stay independent — a two-point stroke is just the degenerate case.
#
# Two strokes CROSS THE RAMP (left line 1 and right line 0, the latter running its whole length),
# so depth cannot be measured vertically. The cutter is a
# footprint prism clipped against a NORMAL-offset copy of the roofline, which holds the depth
# perpendicular to the surface on the flat roof and on the slope alike — the same construction that
# built valid solids on both halves first time during the pattern trials.
#
# DEPTH is the load-bearing number: the roof shell is CANOPY_ROOF_WALL (1.5) over a cavity that
# follows the roofline, so a groove eats that wall and nothing else. 0.5 leaves 1.0 mm, five layers
# at 0.2. The assert is the point — it is why the depth is derived against CANOPY_ROOF_WALL rather
# than written as a bare 0.5.
#
# WIDTH is 1.0, down from the 1.6 the mark inherited from the diagonal reveal it grew out of. Two
# reasons, one aesthetic and one measured. A curve reads as a drawn line at a narrower width than a
# straight slot does — 1.6 mm of curve on an 18 mm strip reads as a channel — and the north exit is
# scored against the groove's own width, so narrowing it is what buys the corner clearance: the
# tilt-corrected NW-corner margin goes 0.36 → 0.66 mm. 1.0 is 2.5 extrusion widths at a
# 0.4 mm nozzle, which is the floor for a groove that has to read as a line rather than a scratch.
# ``ENCODER_GROOVE_W`` deliberately does NOT follow it — see the comment there.
#
# 0.5 IS THE CAP, NOT THE DEPTH. It is what the FLAT roof can spend; on the ramp the groove gets less,
# and the reason is that the cavity is offset straight DOWN in Z (``cav_roof`` in ``build_canopy``),
# not along the surface normal. So measured perpendicular — the direction a groove actually eats — the
# ramp shell is only CANOPY_ROOF_WALL·cos θ: 1.23 mm at the right half's steepest 34.9°, where a
# full-depth groove would leave 0.73 mm of a roof that is supposed to keep 1.0. Nothing caught this
# before because the only stroke that crossed the ramp did so near the top, at 0.96 mm — under the
# limit, and invisible. ``puzzle_depth_at`` is that arithmetic, done once.
CANOPY_PUZZLE_W        = 1.0      # groove width — see below; the encoder's groove keeps its own 1.6
CANOPY_PUZZLE_DEPTH    = 0.5      # the CAP — see puzzle_depth_at for what a groove gets where
CANOPY_PUZZLE_MIN_ROOF = 1.0      # solid roof that must survive under a groove
assert CANOPY_PUZZLE_DEPTH <= CANOPY_ROOF_WALL - CANOPY_PUZZLE_MIN_ROOF + 1e-9, (
    f"a {CANOPY_PUZZLE_DEPTH} mm groove leaves "
    f"{CANOPY_ROOF_WALL - CANOPY_PUZZLE_DEPTH} mm of a {CANOPY_ROOF_WALL} mm roof"
)
# Safe region. The strokes are defined for the assembled keyboard and simply STOP here, which is how
# the continuation stays literal (one line) while the terminals stay inset.
# WEST measures from the roof edge the shoulder facet leaves, not the raw wall, so re-proportioning
# that facet pushes the strokes back instead of letting them cut into it. NORTH is structural: only
# CANOPY_NORTH_ROUND_R + CANOPY_USB_OM_ROOF_MIN of solid sits above the USB overmold pocket. SOUTH
# stops short of the ramp foot so no groove spills onto the cover surface — a keep-out written for a
# FIXED-depth groove, and the reason the curve is allowed past it: see CANOPY_PUZZLE_SOUTH_KO.
CANOPY_PUZZLE_LAND     = 2.4
CANOPY_PUZZLE_NORTH_KO = CANOPY_NORTH_ROUND_R + 0.5 + 1.5      # 3.0; the 0.5 is USB_OM_ROOF_MIN
CANOPY_PUZZLE_SOUTH_KO = 1.5   # ...for the STRAIGHT layout the span is derived from. What is cut
#                                gets down to the foot itself (``y0_ramp``), which is safe only
#                                because ``puzzle_depth_at`` has faded the groove to zero by then.
# EAST is the one exception, and it is the design's: a half's UPPER stroke may run OUT through the
# east wall — the wall bordering the switch columns — so it lands against something instead of
# stopping 2.4 mm short in open roof. The east arris IS broken there, on purpose. Once in the PAIR
# today, on the right half: at PUZZLE_CURVE_A = 4.75 the bow lifts the left half's upper stroke
# 3.2 mm short of that wall, which was a known cost of the amplitude and not a regression.
#
# The endpoint is put a clear margin PAST the wall rather than on it: the cutter's ends are square,
# so an endpoint sitting exactly on x = CANOPY_EAST_X would leave the break at the mercy of boolean
# tolerance — a groove that ends flush with the face it is supposed to open into. One groove width
# past is unambiguous and costs nothing, since everything beyond the wall is air.
CANOPY_PUZZLE_EAST_BREAK = CANOPY_PUZZLE_W                     # 1.0 past CANOPY_EAST_X
assert CANOPY_PUZZLE_EAST_BREAK > CANOPY_PUZZLE_W / 2, \
    "the upper stroke would not clearly clear the east wall"
# WEST is the gap-facing side — the one the assembled pair's strokes cross between the halves — so
# every stroke is aimed OUT through it, past the wall line. What that actually produces is a groove
# that runs over the west shoulder's top arris and stops there: the facet falls away from the swept
# roofline at 2:1, so the cutter stops biting ~0.25 mm past the arris. The mark reaches the roof's
# west edge and disappears over the shoulder, which is the read we want at the gap.
CANOPY_PUZZLE_WEST_BREAK = CANOPY_PUZZLE_W
# NORTH is aimed past the wall for the same reason as west, and produces the same terminal: the
# groove holds full depth to the facet's top line and fades out over the next 0.25 mm as the facet
# drops from under the cutter. Measured, both edges on the right half: 0.5 / 0.35 / 0.15 / 0.0 at the
# top line and 0.1 / 0.2 / 0.3 mm past it. They match because both facets are 2:1.
#
# What the overshoot buys is the absence of a square end ON the roof: a stroke stopped at the facet's
# top line ends in a flat wall a hair short of the edge, and reads as a groove that gave up. Aim it
# past, and the edge is what ends it.
CANOPY_PUZZLE_NORTH_BREAK = CANOPY_PUZZLE_W
# NORTH is the exception, and it is deliberate. One stroke (today the right half's line 0) is aimed
# too far north to reach the west wall — heading gap-ward it climbs — so it leaves at the NW corner
# instead. It is stopped ON the north chamfer's TOP LINE (CANOPY_NORTH_OUTER_Y − h): it borders the
# chamfer, it does not cross it and it does not run through the corner. Sent past that line it drags
# the mark across the NW corner round and up to the USB overmold pocket, whose roof budget is
# CANOPY_USB_OM_ROOF_MIN (0.5 mm) — exactly what a groove spends.
#
# ``canopy_puzzle_strokes`` still checks the pocket clearance, because this bound is what keeps that
# stroke off it: at another separation the same line lands further east, over the pocket.
CANOPY_PUZZLE_POCKET_GAP = 1.0     # min mm between a stroke's edge and the USB pocket's side


def canopy_puzzle_region(side: str) -> tuple[float, float, float, float]:
    """(x0, x1, y0, y1) of the strokeable patch on the roof + ramp, margins applied.

    The EAST bound here is the inset one, which the LOWER stroke keeps; the upper stroke overrides it
    with ``canopy_puzzle_north_x1`` and breaks out through the wall."""
    facet_h = canopy_top_chamfer(side)[1]
    return (CANOPY_WEST_OUTER_X + facet_h + CANOPY_PUZZLE_LAND,
            CANOPY_EAST_X - CANOPY_PUZZLE_LAND,
            CANOPY_RAMP_FOOT_Y + CANOPY_PUZZLE_SOUTH_KO,
            CANOPY_NORTH_OUTER_Y - CANOPY_PUZZLE_NORTH_KO)


def canopy_puzzle_north_x1() -> float:
    """East bound for the UPPER stroke — past the east wall, so that stroke terminates in it."""
    return CANOPY_EAST_X + CANOPY_PUZZLE_EAST_BREAK


def canopy_north_chamfer(side: str) -> tuple[float, float]:
    """(run, drop) of the north-top drafted facet — the same 2:1 style as the case rim and as the
    west shoulder facet, but SMALLER, and the size is derived rather than chosen.

    DROP is the binding leg, because it is what eats the north wall's top: the wall's outer face
    starts ``drop`` below the ridge, and the USB overmold pocket's top has to stay under that with
    CANOPY_USB_OM_ROOF_MIN to spare. ``canopy_ridge_top_z`` already budgets exactly
    CANOPY_NORTH_ROUND_R of top-edge eat when it sizes the roof against that pocket — so the facet's
    drop IS that budget. Spending more is not free: a 2.4 mm drop (matching the west facet leg for
    leg) puts the wall's top face 0.9 mm BELOW the pocket, i.e. the port mouth opens into the facet,
    and buying that back costs 1.40 mm of ridge height on both halves.

    RUN then follows from the case's own facet proportion, so the two bands differ in size but not
    in angle — which is the match that was actually available. The assert is the point: it is why
    the drop is derived from the pocket rather than written as a bare 1.0.

    Before this was derived, the north chamfer measured 2.4 run / 1.2 drop — the reciprocal of the
    west facet — because ``_yz_prism`` let OCC pick the leg order. See ``occ-chamfer-leg-order``."""
    drop = CANOPY_NORTH_FACET_DROP
    head = canopy_ridge_top_z(side) - drop - canopy_usb_om_z(side)[1]
    assert head >= CANOPY_USB_OM_ROOF_MIN - 1e-9, (
        f"{side}: a {drop} mm north facet leaves {head:.2f} mm over the USB pocket, "
        f"under the {CANOPY_USB_OM_ROOF_MIN} mm minimum"
    )
    return drop * C.RIM_FACET_RUN / C.RIM_FACET_DROP, drop


def canopy_north_chamfer_run(side: str) -> float:
    """How far inboard of the north wall the flat roof stops — i.e. the facet's top line.

    One place for consumers to ask, because this is not ``canopy_top_chamfer``'s leg: the north
    facet and the west facet share an angle, not a size. ``canopy_puzzle_strokes`` stops a stroke
    on this line."""
    return canopy_north_chamfer(side)[0]


def canopy_puzzle_north_exit_window() -> tuple[float, float]:
    """(x_min, x_max) on the north chamfer's top line where a stroke may leave the roof.

    WEST bound — the NW corner. The corner round is tangent to the north wall at
    ``CANOPY_WEST_OUTER_X + CANOPY_CORNER_R``, and the chamfer top lines are inset from both walls by
    the same horizontal leg, so the flat roof's north edge is STRAIGHT only east of that same X. A
    stroke leaving west of it exits over the corner's curve, into the one place on the part where the
    west facet, the north chamfer and the corner round already meet. The whole groove width has to
    clear it, not just the centreline.

    EAST bound — the USB overmold pocket, whose roof budget is CANOPY_USB_OM_ROOF_MIN (0.5 mm).

    This is the window ``PUZZLE_LINE_NUDGE`` was solved against; it is stated here, in the module
    that owns the keep-outs, so the nudge can be re-derived rather than re-guessed."""
    return (CANOPY_WEST_OUTER_X + CANOPY_CORNER_R + CANOPY_PUZZLE_W / 2,
            C.pcb_to_case(*C.MCU_POS)[0] - CANOPY_USB_OM_W / 2
            - CANOPY_PUZZLE_W / 2 - CANOPY_PUZZLE_POCKET_GAP)


def canopy_puzzle_strokes(side: str) -> list[Stroke]:
    """This half's two stroke segments, in its own un-mirrored canopy coords.

    West is aimed past the wall (the groove runs off the shoulder there); north stops ON the chamfer
    top line, bordering it.

    The NORTH bound is CONDITIONAL, and that is the interesting part: letting a stroke up to the
    north chamfer puts its terminal inside the band the north keep-out exists to protect. It is
    allowed only where the exit lands in ``canopy_puzzle_north_exit_window`` — east of the NW
    corner's curve and west of the USB overmold pocket. Outside that window the stroke keeps the
    plain north keep-out and stops inboard, which is worse-looking but never wrong.

    Checked, not assumed. The layout is a fitted input, ``PUZZLE_LINE_NUDGE`` is a hand-set number,
    and this is the one keep-out whose violation would stay invisible until a plug went in."""
    return _puzzle_strokes(side, PZ.strokes, y0_ramp=CANOPY_RAMP_FOOT_Y)


def straight_puzzle_strokes(side: str) -> list[Stroke]:
    """The same clip, on the FITTED STRAIGHT layout instead of the curve.

    Not cut any more. It exists because ``canopy_puzzle.PUZZLE_CURVE_SPAN`` — the parameterisation the
    curve's whole shape hangs off — is derived from this layout, and the derivation has to include the
    conditional north break, which lives here rather than in ``canopy_puzzle``. Deriving the span from
    anything else (the raw region chords, say) produces a different mark: line A's span comes out
    89.5 mm instead of 62.2 and the same amplitude then reads as a straight line."""
    return _puzzle_strokes(side, PZ.straight_strokes)


def _puzzle_strokes(side: str, source, **extra) -> list[Stroke]:
    """The clip, shared by the curve and by the straight layout it is parameterised against.

    ``extra`` is what the two do NOT share: the curve is allowed down to the ramp foot, the straight
    layout is not — because ``PUZZLE_CURVE_SPAN`` is derived from the straight layout, and letting an
    allowance made for the curve change the span the curve is built on would move the mark every time
    the allowance was re-tuned."""
    region = canopy_puzzle_region(side)
    common = dict(x1_north=canopy_puzzle_north_x1(),
                  x0_break=CANOPY_WEST_OUTER_X - CANOPY_PUZZLE_WEST_BREAK, **extra)
    segs = source(side, *region, **common,
                  y1_break=CANOPY_NORTH_OUTER_Y + CANOPY_PUZZLE_NORTH_BREAK)
    if not _puzzle_north_exit_ok(segs):
        segs = source(side, *region, **common)
        assert _puzzle_north_exit_ok(segs), \
            f"{side}: a stroke reaches the north keep-out band even without the north break"
    return segs


def puzzle_north_crossings(segs: Sequence[Stroke]) -> list[float]:
    """X where each stroke crosses the north WALL — not where its segment happens to end.

    The endpoint sits a break's-worth past the wall, so measuring the terminal would read a position
    the groove never occupies on the part: the stroke is tilted, so the overshoot also slides it west,
    by 0.2 mm per mm here. Every judgement about where the mark leaves the part — corner clearance,
    pocket clearance — has to be made at the wall.

    Walks each stroke SEGMENT BY SEGMENT rather than end to end. For a two-point stroke that is the
    same arithmetic; for a polyline it is the only version that is true, and it reports a stroke that
    crosses the wall twice as two crossings instead of silently reading the chord."""
    out = []
    for seg in segs:
        for (x0, y0), (x1, y1) in zip(seg, seg[1:]):
            if max(y0, y1) >= CANOPY_NORTH_OUTER_Y > min(y0, y1):
                out.append(x0 + (x1 - x0) * (CANOPY_NORTH_OUTER_Y - y0) / (y1 - y0))
    return out


def _puzzle_north_exit_ok(segs: Sequence[Stroke]) -> bool:
    """Does every stroke that leaves through the north wall do it inside the safe window?

    The pocket-band check is on the TERMINALS, which is what it was always about: a stroke that stops
    inside the band sits over the USB overmold pocket, while a stroke that merely passes through the
    band on its way out through the wall is exactly the case the window exists to allow. Reading
    every point of a polyline here would reject that legal case.

    THE TILT IS APPLIED HERE, not in the window. A stroke meets the north wall at an angle, so the
    groove's footprint measured ALONG that wall is ``(w/2)/sin θ`` per side, not ``w/2``: line A
    crosses at 78.6°, which is 0.51 mm rather than 0.50. The window states the keep-out and cannot
    know the angle; this function has the segment that crosses, so it is the one that can correct for
    it. Worth only 0.01 mm per side against today's 0.66 mm corner margin — but the correction is
    unbounded as a stroke flattens against the wall, and a curved mark's crossing angle is a
    consequence of the amplitude rather than a fixed property of the layout."""
    x_lo, x_hi = canopy_puzzle_north_exit_window()
    if any(CANOPY_NORTH_OUTER_Y - CANOPY_USB_OM_DEPTH < y < CANOPY_NORTH_OUTER_Y
           for seg in segs for _x, y in (seg[0], seg[-1])):
        return False              # a terminal loitering INSIDE the pocket band, not crossing it
    for seg in segs:
        for (x0, y0), (x1, y1) in zip(seg, seg[1:]):
            if not (max(y0, y1) >= CANOPY_NORTH_OUTER_Y > min(y0, y1)):
                continue
            x = x0 + (x1 - x0) * (CANOPY_NORTH_OUTER_Y - y0) / (y1 - y0)
            leg = math.hypot(x1 - x0, y1 - y0)
            half = (CANOPY_PUZZLE_W / 2) / max(abs(y1 - y0) / leg, 1e-6)
            if not (x_lo - CANOPY_PUZZLE_W / 2 + half <= x <= x_hi + CANOPY_PUZZLE_W / 2 - half):
                return False
    return True


def canopy_usb_z(side: str) -> tuple[float, float]:
    """(lo, hi) Z of the north-wall USB port for a half — delegates to ``C.usb_port_z``
    (measured jack band + USB_PORT_CLEAR_* margins); kept as the canopy-local call name."""
    return C.usb_port_z(side)


def usb_port_cutter(side: str) -> Part:
    """The north-wall USB port cutter box for a half, centred on the MCU X column.

    Subtracted TWICE, deliberately. ``build_canopy`` cuts it so the standalone canopy is
    complete on its own, and ``case.build_top_part`` cuts it AGAIN after the cover is fused
    on. The second pass USED to be load-bearing: with the old 4.0 mm jack model the FLIPPED
    half's port floor was 15.6, below ``COVER_TOP_Z`` (16.0), so the cover fuse backfilled
    the bottom of the window. The mid-mount correction lifted that floor to 16.84, clear of
    the cover, so today both halves would survive a single cut. The second pass is KEPT: it
    is idempotent, it costs one boolean, and it is the only thing standing between a future
    band/cover change and a silently half-filled port. Same reason ``_slide_scoop`` is cut
    post-fuse."""
    ucx = C.pcb_to_case(*C.MCU_POS)[0]

    def _bore(w: float, lo: float, hi: float, y0: float, y1: float) -> Part:
        """One rounded-rectangle bore section, w × (hi−lo), spanning y0→y1."""
        b = cast(Part, Solid.make_box(w, y1 - y0, hi - lo).translate((ucx - w / 2, y0, lo)))
        # Round the four mouth corners: the edges running along Y (the bore axis), so the
        # rounding shows on the X–Z opening the plug enters. Filleted on the ISOLATED box —
        # same reason as _slide_scoop, a 3-D fillet on the boolean result is fragile.
        r = min(CANOPY_USB_R, (hi - lo) / 2 - 1e-3, w / 2 - 1e-3)
        axial = [e for e in b.edges() if abs(e.tangent_at(0.5).Y) > 0.9]
        try:
            b = cast(Part, fillet(axial, radius=r))
        except (ValueError, Standard_Failure):
            pass   # never abort the port over its cosmetic rounding; a square mouth still fits
        return b

    # NECK — shell-sized, runs the whole way through (and 1 mm proud on each side so the
    # boolean never leaves a skin).
    lo, hi = canopy_usb_z(side)
    neck = _bore(CANOPY_USB_W, lo, hi,
                 (CANOPY_NORTH_OUTER_Y - CANOPY_NORTH_WALL) - 1.0, CANOPY_NORTH_OUTER_Y + 1.0)
    # POCKET — overmold-sized, only the outer CANOPY_USB_OM_DEPTH of the wall. This is what
    # buys the shell its engagement: without it the overmold stops dead on the outer face.
    plo, phi = canopy_usb_om_z(side)
    pocket = _bore(CANOPY_USB_OM_W, plo, phi,
                   CANOPY_NORTH_OUTER_Y - CANOPY_USB_OM_DEPTH, CANOPY_NORTH_OUTER_Y + 1.0)
    box = cast(Part, neck + pocket)
    return box


# The WEST shoulder facet's legs: the same drafted-facet STYLE as the case rim (slope run/drop).
# Derived per half, because each half has its own ridge.
def canopy_top_chamfer(side: str) -> tuple[float, float]:
    """(V, H) legs of the WEST top shoulder facet for a half.

    This used to size the north-top chamfer as well, which is why the clamp below is written against
    the USB port — a leg on the NORTH wall had to stop above the port mouth. The north edge has its
    own, smaller facet now (``canopy_north_chamfer``, sized against the overmold pocket), and the
    west wall has no port in it, so the clamp is not binding here today: it yields 2.4 on both halves
    against a limit of 2.52. It is kept because it is still a true statement about how much wall
    there is to cut, and dropping it would let a future ridge change eat this facet silently."""
    v = min(2.4, canopy_ridge_top_z(side) - canopy_usb_z(side)[1] - 0.2)   # vertical leg
    h = v * C.RIM_FACET_RUN / C.RIM_FACET_DROP                            # horizontal leg
    assert v > 0.5, f"USB port leaves no room for the canopy roof chamfer ({side})"
    return v, h


def _smoothstep(y0: float, z0: float, y1: float, z1: float, n: int) -> list[tuple[float, float]]:
    """Interior points of a cubic smoothstep (3t²−2t³) from (y0,z0) to (y1,z1).

    Horizontal-tangent at BOTH ends, so the ramp merges into the flat cover at the foot and
    into the flat roof at the top with no crease at either — the slip grows seamlessly out of
    the cover surface. Endpoints omitted; the caller supplies them.

    Kept for dense analytic sampling (_roofline / _offset_roofline / depth queries).
    Geometry itself is now an exact single cubic Bezier (see _ramp_bezier_poles), not an
    interpolating Spline through these samples, so this function no longer determines
    curvature or mesh density."""
    out = []
    for i in range(1, n - 1):
        t = i / (n - 1)
        out.append((y0 + (y1 - y0) * t, z0 + (z1 - z0) * (3 * t * t - 2 * t ** 3)))
    return out


def _ramp_bezier_poles(y0: float, z0: float, y1: float, z1: float) -> list[tuple[float, float]]:
    """4 control points of the EXACT cubic smoothstep Bezier from (y0,z0) to (y1,z1).

    With horizontal tangents at both ends the Hermite form is a single cubic and
    the Bezier representation is P0=(y0,z0), P1=(y0+L/3,z0), P2=(y1−L/3,z1), P3=(y1,z1)
    where L=y1−y0. Y is linear in the Bezier parameter (so t = (Y−y0)/L), Z carries
    3t²−2t³ exactly — 0 deviation, minimal curvature, and no ringing. Used directly
    by _yz_prism and _west_chamfer_section instead of Spline(*sampled points)."""
    L = y1 - y0
    return [(y0, z0), (y0 + L / 3.0, z0), (y1 - L / 3.0, z1), (y1, z1)]


def _dedup(pts: list[tuple[float, float]], tol: float = 1e-4) -> list[tuple[float, float]]:
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) > tol or abs(p[1] - out[-1][1]) > tol:
            out.append(p)
    return out


def _yz_prism(top_pts: list[tuple[float, float]], z_base: float, x_lo: float, x_width: float,
              fillets_2d: list[tuple[float, float, float]] | None = None,
              spline_range: tuple[float, float] | None = None,
              north_chamfer: tuple[float, float] | None = None) -> Part:
    """Extrude a Y–Z profile (flat base at ``z_base`` closed by the ``top_pts`` edge, ordered
    by ascending Y) along +X by ``x_width``, positioned so its −X face sits at ``x_lo``.

    ``fillets_2d`` rounds the profile vertex at each ``(y, z, r)`` in 2-D.

    ``north_chamfer`` ``(run, drop)`` DRAWS the north-top drafted facet into the profile: the roof
    stops ``run`` short of the wall and a straight segment falls to ``drop`` below the ridge on the
    wall face. Drawn, not cut with ``chamfer()``, and that is the whole point — the previous version
    passed ``(v, h)`` to OCC and tried the other order, then the symmetric leg, then a fillet,
    accepting whichever did not throw. It never threw, and it never applied the legs as intended
    either: the shipped north chamfer measured 2.4 mm of run against 1.2 mm of drop, the reciprocal
    of the west shoulder facet it is supposed to match. A wrong-but-successful chamfer is invisible;
    two explicit points cannot be misread. See ``occ-chamfer-leg-order``.

    ``spline_range`` ``(y0, y1)`` draws the ramp between those Y as a single exact
    cubic **Bezier** (``_ramp_bezier_poles`` — the analytic 3t²−2t³ with horizontal
    tangents, 0 deviation, minimal curvature) so the swept surface has no facet steps;
    the rest of the profile stays straight ``Line`` segments. The dense sampled list
    in ``top_pts`` is kept only for analytic queries; geometry no longer interpolates
    through it."""
    top = _dedup(top_pts)
    y_lo, y_hi = top[0][0], top[-1][0]
    z_top = top[-1][1]
    assert north_chamfer is None or spline_range is not None, \
        "the north facet is only drawn on the splined (roofline) profile"
    with BuildPart() as bp:
        with BuildSketch(_YZ) as sk:
            with BuildLine():
                if spline_range is None:
                    Polyline((y_lo, z_base), *top, (y_hi, z_base), close=True)
                else:
                    y0, y1 = spline_range
                    # Exact Bezier poles from the analytic endpoints at y0/y1, not from the
                    # dense sampled ramp list — the list is for _offset_roofline queries.
                    # Find Z at the ramp ends from top_pts (body: foot→ridge, cavity: offset,
                    # puzzle inner: normal-offset). Search exact match, fall back to nearest.
                    def _z_at(target_y: float) -> float:
                        for yy, zz in top:
                            if abs(yy - target_y) < 1e-6:
                                return zz
                        # No exact Y (e.g. offset list with same Y range) — nearest
                        return min(top, key=lambda p: abs(p[0] - target_y))[1]
                    z0, z1 = _z_at(y0), _z_at(y1)
                    after = [p for p in top if p[0] > y1 + 1e-6]
                    # South face: base to ramp foot
                    Line((y_lo, z_base), (y0, z0))              # south face (buried in the cover)
                    # The exact ramp — one cubic Bezier, 0 ringing, minimal curvature for OCC mesher
                    ramp_poles = _ramp_bezier_poles(y0, z0, y1, z1)
                    Bezier(*ramp_poles)
                    if north_chamfer is None:
                        if after:
                            Polyline((y1, z1), *after)                       # flat roof
                        Line(after[-1] if after else (y1, z1), (y_hi, z_base))  # north wall
                    else:
                        run, drop = north_chamfer
                        assert y1 < y_hi - run, \
                            f"a {run} mm north facet run swallows the flat roof"
                        Polyline((y1, z1), (y_hi - run, z_top))              # flat roof, cut short
                        Line((y_hi - run, z_top), (y_hi, z_top - drop))      # the facet itself
                        Line((y_hi, z_top - drop), (y_hi, z_base))           # north wall
                    Line((y_hi, z_base), (y_lo, z_base))          # base
            make_face()
            for fy, fz, r in (fillets_2d or []):
                verts = [v for v in sk.vertices()
                         if abs(v.X - fy) < 0.05 and abs(v.Y - fz) < 0.05]
                if verts:
                    try:
                        fillet(verts, radius=r)
                    except (ValueError, Standard_Failure):
                        pass
            if north_chamfer is not None:
                # Cheap proof that the facet is the shape asked for. It is drawn, so this can only
                # fail if make_face/fillet moved it — but the shipped bug was a chamfer silently
                # applying the reciprocal slope, so the shape gets measured either way.
                run, drop = north_chamfer
                for want in ((y_hi - run, z_top), (y_hi, z_top - drop)):
                    assert any(abs(v.X - want[0]) < 1e-6 and abs(v.Y - want[1]) < 1e-6
                               for v in sk.vertices()), \
                        f"north facet vertex {want} missing — run/drop are not {run}/{drop}"
        extrude(amount=x_width)
    assert bp.part is not None
    return cast(Part, Pos(x_lo, 0, 0) * bp.part)


def _roofline(z_ridge: float) -> list[tuple[float, float]]:
    """The Y–Z top edge, south → north, for a canopy whose roof sits at ``z_ridge``: the ramp
    foot merges into the cover surface (no tongue) → a tangent S-curve slip up → flat roof.
    The near-vertical north wall comes from the base closure (its top corner is rounded by
    CANOPY_NORTH_ROUND_R). ``z_ridge`` is per-half (see ``canopy_ridge_top_z``), so the ramp's
    rise — and with it the spline's ringing amplitude — differs between halves."""
    z_foot = CANOPY_FOOT_Z
    roof = [(CANOPY_RAMP_FOOT_Y, z_foot)]
    roof += _smoothstep(CANOPY_RAMP_FOOT_Y, z_foot, CANOPY_RAMP_TOP_Y, z_ridge,
                        CANOPY_RAMP_SAMPLES)
    roof += [(CANOPY_RAMP_TOP_Y, z_ridge), (CANOPY_NORTH_OUTER_Y, z_ridge)]
    return roof


def _canopy_roof_z(y: float, z_ridge: float) -> float:
    """Outer roof Z at case-Y ``y`` along the swept roofline (south ramp S-curve → flat ridge)
    for a canopy whose roof sits at ``z_ridge``, matching ``_roofline`` / ``_smoothstep`` so the
    funnel mouth anchors to the actual sloped surface above RSW1 rather than to a fixed height.

    ``z_ridge`` has NO default on purpose: ``CANOPY_RAMP_TOP_Y`` (81.6) sits inside the ramp,
    not on the flat roof, so a caller that forgets to pass the per-half ridge silently samples
    the wrong half's slope — the exact bug this signature is designed to force a fix for."""
    y0, y1 = CANOPY_RAMP_FOOT_Y, CANOPY_RAMP_TOP_Y
    z0 = CANOPY_FOOT_Z
    if y <= y0:
        return z0
    if y >= y1:
        return z_ridge
    t = (y - y0) / (y1 - y0)
    return z0 + (z_ridge - z0) * (3 * t * t - 2 * t ** 3)


def _round_nw_corner(part: Part, x_w: float, y_n: float, r: float, z0: float, z1: float) -> Part:
    """Round the vertical NW corner (west wall ∩ north wall) to radius ``r`` by boolean —
    subtract the sharp sliver outside the corner arc. Robust where a 3-D ``fillet`` fails
    because it collides with the north round-over. Matches the case's own corner radius at the
    chamfer-first line the cap sets on.

    This was briefly replaced by a flat diagonal chamfer, on the theory that a vertical cylinder
    is non-tangent to the sloped north-top chamfer above it and so forces OCC to patch the seam
    with a visible kink. That kink was real but MISATTRIBUTED: it was measured on a body whose
    west-top shoulder facet was silently missing (``_round_west_top_edges`` had been no-oping —
    see ``_chamfer_west_top``), so the cylinder was running into a raw square shoulder instead of
    the drafted facet it is meant to meet. With the west facet actually cut, the round is back —
    it is the case's own corner language, and the flat mitre was a style regression."""
    h = z1 - z0
    box = cast(Part, Solid.make_box(r, r, h).translate((x_w, y_n - r, z0)))
    cyl = cast(Part, Solid.make_cylinder(r, h).translate((x_w + r, y_n - r, z0)))
    sliver = cast(Part, box - cyl)                    # the sharp corner outside the arc
    return cast(Part, part - sliver)


def _round_ne_corner(part: Part, x_e: float, y_n: float, r: float, z0: float, z1: float) -> Part:
    """Round the vertical NE corner (east wall ∩ north wall) to radius ``r`` by boolean —
    the mirror of ``_round_nw_corner``.

    The NE corner was historically left sharp while the NW was rounded to the case's own
    corner radius. Rounding both makes the roof read as one continuous north edge rather
    than a one-sided treatment, and it keeps the two top corners speaking the same language
    as the tray's outer corners. Robust where a 3-D ``fillet`` fails for the same reason as
    the NW.

    The geometry mirrors NW: the sliver is the square ``[x_e-r, x_e] × [y_n-r, y_n]`` minus
    the quarter-cylinder centred at its SW corner (``x_e-r, y_n-r``), i.e. the area outside
    the arc at the outer NE corner."""
    h = z1 - z0
    box = cast(Part, Solid.make_box(r, r, h).translate((x_e - r, y_n - r, z0)))
    cyl = cast(Part, Solid.make_cylinder(r, h).translate((x_e - r, y_n - r, z0)))
    sliver = cast(Part, box - cyl)                    # the sharp corner outside the arc
    return cast(Part, part - sliver)


# How far beyond the wall face the chamfer cutter starts. Purely to avoid a coincident-face
# boolean at the wall (the cutter's own boundary landing exactly on the wall it cuts); the
# extra reach reduces to air, so any value > 0 gives the same result.
_WEST_CHAMFER_PAD = 1.0
_EAST_CHAMFER_PAD = 1.0


def _west_chamfer_section(roof: list[tuple[float, float]], k: float, v: float,
                           z_ceil: float) -> Face:
    """One loft section for the shoulder chamfer cutters: the Y–Z region ABOVE the roofline
    pushed DOWN by ``k * v_eff(y)``, closed off at ``z_ceil``.

    ``v_eff`` clamps the vertical leg to the wall's own height above the cover surface, so the
    facet fades to nothing at the ramp foot where the wall is only 1 mm tall — without it
    the cut would eat the fuse overlap between MAIN_RIM_Z and COVER_TOP_Z. The ramp is the
    exact single cubic Bezier (``_ramp_bezier_poles``) through the body's roofline, so the
    cutter tracks the surface without sampling density dependence."""
    def lower(y: float, z: float) -> tuple[float, float]:
        v_eff = min(v, max(0.0, z - CANOPY_FOOT_Z))
        return y, z - k * v_eff

    y0, y1 = CANOPY_RAMP_FOOT_Y, CANOPY_RAMP_TOP_Y
    # Z at ramp ends from the roof list (before lowering) — then lower the Bezier poles
    def _z_at(target_y: float) -> float:
        for yy, zz in roof:
            if abs(yy - target_y) < 1e-6:
                return zz
        return min(roof, key=lambda p: abs(p[0] - target_y))[1]
    z0_raw, z1_raw = _z_at(y0), _z_at(y1)
    # Exact Bezier poles for the ramp, lowered
    lower_poles = [lower(y, z) for y, z in _ramp_bezier_poles(y0, z0_raw, y1, z1_raw)]
    # After: flat roof north of the ramp, lowered
    after = [lower(y, z) for y, z in roof if y > y1 + 1e-6]
    # y extents from lowered poles + after (for ceiling closure)
    y_lo = lower_poles[0][0]
    y_hi = after[-1][0] if after else lower_poles[-1][0]
    with BuildSketch(_YZ) as sk:
        with BuildLine():
            Bezier(*lower_poles)
            if after:
                if len(after) == 1:
                    Line(lower_poles[-1], after[0])
                else:
                    Polyline(lower_poles[-1], *after)
                Line(after[-1], (y_hi, z_ceil))
            else:
                Line(lower_poles[-1], (y_hi, z_ceil))
            Line((y_hi, z_ceil), (y_lo, z_ceil))
            Line((y_lo, z_ceil), lower_poles[0])
        make_face()
    return cast(Face, sk.sketch.faces()[0])


def _chamfer_west_top(part: Part, x_w: float, z_ridge: float,
                      chamfer_v: float, chamfer_h: float) -> Part:
    """Cut the drafted facet on the WEST top shoulder (roof/ramp ↔ west wall) so the tall west
    side carries the same facet style as the case walls. Mirrored by ``_chamfer_east_top``
    on the east side. Done on the SOLID envelope, before hollowing, where
    there is full material below the cut; the cavity is set in one wall thickness so it never
    reaches it.

    A BOOLEAN, not a 3-D edge chamfer. The previous ``chamfer(edges, ...)`` version silently
    no-oped: OCC rejects a chamfer on the west cap's top edges once the ramp's ``Spline`` is
    interpolated through many control points, and every fallback (both asymmetric orders, the
    symmetric leg, four fillet radii) failed too, so the function returned the part untouched
    and the facet vanished with no error. Measured: it worked at CANOPY_RAMP_SAMPLES = 9 and at
    NO tested value from 13 up — i.e. it was a hidden coupling between the ramp's smoothness and
    the west shoulder's style, which is not a tradeoff worth having.

    Instead: ruled-loft a cutter between two Y–Z sections, one at ``x_w − _WEST_CHAMFER_PAD``
    pushed down by the full leg and one at ``x_w + chamfer_h`` pushed down by nothing. Ruling
    linearly in X between them IS the facet plane (drop ``chamfer_v`` per ``chamfer_h`` of run),
    and because both sections are built from the body's own roofline the cutter follows the
    surface exactly, at any sample count. ``chamfer_v`` is the VERTICAL leg (down the wall) and
    ``chamfer_h`` the horizontal one (inboard), matching C.RIM_FACET_DROP / C.RIM_FACET_RUN —
    the old 3-D call left that assignment up to OCC, which applied it the other way round."""
    roof = _roofline(z_ridge)
    z_ceil = z_ridge + 5.0
    k_west = (_WEST_CHAMFER_PAD + chamfer_h) / chamfer_h
    sections = [Pos(x_w - _WEST_CHAMFER_PAD, 0, 0) * _west_chamfer_section(
                    roof, k_west, chamfer_v, z_ceil),
                Pos(x_w + chamfer_h, 0, 0) * _west_chamfer_section(
                    roof, 0.0, chamfer_v, z_ceil)]
    with BuildPart() as bp:
        loft(sections, ruled=True)
    assert bp.part is not None
    out = cast(Part, part - cast(Part, bp.part))
    # Never leave this shoulder hard SILENTLY — the whole point of replacing the edge chamfer.
    assert part.volume - out.volume > 1.0, \
        f"west top shoulder facet removed no material (z_ridge={z_ridge})"
    return out


def _chamfer_east_top(part: Part, x_e: float, z_ridge: float,
                      chamfer_v: float, chamfer_h: float) -> Part:
    """Cut the drafted facet on the EAST top shoulder (roof/ramp ↔ east wall) — the mirror
    of ``_chamfer_west_top``.

    The east wall is the switch-column boundary; its top edge was historically left sharp
    while the west shoulder carried the drafted facet. This adds the same 2:1 facet
    (``chamfer_v`` vertical, ``chamfer_h`` inboard) to the east side so both shoulders
    read as one continuous drafted roofline.

    A BOOLEAN, not a 3-D edge chamfer, for the same reason as the west: OCC rejects an
    edge chamfer once the ramp ``Spline`` density grows, and the ruled-loft cutter tracks
    the roofline at any ``CANOPY_RAMP_SAMPLES``. The east wall is thinner
    (``CANOPY_ROOF_WALL=1.5`` vs ``CANOPY_WEST_WALL=4.0``), so the remaining wall at the
    rim is only ``CANOPY_ROOF_WALL - chamfer_h`` (≈0.3 mm at ``h=1.2``) — thin but
    positive; the cutter still leaves material and the cavity is one wall thickness
    inset so it never reaches the facet."""
    roof = _roofline(z_ridge)
    z_ceil = z_ridge + 5.0
    k_east = (_EAST_CHAMFER_PAD + chamfer_h) / chamfer_h
    sections = [Pos(x_e + _EAST_CHAMFER_PAD, 0, 0) * _west_chamfer_section(
                    roof, k_east, chamfer_v, z_ceil),
                Pos(x_e - chamfer_h, 0, 0) * _west_chamfer_section(
                    roof, 0.0, chamfer_v, z_ceil)]
    with BuildPart() as bp:
        loft(sections, ruled=True)
    assert bp.part is not None
    out = cast(Part, part - cast(Part, bp.part))
    assert part.volume - out.volume > 0.8, \
        f"east top shoulder facet removed no material (z_ridge={z_ridge})"
    return out


def _roofline_slope(y: float, z_ridge: float) -> float:
    """dz/dy of the swept roofline at case-Y ``y`` — the ANALYTIC derivative of ``_smoothstep``.

    Zero outside the ramp, and zero AT both ramp ends, which is the S-curve's whole point.

    Analytic, not a finite difference across ``_roofline``'s sample points, and that is
    load-bearing: a one-sided difference at the foot reads the ramp's first 0.06 mm of rise as a real
    slope, which pushes the offset endpoint north of ``CANOPY_RAMP_FOOT_Y``; ``_yz_prism``'s span
    filter then drops the profile's south face and the sketch will not close."""
    y0, y1 = CANOPY_RAMP_FOOT_Y, CANOPY_RAMP_TOP_Y
    if y <= y0 or y >= y1:
        return 0.0
    t = (y - y0) / (y1 - y0)
    return (z_ridge - CANOPY_FOOT_Z) * 6 * t * (1 - t) / (y1 - y0)


def puzzle_depth_at(y: float, z_ridge: float) -> float:
    """How deep a roof groove may be at case-Y ``y``, measured NORMAL to the surface.

    Two ceilings, both derived from what is actually under the surface there, and the smaller wins:

      • the SHELL. The cavity is a straight Z offset of the roofline, so perpendicular to the surface
        there is only ``CANOPY_ROOF_WALL·cos θ`` of it — 1.5 on the flat roof, 1.23 at the right
        half's steepest 34.9°.
      • the MEMBRANE, which is what binds near the ramp foot. The foot lands ON the cover surface
        (``CANOPY_FOOT_Z == C.COVER_TOP_Z``) and the body's base is one cover thickness below it
        (``CANOPY_FUSE_BASE_Z == C.MAIN_RIM_Z``), so approaching the foot the material under the roof
        thins to the 1.0 mm membrane and the groove has to run out.

    Both are measured against ``CANOPY_PUZZLE_MIN_ROOF``, so the depth reaches EXACTLY zero at the
    foot rather than by a hand-set fade — the mark dies where the ramp becomes the deck because that
    is where there is nothing left to cut, and one number cannot drift from the other.

    Measured, right half: 0.000 at the foot, 0.42 at y 62, **0.230 at the steepest point**, 0.500 from
    the ramp top northward. The left half bottoms out at 0.333, because its ridge is 2.76 mm lower —
    the halves differ here as a consequence, not as a tuning.

    The zero-gradient property matters as much as the values: ``_roofline_slope`` is zero at BOTH ramp
    ends and the membrane term's gradient vanishes with it, so the offset profile arrives horizontal
    at the foot and at the ramp top — which is exactly the tangent ``_yz_prism`` forces on its
    ``Spline``. A multiplicative hand-set taper does not have that property and would ring."""
    m = _roofline_slope(y, z_ridge)
    k = (1.0 + m * m) ** 0.5
    shell = CANOPY_ROOF_WALL / k                                        # ·cos θ
    membrane = (_canopy_roof_z(y, z_ridge) - CANOPY_FUSE_BASE_Z) / k    # ·cos θ
    return max(0.0, min(CANOPY_PUZZLE_DEPTH, min(shell, membrane) - CANOPY_PUZZLE_MIN_ROOF))


def _offset_roofline(roof: list[tuple[float, float]], d: float | Callable[[float], float],
                     z_ridge: float) -> list[tuple[float, float]]:
    """The roofline pushed ``d`` INTO the material along its own NORMAL — ``(m, −1)/√(1+m²)``.

    Not straight down in Z: a Z-drop measures depth vertically, so a 0.5 mm groove would thin to
    0.5·cos 35.9° = 0.40 mm on the right half's steepest run — it would pass any "did it cut?" check
    while going shallow exactly where the surface is most visible. Both ramp ends have zero slope, so
    the offset polyline spans the same Y range as the original and ``_yz_prism`` still accepts it.

    THE OFFSET STOPS AT THE ROOF. It is deliberately NOT carried down either top facet, so a stroke
    aimed off the edge behaves the same on both: the cutter's floor stays flat while the facet dives
    away (2:1 on the west, 2:1 on the north), and the groove fades out ~0.25 mm past the arris. That
    fade IS the terminal — the mark runs off the edge instead of ending in a wall.

    Carrying the offset across the north facet was built and reverted. It worked — 0.5 mm normal all
    the way through the facet, notching the wall — but it reads as the groove being dragged down the
    slope at full depth, where the west ends run off cleanly. Two edges treated alike beats one edge
    treated thoroughly. (It also cost an over-cut: mitring two offset half-planes at that convex
    junction deepened the groove 0.500 → 1.118 mm over the 0.31 mm before the facet, because the true
    erosion there is an arc, which runs backwards in Y and cannot be expressed in a Y-ordered
    profile.)"""
    depth = d if callable(d) else (lambda _y: cast(float, d))
    out: list[tuple[float, float]] = []
    for y, z in roof:
        dy = depth(y)
        assert dy >= 0.0, f"a negative depth at y={y} would put the cutter's floor above the roof"
        m = _roofline_slope(y, z_ridge)
        k = (1 + m * m) ** 0.5
        out.append((y + dy * m / k, z - dy / k))
    assert all(b[0] > a[0] for a, b in zip(out, out[1:])), (
        "normal-offset roofline folded over in Y — the ramp's curvature is too tight for this depth, "
        "or the depth field's own gradient is steeper than the sample spacing"
    )
    # The Spline in ``_yz_prism`` is forced HORIZONTAL at both ramp ends, so an offset profile that
    # arrives tilted there gets bent to meet that tangent and rings. A depth field is allowed to
    # change the profile's shape but not to make its ends steeper than the roofline's own.
    for a, b, r0, r1 in ((out[0], out[1], roof[0], roof[1]),
                         (out[-1], out[-2], roof[-1], roof[-2])):
        if abs(b[0] - a[0]) > 1e-9 and abs(r1[0] - r0[0]) > 1e-9:
            assert abs((b[1] - a[1]) / (b[0] - a[0])) <= abs((r1[1] - r0[1]) / (r1[0] - r0[0])) + 1e-6, (
                "the depth field tilts the offset profile more at a ramp end than the roofline "
                "itself — forcing a horizontal Spline tangent on it will ring"
            )
    return out


def _band_offsets(pts: Sequence[tuple[float, float]], w: float
                  ) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """The two sides of a ``w``-wide band centred on the polyline ``pts``.

    Each station is offset along the normal of its own local tangent (the chord between its
    neighbours, so the offset turns with the mark), which makes the ends square ACROSS the band and
    perpendicular to the run — the same terminal the box prism gave, just no longer restricted to one
    plan angle.

    The assert is the plan-space twin of ``_offset_roofline``'s: offsetting a polyline inward folds it
    over once the turn is tight relative to the width, and a folded band is a self-intersecting face
    that OCC will either refuse or, worse, accept as a bow tie. At the shipped curvature (R ≈ 46 mm
    against a 0.5 mm half-width) the margin is ~90×, so this guards a future re-draw, not today."""
    left: list[tuple[float, float]] = []
    right: list[tuple[float, float]] = []
    for k, (x, y) in enumerate(pts):
        ax, ay = pts[max(0, k - 1)]
        bx, by = pts[min(len(pts) - 1, k + 1)]
        tx, ty = bx - ax, by - ay
        t = math.hypot(tx, ty)
        assert t > 1e-9, "duplicate station in a stroke — the tangent is undefined there"
        nx, ny = -ty / t, tx / t
        left.append((x + nx * w / 2, y + ny * w / 2))
        right.append((x - nx * w / 2, y - ny * w / 2))
    for side in (left, right):
        for (ax, ay), (bx, by) in zip(side, side[1:]):
            assert math.hypot(bx - ax, by - ay) > 1e-6, (
                f"a {w} mm band folded over on itself — the stroke turns tighter than its own width"
            )
    return left, right


def _band_prism(seg: Stroke, w: float, z0: float, z1: float) -> Part:
    """Vertical prism over a SQUARE-ended slot along the polyline ``seg``, ``w`` wide, ``z0``→``z1``.

    Square, not stadium: a stroke ends as if a knife lifted off it — a straight edge square across
    the groove — which is how the strokes are drawn. A rounded cap reads as a blob at the end of a
    thin line, and it is most obvious exactly where it matters, on the terminals that stop in open
    roof rather than running out to an edge.

    A closed ``Polyline`` face extruded in Z — the same idiom as ``tray._deep_facet_region`` — and
    deliberately NOT a swept spline or a round-joined 2-D offset. Every face it adds is planar, so a
    curved mark costs the tessellator almost nothing (measured: +5% triangles) and cannot introduce a
    cylindrical face, which is what ``test_no_terminal_is_rounded`` is really guarding.

    Built at arbitrary plan angles, because the puzzle's curves meet each canopy at whatever angle
    the assembled layout gives them."""
    assert len(seg) >= 2, "a stroke needs at least two stations"
    left, right = _band_offsets(seg, w)
    loop = left + right[::-1]
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            with BuildLine():
                Polyline(*loop, close=True)
            make_face()
        extrude(amount=z1 - z0)
    assert bp.part is not None
    return cast(Part, Pos(0, 0, z0) * bp.part)


def _puzzle_cutter(side: str, z_ridge: float) -> Part:
    """Cutter for this half's two puzzle strokes, at constant depth NORMAL to the swept surface.

    ``footprint prism − solid under the normal-offset roofline``. Everything of the prism above the
    offset surface survives; the part above the REAL surface is air and costs nothing. What is left
    biting the part is a groove of the footprint's shape, ``CANOPY_PUZZLE_DEPTH`` deep measured
    perpendicular to the surface — on the flat roof and on the 35.9° ramp alike, with one boolean and
    no per-stroke fitting. That matters here because two of the four strokes cross the ramp.

    This works because the roof/ramp is a translational sweep of one Y–Z profile along X, i.e. a
    DEVELOPABLE surface, so a flat plan footprint lands on it by clipping alone.

    The offset covers the ROOF only — see ``_offset_roofline``. Every stroke that leaves the roof
    therefore terminates the same way, west and north alike: full depth to the arris, then a fade as
    the facet drops out from under the cutter."""
    inner = _offset_roofline(_roofline(z_ridge), lambda y: puzzle_depth_at(y, z_ridge), z_ridge)
    under = _yz_prism(inner, z_base=CANOPY_FUSE_BASE_Z - 5.0,
                      x_lo=CANOPY_WEST_OUTER_X - 1.0,
                      x_width=(CANOPY_EAST_X + 1.0) - (CANOPY_WEST_OUTER_X - 1.0),
                      spline_range=(CANOPY_RAMP_FOOT_Y, CANOPY_RAMP_TOP_Y))
    prism: Part | None = None
    for seg in canopy_puzzle_strokes(side):
        one = _band_prism(seg, CANOPY_PUZZLE_W, CANOPY_FUSE_BASE_Z, z_ridge + 2.0)
        prism = one if prism is None else cast(Part, prism + one)
    assert prism is not None
    return cast(Part, prism - under)


def build_canopy(hollow: bool = True, side: str = "right", puzzle: bool = True) -> Part:
    """The fastback canopy that FUSES into the TOP cover over the bay.

    The ramp foot merges tangentially into the cover surface (``CANOPY_FOOT_Z``) — no tongue;
    the body base drops to ``CANOPY_FUSE_BASE_Z`` so it overlaps the cover/walls for a clean
    union. Its −X / +Y / +X walls land at the chamfer FIRST point (``CANOPY_WEST_OUTER_X`` /
    ``CANOPY_NORTH_OUTER_Y`` / ``CANOPY_EAST_X``), chamfer EXPOSED; BOTH north corners (NW +
    NE) are rounded to the case's own corner radius (``CANOPY_CORNER_R``) and BOTH top
    shoulders (west + east) carry a swept drafted facet (``_chamfer_west_top`` /
    ``_chamfer_east_top``) of the same 2:1 style. ``hollow=False`` returns the solid envelope;
    ``hollow=True`` (default) the printed shell. ``case.build_top_part`` adds the result onto
    the TOP.

    ``side`` sets BOTH the ridge height (``canopy_ridge_top_z``) and the USB port band
    (``canopy_usb_z``) — the two halves carry the MCU in opposite orientations, so their jacks
    sit at different Z, and the roof now sits only as high as its own half's port needs. The
    two halves are therefore NOT the same height; only the footprint (X/Y) is common."""
    x_w, x_e = CANOPY_WEST_OUTER_X, CANOPY_EAST_X
    y_n = CANOPY_NORTH_OUTER_Y
    z_base, z_ridge = CANOPY_FUSE_BASE_Z, canopy_ridge_top_z(side)
    w_roof, w_west, w_north = CANOPY_ROOF_WALL, CANOPY_WEST_WALL, CANOPY_NORTH_WALL
    chamfer_v, chamfer_h = canopy_top_chamfer(side)

    ramp_span = (CANOPY_RAMP_FOOT_Y, CANOPY_RAMP_TOP_Y)
    roof = _roofline(z_ridge)
    body = _yz_prism(roof, z_base=z_base, x_lo=x_w, x_width=x_e - x_w,
                     north_chamfer=canopy_north_chamfer(side),
                     spline_range=ramp_span)
    body = _round_nw_corner(body, x_w, y_n, CANOPY_CORNER_R, z_base - 0.1, z_ridge + 0.1)
    body = _round_ne_corner(body, x_e, y_n, CANOPY_CORNER_R, z_base - 0.1, z_ridge + 0.1)
    # Facet BOTH top shoulders — west and east — on the solid, before hollowing. East was
    # historically left sharp; it now carries the same 2:1 drafted facet as the west so the
    # roof reads as one continuous chamfered ridge rather than a one-sided shoulder.
    body = _chamfer_west_top(body, x_w, z_ridge, chamfer_v, chamfer_h)
    body = _chamfer_east_top(body, x_e, z_ridge, chamfer_v, chamfer_h)
    shell = body

    if hollow:
        # Roofline-following cavity, open at the bottom (over the bay). Roof/east wall =
        # CANOPY_ROOF_WALL; the west wall keeps CANOPY_WEST_WALL and the north wall lands on the
        # bay's one north face (CANOPY_NORTH_WALL). The cavity starts at the ramp foot and its
        # floor is open, so the fuse-overlap band below the cover top is left solid to merge
        # into the cover.
        y_n_inner = y_n - w_north
        cav_roof = [(y, z - w_roof) for (y, z) in roof
                    if CANOPY_RAMP_FOOT_Y - 1e-6 <= y <= y_n_inner]
        cav_roof.append((y_n_inner, z_ridge - w_roof))
        cav = _yz_prism(_dedup(cav_roof), z_base=z_base - 3.0,
                        x_lo=x_w + w_west, x_width=(x_e - w_roof) - (x_w + w_west),
                        spline_range=ramp_span)
        shell = cast(Part, shell - cav)

    # Roof puzzle strokes — this half's segments of the two lines drawn across the assembled pair.
    # After hollowing and after the shoulder facet / corner round, and clear of both by
    # CANOPY_PUZZLE_LAND, so this step cannot perturb the fragile booleans.
    if puzzle:
        cut = cast(Part, shell - _puzzle_cutter(side, z_ridge))
        # Never let the strokes vanish SILENTLY — the failure mode _chamfer_west_top was rewritten
        # to escape. Two grooves ~20-50 mm long at 0.5 deep remove tens of mm³.
        assert shell.volume - cut.volume > 10.0, \
            f"{side}: roof puzzle strokes removed no material (z_ridge={z_ridge})"
        shell = cut

    # USB-C port through the north (+Y) wall, centred on the MCU X column (required for fit).
    # Band is per-half — see canopy_usb_z. Cut again post-fuse in build_top_part; see
    # usb_port_cutter for why.
    shell = cast(Part, shell - usb_port_cutter(side))

    return cast(Part, shell)


# %%
if __name__ == "__main__":
    from ocp_vscode import show
    # Show the parked canopy IN CONTEXT on the (pre-cover) case parts, right side. This keeps
    # the tracked case.py viewer untouched — the canopy is visualised only from here.
    from sofle_case.case import build_bottom_part, build_top_part
    parts = [build_bottom_part("right"), build_top_part("right"), build_canopy()]
    names = ["bottom", "top", "canopy"]
    show(*parts, names=names)
