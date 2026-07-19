"""Fastback canopy over the MCU / JST / slide-switch bay — FUSED into the TOP cover.

``case.build_top_part`` adds this onto the TOP, so the MCU hood is integral to the cover, not
a separate part. Its ``CANOPY_*`` parameters are self-contained here (not in constants.py) and
depend only on base geometry constants. Cross-section is a Y–Z roofline swept along the bay's
X width (case Y, south → north):

  • Foot   — the ramp merges tangentially DOWN into the cover surface (``CANOPY_FOOT_Z``) —
             NO tongue. The body base drops to ``CANOPY_FUSE_BASE_Z`` (one cover thickness
             below) so it overlaps the cover/walls for a clean OCC union.
  • Ramp   — a tangent S-curve (``_smoothstep`` via a real ``Spline`` — horizontal at both
             ends, no crease) up to the flat roof. Reaches full height ``CANOPY_RAMP_TOP_OLED_GAP``
             before the OLED pins; the whole south bay is empty (PCB-level) so the low foot clears.
  • Roof   — FLAT at ``CANOPY_RIDGE_TOP_Z`` over the MCU (clears the USB-C stack).
  • North / West — VERTICAL walls landing at the chamfer FIRST point (chamfer EXPOSED); the
             NW corner is rounded to the case's own corner radius. The USB-C port is cut
             through the north wall (required — the jack pokes into it).
  • East   — plain vertical wall on the switch-column boundary.

Tangent curves are 2-D profile splines/fillets on the swept cross-section (robust), not
fragile 3-D solid fillets. Still deferred: the reset poke-hole and the slide finger-bowl."""
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
# Canopy parameters (self-contained; depend only on base geometry constants). The canopy is
# FUSED into the TOP cover (``case.build_top_part`` adds it): the ramp grows out of the cover
# surface and merges tangentially into it — no separate part, no standing tongue. Its body
# base drops one cover thickness so it OVERLAPS the cover/walls for a clean OCC union.
# ---------------------------------------------------------------------------
CANOPY_ROOF_WALL    = 1.5                       # roof + east-wall shell thickness
CANOPY_SIDE_WALL    = 4.0                       # N + W wall thickness (case-like; thinned from 4.75
                                               #   so the west cavity clears the nice!nano's west edge)
CANOPY_ROOF_CLEAR   = 0.6                       # headroom over the USB-C body top
# N/W walls land at the chamfer FIRST point (inner chamfer line); the chamfer stays exposed
# (walls are the outer wall face pulled IN by one chamfer leg).
CANOPY_WEST_OUTER_X = (C.pcb_to_case(0, 0)[0] - C.WALL_THICKNESS - C.PCB_XY_CLEARANCE
                       + C.OUTER_TOP_CHAMFER)                                               # ≈ 10.4
CANOPY_NORTH_OUTER_Y = (C.pcb_to_case(0, C.MCU_Y_RELIEF_TARGET_Y)[1]
                        + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE - C.OUTER_TOP_CHAMFER)       # ≈ 121.6
