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
    """TOP is a deep tub: its outer skin runs to the ground (min Z = 0), so there is
    no mid-wall seam. It reaches up to the fused bay-canopy ridge (21.9)."""
    from sofle_case import canopy as CAN
    bb = build_top_part(side).bounding_box()
    assert abs(bb.min.Z - 0.0) < 0.01
    assert abs(bb.max.Z - CAN.CANOPY_RIDGE_TOP_Z) < 0.01


def test_pocket_mouth_has_starter_chamfer():
    """The tub pocket MOUTH is chamfered open (tub-side starter): a point just inside
    the seated skirt-inner face is solid skin up in the seated section but chamfered
    to air near the mouth, so the plate rim self-guides in and the mouth can't
    elephant-foot-pinch. Probed on a plain −X wall span."""
    from build123d import Solid
    top = build_top_part("right")
    y = C.OUTER_DEPTH / 2
    # −X wall: outer face, then SEAM_SKIN inward = seated skirt-inner face.
    skin_inner = C.pcb_to_case(0, 0)[0] - C.WALL_THICKNESS - C.PCB_XY_CLEARANCE + C.SEAM_SKIN
    probe_x = skin_inner - 0.15   # 0.15 inside the skin from the seated inner face

    def solid_at(z, s=0.12):
        b = Solid.make_box(s, 3.0, s).translate((probe_x - s / 2, y - 1.5, z - s / 2))
        return (top & b).volume > 1e-6

    assert solid_at(0.7), "seated skirt is missing skin — probe off the wall"
    assert not solid_at(0.1), "pocket mouth is not chamfered — no tub-side starter"


@pytest.mark.parametrize("side", ["right", "left"])
def test_slide_scoop_top_open(side):
    """The wide 'decrement' scoop opens the −X wall over the slide switch: open at the nub and up
    to the rim there, canopy roof intact at the MCU, wall solid beside the scoop, and the BOTTOM
    part untouched. NB the drop-in actuator channel (SLIDE_ACTUATOR_* cavity) intentionally pours
    to the seam in the switch Y-band, so 'solid wall below the scoop floor' is checked BESIDE that
    channel; and the −X shift retains the canopy west-cap inboard of the scoop reach."""
    from build123d import Solid
    import sofle_case.canopy as CAN
    top = build_top_part(side)
    bottom = build_bottom_part(side)

    # −X wall centre at the slide-switch Y (polygon PCB X=0 edge, case X ≈ 10.5).
    sw_cy = C.pcb_to_case(*C.SW_SLIDE_POS)[1]
    wall_cx = C.pcb_to_case(0, 0)[0] - (C.WALL_THICKNESS + C.PCB_XY_CLEARANCE) / 2
    mcu_x, mcu_y = C.pcb_to_case(*C.MCU_POS)
    beside_dy = C.SLIDE_SCOOP_W / 2 + 2.0            # Y outside the scoop entirely (wall intact)
    chan_dy = C.SLIDE_SCOOP_W / 2 - 1.5              # Y inside the scoop but outside the drop-in channel
    if side == "left":
        wall_cx = C.OUTER_WIDTH - wall_cx
        mcu_x = C.OUTER_WIDTH - mcu_x

    def solid_at(part, x, y, z, s=0.5):
        box = Solid.make_box(s, s, s).translate((x - s / 2, y - s / 2, z - s / 2))
        return (part & box).volume > 1e-6

    # The BOTTOM is now a separate inset plate (below the rabbet ledge); the slide
    # features are TOP-only, so the plate floor at the slide Y stays intact. Probe an
    # on-plate point inboard of the inner wall (the skin zone belongs to the tub).
    inboard_x = C.pcb_to_case(0, 0)[0] + 5.0
    if side == "left":
        inboard_x = C.OUTER_WIDTH - inboard_x

    assert not solid_at(top, wall_cx, sw_cy, C.SLIDE_NUB_Z), "scoop not open at the nub"
    assert not solid_at(top, wall_cx, sw_cy, C.MAIN_RIM_Z), "wall not open up to the rim over the nub"
    assert solid_at(top, wall_cx, sw_cy - chan_dy, C.SLIDE_SCOOP_FLOOR_Z - 1.0), "wall not solid below the scoop floor beside the channel"
    assert solid_at(top, mcu_x, mcu_y, CAN._canopy_roof_z(mcu_y) - 0.6), "canopy roof wrongly cut at the MCU"
    assert solid_at(top, wall_cx, sw_cy + beside_dy, C.SLIDE_NUB_Z), "wall bared beside the scoop"
    assert solid_at(bottom, inboard_x, sw_cy, 2.0), "BOTTOM plate floor wrongly cut at the slide switch"


@pytest.mark.parametrize("side", ["right", "left"])
def test_bottom_part_z_range(side):
    """BOTTOM starts at the floor; standoffs rise to their tap tops (PLATE_SEAT_Z),
    so the plate is taller than the rabbet ledge (SEAM_LEDGE_Z) by design."""
    bb = build_bottom_part(side).bounding_box()
    assert abs(bb.min.Z - 0.0) < 0.01
    assert abs(bb.max.Z - C.PLATE_SEAT_Z) < 0.01


@pytest.mark.parametrize("side", ["right", "left"])
def test_split_conserves_volume(side):
    """Top + bottom equals the un-split assembled solid MINUS the intended rabbet
    clearance (the SEAM_FIT_CLEAR / SEAM_LEDGE_CLEAR gap). The difference must be
    positive (material only removed at the seam, never added or double-counted) and
    small — bounded by the thin clearance gap around the plate rim (~0.9%)."""
    from typing import cast
    from sofle_case.tray import build_tray
    from sofle_case.standoffs import stepped_standoff
    from sofle_case.battery import battery_pocket
    from sofle_case.top_cover import build_top_cover
    from sofle_case.case import _encoder_shell, _slide_scoop, _slide_actuator_cavity, _foot_recesses
    from sofle_case.canopy import build_canopy

    ref = build_tray(rim_z=C.COVER_TOP_Z)
    ref = cast(Part, ref + build_top_cover(fuse_margin=C.COVER_FUSE_MARGIN))
    ref = cast(Part, ref + _encoder_shell())
    ref = cast(Part, ref + build_canopy())   # the canopy is fused into the TOP now
    ref = cast(Part, ref - _slide_scoop())   # the slide scoop is cut from the fused TOP
    ref = cast(Part, ref - _slide_actuator_cavity())  # then the switch drop-in pocket
    for hx, hy in C.MOUNTING_HOLES:
        ref = cast(Part, ref + stepped_standoff(at=C.pcb_to_case(hx, hy)))
    ref = cast(Part, ref - battery_pocket())
    ref = cast(Part, ref - _foot_recesses())   # anti-slip feet are cut from the bottom plate

    combined = build_top_part(side).volume + build_bottom_part(side).volume
    lost = ref.volume - combined
    assert lost > 0, "seam added material (double-count) — must only remove clearance"
    assert lost / ref.volume < 0.012, f"seam gap {lost:.1f} exceeds the rabbet clearance"


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
