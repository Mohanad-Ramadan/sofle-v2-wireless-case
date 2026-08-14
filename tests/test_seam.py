"""The visible parting line between the two cases — where the top case hands over to the wedge.

Over the southern ``TENT_SEAM_SOUTH_FRAC`` of the depth the TOP case's skin carries on below
Z=0 and runs parallel to the desk, ``TENT_SKIRT_LIFT`` above it, so the front reads as one
piece over a reveal so narrow it looks like none. A WAVE then carries it up, crests it above
Z=0 around u=0.67, and brings it back DOWN THROUGH Z=0 again over the rear, where it lands on
a short flat run at ``SEAM_NORTH_RISE_Z`` — a negative number, because that rear stretch is
skirt too.

Seen from the side with the case standing, the bottom case is a LENS: pinched to almost
nothing at the front, swelling to a crest around two-thirds back, closing again toward the
rear. That is the shape the ramp exists to produce, and it is why the ramp is a through-fit
spline over ``SEAM_WAVE_KNOTS`` rather than the two-point hump it began as — a two-point
spline between the runs is monotonic by construction, so the band could only ever widen going
north, and it ended at the full wedge height.

The skirt is therefore TWO bands, not one: the parting line crosses Z=0 twice, and between
those crossings the top case has nothing below Z=0 at all.

Two headline invariants: this costs NO height (the skin drops into space that already existed
between Z=0 and the tent plane), and the skin never touches the desk — ground contact belongs
to the wedge alone, so two separately-printed parts are never fighting over how the case sits."""
import math
from typing import cast

import pytest
from build123d import Part, Solid
from sofle_case import constants as C
from sofle_case.canopy import CANOPY_RIDGE_TOP_Z
from sofle_case.case import (_below_seam_cutter, _seam_ramp_edge, _seam_sweep_params,
                             seam_profile_max_z,
                             bottom_deep_z, seam_profile_min_z, seam_skirt_tub, skirt_extension, tent_ground_z,
                             tub_outline_face,
                             tent_plane,
                             wedge_deep_z)
# shared_builds' rule is "never import builders from sofle_case directly", and this is the one
# sanctioned exception: the mutation test below patches a constant, which the side-keyed cache
# cannot see. Named so nothing reaches for it by accident.
from sofle_case.case import build_top_part as uncached_build_top_part
from tests.shared_builds import build_bottom_part, build_top_part

OUTER = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE


def _seam_z(y: float) -> float:
    """Where the skin's bottom edge belongs over the southern run: parallel to the tent plane,
    lifted clear of it by TENT_SKIRT_LIFT."""
    return tent_ground_z(y) + C.TENT_SKIRT_LIFT


def _zero_crossings() -> tuple[float, float]:
    """The two case-Y values at which the parting line crosses Z=0: climbing, then dropping back.

    These bound the skirt band, which is by definition the skin BELOW Z=0 — it exists south of
    the first and north of the second, and not between them. The wave crosses twice; the old
    two-point ramp crossed once, at its own end, which is why the band used to die at y2 and why
    every test that asserted y2 was really asserting a property of that curve."""
    edge = _seam_ramp_edge()
    pts = [edge @ (i / 2000.0) for i in range(2001)]
    xs = []
    for a, b in zip(pts, pts[1:]):       # sketch-local .Y is case Z; .X is case Y
        if (a.Y <= 0.0 <= b.Y) or (b.Y <= 0.0 <= a.Y):
            t = (0.0 - a.Y) / (b.Y - a.Y) if b.Y != a.Y else 0.0
            xs.append(a.X + t * (b.X - a.X))
    assert len(xs) == 2, f"the parting line crosses Z=0 {len(xs)} times, expected exactly 2"
    return xs[0], xs[1]


def _profile_z_at(y: float, s: float = 0.4) -> float:
    """Where the parting line sits at a given case-Y, read off the installed profile.

    Three stretches, same as the cutter draws them: the lifted tent plane south of y1, the ramp
    between, the flat rear run north of y2.

    MEASURED OVER THE SAME Y-WINDOW ``_lowest_at`` uses, not at the single station. That probe
    takes the minimum Z through a slab of thickness ``s``, so on a sloped stretch it reports the
    slab's lower edge — 0.1 mm below the centre-line value where the rear ramp is falling at
    0.15 mm/mm. Comparing a slab minimum against a point value is measuring the slab, not the
    geometry."""
    lo, hi = y - s / 2, y + s / 2

    def at(yy: float) -> float:
        if yy <= C.TENT_SEAM_Y1:
            return _seam_z(yy)
        if yy >= C.TENT_SEAM_Y2:
            return C.SEAM_NORTH_RISE_Z
        edge = _seam_ramp_edge()
        pts = [edge @ (i / 2000.0) for i in range(2001)]
        # sketch-local .X is case Y, .Y is case Z
        return min(pts, key=lambda p: abs(p.X - yy)).Y

    return min(at(lo + (hi - lo) * i / 20.0) for i in range(21))


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