CANOPY_EAST_X       = 34.6                       # switch-column boundary (bay east edge)
# Ramp foot: where the slip merges DOWN into the cover surface (tangent, no tongue). The whole
# south bay is empty (PCB-level ~7.9 mm) until the tall MCU stack at ~Y83, so the foot sits low.
CANOPY_RAMP_FOOT_Y  = 62.0
CANOPY_RAMP_TOP_OLED_GAP = 0.5
CANOPY_RAMP_TOP_Y   = C.pcb_to_case(*C.J_OLED_POS)[1] - CANOPY_RAMP_TOP_OLED_GAP            # ≈ 81.6
CANOPY_RAMP_SAMPLES = 9      # control points pinning the S-curve for the Spline (smooth)
CANOPY_NORTH_ROUND_R = 2.5
# Heights. The ramp foot merges at the cover surface; the body base drops one cover thickness
# (to MAIN_RIM_Z) so it overlaps the cover/walls for a clean fuse into the TOP.
CANOPY_FOOT_Z       = C.COVER_TOP_Z                                # 13.5; ramp foot = cover surface
CANOPY_FUSE_BASE_Z  = C.MAIN_RIM_Z                                 # 12.5; base overlaps the cover for the fuse
CANOPY_RIDGE_TOP_Z  = C.USB_C_BODY_TOP_Z + CANOPY_ROOF_CLEAR + CANOPY_ROOF_WALL             # 21.9
# NW corner radius = the case's own rounded corner AT the chamfer-first line.
CANOPY_CORNER_R     = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE - C.OUTER_TOP_CHAMFER            # ≈ 3.35
# USB-C port through the north wall — REQUIRED for the fused fit (the jack pokes into the wall;
# it used to sit open over the +Y wall). Centred on the MCU X column. The reset poke-hole and
# slide finger-bowl are still deferred.
CANOPY_USB_W        = C.USB_C_W + 2.0                              # 11.0; port width (jack + plug clearance)
CANOPY_USB_Z_LO     = 13.0                                         # port bottom
CANOPY_USB_Z_HI     = 20.5                                         # port top (clears the USB-C body 19.8)


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
        extrude(amount=x_width)
    assert bp.part is not None
    return cast(Part, Pos(x_lo, 0, 0) * bp.part)


def _roofline() -> list[tuple[float, float]]:
    """The Y–Z top edge, south → north: the ramp foot merges into the cover surface (no
    tongue) → a tangent S-curve slip up → flat roof. The near-vertical north wall comes from
    the base closure (its top corner is rounded by CANOPY_NORTH_ROUND_R)."""
    z_foot, z_ridge = CANOPY_FOOT_Z, CANOPY_RIDGE_TOP_Z
    roof = [(CANOPY_RAMP_FOOT_Y, z_foot)]
    roof += _smoothstep(CANOPY_RAMP_FOOT_Y, z_foot, CANOPY_RAMP_TOP_Y, z_ridge,
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
    """The fastback canopy that FUSES into the TOP cover over the bay.

    The ramp foot merges tangentially into the cover surface (``CANOPY_FOOT_Z``) — no tongue;
    the body base drops to ``CANOPY_FUSE_BASE_Z`` so it overlaps the cover/walls for a clean
    union. Its −X / +Y walls land at the chamfer FIRST point (``CANOPY_WEST_OUTER_X`` /
    ``CANOPY_NORTH_OUTER_Y``), chamfer EXPOSED; the NW corner is rounded to the case's own
    corner radius. ``hollow=False`` returns the solid envelope; ``hollow=True`` (default) the
    printed shell. ``case.build_top_part`` adds the result onto the TOP."""
    x_w, x_e = CANOPY_WEST_OUTER_X, CANOPY_EAST_X
    y_n = CANOPY_NORTH_OUTER_Y
    z_base, z_ridge = CANOPY_FUSE_BASE_Z, CANOPY_RIDGE_TOP_Z
    w_roof, w_side = CANOPY_ROOF_WALL, CANOPY_SIDE_WALL

    ramp_span = (CANOPY_RAMP_FOOT_Y, CANOPY_RAMP_TOP_Y)
    roof = _roofline()
    body = _yz_prism(roof, z_base=z_base, x_lo=x_w, x_width=x_e - x_w,
                     fillets_2d=[(y_n, z_ridge, CANOPY_NORTH_ROUND_R)], spline_range=ramp_span)
    body = _round_nw_corner(body, x_w, y_n, CANOPY_CORNER_R, z_base - 0.1, z_ridge + 0.1)
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

    # USB-C port through the north (+Y) wall, centred on the MCU X column (required for fit).
    ucx = C.pcb_to_case(*C.MCU_POS)[0]
    usb = Solid.make_box(CANOPY_USB_W, w_side + 2.0, CANOPY_USB_Z_HI - CANOPY_USB_Z_LO).translate(
        (ucx - CANOPY_USB_W / 2, (y_n - w_side) - 1.0, CANOPY_USB_Z_LO))
    shell = cast(Part, shell - usb)

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
