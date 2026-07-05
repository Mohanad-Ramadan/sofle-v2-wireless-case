"""Tests for the battery pocket geometry."""
from build123d import Part
from sofle_case import constants as C
from sofle_case.battery import battery_pocket


def test_returns_part():
    assert isinstance(battery_pocket(), Part)


def test_z_range():
    bb = battery_pocket().bounding_box()
    assert abs(bb.min.Z - (C.FLOOR_THICKNESS - C.BATTERY_POCKET_DEPTH)) < 0.01
    assert abs(bb.max.Z - C.FLOOR_THICKNESS) < 0.01


def test_xy_footprint():
    bb = battery_pocket().bounding_box()
    expected_w = C.BATTERY_W + 2 * C.BATTERY_XY_CLEARANCE
    expected_l = C.BATTERY_L + 2 * C.BATTERY_XY_CLEARANCE
    assert abs((bb.max.X - bb.min.X) - expected_w) < 0.01
    assert abs((bb.max.Y - bb.min.Y) - expected_l) < 0.01


def test_centered_on_battery_pos():
    bb = battery_pocket().bounding_box()
    cx, cy = C.pcb_to_case(*C.BATTERY_POCKET_POS)
    assert abs((bb.min.X + bb.max.X) / 2 - cx) < 0.01
    assert abs((bb.min.Y + bb.max.Y) / 2 - cy) < 0.01


def test_clears_all_standoffs():
    """Pocket XY footprint must not overlap any standoff post's lower shoulder."""
    bb = battery_pocket().bounding_box()
    r = C.STANDOFF_OD_LOWER / 2
    for hx, hy in C.MOUNTING_HOLES:
        cx, cy = C.pcb_to_case(hx, hy)
        nx = min(max(cx, bb.min.X), bb.max.X)
        ny = min(max(cy, bb.min.Y), bb.max.Y)
        dist = ((cx - nx) ** 2 + (cy - ny) ** 2) ** 0.5
        assert dist >= r, f"pocket overlaps standoff at ({hx},{hy}): gap {dist:.2f}mm < radius {r}mm"


def test_within_floor_thickness():
    """Pocket depth must not exceed the floor thickness (no through-holes)."""
    assert C.BATTERY_POCKET_DEPTH < C.FLOOR_THICKNESS
