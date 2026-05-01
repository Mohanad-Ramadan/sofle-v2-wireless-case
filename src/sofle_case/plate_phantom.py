"""Switch plate phantom for visual fit-check in the OCP viewer. Gate with SHOW_PLATE_PHANTOM."""
from __future__ import annotations
import json
from pathlib import Path
from typing import cast

from build123d import (
    Part, Wire, Pos, Polyline, make_face, extrude,
    Plane, BuildPart, BuildSketch, BuildLine, Locations,
    Cylinder, Mode,
)
from . import constants as C

_DATA = Path(__file__).resolve().parents[2] / "data"


def _load_plate_polygon() -> list[tuple[float, float]]:
    raw = json.loads((_DATA / "plate_outline.json").read_text())
    return [tuple(p) for p in raw]  # type: ignore[return-value]


def _load_plate_cutouts() -> list[list[tuple[float, float]]]:
    raw = json.loads((_DATA / "plate_cutouts.json").read_text())
    return [[tuple(p) for p in cut] for cut in raw]  # type: ignore[return-value]


def _plate_body() -> Part:
    """Plate polygon extruded from PLATE_SEAT_Z to PLATE_TOP_Z, mounting holes subtracted."""
    poly = [C.pcb_to_case(x, y) for x, y in _load_plate_polygon()]
    pts = poly[:-1] if poly[0] == poly[-1] else poly

    with BuildLine() as bl:
        Polyline(*pts, close=True)
    wire = cast(Wire, bl.line)

    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            make_face(wire)  # type: ignore[arg-type]
        extrude(amount=C.PLATE_THICKNESS)
        for hx, hy in C.MOUNTING_HOLES:
            cx, cy = C.pcb_to_case(hx, hy)
            with Locations((cx, cy, C.PLATE_THICKNESS / 2)):
                Cylinder(
                    radius=C.PCB_HOLE_DIA / 2,
                    height=C.PLATE_THICKNESS + 0.1,
                    mode=Mode.SUBTRACT,
                )

    assert bp.part is not None
    return cast(Part, Pos(0, 0, C.PLATE_SEAT_Z) * bp.part)


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
    for cutout_pcb in _load_plate_cutouts():
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
    show(build_plate_phantom(), name="plate_phantom")
