"""OLED modes, plan Step 2: grown tray north wall (D6) and the short-left USB notch (D7)."""
import math

import pytest
from build123d import Solid

from sofle_case import constants as C
from sofle_case.case import _usb_notch
from sofle_case.tray import _dedupe, _outer_poly_pts, outline
from tests.shared_builds import build_case_half
from tests.test_oled import CASE_BASE, NONE_OUTLINE

SIDES = ("left", "right")
OLED_ON = ("long", "short")
NORTH_Y = 118.315
MCU_X = C.pcb_to_case(*C.MCU_POS)[0]


def _phys_x(side, x):
    return C.OUTER_WIDTH - x if side == "left" else x


def _edges(pts):
    return list(zip(pts, pts[1:] + pts[:1]))


def _box(x0, x1, y0, y1, z0, z1):
    return Solid.make_box(x1 - x0, y1 - y0, z1 - z0).translate((x0, y0, z0))


def _jack_box(side, oled):
    """The jack body (as pcb_phantom._usb_c_stub draws it) at ``oled``'s band, physical frame."""
    lo, hi = C.usb_jack_z(side, oled)
    x0, x1 = sorted(_phys_x(side, MCU_X + s * C.USB_C_W / 2) for s in (-1, 1))
    return _box(x0, x1, C.MCU_BODY_N_Y, C.MCU_BODY_N_Y + C.USB_JACK_Y_PROTRUDE, lo, hi)


# ------------------------------------------------------------------ outline
def test_none_outline_is_baseline_and_default():
    assert outline() is outline("none")
    for got, want in zip(outline("none").pts, NONE_OUTLINE, strict=True):
        assert got == pytest.approx(want, abs=1e-9)
    assert _outer_poly_pts() == list(outline("none").pts)
    assert _dedupe(list(NONE_OUTLINE)) == list(NONE_OUTLINE)


def test_invalid_mode_raises():
    with pytest.raises(ValueError):
        outline("tall")


@pytest.mark.parametrize("oled", OLED_ON)
def test_oled_north_is_one_edge(oled):
    pts = outline(oled).pts
    north = [(a, b) for a, b in _edges(pts)
             if abs(a[1] - NORTH_Y) < 1e-6 and abs(b[1] - NORTH_Y) < 1e-6]
    assert len(north) == 1
    (ax, _), (bx, _) = north[0]
    assert sorted((ax, bx)) == pytest.approx([13.65, 73.65], abs=1e-6)
    assert outline(oled).north_run(MCU_X) == pytest.approx(NORTH_Y, abs=1e-9)
    assert outline(oled).north_run(60.0) == pytest.approx(NORTH_Y, abs=1e-9)
    assert not any(abs(x - 54.65) < 1e-6 for x, _ in pts)      # the reflex step is gone


@pytest.mark.parametrize("oled", OLED_ON)
def test_oled_outline_has_no_degenerate_vertices_and_south_unchanged(oled):
    pts = outline(oled).pts
    n = len(pts)
    assert n == len(NONE_OUTLINE) - 2
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        a = (p1[0] - p0[0], p1[1] - p0[1])
        b = (p2[0] - p1[0], p2[1] - p1[1])
        assert math.hypot(*a) > 1e-3
        assert abs(a[0] * b[1] - a[1] * b[0]) > 1e-6 * math.hypot(*a) * math.hypot(*b)
    for got, want in zip(pts[:12], NONE_OUTLINE[:12], strict=True):
        assert got == pytest.approx(want, abs=1e-9)
    assert pts[12] == pytest.approx((73.65, NORTH_Y), abs=1e-9)
    assert pts[13] == pytest.approx((13.65, NORTH_Y), abs=1e-9)
    assert pts[14] == pytest.approx(NONE_OUTLINE[16], abs=1e-9)
    assert (73.65, NORTH_Y) in [tuple(round(c, 9) for c in p) for p in outline(oled).reflex]


# ------------------------------------------------------------------ built case
@pytest.mark.parametrize("side", SIDES)
@pytest.mark.parametrize("oled", OLED_ON)
def test_oled_case_valid_bbox_and_grown_north(side, oled):
    case = build_case_half(side, oled)
    assert case.is_valid
    assert len(case.solids()) == 1
    bb = case.bounding_box()
    assert bb.max.Y == pytest.approx(125.8, abs=1e-3)
    assert (bb.min.X, bb.min.Y, bb.min.Z) == pytest.approx(CASE_BASE[side][1], abs=1e-3)
    assert (bb.max.X, bb.max.Z) == pytest.approx((153.8, 15.7), abs=1e-3)
    assert case.volume > CASE_BASE[side][0]
    # The north wall at the cover column now reaches y 123.465 (polygon 118.315 + 5.15).
    outer = NORTH_Y + C.WALL_THICKNESS + C.PCB_XY_CLEARANCE
    x = _phys_x(side, 16.0)
    probe_in = _box(x - 0.5, x + 0.5, outer - 1.0, outer - 0.5, 5.0, 6.0)
    probe_out = _box(x - 0.5, x + 0.5, outer + 0.05, outer + 1.0, 0.0, 15.7)
    assert (case & probe_in).volume == pytest.approx(0.5, abs=1e-3)
    assert (case & probe_out).volume < 1e-6


@pytest.mark.parametrize("side", SIDES)
@pytest.mark.parametrize("oled", OLED_ON)
def test_oled_feet_sit_in_solid_floor(side, oled):
    case = build_case_half(side, oled)
    r = C.FOOT_DIA / 2
    for x, y in C.FOOT_POSITIONS:
        px = _phys_x(side, x)
        seat = Solid.make_cylinder(r - 0.05, C.FOOT_DEPTH - 0.1).translate((px, y, 0.05))
        under = Solid.make_cylinder(r, 1.0).translate((px, y, C.FOOT_DEPTH + 0.01))
        assert (case & seat).volume < 1e-6
        assert (case & under).volume == pytest.approx(under.volume, rel=1e-4)


# ------------------------------------------------------------------ USB notch (D7)
def test_notch_only_short_left():
    assert _usb_notch("left", "short") is not None
    for side, oled in (("right", "short"), ("left", "long"), ("right", "long"),
                       ("left", "none"), ("right", "none")):
        assert _usb_notch(side, oled) is None


def test_short_left_notch_clears_jack_phantom():
    case = build_case_half("left", "short")
    jack = _jack_box("left", "short")
    assert jack.bounding_box().min.Z < C.MAIN_RIM_Z           # it really dips into the wall
    assert (case & jack).volume < 1e-6
    lo, _ = C.usb_port_z("left", "short")
    x = _phys_x("left", MCU_X)
    slot = _box(x - 0.5, x + 0.5, 116.5, 123.0, lo + 0.05, C.MAIN_RIM_Z - 0.05)
    assert (case & slot).volume < 1e-6


def test_short_right_has_no_notch():
    case = build_case_half("right", "short")
    lo, _ = C.usb_port_z("right", "short")
    assert lo >= C.MAIN_RIM_Z
    wall = _box(MCU_X - 0.5, MCU_X + 0.5, 117.0, 118.0, 14.5, 15.5)
    assert (case & wall).volume == pytest.approx(1.0, abs=1e-3)
    assert (case & _jack_box("right", "short")).volume < 1e-6
