"""Slide-switch bowl fit and flat-wall (no-hill) guarantees."""
from build123d import Axis, Solid
from sofle_case import constants as C
from sofle_case.tray import build_tray


def test_bowl_removes_material_at_switch():
    """The bowl scoop must remove material from the −X wall at the switch position."""
    tray = build_tray()
    _, cy = C.pcb_to_case(*C.SW_SLIDE_POS)
    wall_outer_x = (C.pcb_to_case(C.PCB_X_MIN, 0)[0]
                    - C.WALL_THICKNESS - C.PCB_XY_CLEARANCE)
    probe = Solid.make_box(1.0, 1.0, 1.0).translate(
        (wall_outer_x - 0.5, cy - 0.5, C.SLIDE_BOWL_CENTER_Z - 0.5)
    )
    assert (tray & probe).volume < 0.01, (
        "bowl did not remove material at the switch position on the −X wall"
    )


def test_neg_x_wall_flat_at_mcu():
    """No hill: the −X wall over the MCU is flat at MAIN_RIM_Z, not raised."""
    tray = build_tray()
    _, mcu_cy = C.pcb_to_case(*C.MCU_POS)
    # At MCU Y the polygon left edge is the (0,0)→(0,-80.5) segment (PCB X=0),
    # not PCB_X_MIN which only applies at the board's bottom corners.
    poly_left_x = C.pcb_to_case(0.0, 0.0)[0]
    wall_center_x = poly_left_x - (C.WALL_THICKNESS + C.PCB_XY_CLEARANCE) / 2
    probe_z = C.MAIN_RIM_Z - 0.5
    probe = Solid.make_box(2.0, 2.0, 0.3).translate(
        (wall_center_x - 1.0, mcu_cy - 1.0, probe_z)
    )
    vol = (tray & probe).volume
    assert vol > 0.01, (
        f"−X wall has no material at MCU Y just below rim — wall may not reach MAIN_RIM_Z"
    )
    above_probe = Solid.make_box(2.0, 2.0, 0.3).translate(
        (wall_center_x - 1.0, mcu_cy - 1.0, C.MAIN_RIM_Z + 0.2)
    )
    above_vol = (tray & above_probe).volume
    assert above_vol < 0.01, (
        f"−X wall over MCU has material above rim — wall is not flat at MAIN_RIM_Z"
    )


def test_no_wall_above_rim():
    """All walls are flat at MAIN_RIM_Z — no feature (hill/ramp/relief) rises above it."""
    tray = build_tray()
    high = tray.edges().filter_by_position(Axis.Z, minimum=C.MAIN_RIM_Z + 0.5, maximum=999)
    assert len(high) == 0, f"{len(high)} edges above the rim — walls are not flat"


def test_slide_slot_clears_plate():
    """Slide-switch bowl centre must stay above the PCB seat shelf."""
    assert C.SLIDE_BOWL_CENTER_Z >= C.PCB_SEAT_Z, (
        f"bowl centre {C.SLIDE_BOWL_CENTER_Z} mm < PCB_SEAT_Z {C.PCB_SEAT_Z}"
    )
