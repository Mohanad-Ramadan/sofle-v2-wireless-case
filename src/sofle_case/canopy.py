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
             NW corner is rounded to the case's own corner radius. The USB-C port is cut
             through the north wall (required — the jack pokes into it).
  • East   — plain vertical wall on the switch-column boundary.

  • Reset  — a vertical Ø``RESET_POKE_DIA`` poke-hole is bored straight down through the roof
             directly above RSW1 (top-mounted, ~16 mm inboard — a side hole can't reach it),
             with a countersunk funnel mouth so a reset tool self-guides in. It breaks into the
             open bay under the roof; the tool travels the rest of the way to the button.

Tangent curves are 2-D profile splines/fillets on the swept cross-section (robust), not
fragile 3-D solid fillets. The slide finger-bowl (over on the −X wall) is handled in ``tray``
and split cleanly into the TOP part by ``case``'s local seam step-down."""
from __future__ import annotations
from typing import cast

from build123d import (
    Part, Pos, Line, Polyline, Spline, make_face, extrude, fillet, chamfer, Solid,
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
CANOPY_RAMP_SAMPLES = 9      # control points pinning the S-curve for the Spline (smooth)
CANOPY_NORTH_ROUND_R = 2.5
# Round-over of the tall WEST + NW top shoulder so it reads with the case's soft corners, not a
# hard block. The EAST top edge (switch-column side) is left sharp on purpose. 3.35 (the case
# corner radius) can't fit — OCC caps this edge set at ~2.36 where the ramp meets the flat roof
# and where the wall is short at the foot — so it lands just under that ceiling.
CANOPY_WEST_ROUND_R = 2.3
# Heights. The ramp foot merges at the cover surface; the body base drops one cover thickness
# (to MAIN_RIM_Z) so it overlaps the cover/walls for a clean fuse into the TOP.
CANOPY_FOOT_Z       = C.COVER_TOP_Z                                # 13.5; ramp foot = cover surface
CANOPY_FUSE_BASE_Z  = C.MAIN_RIM_Z                                 # 12.5; base overlaps the cover for the fuse
CANOPY_RIDGE_TOP_Z  = C.USB_C_BODY_TOP_Z + CANOPY_ROOF_CLEAR + CANOPY_ROOF_WALL             # 21.9
# NW corner radius = the case's own rounded corner AT the facet's rim line.
CANOPY_CORNER_R     = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE - C.RIM_FACET_RUN                # ≈ 3.25
# USB-C port through the north wall — REQUIRED for the fused fit (the jack pokes into the wall;
# it used to sit open over the +Y wall). Centred on the MCU X column.
CANOPY_USB_W        = C.USB_C_W + 2.0                              # 11.0; port width (jack + plug clearance)
CANOPY_USB_Z_LO     = C.MCU_PCB_TOP_Z - 0.8                        # port bottom; tracks the PCB (was literal 13.0)
CANOPY_USB_Z_HI     = C.USB_C_BODY_TOP_Z + 0.7                     # port top; clears the USB-C body (was literal 20.5)

# Canopy roof-edge chamfer: the same drafted-facet STYLE as the case rim (slope run/drop),
# scaled down so the north face's chamfer toe stays clear of the USB-C port mouth below it.
CANOPY_TOP_CHAMFER_V = min(2.4, CANOPY_RIDGE_TOP_Z - CANOPY_USB_Z_HI - 0.2)   # vertical leg
CANOPY_TOP_CHAMFER_H = CANOPY_TOP_CHAMFER_V * C.RIM_FACET_RUN / C.RIM_FACET_DROP  # horizontal leg
assert CANOPY_TOP_CHAMFER_V > 0.5, "USB port leaves no room for the canopy roof chamfer"

# Reset poke-hole: a vertical bore straight down through the canopy roof directly above RSW1,
# with a countersunk funnel mouth on the roof surface so a reset tool self-guides in. The bore
# breaks into the open bay under the roof (RSW1 sits in the plate's open notch, no membrane
# above it), so the tool reaches the button through the bay.
RESET_POKE_DIA         = 1.75  # mm; reset-pin bore (bumped from 1.0 for an easier target)
RESET_FUNNEL_MOUTH_DIA = 2.75  # mm; lead-in mouth scaled to the wider bore (~0.75 mm/side chamfer)
RESET_FUNNEL_DEPTH     = 1.2   # mm; lead-in depth below the surface (mouth → bore)


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


def _canopy_roof_z(y: float) -> float:
    """Outer roof Z at case-Y ``y`` along the swept roofline (south ramp S-curve → flat ridge),
    matching ``_roofline`` / ``_smoothstep`` so the funnel mouth anchors to the actual sloped
    surface above RSW1 rather than to a fixed height."""
    y0, y1 = CANOPY_RAMP_FOOT_Y, CANOPY_RAMP_TOP_Y
    z0, z1 = CANOPY_FOOT_Z, CANOPY_RIDGE_TOP_Z
    if y <= y0:
        return z0
    if y >= y1:
        return z1
    t = (y - y0) / (y1 - y0)
    return z0 + (z1 - z0) * (3 * t * t - 2 * t ** 3)


def _reset_poke_hole() -> Part:
    """Vertical bore + countersunk funnel cutter over RSW1 (subtracted from the fused canopy).

    The bore runs from above the ridge down past the canopy base so it is a clean through-cut
    of the roof (and, for the solid ``hollow=False`` envelope, of the whole block). The funnel
    is a cone widening from the bore radius (``RESET_FUNNEL_DEPTH`` below the surface) to the
    mouth radius at the sloped roof surface, so wherever it crosses the roof it leaves a
    countersunk mouth; it is capped just above the surface to avoid scalloping the uphill roof."""
    rx, ry = C.pcb_to_case(*C.SW_RESET_POS)
    surf_z = _canopy_roof_z(ry)
    r_bore = RESET_POKE_DIA / 2

    z_top = CANOPY_RIDGE_TOP_Z + 1.0            # above everything (removes only air up here)
    z_bot = CANOPY_FUSE_BASE_Z - 1.0            # below the base → through-cut of the roof
    bore = Solid.make_cylinder(r_bore, z_top - z_bot).translate((rx, ry, z_bot))

    r_mouth = RESET_FUNNEL_MOUTH_DIA / 2
    grow = (r_mouth - r_bore) / RESET_FUNNEL_DEPTH   # radius growth per mm of depth
    cone_bot_z = surf_z - RESET_FUNNEL_DEPTH         # bore radius here
    cone_top_z = surf_z + 1.0                        # r_mouth reached at the surface, opens a touch above
    cone_h = cone_top_z - cone_bot_z
    r_cone_top = r_bore + grow * cone_h
    funnel = Solid.make_cone(r_bore, r_cone_top, cone_h).translate((rx, ry, cone_bot_z))

    return cast(Part, bore + funnel)


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


def _round_west_top_edges(part: Part, x_w: float, x_e: float, r: float) -> Part:
    """CHAMFER the highest WEST + NW top-shoulder edges (roof/ramp ↔ west wall) so the tall
    west side carries the same drafted-facet style as the case walls (was a round-over — the
    only rounded shoulder left on an otherwise-chamfered case). Only the west half is touched —
    the EAST top edge (switch-column boundary) is left sharp on purpose. Done on the SOLID
    envelope (before hollowing) where there is full material below the cut; the cavity is set
    in one wall thickness so it never reaches it. Asymmetric (facet-slope) chamfer is tried
    both ways, then symmetric, then the old fillet as a last resort — never left hard."""
    x_mid = (x_w + x_e) / 2
    edges = [e for e in part.edges()
             if e.center().X < x_mid                          # west half only (east stays sharp)
             and abs(e.center().X - x_w) < 1.0                # on the west wall line
             and e.center().Z > C.COVER_TOP_Z + 1.0           # the tall upper shoulder
             and e.length > 1.0
             and abs(e.tangent_at(0.5).Z) < 0.9]              # top edges, not the vertical corner
    if not edges:
        return part
    v, h = CANOPY_TOP_CHAMFER_V, CANOPY_TOP_CHAMFER_H
    for args in ((v, h), (h, v), ((v + h) / 2, None)):
        try:
            return cast(Part, chamfer(edges, length=args[0], length2=args[1]))
        except (ValueError, Standard_Failure, TypeError):
            continue
    for radius in (r, 2.0, 1.5, 1.0):
        try:
            return cast(Part, fillet(edges, radius=radius))
        except (ValueError, Standard_Failure):
            continue
    return part


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
                     chamfers_2d=[(y_n, z_ridge,
                                   CANOPY_TOP_CHAMFER_V, CANOPY_TOP_CHAMFER_H)],
                     spline_range=ramp_span)
    body = _round_nw_corner(body, x_w, y_n, CANOPY_CORNER_R, z_base - 0.1, z_ridge + 0.1)
    # Round the tall west + NW top shoulder (east left sharp) on the solid, before hollowing.
    body = _round_west_top_edges(body, x_w, x_e, CANOPY_WEST_ROUND_R)
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

    # Reset poke-hole: vertical bore + funnel down through the roof over RSW1.
    shell = cast(Part, shell - _reset_poke_hole())

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