def _worst_desk_clearance(side: str, builder=build_top_part) -> float:
    """Closest the top case comes to the tent plane anywhere, measured perpendicular to it over
    the whole tessellated skin. Negative means it has gone through the desk.

    ``builder`` is a seam so the mutation test can hand in the UNCACHED build — see there."""
    o, n = tent_plane()
    verts, _f = builder(side).tessellate(0.2)
    return min((v.X - o[0]) * n[0] + (v.Y - o[1]) * n[1] + (v.Z - o[2]) * n[2] for v in verts)


def test_the_skin_never_touches_the_desk():
    """THE reason the lift exists, beyond looks. At lift 0 the skirt's underside is coplanar
    with the wedge's ground face, so the top and bottom parts share the desk contact and
    whichever prints proud decides how the keyboard sits. The wedge must own it alone — it is
    the part ground_face() chamfers and the part the foot seats are cut into.

    ANCHORED TO TENT_SKIRT_CLEAR_MIN, NOT TO THE LIFT, and that distinction is the whole point
    of the test. It used to read `worst > TENT_SKIRT_LIFT - 0.06`, which derives the threshold
    from the very dial that can violate the invariant: at lift 0.0 it relaxed to `worst > -0.06`
    and passed on a case whose skin sat ON the desk. The physical floor is a constant of the
    print process, not of the styling."""
    for side in ("right", "left"):
        worst = _worst_desk_clearance(side)
        assert worst >= C.TENT_SKIRT_CLEAR_MIN, (
            f"{side}: skin comes within {worst:.4f} mm of the desk, floor is "
            f"{C.TENT_SKIRT_CLEAR_MIN} — the wedge no longer owns ground contact alone")


def test_the_skin_actually_achieves_the_lift_it_is_set_to():
    """Separate assertion, deliberately. The one above protects the case from being unbuildable;
    this one checks it looks the way the dial says — that the reveal really is TENT_SKIRT_LIFT
    wide and the skin is not sitting somewhere else entirely for an unrelated reason.

    Split apart so that turning the styling dial can never move the safety threshold again."""
    worst = _worst_desk_clearance("right")
    assert abs(worst - C.TENT_SKIRT_LIFT) < 0.06, \
        f"skin's closest approach is {worst:.4f} mm, but TENT_SKIRT_LIFT asks for {C.TENT_SKIRT_LIFT}"


def test_the_desk_clearance_guard_is_not_anchored_to_the_dial():
    """Mutation test on the guard itself: drive TENT_SKIRT_LIFT to 0 and the measurement must
    actually collapse, proving `test_the_skin_never_touches_the_desk` would FIRE rather than
    relax alongside it.

    Written because the old form of that guard passed at lift 0 — the failure mode is invisible
    unless something checks that the threshold and the measurement move independently.

    THE UNCACHED BUILDER, deliberately, against shared_builds' usual rule. That cache is keyed on
    `side` alone, so a monkeypatched constant does not invalidate it and the shared instance comes
    back built at the ORIGINAL lift — this test read 0.4973 against a patched 0.0 and failed for
    that reason before the switch. Any mutation test that patches a constant must rebuild."""
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(C, "TENT_SKIRT_LIFT", 0.0)
        worst = _worst_desk_clearance("right", builder=uncached_build_top_part)
    finally:
        monkeypatch.undo()
    assert worst < C.TENT_SKIRT_CLEAR_MIN, (
        f"at lift 0 the skin still stands {worst:.4f} mm off the desk — either the lift no longer "
        f"drives the seam, or the measurement is not seeing the skirt")


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


