"""Raised MCU cover, merged with the +Y outer wall."""
from __future__ import annotations
from build123d import Part, BuildPart, Locations, Box, Mode
from . import constants as C


def build_mcu_cover() -> Part:
    """Returns a Part to be UNION'd with the tray. The +Y face sits flush with the
    case +Y outer edge (y = OUTER_DEPTH). The bottom extends down to PCB_TOP_Z so
    that when union'd with the tray it merges seamlessly into the +Y wall."""
    mcu_x_case, _ = C.pcb_to_case(*C.MCU_POS)

    z_low = C.PCB_TOP_Z
    h = C.MCU_COVER_Z - z_low
    cx = mcu_x_case
    cy = C.OUTER_DEPTH - C.MCU_COVER_D / 2  # +Y face flush at OUTER_DEPTH

    inner_w = C.MCU_COVER_W - 2 * C.WALL_THICKNESS
    inner_d = C.MCU_COVER_D - 2 * C.WALL_THICKNESS
    inner_h = h + 0.02

    with BuildPart() as bp:
        with Locations((cx, cy, z_low + h / 2)):
            Box(C.MCU_COVER_W, C.MCU_COVER_D, h)
        with Locations((cx, cy, z_low + inner_h / 2)):
            Box(inner_w, inner_d, inner_h, mode=Mode.SUBTRACT)

    return bp.part
