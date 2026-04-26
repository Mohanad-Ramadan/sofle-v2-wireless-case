"""Verify cached mounting-hole JSON matches constants.MOUNTING_HOLES."""
from sofle_case import constants as C
from sofle_case.pcb_geometry import load_mounting_holes


def test_holes_match_constants():
    parsed = {(round(x, 2), round(y, 2)) for x, y in load_mounting_holes()}
    expected = {(round(x, 2), round(y, 2)) for x, y in C.MOUNTING_HOLES}
    assert parsed == expected, f"drift: parsed={parsed} vs constants={expected}"


def test_five_holes():
    assert len(load_mounting_holes()) == 5
