"""Tests for the battery pocket geometry (deep pocket for a real 405070 cell)."""
from build123d import Part

from sofle_case import constants as C
from sofle_case.battery import battery_pocket


def test_returns_part():
    assert isinstance(battery_pocket(), Part)


def test_z_range():
    """Blind pocket: top at the floor top, bottom at FLOOR_THICKNESS − POCKET_DEPTH."""
    bb = battery_pocket().bounding_box()
    assert abs(bb.min.Z - (C.FLOOR_THICKNESS - C.BATTERY_POCKET_DEPTH)) < 0.01
    assert abs(bb.max.Z - C.FLOOR_THICKNESS) < 0.01


def test_xy_footprint():
    """Fit a 50 × 72 mm protected cell without squeezing its circuit."""
    bb = battery_pocket().bounding_box()
    assert abs(bb.size.X - 51.0) < 0.01
    assert abs(bb.size.Y - 73.0) < 0.01


def test_center_shifted_east():
    """Pocket center is shifted +BATTERY_POCKET_SHIFT_X (east) from the nominal position."""
    bb = battery_pocket().bounding_box()
    cx, cy = C.pcb_to_case(C.BATTERY_POCKET_POS[0] + C.BATTERY_POCKET_SHIFT_X,
                           C.BATTERY_POCKET_POS[1])
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


def test_solid_base_beneath():
    """BATTERY_FLOOR_BASE of solid floor remains beneath the pocket."""
    assert abs((C.FLOOR_THICKNESS - C.BATTERY_POCKET_DEPTH) - C.BATTERY_FLOOR_BASE) < 1e-9
    assert C.BATTERY_POCKET_DEPTH < C.FLOOR_THICKNESS


def test_socket_clearance_regression():
    """The whole reason for the redesign: a design-thickness cell + Z clearance must clear
    the hotswap socket underside (2 mm below the PCB). Guards against future floor edits."""
    pocket_floor = C.FLOOR_THICKNESS - C.BATTERY_POCKET_DEPTH
    battery_top = pocket_floor + C.BATTERY_THICKNESS
    socket_under = C.PCB_SEAT_Z - 2.0
    assert battery_top + C.BATTERY_Z_CLEARANCE <= socket_under + 1e-6, (
        f"battery top {battery_top} + clr {C.BATTERY_Z_CLEARANCE} exceeds socket underside {socket_under}"
    )


def test_continuous_wire_retention_and_slack_clearance():
    from itertools import pairwise

    from sofle_case.battery import jst_channel_path, jst_wire_channel

    cutter = jst_wire_channel()
    for (x0, y0), (x1, y1) in pairwise(jst_channel_path()):
        length = abs(x1 - x0) + abs(y1 - y0)
        for step in range(3, int(length) - 2):
            t = step / length
            x, y = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
            # Full-height top insertion slot; wider cavity below stores slack.
            assert cutter.is_inside((x, y, C.FLOOR_THICKNESS - 0.2))
            for offset in (-1.1, 1.1):
                sx = x + (offset if x0 == x1 else 0)
                sy = y + (offset if y0 == y1 else 0)
                assert not cutter.is_inside((sx, sy, C.FLOOR_THICKNESS - 0.2))
                assert cutter.is_inside((sx, sy, C.JST_CHANNEL_FLOOR_Z + 2.5))


def test_wire_slot_remains_open_at_turns():
    from sofle_case.battery import jst_channel_path, jst_wire_channel

    cutter = jst_wire_channel()
    for x, y in jst_channel_path()[1:-1]:
        assert cutter.is_inside((x, y, C.FLOOR_THICKNESS - 0.2))
