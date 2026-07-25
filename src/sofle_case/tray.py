"""Outer shell + inner cavity, all walls flat at MAIN_RIM_Z (flush with the
switch plate). The MCU corner is a plain flat wall — no hill; the nice!nano and
its USB-C jack sit open above the rim. The slide-switch bowl scoop on the −X
wall and the +Y wall's B+/B- relief bump are the only local wall features."""
from __future__ import annotations
import math
from functools import cache
from typing import cast
from build123d import (
    Part, Wire, Pos, Polyline, make_face, extrude, offset, Kind, Solid,
    Plane, BuildPart, BuildSketch, BuildLine, Axis, fillet, chamfer, loft,
)
from OCP.Standard import Standard_Failure
from . import constants as C
from .pcb_geometry import polygon_in_case_coords


# ---------------------------------------------------------------------------
# Shared 2D faces — used by shell, cavity, AND hill ring so all share the
# same outer/inner XY profile. This is what guarantees the hill is flush.
# ---------------------------------------------------------------------------

def _polygon_wire() -> Wire:
    poly = polygon_in_case_coords()
    pts = poly[:-1] if poly[0] == poly[-1] else poly
    with BuildLine() as bl:
        Polyline(*pts, close=True)
    assert bl.line is not None
    return cast(Wire, bl.line)


def _poly_pts() -> list[tuple[float, float]]:
    poly = polygon_in_case_coords()
    return poly[:-1] if poly[0] == poly[-1] else poly


def _reflex_vertex_points() -> list[tuple[float, float]]:
    """Outline vertices where the boundary turns the 'wrong way' (reflex, ≥3°).

    A Kind.ARC offset rounds convex corners but leaves reflex corners as sharp
    V-notches — each one used to throw a spurious crease through the outer wall
    and the rim facet. These are the vertices `_rounded_wire` rounds away."""
    pts = _poly_pts()
    n = len(pts)
    area2 = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1]
                for i in range(n))
    ccw = area2 > 0
    out: list[tuple[float, float]] = []
    for i in range(n):
        p0, p1, p2 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
        ax, ay = p1[0] - p0[0], p1[1] - p0[1]
        bx, by = p2[0] - p1[0], p2[1] - p1[1]
        cross = ax * by - ay * bx
        reflex = (cross < 0) if ccw else (cross > 0)
        turn = abs(math.degrees(math.atan2(cross, ax * bx + ay * by)))
        if reflex and turn >= 3.0:
            out.append(p1)
    return out


@cache
def _rounded_wire() -> Wire:
    """The outline wire with every REFLEX vertex rounded by REFLEX_ROUND_R (2-D).

    Used for the OUTER wall and the rim-facet profiles only, so the drafted
    chamfer flows continuously around the jogs/notches instead of creasing at
    each reflex corner. The CAVITY (and the sandwich plate/pocket offsets in
    case.py) keep the sharp polygon — PCB clearance and rabbet fit unchanged;
    rounding a reflex corner only ADDS outer material (fills the notch), so the
    wall gets locally thicker there, never thinner. Per-vertex radius fallback
    so one tight corner can't abort the profile."""
    with BuildSketch(Plane.XY) as sk:
        with BuildLine():
            Polyline(*_poly_pts(), close=True)
        make_face()
        for rx, ry in _reflex_vertex_points():
            for r in (C.REFLEX_ROUND_R, C.REFLEX_ROUND_R * 0.5, C.REFLEX_ROUND_R * 0.25):
                verts = [v for v in sk.vertices()
                         if abs(v.X - rx) < 0.05 and abs(v.Y - ry) < 0.05]
                if not verts:
                    break
                try:
                    fillet(verts, radius=r)
                    break
                except (ValueError, Standard_Failure):
                    continue
    return cast(Wire, sk.sketch.faces()[0].outer_wire())


