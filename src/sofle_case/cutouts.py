"""Subtractive cutouts: USB-C open-top slot through +Y wall."""
from __future__ import annotations
import math
from build123d import (
    Part,
    BuildPart, BuildSketch, BuildLine, Plane, Line, ThreePointArc, make_face,
    extrude, fillet, Axis,
)
from . import constants as C


_PIERCE = 6.0  # extra mm to ensure the cutout fully crosses any wall


def usb_c_cutout() -> Part:
    """Open-top slot through +Y wall, reaching past the MCU into the cavity.

    The PCB outline does not extend to the outer wall — there is ~12 mm of solid
    case between the wall face and the cavity edge at the MCU's X column.  The
    slot must therefore extend inward USB_C_Y_DEPTH mm to clear all solid material
    and give the cable unobstructed access to the jack.

    The bottom corners are quarter-circle arcs of radius USB_C_SIDE_BULGE, giving
    the opening a rounded-rectangle silhouette.  The straight sides run from the
    arc tangent point up to z_hi; the top edge is wider by 2×bulge.
    """
    cx, _ = C.pcb_to_case(*C.MCU_POS)
    z_lo, z_hi = C.USB_C_Z_RANGE
    half_w = C.USB_C_W / 2
    bulge  = C.USB_C_SIDE_BULGE
    total_depth = C.USB_C_Y_DEPTH + _PIERCE
    outer_y     = C.USB_C_OUTER_Y + _PIERCE  # outer +Y face at MCU X (PCB Y=0 + border); extrude goes −Y

    # Midpoint of each 90° corner arc (at 45° along the arc from each end).
    # Arc center for right corner: (cx+half_w+bulge, z_lo); midpoint at 135° from +X.
    _q = math.sqrt(2) / 2  # cos/sin 45°
    mr = (cx + half_w + bulge * _q,       z_lo + bulge * (1 - _q))
    ml = (cx - half_w - bulge * _q,       z_lo + bulge * (1 - _q))

    with BuildPart() as bp:
        with BuildSketch(Plane.XZ.offset(-outer_y)):
            with BuildLine():
                Line((cx - half_w,         z_lo),              (cx + half_w,         z_lo))
                ThreePointArc((cx + half_w, z_lo),              mr,                   (cx + half_w + bulge, z_lo + bulge))
                Line((cx + half_w + bulge, z_lo + bulge),      (cx + half_w + bulge, z_hi))
                Line((cx + half_w + bulge, z_hi),              (cx - half_w - bulge, z_hi))
                Line((cx - half_w - bulge, z_hi),              (cx - half_w - bulge, z_lo + bulge))
                ThreePointArc((cx - half_w - bulge, z_lo + bulge), ml,               (cx - half_w, z_lo))
            make_face()
        extrude(amount=total_depth)
    assert bp.part is not None
    return bp.part


def all_cutouts() -> list[Part]:
    return [usb_c_cutout()]


# %%
if __name__ == "__main__":
    from ocp_vscode import show
    from sofle_case.cutouts import usb_c_cutout
    show(usb_c_cutout(), names=["usb_c"])
