"""PCB phantom for visual fit-check in the OCP viewer. Gate with SHOW_PCB_PHANTOM."""
from __future__ import annotations
from typing import cast
from build123d import (
    Part, Wire, Pos, Polyline, make_face, extrude,
    Plane, BuildPart, BuildSketch, BuildLine, Locations,
    Box, Cylinder, Mode,
)
from . import constants as C
from .pcb_geometry import polygon_in_case_coords

# Phantom-only body dimensions (not structural — not in constants.py)
_MCU_W         = 18.0  # nice!nano width along case X
_MCU_L         = 33.0  # nice!nano length along case Y; USB-C exits the +Y face
_USB_C_STUB_Y  =  7.0  # depth of USB-C jack stub extending from MCU +Y face
_SW_BODY_X     =  8.0  # slide-switch body extent in -X from switch centre
_SW_BODY_Y     =  4.0  # slide-switch body width in Y
_SW_BODY_H     =  3.6  # slide-switch body height above PCB top


def _pcb_plate() -> Part:
    """PCB polygon extruded from PCB_SEAT_Z to PCB_TOP_Z, M2 holes subtracted."""
    poly = polygon_in_case_coords()
    pts = poly[:-1] if poly[0] == poly[-1] else poly

    with BuildLine() as bl:
        Polyline(*pts, close=True)
    wire = cast(Wire, bl.line)

    with BuildPart() as bp:
        with BuildSketch(Plane.XY):
            make_face(wire)  # type: ignore[arg-type]
        extrude(amount=C.PCB_THICKNESS)
        for hx, hy in C.MOUNTING_HOLES:
            cx, cy = C.pcb_to_case(hx, hy)
            with Locations((cx, cy, C.PCB_THICKNESS / 2)):
                Cylinder(
                    radius=C.PCB_HOLE_DIA / 2,
                    height=C.PCB_THICKNESS + 0.1,
                    mode=Mode.SUBTRACT,
                )

    assert bp.part is not None
    return cast(Part, Pos(0, 0, C.PCB_SEAT_Z) * bp.part)


def _mcu_block() -> Part:
    """nice!nano daughter-board block above the main PCB plate."""
    cx, cy = C.pcb_to_case(*C.MCU_POS)
    block_h = C.MCU_PCB_TOP_Z - C.PCB_TOP_Z
    center_z = C.PCB_TOP_Z + block_h / 2

    with BuildPart() as bp:
        with Locations((cx, cy, center_z)):
            Box(_MCU_W, _MCU_L, block_h)

    assert bp.part is not None
    return bp.part


def _usb_c_stub() -> Part:
    """USB-C jack body stub at the +Y face of the MCU block."""
    cx, cy = C.pcb_to_case(*C.MCU_POS)
    mcu_y_face = cy + _MCU_L / 2          # +Y face of MCU block (≈ 118.59 case-Y)
    stub_center_y = mcu_y_face + _USB_C_STUB_Y / 2
    stub_h = C.USB_C_BODY_TOP_Z - C.MCU_PCB_TOP_Z
    center_z = C.MCU_PCB_TOP_Z + stub_h / 2

    with BuildPart() as bp:
        with Locations((cx, stub_center_y, center_z)):
            Box(C.USB_C_W, _USB_C_STUB_Y, stub_h)

    assert bp.part is not None
    return bp.part


def _slide_switch_body() -> Part:
    """Slide-switch body block, extending -X from the switch centre."""
    cx, cy = C.pcb_to_case(*C.SW_SLIDE_POS)
    body_center_x = cx - _SW_BODY_X / 2
    center_z = C.PCB_TOP_Z + _SW_BODY_H / 2

    with BuildPart() as bp:
        with Locations((body_center_x, cy, center_z)):
            Box(_SW_BODY_X, _SW_BODY_Y, _SW_BODY_H)

    assert bp.part is not None
    return bp.part


def build_pcb_phantom() -> Part:
    """PCB plate + MCU daughter board + USB-C jack stub + slide-switch body."""
    return Part(children=[_pcb_plate(), _mcu_block(), _usb_c_stub(), _slide_switch_body()])


if __name__ == "__main__":
    from ocp_vscode import show
    show(build_pcb_phantom(), name="pcb_phantom")
