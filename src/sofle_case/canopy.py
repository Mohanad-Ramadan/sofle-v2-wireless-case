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
  • Ramp   — a tangent S-curve (``_smoothstep`` via a real ``Spline`` — horizontal at both
             ends, no crease) up to the flat roof. Reaches full height ``CANOPY_RAMP_TOP_OLED_GAP``
             before the OLED pins; the whole south bay is empty (PCB-level) so the low foot clears.
  • Roof   — FLAT at ``CANOPY_RIDGE_TOP_Z`` over the MCU (clears the USB-C stack).
  • North / West — VERTICAL walls landing at the chamfer FIRST point (chamfer EXPOSED); the
             NW corner is ROUNDED to the case's own corner radius (``_round_nw_corner``). The
             west wall's top shoulder carries a drafted facet cut by a swept boolean, NOT a 3-D
             edge chamfer (``_chamfer_west_top`` — an edge chamfer cannot survive the ramp
             spline's density). The USB-C port is cut
             through the north wall (required — the plug must pass; the jack itself stops
             ~0.4 mm short of the wall's inner face, see C.USB_JACK_Y_PROTRUDE).
  • East   — plain vertical wall on the switch-column boundary.

There is deliberately NO reset poke-hole. The roof over RSW1 is unbroken: a bore there could not
be relocated into the BOTTOM part (it would end at the PCB underside, Z=PCB_SEAT_Z, not at the
button), so the feature was dropped rather than moved. Reset means opening the case, or the
nice!nano's double-tap over the USB-C port.

Tangent curves are 2-D profile splines/fillets on the swept cross-section (robust), not
fragile 3-D solid fillets. The slide finger-bowl (over on the −X wall) is handled in ``tray``
and split cleanly into the TOP part by ``case``'s local seam step-down."""
from __future__ import annotations
import math
from typing import cast

from build123d import (
    Part, Face, Pos, Rot, Line, Polyline, Spline, make_face, extrude, fillet, chamfer, loft, Solid,
    Plane, BuildPart, BuildSketch, BuildLine,
)
from OCP.Standard import Standard_Failure
from . import constants as C
from . import canopy_puzzle as PZ

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
CANOPY_SIDE_WALL    = 4.0                       # N + W wall thickness (case-like; thinned from 4.75
                                               #   so the west cavity clears the nice!nano's west edge)
CANOPY_ROOF_CLEAR   = 0.6                       # headroom over the USB-C body top
# N/W walls land FLUSH on the drafted rim facet's top line (outer wall face pulled IN by the
# facet's rim inset RIM_FACET_RUN): the wall's facet rises from its toe and meets the canopy
# face exactly at the rim, so wall → facet → canopy face reads as one continuous surface stack.
CANOPY_WEST_OUTER_X = (C.pcb_to_case(0, 0)[0] - C.WALL_THICKNESS - C.PCB_XY_CLEARANCE
                       + C.RIM_FACET_RUN)                                                   # ≈ 10.5
CANOPY_NORTH_OUTER_Y = (C.pcb_to_case(0, C.MCU_Y_RELIEF_TARGET_Y)[1]
                        + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE - C.RIM_FACET_RUN)           # ≈ 121.5
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
# Control points pinning the S-curve for the Spline. 9 was too sparse: the B-spline
# interpolation through 9 points, forced to an exact horizontal tangent at both ends, RANG —
# it overshot and undershot the analytic smoothstep by up to 0.14 mm right where the ramp
# flattens into the roof (measured on the right half's rise; the shorter left ramp rang less —
# 0.087 mm — but was not immune). Densifying damps it ~4x per 2x the samples.
#
# 25 IS A CEILING, NOT A FLOOR — do not raise it chasing the last micron. OCC meshes by
# CURVATURE (angular tolerance), not by deviation, and a denser interpolating spline trades
# deviation for high-frequency curvature wiggle. Measured on the bare prism, right half:
#
#     samples    9        15       25       41        51
#     deviation  0.143mm  0.073mm  0.032mm  —         0.0086mm
#     triangles  28,482   26,988   39,150   216,264   396,620
#     right STL  2.5 MB   —        3.9 MB   —         39.9 MB
#
# Past ~25 the mesh detonates for smoothness that is already an order of magnitude under a
# 0.2 mm layer line: 51 bought 0.023 mm of invisible flatness for 10x the STL. The left half
# never blows up (its ramp is 2.76 mm shorter, so its curvature stays mild) — this is a
# right-half failure mode, so measure the RIGHT half when touching this.
#
# NOTE: this number used to be load-bearing for the west top shoulder's facet — OCC's 3-D
# chamfer on that run silently stopped working above ~9 samples. That coupling is gone;
# _chamfer_west_top is a boolean and is verified at 9/13/21/51/81. Keep it that way: an edge
# chamfer here re-introduces a hidden tie between ramp smoothness and wall style.
CANOPY_RAMP_SAMPLES = 25
CANOPY_NORTH_ROUND_R = 1.0
# Lead-in of the west top shoulder's drafted facet: the cutter's vertical leg fades to 0 at the
# ramp foot, where the west wall is only (COVER_TOP_Z − MAIN_RIM_Z) = 1 mm tall, so the facet
# can never bite into the fuse overlap. Full depth is reached ~7 mm up the ramp (case-Y ≈ 65.7
# on the right half, 66.9 on the left — the shorter left ramp climbs slower per mm of Y).
# Heights. The ramp foot merges at the cover surface; the body base drops one cover thickness
# (to MAIN_RIM_Z) so it overlaps the cover/walls for a clean fuse into the TOP.
CANOPY_FOOT_Z       = C.COVER_TOP_Z                                # 13.5; ramp foot = cover surface
CANOPY_FUSE_BASE_Z  = C.MAIN_RIM_Z                                 # 12.5; base overlaps the cover for the fuse
# ---------------------------------------------------------------------------
# USB port STEPPED bore: overmold pocket (outer) → shell neck (inner).
# See constants.USB_PLUG_SHELL_L for why: the jack mouth sits well behind the outer face, so
# a straight shell-sized hole both blocks the overmold and starves the shell of engagement.
# ---------------------------------------------------------------------------
CANOPY_USB_OM_W = C.USB_OVERMOLD_W + C.USB_OVERMOLD_CLEAR      # 12.85; pocket width
CANOPY_USB_OM_H = C.USB_OVERMOLD_H + C.USB_OVERMOLD_CLEAR      # 7.00;  pocket height
# How far the plug must travel from the outer face before it reaches the jack, and how deep
# the pocket must therefore be so USB_PORT_ENGAGE_TARGET of shell ends up inside the jack.
CANOPY_USB_TRAVEL    = CANOPY_NORTH_OUTER_Y - (C.MCU_BODY_N_Y + C.USB_JACK_Y_PROTRUDE)       # 4.41
CANOPY_USB_OM_DEPTH  = C.USB_PORT_ENGAGE_TARGET - (C.USB_PLUG_SHELL_L - CANOPY_USB_TRAVEL)   # 2.76
# Minimum solid wall left above the pocket, measured where the north wall's top round-over
# starts eating material (at CANOPY_RIDGE_TOP_Z − CANOPY_NORTH_ROUND_R). Without this term
# a 7 mm-tall pocket breaks out through the rounded top shoulder and the port stops being a
# closed hole.
CANOPY_USB_OM_ROOF_MIN = 0.5


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
# stops ~0.4 mm short of the inner face — C.USB_JACK_Y_PROTRUDE; it used to sit open over the
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
# Roof PUZZLE strokes — two straight lines drawn across the ASSEMBLED pair, each crossing both
# canopies. The plan geometry (which line, at what angle, in whose frame) belongs to
# ``canopy_puzzle``, which fitted it from the design sketch; this half of the job is cutting the
# resulting segments into a surface that is flat for 40 mm and then tips over to 35.9°.
#
# A stroke CROSSES THE RAMP (left line 1; the right half's line 0 did too until it was trimmed to
# its sketched half-chord), so depth cannot be measured vertically. The cutter is a
# footprint prism clipped against a NORMAL-offset copy of the roofline, which holds the depth
# perpendicular to the surface on the flat roof and on the slope alike — the same construction that
# built valid solids on both halves first time during the pattern trials.
#
# DEPTH is the load-bearing number: the roof shell is CANOPY_ROOF_WALL (1.5) over a cavity that
# follows the roofline, so a groove eats that wall and nothing else. 0.5 leaves 1.0 mm, five layers
# at 0.2. The assert is the point — it is why the depth is derived against CANOPY_ROOF_WALL rather
# than written as a bare 0.5.
CANOPY_PUZZLE_W        = 1.6      # groove width, as on the diagonal reveal this grew out of
CANOPY_PUZZLE_DEPTH    = 0.5
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
# stops short of the ramp foot so no groove spills onto the cover surface.
CANOPY_PUZZLE_LAND     = 2.4
CANOPY_PUZZLE_NORTH_KO = CANOPY_NORTH_ROUND_R + 0.5 + 1.5      # 3.0; the 0.5 is USB_OM_ROOF_MIN
CANOPY_PUZZLE_SOUTH_KO = 1.5
# EAST is the one exception, and it is the design's: each half's UPPER stroke runs OUT through the
# east wall — the wall bordering the switch columns — so it lands against something instead of
# stopping 2.4 mm short in open roof. The east arris IS broken there, once per half, on purpose.
#
# The endpoint is put a clear margin PAST the wall rather than on it: the cutter is a square-ended
# box prism, so an endpoint sitting exactly on x = CANOPY_EAST_X would leave the break at the mercy
# of boolean tolerance — a groove that ends flush with the face it is supposed to open into. One
# groove width past is unambiguous and costs nothing, since everything beyond the wall is air.
CANOPY_PUZZLE_EAST_BREAK = CANOPY_PUZZLE_W                     # 1.6 past CANOPY_EAST_X
assert CANOPY_PUZZLE_EAST_BREAK > CANOPY_PUZZLE_W / 2, \
    "the upper stroke would not clearly clear the east wall"
# WEST is the gap-facing side — the one the assembled pair's strokes cross between the halves — so
# every stroke is aimed OUT through it, past the wall line. What that actually produces is a groove
# that runs over the west shoulder's top arris and stops there: the facet falls away from the swept
# roofline at 2:1, so the cutter stops biting ~0.25 mm past the arris. The mark reaches the roof's
# west edge and disappears over the shoulder, which is the read we want at the gap.
CANOPY_PUZZLE_WEST_BREAK = CANOPY_PUZZLE_W
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


def canopy_north_chamfer_run(side: str) -> float:
    """The north-top chamfer's PLAN run — how far inboard of the north wall its top line sits.

    Returns the chamfer's VERTICAL leg, which looks wrong and is not: MEASURED on the built part, the
    north chamfer runs 2.4 mm inboard and drops 1.2 mm, i.e. its legs are the INVERSE of the west
    shoulder facet's (1.2 in, 2.4 down) and of the case rim style both are supposed to share.

    ``_yz_prism`` hands OCC ``(chamfer_v, chamfer_h)`` and its fallback loop accepts the first
    ordering that does not throw — so the assignment was never chosen, only survived. Scan of the
    bare right half at x=22: flat roof to y=118.9, then 0.04 / 0.19 / 0.34 / 0.49 / 0.64 mm of drop
    at 119.2 / 119.5 / 119.8 / 120.1 / 120.4 — a 1:2 slope starting at 119.1, where the west facet
    measures 2:1 starting at 11.7.

    This function exists so exactly one place depends on that, and so fixing the leg order is a
    one-word change here rather than a hunt. See ``canopy_puzzle_strokes``, which stops a stroke on
    this line."""
    return canopy_top_chamfer(side)[0]


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


def canopy_puzzle_strokes(side: str) -> list[tuple[tuple[float, float], tuple[float, float]]]:
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
    region = canopy_puzzle_region(side)
    common = dict(x1_north=canopy_puzzle_north_x1(),
                  x0_break=CANOPY_WEST_OUTER_X - CANOPY_PUZZLE_WEST_BREAK)
    segs = PZ.strokes(side, *region, **common,
                      y1_break=CANOPY_NORTH_OUTER_Y - canopy_north_chamfer_run(side))
    if not _puzzle_north_exit_ok(segs):
        segs = PZ.strokes(side, *region, **common)
        assert _puzzle_north_exit_ok(segs), \
            f"{side}: a stroke reaches the north keep-out band even without the north break"
    return segs


def _puzzle_north_exit_ok(segs: list[tuple[tuple[float, float], tuple[float, float]]]) -> bool:
    """Does every terminal inside the north keep-out's band leave through the safe window?"""
    x_lo, x_hi = canopy_puzzle_north_exit_window()
    return all(x_lo <= x <= x_hi
               for seg in segs for x, y in seg
               if y > CANOPY_NORTH_OUTER_Y - CANOPY_USB_OM_DEPTH)


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
                 (CANOPY_NORTH_OUTER_Y - CANOPY_SIDE_WALL) - 1.0, CANOPY_NORTH_OUTER_Y + 1.0)
    # POCKET — overmold-sized, only the outer CANOPY_USB_OM_DEPTH of the wall. This is what
    # buys the shell its engagement: without it the overmold stops dead on the outer face.
    plo, phi = canopy_usb_om_z(side)
    pocket = _bore(CANOPY_USB_OM_W, plo, phi,
                   CANOPY_NORTH_OUTER_Y - CANOPY_USB_OM_DEPTH, CANOPY_NORTH_OUTER_Y + 1.0)
    box = cast(Part, neck + pocket)
    return box


# Canopy roof-edge chamfer: the same drafted-facet STYLE as the case rim (slope run/drop),
# scaled down so the north face's chamfer toe stays clear of the USB-C port mouth below it.
# Derived per half now (each half has its own ridge and its own port band).
def canopy_top_chamfer(side: str) -> tuple[float, float]:
    """(V, H) legs of the north-top drafted chamfer for a half."""
    v = min(2.4, canopy_ridge_top_z(side) - canopy_usb_z(side)[1] - 0.2)   # vertical leg
    h = v * C.RIM_FACET_RUN / C.RIM_FACET_DROP                            # horizontal leg
    assert v > 0.5, f"USB port leaves no room for the canopy roof chamfer ({side})"
    return v, h


def _smoothstep(y0: float, z0: float, y1: float, z1: float, n: int) -> list[tuple[float, float]]:
    """Interior points of a cubic smoothstep (3t²−2t³) from (y0,z0) to (y1,z1).

    Horizontal-tangent at BOTH ends, so the ramp merges into the flat cover at the foot and
    into the flat roof at the top with no crease at either — the slip grows seamlessly out of
    the cover surface. Endpoints omitted; the caller supplies them."""
    out = []
    for i in range(1, n - 1):
        t = i / (n - 1)
        out.append((y0 + (y1 - y0) * t, z0 + (z1 - z0) * (3 * t * t - 2 * t ** 3)))
    return out


def _dedup(pts: list[tuple[float, float]], tol: float = 1e-4) -> list[tuple[float, float]]:
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) > tol or abs(p[1] - out[-1][1]) > tol:
            out.append(p)
    return out


