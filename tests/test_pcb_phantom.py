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
# The battery JST is deliberately NOT excluded: it is the board's floor, and which side of the
# board it sits on is exactly the thing worth pinning. See below.
def test_z_min_is_the_battery_jst_hung_under_the_board():
    """The JST hangs beneath the PCB, like the hotswap sockets, so it — not the seat — is the
    board's lowest point.

    This asserted ``PCB_SEAT_Z`` for as long as nothing was modelled under the board, and that
    was only true because the connector was on the wrong side. Standing on top it fouled the
    cover by 34.2 mm³ and was the single thing holding the case open. Moving it underneath is
    the fix; this is the assertion that records which side it now lives on, so a future edit
    cannot quietly flip it back and still pass.
    """
    bb = build_pcb_phantom(include_encoder=False).bounding_box()
    assert abs(bb.min.Z - C.JST_BOTTOM_Z) < 0.1, (
        f"board floor is Z {bb.min.Z:.2f}, expected the JST at {C.JST_BOTTOM_Z:.2f}"
    )
    assert C.JST_BOTTOM_Z < C.PCB_SEAT_Z, "the JST must hang BELOW the board, not stand on it"


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
