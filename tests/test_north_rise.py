"""The parting line NORTH of the sweep, and the band of bottom case it exposes.

North of ``TENT_SEAM_Y2`` the line used to sit flat at Z=0, so the visible bottom case there was
exactly the wedge and nothing else. It now rides at ``SEAM_NORTH_RISE_Z`` — a fraction of the
plate rim's own top — and the tub's skin is carved off up to it, deepening the recess that shows
the bottom case behind it.

Only the TUB is cut. The bottom's outline does not move at any setting of the dial, which is its
own test below. The SOUTH does not move either — it keeps its descending skirt and its 0.5 mm
reveal whatever the dial says, and test_seam.py owns that detail.
"""
from functools import cache
from pathlib import Path

import pytest
from build123d import Solid
from sofle_case import constants as C
from sofle_case.case import skin_ground_z, _below_seam_cutter, _seam_sweep_params
from tests.shared_builds import build_bottom_part, build_top_part

INSET = C.SEAM_SKIN + C.SEAM_FIT_CLEAR          # 2.2; how far the bottom hides behind the skin
ABOVE_LINE = C.SEAM_LEDGE_Z + 2.0               # a Z where only the tub exists, on any dial


@cache
def _top():
    return build_top_part("right")


@cache
def _bottom():
    return build_bottom_part("right")


def _slab(part, y, s=0.4):
    """The part inside a thin Y-slice, or None where it has no material there."""
    got = part & Solid.make_box(400.0, s, 160.0).translate((-100.0, y - s / 2, -60.0))
    return got if got.volume > 1e-9 else None


def _lowest_at(part, y: float):
    sl = _slab(part, y)
    return None if sl is None else sl.bounding_box().min.Z


def _x_span_at(part, y: float, z: float):
    """(min X, max X) of the part in a thin Y×Z probe — i.e. where its side walls sit."""
    got = part & Solid.make_box(400.0, 0.4, 0.4).translate((-100.0, y - 0.2, z))
    if got.volume < 1e-9:
        return None
    bb = got.bounding_box()
    return bb.min.X, bb.max.X


def test_the_dial_sets_the_line_at_the_back_edge_and_it_is_still_falling():
    """What the dial means now that there is no flat northern run to ride.

    It used to set the level of a run that carried the parting line from the end of the sweep to
    the back of the case, and this test probed two stations on it. That run is gone: it held the
    line level while the desk kept dropping away underneath, so the visible band RE-OPENED over
    the last stretch and the wave turned back up right at the end — the one thing the reference's
    sweep never does. The ramp now finishes at the back edge itself.

    So the dial sets one point, the line's height where the case runs out, and the thing worth
    guarding besides that is that the curve is still DESCENDING when it gets there."""
    end_y, end_z = _seam_sweep_params()[0][-1]
    assert abs(end_y - C.OUTER_DEPTH) < 1e-9, \
        f"the ramp ends at y={end_y:.2f}, not at the back edge {C.OUTER_DEPTH:.2f}"
    assert abs(end_z - C.SEAM_NORTH_RISE_Z) < 1e-9, \
        f"the ramp ends at {end_z:.4f}, not on the dial at {C.SEAM_NORTH_RISE_Z:.4f}"

    top = _top()
    a = _lowest_at(top, C.OUTER_DEPTH - 6.0)
    b = _lowest_at(top, C.OUTER_DEPTH - 1.2)
    assert a is not None and b is not None, "no material near the back edge"
    assert b < a, f"the parting line rises into the back edge ({a:.3f} -> {b:.3f}) — it must fall"


def test_the_recess_deepens_but_the_bottom_never_moves():
    """The dial cuts the TUB back and does nothing else. What it exposes is a RECESS — the
    bottom stays SEAM_SKIN + SEAM_FIT_CLEAR behind the skin exactly as it always did, at every
    Y and at every setting of the dial. Growing the bottom out to meet the skin instead was
    tried and rejected: it drags the bottom's outline onto the tub's real footprint."""
    # Probe at Z=2.0, not 1.0: at y=100 the flush outer band now reaches up to ~1.3-1.5 (it
    # rides SEAM_REVEAL_H below the parting line, and that dial shrank 2.0 -> 1.5), so a Z=1.0
    # probe there was already inside the flush band, not the recessed plate behind it -- it read
    # 0 mm of inset instead of INSET. 2.0 clears that band at both stations and is still well
    # under SEAM_LEDGE_Z, where the bottom part ends.
    top, bot = _top(), _bottom()
    for y in (70.0, 100.0):
        t = _x_span_at(top, y, ABOVE_LINE)
        b = _x_span_at(bot, y, 2.0)
        assert t is not None and b is not None, f"nothing to measure at y={y}"
        for side, tv, bv in (("west", t[0], b[0]), ("east", t[1], b[1])):
            assert abs(abs(tv - bv) - INSET) < 0.05, (
                f"y={y} {side}: bottom sits {abs(tv - bv):.3f} mm behind the skin, expected the "
                f"usual {INSET} — the dial has moved the bottom's outline")


