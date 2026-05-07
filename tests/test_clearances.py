"""Each cutout aligns with its component; clearance ≥ 0.3 mm."""
from build123d import Axis
from sofle_case import constants as C
from sofle_case.cutouts import usb_c_cutout, slide_switch_cutout


def _bb_center(part):
    bb = part.bounding_box()
    return (bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, (bb.min.Z + bb.max.Z) / 2


def test_usb_c_aligns_with_mcu_x():
    cx, _, _ = _bb_center(usb_c_cutout())
    expected, _ = C.pcb_to_case(*C.MCU_POS)
    assert abs(cx - expected) < 0.01


def test_slide_switch_envelops_switch_y():
    """Slot must cover the switch's narrow footprint in Y.  The ramp side
    intentionally overshoots cy-half_wide by a tunable amount (see
    SLIDE_SWITCH_RAMP_TANGENT_SCALARS), which pulls the BB centre several mm
    off the switch centre — so a centre-tolerance check is meaningless here.
    Instead, assert the slot's Y span envelopes [cy-half_narrow, cy+half_narrow],
    the actual functional requirement.
    """
    bb = slide_switch_cutout().bounding_box()
    _, expected = C.pcb_to_case(*C.SW_SLIDE_POS)
    half_narrow = C.SLIDE_SWITCH_W / 2
    assert bb.min.Y <= expected - half_narrow
    assert bb.max.Y >= expected + half_narrow


def test_usb_c_clearance_above_pcb_top():
    """USB-C bottom must clear PCB top by ≥ 0.3 mm (port sits on MCU, MCU sits on PCB)."""
    bb = usb_c_cutout().bounding_box()
    assert bb.min.Z >= C.PCB_TOP_Z + 0.3


def test_mcu_plateau_z():
    """−X wall plateau must reach MCU_HILL_Z above the MCU body Y range."""
    from sofle_case.tray import build_tray
    tray = build_tray()
    _, mcu_cy = C.pcb_to_case(*C.MCU_POS)
    edges_at_mcu = (
        tray.edges()
            .filter_by_position(Axis.Y, minimum=mcu_cy - 5, maximum=mcu_cy + 5)
            .filter_by_position(Axis.X, minimum=0, maximum=6)
    )
    max_z = max((e.bounding_box().max.Z for e in edges_at_mcu), default=0.0)
    assert max_z >= C.MCU_HILL_Z - 0.2, (
        f"MCU plateau top {max_z:.2f} mm < required {C.MCU_HILL_Z} mm"
    )


def test_mcu_hill_not_on_other_walls():
    """All walls except −X must remain at or below MAIN_RIM_Z."""
    from sofle_case.tray import build_tray
    tray = build_tray()
    high_py = (
        tray.edges()
            .filter_by_position(Axis.Y, minimum=C.OUTER_DEPTH - 1.0, maximum=C.OUTER_DEPTH + 1.0)
            .filter_by_position(Axis.Z, minimum=C.MAIN_RIM_Z + 1.0, maximum=999)
    )
    assert len(high_py) == 0, "+Y wall has edges above MAIN_RIM_Z"

    high_px = (
        tray.edges()
            .filter_by_position(Axis.X, minimum=C.OUTER_WIDTH - 1.0, maximum=C.OUTER_WIDTH + 1.0)
            .filter_by_position(Axis.Z, minimum=C.MAIN_RIM_Z + 1.0, maximum=999)
    )
    assert len(high_px) == 0, "+X wall has edges above MAIN_RIM_Z"


def test_mcu_cap_descent_clears_plate():
    """MCU wall cap descends to MAIN_RIM_Z; verify it clears the plate top by ≥ PLATE_RAMP_CLEARANCE."""
    assert C.MAIN_RIM_Z >= C.PLATE_TOP_Z + C.PLATE_RAMP_CLEARANCE, (
        f"MAIN_RIM_Z {C.MAIN_RIM_Z} mm < PLATE_TOP_Z {C.PLATE_TOP_Z} + PLATE_RAMP_CLEARANCE {C.PLATE_RAMP_CLEARANCE}"
    )
