"""OLED window (plan .omc/plans/oled-mcu-cover.md): `none` baselines and mode constants."""
from pathlib import Path

import pytest

from sofle_case import constants as C
from tests.shared_builds import build_case_half, build_mcu_encoder_cover

ROOT = Path(__file__).resolve().parents[1]
SIDES = ("left", "right")
OLED_ON = ("long", "short")

# Baselines at 00b0009 (plan §1).
COVER_BASE = {
    "right": (5397.466460655949, (10.5, 37.392, 10.7), (34.6, 118.8, 25.96)),
    "left": (5411.253235709993, (119.2, 37.392, 10.7), (143.3, 118.8, 25.96)),
}
CASE_BASE = {
    "right": (102053.14202508285, (0.0, -2.597688, 0.0), (153.8, 125.8, 15.7)),
    "left": (102053.14202498141, (0.0, -2.597688, 0.0), (153.8, 125.8, 15.7)),
}
NONE_OUTLINE = [
    (11.150000000000002, 33.650000000000006), (5.150000000000006, 30.150000000000006),
    (21.156659004116612, 2.5523120618679265), (54.88556088553643, 20.150000000000006),
    (111.03812962263311, 20.150000000000006), (148.65, 30.047860625622874),
    (148.65, 109.15), (110.65, 109.15), (110.65, 118.15), (91.65, 118.15), (91.65, 120.65),
    (73.65, 120.65), (73.65, 118.15), (54.650000000000006, 118.15),
    (54.650000000000006, 115.65), (13.650000000000006, 115.65),
    (13.650000000000006, 35.150000000000006),
]


def _phys_x(side, x):
    return C.OUTER_WIDTH - x if side == "left" else x


def _assert_baseline(part, base):
    vol, lo, hi = base
    assert part.is_valid
    assert part.volume == pytest.approx(vol, abs=1e-6)
    bb = part.bounding_box()
    assert (bb.min.X, bb.min.Y, bb.min.Z) == pytest.approx(lo, abs=1e-3)
    assert (bb.max.X, bb.max.Y, bb.max.Z) == pytest.approx(hi, abs=1e-3)


# ------------------------------------------------------------------ Step 0: `none` baselines
@pytest.mark.parametrize("side", SIDES)
def test_none_cover_matches_baseline(side):
    _assert_baseline(build_mcu_encoder_cover(side), COVER_BASE[side])


@pytest.mark.parametrize("side", SIDES)
def test_none_case_matches_baseline(side):
    _assert_baseline(build_case_half(side), CASE_BASE[side])


def test_none_outline_vertices_pinned():
    from sofle_case.tray import _outer_poly_pts

    pts = _outer_poly_pts()
    assert len(pts) == 17
    for got, want in zip(pts, NONE_OUTLINE, strict=True):
        assert got == pytest.approx(want, abs=1e-9)


# ------------------------------------------------------------------ Step 1: constants
def test_default_mode_is_none_and_invalid_modes_raise():
    assert C.OLED_MODE == "none"
    assert C.MCU_SHORT_DROP == pytest.approx(3.2)
    for fn in (C.mcu_pcb_top_z, C.oled_top_z, C.cover_ramp_top_y, C.north_wall_extra):
        with pytest.raises(ValueError):
            fn("tall")
    for fn in (C.usb_jack_z, C.usb_port_z, C.cover_usb_port_z, C.cover_ridge_top_z):
        with pytest.raises(ValueError):
            fn("right", "tall")
    with pytest.raises(ValueError):
        C.oled_top_z("none")


