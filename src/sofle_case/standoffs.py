"""Historical stepped M2 screw bosses used by the monolithic case."""
from __future__ import annotations

from typing import cast

from build123d import BuildPart, Cylinder, Locations, Part, Solid

from . import constants as C


def stepped_standoff(at: tuple[float, float]) -> Part:
    """Build one boss in case coordinates, ending flush at ``PLATE_SEAT_Z``."""
    x, y = at

    lower_h = C.PCB_SEAT_Z - C.FLOOR_THICKNESS
    upper_h = C.PLATE_SEAT_Z - C.PCB_SEAT_Z
    lower_z = C.FLOOR_THICKNESS + lower_h / 2

    with BuildPart() as bp:
        with Locations((x, y, lower_z)):
            Cylinder(C.STANDOFF_OD_LOWER / 2, lower_h)
        with Locations((x, y, C.PCB_SEAT_Z + upper_h / 2)):
            Cylinder(C.STANDOFF_OD_UPPER / 2, upper_h)

    assert bp.part is not None
    boss = cast(Part, bp.part)
    bore_bottom = C.PLATE_SEAT_Z - C.STANDOFF_BORE_DEPTH
    bore = Solid.make_cylinder(C.STANDOFF_TAP_DIA / 2,
                               C.STANDOFF_BORE_DEPTH - C.STANDOFF_BORE_CHAMFER).translate(
                                   (x, y, bore_bottom))
    entry = Solid.make_cone(C.STANDOFF_TAP_DIA / 2,
                            C.STANDOFF_TAP_DIA / 2 + C.STANDOFF_BORE_CHAMFER,
                            C.STANDOFF_BORE_CHAMFER).translate(
                                (x, y, C.PLATE_SEAT_Z - C.STANDOFF_BORE_CHAMFER))
    return cast(Part, boss - bore - entry)


# %%
if __name__ == "__main__":
    from ocp_vscode import show

    from sofle_case.standoffs import stepped_standoff
    show(stepped_standoff(at=(0.0, 0.0)))
