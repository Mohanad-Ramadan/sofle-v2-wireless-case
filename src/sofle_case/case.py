"""Compose the full case half from tray + standoffs, minus cutouts."""
from __future__ import annotations
from typing import Literal, cast
from build123d import Part, fillet, Axis
from . import constants as C
from .tray import build_tray
from .standoffs import stepped_standoff
from .cutouts import usb_c_cutout, slide_switch_cutout


Side = Literal["left", "right"]


def build_case_half(side: Side) -> Part:
    """Build a single case half.

    The Sofle PCB is reversible — both halves share one case STL. ``side`` is
    accepted for CLI symmetry / export naming but produces identical geometry.
    """
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")

    shell = build_tray()

    for hx, hy in C.MOUNTING_HOLES:
        cx, cy = C.pcb_to_case(hx, hy)
        shell += stepped_standoff(at=(cx, cy))

    shell = cast(Part, shell)

    shell -= usb_c_cutout()
    shell -= slide_switch_cutout()

    shell = cast(Part, shell)

    # Round the outer rim corners of the slide switch slot
    z_hi = C.SLIDE_SWITCH_Z_RANGE[1]
    slide_outer_x = C.PCB_OFFSET_X - (C.WALL_THICKNESS + C.PCB_XY_CLEARANCE)  # 8.5
    slot_rim_edges = (
        shell.edges()
             .filter_by_position(Axis.X, minimum=slide_outer_x - 0.1, maximum=slide_outer_x + C.WALL_THICKNESS + 0.1)
             .filter_by_position(Axis.Z, minimum=z_hi - 0.5, maximum=z_hi + 0.1)
    )
    if slot_rim_edges:
        shell = fillet(slot_rim_edges, radius=C.SLIDE_SWITCH_CORNER_R)
        shell = cast(Part, shell)

    if not isinstance(shell, Part):
        shell = Part(children=[shell])

    return shell


# %%
if __name__ == "__main__":
    from ocp_vscode import show
    from sofle_case.case import build_case_half
    from sofle_case import constants as C

    parts = [build_case_half("right")]
    names = ["case"]

    if C.SHOW_PCB_PHANTOM:
        from sofle_case.pcb_phantom import build_pcb_phantom
        parts.append(build_pcb_phantom())
        names.append("pcb_phantom")

    if C.SHOW_PLATE_PHANTOM:
        from sofle_case.plate_phantom import build_plate_phantom
        parts.append(build_plate_phantom())
        names.append("plate_phantom")

    if C.SHOW_SWITCH_PHANTOM:
        from sofle_case.switch_phantom import build_switch_phantom
        parts.append(build_switch_phantom())
        names.append("switch_phantom")

    show(*parts, names=names)