def _outer_extruded(z_lo: float, z_hi: float) -> Part:
    """REFLEX-ROUNDED polygon offset OUTWARD by (WALL_THICKNESS + PCB_XY_CLEARANCE),
    Kind.ARC, extruded from z_lo to z_hi. Rounded so the outer skin has no sharp
    V-notches at reflex outline corners (see _rounded_wire)."""
    wire = _rounded_wire()
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            face = make_face(wire)  # type: ignore[arg-type]
            face = offset(face, amount=C.WALL_THICKNESS + C.PCB_XY_CLEARANCE, kind=Kind.ARC)
        extrude(amount=z_hi - z_lo)
    assert bp.part is not None
    return cast(Part, Pos(0, 0, z_lo) * bp.part)


def offset_extruded(amount: float, z_lo: float, z_hi: float, kind: Kind = Kind.ARC,
                    rounded: bool = False) -> Part:
    """PCB polygon offset OUTWARD by ``amount``, extruded ``z_lo → z_hi``.

    Public helper shared with the sandwich split (case.py): the inset floor plate
    and the tub's plate-pocket cutter are both concentric offsets of the same
    polygon, so they nest with a uniform radial gap. ``amount`` between the cavity
    offset (``PCB_XY_CLEARANCE``) and the outer-skin offset
    (``WALL_THICKNESS + PCB_XY_CLEARANCE``) lands inside the wall. ``Kind.ARC``
    matches the outer shell's rounded convex corners. ``rounded=True`` uses the
    reflex-rounded outline (facet band only — plate/pocket stay sharp)."""
    wire = _rounded_wire() if rounded else _polygon_wire()
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            face = make_face(wire)  # type: ignore[arg-type]
            face = offset(face, amount=amount, kind=kind)
        extrude(amount=z_hi - z_lo)
    assert bp.part is not None
    return cast(Part, Pos(0, 0, z_lo) * bp.part)


def _inner_extruded(z_lo: float, z_hi: float) -> Part:
    """PCB polygon offset by +PCB_XY_CLEARANCE, Kind.INTERSECTION, extruded z_lo→z_hi."""
    wire = _polygon_wire()
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            face = make_face(wire)  # type: ignore[arg-type]
            face = offset(face, amount=C.PCB_XY_CLEARANCE, kind=Kind.INTERSECTION)
        extrude(amount=z_hi - z_lo)
    assert bp.part is not None
    return cast(Part, Pos(0, 0, z_lo) * bp.part)


# ---------------------------------------------------------------------------
# Shell + cavity
# ---------------------------------------------------------------------------

def _outer_shell(rim_z: float = C.MAIN_RIM_Z) -> Part:
    return _outer_extruded(0.0, rim_z)


def _cavity_solid(rim_z: float = C.MAIN_RIM_Z) -> Part:
    return _inner_extruded(C.FLOOR_THICKNESS, rim_z + 0.01)


# ---------------------------------------------------------------------------
# +Y wall B+/B- relief bump (MCU corner)
# ---------------------------------------------------------------------------

def _axis_box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Part:
    """Axis-aligned box from (x0,y0,z0) to (x1,y1,z1)."""
    return cast(Part, Solid.make_box(x1 - x0, y1 - y0, z1 - z0).translate((x0, y0, z0)))


def _mcu_y_relief_x_range() -> tuple[float, float]:
    """X span of the +Y relief, as (x_lo, x_full_hi).

    x_lo reaches the −X wall's OUTER face so the pushed-out cover face joins
    the corner with no notch — but this is add-only (the widen below starts
    inboard), so the −X wall itself is never cut.

    x_full_hi reaches all the way to where the polygon itself naturally steps
    to MCU_Y_RELIEF_TARGET_Y (MCU_Y_RELIEF_X_HI) — the relief must cover this
    whole stretch or a gap remains between the ramp and the polygon's own
    step, which reads as a dip back to the old tight line."""
    corner_x = C.pcb_to_case(0, 0)[0]
    x_lo = corner_x - C.WALL_THICKNESS - C.PCB_XY_CLEARANCE            # −X wall outer face
    x_full_hi = C.pcb_to_case(C.MCU_Y_RELIEF_X_HI, 0)[0]
    return x_lo, x_full_hi


