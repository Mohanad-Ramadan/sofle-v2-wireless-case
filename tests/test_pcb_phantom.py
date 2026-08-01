"""PCB phantom geometry checks."""
import pytest
from build123d import Part
from sofle_case import constants as C
from sofle_case.pcb_phantom import build_pcb_phantom


def test_returns_part():
    assert isinstance(build_pcb_phantom(), Part)


def test_z_min_at_pcb_seat():
    bb = build_pcb_phantom().bounding_box()
    assert abs(bb.min.Z - C.PCB_SEAT_Z) < 0.1


@pytest.mark.parametrize("side", ["right", "left"])
def test_z_max_tracks_this_half_s_jack(side):
    """Neutral (right): the jack sits on the board, so it is the tallest thing. Flipped
    (left): the jack hangs UNDER the board, so the board top is the ceiling instead."""
    bb = build_pcb_phantom(side).bounding_box()
    expected = max(C.usb_jack_z(side)[1], C.MCU_PCB_TOP_Z)
    assert abs(bb.max.Z - expected) < 0.1


def test_flipped_jack_is_lower_than_neutral():
    left = build_pcb_phantom("left").bounding_box()
    right = build_pcb_phantom("right").bounding_box()
    assert left.max.Z < right.max.Z - 2.0, "flipped half should sit visibly lower"


def test_volume_less_than_bbox():
    """M2 holes + partial fill → phantom volume < solid bounding box."""
    phantom = build_pcb_phantom()
    bb = phantom.bounding_box()
    bbox_vol = (
        (bb.max.X - bb.min.X)
        * (bb.max.Y - bb.min.Y)
        * (bb.max.Z - bb.min.Z)
    )
    assert phantom.volume < bbox_vol
