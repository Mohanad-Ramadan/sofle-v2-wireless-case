"""OLED modes, plan Step 3: cover profile, display window, roof and north fit (D3/D4/D5/D9)."""
import pytest
from build123d import Solid

from sofle_case import constants as C
from sofle_case import mcu_encoder_cover as MEC
from sofle_case import tray as Tray
from tests.shared_builds import build_case_half, build_mcu_encoder_cover

SIDES = ("left", "right")
OLED_ON = ("long", "short")
RIDGE = {"none": 25.96, "long": 27.40, "short": 24.20}
WINDOW_X_PHYS = {"right": (18.680, 24.680), "left": (124.580, 130.580)}
WINDOW_Y = (89.075, 111.455)


def _phys_x(side, x):
    return C.OUTER_WIDTH - x if side == "left" else x


def _phys_span(side, x0, x1):
    return tuple(sorted((_phys_x(side, x0), _phys_x(side, x1))))


def _box(x0, x1, y0, y1, z0, z1):
    return Solid.make_box(x1 - x0, y1 - y0, z1 - z0).translate((x0, y0, z0))


def _module_phantom(side, oled):
    """Display-only slab over the module footprint, physical frame, top at the OLED top."""
    x0, x1, y0, y1 = C.oled_module_xy(side)
    x0, x1 = _phys_span(side, x0, x1)
    top = C.oled_top_z(oled)
    return _box(x0, x1, y0, y1, top - C.OLED_PHANTOM_THK, top)


# ------------------------------------------------------------------ profile
def test_none_profile_reproduces_todays_values():
    for side in SIDES:
        p = MEC.profile(side)
        assert p is MEC.profile(side, "none")
        assert p.ridge == pytest.approx(RIDGE["none"])
        assert p.ramp_top_y == C.COVER_RAMP_TOP_Y
        assert p.north_y == pytest.approx(118.8)
        assert p.usb_port_z == C.cover_usb_port_z(side)
        assert p.window_xy is p.module_xy is None
        assert MEC._cover_outer_polygon(p) == MEC._cover_outer_polygon()


@pytest.mark.parametrize("oled", OLED_ON)
@pytest.mark.parametrize("side", SIDES)
def test_oled_profile_values(side, oled):
    p = MEC.profile(side, oled)
    assert p.ridge == pytest.approx(RIDGE[oled], abs=1e-9)
    assert p.ramp_top_y == pytest.approx(80.765)
    assert p.usb_port_z == C.cover_usb_port_z(side, oled)
    assert p.window_xy == C.oled_window_xy(side)
    with pytest.raises(ValueError):
        MEC.build_mcu_encoder_cover(side, oled="tall")


# ------------------------------------------------------------------ north fit (no overhang)
@pytest.mark.parametrize("oled", ("none", *OLED_ON))
def test_cover_north_is_flush_with_grown_tray(oled):
    mcu_x = C.pcb_to_case(*C.MCU_POS)[0]
    tray_outer = (C.TRAY_NORTH_LOW_Y + C.north_wall_extra(oled).get(14, 0.0)
                  + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE)
    expected = tray_outer - C.RIM_FACET_RUN
    assert (Tray.outline(oled).north_run(mcu_x) + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
            == pytest.approx(tray_outer, abs=1e-9))
    assert MEC._north_landing_y(oled) == pytest.approx(expected, abs=1e-9)
    if oled != "none":
        assert expected == pytest.approx(121.465, abs=1e-6)
    for side in SIDES:
        cover = build_mcu_encoder_cover(side, oled=oled)
        assert cover.bounding_box().max.Y == pytest.approx(expected, abs=0.01)
        # No overhang: the cover's north face lies inside the tray's outer wall.
        case_bb = build_case_half(side, oled=oled).bounding_box()
        assert cover.bounding_box().max.Y <= case_bb.max.Y


@pytest.mark.parametrize("oled", OLED_ON)
@pytest.mark.parametrize("side", SIDES)
def test_module_footprint_margins_to_inner_walls(side, oled):
    p = MEC.profile(side, oled)
    inner = MEC._cover_inner_polygon(p)
    west = min(x for x, _ in inner)
    east = max(x for x, _ in inner)
    north = max(y for _, y in inner)
    mx0, mx1, _, my1 = p.module_xy
    assert mx0 - west >= 0.5
    assert east - mx1 >= 0.5
    assert north - my1 == pytest.approx(C.OLED_NORTH_CLEAR, abs=0.01)


