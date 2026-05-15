"""Each cutout aligns with its component; clearance ≥ 0.3 mm."""
from build123d import Axis
from sofle_case import constants as C
from sofle_case.cutouts import usb_c_cutout


def _bb_center(part):
    bb = part.bounding_box()
    return (bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, (bb.min.Z + bb.max.Z) / 2


def test_usb_c_aligns_with_mcu_x():
    cx, _, _ = _bb_center(usb_c_cutout())
    expected, _ = C.pcb_to_case(*C.MCU_POS)
    assert abs(cx - expected) < 0.01


def test_slot_envelops_switch_y():
    """Tray slot must cover the switch's narrow footprint in Y around switch Z range."""
    from sofle_case.tray import build_tray
    tray = build_tray()
    _, cy = C.pcb_to_case(*C.SW_SLIDE_POS)
    hn = C.SLIDE_SWITCH_W / 2
    z_lo = C.SLIDE_SWITCH_Z_RANGE[0]
    z_bot = z_lo - hn
    edges_at_slot = (
        tray.edges()
        .filter_by_position(Axis.Y, minimum=cy - hn - 0.5, maximum=cy + hn + 0.5)
        .filter_by_position(Axis.Z, minimum=z_bot - 0.5, maximum=z_lo + 0.5)
        .filter_by_position(Axis.X, minimum=0, maximum=C.MCU_HILL_NEG_X_INNER_BOUND_X)
    )
    assert len(edges_at_slot) > 0, "No slot edges found at switch Y/Z — slot may not cut through"


def test_usb_c_clearance_above_pcb_top():
    """USB-C bottom must clear PCB top by ≥ 0.3 mm (port sits on MCU, MCU sits on PCB)."""
    bb = usb_c_cutout().bounding_box()
    assert bb.min.Z >= C.PCB_TOP_Z + 0.3


def test_mcu_plateau_z():
    """−X wall plateau must reach MCU_HILL_Z above the MCU body Y range.
    Wall ring spans X≈8.5..12.0 (polygon-offset), so probe X up to inner bound."""
    from sofle_case.tray import build_tray
    tray = build_tray()
    _, mcu_cy = C.pcb_to_case(*C.MCU_POS)
    edges_at_mcu = (
        tray.edges()
            .filter_by_position(Axis.Y, minimum=mcu_cy - 5, maximum=mcu_cy + 5)
            .filter_by_position(Axis.X, minimum=0, maximum=C.MCU_HILL_NEG_X_INNER_BOUND_X)
    )
    max_z = max((e.bounding_box().max.Z for e in edges_at_mcu), default=0.0)
    assert max_z >= C.MCU_HILL_Z - 0.2, (
        f"MCU plateau top {max_z:.2f} mm < required {C.MCU_HILL_Z} mm"
    )


def test_mcu_hill_not_on_other_walls():
    """−Y and +X walls stay at MAIN_RIM_Z; +Y wall raised only in MCU footprint region."""
    from sofle_case.tray import build_tray
    tray = build_tray()
    threshold = C.MAIN_RIM_Z + 1.0

    high_ny = (
        tray.edges()
            .filter_by_position(Axis.Y, minimum=-1.0, maximum=1.0)
            .filter_by_position(Axis.Z, minimum=threshold, maximum=999)
    )
    assert len(high_ny) == 0, "−Y wall has unexpected edges above MAIN_RIM_Z"

    high_px = (
        tray.edges()
            .filter_by_position(Axis.X, minimum=C.OUTER_WIDTH - 1.0, maximum=C.OUTER_WIDTH + 1.0)
            .filter_by_position(Axis.Z, minimum=threshold, maximum=999)
    )
    assert len(high_px) == 0, "+X wall has unexpected edges above MAIN_RIM_Z"

    # Outer +Y face at MCU X column sits at Y≈116.5 (polygon-offset of stepped top edge),
    # not OUTER_DEPTH=121.5 — probe from inner bound up to OUTER_DEPTH.
    high_py_mcu = (
        tray.edges()
            .filter_by_position(Axis.Y, minimum=C.MCU_HILL_PLUS_Y_INNER_BOUND_Y, maximum=C.OUTER_DEPTH + 1.0)
            .filter_by_position(Axis.X, minimum=0.0, maximum=C.MCU_HILL_PLUS_Y_REACH_X + 2.0)
            .filter_by_position(Axis.Z, minimum=threshold, maximum=999)
    )
    assert len(high_py_mcu) > 0, "+Y wall MCU region has no edges above MAIN_RIM_Z — hill missing"


def test_mcu_cap_descent_clears_plate():
    """−Y ramp lowest point must stay above the PCB seat shelf."""
    z_bot = C.SLIDE_SWITCH_Z_RANGE[0] - C.SLIDE_SWITCH_W / 2
    assert z_bot >= C.PCB_SEAT_Z, (
        f"−Y ramp z_bot {z_bot} mm < PCB_SEAT_Z {C.PCB_SEAT_Z}"
    )
