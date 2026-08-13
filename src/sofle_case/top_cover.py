"""Top cover — the sandwich lid.

A thin (``COVER_THICKNESS``) layer the shape of the switch plate, sitting on the
plate top (Z = ``MAIN_RIM_Z``) and held by the same standoffs via taller M2
screws. Each 14 mm plate cutout is grown by ``COVER_WINDOW_OFFSET`` to a 16.1 mm
window (mitered square corners) that clears the switch's 15.6 mm top housing by
0.25 mm/side — the switch pokes through and the cover seats flat; keycaps float
above and never touch it. That 0.25 mm is an assembly budget, not slack: see the
top-cover block in ``constants.py`` for the tolerance stack it has to absorb and
for what happened when the window hugged the collar instead. The plate outline's
own inner notch leaves the MCU/OLED/slide/JST bay open for free.

Geometry is driven by the same authoritative plate data the plate phantom uses
(``data/plate_outline.json`` + ``data/plate_cutouts.json``, re-parsed from the
original Sofle v2 top-plate gerber)."""
from __future__ import annotations
import json
from pathlib import Path
from typing import cast

from build123d import (
    Part, Wire, Pos, Polyline, make_face, extrude, offset, Kind,
    Plane, BuildPart, BuildSketch, BuildLine, Locations, Location, Box, Cylinder,
)
from . import constants as C

_DATA = Path(__file__).resolve().parents[2] / "data"


def _load_switch_positions() -> list[dict]:
    """Top-layer MX switch entries from components.json (excludes encoder SW25).

    Mirrors ``switch_phantom._load_switch_positions`` but read here from the same
    authoritative data — the puller notches must land on the real switch collars, so
    they are placed off the switch positions/rotations (not derived from the square,
    orientation-ambiguous plate cutouts)."""
    raw = json.loads((_DATA / "components.json").read_text())
    return [
        {"x": v["x"], "y": v["y"], "rot": v["rotation"]}
        for k, v in raw.items()
        if k.startswith("SW") and v.get("layer") == "top" and k != "SW25"
    ]


def _load_plate_polygon() -> list[tuple[float, float]]:
    return [tuple(p) for p in json.loads((_DATA / "plate_outline.json").read_text())]  # type: ignore[misc]


def _load_plate_cutouts() -> list[list[tuple[float, float]]]:
    raw = json.loads((_DATA / "plate_cutouts.json").read_text())
    return [[tuple(p) for p in cut] for cut in raw]  # type: ignore[return-value]


def _cover_body(margin: float = 0.0) -> Part:
    """Plate-outline polygon extruded up from the plate top by COVER_THICKNESS.

    ``margin`` grows the outline outward (Kind.ARC) before extruding. The
    standalone cover uses 0.0 (true plate footprint). The sandwich TOP part passes
    ``COVER_FUSE_MARGIN`` so the membrane bites into the upper-wall material and
    fuses into one solid instead of floating inside the cavity."""
    poly = [C.pcb_to_case(x, y) for x, y in _load_plate_polygon()]
    pts = poly[:-1] if poly[0] == poly[-1] else poly
    with BuildLine() as bl:
        Polyline(*pts, close=True)
    wire = cast(Wire, bl.line)
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            face = make_face(wire)  # type: ignore[arg-type]
            if margin:
                face = offset(face, amount=margin, kind=Kind.ARC)
        extrude(amount=C.COVER_THICKNESS)
    assert bp.part is not None
    return cast(Part, Pos(0, 0, C.MAIN_RIM_Z) * bp.part)


def _is_encoder_cutout(case_pts: list[tuple[float, float]]) -> bool:
    """True if this cutout is the EC11 encoder's, matched by centroid proximity
    to SW_ENCODER_POS (within 1 mm)."""
    enc_cx, enc_cy = C.pcb_to_case(*C.SW_ENCODER_POS)
    cx = sum(p[0] for p in case_pts) / len(case_pts)
    cy = sum(p[1] for p in case_pts) / len(case_pts)
    return ((cx - enc_cx) ** 2 + (cy - enc_cy) ** 2) ** 0.5 < 1.0


