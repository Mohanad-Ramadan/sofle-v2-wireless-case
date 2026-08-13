"""The visible parting line between the two cases — where the top case hands over to the wedge.

Over the southern ``TENT_SEAM_SOUTH_FRAC`` of the depth the TOP case's skin carries on below
Z=0 and runs parallel to the desk, ``TENT_SKIRT_LIFT`` above it, so the front reads as one
piece over a narrow reveal of bottom case. It then sweeps back up to Z=0, and from there north
the whole wedge is exposed beneath it.

Seen from the side with the case standing that is the reference's profile exactly: flat along
the desk at the front, a sweep, then a long run rising at the tilt angle. That last run is not
built — it IS the Z=0 plane, which slopes at TENT_ANGLE_DEG once the case stands on its wedge.

Two headline invariants: this costs NO height (the skin drops into space that already existed
between Z=0 and the tent plane), and the skin never touches the desk — ground contact belongs
to the wedge alone, so two separately-printed parts are never fighting over how the case sits."""
import math

import pytest
from build123d import Solid
from sofle_case import constants as C
from sofle_case.canopy import CANOPY_RIDGE_TOP_Z
from sofle_case.case import (_below_seam_cutter, seam_profile_min_z, skirt_extension,
                             tent_ground_z, tent_plane, wedge_deep_z)
from tests.shared_builds import build_bottom_part, build_top_part

OUTER = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE


def _seam_z(y: float) -> float:
    """Where the skin's bottom edge belongs over the southern run: parallel to the tent plane,
    lifted clear of it by TENT_SKIRT_LIFT."""
    return tent_ground_z(y) + C.TENT_SKIRT_LIFT


def _lowest_at(part, y: float, s: float = 0.4):
    """Lowest Z of the part in a thin Y-slice — i.e. where its bottom edge sits at that Y."""
    slab = part & Solid.make_box(400.0, s, 80.0).translate((-100.0, y - s / 2, -40.0))
    if slab.volume < 1e-9:
        return None
    return slab.bounding_box().min.Z


def test_skin_runs_just_above_the_desk_over_the_southern_stretch():
    """South of y1 the top case comes down to within TENT_SKIRT_LIFT of the ground — parallel
    to it, not converging — so only a thin reveal of bottom case shows there."""
    top = build_top_part("right")
    for y in (20.0, 40.0, C.TENT_SEAM_Y1 - 1.0):
        got, want = _lowest_at(top, y), _seam_z(y)
        assert got is not None, f"no material at y={y}"
        assert abs(got - want) < 0.06, \
            f"y={y}: skin bottom at {got:.3f}, expected {C.TENT_SKIRT_LIFT} above the desk ({want:.3f})"


def test_the_skin_never_touches_the_desk():
    """THE reason the lift exists, beyond looks. At lift 0 the skirt's underside is coplanar
    with the wedge's ground face, so the top and bottom parts share the desk contact and
    whichever prints proud decides how the keyboard sits. The wedge must own it alone — it is
    the part ground_face() chamfers and the part the foot seats are cut into.

    Measured against the tent plane itself, over the whole tessellated skin, both halves."""
    o, n = tent_plane()
    for side in ("right", "left"):
        verts, _f = build_top_part(side).tessellate(0.2)
        worst = min((v.X - o[0]) * n[0] + (v.Y - o[1]) * n[1] + (v.Z - o[2]) * n[2] for v in verts)
        assert worst > C.TENT_SKIRT_LIFT - 0.06, \
            f"{side}: skin comes within {worst:.4f} mm of the desk, want {C.TENT_SKIRT_LIFT}"