def test_j3_pads_match_drill_file():
    import importlib.util

    spec = importlib.util.spec_from_file_location("parse_gerber", ROOT / "scripts" / "parse_gerber.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    holes = mod.parse_pth_holes(ROOT / "data" / "raw" / "SofleKeyboard-PTH.drl", 1.0)
    j3 = sorted((x, y) for x, y in holes if abs(y - C.J3_PADS_PCB[0][1]) < 0.05 and 4 < x < 16)
    assert len(j3) == len(C.J3_PADS_PCB)
    for got, want in zip(j3, C.J3_PADS_PCB, strict=True):
        assert got == pytest.approx(want, abs=0.01)


def test_pads_exclude_cs_per_half():
    assert C.oled_pads("right") == (0, 1, 2, 3)
    assert C.oled_pads("left") == (1, 2, 3, 4)
    for side in SIDES:
        nets = C.j3_nets(side)
        chosen = {nets[i] for i in C.oled_pads(side)}
        assert chosen == set(C.OLED_MODULE_NETS) and "CS" not in chosen


@pytest.mark.parametrize("side", SIDES)
def test_window_size_and_west_inset_in_physical_frame(side):
    x0, x1, y0, y1 = C.oled_window_xy(side)
    assert x1 - x0 == pytest.approx(6.0)
    assert y1 - y0 == pytest.approx(22.38)
    mx0, mx1, my0, my1 = C.oled_module_xy(side)
    win_w = min(_phys_x(side, x0), _phys_x(side, x1))
    mod_w = min(_phys_x(side, mx0), _phys_x(side, mx1))
    assert win_w - mod_w == pytest.approx(2.0)
    assert (my0, my1) == pytest.approx((80.765, 119.765))
    assert (y0, y1) == pytest.approx((89.075, 111.455))


def test_window_physical_spans_and_left_is_not_a_mirror():
    rx0, rx1, _, _ = C.oled_window_xy("right")
    lx0, lx1, _, _ = C.oled_window_xy("left")
    left_phys = sorted((_phys_x("left", lx0), _phys_x("left", lx1)))
    assert (rx0, rx1) == pytest.approx((18.680, 24.680))
    assert left_phys == pytest.approx([124.580, 130.580])
    mirror_of_right = sorted((C.OUTER_WIDTH - rx0, C.OUTER_WIDTH - rx1))
    assert abs(left_phys[0] - mirror_of_right[0]) == pytest.approx(4.54)


@pytest.mark.parametrize("side", SIDES)
@pytest.mark.parametrize("oled, ridge", [("none", 25.96), ("long", 27.40), ("short", 24.20)])
def test_ridge_per_mode(side, oled, ridge):
    assert C.cover_ridge_top_z(side, oled) == pytest.approx(ridge, abs=1e-9)
    assert C.cover_ridge_top_z(side) == C.cover_ridge_top_z(side, "none")


@pytest.mark.parametrize("side", SIDES)
def test_short_drops_jack_and_ports_by_3_2(side):
    for fn in (C.usb_jack_z, C.usb_port_z, C.cover_usb_port_z):
        none, short, long_ = fn(side), fn(side, "short"), fn(side, "long")
        assert short == pytest.approx(tuple(z - 3.2 for z in none))
        assert long_ == none
    assert C.usb_jack_z(side) == (
        (C.USB_JACK_FLIPPED_LO_Z, C.USB_JACK_FLIPPED_HI_Z) if side == "left"
        else (C.USB_JACK_NEUTRAL_LO_Z, C.USB_JACK_NEUTRAL_HI_Z))
    assert C.mcu_pcb_top_z("short") == pytest.approx(C.MCU_PCB_TOP_Z - 3.2)
    assert C.mcu_pcb_bot_z() == C.MCU_PCB_BOT_Z


def test_left_short_jack_and_cover_port_bands():
    assert C.usb_jack_z("left", "short") == pytest.approx((14.740, 17.900))
    assert C.cover_usb_port_z("left", "short") == pytest.approx((14.240, 18.400))


@pytest.mark.parametrize("oled", OLED_ON)
def test_header_tails_below_oled_top(oled):
    assert C.mcu_pcb_top_z(oled) + C.MCU_HEADER_TAIL_H < C.oled_top_z(oled)
    assert C.oled_top_z(oled) == pytest.approx({"long": 25.3, "short": 22.1}[oled])


def test_ramp_top():
    assert C.cover_ramp_top_y() == C.COVER_RAMP_TOP_Y
    for oled in OLED_ON:
        assert C.cover_ramp_top_y(oled) == pytest.approx(80.765)


def test_north_wall_extra():
    assert C.north_wall_extra() == {}
    for oled in OLED_ON:
        extra = C.north_wall_extra(oled)
        assert set(extra) == {12, 14}
        assert extra[14] == pytest.approx(2.665)
        assert extra[12] == pytest.approx(0.165)
        # both runs land on one line: polygon y 118.315
        assert C.TRAY_NORTH_LOW_Y + extra[14] == pytest.approx(118.315)
        assert C.TRAY_NORTH_STEP_Y + extra[12] == pytest.approx(118.315)