def _yz_prism(top_pts: list[tuple[float, float]], z_base: float, x_lo: float, x_width: float,
              fillets_2d: list[tuple[float, float, float]] | None = None,
              spline_range: tuple[float, float] | None = None,
              chamfers_2d: list[tuple[float, float, float, float]] | None = None) -> Part:
    """Extrude a Y–Z profile (flat base at ``z_base`` closed by the ``top_pts`` edge, ordered
    by ascending Y) along +X by ``x_width``, positioned so its −X face sits at ``x_lo``.

    ``fillets_2d`` rounds the profile vertex at each ``(y, z, r)`` in 2-D. ``chamfers_2d``
    CHAMFERS the vertex at each ``(y, z, len1, len2)`` instead (drafted-facet style; tried
    asymmetric both ways, then symmetric, then a fillet as last resort — never aborts).
    ``spline_range`` ``(y0, y1)`` draws the ramp between those Y as a real **Spline** (a smooth
    curved edge, so the swept surface has no facet steps) with a horizontal tangent at ``y1``
    (eases into the flat roof); the rest of the profile stays straight ``Line`` segments."""
    top = _dedup(top_pts)
    y_lo, y_hi = top[0][0], top[-1][0]
    with BuildPart() as bp:
        with BuildSketch(_YZ) as sk:
            with BuildLine():
                if spline_range is None:
                    Polyline((y_lo, z_base), *top, (y_hi, z_base), close=True)
                else:
                    y0, y1 = spline_range
                    before = [p for p in top if p[0] <= y0 + 1e-6]
                    ramp = _dedup([p for p in top if y0 - 1e-6 <= p[0] <= y1 + 1e-6])
                    after = [p for p in top if p[0] >= y1 - 1e-6]
                    Line((y_lo, z_base), before[0])              # south face (buried in the cover)
                    if len(before) >= 2:
                        Polyline(*before)                         # (unused: no tongue)
                    # Horizontal tangents at BOTH ends: the ramp merges into the cover at the
                    # foot and into the flat roof at the top with no crease at either.
                    Spline(*ramp, tangents=((1.0, 0.0), (1.0, 0.0)))
                    if len(after) >= 2:
                        Polyline(*after)                          # flat roof
                    Line(after[-1], (y_hi, z_base))               # north wall
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
            for cy_, cz_, l1, l2 in (chamfers_2d or []):
                verts = [v for v in sk.vertices()
                         if abs(v.X - cy_) < 0.05 and abs(v.Y - cz_) < 0.05]
                if not verts:
                    continue
                for args in ((l1, l2), (l2, l1), ((l1 + l2) / 2, None)):
                    try:
                        chamfer(verts, length=args[0], length2=args[1])
                        break
                    except (ValueError, Standard_Failure, TypeError):
                        continue
                else:
                    try:
                        fillet(verts, radius=min(l1, l2))
                    except (ValueError, Standard_Failure):
                        pass
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


