import pytest
from build123d import Part
from sofle_case import constants as C
from tests.shared_builds import build_bottom_part, build_case_half, build_top_part


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
    """TOP is a deep tub whose outer skin runs unbroken to the ground — no mid-wall seam.

    'The ground' is no longer Z=0 over the southern stretch: the skin carries on down to
    TENT_SKIRT_LIFT above the tent plane there, so the front reads as one piece over a thin
    reveal and the bottom wedge only shows properly further north. Its deepest point is
    therefore that lifted run at TENT_SEAM_Y1. Above Z=0 nothing moved — the ceiling is still
    the fused bay-canopy ridge, now THIS half's own (the ridge is derived per half, so left tops
    out 2.76 mm lower than right)."""
    from sofle_case import canopy as CAN
    from sofle_case.case import seam_profile_min_z
    # NOT tent_ground_z(y1) + lift. That is where the southern RUN ends; the sweep leaves it
    # tangentially and so keeps descending a little further before it climbs. seam_profile_min_z
    # is the profile's real minimum and the tolerance can be tight because of it.
    want = seam_profile_min_z()
    bb = build_top_part(side).bounding_box()
    assert abs(bb.min.Z - want) < 0.005, \
        f"tub floor at {bb.min.Z:.4f}, expected the seam profile's minimum {want:.4f}"
    assert abs(bb.max.Z - CAN.canopy_ridge_top_z(side)) < 0.01


def test_pocket_mouth_has_starter_chamfer():
    """The tub pocket MOUTH is chamfered open (tub-side starter): a point just inside
    the seated skirt-inner face is solid skin up in the seated section but chamfered
    to air near the mouth, so the plate rim self-guides in and the mouth can't
    elephant-foot-pinch. Probed on a plain −X wall span."""
    from build123d import Solid

    # Borrowed rather than duplicated: this is the same curve, and a second crossing-finder here
    # would be one more thing to keep in step with the wave.
    from tests.test_seam import _zero_crossings
    top = build_top_part("right")
    # DERIVED, NOT HARD-CODED, and it had to become so. The station must satisfy three things at
    # once: a PLAIN −X wall span (the MCU hill and slide scoop own roughly y=72..104, where there
    # is no skin to probe at this depth), SOUTH of the +Y relief bump at y=115 (north of it the
    # wall is pushed out and its inner face is not the nominal offset computed below), and inside
    # the REAR-SKIRT stretch where the parting line has dropped back under Z=0 — which is the case
    # the mouth clamp below exists for.
    #
    # y=110 satisfied all three until the wave grew its shoulder. Holding the line high past the
    # crest moved the second Z=0 crossing from y≈108.9 back to y≈113.3, so y=110 is now ABOVE the
    # line, its skin is cut away, and the test failed on a geometry that is perfectly correct.
    # The window is real but narrow (≈1.7 mm), so it is computed and asserted rather than guessed,
    # and the probe is sized to fit inside it.
    BUMP_Y = 115.0
    zc = _zero_crossings()[1]
    lo, hi = zc + 0.3, BUMP_Y - 0.3
    assert hi - lo > 0.6, (
        f"the rear-skirt window has closed to {hi - lo:.2f} mm (crossing y={zc:.2f}, bump "
        f"y={BUMP_Y}). There is nowhere left on a plain wall to probe the mouth from below the "
        f"parting line — widen it or move the probe north of the bump and measure the wall")
    y = (lo + hi) / 2.0
    depth = min(3.0, hi - lo)
    # −X wall: outer face, then SEAM_SKIN inward = seated skirt-inner face.
    skin_inner = C.pcb_to_case(0, 0)[0] - C.WALL_THICKNESS - C.PCB_XY_CLEARANCE + C.SEAM_SKIN
    probe_x = skin_inner - 0.15   # 0.15 inside the skin from the seated inner face

    def solid_at(z, s=0.12):
        b = Solid.make_box(s, depth, s).translate((probe_x - s / 2, y - depth / 2, z - s / 2))
        return (top & b).volume > 1e-6

    # Measured from the MOUTH, not from Z=0, because the mouth moves with the parting line —
    # a fixed 0.7/0.1 pair would probe empty space below the line entirely.
    #
    # CLAMPED AT ZERO, and that is the part the negative dial changed. The mouth is the pocket's
    # own chamfered edge at Z=0; the parting line can only take it HIGHER, by cutting the skin
    # back up the wall. When the line drops BELOW Z=0 — the rear skirt — the skin descends past
    # the mouth and the mouth stays where the pocket put it.
    mouth_z = max(0.0, C.SEAM_NORTH_RISE_Z)
    assert solid_at(mouth_z + C.SEAM_LEAD_IN + 0.3), "seated skirt is missing skin — probe off the wall"
    assert not solid_at(mouth_z + 0.1), "pocket mouth is not chamfered — no tub-side starter"


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
    assert solid_at(top, mcu_x, mcu_y, CAN._canopy_roof_z(mcu_y, CAN.canopy_ridge_top_z(side)) - 0.6), \
        "canopy roof wrongly cut at the MCU"
    assert solid_at(top, wall_cx, sw_cy + beside_dy, C.SLIDE_NUB_Z), "wall bared beside the scoop"
    assert solid_at(bottom, inboard_x, sw_cy, 2.0), "BOTTOM plate floor wrongly cut at the slide switch"


