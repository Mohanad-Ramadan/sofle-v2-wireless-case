"""Stepped M2 boss geometry."""
from build123d import GeomType, Part, Solid

from sofle_case import constants as C
from sofle_case.standoffs import stepped_standoff


def test_returns_part_and_spans_floor_to_plate():
    boss = stepped_standoff((50.0, 50.0))
    assert isinstance(boss, Part)
    bb = boss.bounding_box()
    assert abs(bb.min.Z - C.FLOOR_THICKNESS) < 0.01
    assert abs(bb.max.Z - C.PLATE_SEAT_Z) < 0.01


def test_lower_diameter():
    boss = stepped_standoff((0.0, 0.0))
    bb = boss.bounding_box()
    assert abs((bb.max.X - bb.min.X) - C.STANDOFF_OD_LOWER) < 0.01
    assert abs((bb.max.Y - bb.min.Y) - C.STANDOFF_OD_LOWER) < 0.01


def test_blind_m2_bore():
    boss = stepped_standoff((50.0, 50.0))
    probe = Solid.make_cylinder(C.STANDOFF_TAP_DIA / 2 - 0.05,
                                C.STANDOFF_BORE_DEPTH - 0.2).translate(
                                    (50.0, 50.0,
                                     C.PLATE_SEAT_Z - C.STANDOFF_BORE_DEPTH + 0.1))
    assert (boss & probe).volume < 0.1 * probe.volume


def test_bore_has_straight_diameter_and_solid_bottom():
    boss = stepped_standoff((0.0, 0.0))
    z_straight = C.PLATE_SEAT_Z - 2.0
    pilot = Solid.make_cylinder(C.STANDOFF_TAP_DIA / 2 - 0.01, 0.4).translate(
        (0.0, 0.0, z_straight))
    assert (boss & pilot).volume < 1e-6
    wall = Solid.make_cylinder(C.STANDOFF_TAP_DIA / 2 + 0.05, 0.4).translate(
        (0.0, 0.0, z_straight))
    assert (boss & wall).volume > 0.0
    below = Solid.make_cylinder(0.5, 0.2).translate(
        (0.0, 0.0, C.PLATE_SEAT_Z - C.STANDOFF_BORE_DEPTH - 0.4))
    assert (boss & below).volume > 0.0


def test_bore_entry_is_conically_chamfered():
    boss = stepped_standoff((0.0, 0.0))
    straight = Solid.make_cylinder(C.STANDOFF_TAP_DIA / 2 + 0.15, 0.05).translate(
        (0.0, 0.0, C.PLATE_SEAT_Z - 0.8))
    entry_clear = Solid.make_cylinder(C.STANDOFF_TAP_DIA / 2 + 0.1, 0.05).translate(
        (0.0, 0.0, C.PLATE_SEAT_Z - 0.2))
    entry_wide = Solid.make_cylinder(C.STANDOFF_TAP_DIA / 2 + C.STANDOFF_BORE_CHAMFER - 0.05, 0.05).translate(
        (0.0, 0.0, C.PLATE_SEAT_Z - 0.2))
    assert (boss & straight).volume > 0.0
    assert (boss & entry_clear).volume < 1e-6
    assert (boss & entry_wide).volume > 0.0
    assert any(face.geom_type is GeomType.CONE for face in boss.faces())


def test_all_five_case_locations_use_flush_bosses():
    for hole in C.MOUNTING_HOLES:
        x, y = C.pcb_to_case(*hole)
        boss = stepped_standoff((x, y))
        assert abs(boss.bounding_box().max.Z - C.PLATE_SEAT_Z) < 0.01


def test_centered_at_xy():
    boss = stepped_standoff((12.34, 56.78))
    bb = boss.bounding_box()
    assert abs((bb.min.X + bb.max.X) / 2 - 12.34) < 0.01
    assert abs((bb.min.Y + bb.max.Y) / 2 - 56.78) < 0.01
