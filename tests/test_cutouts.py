def test_slide_scoop_is_a_solid():
    from sofle_case.case import _slide_scoop
    scoop = _slide_scoop()
    assert scoop.volume > 0, "slide-switch scoop cutter is empty"
    assert len(scoop.solids()) == 1, "slide-switch scoop cutter is not one solid"


# ----- Slide-switch actuator drop-in pocket ------------------------------------
from typing import cast

import pytest
from build123d import Part, Solid, Box, Location, BuildPart, Locations, Pos

from sofle_case import constants as C
from sofle_case.pcb_geometry import slide_switch_placement, rotate_2d


def _switch_body() -> Part:
    """SK12D07VG3 metal can solid, built from OWNED structural constants + SW31 placement."""
    cx, cy, rot = slide_switch_placement()
    body_z = C.PCB_TOP_Z + C.SLIDE_ACTUATOR_BODY_H / 2
    bdx, bdy = rotate_2d(C.SLIDE_ACTUATOR_PIN_CENTER_X, 0.0, rot)
    with BuildPart() as bp:
        with Locations(Location((cx + bdx, cy + bdy, body_z), (0, 0, rot))):
            Box(C.SLIDE_ACTUATOR_BODY_L, C.SLIDE_ACTUATOR_BODY_W, C.SLIDE_ACTUATOR_BODY_H)
    assert bp.part is not None
    return bp.part


def _switch_nub() -> Part:
    """Actuator nub solid, built from OWNED structural constants + SW31 placement."""
    cx, cy, rot = slide_switch_placement()
    nub_z = C.PCB_TOP_Z + C.SLIDE_ACTUATOR_NUB_BASE + C.SLIDE_ACTUATOR_NUB_H / 2
    ndx, ndy = rotate_2d(
        C.SLIDE_ACTUATOR_PIN_CENTER_X,
        -(C.SLIDE_ACTUATOR_BODY_W / 2 + C.SLIDE_ACTUATOR_NUB_D / 2),
        rot,
    )
    with BuildPart() as bp:
        with Locations(Location((cx + ndx, cy + ndy, nub_z), (0, 0, rot))):
            Box(C.SLIDE_ACTUATOR_NUB_L, C.SLIDE_ACTUATOR_NUB_D, C.SLIDE_ACTUATOR_NUB_H)
    assert bp.part is not None
    return bp.part


def _footprint_bbox():
    """Combined can+nub plan bbox (x0, x1, y0, y1) in case coords."""
    bb_b = _switch_body().bounding_box()
    bb_n = _switch_nub().bounding_box()
    return (
        min(bb_b.min.X, bb_n.min.X), max(bb_b.max.X, bb_n.max.X),
        min(bb_b.min.Y, bb_n.min.Y), max(bb_b.max.Y, bb_n.max.Y),
    )


def test_slide_actuator_cavity_is_a_solid():
    from sofle_case.case import _slide_actuator_cavity
    cav = _slide_actuator_cavity()
    assert cav.volume > 0, "actuator cavity cutter is empty"
    assert len(cav.solids()) == 1, "actuator cavity cutter is not one solid"
    bb = cav.bounding_box()
    # Poured from the seam to the cover underside — never perforates the lid.
    assert abs(bb.min.Z - C.SLIDE_ACTUATOR_FLOOR_Z) < 1e-6
    assert abs(bb.max.Z - C.SLIDE_ACTUATOR_TOP_Z) < 1e-6


@pytest.mark.parametrize("side", ["right", "left"])
def test_top_part_single_valid_solid_with_cavity(side):
    """The extra drop-in cut must leave the TOP part one valid manifold solid."""
    from tests.shared_builds import build_top_part
    top = build_top_part(side)
    assert top.is_valid, f"TOP part invalid after actuator cavity cut ({side})"
    assert len(top.solids()) == 1, f"TOP part is not a single solid ({side})"


