"""PCB phantom geometry checks."""
import pytest
from build123d import Part
from sofle_case import constants as C
from sofle_case import knob as K
from sofle_case.pcb_phantom import build_pcb_phantom


def test_returns_part():
    assert isinstance(build_pcb_phantom(), Part)


# The three checks below ask which BOARD component is the tallest (or lowest) thing on this half,
# so they measure the board WITHOUT the encoder. The EC11 answers that question by fiat — its knob
# crowns 16 mm above the jack and its pins hang below the seat — which would turn all three into
# assertions about the encoder rather than about the jack orientation they exist to pin down.
def test_z_min_at_pcb_seat():
    bb = build_pcb_phantom(include_encoder=False).bounding_box()
    assert abs(bb.min.Z - C.PCB_SEAT_Z) < 0.1


@pytest.mark.parametrize("side", ["right", "left"])
def test_z_max_tracks_this_half_s_jack(side):
    """Neutral (right): the jack sits on the board, so it is the tallest thing. Flipped
    (left): the jack hangs UNDER the board, so the board top is the ceiling instead."""
    bb = build_pcb_phantom(side, include_encoder=False).bounding_box()
    expected = max(C.usb_jack_z(side)[1], C.MCU_PCB_TOP_Z)
    assert abs(bb.max.Z - expected) < 0.1


def test_flipped_jack_is_lower_than_neutral():
    left = build_pcb_phantom("left", include_encoder=False).bounding_box()
    right = build_pcb_phantom("right", include_encoder=False).bounding_box()
    assert left.max.Z < right.max.Z - 2.0, "flipped half should sit visibly lower"


@pytest.mark.parametrize("side", ["right", "left"])
def test_encoder_is_included_by_default(side):
    """The EC11 is board hardware and rides in the phantom unless asked not to.

    It was invisible in every fit-check before: switch_phantom skips SW25 on purpose (it is not an
    MX switch) and this module never picked it up, so the TALLEST OBJECT ON THE KEYBOARD was being
    checked against nothing. The knob crown is the ceiling on both halves — the jack no longer is."""
    with_enc = build_pcb_phantom(side).bounding_box()
    without = build_pcb_phantom(side, include_encoder=False).bounding_box()
    assert with_enc.max.Z > without.max.Z + 10.0, "encoder+knob should tower over the board"
    assert abs(with_enc.max.Z - (K.knob_hem_z() + K.KNOB_H)) < 0.1, "ceiling is the knob crown"
    # ...and the pins hang below the board seat, which is why the seat check excludes it.
    assert with_enc.min.Z < C.PCB_SEAT_Z - 1.0


def test_encoder_can_be_left_out():
    """``include_encoder=False`` is the escape hatch for scenes that already draw the encoder."""
    assert (build_pcb_phantom(include_encoder=False).volume
            < build_pcb_phantom().volume)


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