@pytest.mark.parametrize("side", ["right", "left"])
def test_bottom_part_z_range(side):
    """BOTTOM runs from the tent wedge's deepest point up to the standoff tap tops.

    The floor is no longer Z=0: the bottom case now carries the tent wedge, which hangs
    TENT_WEDGE_MAX_H below the old bottom face at the north and TENT_WEDGE_MIN_H at the
    south. The top is the standoff pin tops, which now stop STANDOFF_PIN_RECESS BELOW
    PLATE_SEAT_Z — the plate is located by the switches, not by the pins — so the part is
    taller than the rabbet ledge by design but no longer reaches the plate."""
    import math
    bb = build_bottom_part(side).bounding_box()
    # A hair above the nominal deep end: the elephant-foot counter-chamfer trims the ground
    # rim inboard by BOTTOM_CHAMFER, and 0.5 mm inboard on a 2 deg plane lifts the deepest
    # surviving point by 0.5*tan(2 deg) ~ 0.017 mm. Never below, though.
    # bottom_deep_z(), not wedge_deep_z(): the flared band reaches past the tub's skin, so the
    # part's footprint runs ~3.7 mm further north than the wedge's and the desk is lower there.
    from sofle_case.case import bottom_deep_z
    lift = C.BOTTOM_CHAMFER * math.tan(math.radians(C.TENT_ANGLE_DEG))
    assert bottom_deep_z() <= bb.min.Z <= bottom_deep_z() + lift + 1e-3, \
        f"floor at {bb.min.Z:.4f}, expected the wedge's deep end {wedge_deep_z():.4f}"
    assert abs(bb.max.Z - (C.PLATE_SEAT_Z - C.STANDOFF_PIN_RECESS)) < 0.01


