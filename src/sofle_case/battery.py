"""Battery pocket: blind recess in the floor for a 405070 LiPo cell (50x70x4mm)."""
from __future__ import annotations
from typing import cast
from build123d import Part, BuildPart, BuildSketch, Plane, Pos, Rectangle, extrude, fillet, Axis
from . import constants as C


def battery_pocket() -> Part:
    """Cutter part: subtract from the tray to recess a battery pocket into the floor.

    Spans Z = (FLOOR_THICKNESS − BATTERY_POCKET_DEPTH) → FLOOR_THICKNESS, i.e. a
    blind pocket cut down from the floor's top face, leaving BATTERY_POCKET_DEPTH
    less material locally while the rest of the floor stays full thickness.
    """
    cx, cy = C.pcb_to_case(*C.BATTERY_POCKET_POS)
    half_w = C.BATTERY_W / 2 + C.BATTERY_XY_CLEARANCE
    half_l = C.BATTERY_L / 2 + C.BATTERY_XY_CLEARANCE
    z_lo = C.FLOOR_THICKNESS - C.BATTERY_POCKET_DEPTH
    z_hi = C.FLOOR_THICKNESS

    with BuildPart() as bp:
        with BuildSketch(Plane.XY.offset(z_lo)):
            Rectangle(half_w * 2, half_l * 2)
        extrude(amount=z_hi - z_lo)
        vertical = bp.edges().filter_by(Axis.Z)
        if vertical:
            fillet(vertical, radius=C.BATTERY_POCKET_CORNER_R)
    assert bp.part is not None
    return cast(Part, Pos(cx, cy, 0) * bp.part)


# %%
if __name__ == "__main__":
    from ocp_vscode import show
    from sofle_case.battery import battery_pocket
    show(battery_pocket())
