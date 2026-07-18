"""Separate "fastback" canopy over the MCU / JST / slide-switch bay.

PARKED module: the upper case was reverted to its pre-cover state, so this is NOT wired into
the case build. It is kept, self-contained (its ``CANOPY_*`` parameters live here, not in
constants.py), as the design we iterated for the MCU cover — a standalone printed cap that
would continue the TOP cover surface over the open bay. Revisit when we decide how to mount
and fit it (see the parked design notes / renders from that session).

The cap SETS ON the case top (it does not fill the chamfer or sit flush). Cross-section is a
Y–Z roofline swept along the bay's X width (case Y, south → north):

  • Tongue — a low flat slab resting on the cover (top ``CANOPY_TONGUE_TOP_Z``, underside on
             the cover at ``CANOPY_SEAT_Z``).
  • Ramp   — an ease-OUT curve (``_ease_out``): rises FAST off the foot then eases into the
             flat roof, so the roof underside clears the bay components early ('mirrored
             slide'). Reaches full height ``CANOPY_RAMP_TOP_OLED_GAP`` before the OLED pins.
  • Roof   — FLAT at ``CANOPY_RIDGE_TOP_Z`` over the MCU (clears the USB-C stack).
  • North / West — VERTICAL walls that land on the flat wall-top at the chamfer FIRST point
             (``CANOPY_NORTH_OUTER_Y`` / ``CANOPY_WEST_OUTER_X``); the chamfer stays EXPOSED.
             The NW corner is rounded to the case's own corner radius. Nothing drops below the
             seat plane.
  • East   — plain vertical wall on the switch-column boundary.

The tangent curves are 2-D profile fillets / sampled ease points on the swept cross-section
(robust), not fragile 3-D solid fillets. ``build_canopy(hollow=False)`` returns the solid
envelope; ``hollow=True`` (default) the printed shell. Not yet designed: how it mounts
(inverted standoffs + hidden bottom screws), the USB-C port, the reset poke-hole, the slide bowl.
"""
from __future__ import annotations
from typing import cast

from build123d import (
    Part, Pos, Line, Polyline, Spline, make_face, extrude, fillet, Solid,
    Plane, BuildPart, BuildSketch, BuildLine,
)
from OCP.Standard import Standard_Failure
from . import constants as C

# A sketch plane whose local axes map cleanly onto global (Y, Z) with the extrude normal along
# +X: local-x = +Y, local-y = +Z. Built-in ``Plane.YZ`` negates/swaps these, so define it here.
_YZ = Plane(origin=(0, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))

# ---------------------------------------------------------------------------
# Self-contained canopy parameters. This module is PARKED — it is not wired into
# the case build (the upper case was reverted to its pre-cover state). Its constants
# live here (not in constants.py) so the module still runs standalone for cover
# experiments; they depend only on the base geometry constants that remain in
# constants.py. Derivations mirror the case's own walls so the cap sits flush.
# ---------------------------------------------------------------------------
CANOPY_ROOF_WALL    = 1.5                       # roof + east-wall shell thickness
CANOPY_SIDE_WALL    = C.WALL_THICKNESS          # 4.75; N + W walls match the case wall
CANOPY_ROOF_CLEAR   = 0.6                       # headroom over the USB-C body top
# SET-ON footprint: the cap rests ON the case top, landing at the chamfer FIRST point (the
# inner chamfer line, where the flat wall-top meets the bevel). It does NOT fill the chamfer
# or sit flush with the outer face — the chamfer stays exposed. West/north land lines are the
# outer wall face pulled IN by one chamfer leg.
CANOPY_WEST_OUTER_X = (C.pcb_to_case(0, 0)[0] - C.WALL_THICKNESS - C.PCB_XY_CLEARANCE
                       + C.OUTER_TOP_CHAMFER)                                               # ≈ 10.4
CANOPY_NORTH_OUTER_Y = (C.pcb_to_case(0, C.MCU_Y_RELIEF_TARGET_Y)[1]
                        + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE - C.OUTER_TOP_CHAMFER)       # ≈ 121.6