@pytest.mark.parametrize("side", ["right", "left"])
def test_split_conserves_volume(side):
    """Top + bottom equals the un-split assembled solid MINUS the intended rabbet
    clearance (the SEAM_FIT_CLEAR / SEAM_LEDGE_CLEAR gap). The difference must be
    positive (material only removed at the seam, never added or double-counted) and
    small — bounded by the thin clearance gap around the plate rim (~0.9%)."""
    from typing import cast
    from tests.shared_builds import build_tray
    from sofle_case.standoffs import stepped_standoff
    from sofle_case.battery import battery_pocket, jst_pocket, jst_wire_channel
    from tests.shared_builds import build_top_cover
    from sofle_case.case import (_encoder_shell, _slide_scoop, _slide_actuator_cavity,
                                 _foot_recesses, tent_wedge, skirt_extension, seam_skirt_tub,
                                 _bottom_outer_shell, _plate_pocket, _below_seam_cutter)
    from tests.shared_builds import build_canopy
    from sofle_case.snaps import snap_reliefs, snap_barbs

    ref = build_tray(rim_z=C.COVER_TOP_Z, bottom_chamfer=False)
    # Both parts now carry material below Z=0 that exists in no other build: the BOTTOM's tent
    # wedge, and the TOP's skin extension over the southern stretch. Without them here the
    # split looks like it invented ~50 cm^3 and the sign check below fires.
    ref = cast(Part, ref + tent_wedge())
    ref = cast(Part, ref + skirt_extension(seam_skirt_tub()))
    # ...and the flared band outboard of the wedge, which is the third thing that exists in
    # neither the tray nor the cover. Without it the split looks like it invented ~8 cm^3.
    ref = cast(Part, ref + _bottom_outer_shell())
    ref = cast(Part, ref + build_top_cover(fuse_margin=C.COVER_FUSE_MARGIN))
    ref = cast(Part, ref + _encoder_shell())
    ref = cast(Part, ref + build_canopy())   # the canopy is fused into the TOP now
    ref = cast(Part, ref - _slide_scoop())   # the slide scoop is cut from the fused TOP
    ref = cast(Part, ref - _slide_actuator_cavity())  # then the switch drop-in pocket
    for hx, hy in C.MOUNTING_HOLES:
        ref = cast(Part, ref + stepped_standoff(at=C.pcb_to_case(hx, hy)))
    ref = cast(Part, ref - battery_pocket())
    # The JST pocket and its wire channel are floor recesses like the battery's. Omitting them
    # here does not fail as "missing pocket" — it fails as a 2939 mm³ SEAM GAP, because this test
    # can only see the difference between the reference and the split halves, not where it came
    # from. Any future floor recess has to be added here too or it will masquerade as seam loss.
    ref = cast(Part, ref - jst_pocket())
    ref = cast(Part, ref - jst_wire_channel())
    ref = cast(Part, ref - _foot_recesses())   # anti-slip feet are cut from the bottom plate
    # The snap latches are the same kind of bookkeeping as the floor recesses above: the reliefs
    # are a void cut from the bottom and the barbs are material added to it, so both have to be
    # named here or the net (-4226 mm³) masquerades as the seam having eaten 2.2% of the case.
    # Order matters here as it does in build_bottom_part — a barb fuses onto a rim the reliefs
    # have already opened, so cutting second would put back material the slot removed.
    ref = cast(Part, ref - snap_reliefs())
    ref = cast(Part, ref + snap_barbs())

    # The RECESS is a void by design, not a seam gap: north of the sweep the parting line rides
    # up to SEAM_NORTH_RISE_Z and the tub's skin below it is carved away, with nothing put back
    # (the bottom stays inset — see the constants block). The un-split solid still has that
    # material, so it has to be named here or it reads as the seam having eaten 1.7% of the case.
    # Measured, not asserted: exactly what the parting profile takes off the tub.
    tub = cast(Part, build_tray(rim_z=C.COVER_TOP_Z, bottom_chamfer=False) - _plate_pocket())
    recess = tub.volume - cast(Part, tub - _below_seam_cutter()).volume

    combined = build_top_part(side).volume + build_bottom_part(side).volume
    lost = ref.volume - combined - recess
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


