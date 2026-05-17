"""Stepped standoff: lower shoulder (PCB seat) + upper pin (through PCB) + M2 tap bore."""
from __future__ import annotations
from build123d import Part, Cylinder, Cone, BuildPart, Mode, Locations
from . import constants as C


def stepped_standoff(at: tuple[float, float]) -> Part:
    """Build one standoff in case coords. Origin = (at_x, at_y, 0).

    Geometry:
      - Lower section: Z=FLOOR_THICKNESS → PCB_SEAT_Z, OD=STANDOFF_OD_LOWER (PCB-seat shoulder)
      - Upper section: Z=PCB_SEAT_Z → PLATE_SEAT_Z, OD=STANDOFF_OD_UPPER (passes through PCB hole)
      - M2 tap bore: drilled top-down from PLATE_SEAT_Z to depth STANDOFF_TAP_DEPTH, Ø=STANDOFF_TAP_DIA
    """
    x, y = at

    lower_h = C.PCB_SEAT_Z - C.FLOOR_THICKNESS       # 2.5 mm
    upper_h = C.PLATE_SEAT_Z - C.PCB_SEAT_Z           # 4.6 mm (passes through PCB + spans MX body gap)
    lower_z = C.FLOOR_THICKNESS + lower_h / 2         # cylinder centre Z = 3.25
    upper_z = C.PCB_SEAT_Z + upper_h / 2              # cylinder centre Z = 5.5

    bore_z = C.PLATE_SEAT_Z - C.STANDOFF_TAP_DEPTH / 2  # centre of tap bore = 4.5

    with BuildPart() as bp:
        with Locations((x, y, lower_z)):
            Cylinder(radius=C.STANDOFF_OD_LOWER / 2, height=lower_h)
        with Locations((x, y, upper_z)):
            Cylinder(radius=C.STANDOFF_OD_UPPER / 2, height=upper_h)
        with Locations((x, y, bore_z)):
            Cylinder(
                radius=C.STANDOFF_TAP_DIA / 2,
                height=C.STANDOFF_TAP_DEPTH,
                mode=Mode.SUBTRACT,
            )
        with Locations((x, y, C.PLATE_SEAT_Z - C.STANDOFF_TAP_CHAMFER / 2)):
            Cone(
                bottom_radius=C.STANDOFF_TAP_DIA / 2,
                top_radius=C.STANDOFF_TAP_DIA / 2 + C.STANDOFF_TAP_CHAMFER,
                height=C.STANDOFF_TAP_CHAMFER,
                mode=Mode.SUBTRACT,
            )

    assert bp.part is not None
    return bp.part


# %%
if __name__ == "__main__":
    from ocp_vscode import show
    from sofle_case.standoffs import stepped_standoff
    show(stepped_standoff(at=(0.0, 0.0)))