CANOPY_EAST_X       = 34.6                       # switch-column boundary (bay east edge)
CANOPY_ENCODER_HALF = 10.0                       # encoder centre → plateau north edge (measured)
CANOPY_ENCODER_CLEAR = 0.2                       # small print gap where the tongue butts the plateau
# The tongue's south edge lands right on the encoder plateau's north face so the bay is closed
# there (no open strip) and the two read as one — with a hair of print clearance.
CANOPY_SOUTH_Y      = (C.pcb_to_case(*C.SW_ENCODER_POS)[1]
                       + CANOPY_ENCODER_HALF + CANOPY_ENCODER_CLEAR)                        # ≈ 60.0
CANOPY_RAMP_FOOT_Y  = 64.0                       # tongue → ramp transition (slip starts south)
CANOPY_RAMP_TOP_OLED_GAP = 0.5
CANOPY_RAMP_TOP_Y   = C.pcb_to_case(*C.J_OLED_POS)[1] - CANOPY_RAMP_TOP_OLED_GAP            # ≈ 81.6
CANOPY_RAMP_SAMPLES = 9      # control points pinning the ease-out curve for the Spline (smooth)
CANOPY_NORTH_ROUND_R = 2.5
# Seat plane: the cap rests on the case top; NOTHING drops below this Z (no chamfer fill).
CANOPY_SEAT_Z       = C.COVER_TOP_Z                                # 13.5; rests on the case top
CANOPY_TONGUE_TOP_Z = C.COVER_TOP_Z + CANOPY_ROOF_WALL             # 15.0; south tongue slab roof (underside on the cover)
CANOPY_RIDGE_TOP_Z  = C.USB_C_BODY_TOP_Z + CANOPY_ROOF_CLEAR + CANOPY_ROOF_WALL             # 21.9
# NW corner radius = the case's own rounded corner AT the chamfer-first line it sets on
# (outer corner arc = WALL + CLEAR, pulled in by one chamfer leg).
CANOPY_CORNER_R     = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE - C.OUTER_TOP_CHAMFER            # ≈ 3.35


def _ease_out(y0: float, z0: float, y1: float, z1: float, n: int) -> list[tuple[float, float]]:
    """Interior points of a quadratic ease-OUT (1−(1−t)²) from (y0,z0) to (y1,z1).

    Steep at y0 (the ramp rises FAST off the foot) and horizontal-tangent at y1 (eases into
    the flat roof with no crease there). This is the 'mirrored slide' — the low belly is gone,
    so the roof underside climbs clear of the bay components quickly. Endpoints omitted."""
    out = []
    for i in range(1, n - 1):
        t = i / (n - 1)
        out.append((y0 + (y1 - y0) * t, z0 + (z1 - z0) * (1 - (1 - t) ** 2)))
    return out


def _dedup(pts: list[tuple[float, float]], tol: float = 1e-4) -> list[tuple[float, float]]:
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) > tol or abs(p[1] - out[-1][1]) > tol:
            out.append(p)
    return out


def _yz_prism(top_pts: list[tuple[float, float]], z_base: float, x_lo: float, x_width: float,
              fillets_2d: list[tuple[float, float, float]] | None = None,
              spline_range: tuple[float, float] | None = None) -> Part:
    """Extrude a Y–Z profile (flat base at ``z_base`` closed by the ``top_pts`` edge, ordered
    by ascending Y) along +X by ``x_width``, positioned so its −X face sits at ``x_lo``.

    ``fillets_2d`` rounds the profile vertex at each ``(y, z, r)`` in 2-D. ``spline_range``
    ``(y0, y1)`` draws the ramp between those Y as a real **Spline** (a smooth curved edge, so
    the swept surface has no facet steps) with a horizontal tangent at ``y1`` (eases into the
    flat roof); the rest of the profile stays straight ``Line`` segments."""
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
                    start_tan = (1.0, 2.0 * (ramp[-1][1] - ramp[0][1]) / (ramp[-1][0] - ramp[0][0]))
                    Line((y_lo, z_base), before[0])              # south face
                    if len(before) >= 2:
                        Polyline(*before)                         # flat tongue
                    Spline(*ramp, tangents=(start_tan, (1.0, 0.0)))   # smooth ease-out ramp
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
        extrude(amount=x_width)
    assert bp.part is not None
    return cast(Part, Pos(x_lo, 0, 0) * bp.part)