def test_encoder_window_matches_the_plateau_cavity():
    """The encoder window is the plate cutout grown by ``ENCODER_SHELL_CAVITY_CLEAR``, so
    the membrane window and the plateau's internal cavity are ONE aperture — no step, and
    no MX-housing margin either (it is not an MX switch).

    It used to be the EXACT cutout, on the grounds that the EC11 body already passes
    through that opening. It does in FR4; a printed copy of it does not — the cutout is
    only 0.07 mm/side clear of the 12.4 mm body on its −Y face, and printed holes come out
    undersize. The window sits entirely under the 16.5 mm plateau, so the old value bought
    invisibility that was already free and paid for it in a pinch."""
    from build123d import Solid
    from tests.shared_builds import build_top_cover
    from sofle_case.top_cover import _load_plate_cutouts, _is_encoder_cutout
    clr = C.ENCODER_SHELL_CAVITY_CLEAR
    edge_x = cy = None
    for cut in _load_plate_cutouts():
        pts = [C.pcb_to_case(x, y) for x, y in cut]
        if len(pts) >= 3 and _is_encoder_cutout(pts):
            edge_x = max(q[0] for q in pts)
            cy = sum(q[1] for q in pts) / len(pts)
            break
    assert edge_x is not None, "encoder cutout not found"
    cover = build_top_cover()

    def probe(x: float) -> float:
        b = Solid.make_box(0.2, 0.2, 0.4).translate(
            (x - 0.1, cy - 0.1, C.MAIN_RIM_Z + C.COVER_THICKNESS / 2 - 0.2))
        return (cover & b).volume

    assert probe(edge_x + clr - 0.2) < 1e-4, (
        "encoder window is narrower than the plateau cavity — it will pinch the EC11 body")
    assert probe(edge_x + clr + 0.3) > 1e-4, (
        "encoder window is wider than the plateau cavity — the plateau wall loses its seat")


def test_encoder_plateau_clears_the_ec11_body():
    """The plateau must pass DOWN over the EC11's proud 12.4 mm box, not land on it.

    Regression, and it is the defect that made the printed case unassemblable with the
    keyboard inside. ``_encoder_shell`` picked the R3.0 plan round-over by edge length
    alone, which also caught the CAVITY's four vertical corners (4.2 mm tall). Rounding a
    concave corner refills it: the cavity corners came back to 8.32 mm from the encoder
    centre against the body's 8.77 mm — 0.45 mm of interference on each of the four
    corners, over the box's whole proud height (Z 15.0 → 17.0), 2.03 mm³ measured on the
    built TOP. The plateau sat on the encoder and held the entire TOP off the switch
    plate, so the shell seated at the north OR the south and rocked about it while the
    empty shells mated perfectly.

    Nothing caught it: every other encoder test probes the roof, the shaft hole or the
    ogee foot — none of them the box the plateau exists to clear."""
    from build123d import Solid
    from sofle_case.encoder_phantom import BODY_W, BODY_H
    top = build_top_part("right")
    ex, ey = C.pcb_to_case(*C.SW_ENCODER_POS)
    body = Solid.make_box(BODY_W, BODY_W, BODY_H).translate(
        (ex - BODY_W / 2, ey - BODY_W / 2, C.PCB_TOP_Z))
    assert (top & body).volume < 1e-3, (
        "encoder plateau intersects the EC11 body — the TOP cannot seat on the plate")


def test_encoder_plateau_outer_corners_stay_rounded():
    """The radial filter that spared the CAVITY corners must not have spared the OUTER
    ones — the rounded-rectangle plan is the plateau's whole style, and a filter that
    caught nothing would pass the clearance test above for the wrong reason."""
    from build123d import Solid
    from sofle_case.case import _encoder_bbox
    top = build_top_part("right")
    ex, ey, bw, bh = _encoder_bbox()
    half_x = bw / 2 + C.ENCODER_SHELL_CAVITY_CLEAR + C.ENCODER_SHELL_WALL
    half_y = bh / 2 + C.ENCODER_SHELL_CAVITY_CLEAR + C.ENCODER_SHELL_WALL
    # Straight-wall band: clear of the ogee foot below and the top round-over above.
    z = C.COVER_TOP_Z + C.ENCODER_BEZEL_FOOT_R + 0.5
    assert z < C.ENCODER_SHELL_TOP_Z - C.ENCODER_BEZEL_TOP_R, "probe Z is inside a blend"
    corner = Solid.make_box(0.4, 0.4, 0.3).translate(
        (ex + half_x - 0.5, ey + half_y - 0.5, z))
    assert (top & corner).volume < 1e-4, (
        "outer plateau corner is square — the plan round-over was lost")


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


