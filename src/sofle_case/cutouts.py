"""Subtractive cutouts: USB-C (+Y wall), slide-switch arched-trapezoid slot (-X wall)."""
from __future__ import annotations
import math
from build123d import (
    Part,
    BuildPart, BuildSketch, BuildLine, Plane, Line, Spline, ThreePointArc, make_face,
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


def slide_switch_cutout() -> Part:
    """Slide-shape slot in -X wall: narrow at switch level, sides flare outward to wide rim opening.

    Right side (farther Y): spline with stretched top tangent for larger arc at rim.
    Left side (closer Y / ramp): spline with stretched top tangent for smoother ramp entry.
    """
    _, cy = C.pcb_to_case(*C.SW_SLIDE_POS)
    z_lo, z_hi = C.SLIDE_SWITCH_Z_RANGE
    half_narrow = C.SLIDE_SWITCH_W / 2
    half_wide   = C.SLIDE_SWITCH_TOP_W / 2

    # Extrude past the switch body so fingers can reach the actuator from outside.
    depth = C.PCB_OFFSET_X + C.SW_SLIDE_POS[0] + 5.0  # ≈ 25.7 mm

    with BuildPart() as bp:
        with BuildSketch(Plane.YZ):  # sketch at X=0; outer wall face is at X=8.5, subtraction still cuts wall
            with BuildLine():
                Line((cy - half_narrow, z_lo), (cy + half_narrow, z_lo))
                Spline(
                    (cy + half_narrow, z_lo),
                    (cy + half_wide,   z_hi),
                    tangents=[(0, 1), (1, 0)],
                    tangent_scalars=list(C.SLIDE_SWITCH_RIGHT_TANGENT_SCALARS),
                )
                Line((cy + half_wide, z_hi), (cy - half_wide, z_hi))
                Spline(
                    (cy - half_wide,   z_hi),
                    (cy - half_narrow, C.PLATE_TOP_Z),  # ramp only above plate — hides plate edge
                    tangents=[(-1, 0), (0, -1)],
                    tangent_scalars=list(C.SLIDE_SWITCH_RAMP_TANGENT_SCALARS),
                )
                Line((cy - half_narrow, C.PLATE_TOP_Z), (cy - half_narrow, z_lo))
            make_face()
        extrude(amount=depth)  # spans outer face → inner cavity at switch Y
        # Fillet the two bottom long edges (parallel to X, at z_lo) → semicircle arch at bottom
        fillet(
            bp.edges().filter_by(Axis.X).filter_by_position(
                Axis.Z, minimum=z_lo - 0.01, maximum=z_lo + 0.01
            ),
            radius=C.SLIDE_SWITCH_W / 2,
        )

    assert bp.part is not None
    return bp.part


def all_cutouts() -> list[Part]:
    return [usb_c_cutout(), slide_switch_cutout()]


# %%
if __name__ == "__main__":
    from ocp_vscode import show
    from sofle_case.cutouts import usb_c_cutout, slide_switch_cutout
    show(usb_c_cutout(), slide_switch_cutout(), names=["usb_c", "slide_switch"])
