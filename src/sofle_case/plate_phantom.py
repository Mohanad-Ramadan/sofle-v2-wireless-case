"""Switch plate phantom for visual fit-check in the OCP viewer.

Select it with ``scripts/build.py --phantoms``.
"""
from __future__ import annotations

from typing import cast

from build123d import (
    BuildLine,
    BuildPart,
    BuildSketch,
    Cylinder,
    Locations,
    Part,
    Plane,
    Polyline,
    Pos,
    Wire,
    extrude,
    make_face,
)

from . import constants as C
from .plate_geometry import load_plate_cutouts, plate_fit_cutter


def _plate_body() -> Part:
    """Plate polygon extruded from PLATE_SEAT_Z to PLATE_TOP_Z, mounting holes subtracted."""
    plate = plate_fit_cutter()
    for hx, hy in C.MOUNTING_HOLES:
        cx, cy = C.pcb_to_case(hx, hy)
        with BuildPart() as hole, Locations((cx, cy, C.PLATE_SEAT_Z + C.PLATE_THICKNESS / 2)):
            Cylinder(C.PCB_HOLE_DIA / 2, C.PLATE_THICKNESS + 0.1)
        plate = cast(Part, plate - hole.part)
    return plate


def _switch_cutout_solid(case_pts: list[tuple[float, float]]) -> Part:
    with BuildLine() as bl:
        Polyline(*case_pts, close=True)
    wire = cast(Wire, bl.line)
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            make_face(wire)  # type: ignore[arg-type]
        extrude(amount=C.PLATE_THICKNESS + 0.2)
    assert bp.part is not None
    return cast(Part, Pos(0, 0, C.PLATE_SEAT_Z - 0.1) * bp.part)


def build_plate_phantom() -> Part:
    """Switch plate body with switch cutouts and mounting holes removed."""
    plate = _plate_body()

    cutout_solids: list[Part] = []
    for cutout_pcb in load_plate_cutouts():
        case_pts = [C.pcb_to_case(x, y) for x, y in cutout_pcb]
        pts = case_pts[:-1] if case_pts[0] == case_pts[-1] else case_pts
        if len(pts) < 3:
            continue
        cutout_solids.append(_switch_cutout_solid(pts))

    result = plate
    for cut in cutout_solids:
        result = result - cut  # type: ignore[assignment]

    if not isinstance(result, Part):
        result = Part(children=[result])
    return result


if __name__ == "__main__":
    from ocp_vscode import show
    show(build_plate_phantom(), names=["plate_phantom"])