def test_the_skin_follows_the_parting_line_across_the_rear():
    """The skin's bottom edge IS the parting line, at every station, including the rear ones.

    This used to be "the skin is gone north of the sweep", which was true while the line sat at
    or above Z=0 there: nothing of the top case hung below Z=0 past y2 and the wedge showed
    unaided. The wave's rear knots take the line back UNDER Z=0, so the skin descends again over
    the last quarter — the rear skirt — and "gone" is the wrong question. What is still exactly
    true, and is the thing worth guarding, is that the skin stops on the line and nowhere else."""
    top = build_top_part("right")
    for y in (C.TENT_SEAM_Y2 - 20.0, C.TENT_SEAM_Y2 - 5.0, C.OUTER_DEPTH - 1.2):
        got = _lowest_at(top, y)
        assert got is not None, f"no material at y={y}"
        want = _profile_z_at(y)
        assert abs(got - want) < 0.06, \
            f"y={y}: skin hangs to {got:.3f}, expected the parting line at {want:.3f}"


def test_the_band_eases_out_instead_of_stepping_out_in_plan():
    """Seen from underneath, the band must GROW out of the wedge's line, not appear at full
    width. It used to jump 3.215 mm in a single millimetre of Y, at y=55 where the reveal opens.

    Two causes, both fixed, and the measurement covers both: the flare was keyed to absolute Z,
    so the band was born carrying 1.037 mm of it while still 0.00 mm tall; and it was born flush
    with the skin while the wedge beside it sat 2.2 mm further in.

    MEASURED AGAINST THE TUB'S OWN PLAN SILHOUETTE, and sampled at 0.25 mm. Against a fixed line
    this would report the outline's own shape instead — and the outline has a real 35 mm cliff at
    the north-east corner (y≈115), which the band has to follow. Stations within a flare radius
    of one of the tub's own steps are therefore skipped: there the band is allowed to move
    exactly as fast as the tub does."""
    from build123d import extrude
    bottom = build_bottom_part("right")
    tub = extrude(tub_outline_face(), amount=1.0)

    def east(part, y, z, s=0.15):
        sl = part & Solid.make_box(400.0, s, s).translate((-100.0, y - s / 2, z - s / 2))
        return None if sl.volume < 1e-9 else sl.bounding_box().max.X

    ys, tv, bv = [], [], []
    y = 50.0
    while y <= C.OUTER_DEPTH - 0.5:
        t = east(tub, y, 0.5)
        b = east(bottom, y, tent_ground_z(y) + 0.4)
        if t is not None and b is not None:
            ys.append(y); tv.append(t); bv.append(b)
        y += 0.25
    assert len(ys) > 200, "the sweep found almost nothing to measure"

    skip = set()
    for i in range(len(ys) - 1):
        if abs(tv[i + 1] - tv[i]) > 0.5:                 # the tub's outline steps here
            skip.update(j for j in range(len(ys))
                        if abs(ys[j] - ys[i]) <= C.SEAM_FLARE_MAX + 1.0)

    worst, worst_y = 0.0, None
    for i in range(len(ys) - 1):
        if i in skip or i + 1 in skip:
            continue
        d = abs((bv[i + 1] - tv[i + 1]) - (bv[i] - tv[i]))
        if d > worst:
            worst, worst_y = d, ys[i + 1]
    assert worst <= C.SEAM_FLARE_STEP_MAX, (
        f"the plan silhouette steps {worst:.3f} mm at y={worst_y:.2f}, over the "
        f"{C.SEAM_FLARE_STEP_MAX} mm cap — the band is jumping out, not easing out")

    # ...and it really does travel the whole way, from the wedge's line out past the skin.
    span = max(b - t for b, t in zip(bv, tv)) - min(b - t for b, t in zip(bv, tv))
    assert span > 3.0, f"the band only moves {span:.2f} mm — the ease is not doing anything"


def test_the_bottom_stays_inside_the_top_s_own_outline():
    """From the bottom plan the two shells must register: the bottom follows the TOP's outline,
    not the PCB polygon's.

    The polygon knows nothing about the +Y relief bump or the tub's north-east corner, so the
    old bottom sailed straight past both. Stated as containment rather than a per-Y comparison,
    because an outward offset ROUNDS convex corners — the band legitimately bulges up to a flare
    radius past the corner in Y, and a station-by-station check reads that as a 33 mm error."""
    from sofle_case.tray import face_lofted
    bottom = build_bottom_part("right")
    grown = face_lofted(tub_outline_face(),
                        [(-40.0, C.SEAM_FLARE_MAX + 0.05), (1.0, C.SEAM_FLARE_MAX + 0.05)])
    below = cast(Part, bottom & Solid.make_box(400.0, 400.0, 60.0)
                 .translate((-100.0, -100.0, -60.0)))
    spill = cast(Part, below - grown)
    assert spill.volume < 1e-3, (
        f"{spill.volume:.3f} mm³ of bottom case sits outside the top's outline grown by the "
        f"flare — the two do not register from below")