def test_slide_switch_clears_top_solid():
    """The physical switch (can + nub) has ZERO overlap with the TOP solid.

    KNOW WHAT THIS DOES NOT PROVE. It measures the case against the SK12 phantom, and every
    dimension of that phantom is assumed rather than measured. A can taller than the modelled
    4.3 mm collides with the printed case while this still reads 0.000 mm^3 — trialled at 5.0
    it reported 0.175 mm^3, a 1.40 x 8.70 mm strip surviving between _slide_actuator_cavity's
    cap and _slide_scoop's inboard reach because neither cut owned it. The assertion is sound;
    the ruler behind it is not verified, and re-running this can never tell you that."""
    from tests.shared_builds import build_top_part
    top = build_top_part("right")
    body_hit = cast(Part, _switch_body() & top).volume
    nub_hit = cast(Part, _switch_nub() & top).volume
    assert body_hit < 1e-6, f"switch can collides TOP by {body_hit:.4f} mm^3"
    assert nub_hit < 1e-6, f"actuator nub collides TOP by {nub_hit:.4f} mm^3"


def test_slide_switch_clearance_is_real_not_coincident():
    """Zero interference is NOT the same claim as clearance, and conflating them is what let
    this ship twice. Coincident faces measure 0.000 mm^3 while touching — the switch reads
    "clear" with nothing between it and the lid, so any print error at all is a hard stop.

    Raise the whole switch and require it to STAY clear. If this fails while
    test_slide_switch_clears_top_solid passes, the pocket is kissing the can, not clearing it."""
    from tests.shared_builds import build_top_part
    top = build_top_part("right")
    margin = 0.3
    for name, body in (("can", _switch_body()), ("nub", _switch_nub())):
        lifted = cast(Part, Pos(0, 0, margin) * body)
        hit = top & lifted
        vol = 0.0 if hit is None else cast(Part, hit).volume
        assert vol < 1e-6, (
            f"slide switch {name} has less than {margin} mm of Z clearance — it fouls the TOP by "
            f"{vol:.4f} mm^3 when raised {margin} mm, so the nominal 0.000 is coincident contact"
        )


def test_slide_actuator_pad_gap_is_real():
    """A grown probe (footprint + 0.4 mm, INSIDE the 0.5 mm pad) still has zero
    overlap with the TOP solid — proving the clearance gap is genuine, not coincident.
    Checked over the pocket's OWN Z extent (floor → SLIDE_ACTUATOR_TOP_Z cap); the can's
    clearance up to its full measured top is covered separately by
    test_slide_switch_clears_top_solid (currently xfail — the cap does not reach it)."""
    from tests.shared_builds import build_top_part
    top = build_top_part("right")
    x0, x1, y0, y1 = _footprint_bbox()
    g = 0.4
    z0, z1 = C.PCB_TOP_Z, C.SLIDE_ACTUATOR_TOP_Z  # 7.9 .. cavity cap (the pocket's own Z span)
    probe = Solid.make_box(
        (x1 - x0) + 2 * g, (y1 - y0) + 2 * g, z1 - z0
    ).translate((x0 - g, y0 - g, z0))
    # build123d returns None for an empty intersection — which is exactly the passing case.
    overlap = probe & top
    hit = 0.0 if overlap is None else cast(Part, overlap).volume
    assert hit < 1e-6, f"grown 0.4 mm probe overlaps TOP by {hit:.4f} mm^3 — pad gap not real"


