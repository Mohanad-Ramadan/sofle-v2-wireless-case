from build123d import Part
from sofle_case import constants as C
from sofle_case.cutouts import (
    usb_c_cutout, slide_switch_cutout, reset_pin_cutout, floor_recess,
)


def test_usb_c_returns_part():
    assert isinstance(usb_c_cutout(), Part)


def test_usb_c_at_plus_y_wall():
    bb = usb_c_cutout().bounding_box()
    # Cutout must straddle the +Y outer wall (y = OUTER_DEPTH)
    assert bb.min.Y < C.OUTER_DEPTH < bb.max.Y


def test_usb_c_z_centered():
    bb = usb_c_cutout().bounding_box()
    cz = (bb.min.Z + bb.max.Z) / 2
    assert abs(cz - C.USB_C_Z_CENTER) < 0.01


def test_slide_switch_at_minus_x_wall():
    bb = slide_switch_cutout().bounding_box()
    assert bb.min.X < 0 < bb.max.X


def test_reset_pin_diameter():
    bb = reset_pin_cutout().bounding_box()
    # Cylinder along X; cross-section in YZ plane is the pin diameter.
    assert abs((bb.max.Y - bb.min.Y) - C.RESET_PIN_DIA) < 0.01
    assert abs((bb.max.Z - bb.min.Z) - C.RESET_PIN_DIA) < 0.01


def test_floor_recess_dims():
    bb = floor_recess().bounding_box()
    assert abs((bb.max.X - bb.min.X) - C.SLIDE_SWITCH_RECESS_W) < 0.01
    assert abs((bb.max.Y - bb.min.Y) - C.SLIDE_SWITCH_RECESS_D) < 0.01
    assert abs((bb.max.Z - bb.min.Z) - (C.SLIDE_SWITCH_RECESS_DEPTH + 0.01)) < 0.02
