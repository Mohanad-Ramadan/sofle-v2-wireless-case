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

``KNOB_BORE_DEPTH`` was the last unmeasured number and it is now backed out of the real keyboard —
see the constant. Together with the shaft length it decides how high the knob ends up;
``knob_seating_report`` prints that arithmetic rather than hiding it.

TWO THINGS SET THE SEATING, AND THE BEZEL IS NEITHER:

  • THE BUSHING IS THE FLOOR. The Ø7 threaded collar stands 5 mm above the mounting face, to Z 22.0
    — 3.4 mm clear of the ring's top — and this bore is Ø6, narrower than the collar, on a hem
    modelled flat. The knob physically cannot go lower, so ~3.9 mm of collar and bare shaft shows
    above the ring NO MATTER WHAT THE COVER DOES. Styling the bezel cannot close that gap; only a
    taller bezel that hides the collar, or a knob with a skirt recess, would;
  • THE SHAFT HAS TO BE CUT, because the 9 mm bore bottoms out long before the hem gets down to the
    collar: on the as-bought 20 mm shaft the knob hangs at Z 28.0, 5.5 mm high. Cut to
    ``shaft_len_for_seating`` the SHAFT ITSELF becomes the stop, so pushing the knob home lands the
    hem at the design gap instead of leaving it to be eyeballed during assembly.

The failure mode at the other end is real too: a bore deeper than ~14.5 swallows the whole shaft
before the hem clears the collar, and the knob comes to rest ON the brass. ``bushing_is_the_stop``
flags it, and trimming makes that case worse rather than better.
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
KNOB_BORE_DEPTH = 9.0     # mm; BACKED OUT OF THE REAL KEYBOARD, not the listing. On the assembled
                          #   board 6.0 mm of bare Ø6 shaft shows between the top of the bushing
                          #   (Z 22.0) and the knob's hem, so the knob bottoms at Z 28.0 and the
                          #   bore is 37.0 − 28.0 = 9.0. The 15.0 guessed here before ("a 17 mm
                          #   knob bores nearly through") was past the point where the knob lands
                          #   ON the bushing — see bushing_is_the_stop.
KNOB_HEM_CLEAR = 0.5      # mm; design gap between the knob's hem and the cover feature below it


def cover_feature_top_z() -> float:
    from .case import encoder_feature_top_z
    return encoder_feature_top_z()


def knob_hem_z() -> float:
    """Case Z of the knob's hem — the lowest it can sit, plus the design gap.

    THE BUSHING IS THE FLOOR, not the bezel. The Ø7 threaded collar stands 5 mm above the mounting
    face — 3.4 mm clear of the ring's top — and this knob's bore is Ø6, i.e. NARROWER THAN THE
    COLLAR, with a hem modelled flat. So the hem cannot descend past ``BUSHING_TOP_Z`` no matter how
    the cover is styled or how far the shaft is cut; the bezel only wins if a taller one is ever
    drawn. This function used to compare the bezel against the encoder BODY and missed the collar
    sitting 5 mm above it, which put the design hem 2.9 mm inside solid brass.

    If your knob turns out to have a skirt recess wide enough to swallow the collar, this is the
    number that moves — measure the recess and the bezel becomes the floor again."""
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


def knob_seating_report() -> str:
    head = (f"knob Ø{KNOB_OD}×{KNOB_H}, bore {KNOB_BORE_DIA}×{KNOB_BORE_DEPTH} | "
            f"design hem Z {knob_hem_z():.2f} (floor: bushing top {E.BUSHING_TOP_Z:.2f} + "
            f"{KNOB_HEM_CLEAR}) | bottomed-on-shaft hem Z {knob_hem_z_if_bottomed():.2f}")
    if bushing_is_the_stop():
        return (f"{head} | BORE TOO DEEP: the knob bottoms {knob_hem_z() - knob_hem_z_if_bottomed():.2f}"
                f" mm inside the Ø{E.BUSHING_DIA} bushing, so it lands on the collar. Cutting the "
                f"shaft cannot fix this")
    return (f"{head} | shaft trim needed {shaft_trim_needed():.2f} mm "
            f"({E.SHAFT_LEN} → {shaft_len_for_seating():.2f}) | bare shaft on show above the ring "
            f"top ({cover_feature_top_z():.2f}): {knob_hem_z() - cover_feature_top_z():.2f} mm")


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
