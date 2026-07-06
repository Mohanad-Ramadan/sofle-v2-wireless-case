"""Tray (shell + cavity) tests."""
from build123d import Part
from sofle_case import constants as C
from sofle_case.tray import build_tray


def test_returns_part():
    t = build_tray()
    assert isinstance(t, Part)


def test_outer_bbox():
    t = build_tray()
    bb = t.bounding_box()
    assert abs((bb.max.X - bb.min.X) - C.OUTER_WIDTH) < 0.01
    assert abs((bb.max.Y - bb.min.Y) - C.OUTER_DEPTH) < 0.01
    assert abs(bb.min.Z - 0.0) < 0.01
    assert abs(bb.max.Z - C.MAIN_RIM_Z) < 0.01  # flat walls, no hill


def test_volume_smaller_than_solid_box():
    """Hollow tray < solid box of the same outer dims."""
    t = build_tray()
    solid_vol = C.OUTER_WIDTH * C.OUTER_DEPTH * C.MAIN_RIM_Z
    assert t.volume < solid_vol * 0.7


def test_tray_is_single_solid():
    """Shell + relief bump/widen must fuse into one continuous solid — guards
    against a disconnected floating ridge at the +Y relief."""
    t = build_tray()
    assert len(t.solids()) == 1, f"tray has {len(t.solids())} solids; expected 1 fused solid"
