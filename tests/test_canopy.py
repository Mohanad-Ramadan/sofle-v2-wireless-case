"""Tests for the PARKED standalone fastback canopy (the MCU cover).

The upper case is in its pre-cover state, so this module is not wired into the case build —
these tests validate the canopy shape in isolation. Its parameters live on the canopy module
(``CAN.CANOPY_*``), not in constants.py.

Design: the cap SETS ON the case top. South→north: a low tongue resting on the cover → an
ease-OUT ramp that rises fast off the foot (clears the bay components) then eases into the
flat roof → flat roof at the ridge → short round-over + vertical north wall. The N/W walls
land on the flat wall-top at the chamfer FIRST point (chamfer left exposed); nothing drops
below the seat plane; the NW corner is rounded to the case's own corner radius.
"""
import pytest
from build123d import Solid, GeomType
from OCP.BRepCheck import BRepCheck_Analyzer

from sofle_case import constants as C
from sofle_case import canopy as CAN
from sofle_case.canopy import build_canopy


def _mcu_cx() -> float:
    return C.pcb_to_case(*C.MCU_POS)[0]


def _roof_top(part, x, y, sx=0.3, sy=0.3):
    col = Solid.make_box(sx, sy, 40).translate((x - sx / 2, y - sy / 2, 0))
    inter = part & col
    s = [] if inter is None else list(inter.solids())
    return max(ss.bounding_box().max.Z for ss in s) if s else None


def _solid_at(part, x, y, z, s=0.3):
    box = Solid.make_box(s, s, s).translate((x - s / 2, y - s / 2, z - s / 2))
    inter = part & box
    return inter is not None and sum(ss.volume for ss in inter.solids()) > 1e-6


def _curved_faces(part):
    return [f for f in part.faces() if f.geom_type != GeomType.PLANE]


@pytest.mark.parametrize("hollow", [False, True])
def test_canopy_is_valid_single_solid(hollow):
    c = build_canopy(hollow=hollow)
    assert len(c.solids()) == 1
    assert BRepCheck_Analyzer(c.wrapped).IsValid()


def test_canopy_rests_on_seat_nothing_below():
    """The cap sets ON the case top: its lowest surface is the seat plane, nothing drops
    below it (no chamfer fill)."""
    c = build_canopy()
    assert abs(c.bounding_box().min.Z - CAN.CANOPY_SEAT_Z) < 0.01, "canopy drops below the seat plane"


def test_canopy_tongue_rests_on_cover():
    """The south tongue is a thin slab resting on the cover: its top is one wall above the
    seat (its underside sits on the cover)."""
    c = build_canopy()
    for y in (CAN.CANOPY_SOUTH_Y + 1, (CAN.CANOPY_SOUTH_Y + CAN.CANOPY_RAMP_FOOT_Y) / 2):
        z = _roof_top(c, _mcu_cx(), y)
        assert z is not None and abs(z - CAN.CANOPY_TONGUE_TOP_Z) < 0.05, f"tongue not flat at y={y}: {z}"


def test_canopy_ramp_rises_fast_off_foot():
    """The 'mirrored slide' ramp is an ease-OUT: monotonic, well ABOVE the straight foot→ridge
    line early (rises fast so the underside clears components), and tangent into the flat roof."""
    c = build_canopy()
    foot, top = CAN.CANOPY_RAMP_FOOT_Y, CAN.CANOPY_RAMP_TOP_Y
    z_low, z_ridge = CAN.CANOPY_TONGUE_TOP_Z, CAN.CANOPY_RIDGE_TOP_Z
    ys = [foot + t * (top - foot) for t in (0.0, 0.25, 0.5, 0.75, 1.0)]
    zs = [_roof_top(c, _mcu_cx(), y) for y in ys]
    assert all(z is not None for z in zs)
    assert all(b >= a - 1e-6 for a, b in zip(zs, zs[1:])), f"ramp not monotonic: {zs}"
    assert abs(zs[0] - z_low) < 0.2, "ramp foot not at the tongue level"
    assert abs(zs[-1] - z_ridge) < 0.2, "ramp top not at the ridge"

    def straight(t):
        return z_low + (z_ridge - z_low) * t

    z20 = _roof_top(c, _mcu_cx(), foot + 0.2 * (top - foot))
    assert z20 > straight(0.2) + 0.15, f"ramp does not rise fast off the foot: {z20} vs {straight(0.2):.2f}"
    # tangent into the roof: nearly at the ridge by 85% of the run
    z85 = _roof_top(c, _mcu_cx(), foot + 0.85 * (top - foot))
    assert z85 > z_low + 0.9 * (z_ridge - z_low), "ramp does not ease flat into the roof"


