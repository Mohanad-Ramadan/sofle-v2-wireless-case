from build123d import Part
from sofle_case import constants as C
from sofle_case.mcu_cover import build_mcu_cover


def test_returns_part():
    p = build_mcu_cover()
    assert isinstance(p, Part)


def test_height_extends_above_rim():
    p = build_mcu_cover()
    bb = p.bounding_box()
    assert abs(bb.max.Z - C.MCU_COVER_Z) < 0.01
    # cover starts at PCB_TOP_Z (so the outer-wall merge handles below-rim region)
    assert bb.min.Z <= C.MAIN_RIM_Z


def test_plus_y_flush_with_outer_wall():
    p = build_mcu_cover()
    bb = p.bounding_box()
    assert abs(bb.max.Y - C.OUTER_DEPTH) < 0.01


def test_x_centered_on_mcu():
    p = build_mcu_cover()
    bb = p.bounding_box()
    cx = (bb.min.X + bb.max.X) / 2
    expected_cx = C.pcb_to_case(*C.MCU_POS)[0]
    assert abs(cx - expected_cx) < 0.01