def _mcu_y_relief_bump(rim_z: float = C.MAIN_RIM_Z) -> Part:
    """Push the MCU cover's +Y OUTER wall out to the index-column line (+Y wall
    only — see MCU_Y_RELIEF_* comment in constants.py). Paired with
    _mcu_y_relief_widen() so wall thickness is preserved — the wall shifts
    outward, it doesn't thin out.

    A single box capped at MAIN_RIM_Z: the walls are flat at the rim now (no
    hill), so there is no wall material above the rim to relieve — the B+/B-
    pads clear into open air above 12.5.

    Z0 starts at the case bottom (not FLOOR_THICKNESS) so this box genuinely
    overlaps the solid floor slab beneath — that's what keeps the resulting
    ridge structurally fused to the rest of the case once _mcu_y_relief_widen()
    hollows out the cavity behind it; a coincident-face touch alone isn't
    reliable enough for OCC's boolean union."""
    x_lo, x_full_hi = _mcu_y_relief_x_range()
    y_old_outer = C.pcb_to_case(0, 0)[1] + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    y_new_outer = C.pcb_to_case(0, C.MCU_Y_RELIEF_TARGET_Y)[1] + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    # Start at the polygon vertex Y (arc start of the Kind.ARC corner at
    # vertex [16]) so the −X wall face is continuous up to y_new_outer —
    # otherwise the arc dips inward between the arc start and the old overlap.
    arc_start_y = C.pcb_to_case(0, 0)[1]
    y_lo = min(y_old_outer - C.MCU_Y_RELIEF_OVERLAP, arc_start_y)
    return _axis_box(x_lo, x_full_hi, y_lo, y_new_outer, 0.0, rim_z)


def _mcu_y_relief_widen(rim_z: float = C.MAIN_RIM_Z) -> Part:
    """Widen the cavity to match _mcu_y_relief_bump() — removes material between
    the old and new inner +Y-wall faces so the added outer bump becomes usable
    interior clearance rather than solid wall.

    Two boxes. The base box starts 0.3 mm inboard of the −X wall's inner
    polygon face: its −X cut runs the full cavity Y-span, so it must stay off
    the −X wall face (X=inner_x) — a box whose −X face *overlaps* that wall
    face over the shared Y-range triggers an OCC coincident-face BRepCheck
    failure. The base box therefore leaves a 0.3 mm strip of bump material
    unremoved at the corner (X=inner_x..inner_x+0.3, Y=corner_y..y_new_inner).

    The corner box removes exactly that strip. It reaches the −X wall face
    (x_lo=inner_x) but only over Y=corner_y..y_new_inner — i.e. it starts
    exactly where the −X wall face ends (Y=corner_y, the polygon vertex). Its
    −X cut face is thus *contiguous* with the wall face, not overlapping it, so
    the two merge into one continuous −X inner wall up to the corner with no
    coincident face and no residual ledge. x_hi overlaps the base box so there
    is no gap between the two cuts.

    Ceiling band (sandwich TOP only, rim_z > MAIN_RIM_Z): below the plate top the
    full X-span is hollowed as before (clearance for the nice!nano + B+/B- wires).
    Above the plate top — the band that becomes the TOP part's ceiling — the hollow
    is bounded on TWO axes so the top closes down to just the battery-wire channel:
      • X ≤ bay_x — the switch-column side (east of the bay) keeps its solid bump
        material as ceiling; without this the switch column next to the MCU was
        left open to air.
      • Y ≤ board_y_hi (the nice!nano's +Y face) — the +Y relief strip out toward
        the USB-C jack is NOT hollowed, so the ceiling closes over it. The USB-C
        jack exits sideways over the +Y wall (into open air above the rim) and
        needs no ceiling hole; the battery wire routes inward under the board and
        drops through the bay, which stays open over the board footprint.
    bay_x is the plate's own switch/bay boundary (MCU_Y_RELIEF_CEILING_X), which
    also clears the nice!nano's right edge; board_y_hi is the module's +Y edge so
    the ceiling starts exactly where the board ends (no board-edge interference)."""
    _, x_full_hi = _mcu_y_relief_x_range()
    inner_x     = C.pcb_to_case(0, 0)[0] - C.PCB_XY_CLEARANCE          # −X inner wall face
    corner_y    = C.pcb_to_case(0, 0)[1]                              # polygon vertex Y; −X wall face ends here
    y_new_inner = C.pcb_to_case(0, C.MCU_Y_RELIEF_TARGET_Y)[1] + C.PCB_XY_CLEARANCE
    _, y_safe_lo = C.pcb_to_case(0, C.MCU_POS[1])                      # safely inside cavity
    z_mid = C.MAIN_RIM_Z + 0.01                                       # plate top: full-X clearance up to here
    base   = _axis_box(inner_x + 0.3, x_full_hi, y_safe_lo, y_new_inner, C.FLOOR_THICKNESS, z_mid)
    corner = _axis_box(inner_x, inner_x + 0.35, corner_y, y_new_inner, C.FLOOR_THICKNESS, z_mid)
    widen  = cast(Part, base + corner)
    if rim_z > C.MAIN_RIM_Z + 1e-6:
        bay_x = C.pcb_to_case(C.MCU_Y_RELIEF_CEILING_X, 0)[0]
        board_y_hi = C.pcb_to_case(*C.MCU_POS)[1] + C.MCU_BODY_L / 2   # nice!nano +Y face
        z_hi  = rim_z + 0.01
        u_base   = _axis_box(inner_x + 0.3, bay_x, y_safe_lo, board_y_hi, z_mid, z_hi)
        u_corner = _axis_box(inner_x, inner_x + 0.35, corner_y, board_y_hi, z_mid, z_hi)
        widen = cast(Part, widen + u_base + u_corner)
    return widen


