"""Compose the full case half from tray + standoffs, minus cutouts."""
from __future__ import annotations
from typing import Literal, cast
from build123d import Part, mirror, Plane, Pos, fillet, Axis, BuildPart, Locations, Cylinder, Sphere
from . import constants as C
from .tray import build_tray
from .standoffs import stepped_standoff
from .cutouts import usb_c_cutout
from .battery import battery_pocket


Side = Literal["left", "right"]


def build_case_half(side: Side) -> Part:
    """Build a single case half.

    ``side="right"`` returns the as-built geometry (MCU hill on the −X wall).
    ``side="left"`` returns the mirror image, reflected about the case
    centreline (X = OUTER_WIDTH / 2), so the MCU hill lands on the +X wall.
    """
    if side not in ("left", "right"):
        raise ValueError(f"side must be 'left' or 'right', got {side!r}")

    shell = build_tray()

    for hx, hy in C.MOUNTING_HOLES:
        cx, cy = C.pcb_to_case(hx, hy)
        shell += stepped_standoff(at=(cx, cy))

    shell = cast(Part, shell)

    shell -= usb_c_cutout()

    shell = cast(Part, shell)

    shell -= battery_pocket()

    shell = cast(Part, shell)

    if side == "left":
        # Mirror about the YZ plane through case centre X = OUTER_WIDTH/2.
        # build123d's mirror() reflects about a plane through the origin, so we
        # shift by -OUTER_WIDTH/2, mirror about YZ, then shift back.
        shell = Pos(-C.OUTER_WIDTH / 2, 0, 0) * shell
        shell = mirror(shell, about=Plane.YZ)
        shell = Pos(C.OUTER_WIDTH / 2, 0, 0) * shell
        shell = cast(Part, shell)

    if not isinstance(shell, Part):
        solids = shell.solids()
        shell = Part(children=list(solids)) if solids else Part(children=[shell])

    return shell


# %%
def _corner_markers() -> Part:
    """Debug spheres at geometry transition points. All coords currently commented
    out — uncomment specific entries to visualise edges in the OCP viewer."""
    coords: tuple[tuple[float, float, float], ...] = (
        # Switch-column-top case edges (outer wall): the staircase along the
        # top wall where each column's back edge steps to match that
        # column's stagger. Runs from the right-edge top end above back to
        # the MCU corner.
        (111.5,  110.0, C.MAIN_RIM_Z),  # column step
        (108.5,  119.0, C.MAIN_RIM_Z),  # column step
        ( 92.46, 119.0,  C.MAIN_RIM_Z),  # column step
        ( 89.5,  121.5, C.MAIN_RIM_Z),  # column step (thumb-cluster tab)
        ( 71.5,  121.5, C.MAIN_RIM_Z),  # column step (thumb-cluster tab)
        ( 68.54, 119.0,  C.MAIN_RIM_Z),  # column step
        ( 52.5,  119.0, C.MAIN_RIM_Z),  # column step -- index column (matches MCU_Y_RELIEF_TARGET_Y)
        ( 49.54, 116.5,  C.MAIN_RIM_Z),  # column step
    )
    with BuildPart() as bp:
        for x, y, z in coords:
            with Locations((x, y, z)):
                Sphere(radius=1.0)
    return bp.part # type: ignore


# %%
if __name__ == "__main__":
    from ocp_vscode import show
    from sofle_case.case import build_case_half
    from sofle_case import constants as C

    _SIDE: Side = "right"

    def _mirror_part(p: Part) -> Part:
        """Apply the same mirror transform as build_case_half() for side='left'.

        Phantoms are always built in right-half (un-mirrored) coordinates. When
        viewing the left half the same shift-mirror-shift must be applied so
        they stay aligned with the case geometry.
        """
        if _SIDE == "left":
            p = cast(Part, Pos(-C.OUTER_WIDTH / 2, 0, 0) * p)
            p = cast(Part, mirror(p, about=Plane.YZ))
            p = cast(Part, Pos(C.OUTER_WIDTH / 2, 0, 0) * p)
        return p

    parts = [build_case_half(_SIDE)]
    names = ["case"]

    if C.SHOW_PCB_PHANTOM:
        from sofle_case.pcb_phantom import build_pcb_phantom
        parts.append(_mirror_part(build_pcb_phantom()))
        names.append("pcb_phantom")

    if C.SHOW_PLATE_PHANTOM:
        from sofle_case.plate_phantom import build_plate_phantom
        parts.append(_mirror_part(build_plate_phantom()))
        names.append("plate_phantom")

    if C.SHOW_SWITCH_PHANTOM:
        from sofle_case.switch_phantom import build_switch_phantom
        parts.append(_mirror_part(build_switch_phantom()))
        names.append("switch_phantom")

    parts.append(_corner_markers())
    names.append("corner_markers")

    show(*parts, names=names)
