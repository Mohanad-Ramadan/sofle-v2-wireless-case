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
from sofle_case.case import (build_bottom_part, build_top_part, tent_ground_z,
                             _below_seam_cutter)

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


def test_the_north_run_rides_at_the_rise():
    """North of the sweep the top case's bottom edge is the dial, flat, and nothing else."""
    top = _top()
    for y in (70.0, 100.0, 120.0):
        got = _lowest_at(top, y)
        assert got is not None, f"no material at y={y}"
        assert abs(got - C.SEAM_NORTH_RISE_Z) < 0.06, (
            f"y={y}: tub reaches down to {got:.3f}, expected the parting line at "
            f"{C.SEAM_NORTH_RISE_Z:.3f}")


def test_the_recess_deepens_but_the_bottom_never_moves():
    """The dial cuts the TUB back and does nothing else. What it exposes is a RECESS — the
    bottom stays SEAM_SKIN + SEAM_FIT_CLEAR behind the skin exactly as it always did, at every
    Y and at every setting of the dial. Growing the bottom out to meet the skin instead was
    tried and rejected: it drags the bottom's outline onto the tub's real footprint."""
    top, bot = _top(), _bottom()
    for y in (70.0, 100.0):
        t = _x_span_at(top, y, ABOVE_LINE)
        b = _x_span_at(bot, y, 1.0)
        assert t is not None and b is not None, f"nothing to measure at y={y}"
        for side, tv, bv in (("west", t[0], b[0]), ("east", t[1], b[1])):
            assert abs(abs(tv - bv) - INSET) < 0.05, (
                f"y={y} {side}: bottom sits {abs(tv - bv):.3f} mm behind the skin, expected the "
                f"usual {INSET} — the dial has moved the bottom's outline")


def test_the_sweep_climbs_monotonically_to_the_rise():
    """Through the blend the edge rises steadily from the southern run to the northern one — no
    dip, no reversal, no step at either end. The higher the dial the steeper this climb, which is
    exactly why it is measured rather than assumed."""
    top = _top()
    ys = [C.TENT_SEAM_Y1 + f * (C.TENT_SEAM_Y2 - C.TENT_SEAM_Y1)
          for f in (0.0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0)]
    zs = [_lowest_at(top, y) for y in ys]
    assert all(z is not None for z in zs), "the sweep has a hole in it"
    for (ya, za), (yb, zb) in zip(zip(ys, zs), zip(ys[1:], zs[1:])):
        assert zb >= za - 0.02, f"edge dips between y={ya:.1f} and y={yb:.1f} ({za:.3f} -> {zb:.3f})"
    start = tent_ground_z(C.TENT_SEAM_Y1) + C.TENT_SKIRT_LIFT
    assert abs(zs[0] - start) < 0.06, "sweep does not start where the southern run ends"
    assert abs(zs[-1] - C.SEAM_NORTH_RISE_Z) < 0.06, "sweep does not finish at the rise"


def test_the_south_is_untouched():
    """The dial acts north of the sweep and nowhere else. Over the southern run the skin still
    descends to TENT_SKIRT_LIFT above the desk, and the bottom still hides INSET behind it — it
    has to, because the skin comes down outside it there with only SEAM_FIT_CLEAR to spare."""
    top, bot = _top(), _bottom()
    for y in (20.0, 40.0):
        got = _lowest_at(top, y)
        want = tent_ground_z(y) + C.TENT_SKIRT_LIFT
        assert got is not None, f"no material at y={y}"
        assert abs(got - want) < 0.06, (
            f"y={y}: skin bottom at {got:.3f}, expected {want:.3f} — the south moved")
    y = 40.0
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
    as far as it can go before it would start eating the tub proper rather than its skin."""
    monkeypatch.setattr(C, "SEAM_NORTH_RISE_Z", frac * C.SEAM_LEDGE_Z)
    got = _below_seam_cutter().bounding_box().max.Z
    assert abs(got - frac * C.SEAM_LEDGE_Z) < 1e-6, (
        f"frac={frac}: the parting profile tops out at {got:.3f}, expected "
        f"{frac * C.SEAM_LEDGE_Z:.3f}")


@pytest.mark.parametrize("bad", ["-0.1", "1.5"])
def test_the_dial_is_bounded_to_the_ledge(bad):
    """Past 1.0 the line would pass the plate rim's top and the bottom case would have nothing
    left to show; below 0 it would climb back down into the wedge. The guard names both ends."""
    src = Path(C.__file__).read_text()
    assert src.count("SEAM_NORTH_RISE_FRAC = ") == 1, "the dial is no longer a single assignment"
    line = [ln for ln in src.splitlines() if ln.startswith("SEAM_NORTH_RISE_FRAC = ")][0]
    src = src.replace(line, f"SEAM_NORTH_RISE_FRAC = {bad}", 1)
    with pytest.raises(AssertionError):
        exec(compile(src, "constants_probe", "exec"), {"__name__": "constants_probe"})