# ------------------------------------------------------------------ window
@pytest.mark.parametrize("oled", OLED_ON)
@pytest.mark.parametrize("side", SIDES)
def test_window_is_straight_walled_through_opening_at_physical_span(side, oled):
    cover = build_mcu_encoder_cover(side, oled=oled)
    assert cover.is_valid and len(cover.solids()) == 1
    ridge = MEC.profile(side, oled).ridge
    under = ridge - C.COVER_TOP_THICKNESS
    wx0, wx1 = WINDOW_X_PHYS[side]
    wy0, wy1 = WINDOW_Y
    # Slabs through the roof below the groove floor; the removed material is the opening.
    for z0, z1 in ((under + 0.05, under + 0.25), (ridge - C.COVER_MARK_DEPTH - 0.25,
                                                  ridge - C.COVER_MARK_DEPTH - 0.05)):
        region = _box(wx0 - 1.5, wx1 + 1.5, wy0 - 1.5, wy1 + 1.5, z0, z1)
        hole = region - cover
        bb = hole.bounding_box()
        assert bb.min.X == pytest.approx(wx0, abs=0.05)
        assert bb.max.X == pytest.approx(wx1, abs=0.05)
        assert bb.min.Y == pytest.approx(wy0, abs=0.05)
        assert bb.max.Y == pytest.approx(wy1, abs=0.05)
        assert bb.size.X == pytest.approx(C.OLED_DISPLAY_W, abs=0.05)
        assert bb.size.Y == pytest.approx(C.OLED_DISPLAY_L, abs=0.05)
        # Prism volume: the walls are vertical, not drafted.
        assert hole.volume == pytest.approx(6.0 * 22.38 * (z1 - z0), rel=1e-3)
    # Through: nothing over the window from the cavity to above the ridge.
    assert (cover & _box(wx0 + 0.05, wx1 - 0.05, wy0 + 0.05, wy1 - 0.05,
                         under - 0.5, ridge + 1.0)).volume < 1e-6


@pytest.mark.parametrize("side", SIDES)
def test_none_cover_has_no_window(side):
    cover = build_mcu_encoder_cover(side)
    ridge = MEC.profile(side).ridge
    wx0, wx1 = WINDOW_X_PHYS[side]
    slab = _box(wx0, wx1, WINDOW_Y[0], WINDOW_Y[1], ridge - C.COVER_TOP_THICKNESS + 0.05,
                ridge - C.COVER_MARK_DEPTH - 0.05)
    assert (slab - cover).volume < 1e-6


# ------------------------------------------------------------------ roof over the module
@pytest.mark.parametrize("oled", OLED_ON)
@pytest.mark.parametrize("side", SIDES)
def test_roof_clears_module_top_by_roof_clearance(side, oled):
    p = MEC.profile(side, oled)
    top = C.oled_top_z(oled)
    mx0, mx1, my0, my1 = p.module_xy
    for i in range(9):
        y = my0 + (my1 - my0) * i / 8
        assert MEC._cover_roof_z(y, p) - C.COVER_TOP_THICKNESS >= top + 0.6 - 1e-9
    assert p.ridge - C.COVER_TOP_THICKNESS == pytest.approx(top + 0.6, abs=1e-9)
    cover = build_mcu_encoder_cover(side, oled=oled)
    for i in range(5):
        for j in range(9):
            x = _phys_x(side, mx0 + (mx1 - mx0) * i / 4)
            y = my0 + (my1 - my0) * j / 8
            probe = _box(x - 0.1, x + 0.1, y - 0.1, y + 0.1, top, top + 0.6 - 0.02)
            assert (cover & probe).volume < 1e-9, (x, y)


@pytest.mark.parametrize("oled", OLED_ON)
@pytest.mark.parametrize("side", SIDES)
def test_oled_phantom_does_not_touch_cover(side, oled):
    cover = build_mcu_encoder_cover(side, oled=oled)
    assert (cover & _module_phantom(side, oled)).volume < 1e-6


@pytest.mark.parametrize("oled", OLED_ON)
@pytest.mark.parametrize("side", SIDES)
def test_ridge_height(side, oled):
    cover = build_mcu_encoder_cover(side, oled=oled)
    assert cover.bounding_box().max.Z == pytest.approx(RIDGE[oled], abs=0.01)


@pytest.mark.parametrize("oled", OLED_ON)
@pytest.mark.parametrize("side", SIDES)
def test_oled_mark_is_not_shifted(side, oled):
    """OLED modes keep the `none` mark position (it may cross the window); strokes that run
    out through the north edge only extend to the grown cover's north face."""
    from sofle_case import cover_mark as M
    base = M.strokes(side, MEC._mark_inside(MEC.profile(side)))
    lit = M.strokes(side, MEC._mark_inside(MEC.profile(side, oled)))
    assert len(lit) == len(base)
    for (pb, wb), (pl, wl) in zip(base, lit):
        assert wl == wb
        assert min(y for _, y in pl) == pytest.approx(min(y for _, y in pb), abs=1e-6)
        assert max(y for _, y in pl) >= max(y for _, y in pb) - 1e-6