def test_slide_drop_in_channel_is_clear():
    """Switch clearance column: across the switch footprint grid, the TOP solid has NO
    material anywhere over the Z span the pocket actually promises, so the tub lowers over
    the switch (or the switch drops in) without collision.

    NB the lower bound is the switch-body base (PCB_TOP_Z), not the cavity floor: the
    tub now owns the full outer skin to the ground, so the −X wall is legitimately
    solid BELOW the switch where part of the footprint bbox overlaps the wall band —
    that material never touches the switch, which sits entirely above PCB top.

    The upper bound was a hardcoded 12.2 — stale twice over. It came from FLOOR_THICKNESS
    3.8 (PCB_TOP_Z is 10.4 now) and it assumed a 4.3 mm can. It is now derived, and clamped
    to SLIDE_ACTUATOR_TOP_Z: the band from the cap up to the real can top (14.5 → 15.4) is a
    known interference, so asserting clearance there would just duplicate the xfail on
    test_slide_switch_clears_top_solid, which owns that claim for the whole can."""
    from tests.shared_builds import build_top_part
    top = build_top_part("right")
    x0, x1, y0, y1 = _footprint_bbox()
    can_top = C.PCB_TOP_Z + C.SLIDE_ACTUATOR_BODY_H
    z_hi = min(can_top, C.SLIDE_ACTUATOR_TOP_Z)

    def solid_at(x, y, z, e=0.1):
        b = Solid.make_box(2 * e, 2 * e, 2 * e).translate((x - e, y - e, z - e))
        return cast(Part, top & b).volume > 1e-7

    xs = [x0 + (x1 - x0) * i / 6 for i in range(1, 6)]
    ys = [y0 + (y1 - y0) * i / 8 for i in range(1, 8)]
    zs = [C.PCB_TOP_Z + (z_hi - C.PCB_TOP_Z) * i / 8 for i in range(9)]
    for z in zs:
        hits = sum(1 for x in xs for y in ys if solid_at(x, y, z))
        assert hits == 0, f"channel blocked: {hits} solid hits at Z={z:.3f}"


def test_slide_cavity_does_not_perforate_lid():
    """The pocket is capped at SLIDE_ACTUATOR_TOP_Z so it CANNOT perforate the lid: the cap is
    derived from the measured can (+SLIDE_ACTUATOR_CAP_CLEAR) but clamped to leave at least
    SLIDE_ACTUATOR_LID_MIN of solid cover above it. The cutter has zero material at/above the cap, and
    the TOP still carries solid (cover/wall) material above the cap over the footprint —
    that band is provably untouched by a cut that lives entirely below it.

    (The slide switch sits in the open MCU/OLED/slide bay notch and behind the
    top-open finger scoop, so there is no continuous membrane directly over it; the
    invariant that matters is that THIS feature removes nothing above the cap.)"""
    from sofle_case.case import _slide_actuator_cavity
    from tests.shared_builds import build_top_part
    x0, x1, y0, y1 = _footprint_bbox()

    # Slab from the cover underside up through the lid, over the whole padded footprint.
    px0, px1 = x0 - C.SLIDE_ACTUATOR_PAD, x1 + C.SLIDE_ACTUATOR_PAD
    py0, py1 = y0 - C.SLIDE_ACTUATOR_PAD, y1 + C.SLIDE_ACTUATOR_PAD
    lid_slab = Solid.make_box(px1 - px0, py1 - py0, 3.0).translate(
        (px0, py0, C.SLIDE_ACTUATOR_TOP_Z))

    def vol(x):
        return 0.0 if x is None else x.volume

    cav = _slide_actuator_cavity()
    assert vol(cav & lid_slab) < 1e-9, "cavity cutter intrudes above the cover underside"

    top = build_top_part("right")
    assert vol(top & lid_slab) > 1.0, "no cover/wall material above the cap — lid missing"


