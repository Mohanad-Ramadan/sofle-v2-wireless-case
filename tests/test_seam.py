"""The visible parting line between the two cases — where the top case hands over to the wedge.

Over the southern ``TENT_SEAM_SOUTH_FRAC`` of the depth the TOP case's skin carries on below
Z=0 and lands on the desk, so the front reads as one unbroken piece and no bottom case shows.
It then sweeps back up to Z=0, and from there north the wedge is exposed beneath it.

Seen from the side with the case standing that is the reference's profile exactly: flat on the
desk at the front, a sweep, then a long run rising at the tilt angle. That last run is not
built — it IS the Z=0 plane, which slopes at TENT_ANGLE_DEG once the case stands on its wedge.

The headline invariant: this costs NO height. The skin drops into space that already existed
between Z=0 and the tent plane."""
import math

from build123d import Solid
from sofle_case import constants as C
from sofle_case.canopy import CANOPY_RIDGE_TOP_Z
from sofle_case.case import (build_bottom_part, build_top_part, skirt_extension, tent_ground_z,
                             tent_plane, wedge_deep_z)

OUTER = C.WALL_THICKNESS + C.PCB_XY_CLEARANCE


def _lowest_at(part, y: float, s: float = 0.4):
    """Lowest Z of the part in a thin Y-slice — i.e. where its bottom edge sits at that Y."""
    slab = part & Solid.make_box(400.0, s, 80.0).translate((-100.0, y - s / 2, -40.0))
    if slab.volume < 1e-9:
        return None
    return slab.bounding_box().min.Z


def test_skin_lands_on_the_desk_over_the_southern_stretch():
    """South of y1 the top case reaches the ground, so the bottom case is invisible there."""
    top = build_top_part("right")
    for y in (20.0, 40.0, 60.0, C.TENT_SEAM_Y1 - 1.0):
        got, want = _lowest_at(top, y), tent_ground_z(y)
        assert got is not None, f"no material at y={y}"
        assert abs(got - want) < 0.06, \
            f"y={y}: skin bottom at {got:.3f}, expected the desk at {want:.3f}"


def test_skin_is_gone_north_of_the_sweep():
    """North of y2 the skin stops at Z=0 again and the wedge takes over as the visible band."""
    top = build_top_part("right")
    for y in (C.TENT_SEAM_Y2 + 4.0, 110.0, 120.0):
        got = _lowest_at(top, y)
        assert got is not None, f"no material at y={y}"
        assert abs(got) < 0.02, f"y={y}: skin still hangs to {got:.3f}, expected Z=0"


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
    assert abs(zs[0] - tent_ground_z(C.TENT_SEAM_Y1)) < 0.06, "sweep does not start on the desk"
    assert abs(zs[-1]) < 0.06, "sweep does not finish at Z=0"


def test_the_skin_never_breaks_through_the_desk():
    """The sweep is a spline, so it is worth proving it stays above the tent plane rather than
    trusting the tangents. One vertex through the plane becomes the sole contact point and the
    keyboard rocks on it."""
    o, n = tent_plane()
    for side in ("right", "left"):
        verts, _f = build_top_part(side).tessellate(0.2)
        worst = min((v.X - o[0]) * n[0] + (v.Y - o[1]) * n[1] + (v.Z - o[2]) * n[2] for v in verts)
        assert worst > -1e-4, f"{side}: skin dips {-worst:.4f} mm through the desk"


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
    # and the deepest the SKIN itself reaches is the desk at y1, well above the wedge's floor
    assert tb.min.Z > wedge_deep_z(), "the skin reaches deeper than the wedge — impossible"
    assert abs(tb.min.Z - tent_ground_z(C.TENT_SEAM_Y1)) < 0.05, \
        f"skin bottoms out at {tb.min.Z:.3f}, expected the desk at y1"


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
    tell: top on Z=0, bottom on the desk at y1, and nothing at all north of y2."""
    sk = skirt_extension()
    assert len(sk.solids()) == 1
    bb = sk.bounding_box()
    assert abs(bb.max.Z) < 1e-6, f"skirt should top out at Z=0, got {bb.max.Z:.4f}"
    assert abs(bb.max.Y - C.TENT_SEAM_Y2) < 0.5, \
        f"skirt reaches y={bb.max.Y:.2f}, expected it to die at y2={C.TENT_SEAM_Y2:.2f}"
    assert bb.min.Z > tent_ground_z(C.TENT_SEAM_Y1) - 0.05


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

    for y in (45.0, 55.0, C.TENT_SEAM_Y1 - 1.0):
        g = tent_ground_z(y)
        for name, seated, mouth, sign in (("east", east(y, g + 2.0), east(y, g + 0.1), 1.0),
                                          ("west", west(y, g + 2.0), west(y, g + 0.1), -1.0)):
            assert seated is not None and mouth is not None, f"{name} y={y}: probe off the wall"
            relief = (mouth - seated) * sign
            assert relief >= C.SEAM_LEAD_IN - 0.02, \
                f"{name} wall y={y}: mouth relieved only {relief:.3f}, want {C.SEAM_LEAD_IN}"
            assert relief <= C.SEAM_LEAD_IN + 0.02, \
                f"{name} wall y={y}: relief {relief:.3f} overshoots — it is eating the skin"
    # closes back to the nominal face rather than staying flared
    y = 55.0
    g = tent_ground_z(y)
    assert abs(east(y, g + C.SEAM_LEAD_IN + 0.2) - east(y, g + 2.0)) < 0.02, "relief never closes"
    # and the opening clears the wedge it has to accept
    assert east(55.0, tent_ground_z(55.0) + 0.1) > bottom.bounding_box().max.X, \
        "mouth is narrower than the wedge it accepts"


def test_the_lead_in_tracks_the_sweep_not_a_flat_plane():
    """The relief is the seam cutter shifted up by SEAM_LEAD_IN, so it follows the blend as
    well as the flat run. Referenced to a plane instead it would drift off the mouth as the
    seam climbs, and the guidance would quietly disappear exactly where the channel narrows."""
    top = build_top_part("right")

    def east(y, z, s=0.1):
        sl = top & Solid.make_box(40.0, s, s).translate((130.0, y - s / 2, z - s / 2))
        return sl.bounding_box().min.X if sl.volume > 1e-12 else None

    checked = 0
    for y in (C.TENT_SEAM_Y1 + 3.0, C.TENT_SEAM_Y1 + 5.0):
        seam = _lowest_at(top, y)
        if seam is None or seam > -1.0:
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
    assert abs(south - tent_ground_z(C.TENT_SEAM_Y1 - 8.0)) < 0.06, \
        "skin is not on the desk south of the handover"
    assert abs(north) < 0.02, "skin still hangs below Z=0 north of the sweep"
