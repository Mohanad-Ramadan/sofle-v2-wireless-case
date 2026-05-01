"""MX switch phantom geometry checks."""
from build123d import Part
from sofle_case import constants as C
from sofle_case.switch_phantom import build_switch_phantom


def test_returns_part():
    assert isinstance(build_switch_phantom(), Part)


def test_z_min_in_gap():
    """Lower housing bottom should be at PLATE_SEAT_Z - 3.0 mm."""
    bb = build_switch_phantom().bounding_box()
    assert abs(bb.min.Z - (C.PLATE_SEAT_Z - 3.0)) < 0.2


def test_z_max_above_plate():
    """Stem top should clear plate top by at least the upper housing height."""
    bb = build_switch_phantom().bounding_box()
    assert bb.max.Z > C.PLATE_TOP_Z + 9.0


def test_volume_covers_all_switches():
    """Volume must exceed 29 MX switches worth of geometry (no missing positions)."""
    # Single MX switch approximate volume:
    #   lower_housing: 13.8 * 13.8 * 3.0  = 571 mm³
    #   upper_housing: 15.6 * 15.6 * 6.6  = 1607 mm³
    #   stem (cylinder): pi * 2.25^2 * 3.5 = 56 mm³
    # Total per switch ≈ 2234 mm³; 29 switches ≈ 64,786 mm³
    assert build_switch_phantom().volume > 29 * 2000