def test_the_rear_skirt_exists_and_closes_the_lens():
    """THE point of the rear knots. The band of visible bottom case must be NARROWER at the back
    than at its crest, or the wave reads as a ripple rather than a lens.

    It cannot be, with the parting line at or above Z=0: the band there is at least the wedge's
    own height (TENT_WEDGE_MAX_H), which is wider than any crest the rabbet-lap floor allows. So
    this measures the one thing that made it possible — that the top case really does descend
    below Z=0 again at the rear."""
    top = build_top_part("right")
    rear = _lowest_at(top, C.OUTER_DEPTH - 1.2)
    assert rear is not None and rear < -0.5, \
        f"no rear skirt: the skin stops at {rear} near the back, not below Z=0"

    def band(y):
        return _lowest_at(top, y) - tent_ground_z(y)

    crest = max(band(y) for y in range(70, 100, 2))
    back = band(C.OUTER_DEPTH - 1.2)
    assert back < crest, (
        f"the band is {back:.2f} mm at the back against a {crest:.2f} mm crest — it re-opens, "
        f"so the lens does not close")


def test_the_ramp_crests_once_and_eases_back():
    """The wave's defining shape, and the assertion that replaced a monotonicity check.

    The ramp used to be a two-point spline, monotonic by construction, and the test said so. The
    wave is not monotonic and MUST NOT BE — it crests above Z=0 and eases back down to the
    northern run, which is the whole reason the bottom case reads as a lens rather than a skirt
    that stops. Asserting "climbs steadily" against this curve tests the old design.

    What still has to hold is that it turns over exactly ONCE. Two crests would be a wobble in
    the parting line, visible from a metre away, and a through-fit spline over a mis-typed knot
    is precisely how you would get one."""
    top = build_top_part("right")
    ys = [C.TENT_SEAM_Y1 + f * (C.TENT_SEAM_Y2 - C.TENT_SEAM_Y1)
          for f in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)]
    zs = [_lowest_at(top, y) for y in ys]
    assert all(z is not None for z in zs), "the ramp has a hole in it"

    rising = [zb > za for za, zb in zip(zs, zs[1:])]
    turns = sum(a != b for a, b in zip(rising, rising[1:]))
    assert turns == 1, (
        f"the ramp changes direction {turns} times, want exactly 1 (up to the crest, then down). "
        f"Profile: {['%.2f' % z for z in zs]}")
    assert rising[0] and not rising[-1], "the ramp must climb first and ease second, not the reverse"

    assert abs(zs[0] - _seam_z(C.TENT_SEAM_Y1)) < 0.06, "ramp does not start where the run ends"
    assert abs(zs[-1] - C.SEAM_NORTH_RISE_Z) < 0.06, "ramp does not finish on the northern run"
    assert max(zs) > C.SEAM_NORTH_RISE_Z + 1.0, \
        "the ramp never rises meaningfully above the northern run — the crest has gone flat"


def test_the_handover_costs_no_height():
    """THE requirement, and it still holds — for the SKIN. The skin fills space that already
    existed between Z=0 and the tent plane, so it adds nothing.

    The flare is a separate matter and it DOES cost height: the bottom case now reaches
    SEAM_FLARE_MAX past the tub's skin, so its footprint runs further north and the desk is
    ~0.4 mm lower by the time it gets there. That is accounted for inside wedge_deep_z(), which
    is why this compares against that function and not against TENT_WEDGE_MAX_H — the two used
    to agree and no longer do."""
    top, bottom = build_top_part("right"), build_bottom_part("right")
    tb, bb = top.bounding_box(), bottom.bounding_box()
    lo, hi = min(tb.min.Z, bb.min.Z), max(tb.max.Z, bb.max.Z)
    lift = C.BOTTOM_CHAMFER * math.tan(math.radians(C.TENT_ANGLE_DEG))
    assert bottom_deep_z() <= lo <= bottom_deep_z() + lift + 1e-3, \
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


