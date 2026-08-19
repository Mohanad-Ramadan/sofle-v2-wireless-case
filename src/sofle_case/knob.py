"""PHANTOM of the user's METAL KNOB — for renders and clash checks only, never printed.

Part in use: aluminium-alloy push-fit potentiometer knob, **Ø13 × 17 mm** (the "13x17mm Silver"
option), Ø6 bore, no set screw,
plastic ribbed insert, indicator line on top
(https://makerselectronics.com/product/aluminum-alloy-potentiometer-knob/).

Two facts drive the cover design:

  • it is a STRAIGHT Ø13 cylinder — and Ø13 is SMALLER THAN THE ENCODER IT SITS ON. The plate
    window measures Ø18.04 across its corners and the sealed bezel needs a Ø19.4-ish foot to carry
    its roof, so the bezel cannot hide under this knob the way it could under a Ø17 one. The knob
    sits IN the bezel rather than over it, and the bezel is a deliberate visible collar;
  • the listing does not publish a skirt recess, and a push-fit knob with a ribbed insert usually
    has none worth counting on, so the underside is modelled FLAT. That is the worst case: the
    knob can descend over nothing, and its hem must clear the tallest thing the cover puts under
    it. If yours does have a recess, measure it — a deep one would let the knob sit lower.

``KNOB_BORE_DEPTH`` is measured on the real knob — see the constant. Together with the shaft length
it decides how high the knob ends up; ``knob_seating_report`` prints that arithmetic rather than
hiding it.

THE PLATEAU IS THE FLOOR, AND THE SHAFT DOES NOT GET CUT:

  • the bore swallows 16 of the shaft's 20 mm, so the knob comes down until it bottoms on the shaft
    with its hem 4 mm above the mounting face (Z 21.4). That is 0.5 mm above the plateau top — the
    design gap, reached with no trimming at all;
  • this module used to claim THE BUSHING IS THE FLOOR, on an assumed Ø7 collar standing 5 mm above
    the mounting face. That collar cannot exist on this part: a Ø6 bore cannot pass a Ø7 collar, so
    a 5 mm one would cap the knob's travel at 15 mm of shaft, and the measured coverage is 16. See
    ``encoder_phantom.BUSHING_H``. The conclusion is robust — anything up to a 3.5 mm collar leaves
    the seating unchanged, because the plateau top (20.9) is the taller floor either way.

The old numbers had this exactly backwards and it was nearly expensive. With the guessed 9 mm bore
the model asked for the shaft to be CUT to 14.5 mm; against the real 16 mm bore that cut is shorter
than the bore itself, so the knob would swallow the whole stub and come to rest on the encoder body
— a one-way cut to a metal shaft, made on a guess. ``bushing_is_the_stop`` still guards the other
end (a bore deep enough to land the knob on a collar, where trimming makes things worse), it simply
no longer fires on this hardware.
"""
from __future__ import annotations
from typing import cast

from build123d import Part, Solid

from . import constants as C
from . import encoder_phantom as E

KNOB_OD = 13.0            # mm; the "13x17mm" option → Ø13. The variant list settles the naming:
                          #   40x10 is a Ø40 × 10 control knob, not a Ø10 × 40 rod, so the first
                          #   number is the diameter throughout.
KNOB_H = 17.0             # mm; the second number
KNOB_BORE_DIA = 6.0       # mm; push-fit onto the Ø6 shaft
KNOB_BORE_DEPTH = 16.0    # mm; MEASURED on the real knob: it takes 16 mm of the 20 mm shaft and
                          #   leaves 4 mm showing. 16 + 4 = 20 closes on the shaft length, which is
                          #   what makes the reading self-checking. Two earlier values were wrong in
                          #   opposite directions: 15.0 was a guess ("a 17 mm knob bores nearly
                          #   through"), and 9.0 was *derived* from it being wrong — backed out of a
                          #   bushing top (Z 22.0) that does not exist on this part. A 17 mm knob
                          #   boring 16 mm deep leaves a 1 mm crown, which is what this knob is.
KNOB_HEM_CLEAR = 0.5      # mm; design gap between the knob's hem and the cover feature below it


def cover_feature_top_z() -> float:
    """Case Z of the tallest COVER feature at the encoder — the other candidate for the hem's floor.

    Deferred to ``case`` when it publishes a figure, because what the cover does at the encoder is
    that module's call, not this one's. Until it publishes one, the cover there IS the ogee plateau
    and its top is the feature top. The import stays function-local AND guarded so this module keeps
    answering while a cover-side redesign is out of tree — without the guard, importing the knob
    (and therefore the PCB phantom, and therefore most of the suite) fails outright."""
    try:
        from .case import encoder_feature_top_z
    except ImportError:
        return C.ENCODER_SHELL_TOP_Z
    return encoder_feature_top_z()


def knob_hem_z() -> float:
    """Case Z of the knob's hem — the lowest it can sit, plus the design gap.

    THE PLATEAU IS THE FLOOR. With no collar on this part (``encoder_phantom.BUSHING_H`` = 0) the
    tallest thing under the hem is the cover's own encoder plateau, so the hem sits ``KNOB_HEM_CLEAR``
    above its top. ``BUSHING_TOP_Z`` stays in the ``max`` deliberately: it is the guard that fires
    if a collar is ever measured onto this part, and up to 3.5 mm it changes nothing because the
    plateau is taller.

    Two earlier versions of this function were both wrong. The first compared the bezel against the
    encoder BODY only; the second "fixed" it by making an assumed 5 mm collar the floor, which put
    the design hem 1.5 mm above where the knob actually rests. If your knob turns out to have a
    skirt recess, this is the number that moves — measure the recess."""
    return max(C.ENCODER_BODY_TOP_Z, E.BUSHING_TOP_Z, cover_feature_top_z()) + KNOB_HEM_CLEAR