def _window_solid(case_pts: list[tuple[float, float]], margin: float) -> Part:
    """A single window: the plate cutout grown outward by ``margin`` (Kind.INTERSECTION,
    i.e. mitered SHARP corners), extruded through the full cover thickness (with a
    small over-cut top and bottom).

    MX switch windows use ``COVER_WINDOW_OFFSET`` (1.05) so a 14 mm cutout grows to a
    16.1 mm window, clearing the 15.6 mm top housing by 0.25 mm/side. The corners are
    mitered (not Kind.ARC rounded): a rounded corner of that radius would leave the
    switch box's square corner protruding into the cover, so the window is kept square
    to match the switch footprint (real MX housings have rounded corners, so a square
    window clears them with room to spare).
    The encoder window uses ``margin=0`` — its exact plate cutout — because the EC11
    body already passes through that opening and the bezel shell caps it from above."""
    pts = case_pts[:-1] if case_pts[0] == case_pts[-1] else case_pts
    with BuildLine() as bl:
        Polyline(*pts, close=True)
    wire = cast(Wire, bl.line)
    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            face = make_face(wire)  # type: ignore[arg-type]
            if margin:
                face = offset(face, amount=margin, kind=Kind.INTERSECTION)
        extrude(amount=C.COVER_THICKNESS + 0.2)
    assert bp.part is not None
    return cast(Part, Pos(0, 0, C.MAIN_RIM_Z - 0.1) * bp.part)


def _puller_notches() -> Part:
    """Two puller-access notches per MX switch, on the switch's local ±Y faces.

    Each notch is a box ``COVER_PULLER_NOTCH_W`` wide (local X), spanning radius
    INNER_R→OUTER_R (local Y) and the full cover thickness. INNER_R sits inside the
    window so the notch merges with it; OUTER_R opens a claw pocket just past the
    15.6 mm collar. Placed at each switch centre and rotated to the switch, so the
    notches track the rotated thumb switches too."""
    w = C.COVER_PULLER_NOTCH_W
    r0, r1 = C.COVER_PULLER_NOTCH_INNER_R, C.COVER_PULLER_NOTCH_OUTER_R
    length = r1 - r0
    y_mid = (r0 + r1) / 2.0
    z = C.MAIN_RIM_Z - 0.1
    h = C.COVER_THICKNESS + 0.2
    with BuildPart() as bp:
        for sw in _load_switch_positions():
            cx, cy = C.pcb_to_case(sw["x"], sw["y"])
            for sign in (+1.0, -1.0):
                # box centred on the local +Y or -Y face, then placed+rotated to the switch
                with Locations(Location((cx, cy, z + h / 2), (0, 0, sw["rot"]))):
                    with Locations((0.0, sign * y_mid, 0.0)):
                        Box(w, length, h)
    assert bp.part is not None
    return cast(Part, bp.part)


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


def build_top_cover(fuse_margin: float = 0.0) -> Part:
    """Plate-shaped lid with switch windows and standoff screw holes removed.

    ``fuse_margin`` (default 0.0) grows the outline outward so the membrane fuses
    to the upper walls when reused as the sandwich TOP part's ceiling. Left at 0.0
    the result is the true-footprint standalone cover."""
    cover = _cover_body(margin=fuse_margin)

    for cutout_pcb in _load_plate_cutouts():
        case_pts = [C.pcb_to_case(x, y) for x, y in cutout_pcb]
        if len(case_pts) < 3:
            continue
        margin = 0.0 if _is_encoder_cutout(case_pts) else C.COVER_WINDOW_OFFSET
        cover = cast(Part, cover - _window_solid(case_pts, margin))

    if C.COVER_PULLER_NOTCH:
        cover = cast(Part, cover - _puller_notches())

    cover = cast(Part, cover - _screw_holes())

    if not isinstance(cover, Part):
        solids = cover.solids()
        cover = Part(children=list(solids)) if solids else Part(children=[cover])
    return cover


# %%
if __name__ == "__main__":
    from ocp_vscode import show
    show(build_top_cover(), names=["top_cover"])
