"""Outer shell + inner cavity, all walls flat at MAIN_RIM_Z (flush with the
switch plate). The MCU corner is a plain flat wall — no hill; the nice!nano and
its USB-C jack sit open above the rim. The slide-switch S-curve valley on the −X
wall and the +Y wall's B+/B- relief bump are the only local wall features."""
from __future__ import annotations
from typing import cast
from build123d import (
    Part, Wire, Pos, Polyline, make_face, extrude, offset, Kind, Solid,
    Plane, BuildPart, BuildSketch, BuildLine, Axis, fillet, chamfer, Line, Spline,
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


def _outer_extruded(z_lo: float, z_hi: float) -> Part:
    """PCB polygon offset OUTWARD by (WALL_THICKNESS + PCB_XY_CLEARANCE), Kind.ARC,
    extruded from z_lo to z_hi."""
    wire = _polygon_wire()
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            face = make_face(wire)  # type: ignore[arg-type]
            face = offset(face, amount=C.WALL_THICKNESS + C.PCB_XY_CLEARANCE, kind=Kind.ARC)
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

def _outer_shell() -> Part:
    return _outer_extruded(0.0, C.MAIN_RIM_Z)


def _cavity_solid() -> Part:
    return _inner_extruded(C.FLOOR_THICKNESS, C.MAIN_RIM_Z + 0.01)


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


def _mcu_y_relief_bump() -> Part:
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
    return _axis_box(x_lo, x_full_hi, y_lo, y_new_outer, 0.0, C.MAIN_RIM_Z)


def _mcu_y_relief_widen() -> Part:
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
    is no gap between the two cuts."""
    _, x_full_hi = _mcu_y_relief_x_range()
    inner_x     = C.pcb_to_case(0, 0)[0] - C.PCB_XY_CLEARANCE          # −X inner wall face
    corner_y    = C.pcb_to_case(0, 0)[1]                              # polygon vertex Y; −X wall face ends here
    y_new_inner = C.pcb_to_case(0, C.MCU_Y_RELIEF_TARGET_Y)[1] + C.PCB_XY_CLEARANCE
    _, y_safe_lo = C.pcb_to_case(0, C.MCU_POS[1])                      # safely inside cavity
    z_hi = C.MAIN_RIM_Z + 0.01                                        # walls are flat at the rim
    base   = _axis_box(inner_x + 0.3, x_full_hi, y_safe_lo, y_new_inner, C.FLOOR_THICKNESS, z_hi)
    corner = _axis_box(inner_x, inner_x + 0.35, corner_y, y_new_inner, C.FLOOR_THICKNESS, z_hi)
    return cast(Part, base + corner)


def _neg_x_wall_cutter_plus_y() -> Part:
    sw_cy  = C.pcb_to_case(*C.SW_SLIDE_POS)[1]
    mcu_cy = C.pcb_to_case(*C.MCU_POS)[1]
    hn     = C.SLIDE_SWITCH_W / 2
    z_lo   = C.SLIDE_SWITCH_Z_RANGE[0]
    z_bot  = z_lo - hn
    z_plat = C.MCU_HILL_Z + 0.01
    z_top  = z_plat + 5.0
    y_mcu  = mcu_cy - C.MCU_BODY_L / 2
    y_far  = C.OUTER_DEPTH + 5.0
    with BuildPart() as bp:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                Line((sw_cy, z_top), (sw_cy, z_bot))
                Spline(
                    (sw_cy, z_bot),
                    (y_mcu, z_plat),
                    tangents=[(1, 0), (1, 0)],
                    tangent_scalars=list(C.S_CURVE_RAMP_PLUS_Y_SCALARS),
                )
                Line((y_mcu, z_plat), (y_far, z_plat))
                Line((y_far, z_plat), (y_far, z_top))
                Line((y_far, z_top), (sw_cy, z_top))
            make_face()
        extrude(amount=C.MCU_HILL_NEG_X_INNER_BOUND_X + 2.0)
    assert bp.part is not None
    return cast(Part, Pos(-1.0, 0, 0) * bp.part)


def _neg_x_wall_cutter_minus_y() -> Part:
    sw_cy  = C.pcb_to_case(*C.SW_SLIDE_POS)[1]
    hn     = C.SLIDE_SWITCH_W / 2
    z_lo   = C.SLIDE_SWITCH_Z_RANGE[0]
    z_bot  = z_lo - hn
    z_rim  = C.MAIN_RIM_Z + 0.01
    z_top  = C.MCU_HILL_Z + 5.01
    y_ramp = C.S_CURVE_RAMP_Y_START
    y_far  = -5.0

    with BuildPart() as bp:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                Line((sw_cy, z_top), (y_far, z_top))
                Line((y_far, z_top), (y_far, z_rim))
                Line((y_far, z_rim), (y_ramp, z_rim))
                Spline(
                    (y_ramp, z_rim),
                    (sw_cy, z_bot),
                    tangents=[(1, 0), (1, 0)],
                    tangent_scalars=list(C.S_CURVE_RAMP_MINUS_Y_SCALARS),
                )
                Line((sw_cy, z_bot), (sw_cy, z_top))
            make_face()
        extrude(amount=C.MCU_HILL_NEG_X_INNER_BOUND_X + 2.0)
    assert bp.part is not None
    return cast(Part, Pos(-1.0, 0, 0) * bp.part)


# ---------------------------------------------------------------------------
# Outer concave corner fillets
# ---------------------------------------------------------------------------

def _fillet_outer_concave_corners(part: Part) -> Part:
    """Fillet sharp V-notches left by Kind.ARC offset at concave polygon vertices.
    Per-corner try/except so one failure doesn't abort the rest."""
    targets: list[tuple[float, float, float, float, float]] = [
        ( 6.0, 33.0,  9.0, 35.5, 0.5),   # [0] (9, 31.5)   — nearly-flat, tiny notch
        (34.5,  9.0, 37.5, 11.5, 0.8),   # [3] (34.5, 13)  — ~5° turn, short segments
        (51.5, 16.5, 54.0, 19.5, 2.0),   # [4] (52, 21)    — ~24° turn
        (107.5,16.5,110.5, 19.5, 2.0),   # [5] (108.5, 21) — convex; try, may be no-op
    ]
    for xlo, ylo, xhi, yhi, r in targets:
        z_edges = [
            e for e in (
                part.edges()
                .filter_by_position(Axis.X, minimum=xlo, maximum=xhi)
                .filter_by_position(Axis.Y, minimum=ylo, maximum=yhi)
            )
            if (abs(e.tangent_at(0.5).X) < 0.01
                and abs(e.tangent_at(0.5).Y) < 0.01
                and e.bounding_box().min.Z < 0.01)   # outer face: starts at Z≈0
        ]
        if not z_edges:
            continue
        try:
            part = cast(Part, fillet(z_edges, radius=r))
        except (ValueError, Standard_Failure):
            pass
    return part


# ---------------------------------------------------------------------------
# Top fillet
# ---------------------------------------------------------------------------

def _fillet_top_edges(part: Part) -> Part:
    """Fillet the slide-switch S-curve valley's top edges on the −X wall.

    The flat perimeter rim is intentionally left SHARP so the wall top sits flush
    with the switch plate (MAIN_RIM_Z == PLATE_TOP_Z) — a bevel there would read
    as a rounded lip standing off the plate. Only the slide-switch valley (which
    dips below the rim for finger access) gets its spline edges softened."""
    r = C.TOP_CHAMFER

    # Slide-switch S-curve ramp spline edges on −X wall (outer + inner faces, ±Y)
    ramp = [
        e for e in part.edges()
        if (bb := e.bounding_box()).max.X <= C.MCU_HILL_NEG_X_INNER_BOUND_X
        and bb.max.Z - bb.min.Z > 5.0
        and bb.max.Y - bb.min.Y > 5.0
    ]
    if ramp:
        try:
            part = cast(Part, fillet(ramp, radius=r))
        except (ValueError, Standard_Failure):
            pass

    return part


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
    chamfer, rather than aborting the build (mirrors _fillet_top_edges)."""
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
# Outer-top chamfer (thick-wall ledge descends outward to the ground)
# ---------------------------------------------------------------------------

def _chamfer_outer_top_edges(part: Part) -> Part:
    """Bevel the OUTER top perimeter (45°) so the thick wall's top edge descends
    toward the ground instead of reading as a hard block. The inner cavity rim is
    left sharp (flush with the switch plate) — only edges on the outer boundary
    are selected.

    Outer vs inner rim is told apart by a radial membership probe: at an outer
    edge, material lies inward (into the wall) and air lies outward; at the inner
    rim it is the reverse. The slide-switch valley top edges sit below the rim, so
    the rim-Z filter skips them automatically. Size fallback + try/except mirror
    the other top-edge passes so an OCC failure never aborts the whole bevel."""
    rim = C.MAIN_RIM_Z
    cx, cy = C.OUTER_WIDTH / 2, C.OUTER_DEPTH / 2

    def _solid(x: float, y: float, z: float) -> bool:
        probe = Solid.make_box(0.4, 0.4, 0.4).translate((x - 0.2, y - 0.2, z - 0.2))
        return cast(float, (part & probe).volume) > 1e-6

    outer = []
    for e in part.edges():
        bb = e.bounding_box()
        if bb.max.Z - bb.min.Z > 0.05:                 # horizontal edges only
            continue
        if not (rim - 0.1 <= bb.min.Z <= rim + 0.1):   # at the flat rim
            continue
        m = e.position_at(0.5)
        dx, dy = m.X - cx, m.Y - cy
        n = (dx * dx + dy * dy) ** 0.5
        if n < 1e-6:
            continue
        ux, uy = dx / n, dy / n
        if _solid(m.X - ux * 0.6, m.Y - uy * 0.6, rim - 0.6) and not _solid(
                m.X + ux * 0.6, m.Y + uy * 0.6, rim - 0.6):
            outer.append(e)
    if not outer:
        return part

    for length in (C.OUTER_TOP_CHAMFER, C.OUTER_TOP_CHAMFER * 0.75, C.OUTER_TOP_CHAMFER * 0.5):
        try:
            return cast(Part, chamfer(outer, length=length))
        except (ValueError, Standard_Failure):
            continue
    return part


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

def build_tray() -> Part:
    shell  = _outer_shell()
    cavity = _cavity_solid()
    hollow = cast(Part, shell - cavity)
    hollow = cast(Part, hollow + _mcu_y_relief_bump())
    hollow = cast(Part, hollow - _mcu_y_relief_widen())
    hollow = cast(Part, hollow - _neg_x_wall_cutter_plus_y())
    hollow = cast(Part, hollow - _neg_x_wall_cutter_minus_y())
    hollow = _fillet_outer_concave_corners(hollow)
    hollow = _fillet_bump_neg_x_corner(hollow)
    filleted = _fillet_top_edges(hollow)
    filleted = _chamfer_outer_top_edges(filleted)
    chamfered = _chamfer_bottom_edges(filleted)
    if isinstance(chamfered, Part):
        return chamfered
    solids = chamfered.solids()
    return Part(children=list(solids)) if solids else Part(children=[chamfered])


# %%
if __name__ == "__main__":
    from ocp_vscode import show
    from sofle_case.tray import build_tray
    show(build_tray())
