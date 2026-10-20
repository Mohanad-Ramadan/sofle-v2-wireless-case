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
from .tray import build_tray, outline

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


def _usb_notch(side: Side, oled: C.OledMode = "none") -> Part | None:
    """Canonical-frame USB slot through the tray north wall, or None when the port band clears
    the rim (every case but short-left, D7). It opens 1 mm into the cavity (south of the inner
    north wall at the MCU column) so the dropped jack body is clear, and runs 2 mm past the
    outer wall; Z spans the port band's low edge to 1 mm above the rim."""
    z_lo, _ = C.usb_port_z(side, oled)
    if z_lo >= C.MAIN_RIM_Z:
        return None
    cx = C.pcb_to_case(*C.MCU_POS)[0]
    y0 = C.TRAY_NORTH_LOW_Y + C.PCB_XY_CLEARANCE - 1.0
    y1 = outline(oled).north_run(cx) + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE + 2.0
    z1 = C.MAIN_RIM_Z + 1.0
    w = C.COVER_USB_PORT_W
    return cast(Part, Solid.make_box(w, y1 - y0, z1 - z_lo).translate((cx - w / 2, y0, z_lo)))


def build_case_half(side: Side, oled: C.OledMode = "none") -> Part:
    """Build exactly one printable, watertight monolithic case half.

    ``oled`` is the literal OLED mode (default ``"none"``, never resolved via C.OLED_MODE)."""
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")

    case = build_tray(rim_z=C.MAIN_RIM_Z, oled=oled)

    # Straight PCB-frame bore: inner wall follows PCB outline + PCB_XY_CLEARANCE
    # full height 6.6..rim 15.7, north wall solid — no MCU bay notch/cavity
    # (MCU on tall headers clears in open air above rim).
    for hx, hy in C.MOUNTING_HOLES:
        case = cast(Part, case + stepped_standoff(C.pcb_to_case(hx, hy)))

    case = cast(Part, case - battery_pocket() - jst_pocket() - jst_wire_channel())
    case = cast(Part, case - slide_finger_cutout() - slide_body_cavity(
        C.PCB_TOP_Z + C.SLIDE_ACTUATOR_BODY_H + 0.3))
    case = cast(Part, case - _foot_recesses())
    notch = _usb_notch(side, oled)
    if notch is not None:
        case = cast(Part, case - notch)

    if side == "left":
        case = _mirror_left(case)
    return case


if __name__ == "__main__":
    import sys

    from ocp_vscode import show

    from .knob import place_knob
    from .mcu_encoder_cover import build_mcu_encoder_cover
    from .pcb_phantom import build_pcb_phantom
    from .plate_phantom import build_plate_phantom
    from .switch_phantom import build_switch_phantom

    # python -m sofle_case.case [right|left] [none|long|short]
    _side = sys.argv[1] if len(sys.argv) > 1 else "right"
    _oled = sys.argv[2] if len(sys.argv) > 2 else "none"

    def _on_side(part):
        """Phantoms are authored in right-hand coords; mirror them onto the left half."""
        if _side != "left":
            return part
        from build123d import Plane, Pos, mirror
        return Pos(C.OUTER_WIDTH / 2, 0, 0) * mirror(
            Pos(-C.OUTER_WIDTH / 2, 0, 0) * part, about=Plane.YZ)

    parts = [
        (build_case_half(_side, oled=_oled), "case"),
        (build_mcu_encoder_cover(_side, oled=_oled), "mcu_encoder_cover"),
        (_on_side(build_pcb_phantom(_side, oled=_oled)), "pcb+encoder+knob"),
        (_on_side(build_plate_phantom()), "plate"),
        (_on_side(build_switch_phantom()), "switches"),
        (_on_side(place_knob(bottomed=True)), "knob_on_untrimmed_shaft"),
    ]
    if _oled != "none":
        from .oled_phantom import build_oled_phantom

        parts.append((_on_side(build_oled_phantom(_side, _oled)), "oled_module"))
    show(*(p for p, _ in parts), names=[n for _, n in parts])