def knob_hem_z_if_bottomed() -> float:
    """Case Z of the hem if the knob is simply pushed on until its bore bottoms on the shaft.

    This is the number that bites in practice: an untrimmed 20 mm shaft holds the knob well above
    the bezel no matter what the cover looks like."""
    return E.SHAFT_TOP_Z - KNOB_BORE_DEPTH


def through_bore_hem_z() -> float:
    """Case Z of the hem if the bore went CLEAN THROUGH the knob — the lowest a knob of this height
    could ever reach on an untrimmed shaft, and the check on whether boring is even the lever."""
    return E.SHAFT_TOP_Z - KNOB_H


def bushing_is_the_stop() -> bool:
    """True when the bore is deep enough to swallow the whole shaft before the hem clears the
    collar — so the knob lands ON the Ø7 bushing and the design gap is unreachable by trimming.

    Trimming makes this WORSE, not better: it lowers the bottomed hem further into the collar. The
    fix there is a shallower bore, a taller bushing stack (nut/washer), or a knob with a recess."""
    return knob_hem_z_if_bottomed() < knob_hem_z()


def shaft_len_for_seating() -> float:
    """Shaft length, from the mounting face, that makes the SHAFT ITSELF the stop: the bore bottoms
    out exactly as the hem reaches ``knob_hem_z``.

    Capped at the as-bought length, because a shaft can be cut and never grown. When the cap binds,
    ``bushing_is_the_stop`` is True and no cut helps."""
    return min(E.SHAFT_LEN, knob_hem_z() + KNOB_BORE_DEPTH - E.BODY_TOP_Z)


def shaft_trim_needed() -> float:
    """How much shaft must come off for the knob to reach ``knob_hem_z`` (0 if it already does)."""
    return max(0.0, knob_hem_z_if_bottomed() - knob_hem_z())


def _seating_floor() -> tuple[str, float]:
    """Which feature the hem actually rests on, and its Z — named rather than assumed, because the
    report asserted "bushing top" through two versions where the bushing was not the winner."""
    floors = (("encoder body", C.ENCODER_BODY_TOP_Z),
              ("bushing top", E.BUSHING_TOP_Z),
              ("cover plateau", cover_feature_top_z()))
    return max(floors, key=lambda f: f[1])


def knob_seating_report() -> str:
    floor_name, floor_z = _seating_floor()
    head = (f"knob Ø{KNOB_OD}×{KNOB_H}, bore {KNOB_BORE_DIA}×{KNOB_BORE_DEPTH} | "
            f"design hem Z {knob_hem_z():.2f} (floor: {floor_name} {floor_z:.2f} + "
            f"{KNOB_HEM_CLEAR}) | bottomed-on-shaft hem Z {knob_hem_z_if_bottomed():.2f}")
    if bushing_is_the_stop():
        return (f"{head} | BORE TOO DEEP: the knob bottoms {knob_hem_z() - knob_hem_z_if_bottomed():.2f}"
                f" mm inside the Ø{E.BUSHING_DIA} bushing, so it lands on the collar. Cutting the "
                f"shaft cannot fix this")
    # Two gaps, and only one of them is what you look at. The design gap is KNOB_HEM_CLEAR by
    # construction whenever the cover is the floor, so quoting it alone says nothing — it read
    # "0.50 mm" for a cover-side style that actually leaves 2.40 mm of bare shaft showing. What is
    # ON SHOW is measured from the hem where the knob ACTUALLY lands, which is the bottomed one
    # until somebody takes a saw to the shaft.
    feature_z = cover_feature_top_z()
    trim = shaft_trim_needed()
    on_show = knob_hem_z_if_bottomed() - feature_z
    tail = (f"as-assembled bare shaft above the cover feature ({feature_z:.2f}): {on_show:.2f} mm")
    if trim > 0:
        tail += (f" — closing it to the {KNOB_HEM_CLEAR} design gap means cutting {trim:.2f} mm "
                 f"off the shaft ({E.SHAFT_LEN} → {shaft_len_for_seating():.2f}), which is "
                 f"one-way")
    return f"{head} | shaft trim needed {trim:.2f} mm | {tail}"


def build_knob_phantom(bottomed: bool = False) -> Part:
    """The knob in case coordinates. ``bottomed`` shows where it lands on an untrimmed shaft."""
    hem = knob_hem_z_if_bottomed() if bottomed else knob_hem_z()
    body = Solid.make_cylinder(KNOB_OD / 2, KNOB_H).translate((0, 0, hem))
    bore = Solid.make_cylinder(KNOB_BORE_DIA / 2, KNOB_BORE_DEPTH).translate((0, 0, hem))
    knob = cast(Part, body - bore)
    ex, ey = C.pcb_to_case(*C.SW_ENCODER_POS)
    return cast(Part, knob.translate((ex, ey, 0)))


def place_knob(bottomed: bool = False) -> Part:
    """The knob in RIGHT-HAND case coordinates — the caller mirrors it for the left half, exactly
    as the case itself is built right-handed and then mirrored."""
    return build_knob_phantom(bottomed=bottomed)


if __name__ == "__main__":
    from ocp_vscode import show
    from .encoder_phantom import build_ec11
    print(knob_seating_report())
    show(place_knob(), place_knob(bottomed=True), build_ec11(), build_ec11(trimmed=False),
         names=["knob(design seating)", "knob(untrimmed shaft)",
                f"ec11(shaft cut to {shaft_len_for_seating():.2f})",
                f"ec11(as bought, {E.SHAFT_LEN} shaft)"])
