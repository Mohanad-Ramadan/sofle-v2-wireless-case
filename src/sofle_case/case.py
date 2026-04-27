"""Compose the full case half from tray + standoffs + MCU cover, minus cutouts."""
from __future__ import annotations
from typing import Literal, cast
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
    shell = cast(Part, shell)

    # Cutouts (subtract)
    shell -= usb_c_cutout()
    shell -= slide_switch_cutout()
    shell -= reset_pin_cutout()
    shell -= floor_recess()

    # Boolean ops return Shape; cast back to Part for type checker.
    shell = cast(Part, shell)

    if side == "right":
        # Mirror about the YZ plane through case centre X = OUTER_WIDTH/2.
        # build123d's mirror() reflects about a plane through the origin, so we
        # shift by -OUTER_WIDTH/2, mirror about YZ, then shift back.
        shell = cast(Part, Pos(-C.OUTER_WIDTH / 2, 0, 0) * shell)
        shell = cast(Part, mirror(shell, about=Plane.YZ))
        shell = cast(Part, Pos(C.OUTER_WIDTH / 2, 0, 0) * shell)

    # Boolean ops (+= / -=) return Solid; wrap as Part to satisfy callers.
    if not isinstance(shell, Part):
        shell = Part(children=[shell])

    return shell


# %%
if __name__ == "__main__":
    from ocp_vscode import show
    from sofle_case.case import build_case_half
    show(build_case_half("left"), build_case_half("right"), names=["left", "right"])
