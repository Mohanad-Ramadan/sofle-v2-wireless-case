"""Compose the full case half from tray + standoffs + MCU cover, minus cutouts."""
from __future__ import annotations
from typing import Literal
from build123d import Part, mirror, Plane, Pos
from . import constants as C
from .tray import build_tray
from .standoffs import stepped_standoff
from .mcu_cover import build_mcu_cover
from .cutouts import (
    usb_c_cutout, slide_switch_cutout, reset_pin_cutout, floor_recess,
)


Side = Literal["left", "right"]


def build_case_half(side: Side) -> Part:
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")

    shell = build_tray()

    # 5 standoffs at PCB-coord mounting holes, translated to case coords.
    for hx, hy in C.MOUNTING_HOLES:
        cx, cy = C.pcb_to_case(hx, hy)
        shell += stepped_standoff(at=(cx, cy))

    # MCU cover (union)
    shell += build_mcu_cover()

    # Cutouts (subtract)
    shell -= usb_c_cutout()
    shell -= slide_switch_cutout()
    shell -= reset_pin_cutout()
    shell -= floor_recess()

    if side == "right":
        # Mirror about the YZ plane through case centre X = OUTER_WIDTH/2.
        # build123d's mirror() reflects about a plane through the origin, so we
        # shift by -OUTER_WIDTH/2, mirror about YZ, then shift back.
        shell = Pos(-C.OUTER_WIDTH / 2, 0, 0) * shell
        shell = mirror(shell, about=Plane.YZ)
        shell = Pos(C.OUTER_WIDTH / 2, 0, 0) * shell

    # Boolean ops (+= / -=) return Solid; wrap as Part to satisfy callers.
    if not isinstance(shell, Part):
        shell = Part(children=[shell])

    return shell