# NB: the old `_fillet_outer_concave_corners` post-pass (per-corner 3-D fillets hunting the
# reflex V-notches) is GONE — the reflex corners are now rounded in the 2-D profile itself
# (`_rounded_wire`), so wall AND facet flow continuously through them by construction.


# ---------------------------------------------------------------------------
# Bottom counter-chamfer (elephant-foot pre-compensation)
# ---------------------------------------------------------------------------

def _chamfer_bottom_edges(part: Part) -> Part:
    """Chamfer the outer bottom perimeter (Z=0 plane) by BOTTOM_CHAMFER.

    The squished first layers fill the missing 45° wedge instead of bulging
    past the nominal footprint. The cavity floor sits at FLOOR_THICKNESS (Z=2.0),
    so the only edges in the Z≈0 plane are the floor's outer perimeter.

    Runs last in build_tray() so it does not perturb the Z-based edge selection
    used by the fillet passes. Falls back to a smaller length, then to no
    chamfer, rather than aborting the build (mirrors the other edge passes)."""
    bottom = part.edges().filter_by_position(Axis.Z, minimum=-0.01, maximum=0.01)
    if not bottom:
        return part
    for length in (C.BOTTOM_CHAMFER, C.BOTTOM_CHAMFER * 0.75):
        try:
            return cast(Part, chamfer(bottom, length=length))
        except (ValueError, Standard_Failure):
            continue
    return part


# ---------------------------------------------------------------------------
# Bump −X/+Y convex corner fillet
# ---------------------------------------------------------------------------

def _fillet_bump_neg_x_corner(part: Part) -> Part:
    """Fillet the sharp 90° convex edge at the relief bump's −X/+Y corner.

    After the bump pushes the +Y wall out, the corner at (x_lo, y_new_outer)
    is a raw box edge. This adds an arc matching the polygon offset's
    Kind.ARC radius so the corner style is consistent."""
    x_lo, _ = _mcu_y_relief_x_range()
    y_new = (C.pcb_to_case(0, C.MCU_Y_RELIEF_TARGET_Y)[1]
             + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE)
    r = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE

    z_edges = [
        e for e in (
            part.edges()
            .filter_by_position(Axis.X, minimum=x_lo - 0.5, maximum=x_lo + 0.5)
            .filter_by_position(Axis.Y, minimum=y_new - 0.5, maximum=y_new + 0.5)
        )
        if (e.bounding_box().max.Z - e.bounding_box().min.Z > 5.0
            and abs(e.tangent_at(0.5).Z) > 0.9)
    ]
    if not z_edges:
        return part
    try:
        return cast(Part, fillet(z_edges, radius=r))
    except (ValueError, Standard_Failure):
        return part


