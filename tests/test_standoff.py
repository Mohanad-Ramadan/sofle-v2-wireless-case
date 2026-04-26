"""Tests for stepped standoff geometry."""
from build123d import Part
from sofle_case import constants as C
from sofle_case.standoffs import stepped_standoff


def test_returns_part():
    s = stepped_standoff(at=(50.0, 50.0))
    assert isinstance(s, Part)


def test_height():
    s = stepped_standoff(at=(50.0, 50.0))
    bb = s.bounding_box()
    # Standoff goes from FLOOR_THICKNESS (2.0) up to PLATE_SEAT_Z (6.5)
    assert abs(bb.min.Z - C.FLOOR_THICKNESS) < 0.01
    assert abs(bb.max.Z - C.PLATE_SEAT_Z) < 0.01


def test_lower_diameter():
    """At Z just above floor, OD should be STANDOFF_OD_LOWER."""
    s = stepped_standoff(at=(0.0, 0.0))
    bb = s.bounding_box()
    # XY half-extent at the widest cross-section is OD_LOWER/2
    assert abs((bb.max.X - bb.min.X) - C.STANDOFF_OD_LOWER) < 0.01
    assert abs((bb.max.Y - bb.min.Y) - C.STANDOFF_OD_LOWER) < 0.01


def test_centered_at_xy():
    s = stepped_standoff(at=(12.34, 56.78))
    bb = s.bounding_box()
    cx = (bb.min.X + bb.max.X) / 2
    cy = (bb.min.Y + bb.max.Y) / 2
    assert abs(cx - 12.34) < 0.01
    assert abs(cy - 56.78) < 0.01