def test_canopy_ramp_underside_clears_foot_components():
    """The mirrored ramp lifts the underside clear over the ramp-foot region (slide/reset/JST
    at ~Y70): the underside there is well above the old low belly (~12.6)."""
    c = build_canopy()
    # lowest solid Z in the topmost band at the MCU column over y=70 (the shell underside)
    y = 70.0
    zs = [z / 10 for z in range(130, 230)]
    solid = [z for z in zs if _solid_at(c, _mcu_cx(), y, z, s=0.2)]
    assert solid, "no shell over the ramp foot"
    assert min(solid) > 14.5, f"underside still low over the ramp foot: {min(solid)}"


def test_canopy_flat_roof_at_ridge():
    c = build_canopy()
    for y in (90.0, 105.0, 115.0):
        z = _roof_top(c, _mcu_cx(), y)
        assert z is not None and abs(z - CAN.CANOPY_RIDGE_TOP_Z) < 0.05, f"roof not flat at y={y}: {z}"


def test_canopy_ridge_is_tallest_point():
    c = build_canopy()
    assert abs(c.bounding_box().max.Z - CAN.CANOPY_RIDGE_TOP_Z) < 0.01


def test_canopy_west_sets_on_chamfer_first_point():
    """The west wall lands at the chamfer FIRST point (inner chamfer line), resting on the flat
    wall-top — NOT flush with the outer face, and it does not drop into the chamfer."""
    c = build_canopy()
    assert abs(c.bounding_box().min.X - CAN.CANOPY_WEST_OUTER_X) < 0.05
    assert _solid_at(c, CAN.CANOPY_WEST_OUTER_X + 0.3, 100.0, CAN.CANOPY_SEAT_Z + 0.3), "west wall not on the seat"
    assert not _solid_at(c, CAN.CANOPY_WEST_OUTER_X + 0.3, 100.0, CAN.CANOPY_SEAT_Z - 0.5), "west wall drops below the seat"


def test_canopy_north_sets_on_chamfer_first_point():
    """The north wall lands at the chamfer first point, is vertical (tall solid span at fixed
    y), and rests on the seat."""
    c = build_canopy()
    assert abs(c.bounding_box().max.Y - CAN.CANOPY_NORTH_OUTER_Y) < 0.05
    yin = CAN.CANOPY_NORTH_OUTER_Y - 0.3
    assert _solid_at(c, _mcu_cx(), yin, CAN.CANOPY_SEAT_Z + 0.3), "north wall not on the seat"
    assert _solid_at(c, _mcu_cx(), yin, 17.0), "north wall not tall/vertical"
    assert not _solid_at(c, _mcu_cx(), yin, CAN.CANOPY_SEAT_Z - 0.5), "north wall drops below the seat"


def test_canopy_nw_corner_is_rounded():
    """The NW corner is rounded to the case's corner radius (the would-be sharp corner is cut
    back, and a curved corner face exists), so it nests on the case's rounded corner."""
    c = build_canopy()
    r = CAN.CANOPY_CORNER_R
    xw, yn = CAN.CANOPY_WEST_OUTER_X, CAN.CANOPY_NORTH_OUTER_Y
    assert not _solid_at(c, xw + 0.3, yn - 0.3, 14.0), "NW corner is sharp, not rounded"
    assert _solid_at(c, xw + 0.3, 100.0, 14.0), "west wall missing away from the corner"
    nw = [f for f in _curved_faces(c)
          if f.center().X < xw + r and f.center().Y > yn - r]
    assert nw, "no rounded corner face at the NW"


def test_canopy_east_is_vertical_planar():
    """The east (switch-facing) side is a plain vertical wall — no curved flare."""
    c = build_canopy()
    assert abs(c.bounding_box().max.X - CAN.CANOPY_EAST_X) < 0.05
    east_curved = [f for f in _curved_faces(c) if f.center().X > CAN.CANOPY_EAST_X - 1.0]
    assert not east_curved, "east side has a curved flare; it should be a plain vertical wall"


def test_canopy_is_hollow_shell():
    """The printed canopy is a hollow shell — open under the roof — not a solid brick."""
    c = build_canopy()
    assert not _solid_at(c, _mcu_cx(), 100.0, CAN.CANOPY_RIDGE_TOP_Z - CAN.CANOPY_ROOF_WALL - 1.0), \
        "canopy is not hollow under the roof"
    assert build_canopy().volume < build_canopy(hollow=False).volume, "hollow not lighter than envelope"
