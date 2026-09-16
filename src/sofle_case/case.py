"""Monolithic printable Sofle case."""
from __future__ import annotations

from typing import Literal, cast

from build123d import (
    Box,
    BuildPart,
    Location,
    Locations,
    Part,
    Plane,
    Pos,
    Solid,
    fillet,
    mirror,
)

from . import constants as C
from .battery import battery_pocket, jst_pocket, jst_wire_channel
from .pcb_geometry import rotate_2d, slide_switch_placement
from .standoffs import stepped_standoff
from .tray import build_tray

Side = Literal["left", "right"]


def _mirror_left(part: Part) -> Part:
    """Mirror right-hand geometry about the case centreline."""
    return cast(Part, Pos(C.OUTER_WIDTH / 2, 0, 0) * mirror(
        Pos(-C.OUTER_WIDTH / 2, 0, 0) * part, about=Plane.YZ))


def _slide_scoop() -> Part:
    """Top/side-open finger scoop over the slide actuator."""
    sw_cy = C.pcb_to_case(*C.SW_SLIDE_POS)[1]
    outer = C.pcb_to_case(0, 0)[0] - C.WALL_THICKNESS - C.PCB_XY_CLEARANCE
    inner = C.pcb_to_case(0, 0)[0] - C.PCB_XY_CLEARANCE
    x0 = outer - 1.5 - C.SLIDE_SCOOP_X_SHIFT
    x1 = inner + C.SLIDE_SCOOP_INNER_MARGIN - C.SLIDE_SCOOP_X_SHIFT
    z0, z1 = C.SLIDE_SCOOP_FLOOR_Z, C.MAIN_RIM_Z + 1.0
    box = cast(Part, Solid.make_box(
        x1 - x0, C.SLIDE_SCOOP_W, z1 - z0).translate(
            (x0, sw_cy - C.SLIDE_SCOOP_W / 2, z0)))
    # Keep the opening vertical to the rim.  Filleting these edges rounds the
    # top of the cutter back into the case and leaves an actuator ceiling.
    floor = [e for e in box.edges() if e.bounding_box().max.Z < z0 + 0.05]
    if floor:
        try:
            box = cast(Part, fillet(floor, radius=C.SLIDE_SCOOP_FLOOR_R))
        except ValueError:
            box = cast(Part, box)
    return box


def _slide_actuator_cavity() -> Part:
    """Registered actuator clearance from 0.3 below the PCB top to can-top + 0.3."""
    cx, cy, rot = slide_switch_placement()
    offsets = [
        (C.SLIDE_ACTUATOR_PIN_CENTER_X, 0.0,
         C.SLIDE_ACTUATOR_BODY_L, C.SLIDE_ACTUATOR_BODY_W),
        (C.SLIDE_ACTUATOR_PIN_CENTER_X,
         -(C.SLIDE_ACTUATOR_BODY_W / 2 + C.SLIDE_ACTUATOR_NUB_D / 2),
         C.SLIDE_ACTUATOR_NUB_L, C.SLIDE_ACTUATOR_NUB_D),
    ]
    pad = C.SLIDE_ACTUATOR_PAD
    z0 = C.PCB_TOP_Z - 0.3
    z1 = C.PCB_TOP_Z + C.SLIDE_ACTUATOR_BODY_H + 0.3
    with BuildPart() as bp:
        for lx, ly, dx, dy in offsets:
            ox, oy = rotate_2d(lx, ly, rot)
            with Locations(Location((cx + ox, cy + oy, (z0 + z1) / 2), (0, 0, rot))):
                Box(dx + 2 * pad, dy + 2 * pad, z1 - z0)
    assert bp.part is not None
    return bp.part


def _foot_recesses() -> Part:
    """Four 0.6 mm-deep underside seats opening at Z=0."""
    seats = None
    for x, y in C.FOOT_POSITIONS:
        cutter = Solid.make_cylinder(C.FOOT_DIA / 2, C.FOOT_DEPTH + 0.1).translate(
            (x, y, -0.1))
        seats = cutter if seats is None else seats + cutter
    assert seats is not None
    return cast(Part, seats)


def build_case_half(side: Side) -> Part:
    """Build exactly one printable, watertight monolithic case half."""
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")

    case = build_tray(rim_z=C.MAIN_RIM_Z)

    # Straight PCB-frame bore: inner wall follows PCB outline + 0.2 clearance
    # full height 6.6..rim 15.7, north wall solid — no MCU bay notch/cavity
    # (MCU on tall headers clears in open air above rim).
    for hx, hy in C.MOUNTING_HOLES:
        case = cast(Part, case + stepped_standoff(C.pcb_to_case(hx, hy)))

    case = cast(Part, case - battery_pocket() - jst_pocket() - jst_wire_channel())
    case = cast(Part, case - _slide_scoop() - _slide_actuator_cavity())
    case = cast(Part, case - _foot_recesses())

    if side == "left":
        case = _mirror_left(case)
    return case


if __name__ == "__main__":
    from ocp_vscode import show
    show(build_case_half("right"), names=["case"])