def test_the_lift_leaves_a_real_skirt_at_the_south():
    """The lift eats the skirt from below and the wedge's thin end is all it has to eat: at
    TENT_SKIRT_LIFT == TENT_WEDGE_MIN_H the bottom edge reaches Z=0 and there is no skirt at
    the front at all. The guard in constants computes that ceiling; this measures the skin."""
    assert C.TENT_SKIRT_LIFT <= C.TENT_SKIRT_LIFT_MAX, "the lift is past its own ceiling"
    top = build_top_part("right")
    for y in (2.0, 10.0):
        got = _lowest_at(top, y)
        assert got is not None, f"no material at y={y}"
        assert got < -C.TENT_SKIRT_MIN_H + 0.06, \
            f"y={y}: only {-got:.3f} mm of skirt below Z=0 — it has become a feather edge"


def test_skin_is_gone_north_of_the_sweep():
    """North of y2 the skin stops at the parting line and the bottom case takes over below it.

    That line used to be Z=0 flat; SEAM_NORTH_RISE_FRAC now dials it up the wall, so this reads
    the dial rather than the old constant. At frac 0 it is still Z=0 and this is the same test
    it always was."""
    top = build_top_part("right")
    for y in (C.TENT_SEAM_Y2 + 4.0, 110.0, 120.0):
        got = _lowest_at(top, y)
        assert got is not None, f"no material at y={y}"
        assert abs(got - C.SEAM_NORTH_RISE_Z) < 0.02, \
            f"y={y}: skin hangs to {got:.3f}, expected the parting line at {C.SEAM_NORTH_RISE_Z:.3f}"


def test_the_sweep_climbs_monotonically_between_the_two():
    """Through the blend the edge rises steadily from the desk to Z=0 — no dip, no reversal,
    and no step at either end. A kink here is exactly what the sweep exists to avoid."""
    top = build_top_part("right")
    ys = [C.TENT_SEAM_Y1 + f * (C.TENT_SEAM_Y2 - C.TENT_SEAM_Y1) for f in
          (0.0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0)]
    zs = [_lowest_at(top, y) for y in ys]
    assert all(z is not None for z in zs)
    for (ya, za), (yb, zb) in zip(zip(ys, zs), zip(ys[1:], zs[1:])):
        assert zb >= za - 0.02, f"edge dips between y={ya:.1f} and y={yb:.1f} ({za:.3f} -> {zb:.3f})"
    assert abs(zs[0] - _seam_z(C.TENT_SEAM_Y1)) < 0.06, "sweep does not start where the run ends"
    assert abs(zs[-1] - C.SEAM_NORTH_RISE_Z) < 0.06, "sweep does not finish on the northern run"


def test_the_handover_costs_no_height():
    """THE requirement. The skin fills space that already existed between Z=0 and the tent
    plane, so the envelope must be identical to what the wedge alone produced."""
    top, bottom = build_top_part("right"), build_bottom_part("right")
    tb, bb = top.bounding_box(), bottom.bounding_box()
    lo, hi = min(tb.min.Z, bb.min.Z), max(tb.max.Z, bb.max.Z)
    lift = C.BOTTOM_CHAMFER * math.tan(math.radians(C.TENT_ANGLE_DEG))
    assert wedge_deep_z() <= lo <= wedge_deep_z() + lift + 1e-3, \
        f"floor moved to {lo:.4f} — the skin added height"
    assert abs(hi - CANOPY_RIDGE_TOP_Z) < 0.01
    # and the deepest the SKIN itself reaches is the lifted run at y1, well above the wedge's floor
    assert tb.min.Z > wedge_deep_z(), "the skin reaches deeper than the wedge — impossible"
    assert abs(tb.min.Z - seam_profile_min_z()) < 0.005, \
        f"skin bottoms out at {tb.min.Z:.4f}, expected the profile minimum {seam_profile_min_z():.4f}"


def test_skin_stays_outboard_of_the_wedge():
    """The skin is the outer SEAM_SKIN band and the wedge is inset behind it, so they descend
    past each other without touching. If that ever stopped holding the parts would not close."""
    top, bottom = build_top_part("right"), build_bottom_part("right")
    assert (top & bottom).volume < 1e-6, "skin and wedge collide below Z=0"
    for side in ("right", "left"):
        assert len(build_top_part(side).solids()) == 1, f"{side} top fractured"


