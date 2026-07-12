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
    """TOP spans the seam up to the encoder plateau top (6.25 → 18.0)."""
    bb = build_top_part(side).bounding_box()
    assert abs(bb.min.Z - C.SEAM_Z) < 0.01
    assert abs(bb.max.Z - C.ENCODER_SHELL_TOP_Z) < 0.01


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
    from sofle_case.case import _encoder_shell

    ref = build_tray(rim_z=C.COVER_TOP_Z)
    ref = cast(Part, ref + build_top_cover(fuse_margin=C.COVER_FUSE_MARGIN))
    ref = cast(Part, ref + _encoder_shell())
    for hx, hy in C.MOUNTING_HOLES:
        ref = cast(Part, ref + stepped_standoff(at=C.pcb_to_case(hx, hy)))
    ref = cast(Part, ref - battery_pocket())

    combined = build_top_part(side).volume + build_bottom_part(side).volume
    # 1e-4 rel tolerates OCC boolean/seam-reassembly float noise from the
    # collar addition; the collar is post-clip so exact conservation is looser.
    assert abs(combined - ref.volume) / ref.volume < 1e-4


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


def test_encoder_bezel_is_hollow_shell():
    """The encoder bezel must be a HOLLOW cap, not a solid block: its cavity
    clears the 12 mm EC11 box, the roof is closed, and only the shaft hole is open."""
    from build123d import Solid
    from sofle_case.case import _encoder_bbox
    top = build_top_part("right")
    enc_cx, enc_cy, _, _ = _encoder_bbox()

    # Cavity is hollow where the encoder box sits (5 mm off-centre, box level).
    box_probe = Solid.make_box(1.0, 1.0, 1.0).translate(
        (enc_cx + 5.0, enc_cy, C.ENCODER_BODY_TOP_Z - 1.0))
    assert (top & box_probe).volume < 1e-3, "bezel is solid where the encoder box must sit"

    # Roof is closed above the box (annulus) 5 mm off-centre, just under the top.
    roof_probe = Solid.make_box(1.0, 1.0, 0.4).translate(
        (enc_cx + 5.0, enc_cy, C.ENCODER_SHELL_TOP_Z - 0.5))
    assert (top & roof_probe).volume > 1e-3, "bezel roof is open — box would be exposed"

    # Shaft hole is open through the roof at the centre.
    shaft_probe = Solid.make_cylinder(
        C.ENCODER_SHAFT_HOLE_DIA / 2 - 0.3, 0.4
    ).translate((enc_cx, enc_cy, C.ENCODER_SHELL_TOP_Z - 0.5))
    assert (top & shaft_probe).volume < 1e-3, "shaft hole is blocked"


def test_encoder_bezel_base_is_plateau_not_box():
    """The plateau leaves the cover as a tangent ogee: the concave foot flares out
    wider than the straight wall. Probe just beyond the wall — solid at the foot
    (bulge), empty at the straight mid-wall."""
    from build123d import Solid
    from sofle_case.case import _encoder_bbox
    top = build_top_part("right")
    enc_cx, enc_cy, bw, _ = _encoder_bbox()
    wall_half = bw / 2 + C.ENCODER_SHELL_CAVITY_CLEAR + C.ENCODER_SHELL_WALL
    # Just past the straight wall — only the flared foot reaches this radius.
    probe_x = enc_cx + wall_half + 0.3

    foot = Solid.make_box(0.4, 0.4, 0.2).translate(
        (probe_x, enc_cy, C.COVER_TOP_Z + 0.15))
    assert (top & foot).volume > 1e-4, "no foot flare — base is a plain box"

    mid_z = (C.COVER_TOP_Z + C.ENCODER_CAVITY_TOP_Z) / 2
    wall = Solid.make_box(0.4, 0.4, 0.3).translate((probe_x, enc_cy, mid_z))
    assert (top & wall).volume < 1e-4, "straight wall as wide as the foot — no ogee flare"


def test_encoder_window_is_exact_cutout():
    """The encoder cover window follows the exact plate cutout (no MX housing
    margin): material remains just past the cutout edge where the enlarged MX
    window would have removed it."""
    from build123d import Solid
    from sofle_case.top_cover import build_top_cover
    from sofle_case.case import _encoder_bbox
    enc_cx, enc_cy, bw, _ = _encoder_bbox()
    cover = build_top_cover()
    # 0.5 mm past the exact cutout edge — inside the old +COVER_WINDOW_OFFSET window.
    probe = Solid.make_box(0.6, 0.6, 0.4).translate(
        (enc_cx + bw / 2 + 0.5, enc_cy, C.MAIN_RIM_Z + 0.3))
    assert (cover & probe).volume > 1e-3, (
        "encoder window is enlarged — should be the exact plate cutout"
    )


def test_top_windows_clear_switch_housings():
    """The membrane windows clear every MX top housing (switches poke through)."""
    from sofle_case.switch_phantom import build_switch_phantom
    top = build_top_part("right")
    assert (top & build_switch_phantom()).volume < 1e-3


def test_top_ceiling_closed_over_mcu_switch_column():
    """Regression: the TOP part's ceiling near the MCU is closed except the
    battery-wire channel over the nice!nano footprint.

    The +Y relief widened the cavity up to the new rim, scooping the ceiling open
    across the whole relief. The ceiling band is now solid on two axes — over the
    switch column (east of the bay) and over the +Y strip toward the USB-C jack —
    leaving open only the MCU/OLED bay over the board, where the wire drops through
    to the seam. Probe the ceiling band just under the top face."""
    from build123d import Solid
    top = build_top_part("right")

    def solid_at(x, y, z, s=0.3):
        box = Solid.make_box(s, s, s).translate((x - s / 2, y - s / 2, z - s / 2))
        return (top & box).volume > 1e-7

    # Probe just above the plate top (below the outer-top chamfer bevel, which
    # legitimately cuts the top-outer edge back at the thin wall).
    z = C.MAIN_RIM_Z + 0.1
    # Switch column next to the MCU must be solid (was open to air).
    for y in (119.0, 120.0):
        for x in (40.0, 46.0, 52.0):
            assert solid_at(x, y, z), f"switch-column ceiling open at ({x}, {y})"
    # The +Y strip toward the USB-C jack (beyond the board's +Y edge ≈118.8) is
    # closed — the jack exits sideways over the wall and needs no ceiling hole.
    for x in (22.0, 26.0, 31.0):
        assert solid_at(x, 120.0, z), f"USB-C +Y strip open at ({x}, 120)"
    # …but the bay over the board stays OPEN as the wire channel down to the seam.
    for x in (22.0, 26.0, 31.0):
        assert not solid_at(x, 110.0, z), f"wire-channel bay wrongly closed at ({x}, 110)"


@pytest.mark.parametrize("builder", [build_top_part, build_bottom_part])
def test_split_left_equals_right(builder):
    left, right = builder("left"), builder("right")
    # 1e-5 rel tolerates OCC mirror/heal float noise; a real asymmetry is far larger.
    assert abs(left.volume - right.volume) / left.volume < 1e-5
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
