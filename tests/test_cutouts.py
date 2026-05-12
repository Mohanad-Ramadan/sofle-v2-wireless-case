from build123d import Part
from sofle_case import constants as C
from sofle_case.cutouts import usb_c_cutout


def test_usb_c_returns_part():
    assert isinstance(usb_c_cutout(), Part)


def test_usb_c_at_plus_y_wall():
    bb = usb_c_cutout().bounding_box()
    assert bb.min.Y < C.OUTER_DEPTH < bb.max.Y


def test_usb_c_bottom_matches_z_range():
    """Slot bottom matches USB_C_Z_RANGE[0] — just below the nice!nano USB-C jack lip."""
    bb = usb_c_cutout().bounding_box()
    assert abs(bb.min.Z - C.USB_C_Z_RANGE[0]) < 0.01


def test_usb_c_top_punches_past_rim():
    """Slot top must extend past wall rim so it is open to air on a single STL."""
    bb = usb_c_cutout().bounding_box()
    assert bb.max.Z > C.MAIN_RIM_Z


def test_usb_c_reaches_mcu_in_y():
    """Cutout min.Y must reach at least to the MCU's +Y body edge (case Y ≈ 118.5)."""
    bb = usb_c_cutout().bounding_box()
    mcu_cx, mcu_cy = C.pcb_to_case(*C.MCU_POS)
    # nice!nano body is ~33 mm long; +Y edge ≈ MCU centre + 16.5 mm
    mcu_y_edge = mcu_cy + 16.5
    assert bb.min.Y <= mcu_y_edge


def test_neg_x_wall_cutter_plus_y_returns_part():
    from sofle_case.tray import _neg_x_wall_cutter_plus_y
    assert isinstance(_neg_x_wall_cutter_plus_y(), Part)


def test_neg_x_wall_cutter_minus_y_returns_part():
    from sofle_case.tray import _neg_x_wall_cutter_minus_y
    assert isinstance(_neg_x_wall_cutter_minus_y(), Part)