# How far WEST of the wall face the chamfer cutter starts. Purely to avoid a coincident-face
# boolean at x_w (the cutter's own boundary landing exactly on the wall it cuts); the extra
# reach reduces to air, so any value > 0 gives the same result.
_WEST_CHAMFER_PAD = 1.0


def _west_chamfer_section(roof: list[tuple[float, float]], k: float, v: float,
                          z_ceil: float) -> Face:
    """One loft section for ``_chamfer_west_top``: the Y–Z region ABOVE the roofline pushed DOWN
    by ``k * v_eff(y)``, closed off at ``z_ceil``.

    ``v_eff`` clamps the vertical leg to the wall's own height above the cover surface, so the
    facet fades to nothing at the ramp foot where the west wall is only 1 mm tall — without it
    the cut would eat the fuse overlap between MAIN_RIM_Z and COVER_TOP_Z. The ramp is drawn as
    a real ``Spline`` through the SAME points as the body's roofline, which is what makes this
    cutter track the body surface at any ``CANOPY_RAMP_SAMPLES``."""
    def lower(y: float, z: float) -> tuple[float, float]:
        v_eff = min(v, max(0.0, z - CANOPY_FOOT_Z))
        return y, z - k * v_eff

    pts = [lower(y, z) for y, z in roof]
    y_lo, y_hi = pts[0][0], pts[-1][0]
    ramp = _dedup([p for p in pts
                   if CANOPY_RAMP_FOOT_Y - 1e-6 <= p[0] <= CANOPY_RAMP_TOP_Y + 1e-6])
    after = [p for p in pts if p[0] >= CANOPY_RAMP_TOP_Y - 1e-6]
    with BuildSketch(_YZ) as sk:
        with BuildLine():
            Spline(*ramp, tangents=((1.0, 0.0), (1.0, 0.0)))
            if len(after) >= 2:
                Polyline(*after)
            Line(after[-1], (y_hi, z_ceil))
            Line((y_hi, z_ceil), (y_lo, z_ceil))
            Line((y_lo, z_ceil), ramp[0])
        make_face()
    return cast(Face, sk.sketch.faces()[0])


