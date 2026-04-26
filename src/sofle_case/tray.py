"""Outer shell + inner cavity (PCB polygon offset by PCB_XY_CLEARANCE) + top chamfer."""
from __future__ import annotations
from build123d import (
    Part, Pos, RectangleRounded, Polyline, make_face, extrude, offset, Kind,
    Plane, BuildPart, BuildSketch, BuildLine, Locations, Axis, chamfer,
)
from . import constants as C
from .pcb_geometry import polygon_in_case_coords


def _outer_shell() -> Part:
    """Solid rounded-rect prism in case coords; lower-left at (0,0,0)."""
    with BuildPart() as bp:
        with BuildSketch(Plane.XY.offset(0)):
            with Locations((C.OUTER_WIDTH / 2, C.OUTER_DEPTH / 2)):
                RectangleRounded(C.OUTER_WIDTH, C.OUTER_DEPTH, C.CORNER_RADIUS)
        extrude(amount=C.MAIN_RIM_Z)
    return bp.part


def _cavity_solid() -> Part:
    """PCB polygon offset by +PCB_XY_CLEARANCE, extruded from floor to over-rim."""
    poly = polygon_in_case_coords()
    # Drop closing duplicate for Polyline.
    pts = poly[:-1] if poly[0] == poly[-1] else poly

    # Polyline must be built inside BuildLine, then used as a wire for make_face.
    with BuildLine() as bl:
        Polyline(*pts, close=True)
    wire = bl.line

    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            face = make_face(wire)
            face = offset(face, amount=C.PCB_XY_CLEARANCE, kind=Kind.INTERSECTION)
        extrude(amount=C.MAIN_RIM_Z + 1.0)
    # Translate so the cavity starts at Z=FLOOR_THICKNESS (extrude went up from Z=0).
    return Pos(0, 0, C.FLOOR_THICKNESS) * bp.part


def _chamfer_top_edges(part: Part) -> Part:
    """Chamfer only the outer top edges (Z == MAIN_RIM_Z) by TOP_CHAMFER."""
    top_edges = part.edges().filter_by_position(
        Axis.Z, minimum=C.MAIN_RIM_Z - 0.001, maximum=C.MAIN_RIM_Z + 0.001
    )
    if not top_edges:
        return part
    return chamfer(top_edges, length=C.TOP_CHAMFER)


def build_tray() -> Part:
    shell = _outer_shell()
    cavity = _cavity_solid()
    hollow = shell - cavity
    return _chamfer_top_edges(hollow)
