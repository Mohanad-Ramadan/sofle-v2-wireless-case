"""PCB phantom for visual fit-check in the OCP viewer. Gate with SHOW_PCB_PHANTOM."""
from __future__ import annotations
import json
import math
from pathlib import Path
from typing import cast
from build123d import (
    Part, Wire, Pos, Polyline, make_face, extrude,
    Plane, BuildPart, BuildSketch, BuildLine, Locations, Location,
    Box, Cylinder, Mode,
)
from . import constants as C
from .pcb_geometry import polygon_in_case_coords

_DATA = Path(__file__).resolve().parents[2] / "data"

# Phantom-only body dimensions (not structural — not in constants.py)
_MCU_W         = 18.0  # nice!nano width along case X
_USB_C_STUB_Y  =  7.0  # depth of USB-C jack stub extending from MCU +Y face

# SK12D07VG3 slide switch geometry (local frame: pins along local X)
# Pin span from drill data: local X = -2.1 .. +6.1 → center at +2.0
_SK12_BODY_L   =  8.7  # metal can length along pin row (local X)
_SK12_BODY_W   =  4.4  # metal can width perpendicular to pins (local Y)
_SK12_BODY_H   =  4.3  # metal can height above PCB
_SK12_NUB_L    =  3.5  # actuator nub length along pin row (local X)
_SK12_NUB_D    =  3.0  # actuator protrusion beyond body edge (local -Y)
_SK12_NUB_H    =  2.0  # actuator height above metal can
_SK12_PIN_CENTER_X = 2.0  # body center offset from footprint origin (local X)

# SW31 pin holes from SofleKeyboard-PTH.drl (inch→mm). All at PCB X≈2.944.
_SW31_PIN_HOLES: tuple[tuple[float, float, float], ...] = (
    # (pcb_x_mm, pcb_y_mm, drill_dia_mm)
    (0.1159 * 25.4, -1.6192 * 25.4, 0.0591 * 25.4),  # mounting
    (0.1159 * 25.4, -1.7019 * 25.4, 0.0315 * 25.4),  # signal (ref point)
    (0.1159 * 25.4, -1.7806 * 25.4, 0.0315 * 25.4),  # signal
    (0.1159 * 25.4, -1.8594 * 25.4, 0.0315 * 25.4),  # signal
    (0.1159 * 25.4, -1.9420 * 25.4, 0.0591 * 25.4),  # mounting
)


def _slide_switch_pin_holes() -> Part:
    """SW31 PTH pin holes as cylinders through PCB thickness for visual confirmation."""
    with BuildPart() as bp:
        for pcb_x, pcb_y, dia in _SW31_PIN_HOLES:
            cx, cy = C.pcb_to_case(pcb_x, pcb_y)
            with Locations((cx, cy, C.PCB_SEAT_Z + C.PCB_THICKNESS / 2)):
                Cylinder(radius=dia / 2, height=C.PCB_THICKNESS + 0.02)
    assert bp.part is not None
    return bp.part


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
    """nice!nano + header legs block above the main PCB plate."""
    cx, cy = C.pcb_to_case(*C.MCU_POS)
    block_h  = C.MCU_HILL_Z - C.PCB_TOP_Z   # 11.0 mm: full MCU + header legs
    center_z = C.PCB_TOP_Z + block_h / 2

    with BuildPart() as bp:
        with Locations((cx, cy, center_z)):
            Box(_MCU_W, C.MCU_BODY_L, block_h)

    assert bp.part is not None
    return bp.part


def _usb_c_stub() -> Part:
    """USB-C jack body stub at the +Y face of the MCU block."""
    cx, cy = C.pcb_to_case(*C.MCU_POS)
    mcu_y_face = cy + C.MCU_BODY_L / 2    # +Y face of MCU block (≈ 118.59 case-Y)
    stub_center_y = mcu_y_face + _USB_C_STUB_Y / 2
    stub_h = C.USB_C_BODY_TOP_Z - C.MCU_PCB_TOP_Z
    center_z = C.MCU_PCB_TOP_Z + stub_h / 2

    with BuildPart() as bp:
        with Locations((cx, stub_center_y, center_z)):
            Box(C.USB_C_W, _USB_C_STUB_Y, stub_h)

    assert bp.part is not None
    return bp.part


def _rotate_2d(lx: float, ly: float, deg: float) -> tuple[float, float]:
    """Rotate a local (x, y) offset by *deg* degrees CCW."""
    r = math.radians(deg)
    return lx * math.cos(r) - ly * math.sin(r), lx * math.sin(r) + ly * math.cos(r)


def _slide_switch_body() -> Part:
    """SK12D07VG3 metal can + actuator nub, placed via components.json rotation.

    Local frame: pins along local X, body centered over pin span.
    Actuator nub extends in local -Y (toward -X wall after 270° rotation).
    """
    raw = json.loads((_DATA / "components.json").read_text())
    sw = raw["SW31"]
    cx, cy = C.pcb_to_case(sw["x"], sw["y"])
    rot = sw["rotation"]

    body_z = C.PCB_TOP_Z + _SK12_BODY_H / 2
    nub_z = C.PCB_TOP_Z + 1.5 + _SK12_NUB_H / 2

    bdx, bdy = _rotate_2d(_SK12_PIN_CENTER_X, 0.0, rot)
    ndx, ndy = _rotate_2d(
        _SK12_PIN_CENTER_X,
        -(_SK12_BODY_W / 2 + _SK12_NUB_D / 2),
        rot,
    )

    with BuildPart() as bp:
        with Locations(Location((cx + bdx, cy + bdy, body_z), (0, 0, rot))):
            Box(_SK12_BODY_L, _SK12_BODY_W, _SK12_BODY_H)
        with Locations(Location((cx + ndx, cy + ndy, nub_z), (0, 0, rot))):
            Box(_SK12_NUB_L, _SK12_NUB_D, _SK12_NUB_H)

    assert bp.part is not None
    return bp.part


def build_pcb_phantom() -> Part:
    """PCB plate + MCU daughter board + USB-C jack stub + slide-switch body + pin holes."""
    return Part(children=[
        _pcb_plate(), _mcu_block(), _usb_c_stub(),
        _slide_switch_body(), _slide_switch_pin_holes(),
    ])


if __name__ == "__main__":
    from ocp_vscode import show
    show(build_pcb_phantom(), name="pcb_phantom")
