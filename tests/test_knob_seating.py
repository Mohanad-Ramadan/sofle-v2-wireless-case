"""Knob seating on the EC11 shaft.

These pin a MEASUREMENT, not a preference: the real knob takes 16 mm of the 20 mm shaft and leaves
4 mm showing. Every number here has been wrong at least once, and the arithmetic feeds a one-way
cut to a metal shaft, so the invariant that matters most is the last test in this file.
"""
from sofle_case import encoder_phantom as E
from sofle_case import knob as K


def test_knob_takes_16_of_the_20mm_shaft():
    """The measured bore covers 16 mm and leaves 4 mm of the shaft exposed."""
    assert K.KNOB_BORE_DEPTH == 16.0
    assert E.SHAFT_TOP_Z - K.knob_hem_z_if_bottomed() == 16.0, "knob should cover 16 mm of shaft"
    assert abs(K.knob_hem_z_if_bottomed() - E.BODY_TOP_Z - 4.0) < 1e-9, (
        "4 mm of shaft should show above the mounting face")


def test_no_collar_stands_between_the_hem_and_the_mounting_face():
    """A Ø6 bore cannot pass a Ø7 collar, so a collar taller than the exposed shaft is a
    contradiction, not a detail. This is the check that falsified the assumed 5 mm bushing."""
    exposed = K.knob_hem_z() - E.BODY_TOP_Z
    assert E.BUSHING_H <= exposed, (
        f"a {E.BUSHING_H} mm collar cannot fit in {exposed} mm of exposed shaft — one of the two "
        f"is measured wrong")


def test_the_knob_bottoms_on_the_shaft_not_on_a_collar():
    """``bushing_is_the_stop`` is the failure mode where trimming makes things worse. It must not
    fire on this hardware."""
    assert not K.bushing_is_the_stop()


def test_hem_clears_the_tallest_hardware_feature():
    """The design and physical seating positions both clear the tallest hardware."""
    floor_z = max(E.BODY_TOP_Z, E.BUSHING_TOP_Z)
    assert K.knob_hem_z() == floor_z + K.KNOB_HEM_CLEAR
    assert K.knob_hem_z_if_bottomed() >= floor_z, (
        "the knob as actually assembled would sit inside hardware")


def test_never_ask_for_a_shaft_shorter_than_the_bore():
    """Cutting the shaft below the bore depth means the knob swallows the whole stub and comes to
    rest on the encoder body — and a cut shaft cannot be grown back.

    Worth being honest about what this does and does not catch. It would NOT have caught the bug it
    was written after: with the guessed 9 mm bore the model asked for a cut to 14.5 mm, and 14.5 > 9
    is perfectly self-consistent. The instruction was only lethal once applied to the real 16 mm
    bore. No internal invariant catches a wrong measured constant — only ``KNOB_BORE_DEPTH`` being
    right does, which is what the first test in this file pins. This one guards the weaker case: a
    future edit that makes the trim arithmetic inconsistent with the bore it already knows about."""
    assert K.shaft_len_for_seating() >= K.KNOB_BORE_DEPTH, (
        f"cut to {K.shaft_len_for_seating()} mm would be shorter than the {K.KNOB_BORE_DEPTH} mm "
        f"bore — the knob would bottom on the encoder body")
