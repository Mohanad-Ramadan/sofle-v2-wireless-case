"""Outer shell + inner cavity, all walls flat at MAIN_RIM_Z (flush with the
switch plate). The MCU corner is a plain flat wall — no hill; the nice!nano and
its USB-C jack sit open above the rim. The slide-switch bowl scoop on the −X
wall and the +Y wall's B+/B- relief bump are the only local wall features."""
from __future__ import annotations

import math
from functools import cache
from typing import cast

from build123d import (
    Axis,
    BuildLine,
    BuildPart,
    BuildSketch,
    Face,
    Kind,
    Part,
    Plane,
    Polyline,
    Pos,
    Solid,
    Wire,
    chamfer,
    extrude,
    fillet,
    make_face,
    offset,
)
from OCP.LocOpe import LocOpe_DPrism
from OCP.Standard import Standard_Failure
from OCP.TopoDS import TopoDS

from . import constants as C
from .pcb_geometry import polygon_in_case_coords, thumb_switch_midpoint_x

# ---------------------------------------------------------------------------
# Shared 2D faces keep shell, cavity, and local relief geometry on the same
# outer/inner XY profile.
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


def _grow_segments(pts: list[tuple[float, float]], idxs: set[int],
                   extra: float) -> list[tuple[float, float]]:
    """``pts`` with the segments in ``idxs`` pushed OUTWARD by ``extra``, corners re-solved.

    Segment ``i`` runs ``pts[i] -> pts[i+1]``. Each listed segment's supporting LINE is moved out
    along its own outward normal, then EVERY vertex is recomputed as the intersection of its two
    adjacent lines. Doing it by line intersection rather than by moving points is what makes the
    grown stretch join its untouched neighbours cleanly: the shared corner simply slides along the
    neighbour's own line, so no step, no taper and no new vertices appear at the handover. A
    parallel or degenerate pair keeps its original vertex."""
    if not idxs or extra == 0.0:
        return list(pts)
    n = len(pts)
    area2 = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1]
                for i in range(n))
    ccw = area2 > 0
    lines: list[tuple[float, float, float, float]] = []   # (px, py, ux, uy)
    for i in range(n):
        p, q = pts[i], pts[(i + 1) % n]
        ex, ey = q[0] - p[0], q[1] - p[1]
        el = math.hypot(ex, ey)
        ux, uy = ex / el, ey / el
        nx, ny = (uy, -ux) if ccw else (-uy, ux)          # outward normal
        off = extra if i in idxs else 0.0
        lines.append((p[0] + nx * off, p[1] + ny * off, ux, uy))
    out: list[tuple[float, float]] = []
    for i in range(n):
        ax, ay, aux, auy = lines[(i - 1) % n]
        bx, by, bux, buy = lines[i]
        den = aux * buy - auy * bux
        if abs(den) < 1e-9:                               # parallel — nothing to re-solve
            out.append(pts[i])
            continue
        t = ((bx - ax) * buy - (by - ay) * bux) / den
        out.append((ax + aux * t, ay + auy * t))
    return out


# The southern runs, as segment indices into the STRAIGHTENED outline (the list `_outer_poly_pts`
# grows): 2 = SW thumb ramp (pts[2]->pts[4]), 3 = flat front (pts[4]->pts[5]), 4 = SE ramp E4
# (pts[5]->pts[6]). These three are what SOUTH_WALL_EXTRA pushes outward; their neighbours — the
# west thumb edge and the east wall — are held, and the shared corners slide along them.
SOUTH_RUN_IDXS = frozenset({2, 3, 4})

# The flat-front/E4 corner — vertex 4 of the same list, the CONVEX one the deep facet drafts
# through. `_rounded_wire` pre-rounds it by FRONT_CORNER_ROUND_R so the facet's cone survives
# the inset there; see that constant's block.
SOUTH_E4_IDX = 4