def test_the_skirt_matches_the_wall_above_it_across_the_relief_bump():
    """What replaced "the sweep finishes clear of the relief bump".

    That test asserted the skin never reached the +Y bump, because skirt_extension built its band
    from a polygon offset and the bump stands proud of it — a band reaching the bump would sit
    INSIDE the wall above and leave a step at Z=0 along its whole face. The rear skirt has to go
    there, so the band is now sectioned from the tub itself and the restriction is gone.

    This measures the property that made it safe: at a station ON the bump, the skirt's outer
    face and the wall's outer face are the same face — no step at the handover."""
    from sofle_case.tray import _bump_facet_south_y
    y = max(_bump_facet_south_y() + 2.0, C.OUTER_DEPTH - 6.0)
    assert y < C.OUTER_DEPTH, "probe station fell off the back of the case"
    top = build_top_part("right")

    def east_face(z):
        slab = top & Solid.make_box(400.0, 1.0, 0.6).translate((-100.0, y - 0.5, z - 0.3))
        return None if slab.volume < 1e-9 else slab.bounding_box().max.Y

    above = east_face(1.0)                       # the wall, just above the handover
    below = east_face(C.SEAM_NORTH_RISE_Z / 2)   # the skirt, halfway down the rear band
    assert above is not None and below is not None, f"no material to measure at y={y}"
    assert abs(above - below) < 0.02, (
        f"y={y:.1f}: wall reaches +Y {above:.3f} but the skirt below it reaches {below:.3f} — "
        f"a {abs(above - below):.3f} mm step at the bump, so the band is not following the wall")


def test_skirt_extension_alone_is_a_clean_solid():
    """Guards the builder itself, independent of what it gets fused to. Its own extents are the
    tell: top on Z=0, bottom on the lifted run at y1, and nothing at all north of y2."""
    sk = skirt_extension(seam_skirt_tub())
    # TWO solids now, and that is the design: the wave crosses Z=0 twice, so the band exists over
    # the southern stretch and again over the rear, with the crest's stretch — where the parting
    # line is ABOVE Z=0 and there is no skin below it — separating them. It was one solid while
    # the line crossed zero once. Each piece still has to be clean.
    solids = sk.solids()
    assert len(solids) == 2, f"expected a southern band and a rear band, got {len(solids)}"
    assert all(s.volume > 1.0 for s in solids), "one of the two bands is a sliver"
    bb = sk.bounding_box()
    assert abs(bb.max.Z) < 1e-6, f"skirt should top out at Z=0, got {bb.max.Z:.4f}"
    # The band is the skin BELOW Z=0, so it dies where the parting line FIRST reaches Z=0 — and
    # with the wave that is inside the ramp, not at its end: the ramp crosses zero around u=0.55
    # and spends the rest of its run above it. Measured against the profile rather than against
    # y2, because "where does the seam cross Z=0" is a property of the installed curve. The old
    # form asserted y2 whenever the northern run was flat, which was only ever true because the
    # two-point ramp reached Z=0 exactly once, at its end.
    up, down = _zero_crossings()
    south, rear = sorted(solids, key=lambda s: s.bounding_box().min.Y)
    assert abs(south.bounding_box().max.Y - up) < 0.5, (
        f"southern band dies at y={south.bounding_box().max.Y:.2f}, expected y={up:.2f} where the "
        f"parting line climbs through Z=0")
    assert abs(rear.bounding_box().min.Y - down) < 0.5, (
        f"rear band starts at y={rear.bounding_box().min.Y:.2f}, expected y={down:.2f} where the "
        f"parting line drops back through Z=0")
    assert bb.max.Y <= C.OUTER_DEPTH + 1e-6, \
        f"skirt reaches y={bb.max.Y:.2f}, past the back of the case"
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
    # The ceiling is exactly the fraction whose ramp ends at the BACK OF THE CASE. It used to be
    # the fraction whose ramp ended at the +Y bump limit, 20 mm short of that — a fence around a
    # skirt built from a polygon offset. skirt_extension sections the tub now, so the bump is no
    # longer a special case and the only limit left is the part's own depth.
    assert abs((C.TENT_SEAM_FRAC_MAX + C.TENT_SEAM_RAMP_FRAC) * C.OUTER_DEPTH
               - C.OUTER_DEPTH) < 1e-9


def test_the_handover_actually_sits_where_the_dial_says():
    """Measured on the solid, not just the arithmetic: on the desk just south of y1, and clear
    of it just north of y2. Catches the constant being changed without the geometry following."""
    top = build_top_part("right")
    south = _lowest_at(top, C.TENT_SEAM_Y1 - 8.0)
    # There is no flat rear run left to probe — the ramp descends all the way to the back edge,
    # which is what stops the band re-opening at the end. So the north station is compared with
    # the PROFILE there, and the dial is checked where it actually applies: at y = OUTER_DEPTH.
    north = _lowest_at(top, C.OUTER_DEPTH - 1.2)
    assert abs(south - _seam_z(C.TENT_SEAM_Y1 - 8.0)) < 0.06, \
        "skin is not on its lifted run south of the handover"
    assert abs(north - _profile_z_at(C.OUTER_DEPTH - 1.2)) < 0.06, \
        "skin is not on the ramp near the back edge"
    assert abs(_seam_sweep_params()[0][-1][1] - C.SEAM_NORTH_RISE_Z) < 1e-9, \
        "the ramp does not finish on the dial"


