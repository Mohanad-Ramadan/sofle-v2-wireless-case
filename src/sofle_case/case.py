"""Compose the full case half from tray + standoffs, minus cutouts."""
from __future__ import annotations
from typing import Literal, cast
from build123d import Part, mirror, Plane, Pos, fillet, Axis, BuildPart, Locations, Cylinder, Sphere
from . import constants as C
from .tray import build_tray
from .standoffs import stepped_standoff
from .cutouts import usb_c_cutout


Side = Literal["left", "right"]


def build_case_half(side: Side) -> Part:
    """Build a single case half.

    ``side="left"`` returns the as-built geometry (MCU hill on the −X wall).
    ``side="right"`` returns the mirror image, reflected about the case
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

    if side == "right":
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
    x_inner   = C.PCB_OFFSET_X - C.PCB_XY_CLEARANCE                       # 11.000
    x_outer   = C.PCB_OFFSET_X - (C.WALL_THICKNESS + C.PCB_XY_CLEARANCE)  # 8.500
    sw_cy     = C.pcb_to_case(*C.SW_SLIDE_POS)[1]
    mcu_cy    = C.pcb_to_case(*C.MCU_POS)[1]
    half_narrow = C.SLIDE_SWITCH_W / 2                                    # 3.0
    half_wide   = C.SLIDE_SWITCH_TOP_W / 2                                # 7.0
    y_slot_n  = sw_cy + half_wide                                         # 77.270
    y_mcu_bot = mcu_cy - C.MCU_BODY_L / 2                                 # 80.840
    z_slot_lo = C.SLIDE_SWITCH_Z_RANGE[0]                                 # 7.200
    y_spline_hits_wall_top = 75.780   # numerically solved; slot +Y spline @ z=13.7
    coords: tuple[tuple[float, float, float], ...] = (
        # −X wall TOP kinks (inner wall face, x_inner = 11.0)
        # (x_inner, y_slot_n,               C.S_CURVE_RAMP_Z_FLOOR),  # P1 (11.00, 77.27, 13.70)
        # (x_inner, y_mcu_bot,              C.MCU_HILL_Z),            # P2 (11.00, 80.84, 17.10)
        # # Slot polygon: two cutout points (−Y interior side, outer wall face x_outer = 8.5)
        # (x_outer, sw_cy - half_narrow,    z_slot_lo),               # A1 (8.50, 67.27, 7.20)  −Y narrow bottom
        # (x_outer, sw_cy - half_wide,      C.S_CURVE_RAMP_Z_FLOOR),  # A3 (8.50, 63.27, 13.70) −Y wide top corner
        # # Slot polygon: +Y rim spline endpoints (right side of switch rim)
        # (x_outer, sw_cy + half_narrow,    z_slot_lo),               # B1 (8.50, 73.27, 7.20)  +Y narrow bottom
        # (x_outer, sw_cy + half_wide,      C.S_CURVE_RAMP_Z_FLOOR),  # B2 (8.50, 77.27, 13.70) +Y wide top corner
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
        """Apply the same mirror transform as build_case_half() for side='right'.

        Phantoms are always built in left-half (un-mirrored) coordinates. When
        viewing the right half the same shift-mirror-shift must be applied so
        they stay aligned with the case geometry.
        """
        if _SIDE == "right":
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
