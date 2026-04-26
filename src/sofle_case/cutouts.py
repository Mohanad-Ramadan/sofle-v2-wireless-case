"""Subtractive cutouts: USB-C (in MCU cover +Y face), slide-switch slot (-X wall),
reset pinhole (-X wall), floor recess for slide-switch body."""
from __future__ import annotations
from build123d import Part, Pos, Rot, Box, Cylinder, Align
from . import constants as C


_PIERCE = 6.0  # extra mm to ensure the cutout fully crosses any wall


def usb_c_cutout() -> Part:
    """Through-slot in +Y wall (within MCU cover) at MCU X, centered Z=USB_C_Z_CENTER."""
    cx, _ = C.pcb_to_case(*C.MCU_POS)
    cy = C.OUTER_DEPTH  # the +Y wall plane
    cz = C.USB_C_Z_CENTER
    return Pos(cx, cy, cz) * Box(
        C.USB_C_W, C.WALL_THICKNESS + _PIERCE, C.USB_C_H,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )


def slide_switch_cutout() -> Part:
    """Through-slot in -X wall at slide-switch Y; Z range per spec."""
    _, cy = C.pcb_to_case(*C.SW_SLIDE_POS)
    z_lo, z_hi = C.SLIDE_SWITCH_Z_RANGE
    cz = (z_lo + z_hi) / 2
    slot_h = z_hi - z_lo
    return Pos(0.0, cy, cz) * Box(
        C.WALL_THICKNESS + _PIERCE, C.SLIDE_SWITCH_W, slot_h,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )


def reset_pin_cutout() -> Part:
    """Cylindrical pinhole in -X wall, axis along X."""
    _, cy = C.pcb_to_case(*C.SW_RESET_POS)
    cz = C.RESET_Z_CENTER
    cyl = Cylinder(
        radius=C.RESET_PIN_DIA / 2,
        height=C.WALL_THICKNESS + _PIERCE,
    )
    # Default cylinder axis is Z; rotate to X.
    return Pos(0.0, cy, cz) * Rot(0, 90, 0) * cyl


def floor_recess() -> Part:
    """Rectangular pocket in floor under slide switch body."""
    cx, cy = C.pcb_to_case(*C.SW_SLIDE_POS)
    recess_depth_pierced = C.SLIDE_SWITCH_RECESS_DEPTH + 0.01
    cz = C.FLOOR_THICKNESS - recess_depth_pierced / 2
    return Pos(cx, cy, cz) * Box(
        C.SLIDE_SWITCH_RECESS_W, C.SLIDE_SWITCH_RECESS_D, recess_depth_pierced,
        align=(Align.CENTER, Align.CENTER, Align.CENTER),
    )