def test_split_bottom_left_equals_right():
    """The BOTTOM plate carries no MCU features, so it stays a strict mirror — one STL
    serves both halves."""
    left, right = build_bottom_part("left"), build_bottom_part("right")
    # 1e-5 rel tolerates OCC mirror/heal float noise; a real asymmetry is far larger.
    assert abs(left.volume - right.volume) / left.volume < 1e-5
    lbb, rbb = left.bounding_box(), right.bounding_box()
    # 1e-5 on the box, raised from 1e-6 when the tent went 3 deg -> 7 deg. The deeper wedge gives
    # OCC's mirror/heal more geometry to accumulate noise over and the X pair went to 2.9e-6.
    # Verified as noise and not asymmetry before the number was touched: minX and maxX shift by
    # the SAME 2.9e-6 (a rigid translation of the mirrored copy, not a change of size), the
    # volumes agree to 5e-8 relative, and Y and Z are bit-identical. A real asymmetry moves one
    # edge and not the other, and shows in the volume first.
    # X IS COMPARED MIRRORED, the others directly. The left half is the right one reflected about
    # x = OUTER_WIDTH/2, so its min.X pairs with the right's MAX.X, not its min. Comparing them
    # straight only ever worked because the old bottom happened to be bbox-symmetric about that
    # line: it was a plain offset of the outline, inset the same 2.2 mm all round. The flared
    # band is not — it exists only north of where the reveal opens, and the outline is narrower
    # there — so the box is now 2.20..155.45 and a direct comparison reports a 3.6 mm asymmetry
    # that is really just the mirror working correctly.
    for a, b in (
        (lbb.min.X, C.OUTER_WIDTH - rbb.max.X), (lbb.max.X, C.OUTER_WIDTH - rbb.min.X),
        (lbb.min.Y, rbb.min.Y), (lbb.max.Y, rbb.max.Y),
        (lbb.min.Z, rbb.min.Z), (lbb.max.Z, rbb.max.Z),
    ):
        assert abs(a - b) < 1e-5


def test_split_top_same_footprint_different_height_and_window():
    """The TOP is deliberately NOT mirror-identical: the halves carry opposite MCU orientations,
    so the USB port sits at a different Z on each.

    The X/Y FOOTPRINT is still common — that is what has to match for the plate, rabbet and seam
    to interchange. The HEIGHT is not, and no longer claims to be: the ridge is derived per half
    (``canopy_ridge_top_z``) so each half carries only as much roof as its own port needs, which
    leaves the left half 2.76 mm shorter. This test used to assert a common ``max.Z`` — that was
    correct under the shared ridge and is now the thing most likely to be assumed by mistake, so
    it asserts the difference explicitly instead."""
    from sofle_case import canopy as CAN
    left, right = build_top_part("left"), build_top_part("right")
    lbb, rbb = left.bounding_box(), right.bounding_box()
    for a, b in (
        (lbb.min.X, rbb.min.X), (lbb.max.X, rbb.max.X),
        (lbb.min.Y, rbb.min.Y), (lbb.max.Y, rbb.max.Y),
        (lbb.min.Z, rbb.min.Z),
    ):
        assert abs(a - b) < 1e-6, "TOP X/Y footprint and floor should be common to both halves"
    # Heights differ, each pinned to its OWN ridge — not to each other and not to the max.
    for side, bb in (("left", lbb), ("right", rbb)):
        assert abs(bb.max.Z - CAN.canopy_ridge_top_z(side)) < 0.01, f"{side} TOP is not at its ridge"
    assert rbb.max.Z - lbb.max.Z > 2.0, \
        "the halves' TOPs are the same height — the per-half ridge collapsed back to a shared one"
    # This test used to also assert a volume DIFFERENCE between the halves as proof the
    # per-side window was applied. That proxy is gone: it was really measuring how much cover
    # material the flipped half's low window scooped out, and once the mid-mount correction
    # lifted that window the two halves differ by only ~0.2 mm³ — a threshold that small is
    # noise, not a guard. ``test_top_usb_window_is_side_specific`` asserts the same claim
    # directly, by probing each half open at its own band and closed at the other's.