# ---------------------------------------------------------------------------
# Drafted rim facet (outer-top treatment; replaces the old flat chamfer)
# ---------------------------------------------------------------------------

def _rim_facet_frustum(drop: float, run: float, rim_z: float) -> Part:
    """The 'keep' frustum whose sloped outer wall IS the facet plane.

    A loft between two concentric PCB-polygon offsets (both Kind.ARC, so topologically
    identical — the loft is well-conditioned even on the arc corners): the outer wall
    offset at the toe (Z = rim_z − drop) tapering inward by ``run`` at the rim (Z = rim_z).
    Both cross-sections are extended ``e`` past the toe/rim along the same slope so the
    wedge cutter (outer band − this frustum) has no coincident cap faces to trip OCC."""
    outer = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    slope = run / drop                       # radial inset per unit Z
    e = 0.6                                   # end extension beyond toe and rim
    z0, z1 = rim_z - drop - e, rim_z + e
    amt0 = outer + slope * e                  # wider than the band below the toe → no cut there
    amt1 = outer - run - slope * e            # narrower above the rim
    wire = _rounded_wire()                    # reflex-rounded → facet continuous at the jogs
    with BuildPart() as bp:
        with BuildSketch(Plane(origin=(0, 0, z0))):
            face = make_face(wire)  # type: ignore[arg-type]
            face = offset(face, amount=amt0, kind=Kind.ARC)
        with BuildSketch(Plane(origin=(0, 0, z1))):
            face = make_face(wire)  # type: ignore[arg-type]
            face = offset(face, amount=amt1, kind=Kind.ARC)
        loft()
    assert bp.part is not None
    return cast(Part, bp.part)


def _rim_facet_cutter(drop: float, run: float, rim_z: float) -> Part:
    """Wedge ring shaved from the outer-wall top: the full outer prism minus the keep
    frustum. Zero width at the toe (Z = rim_z − drop), ``run`` wide at the rim. Subtracting
    it from the tray slopes the outer-top edge inward — the drafted facet."""
    outer = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    e = 0.6
    band = offset_extruded(outer, rim_z - drop - e, rim_z + e, rounded=True)
    return cast(Part, band - _rim_facet_frustum(drop, run, rim_z))


def _mcu_bump_exclusion(rim_z: float) -> Part:
    """Plan region where the POLYGON-offset facet cutters must not cut: the +Y relief bump
    is proud of the nominal outline offset over its whole footprint (it fills the NW corner
    out to the flat y = bump-face line), so the nominal wedge would tunnel grooves INSIDE
    the bump. The bump instead gets its own face-aligned wedges (`_bump_face_facets`) so its
    faces carry the SAME drafted chamfer as every other wall. The box ends at the bump's east
    face, where the polygon wall arrives at the same outer line — the polygon facet resumes
    there on the same plane, so the chamfer runs continuous across the joint."""
    x_lo, x_hi = _mcu_y_relief_x_range()
    y_lo = _poly_pts()[16][1] - 0.75      # just south of the west wall's north corner
    return _axis_box(x_lo - 1.0, x_hi + 0.02, y_lo,
                     C.OUTER_DEPTH + 2.0, 0.0, rim_z + 1.0)


def _planar_wedge(pts3d: list[tuple[float, float, float]],
                  direction: tuple[float, float, float], length: float) -> Part:
    """Planar profile (3-D points, closed) extruded ``length`` along ``direction``."""
    w = Polyline(*pts3d, close=True)
    f = make_face(w)  # type: ignore[arg-type]
    return cast(Part, extrude(f, amount=length, dir=direction))  # type: ignore[arg-type]