def test_the_sweep_finishes_clear_of_the_relief_bump():
    """The +Y bump stands proud of the nominal outline offset. If the skin reached it, the band
    would have to chase the tub's real footprint instead of a plain offset — the complexity
    that was deliberately designed out. Guarded in constants too; restated here."""
    from sofle_case.tray import _bump_facet_south_y
    assert C.TENT_SEAM_Y2 < _bump_facet_south_y(), \
        f"sweep ends at y={C.TENT_SEAM_Y2:.1f}, into the bump at y={_bump_facet_south_y():.1f}"


def test_skirt_extension_alone_is_a_clean_solid():
    """Guards the builder itself, independent of what it gets fused to. Its own extents are the
    tell: top on Z=0, bottom on the lifted run at y1, and nothing at all north of y2."""
    sk = skirt_extension()
    assert len(sk.solids()) == 1
    bb = sk.bounding_box()
    assert abs(bb.max.Z) < 1e-6, f"skirt should top out at Z=0, got {bb.max.Z:.4f}"
    # The band is the skin BELOW Z=0, so it dies where the parting line reaches Z=0 — at y2 when
    # the northern run is flat there, and progressively further south as SEAM_NORTH_RISE_FRAC
    # lifts that run and the sweep therefore crosses zero earlier.
    assert bb.max.Y <= C.TENT_SEAM_Y2 + 0.5, \
        f"skirt reaches y={bb.max.Y:.2f}, past the end of the sweep at y2={C.TENT_SEAM_Y2:.2f}"
    if C.SEAM_NORTH_RISE_Z <= 0.0:
        assert bb.max.Y >= C.TENT_SEAM_Y2 - 0.5, \
            f"skirt dies at y={bb.max.Y:.2f} with a flat northern run, expected y2"
    else:
        assert C.TENT_SEAM_Y1 < bb.max.Y < C.TENT_SEAM_Y2, \
            f"skirt dies at y={bb.max.Y:.2f}, expected inside the sweep where the line crosses Z=0"
    assert abs(bb.min.Z - seam_profile_min_z()) < 0.005, \
        f"skirt bottoms out at {bb.min.Z:.4f}, expected the profile minimum {seam_profile_min_z():.4f}"