def test_top_usb_window_is_side_specific():
    """Each half is open only across its own measured jack band. Probed at the MCU column
    on the canopy's north wall, in the bands the two windows do NOT share."""
    from build123d import Solid
    from sofle_case import canopy as CAN

    def solid_at(part, x, y, z, s=0.3):
        box = Solid.make_box(s, s, s).translate((x - s / 2, y - s / 2, z - s / 2))
        inter = part & box
        return inter is not None and sum(ss.volume for ss in inter.solids()) > 1e-6

    yw = CAN.CANOPY_NORTH_OUTER_Y - CAN.CANOPY_NORTH_WALL / 2
    z_left_only, z_right_only, z_shared = 17.5, 23.5, 20.4
    for side, open_z, solid_z in (("left", z_left_only, z_right_only),
                                  ("right", z_right_only, z_left_only)):
        top = build_top_part(side)
        cx = C.pcb_to_case(*C.MCU_POS)[0]
        if side == "left":
            cx = C.OUTER_WIDTH - cx
        assert not solid_at(top, cx, yw, open_z), f"{side} TOP blocked in its own band"
        assert solid_at(top, cx, yw, solid_z), f"{side} TOP open in the other half's band"
        assert not solid_at(top, cx, yw, z_shared), f"{side} TOP blocked at the shared seam"


def test_top_usb_window_is_open_through_its_whole_band():
    """Regression guard on the post-fuse re-cut in ``canopy.usb_port_cutter``.

    Under the old (guessed) 4.0 mm jack model the flipped half's window floor was 15.6 —
    BELOW ``COVER_TOP_Z`` (16.0) — so fusing the cover on backfilled the bottom of the
    window. That was measured, not hypothetical. The mid-mount correction lifted the floor
    to 16.84, clear of the cover, so the original failure no longer reproduces on today's
    numbers. The probe is therefore band-relative rather than pinned to COVER_TOP_Z: it
    still fires if a future band (or a thicker cover) drops back into the cover, and the
    solid-below check keeps it from passing vacuously if the window ever vanishes."""
    from build123d import Solid
    from sofle_case import canopy as CAN

    top = build_top_part("left")
    cx = C.OUTER_WIDTH - C.pcb_to_case(*C.MCU_POS)[0]
    # Probe in the NECK, past the overmold pocket — a mid-wall Y now lands inside the pocket,
    # where the opening is the taller pocket band and the sill check below would read void.
    yw = CAN.CANOPY_NORTH_OUTER_Y - CAN.CANOPY_USB_OM_DEPTH - 0.5
    lo, hi = CAN.canopy_usb_z("left")

    def probe(z: float) -> float:
        box = Solid.make_box(0.3, 0.3, 0.3).translate((cx - 0.15, yw - 0.15, z - 0.15))
        inter = top & box
        return 0.0 if inter is None else sum(s.volume for s in inter.solids())

    for z in (lo + 0.2, (lo + hi) / 2, hi - 0.2):
        assert probe(z) <= 1e-6, f"window backfilled at z={z:.2f}"
    # The wall must still be solid just under the sill — otherwise the probes above pass
    # for the wrong reason (no wall there at all).
    assert probe(lo - 0.4) > 1e-3, "no wall below the window sill — window is not a bounded hole"


@pytest.mark.parametrize("builder", [build_top_part, build_bottom_part])
def test_split_invalid_side_raises(builder):
    with pytest.raises(ValueError):
        builder("middle")