def _bump_face_facets(rim_z: float) -> Part:
    """Drafted-facet wedges for the +Y relief bump's own faces (north, west, NW corner).

    The bump is excluded from the polygon-offset facet (see `_mcu_bump_exclusion`), so these
    wedges cut the SAME chamfer profile (RIM_FACET_DROP/RUN) aligned to the bump's actual
    faces: a Y–Z wedge along the north face, an X–Z wedge along the west face, and a conical
    ring segment around the NW corner arc (the `_fillet_bump_neg_x_corner` cylinder), so the
    chamfer flows wall → corner → bump → polygon wall with no bare stretch and no crease."""
    drop, run = C.RIM_FACET_DROP, C.RIM_FACET_RUN
    z0, z1, z1e = rim_z - drop, rim_z, rim_z + 0.5
    x_lo, x_hi = _mcu_y_relief_x_range()
    y_out = C.pcb_to_case(0, C.MCU_Y_RELIEF_TARGET_Y)[1] + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    r = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE   # NW corner fillet radius (_fillet_bump_neg_x_corner)
    ccx, ccy = x_lo + r, y_out - r              # corner arc centre
    y_w_lo = _poly_pts()[16][1] - 0.6           # west wedge start: overlaps the polygon facet's plane

    north = _planar_wedge(
        [(ccx - 0.2, y_out + 0.2, z0), (ccx - 0.2, y_out + 0.2, z1e),
         (ccx - 0.2, y_out - run, z1e), (ccx - 0.2, y_out - run, z1),
         (ccx - 0.2, y_out, z0)],
        (1.0, 0.0, 0.0), (x_hi + 0.02) - (ccx - 0.2))
    west = _planar_wedge(
        [(x_lo - 0.2, y_w_lo, z0), (x_lo - 0.2, y_w_lo, z1e),
         (x_lo + run, y_w_lo, z1e), (x_lo + run, y_w_lo, z1),
         (x_lo, y_w_lo, z0)],
        (0.0, 1.0, 0.0), (ccy + 0.2) - y_w_lo)
    # NW corner: quadrant box minus the keep-cone (the corner cylinder tapering inward by
    # ``run`` over ``drop``, extended past both ends so no coincident caps).
    e = 0.5
    slope = run / drop
    box = _axis_box(x_lo - 0.2, ccx, ccy, y_out + 0.2, z0, z1e)
    cone = cast(Part, Solid.make_cone(
        r + slope * e, r - run - slope * e, drop + 2 * e
    ).translate((ccx, ccy, z0 - e)))
    corner = cast(Part, box - cone)
    return cast(Part, north + west + corner)


def _front_panel_params() -> tuple[float, float, float, float]:
    """Shared geometry of the deep-facet triangle on the flat central front.

    Returns ``(axis, y_toe, slope, half_toe)``: the mirror axis (flat-panel centre =
    midpoint of the flat front edge pts[4]→pts[5]), the facet toe's case-Y (the outer
    face), the plan dx/dy of each oblique slash side (``FRONT_SLASH_ELEV_RUN /
    FRONT_FACET_RUN``), and the deep-panel half-width at the toe. The flat panel is the
    outline's only symmetric south stretch, so it is the only place two mirror-image
    slashes can both land on real wall (see constants' front-facet block)."""
    pts = _poly_pts()
    p4, p5 = pts[4], pts[5]                     # flat central front (y constant)
    assert abs(p4[1] - p5[1]) < 1e-6, "flat front pts[4]→pts[5] is no longer flat; crease axis invalid"
    axis = (p4[0] + p5[0]) / 2.0
    outer = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    y_toe = p4[1] - outer
    slope = C.FRONT_SLASH_ELEV_RUN / C.FRONT_FACET_RUN
    ht = C.FRONT_PANEL_HALF_TOE
    assert ht <= (p5[0] - p4[0]) / 2 + 1e-9, "FRONT_PANEL_HALF_TOE spills the slashes off the flat panel"
    return axis, y_toe, slope, ht


def _front_slash_crossings() -> tuple[tuple[float, float, float], ...]:
    """The four deep→shallow crease crossings — a mirror pair about the flat-panel centre —
    as ``(west_rim, west_toe, east_rim, east_toe)`` in right-half case coords. Rim at
    Z = COVER_TOP_Z, toe at Z = COVER_TOP_Z − FRONT_FACET_DROP. Inspection/marker/test
    scaffolding; the region itself is built in `_front_facet_mask`."""
    axis, y_toe, slope, ht = _front_panel_params()
    y_rim = y_toe + C.FRONT_FACET_RUN
    z_rim, z_toe = C.COVER_TOP_Z, C.COVER_TOP_Z - C.FRONT_FACET_DROP
    run = C.FRONT_SLASH_ELEV_RUN
    west_toe = (axis - ht, y_toe, z_toe)
    west_rim = (axis - ht + run, y_rim, z_rim)     # rim pulled toward the axis → panel narrower at rim
    east_toe = (axis + ht, y_toe, z_toe)
    east_rim = (axis + ht - run, y_rim, z_rim)
    return west_rim, west_toe, east_rim, east_toe


