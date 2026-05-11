"""Outer shell + inner cavity + integrated MCU hill (−X and +Y walls)."""
from __future__ import annotations
from typing import cast
from build123d import (
    Part, Wire, Pos, Polyline, make_face, extrude, offset, Kind, Solid,
    Plane, BuildPart, BuildSketch, BuildLine, Axis, fillet, Line, Spline,
)
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
    return _inner_extruded(C.FLOOR_THICKNESS, C.MCU_HILL_Z + 0.01)


# ---------------------------------------------------------------------------
# MCU hill — wall-ring extension over the −X / +Y corner above MCU
# ---------------------------------------------------------------------------

def _axis_box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Part:
    """Axis-aligned box from (x0,y0,z0) to (x1,y1,z1)."""
    return cast(Part, Solid.make_box(x1 - x0, y1 - y0, z1 - z0).translate((x0, y0, z0)))


def _hill_discard_outside_L() -> Part:
    """Three boxes covering everything outside the MCU L-corner over hill Z range.
    Subtracted from the full hill ring to keep only the −X-above-slide-switch
    strip and the +Y-up-to-MCU-east strip. South bound sits at the slide-switch
    slot's +Y flare endpoint so the hill ring meets the slot top with no sliver."""
    sw_cy = C.pcb_to_case(*C.SW_SLIDE_POS)[1]
    hill_y_start = sw_cy + C.SLIDE_SWITCH_TOP_W / 2     # slot's +Y flare top corner Y
    inner_x = C.MCU_HILL_NEG_X_INNER_BOUND_X
    inner_y = C.MCU_HILL_PLUS_Y_INNER_BOUND_Y
    plus_y_x_end = C.MCU_HILL_PLUS_Y_REACH_X + C.MCU_HILL_PLUS_Y_RAMP_RUN
    bx_min, bx_max = -1.0, C.OUTER_WIDTH + 1.0
    by_min, by_max = -1.0, C.OUTER_DEPTH + 1.0
    z_lo, z_hi = C.MAIN_RIM_Z, C.MCU_HILL_Z + 0.01

    south  = _axis_box(bx_min,         bx_max, by_min,       hill_y_start, z_lo, z_hi)
    middle = _axis_box(inner_x,        bx_max, hill_y_start, inner_y,      z_lo, z_hi)
    top_e  = _axis_box(plus_y_x_end,   bx_max, inner_y,      by_max,       z_lo, z_hi)
    return cast(Part, south + middle + top_e)


def _neg_x_descent_cutter() -> Part:
    """Region ABOVE the −X wall descent spline (YZ profile). Spline starts at
    (sw_cy + SLIDE_SWITCH_TOP_W/2, MAIN_RIM_Z) — just past the slide-switch slot's
    +Y flare end — so hill ring grows seamlessly from the rim with no Z step."""
    sw_cy  = C.pcb_to_case(*C.SW_SLIDE_POS)[1]
    mcu_cy = C.pcb_to_case(*C.MCU_POS)[1]
    y_low      = sw_cy + C.SLIDE_SWITCH_TOP_W / 2
    y_mcu_bot  = mcu_cy - C.MCU_BODY_L / 2
    z_top      = C.MCU_HILL_Z + 5.0
    y_safety   = 5.0

    with BuildPart() as bp:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                Spline(
                    (y_low,     C.MAIN_RIM_Z),
                    (y_mcu_bot, C.MCU_HILL_Z),
                    tangents=[(1, 0), (1, 0)],
                    tangent_scalars=list(C.MCU_HILL_DESCENT_SCALARS),
                )
                Line((y_mcu_bot,        C.MCU_HILL_Z), (y_mcu_bot,        z_top))
                Line((y_mcu_bot,        z_top),        (y_low - y_safety, z_top))
                Line((y_low - y_safety, z_top),        (y_low - y_safety, C.MAIN_RIM_Z))
                Line((y_low - y_safety, C.MAIN_RIM_Z), (y_low,             C.MAIN_RIM_Z))
            make_face()
        # Plane.YZ extrudes in +X. Span enough X to cover the −X wall ring with margin.
        extrude(amount=C.MCU_HILL_NEG_X_INNER_BOUND_X + 2.0)
    assert bp.part is not None
    return cast(Part, Pos(-1.0, 0, 0) * bp.part)


