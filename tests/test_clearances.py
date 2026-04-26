"""Each cutout aligns with its component; clearance ≥ 0.3 mm."""
from sofle_case import constants as C
from sofle_case.cutouts import (
    usb_c_cutout, slide_switch_cutout, reset_pin_cutout,
)


def _bb_center(part):
    bb = part.bounding_box()
    return (bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, (bb.min.Z + bb.max.Z) / 2


def test_usb_c_aligns_with_mcu_x():
    cx, _, _ = _bb_center(usb_c_cutout())
    expected, _ = C.pcb_to_case(*C.MCU_POS)
    assert abs(cx - expected) < 0.01


def test_slide_switch_aligns_with_sw31_y():
    _, cy, _ = _bb_center(slide_switch_cutout())
    _, expected = C.pcb_to_case(*C.SW_SLIDE_POS)
    assert abs(cy - expected) < 0.01


def test_reset_aligns_with_rsw1_y():
    _, cy, cz = _bb_center(reset_pin_cutout())
    _, expected = C.pcb_to_case(*C.SW_RESET_POS)
    assert abs(cy - expected) < 0.01
    assert abs(cz - C.RESET_Z_CENTER) < 0.01


def test_usb_c_clearance_above_pcb_top():
    """USB-C bottom must clear PCB top by ≥ 0.3 mm (port sits on MCU, MCU sits on PCB)."""
    bb = usb_c_cutout().bounding_box()
    assert bb.min.Z >= C.PCB_TOP_Z + 0.3