def _front_facet_mask() -> Part:
    """Plan REGION (extruded prism) selecting where the deep south facet applies.

    A symmetric TRIANGLE on the flat central front (outline pts[4]→pts[5]). Its two oblique
    sides are exact mirror images about the panel centreline, so each crosses the front facet
    band as a mirrored diagonal slash (~34°); the deep panel is wider at the toe than the rim.
    The apex sits north of the facet band, and a south cap just below the toe keeps the triangle
    on the flat panel so it never bleeds onto the E2/E3 thumb ramps or the SE ramp E4 (those stay
    plain shallow perimeter facet). Replaces the old asymmetric vertical-cut + horizontal-cap
    mask. See constants.FRONT_SLASH_ELEV_RUN / FRONT_PANEL_HALF_TOE and `_front_slash_crossings`."""
    axis, y_toe, slope, ht = _front_panel_params()
    y_south = y_toe - 1.0                 # cap just south of the toe (keeps the triangle off the ramps)
    y_apex = y_toe + ht / slope           # where the two mirror sides meet, north of the facet band
    xs_w = axis - ht + slope * (y_south - y_toe)
    xs_e = axis + ht - slope * (y_south - y_toe)
    z0, z1 = -1.0, C.COVER_TOP_Z + 2.0
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            with BuildLine():
                Polyline((xs_w, y_south), (axis, y_apex), (xs_e, y_south), close=True)
            make_face()
        extrude(amount=z1 - z0)
    assert bp.part is not None
    return cast(Part, Pos(0, 0, z0) * bp.part)


def _apply_rim_facets(part: Part, rim_z: float) -> Part:
    """Shave the drafted perimeter facet (bump handled by its own face wedges) and the
    deeper south facet (masked to the front, between the two mirrored slashes)."""
    perim = cast(Part, _rim_facet_cutter(C.RIM_FACET_DROP, C.RIM_FACET_RUN, rim_z)
                 - _mcu_bump_exclusion(rim_z))
    front = cast(Part, _rim_facet_cutter(C.FRONT_FACET_DROP, C.FRONT_FACET_RUN, rim_z)
                 & _front_facet_mask())
    return cast(Part, part - perim - front - _bump_face_facets(rim_z))


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

def build_tray(rim_z: float = C.MAIN_RIM_Z) -> Part:
    """Outer shell + inner cavity, walls flat at ``rim_z``.

    ``rim_z`` defaults to ``MAIN_RIM_Z`` (12.5, flush with the switch plate) — the
    single-tray case. The sandwich TOP part raises it to ``COVER_TOP_Z`` (13.5) so
    the upper walls run high enough to carry the membrane ceiling; the outer-top
    chamfer, +Y relief and slide-switch valley all track the rim automatically."""
    shell  = _outer_shell(rim_z)
    cavity = _cavity_solid(rim_z)
    hollow = cast(Part, shell - cavity)
    hollow = cast(Part, hollow + _mcu_y_relief_bump(rim_z))
    hollow = cast(Part, hollow - _mcu_y_relief_widen(rim_z))
    # NB: the slide-switch finger scoop is NOT cut here — it is a TOP-only, above-seam feature
    # that also lowers the fused canopy, so case.build_top_part applies it (see case._slide_scoop).
    hollow = _fillet_bump_neg_x_corner(hollow)
    faceted = _apply_rim_facets(hollow, rim_z)
    chamfered = _chamfer_bottom_edges(faceted)
    if isinstance(chamfered, Part):
        return chamfered
    solids = chamfered.solids()
    return Part(children=list(solids)) if solids else Part(children=[chamfered])


# %%
if __name__ == "__main__":
    from ocp_vscode import show
    from sofle_case.tray import build_tray
    show(build_tray())
