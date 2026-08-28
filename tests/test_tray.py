"""Tray (shell + cavity) tests."""
from build123d import Part
from sofle_case import constants as C
from sofle_case.tray import outer_south_overhang
from tests.shared_builds import build_tray


def test_returns_part():
    t = build_tray()
    assert isinstance(t, Part)


def test_outer_bbox():
    t = build_tray()
    bb = t.bounding_box()
    assert abs((bb.max.X - bb.min.X) - C.OUTER_WIDTH) < 0.01
    # DEEPER than OUTER_DEPTH now: the three southern runs are grown outward by SOUTH_WALL_EXTRA
    # to give the deep facet something to rake into, and OUTER_DEPTH was left as the datum the
    # seam wave and tent plane are stated in rather than moved to absorb it.
    over = outer_south_overhang()
    assert 0.0 < over <= C.SOUTH_WALL_EXTRA + 0.01, \
        "south skin cannot reach further south than the growth that pushed it"
    assert abs((bb.max.Y - bb.min.Y) - (C.OUTER_DEPTH + over)) < 0.01
    assert abs(bb.max.Y - C.OUTER_DEPTH) < 0.01, "the NORTH edge must not have moved"
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


def test_walls_are_full_thickness():
    """The flat +X wall is WALL_THICKNESS thick: solid just inside the outer face,
    cavity air just past the inner face (tracks WALL_THICKNESS, not a literal)."""
    from build123d import Solid
    t = build_tray()
    y, z = 65.0, C.FLOOR_THICKNESS + 2.0   # +X flat wall region, above the floor, below the chamfer
    x_out = C.OUTER_WIDTH

    def solid(x: float) -> bool:
        p = Solid.make_box(0.4, 0.4, 0.4).translate((x - 0.2, y - 0.2, z - 0.2))
        return (t & p).volume > 1e-6

    assert solid(x_out - (C.WALL_THICKNESS - 1.0)), "+X wall thinner than expected"
    assert not solid(x_out - (C.WALL_THICKNESS + 1.5)), "no cavity behind the +X wall"


def test_outer_top_chamfer_present():
    """The outer-top perimeter carries a chamfer (angled faces up at the rim) while
    the inner cavity rim stays at MAIN_RIM_Z (flush with the plate, nothing above)."""
    t = build_tray()
    angled = [
        f for f in t.faces()
        if 0.1 < abs(f.normal_at().Z) < 0.98
        and f.bounding_box().max.Z > C.MAIN_RIM_Z - 0.1
    ]
    assert len(angled) > 0, "no outer-top chamfer face found"
    assert abs(t.bounding_box().max.Z - C.MAIN_RIM_Z) < 0.01, "chamfer changed rim height"