def _roofline() -> list[tuple[float, float]]:
    """The Y–Z top edge, south → north: a low tongue (rests on the cover) → an ease-OUT ramp
    that rises FAST off the foot then eases into the flat roof → flat roof. The near-vertical
    north wall comes from the base closure (its top corner is rounded by CANOPY_NORTH_ROUND_R)."""
    z_low, z_ridge = CANOPY_TONGUE_TOP_Z, CANOPY_RIDGE_TOP_Z
    roof = [(CANOPY_SOUTH_Y, z_low), (CANOPY_RAMP_FOOT_Y, z_low)]
    roof += _ease_out(CANOPY_RAMP_FOOT_Y, z_low, CANOPY_RAMP_TOP_Y, z_ridge,
                      CANOPY_RAMP_SAMPLES)
    roof += [(CANOPY_RAMP_TOP_Y, z_ridge), (CANOPY_NORTH_OUTER_Y, z_ridge)]
    return roof


def _round_nw_corner(part: Part, x_w: float, y_n: float, r: float, z0: float, z1: float) -> Part:
    """Round the vertical NW corner (west wall ∩ north wall) to radius ``r`` by boolean —
    subtract the sharp sliver outside the corner arc. Robust where a 3-D ``fillet`` fails
    because it collides with the north round-over. Matches the case's own corner radius at the
    chamfer-first line the cap sets on."""
    cx, cy = x_w + r, y_n - r                         # arc centre (13.75, 118.25 for r=3.35)
    h = z1 - z0
    box = cast(Part, Solid.make_box(r, r, h).translate((x_w, y_n - r, z0)))
    cyl = cast(Part, Solid.make_cylinder(r, h).translate((cx, cy, z0)))
    sliver = cast(Part, box - cyl)                    # the sharp corner outside the arc
    return cast(Part, part - sliver)


def build_canopy(hollow: bool = True) -> Part:
    """The separate fastback canopy that SETS ON the case top over the bay.

    It rests on the case at ``CANOPY_SEAT_Z``; its −X / +Y edges land at the chamfer FIRST
    point (``CANOPY_WEST_OUTER_X`` / ``CANOPY_NORTH_OUTER_Y``) on the flat wall-top, leaving
    the chamfer EXPOSED (no fill, not flush). Nothing drops below the seat. The NW corner is
    rounded to the case's own corner radius. ``hollow=False`` returns the solid envelope;
    ``hollow=True`` (default) the printed shell."""
    x_w, x_e = CANOPY_WEST_OUTER_X, CANOPY_EAST_X
    y_n = CANOPY_NORTH_OUTER_Y
    z_seat, z_ridge = CANOPY_SEAT_Z, CANOPY_RIDGE_TOP_Z
    w_roof, w_side = CANOPY_ROOF_WALL, CANOPY_SIDE_WALL

    ramp_span = (CANOPY_RAMP_FOOT_Y, CANOPY_RAMP_TOP_Y)
    roof = _roofline()
    body = _yz_prism(roof, z_base=z_seat, x_lo=x_w, x_width=x_e - x_w,
                     fillets_2d=[(y_n, z_ridge, CANOPY_NORTH_ROUND_R)], spline_range=ramp_span)
    body = _round_nw_corner(body, x_w, y_n, CANOPY_CORNER_R, z_seat - 0.1, z_ridge + 0.1)
    shell = body

    if hollow:
        # Roofline-following cavity, open at the bottom (drops over the bay). Roof/east wall =
        # CANOPY_ROOF_WALL; the N/W walls stay CANOPY_SIDE_WALL thick (match the case). The
        # south tongue (a one-wall slab resting on the cover) stays solid — the cavity starts
        # at the ramp foot, and its floor is open so nothing is added below the seat.
        y_n_inner = y_n - w_side
        cav_roof = [(y, z - w_roof) for (y, z) in roof
                    if CANOPY_RAMP_FOOT_Y - 1e-6 <= y <= y_n_inner]
        cav_roof.append((y_n_inner, z_ridge - w_roof))
        cav = _yz_prism(_dedup(cav_roof), z_base=z_seat - 3.0,
                        x_lo=x_w + w_side, x_width=(x_e - w_roof) - (x_w + w_side),
                        spline_range=ramp_span)
        shell = cast(Part, shell - cav)

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