def test_the_ramp_lands_on_the_rise_from_both_ends():
    """What this test can still say now that the ramp is a wave.

    It used to assert the blend climbs monotonically to the rise, which was true of a two-point
    spline and is deliberately false of the wave — that curve crests above Z=0 and eases back
    down (the lens shape; see SEAM_WAVE_KNOTS). The SHAPE is test_seam's business. What belongs
    HERE, in the dial's own file, is only that the ramp still starts on the southern run and
    still finishes on whatever height the dial puts the northern one at — i.e. that the dial
    keeps its grip on the north end of a curve it does not otherwise control."""
    top = _top()
    ys = [C.TENT_SEAM_Y1, C.TENT_SEAM_Y2]
    zs = [_lowest_at(top, y) for y in ys]
    assert all(z is not None for z in zs), "the ramp has a hole in it"
    start = skin_ground_z(C.TENT_SEAM_Y1) + C.TENT_SKIRT_LIFT
    assert abs(zs[0] - start) < 0.06, "ramp does not start where the southern run ends"
    assert abs(zs[-1] - C.SEAM_NORTH_RISE_Z) < 0.06, "ramp does not finish at the rise"


def test_the_south_is_untouched():
    """The dial acts north of the sweep and nowhere else. Over the southern run the skin still
    descends to TENT_SKIRT_LIFT above the desk, and the bottom still hides INSET behind it — it
    has to, because the skin comes down outside it there with only SEAM_FIT_CLEAR to spare."""
    top, bot = _top(), _bottom()
    for y in (20.0, 40.0):
        got = _lowest_at(top, y)
        want = skin_ground_z(y) + C.TENT_SKIRT_LIFT
        assert got is not None, f"no material at y={y}"
        assert abs(got - want) < 0.06, (
            f"y={y}: skin bottom at {got:.3f}, expected {want:.3f} — the south moved")
    # y=42, NOT y=40, and the station was picked by MEASURING the gap along the wall rather than
    # by reasoning about it — two plausible-looking choices were wrong first.
    #
    # E1 and W1's free-end cuts span y 39.0-40.2, and a cut removes the rim's outer face, so a
    # span at y=40 reads 5.600 instead of 2.200. The arm BODY does not: it is still rim, its
    # outer face is untouched, and only the inboard slot moves — which is why y=42 reads a clean
    # 2.200 despite sitting in the middle of both arms.
    #
    # The other trap is that INSET is measured in X, so it is the perpendicular offset only on a
    # wall whose normal is ±X. y=30 was tried and read 3.879 on the east: correct geometry, wrong
    # ruler, because at y=30 the outline is on the SE diagonal. y=38 was tried and read 2.926 on
    # the west, where the SW corner blend has not yet straightened out. Measured, both walls give
    # exactly 2.200 from y=38.5 north, so y=42 clears every one of those edges.
    y = 42.0
    t = _x_span_at(top, y, ABOVE_LINE)
    b = _x_span_at(bot, y, 1.0)
    assert t is not None and b is not None
    for side, tv, bv in (("west", t[0], b[0]), ("east", t[1], b[1])):
        assert abs(abs(tv - bv) - INSET) < 0.05, (
            f"y={y} {side}: bottom sits {abs(tv - bv):.3f} mm behind the skin, expected the "
            f"usual {INSET} — the dial has reached into the south")


@pytest.mark.parametrize("frac", [0.0, 0.5, 1.0])
def test_the_dial_is_a_fraction_of_the_ledge(monkeypatch, frac):
    """0 leaves the line flat at Z=0 as it always was; 1 puts it on the plate rim's top, which is
    as far as it can go before it would start eating the tub proper rather than its skin.

    Read off the curve's ENDPOINT, not off a slab through the solid and not off the profile's
    global maximum. Two separate reasons, both learned the hard way:
      * the maximum is the crest (u≈0.67), which the dial does not move at all, so a bounding box
        reports it stuck at 3.87 whatever the dial says;
      * there is no flat run left to slab through — the ramp descends into the back edge, so any
        station short of it reads a little high and by an amount that depends on the tail slope."""
    monkeypatch.setattr(C, "SEAM_NORTH_RISE_Z", frac * C.SEAM_LEDGE_Z)
    end_y, end_z = _seam_sweep_params()[0][-1]
    assert abs(end_y - C.OUTER_DEPTH) < 1e-9
    assert abs(end_z - frac * C.SEAM_LEDGE_Z) < 1e-9, (
        f"frac={frac}: the line lands at {end_z:.3f} at the back edge, expected "
        f"{frac * C.SEAM_LEDGE_Z:.3f}")


@pytest.mark.parametrize("bad", ["-3.0", "1.5"])
def test_the_dial_is_bounded_to_the_ledge(bad):
    """Past 1.0 the line would pass the plate rim's top and the bottom case would have nothing
    left to show. The floor is no longer 0.0 — negative IS the rear skirt, and the dial is set
    negative — so the low end tested here is past SEAM_NORTH_RISE_FRAC_MIN, where the rear skin
    would go through the desk. -0.1 used to belong in this list and is now perfectly legal."""
    src = Path(C.__file__).read_text()
    assert src.count("SEAM_NORTH_RISE_FRAC = ") == 1, "the dial is no longer a single assignment"
    line = [ln for ln in src.splitlines() if ln.startswith("SEAM_NORTH_RISE_FRAC = ")][0]
    src = src.replace(line, f"SEAM_NORTH_RISE_FRAC = {bad}", 1)
    with pytest.raises(AssertionError):
        exec(compile(src, "constants_probe", "exec"), {"__name__": "constants_probe"})