def test_the_channel_mouth_has_a_lead_in_all_the_way_round():
    """Where the skin descends past the wedge they form a channel with only SEAM_FIT_CLEAR
    between them, and its mouth is at the SEAM — not at Z=0, so _chamfer_pocket_mouth's
    starter is buried inboard and useless there. Without relief the bottom case has to arrive
    within 0.2 mm to start.

    BOTH walls are checked, and that is the point of the test. This was first built as a
    chamfer, and OCC propagates a chamfer along the tangent-continuous edge chain: a 0.84 mm
    arc at the SE corner poisoned the whole front-and-east chain at any leg, so the west and
    thumb edges got their lead-in and the rest silently stayed square. Probing one wall would
    not have caught it."""
    top, bottom = build_top_part("right"), build_bottom_part("right")

    def east(y, z, s=0.1):
        sl = top & Solid.make_box(40.0, s, s).translate((130.0, y - s / 2, z - s / 2))
        return sl.bounding_box().min.X if sl.volume > 1e-12 else None

    def west(y, z, s=0.1):
        sl = top & Solid.make_box(40.0, s, s).translate((-16.0, y - s / 2, z - s / 2))
        return sl.bounding_box().max.X if sl.volume > 1e-12 else None

    # Sample the flat run, but only where BOTH walls actually exist. The east wall is cut away
    # by the thumb cluster at the south — ramp E4 tops out around y=33 and the offset outline
    # takes a few mm more to reach full X — so anything below EAST_WALL_SOUTH_Y probes thin
    # air. The last sample tracks y1 so the test still follows TENT_SEAM_SOUTH_FRAC.
    east_wall_south_y = 40.0
    ys = [y for y in (40.0, 45.0, C.TENT_SEAM_Y1 - 1.0) if east_wall_south_y <= y < C.TENT_SEAM_Y1]
    assert ys, (f"TENT_SEAM_SOUTH_FRAC={C.TENT_SEAM_SOUTH_FRAC} ends the flat run at "
                f"y={C.TENT_SEAM_Y1:.1f}, south of the east wall at y={east_wall_south_y} — "
                f"no sample can probe both walls, so this test would prove nothing")
    def seated_z(g):
        """Height for the SEATED reference probe: the plain, un-relieved skirt face.

        It has to thread a window — above the lead-in relief (which ends SEAM_LEAD_IN above the
        seam) and below the pocket mouth chamfer (which flares the same face for
        SEAM_POCKET_LEAD_IN below Z=0). A fixed 'seam + 2 mm' does not: with the skirt lifted,
        the seam at these southern samples is shallow enough that 2 mm lands ABOVE Z=0, inside
        the mouth chamfer, and the test then reads a relief short by exactly that chamfer."""
        lo, hi = g + C.SEAM_LEAD_IN, -C.SEAM_POCKET_LEAD_IN
        assert lo < hi, (f"no plain skirt left at seam={g:.3f}: the lead-in relief (to {lo:.3f}) "
                         f"meets the mouth chamfer (from {hi:.3f}) — nothing to measure against")
        return (lo + hi) / 2.0

    for y in ys:
        g = _seam_z(y)
        s_z = seated_z(g)
        for name, seated, mouth, sign in (("east", east(y, s_z), east(y, g + 0.1), 1.0),
                                          ("west", west(y, s_z), west(y, g + 0.1), -1.0)):
            assert seated is not None and mouth is not None, f"{name} y={y}: probe off the wall"
            relief = (mouth - seated) * sign
            assert relief >= C.SEAM_LEAD_IN - 0.02, \
                f"{name} wall y={y}: mouth relieved only {relief:.3f}, want {C.SEAM_LEAD_IN}"
            assert relief <= C.SEAM_LEAD_IN + 0.02, \
                f"{name} wall y={y}: relief {relief:.3f} overshoots — it is eating the skin"
    # closes back to the nominal face rather than staying flared
    y = ys[-1]
    g = _seam_z(y)
    assert abs(east(y, g + C.SEAM_LEAD_IN + 0.2) - east(y, seated_z(g))) < 0.02, "relief never closes"
    # and the opening clears the wedge it has to accept — measured in the SAME Y slice, not
    # against the bottom's global extent. North of the sweep the bottom now comes out flush with
    # the tub, so its widest point is out at the skin and would fail this trivially while saying
    # nothing about the channel down here.
    local = bottom & Solid.make_box(400.0, 0.4, 200.0).translate((-100.0, y - 0.2, -80.0))
    assert east(y, g + 0.1) > local.bounding_box().max.X, \
        "mouth is narrower than the wedge it accepts"


