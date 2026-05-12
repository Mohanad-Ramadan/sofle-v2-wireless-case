"""Compose the full case half from tray + standoffs, minus cutouts."""
from __future__ import annotations
from typing import Literal, cast
from build123d import Part, fillet, Axis, BuildPart, Locations, Cylinder, Sphere
from . import constants as C
from .tray import build_tray
from .standoffs import stepped_standoff
from .cutouts import usb_c_cutout


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

    shell = cast(Part, shell)

    if not isinstance(shell, Part):
        solids = shell.solids()
        shell = Part(children=list(solids)) if solids else Part(children=[shell])

    return shell


# %%
def _corner_markers() -> Part:
    """Spheres at the wall-TOP transition kinks (P1–P2), the slot-cutout polygon
    corners (A1, A3 −Y interior, B1–B2 +Y rim spline endpoints), and the ramp
    south start (C1) where the TOP_CHAMFER fillet visibly stops on the outer
    wall edge next to the rotary-encoder area.
    """
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

    parts.append(_corner_markers())
    names.append("corner_markers")

    show(*parts, names=names)