def _plus_y_descent_cutter() -> Part:
    """Region ABOVE the +Y wall linear ramp (XZ profile). Subtract to sculpt
    the descent from MCU_HILL_Z down to MAIN_RIM_Z east of the MCU footprint."""
    x_mcu_right = C.MCU_HILL_PLUS_Y_REACH_X
    x_ramp_end  = x_mcu_right + C.MCU_HILL_PLUS_Y_RAMP_RUN
    z_top       = C.MCU_HILL_Z + 5.0
    x_safety    = 5.0
    y_thickness = 6.0   # covers wall Y ∈ [INNER_Y_BOUND, INNER_Y_BOUND + 6]

    with BuildPart() as bp:
        with BuildSketch(Plane.XZ):
            with BuildLine():
                Line((x_mcu_right,            C.MCU_HILL_Z), (x_ramp_end,            C.MAIN_RIM_Z))
                Line((x_ramp_end,             C.MAIN_RIM_Z), (x_ramp_end + x_safety, C.MAIN_RIM_Z))
                Line((x_ramp_end + x_safety,  C.MAIN_RIM_Z), (x_ramp_end + x_safety, z_top))
                Line((x_ramp_end + x_safety,  z_top),        (x_mcu_right,           z_top))
                Line((x_mcu_right,            z_top),        (x_mcu_right,           C.MCU_HILL_Z))
            make_face()
        extrude(amount=y_thickness)
    assert bp.part is not None
    # Plane.XZ extrudes in −Y; translate so cutter covers Y ∈ [inner_y_bound, inner_y_bound+thickness].
    return cast(Part, Pos(0, C.MCU_HILL_PLUS_Y_INNER_BOUND_Y + y_thickness, 0) * bp.part)


def _mcu_hill_solid() -> Part:
    """Hill = wall ring extruded from MAIN_RIM_Z to MCU_HILL_Z, restricted to the
    L-corner over MCU, with descent cutters sculpting both top transitions.

    Outer face is the polygon-offset shell face; inner face is the cavity face.
    Both faces are shared with the rest of the case → boolean union with the
    shell produces a single continuous solid (no floating slab)."""
    z_lo, z_hi = C.MAIN_RIM_Z, C.MCU_HILL_Z

    outer = _outer_extruded(z_lo, z_hi)
    inner = _inner_extruded(z_lo, z_hi)
    ring = cast(Part, outer - inner)

    ring = cast(Part, ring - _hill_discard_outside_L())
    ring = cast(Part, ring - _neg_x_descent_cutter())
    ring = cast(Part, ring - _plus_y_descent_cutter())
    return ring


# ---------------------------------------------------------------------------
# Top fillet
# ---------------------------------------------------------------------------

def _fillet_top_edges(part: Part) -> Part:
    """Fillet outer top edges (MAIN_RIM_Z through MCU_HILL_Z) by TOP_CHAMFER radius."""
    top_edges = part.edges().filter_by_position(
        Axis.Z, minimum=C.MAIN_RIM_Z - 0.5, maximum=C.MCU_HILL_Z + 0.5
    )
    if not top_edges:
        return part
    try:
        return cast(Part, fillet(top_edges, radius=C.TOP_CHAMFER))
    except ValueError:
        return part


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

def build_tray() -> Part:
    shell  = _outer_shell()
    cavity = _cavity_solid()
    hill   = _mcu_hill_solid()
    hollow = cast(Part, (shell + hill) - cavity)
    filleted = _fillet_top_edges(hollow)
    if isinstance(filleted, Part):
        return filleted
    solids = filleted.solids()
    return Part(children=list(solids)) if solids else Part(children=[filleted])


# %%
if __name__ == "__main__":
    from ocp_vscode import show
    from sofle_case.tray import build_tray
    show(build_tray())