def _chamfer_west_top(part: Part, x_w: float, z_ridge: float,
                      chamfer_v: float, chamfer_h: float) -> Part:
    """Cut the drafted facet on the WEST top shoulder (roof/ramp ↔ west wall) so the tall west
    side carries the same facet style as the case walls. The EAST top edge (switch-column
    boundary) is left sharp on purpose. Done on the SOLID envelope, before hollowing, where
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


def _offset_roofline(roof: list[tuple[float, float]], d: float,
                     z_ridge: float) -> list[tuple[float, float]]:
    """The roofline pushed ``d`` INTO the material along its own NORMAL — ``(m, −1)/√(1+m²)``.

    Not straight down in Z: a Z-drop measures depth vertically, so a 0.5 mm groove would thin to
    0.5·cos 35.9° = 0.40 mm on the right half's steepest run — it would pass any "did it cut?" check
    while going shallow exactly where the surface is most visible. Both ramp ends have zero slope, so
    the offset polyline spans the same Y range as the original and ``_yz_prism`` still accepts it."""
    out: list[tuple[float, float]] = []
    for y, z in roof:
        m = _roofline_slope(y, z_ridge)
        k = (1 + m * m) ** 0.5
        out.append((y + d * m / k, z - d / k))
    assert all(b[0] > a[0] for a, b in zip(out, out[1:])), \
        "normal-offset roofline folded over in Y — the ramp's curvature is too tight for this depth"
    return out


def _slot_prism(seg: tuple[tuple[float, float], tuple[float, float]], w: float,
                z0: float, z1: float) -> Part:
    """Vertical prism over a SQUARE-ended slot along ``seg``, ``w`` wide, spanning ``z0``→``z1``.

    Square, not stadium: a stroke ends as if a knife lifted off it — a straight edge square across
    the groove — which is how the strokes are drawn. A rounded cap reads as a blob at the end of a
    thin line, and it is most obvious exactly where it matters, on the terminals that stop in open
    roof rather than running out to an edge.

    Built at an arbitrary plan angle, because the puzzle's lines meet each canopy at whatever angle
    the assembled layout gives them."""
    (x0, y0), (x1, y1) = seg
    length = math.hypot(x1 - x0, y1 - y0)
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    box = cast(Part, Solid.make_box(length, w, z1 - z0).translate((-length / 2, -w / 2, 0)))
    return cast(Part, Pos((x0 + x1) / 2, (y0 + y1) / 2, z0) * (Rot(0, 0, ang) * box))


def _puzzle_cutter(side: str, z_ridge: float) -> Part:
    """Cutter for this half's two puzzle strokes, at constant depth NORMAL to the swept surface.

    ``footprint prism − solid under the normal-offset roofline``. Everything of the prism above the
    offset surface survives; the part above the REAL surface is air and costs nothing. What is left
    biting the part is a groove of the footprint's shape, ``CANOPY_PUZZLE_DEPTH`` deep measured
    perpendicular to the surface — on the flat roof and on the 35.9° ramp alike, with one boolean and
    no per-stroke fitting. That matters here because two of the four strokes cross the ramp.

    This works because the roof/ramp is a translational sweep of one Y–Z profile along X, i.e. a
    DEVELOPABLE surface, so a flat plan footprint lands on it by clipping alone."""
    inner = _offset_roofline(_roofline(z_ridge), CANOPY_PUZZLE_DEPTH, z_ridge)
    under = _yz_prism(inner, z_base=CANOPY_FUSE_BASE_Z - 5.0,
                      x_lo=CANOPY_WEST_OUTER_X - 1.0,
                      x_width=(CANOPY_EAST_X + 1.0) - (CANOPY_WEST_OUTER_X - 1.0),
                      spline_range=(CANOPY_RAMP_FOOT_Y, CANOPY_RAMP_TOP_Y))
    prism: Part | None = None
    for seg in canopy_puzzle_strokes(side):
        one = _slot_prism(seg, CANOPY_PUZZLE_W, CANOPY_FUSE_BASE_Z, z_ridge + 2.0)
        prism = one if prism is None else cast(Part, prism + one)
    assert prism is not None
    return cast(Part, prism - under)


def build_canopy(hollow: bool = True, side: str = "right", puzzle: bool = True) -> Part:
    """The fastback canopy that FUSES into the TOP cover over the bay.

    The ramp foot merges tangentially into the cover surface (``CANOPY_FOOT_Z``) — no tongue;
    the body base drops to ``CANOPY_FUSE_BASE_Z`` so it overlaps the cover/walls for a clean
    union. Its −X / +Y walls land at the chamfer FIRST point (``CANOPY_WEST_OUTER_X`` /
    ``CANOPY_NORTH_OUTER_Y``), chamfer EXPOSED; the NW corner is rounded to the case's own
    corner radius (``CANOPY_CORNER_R``) and the west top shoulder carries a swept drafted facet.
    ``hollow=False`` returns the solid envelope; ``hollow=True`` (default) the
    printed shell. ``case.build_top_part`` adds the result onto the TOP.

    ``side`` sets BOTH the ridge height (``canopy_ridge_top_z``) and the USB port band
    (``canopy_usb_z``) — the two halves carry the MCU in opposite orientations, so their jacks
    sit at different Z, and the roof now sits only as high as its own half's port needs. The
    two halves are therefore NOT the same height; only the footprint (X/Y) is common."""
    x_w, x_e = CANOPY_WEST_OUTER_X, CANOPY_EAST_X
    y_n = CANOPY_NORTH_OUTER_Y
    z_base, z_ridge = CANOPY_FUSE_BASE_Z, canopy_ridge_top_z(side)
    w_roof, w_side = CANOPY_ROOF_WALL, CANOPY_SIDE_WALL
    chamfer_v, chamfer_h = canopy_top_chamfer(side)

    ramp_span = (CANOPY_RAMP_FOOT_Y, CANOPY_RAMP_TOP_Y)
    roof = _roofline(z_ridge)
    body = _yz_prism(roof, z_base=z_base, x_lo=x_w, x_width=x_e - x_w,
                     chamfers_2d=[(y_n, z_ridge, chamfer_v, chamfer_h)],
                     spline_range=ramp_span)
    body = _round_nw_corner(body, x_w, y_n, CANOPY_CORNER_R, z_base - 0.1, z_ridge + 0.1)
    # Facet the tall west top shoulder (east left sharp) on the solid, before hollowing.
    body = _chamfer_west_top(body, x_w, z_ridge, chamfer_v, chamfer_h)
    shell = body

    if hollow:
        # Roofline-following cavity, open at the bottom (over the bay). Roof/east wall =
        # CANOPY_ROOF_WALL; the N/W walls stay CANOPY_SIDE_WALL thick (match the case). The
        # cavity starts at the ramp foot and its floor is open, so the fuse-overlap band below
        # the cover top is left solid to merge into the cover.
        y_n_inner = y_n - w_side
        cav_roof = [(y, z - w_roof) for (y, z) in roof
                    if CANOPY_RAMP_FOOT_Y - 1e-6 <= y <= y_n_inner]
        cav_roof.append((y_n_inner, z_ridge - w_roof))
        cav = _yz_prism(_dedup(cav_roof), z_base=z_base - 3.0,
                        x_lo=x_w + w_side, x_width=(x_e - w_roof) - (x_w + w_side),
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
