from build123d import Part
from sofle_case import constants as C
from sofle_case.case import build_case_half


def test_left_returns_part():
    p = build_case_half("left")
    assert isinstance(p, Part)


def test_left_outer_bbox():
    p = build_case_half("left")
    bb = p.bounding_box()
    assert abs((bb.max.X - bb.min.X) - C.OUTER_WIDTH) < 0.01
    assert abs((bb.max.Y - bb.min.Y) - C.OUTER_DEPTH) < 0.01
    assert abs(bb.min.Z - 0.0) < 0.01
    assert abs(bb.max.Z - C.MCU_COVER_Z) < 0.01


def test_right_is_mirror_of_left():
    left = build_case_half("left")
    right = build_case_half("right")
    # Volumes equal within float tolerance
    assert abs(left.volume - right.volume) / left.volume < 1e-3


def test_invalid_side_raises():
    import pytest as _pt
    with _pt.raises(ValueError):
        build_case_half("middle")
