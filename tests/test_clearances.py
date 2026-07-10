"""Slide-switch slot fit and flat-wall (no-hill) guarantees."""
from build123d import Axis
from sofle_case import constants as C
from sofle_case.tray import build_tray


def test_slot_envelops_switch_y():
    """The rectangular slot must cut the −X wall over the switch footprint in Y,
    with its floor at SLIDE_SLOT_Z_FLOOR."""
    tray = build_tray()
    _, cy = C.pcb_to_case(*C.SW_SLIDE_POS)
    hw = C.SLIDE_SLOT_W / 2
    zf = C.SLIDE_SLOT_Z_FLOOR
    edges_at_slot = (
        tray.edges()
        .filter_by_position(Axis.Y, minimum=cy - hw - 0.5, maximum=cy + hw + 0.5)
        .filter_by_position(Axis.Z, minimum=zf - 0.5, maximum=zf + 3.0)
        .filter_by_position(Axis.X, minimum=0, maximum=C.MCU_HILL_NEG_X_INNER_BOUND_X)
    )
    assert len(edges_at_slot) > 0, "No slot edges found at switch Y — slot may not cut through"


def test_neg_x_wall_flat_at_mcu():
    """No hill: the −X wall over the MCU is flat at MAIN_RIM_Z, not raised."""
    tray = build_tray()
    _, mcu_cy = C.pcb_to_case(*C.MCU_POS)
    edges_at_mcu = (
        tray.edges()
            .filter_by_position(Axis.Y, minimum=mcu_cy - 5, maximum=mcu_cy + 5)
            .filter_by_position(Axis.X, minimum=0, maximum=C.MCU_HILL_NEG_X_INNER_BOUND_X)
    )
    max_z = max((e.bounding_box().max.Z for e in edges_at_mcu), default=0.0)
    assert abs(max_z - C.MAIN_RIM_Z) < 0.2, (
        f"−X wall over MCU top {max_z:.2f} mm != flat rim {C.MAIN_RIM_Z} mm"
    )


def test_no_wall_above_rim():
    """All walls are flat at MAIN_RIM_Z — no feature (hill/ramp/relief) rises above it."""
    tray = build_tray()
    high = tray.edges().filter_by_position(Axis.Z, minimum=C.MAIN_RIM_Z + 0.5, maximum=999)
    assert len(high) == 0, f"{len(high)} edges above the rim — walls are not flat"


def test_slide_slot_clears_plate():
    """Slide-switch slot floor must stay above the PCB seat shelf."""
    assert C.SLIDE_SLOT_Z_FLOOR >= C.PCB_SEAT_Z, (
        f"slide slot floor {C.SLIDE_SLOT_Z_FLOOR} mm < PCB_SEAT_Z {C.PCB_SEAT_Z}"
    )
