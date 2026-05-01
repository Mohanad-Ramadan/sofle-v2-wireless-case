"""Each cutout aligns with its component; clearance ≥ 0.3 mm."""
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