@pytest.mark.parametrize("angle", [1.0, 3.0, 7.0, 10.0])
def test_the_seam_cutter_never_reaches_above_the_rabbet_ledge(monkeypatch, angle):
    """The cutter's ceiling — restated for the wave, because its old form was Z=0 and the wave
    deliberately crests above that.

    Z=0 was never the real limit; it was where the old profile happened to stop. What the cutter
    must not do is eat the TUB, and the height at which that starts is SEAM_LEDGE_Z: below the
    ledge the tub is only its outer skin, because _plate_pocket has already taken the floor and
    inner wall out from behind it, so the cutter takes skin and nothing else. Above the ledge it
    starts taking the tub proper. That is the same reason SEAM_NORTH_RISE_FRAC's ceiling is 1.0,
    asked at a different Y.

    Also pinned to seam_profile_max_z(), so the built solid and the measured curve agree — the
    two are consumed by different callers (_lead_in_relief gates on the measurement) and a drift
    between them would strand the channel mouth exactly where the crest needs it opened."""
    monkeypatch.setattr(C, "TENT_ANGLE_DEG", angle)
    cutter = _below_seam_cutter()
    inside = cutter & Solid.make_box(400.0, C.OUTER_DEPTH, 200.0).translate((-100.0, 0.0, -100.0))
    assert inside.volume > 1e-9, f"{angle} deg: the cutter missed the case entirely"
    got = inside.bounding_box().max.Z
    assert got < C.SEAM_LEDGE_Z, (
        f"{angle} deg: the seam cutter reaches Z={got:.4f}, at or above the rabbet ledge "
        f"{C.SEAM_LEDGE_Z:.4f} — it is eating the tub, not its skin")
    assert abs(got - seam_profile_max_z()) < 0.01, (
        f"{angle} deg: the built cutter tops out at {got:.4f} but the measured profile says "
        f"{seam_profile_max_z():.4f} — solid and curve have drifted apart")


@pytest.mark.parametrize("angle", [1.0, 3.0, 7.0, 10.0])
def test_the_seam_cutter_holds_at_z0_south_of_the_case(monkeypatch, angle):
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
    depends on the angle and both branches must land in the same place.

    Measured SOUTH of y=0 only. The ceiling inside the case is a different question with a
    different answer now that the wave crests above Z=0 — see the test above. Out here, where
    there is no case for the profile to be a parting line of, the hold at Z=0 is absolute."""
    monkeypatch.setattr(C, "TENT_ANGLE_DEG", angle)
    cutter = _below_seam_cutter()
    overhang = cutter & Solid.make_box(400.0, 20.0, 200.0).translate((-100.0, -20.0, -100.0))
    assert overhang.volume > 1e-9, f"{angle} deg: no cutter south of the case at all"
    got = overhang.bounding_box().max.Z
    assert got <= 1e-6, (
        f"{angle} deg: south of the case the seam cutter reaches Z={got:.4f} — the hold at Z=0 "
        f"has failed and it will eat the tub proper at the front edge")


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
    assert gap >= C.TENT_SKIRT_CLEAR_MIN, (
        f"{angle} deg: the dip pulled the skin to {gap:.4f} mm off the desk, under the "
        f"{C.TENT_SKIRT_CLEAR_MIN} mm floor")
    # ...and it costs essentially nothing of whatever lift is set, which is the docstring's other
    # claim. Stated as ABSOLUTE mm eaten, not as a fraction of the dial: the old form
    # `gap > TENT_SKIRT_LIFT * 0.9` scaled its own threshold down with the lift and went trivially
    # true at 0, exactly as the clearance guard did. How much the dip costs is a property of the
    # tangency, and it does not get cheaper because the reveal got narrower.
    eaten = C.TENT_SKIRT_LIFT - gap
    assert eaten < 0.05, (
        f"{angle} deg: the dip pulled the skin {eaten:.4f} mm closer to the desk than the run "
        f"does — it must not, the desk falls faster than the spline")
