"""Outer shell + inner cavity (PCB polygon offset by PCB_XY_CLEARANCE) + top fillet."""
from __future__ import annotations
from typing import cast
from build123d import (
    Part, Wire, Pos, Polyline, make_face, extrude, offset, Kind,
    Plane, BuildPart, BuildSketch, BuildLine, Axis, fillet, Line, Spline,
)
from . import constants as C
from .pcb_geometry import polygon_in_case_coords


def _outer_shell() -> Part:
    """PCB polygon offset outward by (WALL_THICKNESS + PCB_XY_CLEARANCE) with ARC corners."""
    poly = polygon_in_case_coords()
    pts = poly[:-1] if poly[0] == poly[-1] else poly
    with BuildLine() as bl:
        Polyline(*pts, close=True)
    assert bl.line is not None
    wire = cast(Wire, bl.line)
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            face = make_face(wire)  # type: ignore[arg-type]
            face = offset(face, amount=C.WALL_THICKNESS + C.PCB_XY_CLEARANCE, kind=Kind.ARC)
        extrude(amount=C.MAIN_RIM_Z)
    assert bp.part is not None
    return bp.part


def _cavity_solid() -> Part:
    """PCB polygon offset by +PCB_XY_CLEARANCE, extruded from floor to over-rim."""
    poly = polygon_in_case_coords()
    # Drop closing duplicate for Polyline.
    pts = poly[:-1] if poly[0] == poly[-1] else poly

    # Polyline must be built inside BuildLine, then used as a wire for make_face.
    with BuildLine() as bl:
        Polyline(*pts, close=True)
    assert bl.line is not None
    wire = cast(Wire, bl.line)

    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            face = make_face(wire)  # type: ignore[arg-type]
            face = offset(face, amount=C.PCB_XY_CLEARANCE, kind=Kind.INTERSECTION)
        extrude(amount=C.MAIN_RIM_Z + 0.01)
    assert bp.part is not None
    # Translate so the cavity starts at Z=FLOOR_THICKNESS (extrude went up from Z=0).
    return cast(Part, Pos(0, 0, C.FLOOR_THICKNESS) * bp.part)


def _fillet_top_edges(part: Part) -> Part:
    """Fillet all top edges (Z == MAIN_RIM_Z) by TOP_CHAMFER radius."""
    top_edges = part.edges().filter_by_position(
        Axis.Z, minimum=C.MAIN_RIM_Z - 0.001, maximum=C.MAIN_RIM_Z + 0.001
    )
    if not top_edges:
        return part
    return cast(Part, fillet(top_edges, radius=C.TOP_CHAMFER))


def _mcu_wall_cap() -> Part:
    """Plateau cap above MAIN_RIM_Z on the −X wall, covering the MCU region.

    Profile (Y-Z plane, clockwise):
      bottom : flat at MAIN_RIM_Z  from y_low → y_end
      +Y side: vertical rise at y_end  MAIN_RIM_Z → MCU_HILL_Z
      top    : flat at MCU_HILL_Z  from y_end → y_mcu_bot
      descent: spline from (y_mcu_bot, MCU_HILL_Z) → (y_low, MAIN_RIM_Z)
    Extruded in +X across the −X outer wall thickness.
    """
    _, sw_cy  = C.pcb_to_case(*C.SW_SLIDE_POS)
    _, mcu_cy = C.pcb_to_case(*C.MCU_POS)

    mcu_half_l = C.MCU_BODY_L / 2
    y_mcu_bot  = mcu_cy - mcu_half_l                    # MCU −Y body edge ≈ 80.8 mm
    y_low      = sw_cy                                   # descent lands at switch centre Y
    y_end      = C.OUTER_DEPTH - C.WALL_THICKNESS        # flush with +Y inner wall face

    x_pcb_left = C.PCB_X_MIN + C.PCB_OFFSET_X           # left PCB edge in case coords = 3.0 mm
    x_outer    = x_pcb_left - C.WALL_THICKNESS - C.PCB_XY_CLEARANCE   # ≈ 0.0 mm
    x_inner    = x_pcb_left + C.PCB_XY_CLEARANCE                      # ≈ 3.5 mm
    cap_depth  = x_inner - x_outer

    with BuildPart() as bp:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                # Full-height profile from Z=0 so the cap has genuine volume
                # overlap with the hollow wall — ensures OCC fuse produces one solid.
                Line((y_low,     0),              (y_end,     0))
                Line((y_end,     0),              (y_end,     C.MCU_HILL_Z))
                Line((y_end,     C.MCU_HILL_Z),   (y_mcu_bot, C.MCU_HILL_Z))
                Spline(
                    (y_mcu_bot, C.MCU_HILL_Z),
                    (y_low,     C.MAIN_RIM_Z),
                    tangents=[(-1, 0), (-1, 0)],
                    tangent_scalars=list(C.MCU_HILL_DESCENT_SCALARS),
                )
                Line((y_low,     C.MAIN_RIM_Z),   (y_low,     0))
            make_face()
        extrude(amount=cap_depth)

    assert bp.part is not None
    return cast(Part, Pos(x_outer, 0, 0) * bp.part)


def build_tray() -> Part:
    shell = _outer_shell()
    cavity = _cavity_solid()
    hollow = cast(Part, shell - cavity)
    hollow = cast(Part, hollow + _mcu_wall_cap())
    return _fillet_top_edges(hollow)


# %%
if __name__ == "__main__":
    from ocp_vscode import show
    from sofle_case.tray import build_tray
    show(build_tray())
