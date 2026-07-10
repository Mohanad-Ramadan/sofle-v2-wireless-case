import pytest
from build123d import Part
from sofle_case import constants as C
from sofle_case.case import build_case_half, build_top_part, build_bottom_part


def test_left_returns_part():
    p = build_case_half("left")
    assert isinstance(p, Part)


def test_left_outer_bbox():
    p = build_case_half("left")
    bb = p.bounding_box()
    assert abs((bb.max.X - bb.min.X) - C.OUTER_WIDTH) < 0.01
    assert abs((bb.max.Y - bb.min.Y) - C.OUTER_DEPTH) < 0.01
    assert abs(bb.min.Z - 0.0) < 0.01
    assert abs(bb.max.Z - C.MAIN_RIM_Z) < 0.01  # flat walls, no hill


def test_left_equals_right():
    """Reversible PCB → single STL serves both halves; geometry is identical."""
    left = build_case_half("left")
    right = build_case_half("right")
    assert abs(left.volume - right.volume) / left.volume < 1e-6
    lbb, rbb = left.bounding_box(), right.bounding_box()
    for a, b in (
        (lbb.min.X, rbb.min.X), (lbb.max.X, rbb.max.X),
        (lbb.min.Y, rbb.min.Y), (lbb.max.Y, rbb.max.Y),
        (lbb.min.Z, rbb.min.Z), (lbb.max.Z, rbb.max.Z),
    ):
        assert abs(a - b) < 1e-6


def test_invalid_side_raises():
    import pytest as _pt
    with _pt.raises(ValueError):
        build_case_half("middle")


# ---------------------------------------------------------------------------
# Sandwich clamshell split (TOP / BOTTOM parts)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("side", ["right", "left"])
def test_split_parts_are_valid_single_solids(side):
    top = build_top_part(side)
    bottom = build_bottom_part(side)
    assert top.is_valid, f"{side} top failed BRepCheck"
    assert bottom.is_valid, f"{side} bottom failed BRepCheck"
    assert len(top.solids()) == 1, f"{side} top has {len(top.solids())} solids"
    assert len(bottom.solids()) == 1, f"{side} bottom has {len(bottom.solids())} solids"


@pytest.mark.parametrize("side", ["right", "left"])
def test_top_part_z_range(side):
    """TOP spans the seam up to the membrane rim (6.25 → 13.5)."""
    bb = build_top_part(side).bounding_box()
    assert abs(bb.min.Z - C.SEAM_Z) < 0.01
    assert abs(bb.max.Z - C.COVER_TOP_Z) < 0.01


@pytest.mark.parametrize("side", ["right", "left"])
def test_bottom_part_z_range(side):
    """BOTTOM starts at the floor; standoffs protrude past the seam to their tap
    tops (PLATE_SEAT_Z), so the part is taller than SEAM_Z by design."""
    bb = build_bottom_part(side).bounding_box()
    assert abs(bb.min.Z - 0.0) < 0.01
    assert abs(bb.max.Z - C.PLATE_SEAT_Z) < 0.01


@pytest.mark.parametrize("side", ["right", "left"])
def test_split_conserves_volume(side):
    """Top + bottom volume equals the un-split assembled solid — no material lost
    or double-counted at the planar seam."""
    from typing import cast
    from sofle_case.tray import build_tray
    from sofle_case.standoffs import stepped_standoff
    from sofle_case.battery import battery_pocket
    from sofle_case.top_cover import build_top_cover

    ref = build_tray(rim_z=C.COVER_TOP_Z)
    ref = cast(Part, ref + build_top_cover(fuse_margin=C.COVER_FUSE_MARGIN))
    for hx, hy in C.MOUNTING_HOLES:
        ref = cast(Part, ref + stepped_standoff(at=C.pcb_to_case(hx, hy)))
    ref = cast(Part, ref - battery_pocket())

    combined = build_top_part(side).volume + build_bottom_part(side).volume
    assert abs(combined - ref.volume) / ref.volume < 1e-6


def test_top_screw_holes_open():
    """M2 clearance holes pass through the membrane at all 5 standoff locations."""
    from build123d import Solid
    top = build_top_part("right")
    for hx, hy in C.MOUNTING_HOLES:
        cx, cy = C.pcb_to_case(hx, hy)
        pin = Solid.make_cylinder(
            C.COVER_SCREW_CLEARANCE_DIA / 2 - 0.1, C.COVER_THICKNESS + 0.2
        ).translate((cx, cy, C.MAIN_RIM_Z - 0.1))
        assert (top & pin).volume < 1e-3, f"screw hole blocked at PCB ({hx}, {hy})"


def test_top_windows_clear_switch_housings():
    """The membrane windows clear every MX top housing (switches poke through)."""
    from sofle_case.switch_phantom import build_switch_phantom
    top = build_top_part("right")
    assert (top & build_switch_phantom()).volume < 1e-3


def test_top_ceiling_closed_over_mcu_switch_column():
    """Regression: the switch column next to the MCU must NOT be open to air.

    The +Y relief widened the cavity up to the new rim, scooping the ceiling open
    across the whole relief; the switch-column side (east of the bay) is now kept
    solid. Probe the ceiling band just under the top face, in the +Y strip beyond
    the switch windows — it must be solid over the switch column (case X≳40) yet
    still OPEN over the MCU bay (case X≲34, where the nice!nano pokes through)."""
    from build123d import Solid
    top = build_top_part("right")

    def solid_at(x, y, z, s=0.3):
        box = Solid.make_box(s, s, s).translate((x - s / 2, y - s / 2, z - s / 2))
        return (top & box).volume > 1e-7

    z = C.COVER_TOP_Z - 0.5  # inside the ceiling band (12.5 → 13.5)
    for y in (120.0, 121.0):  # the +Y strip that was open to air
        for x in (40.0, 46.0, 52.0):  # over the switch column next to the MCU
            assert solid_at(x, y, z), f"ceiling open to air at ({x}, {y}, {z})"
    # …but the MCU bay must stay open (nice!nano clearance)
    assert not solid_at(28.0, 116.0, z), "MCU bay wrongly closed over the nice!nano"


@pytest.mark.parametrize("builder", [build_top_part, build_bottom_part])
def test_split_left_equals_right(builder):
    left, right = builder("left"), builder("right")
    assert abs(left.volume - right.volume) / left.volume < 1e-6
    lbb, rbb = left.bounding_box(), right.bounding_box()
    for a, b in (
        (lbb.min.X, rbb.min.X), (lbb.max.X, rbb.max.X),
        (lbb.min.Y, rbb.min.Y), (lbb.max.Y, rbb.max.Y),
        (lbb.min.Z, rbb.min.Z), (lbb.max.Z, rbb.max.Z),
    ):
        assert abs(a - b) < 1e-6


@pytest.mark.parametrize("builder", [build_top_part, build_bottom_part])
def test_split_invalid_side_raises(builder):
    with pytest.raises(ValueError):
        builder("middle")
