"""Stepped standoff: lower shoulder (PCB seat) + upper pin (through PCB) + M2 tap bore."""
from __future__ import annotations
from build123d import Part, Cylinder, Cone, BuildPart, Mode, Locations
from . import constants as C


def stepped_standoff(at: tuple[float, float]) -> Part:
    """Build one standoff in case coords. Origin = (at_x, at_y, 0).

    Geometry:
      - Lower section: Z=FLOOR_THICKNESS → PCB_SEAT_Z, OD=STANDOFF_OD_LOWER (PCB-seat shoulder)
      - Upper section: Z=PCB_SEAT_Z → pin_top, OD=STANDOFF_OD_UPPER (passes through PCB hole)
      - M2 tap bore: drilled top-down from pin_top to depth STANDOFF_TAP_DEPTH, Ø=STANDOFF_TAP_DIA

    ``pin_top`` is PLATE_SEAT_Z − STANDOFF_PIN_RECESS, NOT PLATE_SEAT_Z. The pin is a screw
    boss, not a seat: the plate is located by the switches, and a pin that reached the plate
    would be a second datum for the same face. See STANDOFF_PIN_RECESS in constants.py.
    """
    x, y = at

    pin_top = C.PLATE_SEAT_Z - C.STANDOFF_PIN_RECESS  # deliberately BELOW the plate underside

    lower_h = C.PCB_SEAT_Z - C.FLOOR_THICKNESS       # 2.5 mm
    upper_h = pin_top - C.PCB_SEAT_Z                  # passes through the PCB, stops short of the plate
    lower_z = C.FLOOR_THICKNESS + lower_h / 2
    upper_z = C.PCB_SEAT_Z + upper_h / 2

    bore_z = pin_top - C.STANDOFF_TAP_DEPTH / 2       # centre of tap bore (follows the pin down)

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
        with Locations((x, y, pin_top - C.STANDOFF_TAP_CHAMFER / 2)):
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
