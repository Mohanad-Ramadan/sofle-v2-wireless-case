"""Top cover — the sandwich lid.

A thin (``COVER_THICKNESS``) layer the shape of the switch plate, sitting on the
plate top (Z = ``MAIN_RIM_Z``) and held by the same standoffs via taller M2
screws. Each 14 mm plate cutout is grown by ``COVER_WINDOW_OFFSET`` to a ~16.5 mm
window so the switch's 15.6 mm top housing pokes through and the cover seats flat
on the plate; keycaps float above and never touch it. The plate outline's own
inner notch leaves the MCU/OLED/slide/JST bay open for free.

Geometry is driven by the same authoritative plate data the plate phantom uses
(``data/plate_outline.json`` + ``data/plate_cutouts.json``, re-parsed from the
original Sofle v2 top-plate gerber)."""
from __future__ import annotations
import json
from pathlib import Path
from typing import cast

from build123d import (
    Part, Wire, Pos, Polyline, make_face, extrude, offset, Kind,
    Plane, BuildPart, BuildSketch, BuildLine, Locations, Cylinder,
)
from . import constants as C

_DATA = Path(__file__).resolve().parents[2] / "data"


def _load_plate_polygon() -> list[tuple[float, float]]:
    return [tuple(p) for p in json.loads((_DATA / "plate_outline.json").read_text())]  # type: ignore[misc]


def _load_plate_cutouts() -> list[list[tuple[float, float]]]:
    raw = json.loads((_DATA / "plate_cutouts.json").read_text())
    return [[tuple(p) for p in cut] for cut in raw]  # type: ignore[return-value]


def _cover_body() -> Part:
    """Plate-outline polygon extruded up from the plate top by COVER_THICKNESS."""
    poly = [C.pcb_to_case(x, y) for x, y in _load_plate_polygon()]
    pts = poly[:-1] if poly[0] == poly[-1] else poly
    with BuildLine() as bl:
        Polyline(*pts, close=True)
    wire = cast(Wire, bl.line)
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            make_face(wire)  # type: ignore[arg-type]
        extrude(amount=C.COVER_THICKNESS)
    assert bp.part is not None
    return cast(Part, Pos(0, 0, C.MAIN_RIM_Z) * bp.part)


def _window_solid(case_pts: list[tuple[float, float]]) -> Part:
    """A single switch window: the plate cutout grown outward by COVER_WINDOW_OFFSET,
    extruded through the full cover thickness (with a small over-cut top and bottom)."""
    pts = case_pts[:-1] if case_pts[0] == case_pts[-1] else case_pts
    with BuildLine() as bl:
        Polyline(*pts, close=True)
    wire = cast(Wire, bl.line)
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            face = make_face(wire)  # type: ignore[arg-type]
            face = offset(face, amount=C.COVER_WINDOW_OFFSET, kind=Kind.ARC)
        extrude(amount=C.COVER_THICKNESS + 0.2)
    assert bp.part is not None
    return cast(Part, Pos(0, 0, C.MAIN_RIM_Z - 0.1) * bp.part)


def _screw_holes() -> Part:
    """M2 clearance holes through the cover at each standoff."""
    with BuildPart() as bp:
        for hx, hy in C.MOUNTING_HOLES:
            cx, cy = C.pcb_to_case(hx, hy)
            with Locations((cx, cy, C.MAIN_RIM_Z + C.COVER_THICKNESS / 2)):
                Cylinder(radius=C.COVER_SCREW_CLEARANCE_DIA / 2,
                         height=C.COVER_THICKNESS + 0.2)
    assert bp.part is not None
    return cast(Part, bp.part)


def build_top_cover() -> Part:
    """Plate-shaped lid with switch windows and standoff screw holes removed."""
    cover = _cover_body()

    for cutout_pcb in _load_plate_cutouts():
        case_pts = [C.pcb_to_case(x, y) for x, y in cutout_pcb]
        if len(case_pts) < 3:
            continue
        cover = cast(Part, cover - _window_solid(case_pts))

    cover = cast(Part, cover - _screw_holes())

    if not isinstance(cover, Part):
        solids = cover.solids()
        cover = Part(children=list(solids)) if solids else Part(children=[cover])
    return cover


# %%
if __name__ == "__main__":
    from ocp_vscode import show
    show(build_top_cover(), name="top_cover")