def test_the_lead_in_tracks_the_sweep_not_a_flat_plane():
    """The relief is the seam cutter shifted up by SEAM_LEAD_IN, so it follows the blend as
    well as the flat run. Referenced to a plane instead it would drift off the mouth as the
    seam climbs, and the guidance would quietly disappear exactly where the channel narrows."""
    top = build_top_part("right")

    def east(y, z, s=0.1):
        sl = top & Solid.make_box(40.0, s, s).translate((130.0, y - s / 2, z - s / 2))
        return sl.bounding_box().min.X if sl.volume > 1e-12 else None

    def seam_at(y, s=0.1):
        """The seam at THIS y, on the same slice thickness the relief probes use.

        _lowest_at samples a 0.4 mm slab and reports its minimum, which is the seam 0.2 mm
        SOUTH of y — fine on the flat run, misleading in the blend, and increasingly so as
        SEAM_NORTH_RISE_FRAC steepens the climb (0.24 mm of Z per mm of Y at frac 0, 0.65 at
        0.5). Probing 0.08 above a seam read that low lands in air."""
        sl = top & Solid.make_box(400.0, s, 160.0).translate((-100.0, y - s / 2, -60.0))
        return sl.bounding_box().min.Z if sl.volume > 1e-9 else None

    checked = 0
    ramp = C.TENT_SEAM_Y2 - C.TENT_SEAM_Y1
    for y in (C.TENT_SEAM_Y1 + 0.2 * ramp, C.TENT_SEAM_Y1 + 0.35 * ramp):
        seam = seam_at(y)
        # The seated reference sits 0.85 above the seam; it must clear the relief (which ends
        # SEAM_LEAD_IN up) and stay below the pocket mouth chamfer, or it measures the chamfer.
        if seam is None or seam + 0.85 > -C.SEAM_POCKET_LEAD_IN - 0.05:
            continue                      # channel too shallow here to carry a relief
        relief = east(y, seam + 0.08) - east(y, seam + 0.85)
        assert abs(relief - C.SEAM_LEAD_IN) < 0.03, \
            f"y={y:.1f} (in the blend): relief {relief:.3f}, want {C.SEAM_LEAD_IN}"
        checked += 1
    assert checked, "no sample landed inside the blend — the test proved nothing"


def test_the_south_fraction_is_the_dial():
    """TENT_SEAM_SOUTH_FRAC alone drives where the handover sits — everything else derives.

    Its range is 0.0-1.0, but the usable ceiling is lower: the sweep has to finish before the
    +Y relief bump, so TENT_SEAM_FRAC_MAX depends on the ramp length. The constants guard
    computes that ceiling and names it in its failure, rather than just refusing."""
    assert 0.0 <= C.TENT_SEAM_SOUTH_FRAC <= 1.0
    assert abs(C.TENT_SEAM_Y1 - C.TENT_SEAM_SOUTH_FRAC * C.OUTER_DEPTH) < 1e-9
    assert abs(C.TENT_SEAM_Y2 - (C.TENT_SEAM_Y1 + C.TENT_SEAM_RAMP_FRAC * C.OUTER_DEPTH)) < 1e-9
    assert C.TENT_SEAM_SOUTH_FRAC <= C.TENT_SEAM_FRAC_MAX, "the dial is past its own ceiling"
    # the ceiling is exactly the fraction whose sweep ends on the bump limit
    assert abs((C.TENT_SEAM_FRAC_MAX + C.TENT_SEAM_RAMP_FRAC) * C.OUTER_DEPTH
               - (C.OUTER_DEPTH - 20.0)) < 1e-9


def test_the_handover_actually_sits_where_the_dial_says():
    """Measured on the solid, not just the arithmetic: on the desk just south of y1, and clear
    of it just north of y2. Catches the constant being changed without the geometry following."""
    top = build_top_part("right")
    south = _lowest_at(top, C.TENT_SEAM_Y1 - 8.0)
    north = _lowest_at(top, C.TENT_SEAM_Y2 + 8.0)
    assert abs(south - _seam_z(C.TENT_SEAM_Y1 - 8.0)) < 0.06, \
        "skin is not on its lifted run south of the handover"
    assert abs(north - C.SEAM_NORTH_RISE_Z) < 0.02, \
        "skin is not on its northern run past the sweep"