@pytest.mark.parametrize("side", ["right", "left"])
def test_slide_cavity_leaves_bottom_unchanged(side):
    """The slide cavity is a TOP-only feature; the BOTTOM is a separate inset plate
    below the rabbet ledge, so its volume is independent of the slide cavity. Baseline
    is the inset floor plate + standoffs − battery pocket (identical both sides)."""
    from tests.shared_builds import build_bottom_part
    # Baseline reflects FLOOR_THICKNESS=6.3 (deep-battery redesign): the inset plate spans
    # floor→SEAM_LEDGE_Z, which rose with the floor, so the plate is taller than before.
    # Rebased for SEAM_FIT_CLEAR 0.3→0.2: the derived rim (SEAM_RIM_THK 2.45→2.55) adds
    # ~311.8 mm³ of plate material (was 72618.786656).
    # Rebased again for the TENT WEDGE: the bottom case grew the wedge that stands the
    # keyboard at TENT_ANGLE_DEG, +47.9 cm³ of solid (was 72930.559471), less the
    # elephant-foot chamfer cut on its tilted ground rim. The wedge rides the PLATE's rim
    # profile (inset behind the tub skin), not the tub footprint. The test's point is
    # unchanged — the slide cavity is a TOP feature and must not show up in this number.
    # Rebased for the tent going 2 deg -> 3 deg, which was never carried into this number: the
    # wedge grew with the angle and the baseline stayed at its 2 deg value, so this assertion was
    # already failing (137697.065 measured against 120795.947) before SEAM_NORTH_RISE_FRAC
    # existed. That dial cuts the TUB back and leaves the bottom's geometry alone, so it does
    # not appear here at all — as with the slide cavity, which is the point of the test.
    # Rebased for the tent angle, 3 deg -> 7 deg -> 6 deg (7 was tried, 6 was kept). The wedge is
    # part of the bottom part, so this number tracks the angle and is checked against the wedge's
    # OWN volume change before being accepted, never just re-measured: 3->7 was +68021.07 mm3
    # against a wedge growth of +68048, and 7->6 is -17088.4 against a wedge shrink of -17088.
    # Any residual is the elephant-foot counter-chamfer on the ground rim, which cuts more as the
    # rim tilts more (BOTTOM_CHAMFER * tan(angle) deeper). So the bottom moves by the wedge and by
    # nothing else, which is exactly what this assertion exists to prove — as with the slide cavity.
    # 2e-2 abs tolerates OCC mirror/heal float noise on the left half (~1e-2).
    # Rebased for the FLARED OUTER BAND: the bottom case no longer stops at the plate rim, it
    # comes out to the tub's skin and stands SEAM_FLARE_MAX past it below the reveal, so the
    # visible band is real material now instead of the floor of a recess. +8205.8 mm³ (was
    # 188629.693062), checked against _bottom_outer_shell()'s own volume before being accepted.
    # Rebased again, +537.4, when the band moved onto the TUB's outline and its flare was
    # re-datumed to the band's own top edge: the tub outline is 126.9 mm² larger in plan than the
    # polygon offset (it carries the +Y bump), and the eased onset adds material through y=55-75
    # that the one-shot step used to leave out.
    # Rebased +65.3 mm³ (0.03%), from two changes that both move the band's slab layout:
    #   * _seam_z_at stopped being a nearest-of-1001-samples lookup and became an interpolated
    #     4001-point table. The old form quantised the parting line to ~0.126 mm in Y; this one
    #     puts the sections where the curve actually is. More accurate, not less — and worth
    #     touching because the old lookup rebuilt the ramp spline on EVERY call and was
    #     essentially the entire 28 s build cost.
    #   * SEAM_FLARE_STEP_MAX went 0.15 -> 0.20, and _flare_slab_bounds reads it as "how fine to
    #     cut the slabs". That coupling is worth knowing about: the cap is an acceptance
    #     threshold AND a build input, so moving it moves the part.
    #   * +8.66 more when face_lofted went UNRULED. A ruled loft chords between its sections, so
    #     it cut the corner on a wall that curves outward — the smooth surface bulges back out to
    #     where the flare law actually says it should be. More material, and the right amount.
    # Rebased -2296.88 mm³ (-1.16%) when the band went FLUSH and stopped being flared. Broken out,
    # because the total is three separate effects and only the first is the intended one:
    #   * -2242.72  the band's own volume, 8754.72 -> 6512.00. It no longer stands 1.5 mm proud
    #               of the skin, and no longer overhangs to y=127.5.
    #   *   -65.06  the elephant-foot counter-chamfer on the ground rim, WHICH WAS DOING NOTHING
    #               BEFORE. _chamfer_wedge_ground_edge cut exactly 0.000000 mm³ at HEAD — it was
    #               falling through both legs to its silent no-op, because the flared band's
    #               ground rim defeated OCC's chamfer. On the flush rim it lands on the full
    #               BOTTOM_CHAMFER leg. So the printed part gets its counter-chamfer back, and
    #               this is the number proving it rather than a fallback pretending to succeed.
    #     +9.28  the fuse sealing coincident faces: the band's inner face and the wedge's outer
    #               face are both at rim_outer, and OCC closes the hairline between them.
    #   (-2242.72 - 65.06 + 9.28 = -2298.50 against -2296.88 measured; the 1.6 mm³ residual is
    #    0.0008% and is boolean float noise.)
    # Rebased +316.81 mm³ (+0.16%) when the wave's tail became a shoulder-then-straight instead
    # of an arc. Holding the parting line high past the crest means the desk keeps dropping away
    # under it, so the visible band is up to 1.38 mm taller through y≈100-110 — the band's own
    # volume moved +303.81 of the +316.81, and the remaining +13.00 is the ground-rim chamfer
    # cutting a slightly different rim. No dimension changed; the line just takes a different
    # route between the same crest and the same back edge.
    # Rebased +5.97 mm³ (+0.003%) when the standoff pins were recessed below the plate
    # (STANDOFF_PIN_RECESS). Two effects, opposite signs, and the net is small because they very
    # nearly cancel: MX_BODY_CLEAR 3.0 -> 3.7 lifts PLATE_SEAT_Z by 0.7, which would have made
    # each of the 5 pins 0.7 mm TALLER, and the 0.6 mm recess gives back all but 0.1 of that.
    # 5 pins x 0.1 mm of Ø3.9 shaft, less the tap bore that follows them down, is the residual.
    # No outer dimension moved: the wedge, band and parting line are all below the seam and are
    # untouched by anything above PCB_SEAT_Z.
    # Rebased −17.90 mm³ (−0.009%) when MX_BODY_CLEAR went 3.7 -> 3.40 (the derived ai03 plate
    # datum, 5.0 − PLATE_THICKNESS). PLATE_SEAT_Z drops 0.3, so every standoff pin top drops 0.3
    # with it. The loss is the FULL Ø3.9 shaft section, not shaft-minus-bore, because the tap bore
    # is drilled down from the pin top and translates with it — bore length is unchanged, the pin
    # simply starts 0.3 mm lower. 5 pins x 0.3 x π/4 x 3.9² = 17.92 predicted vs 17.90 measured;
    # the 0.02 residual is the entry chamfer meeting a shorter pin.
    # No outer dimension moved: everything the wedge, band and parting line touch is below the
    # seam, and nothing above PCB_SEAT_Z reaches them.
    # Rebased −1065.62 mm³ (−0.55%) when the battery JST moved UNDER the PCB. Standing on the
    # board it fouled the cover by 34.2 mm³ and was the only hardware holding the case open; the
    # fix put it in a blind floor pocket with a wire channel to the battery, so the bottom loses
    # that material. The delta is fully accounted for and worth checking rather than trusting:
    #   jst_pocket             732.459
    #   jst_wire_channel     + 358.063
    #   shared overlap       −  12.500   (_CHANNEL_OVERLAP, 1.0 x 5.0 x 2.5, counted once)
    #   union                = 1078.021
    #   already-void         −  12.40    (the channel's east end reaches INTO the battery pocket,
    #                                     which is air already — the same 1.0 x 5.0 x 2.5 slug)
    #   removed              = 1065.62   measured −1065.624 (right) / −1065.619 (left)
    # This number moved ONCE ALREADY, from −1186.87, when the connector's dimensions went from
    # datasheet-derived to calipered (6.5 x 8.0 x 8.0, replacing 7.6 x 7.4 x 9.5). The pocket got
    # shallower and shorter — and WIDER, which was the point: at 7.4 it was 8.4 mm across for an
    # 8.0 mm part and would likely not have accepted it. A baseline that only ever shrinks is not
    # evidence the pocket fits.
    # Still no outer dimension moved: the pocket bottoms at Z 1.80 and the channel at 3.80, both
    # far above the wedge's own surfaces, so the ground plane and parting line are untouched.
    # 2e-2 abs still tolerates OCC mirror/heal float noise on the left half (~1e-2).
    assert abs(build_bottom_part(side).volume - 194389.226835) < 2e-2
