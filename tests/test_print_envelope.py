"""Each half must fit a 250×210mm FDM bed."""
from sofle_case.case import build_case_half

BED_X = 250.0
BED_Y = 210.0


def test_left_fits_bed():
    bb = build_case_half("left").bounding_box()
    assert (bb.max.X - bb.min.X) <= BED_X
    assert (bb.max.Y - bb.min.Y) <= BED_Y


def test_right_fits_bed():
    bb = build_case_half("right").bounding_box()
    assert (bb.max.X - bb.min.X) <= BED_X
    assert (bb.max.Y - bb.min.Y) <= BED_Y