@pytest.mark.parametrize("angle", [1.0, 3.0, 7.0, 10.0])
def test_the_seam_cutter_never_reaches_above_z0(monkeypatch, angle):
    """The cutter's southern guard branch, which only becomes REACHABLE at a steep angle.

    ``_below_seam_cutter`` starts its profile 20 mm south of the case, and the southern run is
    the tent plane lifted by ``TENT_SKIRT_LIFT``. That lifted plane rises going south, so far
    enough out it crosses Z=0 — at 3 deg it has not yet done so by y=-20 (z_s = -0.45), at 7 deg
    it has (z_s = +1.96). Past the crossing the profile is HELD at Z=0 rather than followed,
    because everything below the profile is the cutter and a cutter reaching above Z=0 eats the
    tub proper instead of its skirt.

    The hold is safe at every angle, and not by luck: the crossing sits at y = -20 + z_s/tan,
    and substituting z_s = -TENT_WEDGE_MIN_H + 20*tan + TENT_SKIRT_LIFT collapses the whole
    thing to (TENT_SKIRT_LIFT - TENT_WEDGE_MIN_H)/tan, which is negative for any angle so long
    as the lift stays under the wedge's thin end — which ``TENT_SKIRT_LIFT_MAX`` already
    guarantees. So the crossing is always SOUTH of the case and the tub is never touched.

    Swept across the band rather than tested at one angle, because the branch that fires
    depends on the angle and both branches must land in the same place."""
    monkeypatch.setattr(C, "TENT_ANGLE_DEG", angle)
    cutter = _below_seam_cutter()
    inside = cutter & Solid.make_box(400.0, C.OUTER_DEPTH, 200.0).translate((-100.0, 0.0, -100.0))
    assert inside.volume > 1e-9, f"{angle} deg: the cutter missed the case entirely"
    assert inside.bounding_box().max.Z <= C.SEAM_NORTH_RISE_Z + 1e-6, (
        f"{angle} deg: the seam cutter reaches Z={inside.bounding_box().max.Z:.4f} inside the "
        f"case, above the parting line at {C.SEAM_NORTH_RISE_Z:.4f} — it is eating the tub, "
        f"not the skirt")


@pytest.mark.parametrize("angle", [3.0, 7.0, 10.0])
def test_the_sweep_dips_below_the_run_and_costs_no_clearance(monkeypatch, angle):
    """The sweep leaves the southern run along the PLANE'S slope, so it keeps descending for a
    few mm before it curves up — the profile's minimum is south of the ramp's midpoint and below
    the run's end at y1, not equal to it.

    That is tangency working as intended, not a defect, and the reason it needs its own test is
    that it hid for a long time: at 3 deg the dip is 0.024 mm and four separate assertions
    compared the tub's floor against z1 with a 0.05 tolerance, so it fitted underneath. At 7 deg
    it is 0.074 and all four failed at once. They were wrong the whole time; the angle only made
    it visible. They now compare against seam_profile_min_z() and can afford a 0.005 tolerance.

    THE INVARIANT THAT ACTUALLY MATTERS IS UNAFFECTED, which is the other half of this test. The
    dip is measured against z1 — one number — while the desk is a tilted plane that drops
    northward FASTER than the spline does. So dipping below z1 moves the skin AWAY from the desk,
    not toward it, and the ground clearance stays the full TENT_SKIRT_LIFT."""
    monkeypatch.setattr(C, "TENT_ANGLE_DEG", angle)
    z1 = tent_ground_z(C.TENT_SEAM_Y1) + C.TENT_SKIRT_LIFT
    lo = seam_profile_min_z()
    dip = z1 - lo
    assert dip > 0.0, "the sweep no longer leaves the run tangentially — someone kinked the seam"
    assert dip < 0.2, f"{angle} deg: sweep dips {dip:.4f} mm, far more than tangency explains"
    # and the clearance to the DESK is untouched by it — measured perpendicular to the plane
    o, n = tent_plane()
    y_dip = C.TENT_SEAM_Y1 + 1.2                      # ~where the minimum sits, all angles
    gap = (y_dip - o[1]) * n[1] + (lo - o[2]) * n[2]
    assert gap > C.TENT_SKIRT_LIFT * 0.9, (
        f"{angle} deg: the dip pulled the skin to {gap:.4f} mm off the desk, eating into the "
        f"{C.TENT_SKIRT_LIFT} mm lift — it must not, the desk falls faster than the spline")