def _outer_poly_pts() -> list[tuple[float, float]]:
    """`_poly_pts()` with the SW reflex kink dropped AND the southern runs grown outward.

    Two departures from the sharp polygon, both OUTER-ONLY — `_reflex_vertex_points` /
    `_rounded_wire` / the rim facets consume this, while the cavity and plate-fit band
    keep the full sharp `_poly_pts()`, so PCB clearance remains unchanged:

      * pts[3], the barely-1 mm reflex kink, is DROPPED so the thumb ramp pts[2]->pts[4] is ONE
        straight segment and the West crease rides a clean ramp like the East on E4. That only
        ADDS a sliver of outer material (fills the notch).
      * the three southern runs are pushed outward by ``SOUTH_WALL_EXTRA`` (`_grow_segments`) —
        the material the deep south facet is raked into. See that constant's block.
    """
    pts = _poly_pts()
    straight = pts[:3] + pts[4:]     # drop pts[3] — straighten the SW thumb ramp
    return _grow_segments(straight, set(SOUTH_RUN_IDXS), C.SOUTH_WALL_EXTRA)


def _reflex_vertex_points() -> list[tuple[float, float]]:
    """Outline vertices where the boundary turns the 'wrong way' (reflex, ≥3°).

    A Kind.ARC offset rounds convex corners but leaves reflex corners as sharp
    V-notches — each one used to throw a spurious crease through the outer wall
    and the rim facet. These are the vertices `_rounded_wire` rounds away."""
    pts = _outer_poly_pts()          # SW-straightened outline (outer wall + facet only)
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
    """The outline wire with every REFLEX vertex rounded by REFLEX_ROUND_R, plus the convex
    flat-front/E4 corner rounded by FRONT_CORNER_ROUND_R (2-D).

    Used for the OUTER wall and the rim-facet profiles only, so the drafted
    chamfer flows continuously around the jogs/notches instead of creasing at
    each reflex corner. The CAVITY and plate offsets in case.py keep the sharp
    polygon — PCB clearance unchanged;
    rounding a reflex corner only ADDS outer material (fills the notch), so the
    wall gets locally thicker there, never thinner. Per-vertex radius fallback
    so one tight corner can't abort the profile."""
    rounds = [(p, C.REFLEX_ROUND_R) for p in _reflex_vertex_points()]
    rounds.append((_outer_poly_pts()[SOUTH_E4_IDX], C.FRONT_CORNER_ROUND_R))
    with BuildSketch(Plane.XY) as sk:
        with BuildLine():
            Polyline(*_outer_poly_pts(), close=True)
        make_face()
        for (rx, ry), r0 in rounds:
            for r in (r0, r0 * 0.5, r0 * 0.25):
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

    Public helper shared with the monolithic case (case.py): fit-band support
    geometry is a concentric offset of the same
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


