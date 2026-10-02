"""Monolithic printable Sofle case."""
from __future__ import annotations

from typing import Literal, cast

from build123d import (
    Part,
    Plane,
    Pos,
    Solid,
    mirror,
)

from . import constants as C
from .battery import battery_pocket, jst_pocket, jst_wire_channel
from .slide_access import slide_body_cavity, slide_finger_cutout
from .standoffs import stepped_standoff
from .tray import build_tray

Side = Literal["left", "right"]


def _mirror_left(part: Part) -> Part:
    """Mirror right-hand geometry about the case centreline."""
    return cast(Part, Pos(C.OUTER_WIDTH / 2, 0, 0) * mirror(
        Pos(-C.OUTER_WIDTH / 2, 0, 0) * part, about=Plane.YZ))


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

    # Straight PCB-frame bore: inner wall follows PCB outline + PCB_XY_CLEARANCE
    # full height 6.6..rim 15.7, north wall solid — no MCU bay notch/cavity
    # (MCU on tall headers clears in open air above rim).
    for hx, hy in C.MOUNTING_HOLES:
        case = cast(Part, case + stepped_standoff(C.pcb_to_case(hx, hy)))

    case = cast(Part, case - battery_pocket() - jst_pocket() - jst_wire_channel())
    case = cast(Part, case - slide_finger_cutout() - slide_body_cavity(
        C.PCB_TOP_Z + C.SLIDE_ACTUATOR_BODY_H + 0.3))
    case = cast(Part, case - _foot_recesses())

    if side == "left":
        case = _mirror_left(case)
    return case


if __name__ == "__main__":
    from ocp_vscode import show

    from .knob import place_knob
    from .mcu_encoder_cover import build_mcu_encoder_cover
    from .pcb_phantom import build_pcb_phantom
    from .plate_phantom import build_plate_phantom
    from .switch_phantom import build_switch_phantom

    _side = "right"
    show(
        build_case_half(_side),
        build_mcu_encoder_cover(_side),
        build_pcb_phantom(_side),
        build_plate_phantom(),
        build_switch_phantom(),
        place_knob(bottomed=True),
        names=[
            "case",
            "mcu_encoder_cover",
            "pcb+encoder+knob",
            "plate",
            "switches",
            "knob_on_untrimmed_shaft",
        ],
    )
