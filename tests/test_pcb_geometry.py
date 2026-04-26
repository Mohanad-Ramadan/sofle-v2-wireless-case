"""Tests for PCB polygon loader."""
from sofle_case import constants as C
from sofle_case.pcb_geometry import load_pcb_polygon, polygon_in_case_coords


def test_load_polygon_closed():
    poly = load_pcb_polygon()
    assert len(poly) >= 6
    assert poly[0] == poly[-1]


def test_load_polygon_bbox():
    poly = load_pcb_polygon()
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    assert abs(min(xs) - C.PCB_X_MIN) < 0.05
    assert abs(max(xs) - C.PCB_X_MAX) < 0.05
    assert abs(min(ys) - C.PCB_Y_MIN) < 0.05
    assert abs(max(ys) - C.PCB_Y_MAX) < 0.05


def test_translate_to_case_coords():
    case_poly = polygon_in_case_coords()
    xs = [p[0] for p in case_poly]
    ys = [p[1] for p in case_poly]
    # PCB is centered in case, so polygon should sit fully inside (0..OUTER_*).
    assert min(xs) > 0
    assert max(xs) < C.OUTER_WIDTH
    assert min(ys) > 0
    assert max(ys) < C.OUTER_DEPTH