@cache
def outer_south_overhang() -> float:
    """How far SOUTH of Y=0 the outer skin reaches, in mm (0 before the south wall was grown).

    ``OUTER_DEPTH`` is the outer skin's own bounding depth and the footprint datum, so
    ``SOUTH_WALL_EXTRA`` was deliberately NOT folded back
    into it — the case simply reaches below Y=0 now. This reports by how much, measured off the
    real offset profile rather than predicted, because the southmost point is the thumb tip's
    offset ARC and its dip is set by where the grown corner landed, not by the growth directly.
    Public so the bbox tests can state the true depth instead of hard-coding a number."""
    return max(0.0, -_outer_extruded(0.0, 1.0).bounding_box().min.Y)


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
    Strict PCB-frame north wall is now fully chamfered like the rest of the
    perimeter — no XY mask; full loop at Z≈0.

    Runs last in build_tray() so it does not perturb Z-based edge selection.
    Falls back to a smaller length, then to no chamfer, rather than aborting
    the build. If north bottom edge is missing after facet change (tolerance
    or facet cut), the bottom loop is derived from the outer-extruded wire at
    Z≈0 to ensure the closed north segment is chamfered."""
    bottom = part.edges().filter_by_position(Axis.Z, minimum=-0.01, maximum=0.01)
    if not bottom:
        # Fallback: derive bottom loop from outer wire's bottom edges (strict frame)
        try:
            outer = _outer_extruded(0.0, 1.0)
            outer_bottom = outer.edges().filter_by_position(Axis.Z, minimum=-0.01, maximum=0.01)
            # Use broader Z tolerance on part to capture north edge if slightly offset
            fallback = part.edges().filter_by_position(Axis.Z, minimum=-0.5, maximum=0.5)
            # Filter fallback to those near outer loop's Y range to avoid picking interior floor edges
            if fallback:
                bottom = fallback
            elif outer_bottom:
                # As last resort, chamfer will be attempted on outer_bottom's location;
                # but edges must belong to part, so return part unchanged if no part edges found
                return part
            else:
                return part
        except (ValueError, Standard_Failure):
            return part
    # Verify north segment present: outer north Y is at pcb 0 + WALL + CLEAR
    try:
        outer_north = C.pcb_to_case(0, 0)[1] + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
        has_north = any(
            b.bounding_box().max.Y > outer_north - 1.0 and b.bounding_box().min.Y < outer_north + 1.0
            for b in bottom
        )
        if not has_north:
            # North edge missing — broaden Z tolerance to capture it from outer loop
            broad = part.edges().filter_by_position(Axis.Z, minimum=-0.5, maximum=0.5)
            # Keep only edges near Z≈0 and with Y near north or spanning perimeter
            if broad:
                # Prefer broad set that includes north; verify again
                has_north_broad = any(
                    b.bounding_box().max.Y > outer_north - 1.0 for b in broad
                )
                if has_north_broad:
                    bottom = broad
    except (ValueError, Standard_Failure, AttributeError):
        pass
    for length in (C.BOTTOM_CHAMFER, C.BOTTOM_CHAMFER * 0.75):
        try:
            return cast(Part, chamfer(bottom, length=length))
        except (ValueError, Standard_Failure):
            continue
    return part


# ---------------------------------------------------------------------------
# Drafted rim facet (outer-top treatment; replaces the old flat chamfer)
# ---------------------------------------------------------------------------

# End extension of the facet frustum beyond the toe and the rim. Below the toe the
# frustum is then WIDER than the outer band, so the wedge cutter (band − frustum) has
# zero width there and no coincident cap face for OCC to trip on.
_FACET_END_EXT = 0.6


def _rim_facet_frustum(drop: float, run: float, rim_z: float) -> Solid:
    """The 'keep' frustum whose sloped outer wall IS the facet plane.

    A DRAFTED PRISM raised from ONE cross-section — the outer-wall offset taken at
    Z = rim_z − drop − e and drafted inward by atan(run/drop), so it has shed exactly
    ``run`` by the time it reaches the rim.

    Drafting one section is what keeps the facet clean. The previous implementation
    lofted between two independently computed Kind.ARC offsets of the same wire, but
    an outward arc-offset does not preserve edge count: at the perimeter amounts the
    two sections come out 23 vs 24 edges, at the front amounts 23 vs 27. With no 1:1
    vertex correspondence OCC abandons ruled surfaces and approximates the whole band
    with BSpline patches whose rulings skew — that was the source of the creases, the
    wandering facet width and the toe line dipping below Z = rim_z − drop.
    ``LocOpe_DPrism`` instead drafts each prism face in place, so a straight outline
    segment yields an exact PLANE and an arc corner an exact CONE."""
    outer = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    slope = run / drop                       # radial inset per unit Z
    e = _FACET_END_EXT
    z0, z1 = rim_z - drop - e, rim_z + e
    amt0 = outer + slope * e                 # widest section, below the toe
    wire = _rounded_wire()                   # reflex-rounded → facet continuous at the jogs
    with BuildSketch(Plane(origin=(0, 0, z0))) as sk:
        face = make_face(wire)  # type: ignore[arg-type]
        face = offset(face, amount=amt0, kind=Kind.ARC)
    profile = cast(Face, sk.sketch.faces()[0])  # type: ignore[union-attr]
    angle = math.atan(slope)
    # LocOpe_DPrism takes the SLANT height along the drafted wall, not the rise.
    prism = LocOpe_DPrism(profile.wrapped, (z1 - z0) / math.cos(angle), angle)
    return Solid(TopoDS.Solid_s(prism.Shape()))


def _rim_facet_cutter(drop: float, run: float, rim_z: float) -> Part:
    """Wedge ring shaved from the outer-wall top: the full outer prism minus the keep
    frustum. Zero width at the toe (Z = rim_z − drop), ``run`` wide at the rim. Subtracting
    it from the tray slopes the outer-top edge inward — the drafted facet."""
    outer = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    e = _FACET_END_EXT
    band = offset_extruded(outer, rim_z - drop - e, rim_z + e, rounded=True)
    return cast(Part, band - _rim_facet_frustum(drop, run, rim_z))


def _sw_ramp_offset_pt_at_x(off: float, x: float) -> tuple[float, float]:
    """Point (x, y) on the GROWN, straightened SW thumb ramp offset OUTWARD by ``off`` at the given
    case-X. off=outer → the facet toe (outer-face) line; off=outer−RUN → the rim inset line.

    Read off `_outer_poly_pts()`, not the sharp polygon: the ramp the facet actually rides is the
    one SOUTH_WALL_EXTRA has already pushed out, so the crease has to be dropped onto that line."""
    o = _outer_poly_pts()
    a, b = o[2], o[3]                         # SW thumb ramp, grown & straightened
    ex, ey = b[0] - a[0], b[1] - a[1]
    el = math.hypot(ex, ey); ux, uy = ex / el, ey / el
    nx, ny = uy, -ux                          # outward normal (CCW outline)
    p0x, p0y = a[0] + nx * off, a[1] + ny * off
    return x, p0y + uy * (x - p0x) / ux


def _front_slash_crossings(rim_z: float = C.MAIN_RIM_Z) -> tuple[tuple[float, float, float], ...]:
    """Rim & toe of the two front creases in right-half case coords.
      • EAST '\\' — the cap y=FRONT_FACET_Y_MASK crossing ramp E4's offset lines (rim = outer−RUN, toe
        = full outer).
      • WEST '/'  — a DERIVED exact mirror twin of the East: the East's X-run mirrored (rim east of
        toe), dropped onto the GROWN straightened SW ramp's offset lines. Same run/angle as the
        East by construction. It sits centred on the thumb-switch midpoint while it fits there and
        is otherwise CLAMPED east onto the ramp — see the block over the clamp below."""
    pts = _outer_poly_pts()                   # GROWN outline — the wall the facet actually rides
    outer = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    z_rim, z_toe = rim_z, rim_z - C.FRONT_FACET_DROP
    off_rim, off_toe = outer - C.FRONT_FACET_RUN, outer
    # East '\': the cap crossing ramp E4 — index 4 of the grown list (sharp pts[5]→pts[6]).
    a, b = pts[4], pts[5]
    ex, ey = b[0] - a[0], b[1] - a[1]
    el = math.hypot(ex, ey); ux, uy = ex / el, ey / el
    nx, ny = uy, -ux                          # outward normal (CCW outline)

    def _cap_cross(off: float) -> float:
        px, py = a[0] + nx * off, a[1] + ny * off
        return px + ux * (C.FRONT_FACET_Y_MASK - py) / uy

    e_rim_x, e_toe_x = _cap_cross(off_rim), _cap_cross(off_toe)
    # Both crossings must stay ON the E4 segment, east of the flat-front/E4 corner (`a`) by
    # FRONT_CREASE_END_MARGIN. `_cap_cross` solves the infinite LINE, not the bounded edge — push
    # FRONT_FACET_Y_MASK low enough and the "crossing" extrapolates past the corner onto the
    # flat-front's own line, which is not where the real wall bends and would silently mis-mask.
    # Each offset line clears the corner at its OWN offset (the normal has an X component too).
    corner_rim_x, corner_toe_x = a[0] + nx * off_rim, a[0] + nx * off_toe
    assert e_rim_x >= corner_rim_x + C.FRONT_CREASE_END_MARGIN, (
        "East crease rim crossing runs past the flat-front/E4 corner — raise FRONT_FACET_Y_MASK "
        f"(corner at x={corner_rim_x:.2f}, need >= {corner_rim_x + C.FRONT_CREASE_END_MARGIN:.2f})")
    assert e_toe_x >= corner_toe_x + C.FRONT_CREASE_END_MARGIN, (
        "East crease toe crossing runs past the flat-front/E4 corner — raise FRONT_FACET_Y_MASK "
        f"(corner at x={corner_toe_x:.2f}, need >= {corner_toe_x + C.FRONT_CREASE_END_MARGIN:.2f})")
    east_rim = (e_rim_x, C.FRONT_FACET_Y_MASK, z_rim)
    east_toe = (e_toe_x, C.FRONT_FACET_Y_MASK, z_toe)
    # West '/': the East's run, mirrored (rim east of toe → '/'), laid on the thumb ramp.
    #
    # It WANTS to sit centred on the thumb-switch midpoint, and while it fits there it does. But
    # the run is not a free choice — E4 lies 75° off +Y, so every mm of FRONT_FACET_RUN stretches
    # the slash ~3.8 mm in X, and past ~3.25 mm of run a midpoint-centred twin hangs off the west
    # end of the thumb ramp entirely. The mask's west boundary would then cross the west thumb
    # EDGE instead of the ramp and the two creases would stop being twins.
    #
    # So the twin is CLAMPED, never reshaped: the run and the angle are the East's whatever
    # happens, and only the position gives — it slides EAST just far enough to keep
    # FRONT_CREASE_END_MARGIN clear of the ramp's ends, and not one mm further. At the runs that
    # already fitted it does not move at all. Each end is measured against ITS OWN offset line
    # (the toe on the outer face, the rim on the inset line), because those two lines start and
    # end at different X.
    run = abs(e_toe_x - e_rim_x)
    o = _outer_poly_pts()
    a2, b2 = o[2], o[3]                       # grown, straightened thumb ramp
    rx, ry = b2[0] - a2[0], b2[1] - a2[1]
    rnx = ry / math.hypot(rx, ry)             # outward normal's X component (CCW outline)
    m = C.FRONT_CREASE_END_MARGIN
    toe_lo = a2[0] + rnx * off_toe + m        # ramp's outer face starts here
    rim_hi = b2[0] + rnx * off_rim - m        # inset line ends at the flat-front corner
    assert toe_lo <= rim_hi - run, (
        "West crease twin no longer fits on the thumb ramp — lower FRONT_FACET_RUN "
        f"(run {run:.2f} mm needs {rim_hi - toe_lo:.2f} mm of ramp)")
    toe_x = min(max(thumb_switch_midpoint_x() - run / 2, toe_lo), rim_hi - run)
    w_rim = _sw_ramp_offset_pt_at_x(off_rim, toe_x + run)
    w_toe = _sw_ramp_offset_pt_at_x(off_toe, toe_x)
    west_rim = (w_rim[0], w_rim[1], z_rim)
    west_toe = (w_toe[0], w_toe[1], z_toe)
    return east_rim, east_toe, west_rim, west_toe


def _front_facet_mask(rim_z: float = C.MAIN_RIM_Z) -> Part:
    """Plan REGION (extruded prism) selecting where the deep south facet applies.

    Bounded NORTH/EAST by the flat cap y=FRONT_FACET_Y_MASK — whose crossing of ramp E4 is the East
    '\\' slash (kept in place) — and WEST by the plane through the DERIVED West-twin crease endpoints
    on the straightened SW thumb ramp (`_front_slash_crossings`). The West is a rigid mirror copy of
    the East's front-elevation profile (same run/angle), centred at the thumb-switch midpoint, so the
    two read as exact twins; forcing the East's run makes this cut oblique enough to reach the '/'
    lean while staying clear of the flat-front corner. The ramp is straightened in `_outer_poly_pts`.
    Deep = thumb ramp → flat front → E4; thumb tip + side/back walls stay shallow."""
    _e_rim, _e_toe, w_rim, w_toe = _front_slash_crossings(rim_z)
    y_n = C.FRONT_FACET_Y_MASK
    BIG = 220.0
    dx, dy = w_rim[0] - w_toe[0], w_rim[1] - w_toe[1]   # west boundary = plan line through toe→rim

    def _wx(y: float) -> float:
        return w_toe[0] + dx * (y - w_toe[1]) / dy

    z0, z1 = -1.0, rim_z + 2.0
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            with BuildLine():
                Polyline((_wx(-BIG), -BIG), (_wx(y_n), y_n), (BIG, y_n), (BIG, -BIG), close=True)
            make_face()
        extrude(amount=z1 - z0)
    assert bp.part is not None
    return cast(Part, Pos(0, 0, z0) * bp.part)


def _apply_rim_facets(part: Part, rim_z: float) -> Part:
    """Shave the drafted perimeter facet and the deeper south facet (masked to
    the front, between the two mirrored slashes). Strict PCB-frame north wall
    is now fully chamfered like the rest of the perimeter — no MCU bump
    exclusion or wedge facets."""
    perim = _rim_facet_cutter(C.RIM_FACET_DROP, C.RIM_FACET_RUN, rim_z)
    front = cast(Part, _rim_facet_cutter(C.FRONT_FACET_DROP, C.FRONT_FACET_RUN, rim_z)
                 & _front_facet_mask(rim_z))
    return cast(Part, part - perim - front)


# ---------------------------------------------------------------------------
# Drafted bottom "boat" facet — mirrored bottom chamfer leaving a straight
# full-size middle band.
# ---------------------------------------------------------------------------

def _bottom_facet_frustum(drop: float, run: float) -> Solid:
    """Keep frustum for the bottom facet — mirrored version of _rim_facet_frustum.

    Wide at Z=0? Actually NARROW at Z=0 (outer−run) and WIDER at the toe
    Z=drop (exactly outer), so that (band − frustum) is a wedge that is
    ``run`` wide at the bottom face and zero at the toe. Leaves a straight
    full-size middle band between the top and bottom facets.

    The frustum is a drafted prism (LocOpe_DPrism) with the profile taken at
    Z=−e and drafted outward (negative angle) so it grows by ``slope`` per mm
    of rise.
    """
    outer = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    slope = run / drop
    e = _FACET_END_EXT
    z0, z1 = -e, drop + e
    # Narrowest section below the bottom, grows to outer+ slope*e above toe.
    amt0 = outer - run - slope * e
    wire = _rounded_wire()
    with BuildSketch(Plane(origin=(0, 0, z0))) as sk:
        face = make_face(wire)  # type: ignore[arg-type]
        face = offset(face, amount=amt0, kind=Kind.ARC)
    profile = cast(Face, sk.sketch.faces()[0])  # type: ignore[union-attr]
    angle = -math.atan(slope)  # negative = expand outward with height
    prism = LocOpe_DPrism(profile.wrapped, (z1 - z0) / math.cos(angle), angle)
    return Solid(TopoDS.Solid_s(prism.Shape()))


def _bottom_facet_cutter(drop: float, run: float) -> Part:
    """Wedge ring shaved from the outer-bottom edge: band minus keep frustum.

    Band is the full outer prism from −e to drop+e; keep frustum is narrow at
    Z=0 (outer−run) and exactly outer at Z=drop. Subtraction is therefore
    ``run`` wide at Z=0 and zero at the toe.
    """
    outer = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    e = _FACET_END_EXT
    band = offset_extruded(outer, -e, drop + e, rounded=True)
    return cast(Part, band - _bottom_facet_frustum(drop, run))


def _apply_bottom_facets(part: Part) -> Part:
    """Shave the drafted bottom perimeter facet and the deeper south bottom
    facet (masked to the front, between the two mirrored slashes).

    Mirrors _apply_rim_facets: shallow 2×4 everywhere, deep 6×4 at the south
    front inside the same FRONT_FACET_Y_MASK region (including the
    SOUTH_WALL_EXTRA growth via _rounded_wire / _front_facet_mask).
    """
    perim = _bottom_facet_cutter(C.BOTTOM_FACET_DROP, C.BOTTOM_FACET_RUN)
    # Reuse the same south mask as the top (Y_MASK=22) — it covers the bottom
    # Z range as well (prism from −1 to rim_z+2).
    front = cast(Part, _bottom_facet_cutter(C.FRONT_BOTTOM_DROP, C.FRONT_BOTTOM_RUN)
                 & _front_facet_mask())
    return cast(Part, part - perim - front)


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

def build_tray(rim_z: float = C.MAIN_RIM_Z, bottom_chamfer: bool = True) -> Part:
    """Outer shell + inner cavity, walls flat at ``rim_z``.

    ``rim_z`` defaults to ``MAIN_RIM_Z`` (flush with the switch plate); the outer facet,
    +Y relief and slide-switch access all track the rim automatically."""
    shell  = _outer_shell(rim_z)
    cavity = _cavity_solid(rim_z)
    hollow = cast(Part, shell - cavity)
    faceted = _apply_rim_facets(hollow, rim_z)
    bottom_faceted = _apply_bottom_facets(faceted)
    # A caller may disable the bottom counter-chamfer for another print orientation. The
    # monolithic CLI keeps the default flat underside. Must run AFTER bottom facets so
    # the tiny 0.5 mm relief applies to the new Z=0 bottom edge.
    chamfered = _chamfer_bottom_edges(bottom_faceted) if bottom_chamfer else bottom_faceted
    if isinstance(chamfered, Part):
        return chamfered
    solids = chamfered.solids()
    return Part(children=list(solids)) if solids else Part(children=[chamfered])


# %%
if __name__ == "__main__":
    from ocp_vscode import show

    from sofle_case.tray import build_tray
    show(build_tray())
