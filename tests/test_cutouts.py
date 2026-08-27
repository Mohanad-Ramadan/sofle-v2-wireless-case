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
    # Rebased −1817.00 mm³ (−0.93%) for the battery JST, which now hangs UNDER the PCB in a floor
    # pocket with a diagonal wire channel to the battery. Standing on the board it fouled the
    # cover by 34.2 mm³ and was the only hardware holding the case open. Accounted for in full:
    #   jst_pocket             959.440
    #   jst_wire_channel     + 2194.650
    #   shared overlap       −   78.750   (the channel's first leg starts inside the JST pocket)
    #   union                = 3075.340
    #   already-void         −   71.559   (its last leg ends inside the battery pocket)
    #   net new void         = 3003.781   measured −3003.835 (right) / −3003.831 (left)
    # The 0.4 residual is the pocket's corner fillets, where the channel crosses the rounding.
    #
    # THIS NUMBER HAS MOVED FIVE TIMES, and the sequence is the point:
    #   −1186.87  datasheet-derived connector (7.6 x 7.4 x 9.5)
    #   −1065.62  calipered instead (6.5 x 8.0 x 8.0) — smaller in two axes, but WIDER in the
    #             third, which was the whole risk: at 7.4 the pocket was 8.4 mm across for an
    #             8.0 mm part and would likely not have accepted it
    #   −1817.00  pocket re-placed onto the real pin row (JST_POS is PIN 1, not the body centre)
    #             and the channel made diagonal and full-depth
    #   −1997.07  pocket widened to 11.54 to span BOTH mounting positions: the middle hole is B+
    #             and both outer holes are GND, so the connector is reversible on the board and a
    #             pocket fitting only one pair would freeze a choice the wiring leaves open
    #   −2989.82  channel re-routed from a diagonal to a hooked orthogonal path (north, east,
    #             south, east), ~92 mm instead of 64 — the length is deliberate slack
    #   −3003.84  entry leg dropped 0.5 so its south face lands FLUSH on the battery pocket's
    #             south wall instead of 0.5 mm north of it, which left a jog at the junction
    # A baseline that only ever shrinks is not evidence the pocket fits. Four times now it grew.
    #
    # Still no outer dimension moved: the pocket and channel both bottom at Z 1.80, far above the
    # wedge's own surfaces, so the ground plane and parting line are untouched.
    # Rebased +67.88 mm³ (+0.035%) for FOOT_DIA 10.0 -> 8.0. The seats are the ONLY thing that
    # moved, and they give material back rather than taking it:
    #   Ø10:  4 x π x 5² x FOOT_DEPTH(0.6) = 188.50 mm³ removed
    #   Ø8:   4 x π x 4² x 0.6             = 120.64 mm³ removed
    #   net                                = + 67.86 predicted vs +67.875 measured
    # The 0.015 residual is the seats meeting a TILTED ground face: _foot_recesses cuts
    # perpendicular to the tent plane, so a seat's rim sits at slightly different depths across
    # its diameter, and a smaller disc samples that 6° slope differently. Nothing else in the
    # bottom part is a function of FOOT_DIA — the wedge, band and parting line are untouched,
    # which is the same invariant the rest of this baseline's history exists to prove.
    #
    # Rebased −67.88 mm³ AGAIN, restoring FOOT_DIA to 10.0. The shrink above was made to keep the
    # seats off the snap arms' relief slots, and the two passes that followed it (eleven arms on
    # even arc-length stations, SNAP_TAB_SLOT_W 1.2 -> 0.9) moved every slot it had been measured
    # against. Ø10 clears them all now; three feet moved 1.6-1.9 mm inboard to keep the 1.2 mm
    # printability gate, and the tightest arm-to-seat gap is 2.15 mm — better than the 1.76 mm the
    # Ø8 layout had. The delta returns the PREVIOUS baseline to six decimals under a rebuild with
    # only FOOT_DIA reverted, which is what proves the moved positions cost nothing: a seat's
    # volume is π r² × FOOT_DEPTH wherever it sits, because _foot_recesses cuts perpendicular to
    # the tent plane rather than vertically, so sliding one along the 6° slope does not change it.
    # Rebased −4578.55 mm³ (−2.38%) for the NINE SNAP LATCHES. Accounted for in full:
    #   8 straight reliefs  −3805.907  (their cutters total more; the surplus is air below the
    #                                   wedge, because every slot deliberately overruns the
    #                                   ground face so the release port opens on the underside)
    #   N2's wrapped relief −  788.811  (a concentric band, not local boxes — it follows the
    #                                   4.24 mm arc between the lobe and the run past it)
    #   8 straight barbs    +   14.987
    #   N2's barb           +    1.873
    #   predicted           = −4577.858  vs −4578.546 measured, −0.69 residual (0.015%)
    #
    # AN EARLIER VERSION OF THIS NUMBER WAS OFF BY 1.4 mm³ AND THAT WAS A REAL BUG, not noise.
    # The barb sits at 0.8L and runs SNAP_BARB_X_LEN long, so on the short N2 arm (L=14) its
    # outboard half landed PAST the free end, inside the relief slot — and barbs are fused on
    # AFTER the slot is cut, so it plugged the slot and welded the arm back to the rim it is
    # supposed to be free of. Every geometric test still passed; only the volume disagreed.
    # barb_u() now clamps to keep the barb on the arm (inactive at L=22, to 4 decimals).
    #
    # THE ORDER OF THOSE TWO OPS AGAINST _chamfer_wedge_ground_edge MATTERS, and this number is
    # what caught it. Cutting the reliefs BEFORE the chamfer left a 27.4 mm³ discrepancy: that
    # helper selects ground_face(part).outer_wire().edges(), and nine through-slots hand it the
    # slot mouths as extra edges to chamfer — putting a 0.5 mm chamfer inside each release port.
    # Chamfering first drops the residual to 1.38. A helper with a silent no-op fallback and a
    # documented history of taking it (docs/z-stack.md) is exactly the kind that fails quietly,
    # so the sequencing is asserted here by arithmetic rather than trusted.
    # Rebased −481.021325 mm³ (−0.256%) for the SOUTH CHAIN going from two arms to four:
    # S2-south-W deleted, S1 re-aimed to the run's centre, and SE1-se-diag, T1-thumb-gulf and
    # SW1-sw-diag added, so the four of them divide the E1->W1 perimeter into five equal
    # 40.69 mm steps. Arm count goes 9 -> 11.
    #
    # THE DELTA WAS VALIDATED BY REBUILDING, NOT BY ARITHMETIC, because the arithmetic does not
    # close here and it is worth saying why. The relief cutters total 1121.777 mm³ more than
    # before (SE1 683.645 + T1 438.132 + SW1 683.645, less S2's 683.645) against a measured
    # swing of only 481.021 — the rest is cutter that never met material, since every slot
    # deliberately overruns the wedge's ground face so its release port opens on the underside,
    # and the wedge is thinnest exactly where the south chain lives (b = 9.42 mm at the south
    # front, 7.58 at the gulf). So the check that actually stands behind this number is: with
    # C.SNAP_ARMS monkeypatched back to the previous nine-arm tuple and SNAP_CORNER_BARB_LO_Z
    # back to 2.30, build_bottom_part("right") returns 187940.344201 — the old baseline, to all
    # six decimals. The geometry is otherwise untouched.
    #
    # Barb volumes read 2.954 mm³ each now rather than 1.873. That is SNAP_BARB_EMBED: the barb
    # carries a backing slab (8.0 x 0.15 x 0.9007 = 1.081) sunk into the rim so the fuse has a
    # real overlap instead of one tangent plane. It sits inside the arm, so it contributes
    # nothing to this total — the two figures differ by exactly the slab.
    # Rebased again, +71.305234 mm³ (+0.038%), when every arm was re-spaced to divide the whole
    # 495.26 mm rim evenly instead of only the southern stretch. The count did not change — ten
    # straight arms plus N2 — so this is not arms appearing or vanishing, it is eleven slots and
    # barbs moving to different walls. The volume goes UP because the relief slot is a constant
    # 1.2 mm wide but runs the full local wall height, and the arms moved on balance toward the
    # SOUTH and the shallow end of the wedge, where there is less material under them for the
    # slot to overrun into. Arm lengths also changed (SW1 22->16, SE1 22->20) and thicknesses
    # were re-derived per arm from the force budget, which moves the slot's radial position but
    # not its width.
    # Rebased +1176.396083 mm³ (+0.63%) for SNAP_TAB_SLOT_W 1.2 -> 0.9. The volume goes UP
    # because a narrower relief slot REMOVES LESS: eleven arms, each slot 0.30 mm narrower over
    # roughly (L + slot) of length and the local wall height, which is 7.6 mm at the gulf and
    # ~20 mm at the north. 11 x 0.30 x ~22.9 x ~15 comes to ~1130 mm³ against the 1176 measured,
    # and the balance is the wedge overrun the slot no longer cuts.
    #
    # The other half of this change contributes NOTHING here: barb_lo_z going from a 1.40-4.40
    # ladder to a flat 3.95 moves every barb in Z but does not resize it, and the rim it stands
    # on is a plain vertical prism through that whole band, so the same solid just sits higher
    # or lower. The catch pockets that pair with it are cut from the TOP.
    #
    # Validated by rebuilding rather than by arithmetic, as before: with C.SNAP_TAB_SLOT_W put
    # back to 1.2 and the old ladder restored onto SNAP_ARMS and SNAP_CORNER_BARB_LO_Z,
    # build_bottom_part("right") returns 187530.628110 — the previous baseline, to all six
    # decimals.
    # Rebased +66.075821 mm³ (+0.035%) for SEAM_WAVE_BAND_SCALE 1.0 -> 1.02 (the seam-wave crest
    # raised from 3.60 to 3.87 mm). The bottom part's visible band is taller wherever the wave is
    # taller, and nothing else in this build depends on the wave -- the wedge, plate, pins,
    # pockets and feet are all either below the seam or governed by their own dials. Validated by
    # rebuilding, not arithmetic, as this file insists on: SEAM_WAVE_KNOTS is baked in at import
    # time (like the literal table it replaced), so this was checked by reverting the working tree
    # to before SEAM_WAVE_BAND_SCALE existed and rebuilding, which reproduces the previous
    # 188707.024193 baseline to all six decimals.
    # Rebased -17.261403 mm³ (-0.009%) for moving E2-east-N to its rim run's physical ceiling
    # (SNAP_RUN_EAST 29.11 -> 24.75) to buy back as much ambient-wall clearance as that run has to
    # give, at the cost of the NE corner's even-spacing (see the SNAP_ARMS note above E2 and
    # test_every_barb_is_evenly_spaced_around_the_whole_rim's named exception). E1-east-S
    # (38.15 -> 35.81) and N3-north-east (24.61 -> 24.70) moved to do the least damage to the rest
    # of the rim given E2 fixed at that ceiling, not to hit a spacing target of their own. The
    # relief slot's footprint shifts with each arm, hence the volume change; nothing else moved.
    # Rebased -1181.742773 mm³ (-0.626%) for SNAP_TAB_SLOT_W 0.9 -> 1.2, which UNDOES the
    # +1176.396083 logged above: a wider relief slot removes more. The two are not equal and
    # opposite because the arms are not where they were when 0.9 was taken — E2, E1 and N3 moved
    # for the NE-corner reposition logged just below it, and a slot's overrun into the wedge is a
    # function of the local wall height, so the same 0.30 mm of extra width cuts a different
    # amount of real material at each new station. 5.35 mm³ of difference across eleven arms.
    #
    # The widening is a PRINTABILITY change, not a mechanical one: at 0.9 the slot was a little
    # over two 0.4 mm extrusions and could partially bridge, and a bridged OUTBOARD leg turns the
    # arm from a cantilever into a fixed-fixed strip at 8x the root strain — a fracture, not a
    # soft latch. Nothing else in this part is a function of the slot width: barbs, seats, wedge,
    # pockets and parting line are untouched, and the suite at 1.2 failed on this baseline alone.
    # Rebased -1.242615 mm³ (-0.001%) for T1-thumb-gulf's thickness 1.30 -> 1.40, taken to clear
    # SNAP_TAB_SLOT_W's own 1.2 mm print-reliability floor by a real margin (T1 had come out of
    # the force budget at only 0.10 mm above it, thinnest of any arm — see the note above
    # SNAP_ARMS). The volume goes DOWN, not up, because T1's outboard leg is a through-cut across
    # the full (thickness + SNAP_TAB_SLOT_W) band at the free end: a thicker arm pushes that cut's
    # inboard edge further in, so it removes MORE material there, not less. Nothing else moved —
    # T1's barb, catch pocket and root relief are unaffected by thickness, and no other arm's
    # force or geometry changed (total closing force absorbs the +0.63 N with 0.69 N to spare).
    # Rebased +46.639414 mm³ (+0.025%) for UNIFORM ARM THICKNESS: every straight arm and the N2
    # corner set to 1.50 mm, replacing the per-arm force-budget values (1.40-2.15 straight,
    # 2.00 corner). Print-reliability margin above SNAP_TAB_SLOT_W's 1.2 mm floor was uneven
    # across the set — T1 at only +0.20 mm (just fixed above), the rest anywhere from +0.35 to
    # +0.95 mm — and a single value gives every arm the same, deliberately generous +0.30 mm.
    # Volume goes UP overall because most arms got THINNER (S1 2.15->1.50 is the biggest single
    # move), and a thinner arm's outboard through-cut spans less of the local wall (it cuts
    # (thickness + SNAP_TAB_SLOT_W) at the free end), so it removes LESS material — T1 and SW1
    # move the other way (1.40->1.50, 1.55->1.50) but are outweighed by the rest.
    #
    # T1 ALSO MOVED 0.35 mm ALONG ITS OWN RUN (s 2.96 -> 2.61), which does not touch this volume
    # at all (root position, not size) but is folded into the same commit: widening the slot to
    # 1.2 mm had quietly taken T1's free-end cut from 1.56 mm clear of its run's own end down to
    # 1.26 mm, because GULF_A (18.42 mm) is the shortest run on the rim and T1's 13 mm arm plus
    # a 1.2 mm slot leaves only 4.22 mm to split between the root and the cut. The old split
    # (1.96 root / 1.26 cut) is now balanced (1.61 / 1.61) — the best either side can do on this
    # run, not an arbitrary choice.
    #
    # UNIFORM LENGTH WAS TRIED AND REJECTED, measured rather than assumed: GULF_A caps a shared
    # length at 12.46 mm (below T1's own current 13 mm), and forcing every arm down to that
    # length quadruples-plus the total closing force (61.56 N against the 28 N cap, because
    # force goes as 1/L^3) while pushing every arm's strain to 0.467% — closer to the 0.5% PLA
    # cap than any arm sits today. Shortening to chase uniformity would have made the design
    # both less printable (force, not thickness, is what the total-force test actually gates)
    # and no safer in the one dimension that motivated this change.
    # Rebased -51.351904 mm³ (-0.027%) for the CLOSING-FORCE RE-TUNE: arm thickness went from a
    # uniform 1.50 mm back to per-arm (S1/E1/N1/W1/N3/W2/E2 1.500->1.866, SE1 1.500->1.542, N2
    # corner 1.50->2.30; SW1/T1 unchanged), sized to hit a 30.0 N total closing force rather than
    # either force-evenness or a uniform print margin. Volume goes DOWN because every arm that
    # got thicker cuts MORE at its outboard through-cut (that leg spans the full
    # (thickness + SNAP_TAB_SLOT_W) band at the free end — see the SNAP_TAB_SLOT_W note), and
    # more arms got thicker than thinner this time.
    # Rebased +46.187839 mm³ (+0.025%) for the SCREWLESS RE-TUNE: every straight arm and the N2
    # corner back to a uniform 1.50 mm print floor (S1/E1/N1/W1/N3/W2/E2 1.866->1.500, SE1
    # 1.542->1.500, N2 2.300->1.500; SW1/T1 already there), and SNAP_BARB_PROUD 0.52 -> 0.45. With
    # the snaps now the sole closure, the 30 N force target is retired — thickness drops to the
    # floor everywhere (see the note above SNAP_ARMS). Volume goes UP because thinner arms cut LESS
    # at their outboard through-cut ((thickness + SNAP_TAB_SLOT_W) at the free end); the shorter
    # barb (proud 0.52->0.45, a fused ADDER) subtracts a little of that gain, net +46.19. This
    # almost exactly reverses the previous -51.35 mm³ thickening rebase, as expected.
    # Rebased -110.703880 mm³ (-0.059%) for PRY-SPREAD STIFFNESS: the long arms and the corner go
    # from the 1.50 mm floor to 2.20 mm and SW1 to 2.00 mm (its L/t>=8 limit), run thick so the
    # snaps resist a drop/bag load that spreads the seam (stiffness ~ thickness^3). Only T1 stays
    # at 1.50 mm — it is the one strain-binding arm and its fatigue margin is set by proud, not
    # thickness (see the note above SNAP_ARMS). Volume goes DOWN because a thicker arm's outboard
    # through-cut spans more of the local wall ((thickness + SNAP_TAB_SLOT_W) at the free end), so
    # it removes MORE material. Worst-case strain is unchanged at 0.333% (T1).
    # Rebased +6.613565 mm³ (+0.004%) for a TALLER BARB: SNAP_LEAD_IN_DEG 30 -> 22 makes the barb
    # 0.78 -> 1.11 mm tall (~11 print layers at 0.1 mm instead of ~4) for print fidelity, at the
    # same proud/deflect/strain. The barb is a fused ADDER, so a taller one adds a little volume.
    # Rebased +52.419600 mm³ (+0.028%) for SCREWLESS: the M2 self-tap bore + entry chamfer are
    # removed from all 5 standoff pins (the pins are now solid PCB-registration bosses), so the
    # bottom part no longer subtracts those voids.
    # Rebased +26.874874 mm³ (+0.014%) for STANDOFF_PIN_RECESS 0.6 -> 0.15: real print evidence
    # (two shops) showed the old 0.6 mm gap let the switch plate sag/slip toward the PCB during
    # assembly, not FDM inaccuracy — see the note above STANDOFF_PIN_RECESS in constants.py. Each
    # of the 5 solid pins grew 0.45 mm taller (Ø3.9 cross-section), adding standoff material.
    # Rebased +204.846 mm³ (+0.109%) for the AGGRESSIVE-HOLD RE-TUNE (2026-08-26): SEAM_FIT_CLEAR
    # 0.20 -> 0.15, the long arms + SE1 + N2 corner 2.20 -> 2.35 mm (SW1 held at 2.00 by its L/t>=8
    # limit, T1 at the 1.50 mm floor), and SNAP_BARB_PROUD 0.45 -> 0.55. Net volume goes UP because
    # the tighter SEAM_FIT_CLEAR narrows the full-perimeter skirt pocket in the tub (SEAM_RIM_THK
    # 2.55 -> 2.60), removing LESS material around the whole seam — a perimeter-scale effect that
    # outweighs the two local subtractive ones: the thicker arms' wider outboard through-cuts and
    # the deeper catch pockets under the taller barb (proud 0.45 -> 0.55) both remove a little more.
    # This retune raised closing force ~1.9x and click energy ~3x for a firmer seat; see the note
    # above SNAP_ARMS in constants.py and the two guardrail tests in test_snaps.py.
    # Rebased +17916.261 mm³ (+9.5%) for the BLIND-PORT SKIN: an 18461.36 mm³ slab added under the
    # wedge to close the 11 snap release ports, less the 545.10 mm³ of air gap it carves back out
    # under the arms (the standalone snap_bottom_gap() reads 674.8, but its outboard margin lies
    # past the skin's rim profile and removes no real material). The arms keep their full height, so
    # this touches no snap force (test_snaps is unchanged); the cost is ~1.3 mm of added height, not
    # force. See .omc/specs/deep-dive-bottom-cover-inlay.md.
    # Rebased +828.444 mm³ when the visible OUTER BAND was re-datumed to the skin desk too: the
    # band used to stop at the old wedge ground and float _skin_drop() proud of the new desk, so it
    # now extends down to reach it (the top skirt does the same at the south, restoring the front
    # reveal to TENT_SKIRT_LIFT). Checked against _bottom_outer_shell()'s own volume growth.
    # 2e-2 abs still tolerates OCC mirror/heal float noise on the left half (~1e-2).
    # Rebased +329.693 mm³ for two dial changes together: SEAM_REVEAL_H 2.0 -> 1.5 mm (a
    # shallower reveal exposes more of the flush outer band at a given Y — see test_north_rise's
    # recess probe, which had to move for the same reason) and TENT_SEAM_SOUTH_FRAC/RAMP_FRAC
    # 0.36/0.64 -> 0.3295/0.6705 (more ramp room so the wave spline leaves the southern run
    # tangent to the knot after it instead of overshooting into a visible kink — the knot itself,
    # and TENT_SEAM_Y2, are unmoved). Neither change touches the wedge or the snap arms.
    assert abs(build_bottom_part(side).volume - 206800.903) < 2e-2
